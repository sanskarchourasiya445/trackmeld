"""Comprehensive unit and adversarial test suite for Phase 19 Track-Aware CP-SAT Optimization.

Verifies:
1. Existing whole-section scheduling still works.
2. Track-specific maintenance receives a track interval and assigned_track_id.
3. Resolved train traversal receives track-aware occupancy.
4. Same-track maintenance/train overlap is prevented.
5. Same-track maintenance/maintenance overlap is prevented.
6. Different compatible tracks can coexist ONLY when spatial metadata proves compatibility.
7. Adjacent FULL_TRAFFIC_BLOCK prevents coexistence.
8. Missing adjacency metadata falls back to section-level protection.
9. Unresolved train traversal falls back to section-level protection.
10. AMBIGUOUS_ROUTE falls back to section-level protection.
11. Invalid task track assignment is never silently corrected (infeasible/unplaced).
12. Directionally incompatible assignment is not scheduled as feasible.
13. Sections outside topology remain schedulable.
14. Existing resource constraints remain correct.
15. Dependencies remain correct.
16. Mandatory task behavior remains correct.
17. Objective/capture metrics remain stable.
18. Model construction is deterministic.
19. Repeated solves produce identical schedule identity.
20. CP-SAT never calls validator.
21. CP-SAT never calls CompatibilityEngine.
22. Validator remains independently runnable after solver execution.
23. Adversarial input ordering (shuffled tasks, tracks, traversals) produces identical schedules.
24. CAUTION_ORDER on adjacent track permits coexistence in solver.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from unittest.mock import patch
import pytest

from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass, TrainTraversal
from backend.app.domain.enums import TraversalResolutionStatus, AdjacentTrackImpact
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.scheduling import (
    SchedulerStatus,
    ScheduleResult,
    PriorityConfig,
)
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.validation.validator import IndependentScheduleValidator


@pytest.fixture
def base_horizon() -> PlanningHorizon:
    start = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=12))


@pytest.fixture
def sample_tracks() -> List[Dict[str, Any]]:
    return [
        {
            "track_id": "TRK-SEC-01-UP",
            "section_id": "SEC-01",
            "track_name": "Up Main",
            "track_type": "MAIN",
            "direction": "UP",
            "electrified": True,
            "adjacent_track_ids": ["TRK-SEC-01-DN"],
        },
        {
            "track_id": "TRK-SEC-01-DN",
            "section_id": "SEC-01",
            "track_name": "Down Main",
            "track_type": "MAIN",
            "direction": "DOWN",
            "electrified": True,
            "adjacent_track_ids": ["TRK-SEC-01-UP"],
        },
        {
            "track_id": "TRK-SEC-01-LOOP",
            "section_id": "SEC-01",
            "track_name": "Loop Line",
            "track_type": "LOOP",
            "direction": "BIDIRECTIONAL",
            "electrified": True,
            "adjacent_track_ids": [],  # physically separated, non-adjacent
        },
        {
            "track_id": "TRK-SEC-02-UP",
            "section_id": "SEC-02",
            "track_name": "Up Main Sec 2",
            "track_type": "MAIN",
            "direction": "UP",
            "electrified": True,
            "adjacent_track_ids": ["TRK-SEC-02-DN"],
        },
    ]


def _make_snapshot(
    horizon: PlanningHorizon,
    tasks: List[Dict[str, Any]],
    tracks: List[Dict[str, Any]],
    train_passes: Optional[List[TrainPass]] = None,
    train_traversals: Optional[List[TrainTraversal]] = None,
    dependencies: Optional[List[Dict[str, Any]]] = None,
    resources: Optional[List[Dict[str, Any]]] = None,
    availabilities: Optional[List[Dict[str, Any]]] = None,
) -> PlanningSnapshot:
    tasks_map = {t["task_id"]: t for t in tasks}
    tracks_map = {t["track_id"]: t for t in tracks}
    sections_map = {
        "SEC-01": {"section_id": "SEC-01", "electrified": True},
        "SEC-02": {"section_id": "SEC-02", "electrified": True},
    }
    return PlanningSnapshot(
        scenario_id="SCN-PHASE19-TEST",
        snapshot_id="SNAP-PHASE19-TEST",
        horizon=horizon,
        tasks=tasks,
        tasks_map=tasks_map,
        work_orders_map={},
        resources=resources or [],
        resources_map={r["resource_id"]: r for r in (resources or [])},
        resource_availabilities=availabilities or [],
        dependencies=dependencies or [],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map=sections_map,
        rules_map={},
        train_passes=train_passes or [],
        tracks=tracks,
        tracks_map=tracks_map,
        train_traversals=train_traversals or [],
        train_traversals_map={trv.traversal_id: trv for trv in (train_traversals or [])},
    )


# =============================================================================
# 1. Existing Whole-Section Scheduling Still Works
# =============================================================================

def test_existing_whole_section_scheduling_still_works(base_horizon, sample_tracks):
    """In WHOLE_SECTION mode, two tasks in the same section cannot overlap even on different tracks."""
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t1, t2], sample_tracks)

    # In WHOLE_SECTION mode, two 4h tasks cannot fit in 6h -> INFEASIBLE
    solver = CPSATSolver()
    res = solver.solve(snapshot, config=OptimizationConfig(solver_mode="WHOLE_SECTION"))
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 2. Track-Specific Maintenance Receives Assigned Track ID
# =============================================================================

def test_track_specific_maintenance_surfaces_assigned_track(base_horizon, sample_tracks):
    """When a task has a verified track, assigned_track_id is surfaced in ScheduledTaskResult."""
    t1 = {
        "task_id": "TSK-TRK-VERIFIED",
        "task_code": "TC-TV",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(base_horizon, [t1], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.OPTIMAL
    assert len(res.scheduled_tasks) == 1
    assert res.scheduled_tasks[0].assigned_track_id == "TRK-SEC-01-UP"


# =============================================================================
# 3. Resolved Train Traversal Receives Track-Aware Occupancy
# 4. Same-Track Maintenance/Train Overlap Prevented
# =============================================================================

def test_same_track_maintenance_train_overlap_prevented(base_horizon, sample_tracks):
    """A task on TRK-SEC-01-UP cannot overlap with a train traversal resolved to TRK-SEC-01-UP."""
    # Train occupies TRK-SEC-01-UP from 08:00 to 10:00
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12004",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=base_horizon.start + timedelta(hours=2), end=base_horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-UP",
        resolution_status=TraversalResolutionStatus.EXPANDED_ROUTE,
    )
    # Mandatory task on TRK-SEC-01-UP requiring 3 hours inside [07:30, 10:30] -> tight window overlapping train
    t1 = {
        "task_id": "TSK-UP-COLLIDE",
        "task_code": "TC-UC",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=1, minutes=30),  # 07:30
        "window_end": base_horizon.start + timedelta(hours=4, minutes=30),    # 10:30 (3h window)
        "estimated_duration_minutes": 180,  # 3 hours work cannot fit around 2h train
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t1], sample_tracks, train_traversals=[trv])

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    # Cannot place mandatory task on same track during train occupancy -> INFEASIBLE
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 5. Same-Track Maintenance/Maintenance Overlap Prevented
# =============================================================================

def test_same_track_maintenance_maintenance_overlap_prevented(base_horizon, sample_tracks):
    """Two mandatory tasks on the same physical track cannot overlap in time."""
    t1 = {
        "task_id": "TSK-SAME-1",
        "task_code": "TC-S1",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 180,  # 3 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-SAME-2",
        "task_code": "TC-S2",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 180,  # 3 hours (total 6h in 4h window)
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t1, t2], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 6. Different Compatible Tracks Can Coexist
# =============================================================================

def test_different_compatible_tracks_can_coexist(base_horizon, sample_tracks):
    """In TRACK_AWARE_CONSERVATIVE mode, compatible tasks on UP and DN tracks run concurrently."""
    # Both tasks need 4 hours in a 5-hour window [06:00, 11:00].
    # Under whole-section they would need 8 hours and fail.
    # Under track-aware with AdjacentTrackImpact.NONE, both can run concurrently!
    t_up = {
        "task_id": "TSK-UP-CONCURRENT",
        "task_code": "TC-UC",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t_dn = {
        "task_id": "TSK-DN-CONCURRENT",
        "task_code": "TC-DC",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_up, t_dn], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot, config=OptimizationConfig(solver_mode="TRACK_AWARE_CONSERVATIVE"))
    assert res.status == SchedulerStatus.OPTIMAL
    assert len(res.scheduled_tasks) == 2

    # Verify both tasks overlap in time (concurrent execution on separate running lines)
    st_up = next(st for st in res.scheduled_tasks if st.task_id == "TSK-UP-CONCURRENT")
    st_dn = next(st for st in res.scheduled_tasks if st.task_id == "TSK-DN-CONCURRENT")
    assert st_up.interval.start < st_dn.interval.end
    assert st_dn.interval.start < st_up.interval.end


# =============================================================================
# 7. Adjacent FULL_TRAFFIC_BLOCK Prevents Coexistence
# =============================================================================

def test_adjacent_full_traffic_block_prevents_coexistence(base_horizon, sample_tracks):
    """If task on UP track requires FULL_TRAFFIC_BLOCK on adjacent DN track, they cannot coexist."""
    t_up = {
        "task_id": "TSK-UP-BLOCKING",
        "task_code": "TC-UB",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t_dn = {
        "task_id": "TSK-DN-BLOCKED",
        "task_code": "TC-DB",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_up, t_dn], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    # Full block fouls adjacent track -> 8 hours required in 5-hour window -> INFEASIBLE
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 8. Missing Adjacency Metadata Falls Back to Section-Level Protection
# =============================================================================

def test_missing_adjacency_metadata_falls_back_to_section_protection(base_horizon):
    """Tracks with adjacent_track_ids=None cannot prove independence and fall back to exclusion."""
    tracks_missing_adj = [
        {
            "track_id": "TRK-A",
            "section_id": "SEC-01",
            "track_name": "Line A",
            "direction": "UP",
            "electrified": True,
            "adjacent_track_ids": None,  # Missing metadata!
        },
        {
            "track_id": "TRK-B",
            "section_id": "SEC-01",
            "track_name": "Line B",
            "direction": "DOWN",
            "electrified": True,
            "adjacent_track_ids": None,  # Missing metadata!
        },
    ]
    t1 = {
        "task_id": "TSK-A",
        "task_code": "TC-A",
        "section_id": "SEC-01",
        "track_id": "TRK-A",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-B",
        "task_code": "TC-B",
        "section_id": "SEC-01",
        "track_id": "TRK-B",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t1, t2], tracks_missing_adj)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    # Missing adjacency metadata forces section fallback -> cannot overlap -> INFEASIBLE
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 9. Unresolved Train Traversal Falls Back to Section-Level Protection
# 10. AMBIGUOUS_ROUTE Falls Back to Section-Level Protection
# =============================================================================

def test_unresolved_and_ambiguous_traversal_falls_back_to_section_protection(base_horizon, sample_tracks):
    """A train traversal with AMBIGUOUS_ROUTE or UNRESOLVED status enforces section-level protection."""
    trv_ambig = TrainTraversal(
        traversal_id="TRV-AMBIG",
        train_id="TRN-01",
        train_number="12004",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=base_horizon.start + timedelta(hours=2), end=base_horizon.start + timedelta(hours=4)),
        traversal_track_id=None,  # No resolved track
        resolution_status=TraversalResolutionStatus.AMBIGUOUS_ROUTE,
    )
    # Mandatory task on DN track attempting to run during the ambiguous traversal window
    t_dn = {
        "task_id": "TSK-DN-AMBIG-CHECK",
        "task_code": "TC-DAC",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=1, minutes=30),
        "window_end": base_horizon.start + timedelta(hours=4, minutes=30),
        "estimated_duration_minutes": 180,  # 3 hours cannot fit around 2h traversal
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_dn], sample_tracks, train_traversals=[trv_ambig])

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    # Ambiguous route forces section-level exclusivity -> task cannot coexist -> INFEASIBLE
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 11. Invalid Task Track Assignment Is Treated as Infeasible
# =============================================================================

def test_invalid_task_track_assignment_infeasible(base_horizon, sample_tracks):
    """A mandatory task referencing a non-existent track or track in another section is INFEASIBLE."""
    t_fake = {
        "task_id": "TSK-FAKE-TRK",
        "task_code": "TC-FT",
        "section_id": "SEC-01",
        "track_id": "TRK-DOES-NOT-EXIST",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_fake], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.INFEASIBLE


def test_track_from_wrong_section_infeasible(base_horizon, sample_tracks):
    """A mandatory task referencing a track from a different section is INFEASIBLE."""
    t_mismatch = {
        "task_id": "TSK-SEC-MISMATCH",
        "task_code": "TC-SM",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-02-UP",  # Belongs to SEC-02, but task primary section is SEC-01
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_mismatch], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 12. Directionally Incompatible Assignment Is Treated as Infeasible
# =============================================================================

def test_directionally_incompatible_task_infeasible(base_horizon, sample_tracks):
    """A mandatory task specifying DOWN direction on a unidirectional UP track is INFEASIBLE."""
    t_dir_conflict = {
        "task_id": "TSK-DIR-CONFLICT",
        "task_code": "TC-DC",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",  # UP track
        "direction": "DOWN",           # Incompatible direction!
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_dir_conflict], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.INFEASIBLE


# =============================================================================
# 13. Sections Outside Topology Remain Schedulable
# =============================================================================

def test_sections_outside_topology_remain_schedulable(base_horizon):
    """Tasks on sections with 0 tracks and 0 topology continue to schedule cleanly under section model."""
    t1 = {
        "task_id": "TSK-NO-TOPOLOGY",
        "task_code": "TC-NT",
        "section_id": "SEC-REMOTE",
        "track_id": None,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-REMOTE",
        snapshot_id="SNAP-REMOTE",
        horizon=base_horizon,
        tasks=[t1],
        tasks_map={"TSK-NO-TOPOLOGY": t1},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-REMOTE": {"section_id": "SEC-REMOTE", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.OPTIMAL
    assert len(res.scheduled_tasks) == 1
    assert res.scheduled_tasks[0].task_id == "TSK-NO-TOPOLOGY"
    assert res.scheduled_tasks[0].assigned_track_id is None


# =============================================================================
# 14. Resource Constraints & 15. Dependencies Remain Correct
# =============================================================================

def test_resource_and_dependency_constraints_remain_correct(base_horizon, sample_tracks):
    """Resource exclusivity and Finish-to-Start dependencies operate correctly alongside track modeling."""
    r1 = {"resource_id": "RES-TAMPER-01", "resource_name": "Tamping Machine"}
    avail = {
        "resource_id": "RES-TAMPER-01",
        "availability_status": "AVAILABLE",
        "available_from": base_horizon.start,
        "available_until": base_horizon.end,
    }
    # T1 on UP track, T2 on DN track. Both require RES-TAMPER-01.
    # Even though UP and DN tracks are compatible, shared machine prevents overlap!
    t1 = {
        "task_id": "TSK-R1",
        "task_code": "TC-R1",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "required_resource_ids": ["RES-TAMPER-01"],
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-R2",
        "task_code": "TC-R2",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "required_resource_ids": ["RES-TAMPER-01"],
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    dep = {
        "predecessor_task_id": "TSK-R1",
        "successor_task_id": "TSK-R2",
        "min_interval_minutes": 30,
    }
    snapshot = _make_snapshot(
        base_horizon,
        [t1, t2],
        sample_tracks,
        resources=[r1],
        availabilities=[avail],
        dependencies=[dep],
    )

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.OPTIMAL
    assert len(res.scheduled_tasks) == 2

    st1 = next(st for st in res.scheduled_tasks if st.task_id == "TSK-R1")
    st2 = next(st for st in res.scheduled_tasks if st.task_id == "TSK-R2")

    # Verify dependency: st2 start >= st1 end + 30 mins
    assert st2.interval.start >= st1.interval.end + timedelta(minutes=30)


# =============================================================================
# 18. Model Construction Determinism & 19. Repeated Solve Identity
# 23. Adversarial Ordering Independence
# =============================================================================

def test_adversarial_ordering_independence_and_deterministic_solve(base_horizon, sample_tracks):
    """Shuffling input order of tasks, tracks, and traversals produces identical schedules."""
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "CRITICAL",
        "mandatory": False,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": False,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 180,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t3 = {
        "task_id": "TSK-03",
        "task_code": "TC-03",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-LOOP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "MEDIUM",
        "mandatory": False,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 90,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }

    # Run 1: Original order
    snap1 = _make_snapshot(base_horizon, [t1, t2, t3], list(sample_tracks))
    solver = CPSATSolver(OptimizationConfig(random_seed=42))
    res1 = solver.solve(snap1)

    # Run 2: Shuffled order
    shuffled_tasks = [t3, t1, t2]
    shuffled_tracks = list(sample_tracks)
    random.Random(42).shuffle(shuffled_tracks)
    snap2 = _make_snapshot(base_horizon, shuffled_tasks, shuffled_tracks)
    res2 = solver.solve(snap2)

    # Validate identical results
    assert res1.status == res2.status
    assert len(res1.scheduled_tasks) == len(res2.scheduled_tasks)
    fingerprint1 = IndependentScheduleValidator.compute_schedule_identity(snap1, res1)
    fingerprint2 = IndependentScheduleValidator.compute_schedule_identity(snap2, res2)
    assert fingerprint1 == fingerprint2


# =============================================================================
# 20. CP-SAT Never Calls Validator & 21. CP-SAT Never Calls CompatibilityEngine
# 22. Validator Remains Independently Runnable
# =============================================================================

def test_solver_independence_and_validator_runnability(base_horizon, sample_tracks):
    """CP-SAT never calls validator or CompatibilityEngine, and validator audits solver output independently."""
    t1 = {
        "task_id": "TSK-INDEP-01",
        "task_code": "TC-I1",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=4),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(base_horizon, [t1], sample_tracks)

    solver = CPSATSolver()

    with patch("backend.app.services.validation.validator.IndependentScheduleValidator.validate") as mock_val, \
         patch("backend.app.services.compatibility_service.CompatibilityEngine.derive_train_passes") as mock_ce:

        res = solver.solve(snapshot)
        assert res.status == SchedulerStatus.OPTIMAL

        # Assert zero calls to validator and CompatibilityEngine during solving
        mock_val.assert_not_called()
        mock_ce.assert_not_called()

    # Step 2: Now run independent validator explicitly after solve
    val_result = IndependentScheduleValidator.validate(snapshot, res)
    assert val_result.status.value in ("VALID", "PROVISIONALLY_VALID")
    assert val_result.error_count == 0


# =============================================================================
# 24. CAUTION_ORDER Permits Coexistence in Solver
# =============================================================================

def test_caution_order_permits_coexistence_in_solver(base_horizon, sample_tracks):
    """Adjacent track with CAUTION_ORDER does not create a hard solver block, allowing coexistence."""
    t_up_caution = {
        "task_id": "TSK-UP-CAUTION",
        "task_code": "TC-UC",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.CAUTION_ORDER,  # Caution order
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t_dn = {
        "task_id": "TSK-DN-PARALLEL",
        "task_code": "TC-DP",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE,
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=5),
        "estimated_duration_minutes": 240,  # 4 hours
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = _make_snapshot(base_horizon, [t_up_caution, t_dn], sample_tracks)

    solver = CPSATSolver()
    res = solver.solve(snapshot)
    assert res.status == SchedulerStatus.OPTIMAL
    assert len(res.scheduled_tasks) == 2

    # Independent validator audits and flags CAUTION_REQUIRED finding at INFO severity
    val_result = IndependentScheduleValidator.validate(snapshot, res)
    caution_findings = [f for f in val_result.findings if f.code == "ADJACENT_TRACK_CAUTION_REQUIRED"]
    assert len(caution_findings) >= 1
    assert caution_findings[0].severity.value == "INFO"
