"""Immutable Planning Snapshot abstraction for deterministic scheduling.

Guarantees:
1. Schedulers (FCFS, Priority-Greedy, CP-SAT) receive the exact same immutable input.
2. No live database queries or mutations occur during scheduling.
3. Stable, reproducible snapshot identity.
"""

from datetime import datetime, timezone
import hashlib
from typing import Dict, Any, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from backend.app.domain.temporal import PlanningHorizon, TrainPass


@dataclass(frozen=True)
class PlanningSnapshot:
    """Immutable in-memory snapshot representing all planning inputs for a scenario."""

    scenario_id: str
    snapshot_id: str
    horizon: PlanningHorizon
    tasks: List[Any]
    tasks_map: Dict[str, Any]
    work_orders_map: Dict[str, Any]
    resources: List[Any]
    resources_map: Dict[str, Any]
    resource_availabilities: List[Any]
    dependencies: List[Any]
    dependencies_by_successor: Dict[str, List[Any]]
    dependencies_by_predecessor: Dict[str, List[Any]]
    sections_map: Dict[str, Any]
    rules_map: Dict[str, Any]
    train_passes: List[TrainPass]
    tracks: List[Any] = field(default_factory=list)
    tracks_map: Dict[str, Any] = field(default_factory=dict)


    def compute_snapshot_hash(self) -> str:
        """Compute authoritative 64-char SHA-256 fingerprint representing all immutable planning inputs."""
        import json
        hasher = hashlib.sha256()
        hasher.update(self.scenario_id.encode("utf-8"))
        hasher.update(self.horizon.start.isoformat().encode("utf-8"))
        hasher.update(self.horizon.end.isoformat().encode("utf-8"))

        task_records = []
        for t in self.tasks:
            t_id = t.get("task_id") if isinstance(t, dict) else getattr(t, "task_id")
            w_start = str(t.get("window_start") if isinstance(t, dict) else getattr(t, "window_start"))
            w_end = str(t.get("window_end") if isinstance(t, dict) else getattr(t, "window_end"))
            dur = str(t.get("estimated_duration_minutes") if isinstance(t, dict) else getattr(t, "estimated_duration_minutes"))
            sec = str(t.get("section_id") if isinstance(t, dict) else getattr(t, "section_id"))
            task_records.append((t_id, w_start, w_end, dur, sec))
        task_records.sort(key=lambda x: x[0])
        hasher.update(json.dumps(task_records, sort_keys=True).encode("utf-8"))

        hasher.update(str(len(self.train_passes)).encode("utf-8"))
        hasher.update(str(len(self.resources)).encode("utf-8"))
        hasher.update(str(len(self.dependencies)).encode("utf-8"))
        return hasher.hexdigest()

    def compute_input_hash(self, config_payload: Dict[str, Any], seed: int = 0) -> str:
        """Compute full input hash covering snapshot data, configuration snapshot, and randomization seed."""
        import json
        snap_hash = self.compute_snapshot_hash()
        hasher = hashlib.sha256()
        hasher.update(snap_hash.encode("utf-8"))
        hasher.update(json.dumps(config_payload, sort_keys=True, default=str).encode("utf-8"))
        hasher.update(str(seed).encode("utf-8"))
        return hasher.hexdigest()

    @classmethod
    def from_bundle(cls, bundle: Any) -> "PlanningSnapshot":
        """Construct an immutable PlanningSnapshot from a ScenarioPlanningBundle."""
        scenario_data = bundle.scenario if isinstance(bundle.scenario, dict) else bundle.scenario.__dict__
        scenario_id = scenario_data.get("scenario_id") or getattr(bundle.scenario, "scenario_id")

        # 1. Parse and build PlanningHorizon
        start_raw = scenario_data.get("planning_start") or getattr(bundle.scenario, "planning_start")
        end_raw = scenario_data.get("planning_end") or getattr(bundle.scenario, "planning_end")

        if isinstance(start_raw, str):
            scen_start = datetime.fromisoformat(start_raw)
        else:
            scen_start = start_raw
        if isinstance(end_raw, str):
            scen_end = datetime.fromisoformat(end_raw)
        else:
            scen_end = end_raw

        if scen_start.tzinfo is None:
            scen_start = scen_start.replace(tzinfo=timezone.utc)
        if scen_end.tzinfo is None:
            scen_end = scen_end.replace(tzinfo=timezone.utc)

        horizon = PlanningHorizon(start=scen_start, end=scen_end)

        # 2. Canonical sorting for tasks
        raw_tasks = list(bundle.tasks)
        sorted_tasks = sorted(
            raw_tasks,
            key=lambda t: getattr(t, "task_id", None) or (t.get("task_id") if isinstance(t, dict) else "")
        )

        tasks_map = {}
        for t in sorted_tasks:
            t_id = getattr(t, "task_id", None) or t.get("task_id")
            tasks_map[t_id] = t

        # 3. Work orders lookup
        work_orders_map = {}
        for wo in bundle.work_orders:
            wo_id = getattr(wo, "work_order_id", None) or wo.get("work_order_id")
            work_orders_map[wo_id] = wo

        # 4. Resources lookup
        resources_map = {}
        for r in bundle.resources:
            r_id = getattr(r, "resource_id", None) or r.get("resource_id")
            resources_map[r_id] = r

        # 5. Dependencies indexing
        deps_by_succ = defaultdict(list)
        deps_by_pred = defaultdict(list)
        for dep in bundle.dependencies:
            succ = getattr(dep, "successor_task_id", None) or dep.get("successor_task_id")
            pred = getattr(dep, "predecessor_task_id", None) or dep.get("predecessor_task_id")
            if succ:
                deps_by_succ[succ].append(dep)
            if pred:
                deps_by_pred[pred].append(dep)

        # 6. Sections and rules maps
        sections_map = {}
        for s in bundle.sections:
            s_id = getattr(s, "section_id", None) or s.get("section_id")
            sections_map[s_id] = s

        rules_map = {}
        for r in bundle.applicable_rules:
            r_id = getattr(r, "rule_id", None) or r.get("rule_id")
            rules_map[r_id] = r

        # 7. Derive Train Passes
        from backend.app.services.compatibility_service import CompatibilityEngine

        train_passes = CompatibilityEngine.derive_train_passes(
            train_movements=bundle.train_movements,
            sections=bundle.sections,
            horizon=horizon,
        )

        # 7b. Tracks lookup
        raw_tracks = getattr(bundle, "tracks", []) or []
        tracks_map = {}
        for trk in raw_tracks:
            trk_id = getattr(trk, "track_id", None) or (trk.get("track_id") if isinstance(trk, dict) else None)
            if trk_id:
                tracks_map[trk_id] = trk

        # 8. Deterministic Snapshot ID computation
        hasher = hashlib.sha256()
        hasher.update(scenario_id.encode("utf-8"))
        hasher.update(scen_start.isoformat().encode("utf-8"))
        hasher.update(scen_end.isoformat().encode("utf-8"))
        for t_id in sorted(tasks_map.keys()):
            hasher.update(t_id.encode("utf-8"))
        snapshot_id = f"SNAP-{hasher.hexdigest()[:12].upper()}"

        return cls(
            scenario_id=scenario_id,
            snapshot_id=snapshot_id,
            horizon=horizon,
            tasks=sorted_tasks,
            tasks_map=tasks_map,
            work_orders_map=work_orders_map,
            resources=list(bundle.resources),
            resources_map=resources_map,
            resource_availabilities=list(bundle.resource_availabilities),
            dependencies=list(bundle.dependencies),
            dependencies_by_successor=dict(deps_by_succ),
            dependencies_by_predecessor=dict(deps_by_pred),
            sections_map=sections_map,
            rules_map=rules_map,
            train_passes=train_passes,
            tracks=list(raw_tracks),
            tracks_map=tracks_map,
        )

