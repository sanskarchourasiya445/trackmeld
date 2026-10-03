"""Independent Hard-Constraint Checking Functions for TrackMeld Schedule Validation.

CRITICAL ARCHITECTURAL BOUNDARY:
These checks are 100% independent from the Phase 4 CompatibilityEngine and the
Phase 6 CP-SAT mathematical solver. They recompute and verify all hard physical,
safety, and temporal constraints directly from raw PlanningSnapshot data.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict

from backend.app.domain.temporal import TimeInterval
from backend.app.domain.scheduling import ScheduleResult, ScheduledTaskResult, SchedulerStatus
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.validation.models import (
    ValidationFinding,
    ValidationSeverity,
    ValidationCategory,
)


def _to_utc_dt(val: Any) -> datetime:
    """Normalize timestamp or ISO string to UTC datetime."""
    if isinstance(val, str):
        dt = datetime.fromisoformat(val)
    elif isinstance(val, datetime):
        dt = val
    else:
        raise ValueError(f"Cannot convert {val} of type {type(val)} to datetime")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class ScheduleCheckRunner:
    """Runs independent verification checks against a PlanningSnapshot and ScheduleResult."""

    def __init__(self, snapshot: PlanningSnapshot, schedule: ScheduleResult) -> None:
        self.snapshot = snapshot
        self.schedule = schedule
        self.findings: List[ValidationFinding] = []
        self.checks_executed: List[str] = []

        # Audit counters
        self.checked_task_count = 0
        self.checked_section_count = 0
        self.checked_resource_count = 0
        self.checked_train_movement_count = 0

    def run_all_checks(self) -> List[ValidationFinding]:
        """Execute all independent checks in deterministic order."""
        self._check_structural()
        self._check_horizon()
        self._check_task_windows()
        self._check_durations_and_buffers()
        self._check_section_occupancy()
        self._check_multi_section_tasks()
        self._check_train_movements()
        self._check_track_spatial_safety()
        self._check_resources()
        self._check_dependencies()
        self._check_mandatory_tasks()
        self._check_domain_rules()
        self._check_solver_output_sanity()

        # Sort findings deterministically
        self.findings.sort(key=lambda f: f.sort_key())
        return self.findings

    # -------------------------------------------------------------------------
    # 1. Structural Checks
    # -------------------------------------------------------------------------
    def _check_structural(self) -> None:
        self.checks_executed.append("STRUCTURAL")
        seen_task_ids: Set[str] = set()

        for st in self.schedule.scheduled_tasks:
            self.checked_task_count += 1
            t_id = st.task_id

            # 1.1 Exists in snapshot
            if t_id not in self.snapshot.tasks_map:
                self.findings.append(
                    ValidationFinding(
                        code="UNKNOWN_TASK_SCHEDULED",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURAL,
                        message=f"Task '{t_id}' scheduled but absent from input PlanningSnapshot.",
                        task_id=t_id,
                        expected=f"Task in {list(self.snapshot.tasks_map.keys())[:5]}...",
                        actual=t_id,
                    )
                )

            # 1.2 Duplicate schedule record
            if t_id in seen_task_ids:
                self.findings.append(
                    ValidationFinding(
                        code="DUPLICATE_TASK_PLACEMENT",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURAL,
                        message=f"Task '{t_id}' appears multiple times in scheduled tasks list.",
                        task_id=t_id,
                        actual=f"Multiple occurrences of task_id '{t_id}'",
                    )
                )
            seen_task_ids.add(t_id)

            # 1.3 Interval integrity
            if st.interval is None or st.possession_interval is None:
                self.findings.append(
                    ValidationFinding(
                        code="MISSING_INTERVAL_SPECIFICATION",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURAL,
                        message=f"Task '{t_id}' has null work interval or possession interval.",
                        task_id=t_id,
                    )
                )
            else:
                if st.interval.start >= st.interval.end:
                    self.findings.append(
                        ValidationFinding(
                            code="INVALID_WORK_INTERVAL_BOUNDS",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.TEMPORAL,
                            message=f"Task '{t_id}' interval has non-positive duration [{st.interval.start.isoformat()}, {st.interval.end.isoformat()}). Half-open requires start < end.",
                            task_id=t_id,
                            actual=f"start={st.interval.start.isoformat()}, end={st.interval.end.isoformat()}",
                        )
                    )

            # 1.4 Referenced section existence
            orig = self.snapshot.tasks_map.get(t_id, {})
            sec_id = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)
            if sec_id and sec_id not in self.snapshot.sections_map:
                self.findings.append(
                    ValidationFinding(
                        code="UNKNOWN_SECTION_REFERENCED",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.STRUCTURAL,
                        message=f"Task '{t_id}' references unknown primary section '{sec_id}'.",
                        task_id=t_id,
                        section_id=sec_id,
                    )
                )

    # -------------------------------------------------------------------------
    # 2. Horizon Checks
    # -------------------------------------------------------------------------
    def _check_horizon(self) -> None:
        self.checks_executed.append("HORIZON")
        h_start = self.snapshot.horizon.start
        h_end = self.snapshot.horizon.end

        for st in self.schedule.scheduled_tasks:
            if not st.interval or not st.possession_interval:
                continue

            # Work interval within horizon
            if st.interval.start < h_start or st.interval.end > h_end:
                self.findings.append(
                    ValidationFinding(
                        code="HORIZON_BOUNDARY_BREACH",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.HORIZON,
                        message=f"Task '{st.task_id}' work interval [{st.interval.start.isoformat()}, {st.interval.end.isoformat()}) exceeds horizon [{h_start.isoformat()}, {h_end.isoformat()}).",
                        task_id=st.task_id,
                        expected=f"[{h_start.isoformat()}, {h_end.isoformat()})",
                        actual=f"[{st.interval.start.isoformat()}, {st.interval.end.isoformat()})",
                    )
                )

            # Possession interval within horizon
            if st.possession_interval.start < h_start or st.possession_interval.end > h_end:
                self.findings.append(
                    ValidationFinding(
                        code="POSSESSION_HORIZON_BREACH",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.HORIZON,
                        message=f"Task '{st.task_id}' possession envelope [{st.possession_interval.start.isoformat()}, {st.possession_interval.end.isoformat()}) exceeds planning horizon.",
                        task_id=st.task_id,
                        expected=f"[{h_start.isoformat()}, {h_end.isoformat()})",
                        actual=f"[{st.possession_interval.start.isoformat()}, {st.possession_interval.end.isoformat()})",
                    )
                )

    # -------------------------------------------------------------------------
    # 3. Task Window Checks
    # -------------------------------------------------------------------------
    def _check_task_windows(self) -> None:
        self.checks_executed.append("TASK_WINDOW")
        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id)
            if not orig or not st.interval:
                continue

            w_start_raw = orig.get("window_start") if isinstance(orig, dict) else getattr(orig, "window_start")
            w_end_raw = orig.get("window_end") if isinstance(orig, dict) else getattr(orig, "window_end")
            if not w_start_raw or not w_end_raw:
                continue

            w_start = _to_utc_dt(w_start_raw)
            w_end = _to_utc_dt(w_end_raw)

            # Work must be completely inside allowed window [w_start, w_end)
            if st.interval.start < w_start or st.interval.end > w_end:
                self.findings.append(
                    ValidationFinding(
                        code="TASK_WINDOW_VIOLATION",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.WINDOW,
                        message=f"Task '{st.task_id}' interval [{st.interval.start.isoformat()}, {st.interval.end.isoformat()}) violates allowed work window [{w_start.isoformat()}, {w_end.isoformat()}).",
                        task_id=st.task_id,
                        expected=f"[{w_start.isoformat()}, {w_end.isoformat()})",
                        actual=f"[{st.interval.start.isoformat()}, {st.interval.end.isoformat()})",
                        evidence={"window_start": w_start.isoformat(), "window_end": w_end.isoformat()},
                    )
                )

    # -------------------------------------------------------------------------
    # 4. Duration & Buffer Checks
    # -------------------------------------------------------------------------
    def _check_durations_and_buffers(self) -> None:
        self.checks_executed.append("DURATION_AND_BUFFERS")
        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id)
            if not orig or not st.interval or not st.possession_interval:
                continue

            exp_dur = orig.get("estimated_duration_minutes", 60) if isinstance(orig, dict) else getattr(orig, "estimated_duration_minutes", 60)
            buf_before = orig.get("safety_buffer_before_minutes", 10) if isinstance(orig, dict) else getattr(orig, "safety_buffer_before_minutes", 10)
            buf_after = orig.get("safety_buffer_after_minutes", 10) if isinstance(orig, dict) else getattr(orig, "safety_buffer_after_minutes", 10)

            act_dur = st.interval.duration_minutes
            if abs(act_dur - exp_dur) > 0.01 or abs(st.duration_minutes - exp_dur) > 0.01:
                self.findings.append(
                    ValidationFinding(
                        code="DURATION_MISMATCH",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.DURATION,
                        message=f"Task '{st.task_id}' scheduled duration ({act_dur:.1f} min / reported {st.duration_minutes:.1f} min) does not match defined task duration {exp_dur:.1f} min.",
                        task_id=st.task_id,
                        expected=f"{exp_dur} minutes",
                        actual=f"{act_dur} minutes",
                    )
                )

            # Possession envelope check
            exp_pos_start = st.interval.start - timedelta(minutes=buf_before)
            exp_pos_end = st.interval.end + timedelta(minutes=buf_after)

            if abs((st.possession_interval.start - exp_pos_start).total_seconds()) > 1.0 or abs((st.possession_interval.end - exp_pos_end).total_seconds()) > 1.0:
                self.findings.append(
                    ValidationFinding(
                        code="POSSESSION_BUFFER_CORRUPTED",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.TEMPORAL,
                        message=f"Task '{st.task_id}' possession envelope [{st.possession_interval.start.isoformat()}, {st.possession_interval.end.isoformat()}) fails to reflect buffers (-{buf_before}m, +{buf_after}m).",
                        task_id=st.task_id,
                        expected=f"[{exp_pos_start.isoformat()}, {exp_pos_end.isoformat()})",
                        actual=f"[{st.possession_interval.start.isoformat()}, {st.possession_interval.end.isoformat()})",
                    )
                )

    # -------------------------------------------------------------------------
    # 5. Section Occupancy Checks
    # -------------------------------------------------------------------------
    def _check_section_occupancy(self) -> None:
        self.checks_executed.append("SECTION_OCCUPANCY")
        tasks_by_sec = defaultdict(list)

        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            secs = set()
            sec_id = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)
            if sec_id:
                secs.add(sec_id)
            add_secs = orig.get("additional_sections", []) if isinstance(orig, dict) else [getattr(s, "section_id", s) for s in getattr(orig, "affected_sections", [])]
            for a_sec in add_secs:
                secs.add(a_sec)
            for a_sec in (st.affected_sections or []):
                secs.add(a_sec)

            for s in secs:
                tasks_by_sec[s].append(st)

        self.checked_section_count = len(tasks_by_sec)

        for sec_id, task_list in tasks_by_sec.items():
            if len(task_list) <= 1:
                continue

            # Sort by possession interval start
            sorted_tasks = sorted(task_list, key=lambda t: t.possession_interval.start)

            for i in range(len(sorted_tasks) - 1):
                t1 = sorted_tasks[i]
                t2 = sorted_tasks[i + 1]

                # Half-open check: overlap iff max(start1, start2) < min(end1, end2)
                # Since sorted by start, overlap exists iff start2 < end1
                if t2.possession_interval.start < t1.possession_interval.end:
                    overlap_int = TimeInterval(
                        start=max(t1.possession_interval.start, t2.possession_interval.start),
                        end=min(t1.possession_interval.end, t2.possession_interval.end),
                    )
                    self.findings.append(
                        ValidationFinding(
                            code="SECTION_OCCUPANCY_CONFLICT",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.SECTION,
                            message=f"Physical track collision on section '{sec_id}' between task '{t1.task_id}' and '{t2.task_id}'.",
                            task_id=t2.task_id,
                            section_id=sec_id,
                            evidence={
                                "conflicting_task_1": t1.task_id,
                                "interval_1": f"[{t1.possession_interval.start.isoformat()}, {t1.possession_interval.end.isoformat()})",
                                "conflicting_task_2": t2.task_id,
                                "interval_2": f"[{t2.possession_interval.start.isoformat()}, {t2.possession_interval.end.isoformat()})",
                                "overlap": f"[{overlap_int.start.isoformat()}, {overlap_int.end.isoformat()})",
                            },
                        )
                    )

    # -------------------------------------------------------------------------
    # 6. Multi-Section Task Checks
    # -------------------------------------------------------------------------
    def _check_multi_section_tasks(self) -> None:
        self.checks_executed.append("MULTI_SECTION")
        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            add_secs = orig.get("additional_sections", []) if isinstance(orig, dict) else [s.section_id for s in getattr(orig, "affected_sections", [])]
            if not add_secs:
                continue

            for sec_id in add_secs:
                if sec_id not in self.snapshot.sections_map:
                    self.findings.append(
                        ValidationFinding(
                            code="UNKNOWN_MULTI_SECTION_REFERENCED",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.MULTI_SECTION,
                            message=f"Multi-section task '{st.task_id}' references non-existent corridor section '{sec_id}'.",
                            task_id=st.task_id,
                            section_id=sec_id,
                        )
                    )

    # -------------------------------------------------------------------------
    # 7. Train Movement Clearance Checks
    # -------------------------------------------------------------------------
    def _check_train_movements(self) -> None:
        self.checks_executed.append("TRAIN_MOVEMENT")
        self.checked_train_movement_count = len(self.snapshot.train_passes)

        # Index train passes by section for O(1) section retrieval
        trains_by_sec = defaultdict(list)
        for tp in self.snapshot.train_passes:
            trains_by_sec[tp.section_id].append(tp)

        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            primary_sec = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)
            add_secs = orig.get("additional_sections", []) if isinstance(orig, dict) else [getattr(s, "section_id", s) for s in getattr(orig, "affected_sections", [])]
            all_secs = set()
            if primary_sec:
                all_secs.add(primary_sec)
            all_secs.update(add_secs)
            if st.affected_sections:
                all_secs.update(st.affected_sections)

            for sec_id in all_secs:
                if not sec_id:
                    continue
                for tp in trains_by_sec.get(sec_id, []):
                    # Half-open overlap check: pos_start < train_end AND train_start < pos_end
                    if st.possession_interval.start < tp.interval.end and tp.interval.start < st.possession_interval.end:
                        overlap_start = max(st.possession_interval.start, tp.interval.start)
                        overlap_end = min(st.possession_interval.end, tp.interval.end)
                        self.findings.append(
                            ValidationFinding(
                                code="TRAIN_MOVEMENT_CONFLICT",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.TRAIN_MOVEMENT,
                                message=f"Possession for task '{st.task_id}' collides with scheduled train '{tp.train_number}' on section '{sec_id}'.",
                                task_id=st.task_id,
                                section_id=sec_id,
                                train_movement_id=tp.train_id,
                                evidence={
                                    "train_number": tp.train_number,
                                    "train_interval": f"[{tp.interval.start.isoformat()}, {tp.interval.end.isoformat()})",
                                    "possession_interval": f"[{st.possession_interval.start.isoformat()}, {st.possession_interval.end.isoformat()})",
                                    "overlap": f"[{overlap_start.isoformat()}, {overlap_end.isoformat()})",
                                },
                            )
                        )

    # -------------------------------------------------------------------------
    # 7b. Track Spatial Safety Checks (Phase 16G-C)
    # -------------------------------------------------------------------------
    def _check_track_spatial_safety(self) -> None:
        """Independent verification of track assignments, direction constraints, and adjacent track safety.

        CRITICAL ARCHITECTURAL BOUNDARY:
        - Independent post-solve audit: does NOT call CompatibilityEngine or CP-SAT.
        - Uses pure, deterministic domain functions from backend.app.domain.spatial_compatibility.
        - Additive diagnostic and safety layer: DOES NOT relax or replace section-level mutex.
        - Whole-section checks (_check_section_occupancy, _check_train_movements) remain authoritative.
        """
        self.checks_executed.append("TRACK_SPATIAL_SAFETY")
        tracks_map = getattr(self.snapshot, "tracks_map", {}) or {}

        # 1. Audit Track Assignments and Direction Alignment on Scheduled Tasks
        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            t_track_id = orig.get("track_id") if isinstance(orig, dict) else getattr(orig, "track_id", None)
            sec_id = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)

            if t_track_id:
                # 1.1 Invalid Track Assignment
                if t_track_id not in tracks_map:
                    self.findings.append(
                        ValidationFinding(
                            code="INVALID_TRACK_ASSIGNMENT",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.TRACK,
                            message=f"Task '{st.task_id}' references unknown or invalid track '{t_track_id}' not found in planning snapshot infrastructure.",
                            task_id=st.task_id,
                            section_id=sec_id,
                            actual=t_track_id,
                            expected="Valid track ID from snapshot.tracks_map",
                        )
                    )
                else:
                    # 1.2 Direction conflict on unidirectional track
                    track_obj = tracks_map[t_track_id]
                    trk_dir = getattr(track_obj, "direction", None) or (track_obj.get("direction") if isinstance(track_obj, dict) else None)
                    task_dir = orig.get("direction") if isinstance(orig, dict) else getattr(orig, "direction", None)
                    if task_dir in ("UP", "DOWN") and trk_dir in ("UP", "DOWN") and task_dir != trk_dir:
                        self.findings.append(
                            ValidationFinding(
                                code="TRACK_DIRECTION_CONFLICT",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.TRACK,
                                message=f"Task '{st.task_id}' direction '{task_dir}' conflicts with track '{t_track_id}' direction '{trk_dir}'.",
                                task_id=st.task_id,
                                section_id=sec_id,
                                evidence={"task_direction": task_dir, "track_direction": trk_dir, "track_id": t_track_id},
                            )
                        )

        # 2. Audit Track Assignments and Direction on Train Movements
        raw_movs = getattr(self.snapshot, "train_movements", []) or []
        for m in raw_movs:
            m_id = getattr(m, "movement_id", None) or (m.get("movement_id") if isinstance(m, dict) else None)
            m_track_id = getattr(m, "track_id", None) or (m.get("track_id") if isinstance(m, dict) else None)
            if m_track_id:
                if m_track_id not in tracks_map:
                    self.findings.append(
                        ValidationFinding(
                            code="INVALID_TRACK_ASSIGNMENT",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.TRACK,
                            message=f"Train movement '{m_id}' references unknown or invalid track '{m_track_id}'.",
                            train_movement_id=m_id,
                            actual=m_track_id,
                            expected="Valid track ID from snapshot.tracks_map",
                        )
                    )
                else:
                    track_obj = tracks_map[m_track_id]
                    trk_dir = getattr(track_obj, "direction", None) or (track_obj.get("direction") if isinstance(track_obj, dict) else None)
                    m_dir = getattr(m, "direction", None) or (m.get("direction") if isinstance(m, dict) else None)
                    if m_dir in ("UP", "DOWN") and trk_dir in ("UP", "DOWN") and m_dir != trk_dir:
                        self.findings.append(
                            ValidationFinding(
                                code="TRACK_DIRECTION_CONFLICT",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.TRACK,
                                message=f"Train movement '{m_id}' direction '{m_dir}' conflicts with track '{m_track_id}' direction '{trk_dir}'.",
                                train_movement_id=m_id,
                                evidence={"movement_direction": m_dir, "track_direction": trk_dir, "track_id": m_track_id},
                            )
                        )

        # 3. Audit Train Passes and Traversals for Direction Conflict
        for tp in getattr(self.snapshot, "train_passes", []) or []:
            tp_track = getattr(tp, "track_id", None) or (tp.get("track_id") if isinstance(tp, dict) else None)
            if tp_track:
                if tp_track not in tracks_map:
                    self.findings.append(
                        ValidationFinding(
                            code="INVALID_TRACK_ASSIGNMENT",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.TRACK,
                            message=f"Train pass '{tp.pass_id}' references unknown or invalid track '{tp_track}'.",
                            train_movement_id=tp.train_id,
                            actual=tp_track,
                            expected="Valid track ID from snapshot.tracks_map",
                        )
                    )
                else:
                    track_obj = tracks_map[tp_track]
                    trk_dir = getattr(track_obj, "direction", None) or (track_obj.get("direction") if isinstance(track_obj, dict) else None)
                    tp_dir = getattr(tp, "direction", None) or (tp.get("direction") if isinstance(tp, dict) else None)
                    if tp_dir in ("UP", "DOWN") and trk_dir in ("UP", "DOWN") and tp_dir != trk_dir:
                        self.findings.append(
                            ValidationFinding(
                                code="TRACK_DIRECTION_CONFLICT",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.TRACK,
                                message=f"Train pass '{tp.pass_id}' direction '{tp_dir}' conflicts with track '{tp_track}' direction '{trk_dir}'.",
                                train_movement_id=tp.train_id,
                                evidence={"pass_direction": tp_dir, "track_direction": trk_dir, "track_id": tp_track},
                            )
                        )

        # 4. Pairwise Adjacent Track Analysis Between Scheduled Tasks
        tasks_by_sec = defaultdict(list)
        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            sec_id = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)
            if sec_id:
                tasks_by_sec[sec_id].append(st)

        from backend.app.domain.spatial_compatibility import (
            evaluate_spatial_compatibility,
            SpatialOccupant,
            SpatialCompatibilityStatus,
            SpatialCompatibilityReason,
        )

        for sec_id, task_list in tasks_by_sec.items():
            if len(task_list) <= 1:
                continue

            for i in range(len(task_list)):
                for j in range(i + 1, len(task_list)):
                    st1 = task_list[i]
                    st2 = task_list[j]

                    # Temporal overlap check [start, end)
                    if not (st1.possession_interval.start < st2.possession_interval.end and st2.possession_interval.start < st1.possession_interval.end):
                        continue

                    orig1 = self.snapshot.tasks_map.get(st1.task_id, {})
                    orig2 = self.snapshot.tasks_map.get(st2.task_id, {})
                    trk1_id = orig1.get("track_id") if isinstance(orig1, dict) else getattr(orig1, "track_id", None)
                    trk2_id = orig2.get("track_id") if isinstance(orig2, dict) else getattr(orig2, "track_id", None)

                    # If either has no track, section check already handles it
                    if not trk1_id or not trk2_id or trk1_id not in tracks_map or trk2_id not in tracks_map:
                        continue

                    # If same track, SECTION_OCCUPANCY_CONFLICT already flags ERROR; avoid redundant duplicate finding
                    if trk1_id == trk2_id:
                        continue

                    occ1 = SpatialOccupant.from_task(orig1, interval_override=(st1.possession_interval.start, st1.possession_interval.end))
                    occ2 = SpatialOccupant.from_task(orig2, interval_override=(st2.possession_interval.start, st2.possession_interval.end))

                    res = evaluate_spatial_compatibility(occ1, occ2, tracks_map)

                    if res.status == SpatialCompatibilityStatus.INCOMPATIBLE:
                        if res.reason == SpatialCompatibilityReason.ADJACENT_TRACK_FULL_BLOCK:
                            self.findings.append(
                                ValidationFinding(
                                    code="ADJACENT_TRACK_FULL_BLOCK",
                                    severity=ValidationSeverity.ERROR,
                                    category=ValidationCategory.TRACK,
                                    message=res.message,
                                    task_id=st2.task_id,
                                    section_id=sec_id,
                                    evidence=res.evidence,
                                )
                            )
                    elif res.status == SpatialCompatibilityStatus.COMPATIBLE and res.requires_caution_order:
                        self.findings.append(
                            ValidationFinding(
                                code="ADJACENT_TRACK_CAUTION_REQUIRED",
                                severity=ValidationSeverity.INFO,
                                category=ValidationCategory.TRACK,
                                message=res.message,
                                task_id=st2.task_id,
                                section_id=sec_id,
                                evidence=res.evidence,
                            )
                        )
                    elif res.status == SpatialCompatibilityStatus.INSUFFICIENT_DATA:
                        if res.reason in (SpatialCompatibilityReason.MISSING_ADJACENCY_METADATA, SpatialCompatibilityReason.UNSPECIFIED_SPATIAL_RELATION):
                            self.findings.append(
                                ValidationFinding(
                                    code="SPATIAL_METADATA_INCOMPLETE",
                                    severity=ValidationSeverity.INFO,
                                    category=ValidationCategory.TRACK,
                                    message=res.message,
                                    task_id=st2.task_id,
                                    section_id=sec_id,
                                    evidence=res.evidence,
                                )
                            )

        # 5. Pairwise Adjacent Track Analysis Between Scheduled Tasks and Train Passes
        for sec_id, task_list in tasks_by_sec.items():
            train_passes_in_sec = [tp for tp in getattr(self.snapshot, "train_passes", []) if getattr(tp, "section_id", None) == sec_id]
            for st in task_list:
                orig = self.snapshot.tasks_map.get(st.task_id, {})
                trk_id = orig.get("track_id") if isinstance(orig, dict) else getattr(orig, "track_id", None)
                if not trk_id or trk_id not in tracks_map:
                    continue

                for tp in train_passes_in_sec:
                    # Check temporal overlap
                    if not (st.possession_interval.start < tp.interval.end and tp.interval.start < st.possession_interval.end):
                        continue

                    tp_track = getattr(tp, "track_id", None) or (tp.get("track_id") if isinstance(tp, dict) else None)
                    if not tp_track or tp_track not in tracks_map:
                        # Unresolved traversal/pass track: section check already covers it; do not fabricate
                        continue

                    # If same track, TRAIN_MOVEMENT_CONFLICT already flags it
                    if trk_id == tp_track:
                        continue

                    occ_task = SpatialOccupant.from_task(orig, interval_override=(st.possession_interval.start, st.possession_interval.end))
                    occ_train = SpatialOccupant.from_train_pass(tp)

                    res = evaluate_spatial_compatibility(occ_task, occ_train, tracks_map)

                    if res.status == SpatialCompatibilityStatus.INCOMPATIBLE:
                        if res.reason == SpatialCompatibilityReason.ADJACENT_TRACK_FULL_BLOCK:
                            self.findings.append(
                                ValidationFinding(
                                    code="ADJACENT_TRACK_FULL_BLOCK",
                                    severity=ValidationSeverity.ERROR,
                                    category=ValidationCategory.TRACK,
                                    message=res.message,
                                    task_id=st.task_id,
                                    section_id=sec_id,
                                    train_movement_id=tp.train_id,
                                    evidence=res.evidence,
                                )
                            )
                    elif res.status == SpatialCompatibilityStatus.COMPATIBLE and res.requires_caution_order:
                        self.findings.append(
                            ValidationFinding(
                                code="ADJACENT_TRACK_CAUTION_REQUIRED",
                                severity=ValidationSeverity.INFO,
                                category=ValidationCategory.TRACK,
                                message=res.message,
                                task_id=st.task_id,
                                section_id=sec_id,
                                train_movement_id=tp.train_id,
                                evidence=res.evidence,
                            )
                        )

    # -------------------------------------------------------------------------
    # 8. Resource Availability & Exclusivity Checks
    # -------------------------------------------------------------------------
    def _check_resources(self) -> None:
        self.checks_executed.append("RESOURCES")
        # Map tasks requiring each resource
        tasks_by_res = defaultdict(list)

        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            # Look up required resources
            res_ids = []
            if isinstance(orig, dict) and "required_resource_ids" in orig:
                res_ids.extend(orig["required_resource_ids"])
            reqs = orig.get("resource_requirements", []) if isinstance(orig, dict) else getattr(orig, "resource_requirements", [])
            for r in reqs:
                rid = r.get("resource_id") if isinstance(r, dict) else getattr(r, "resource_id", None)
                if rid and rid not in res_ids:
                    res_ids.append(rid)

            for r_id in res_ids:
                tasks_by_res[r_id].append(st)

        self.checked_resource_count = len(tasks_by_res)

        # Index resource availability
        avail_by_res = defaultdict(list)
        for a in self.snapshot.resource_availabilities:
            rid = a.get("resource_id") if isinstance(a, dict) else getattr(a, "resource_id", None)
            status = a.get("availability_status", "AVAILABLE") if isinstance(a, dict) else getattr(a, "availability_status", "AVAILABLE")
            if hasattr(status, "value"):
                status = status.value
            if status == "AVAILABLE":
                a_from = _to_utc_dt(a.get("available_from") if isinstance(a, dict) else getattr(a, "available_from"))
                a_until = _to_utc_dt(a.get("available_until") if isinstance(a, dict) else getattr(a, "available_until"))
                avail_by_res[rid].append((a_from, a_until))

        # Check each resource requirement
        for r_id, task_list in tasks_by_res.items():
            # 8.1 Resource existence
            if r_id not in self.snapshot.resources_map:
                self.findings.append(
                    ValidationFinding(
                        code="UNKNOWN_RESOURCE_REFERENCED",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.RESOURCE,
                        message=f"Tasks reference unknown resource '{r_id}'.",
                        resource_id=r_id,
                    )
                )

            # 8.2 Availability window check
            if r_id in avail_by_res:
                windows = avail_by_res[r_id]
                for st in task_list:
                    # Task work interval must be enclosed in at least one available window
                    contained = any(w_start <= st.interval.start and st.interval.end <= w_end for w_start, w_end in windows)
                    if not contained:
                        self.findings.append(
                            ValidationFinding(
                                code="RESOURCE_UNAVAILABLE",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.RESOURCE,
                                message=f"Task '{st.task_id}' scheduled outside active availability windows of resource '{r_id}'.",
                                task_id=st.task_id,
                                resource_id=r_id,
                                evidence={
                                    "task_interval": f"[{st.interval.start.isoformat()}, {st.interval.end.isoformat()})",
                                    "available_windows": [f"[{w[0].isoformat()}, {w[1].isoformat()})" for w in windows],
                                },
                            )
                        )

            # 8.3 Resource Exclusivity / Capacity Check (Sweep-line)
            res_obj = self.snapshot.resources_map.get(r_id, {})
            capacity = res_obj.get("capacity", 1) if isinstance(res_obj, dict) else getattr(res_obj, "capacity", 1)

            # Create event points: (time, +demand, task_id), (time, -demand, task_id)
            events = []
            for st in task_list:
                events.append((st.interval.start, 1, st.task_id))
                events.append((st.interval.end, -1, st.task_id))

            # Half-open: end events processed BEFORE start events at the exact same timestamp!
            events.sort(key=lambda x: (x[0], x[1]))

            curr_load = 0
            active_tasks = set()
            for t_time, delta, t_id in events:
                if delta > 0:
                    curr_load += 1
                    active_tasks.add(t_id)
                    if curr_load > capacity:
                        self.findings.append(
                            ValidationFinding(
                                code="RESOURCE_CAPACITY_CONFLICT",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.RESOURCE,
                                message=f"Resource '{r_id}' demand ({curr_load}) exceeds capacity ({capacity}) among concurrent tasks: {list(active_tasks)}.",
                                resource_id=r_id,
                                evidence={
                                    "capacity": capacity,
                                    "current_demand": curr_load,
                                    "active_tasks": list(active_tasks),
                                    "timestamp": t_time.isoformat(),
                                },
                            )
                        )
                else:
                    curr_load -= 1
                    active_tasks.discard(t_id)

    # -------------------------------------------------------------------------
    # 9. Dependency Precedence Checks
    # -------------------------------------------------------------------------
    def _check_dependencies(self) -> None:
        self.checks_executed.append("DEPENDENCIES")
        sched_map = {st.task_id: st for st in self.schedule.scheduled_tasks}

        for dep in self.snapshot.dependencies:
            p_id = dep.get("predecessor_task_id") if isinstance(dep, dict) else getattr(dep, "predecessor_task_id")
            s_id = dep.get("successor_task_id") if isinstance(dep, dict) else getattr(dep, "successor_task_id")
            min_int = dep.get("min_interval_minutes", 0) if isinstance(dep, dict) else getattr(dep, "min_interval_minutes", 0)

            # If successor is scheduled, predecessor MUST be scheduled
            if s_id in sched_map:
                if p_id not in sched_map:
                    self.findings.append(
                        ValidationFinding(
                            code="DEPENDENCY_PREDECESSOR_NOT_SCHEDULED",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.DEPENDENCY,
                            message=f"Successor task '{s_id}' scheduled, but required predecessor '{p_id}' was not scheduled.",
                            task_id=s_id,
                            evidence={"predecessor_task_id": p_id},
                        )
                    )
                else:
                    p_task = sched_map[p_id]
                    s_task = sched_map[s_id]
                    req_start = p_task.interval.end + timedelta(minutes=min_int)

                    if s_task.interval.start < req_start:
                        self.findings.append(
                            ValidationFinding(
                                code="DEPENDENCY_TIMING_VIOLATION",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.DEPENDENCY,
                                message=f"Finish-to-Start timing violated: successor '{s_id}' starts at {s_task.interval.start.isoformat()} before predecessor '{p_id}' finishes plus buffer ({req_start.isoformat()}).",
                                task_id=s_id,
                                evidence={
                                    "predecessor_task_id": p_id,
                                    "predecessor_end": p_task.interval.end.isoformat(),
                                    "successor_start": s_task.interval.start.isoformat(),
                                    "required_buffer_minutes": min_int,
                                },
                            )
                        )

    # -------------------------------------------------------------------------
    # 10. Mandatory Task Checks
    # -------------------------------------------------------------------------
    def _check_mandatory_tasks(self) -> None:
        self.checks_executed.append("MANDATORY_TASKS")
        scheduled_ids = {st.task_id for st in self.schedule.scheduled_tasks}
        unscheduled_ids = {ut.task_id for ut in self.schedule.unscheduled_tasks}

        for task in self.snapshot.tasks:
            t_id = task.get("task_id") if isinstance(task, dict) else getattr(task, "task_id")
            mandatory = task.get("mandatory", False) if isinstance(task, dict) else getattr(task, "mandatory", False)

            if mandatory:
                if t_id not in scheduled_ids:
                    # Must be explicitly accounted for in unscheduled results with reason code
                    if t_id not in unscheduled_ids:
                        self.findings.append(
                            ValidationFinding(
                                code="MANDATORY_TASK_SILENTLY_DROPPED",
                                severity=ValidationSeverity.ERROR,
                                category=ValidationCategory.MANDATORY,
                                message=f"Mandatory task '{t_id}' neither scheduled nor accounted for in unscheduled results.",
                                task_id=t_id,
                            )
                        )
                    else:
                        # Accounted for with reason code: issue WARNING for operational awareness
                        self.findings.append(
                            ValidationFinding(
                                code="MANDATORY_TASK_UNSCHEDULED",
                                severity=ValidationSeverity.WARNING,
                                category=ValidationCategory.MANDATORY,
                                message=f"Mandatory task '{t_id}' could not be placed due to physical/objective constraints.",
                                task_id=t_id,
                            )
                        )

    # -------------------------------------------------------------------------
    # 11. Domain & Railway Rule Checks
    # -------------------------------------------------------------------------
    def _check_domain_rules(self) -> None:
        self.checks_executed.append("DOMAIN_RULES")
        for st in self.schedule.scheduled_tasks:
            orig = self.snapshot.tasks_map.get(st.task_id, {})
            req_power = orig.get("requires_power_block", False) if isinstance(orig, dict) else getattr(orig, "requires_power_block", False)
            sec_id = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)

            if req_power and sec_id:
                sec_obj = self.snapshot.sections_map.get(sec_id, {})
                electrified = sec_obj.get("electrified", True) if isinstance(sec_obj, dict) else getattr(sec_obj, "electrified", True)

                if not electrified:
                    self.findings.append(
                        ValidationFinding(
                            code="POWER_BLOCK_ON_UNELECTRIFIED_TRACK",
                            severity=ValidationSeverity.ERROR,
                            category=ValidationCategory.RULE,
                            message=f"Task '{st.task_id}' requires traction power block, but section '{sec_id}' is not electrified.",
                            task_id=st.task_id,
                            section_id=sec_id,
                            rule_reference="ACT-1989-S15",
                        )
                    )

    # -------------------------------------------------------------------------
    # 12. Solver Output Sanity Checks
    # -------------------------------------------------------------------------
    def _check_solver_output_sanity(self) -> None:
        self.checks_executed.append("SOLVER_OUTPUT")
        status = self.schedule.status

        # UNKNOWN or INFEASIBLE solver results must produce ERROR
        if status == SchedulerStatus.UNKNOWN:
            self.findings.append(
                ValidationFinding(
                    code="SOLVER_STATUS_UNKNOWN",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.SOLVER_OUTPUT,
                    message="Schedule produced by solver has status UNKNOWN (execution timed out or terminated abnormally).",
                )
            )
        elif status == SchedulerStatus.INFEASIBLE:
            self.findings.append(
                ValidationFinding(
                    code="SOLVER_STATUS_INFEASIBLE",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.SOLVER_OUTPUT,
                    message="Solver mathematically proved scenario INFEASIBLE under hard constraints.",
                )
            )
        elif status == SchedulerStatus.INVALID_INPUT:
            self.findings.append(
                ValidationFinding(
                    code="SOLVER_STATUS_INVALID_INPUT",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.SOLVER_OUTPUT,
                    message="Scenario rejected during pre-solve checks due to invalid input or circular dependencies.",
                )
            )
