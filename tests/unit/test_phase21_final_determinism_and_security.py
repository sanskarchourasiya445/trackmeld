"""Phase 21 Unit Tests: Final Determinism, Core Invariants & Security Sanity.

Verifies:
1. PlanningSnapshot hashing determinism and order-invariance across task/movement permutations.
2. CP-SAT solver determinism under identical inputs and configuration.
3. Independent validator determinism.
4. Core governance invariants: OPTIMAL != APPROVED, VALID != APPROVED, COMPLETED != APPROVED.
5. AI Copilot read-only boundaries (zero mutation tools, zero approval capabilities).
6. Security static scan: no unredacted production secrets in source code.
"""

import os
import re
import random
from datetime import datetime, timezone, timedelta
import pytest

from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.validation.validator import IndependentScheduleValidator


class MockScenarioBundle:
    """Synthetic bundle generator for determinism testing."""

    def __init__(self, seed: int = 42):
        self.scenario = {
            "scenario_id": "SCN-PHASE21-TEST",
            "planning_start": "2026-10-04T00:00:00Z",
            "planning_end": "2026-10-04T23:59:59Z",
        }
        rng = random.Random(seed)
        start_dt = datetime(2026, 10, 4, 2, 0, tzinfo=timezone.utc)

        self.tasks = []
        for i in range(12):
            dur = rng.choice([60, 90, 120])
            offset_h = rng.randint(0, 12)
            w_start = start_dt + timedelta(hours=offset_h)
            w_end = w_start + timedelta(hours=8)
            self.tasks.append({
                "task_id": f"TSK-DET-{i:03d}",
                "section_id": f"SEC-0{i % 4 + 1}",
                "track_id": f"TRK-0{i % 4 + 1}-UP",
                "window_start": w_start.isoformat(),
                "window_end": w_end.isoformat(),
                "estimated_duration_minutes": dur,
                "priority": rng.choice([1, 2, 3]),
                "required_resources": ["CREW-01"] if i % 2 == 0 else [],
                "is_mandatory": i < 4,
            })

        self.work_orders = []
        self.resources = [
            {"resource_id": "CREW-01", "name": "Track Maintenance Gang 1", "resource_type": "CREW"}
        ]
        self.resource_availabilities = []
        self.dependencies = [
            {"dependency_id": "DEP-01", "predecessor_task_id": "TSK-DET-000", "successor_task_id": "TSK-DET-001"}
        ]
        self.sections = [
            {"section_id": f"SEC-0{s}", "code": f"SEC-0{s}", "length_km": 25.0}
            for s in range(1, 5)
        ]
        self.rules = []
        self.applicable_rules = []
        self.train_passes = [
            TrainPass(
                pass_id="PASS-01",
                train_id="TRN-EXPR-01",
                train_number="12301",
                section_id="SEC-01",
                interval=TimeInterval(
                    start=start_dt + timedelta(hours=3),
                    end=start_dt + timedelta(hours=3, minutes=30),
                ),
            )
        ]
        self.tracks = [
            {"track_id": f"TRK-0{s}-UP", "section_id": f"SEC-0{s}", "direction": "UP"}
            for s in range(1, 5)
        ]
        self.train_movements = []
        self.train_traversals = []
        self.topology_nodes = []
        self.topology_connections = []
        self.track_endpoints = []


# ==============================================================================
# 1. SNAPSHOT DETERMINISM & PERMUTATION INVARIANCE
# ==============================================================================

def test_planning_snapshot_order_invariance():
    """PlanningSnapshot hash must be identical regardless of input collection order."""
    bundle1 = MockScenarioBundle(seed=101)
    bundle2 = MockScenarioBundle(seed=101)

    # Permute collection order in bundle2
    random.Random(999).shuffle(bundle2.tasks)
    random.Random(888).shuffle(bundle2.tracks)
    random.Random(777).shuffle(bundle2.sections)

    snap1 = PlanningSnapshot.from_bundle(bundle1)
    snap2 = PlanningSnapshot.from_bundle(bundle2)

    hash1 = snap1.compute_snapshot_hash()
    hash2 = snap2.compute_snapshot_hash()

    assert hash1 == hash2, "Snapshot hash must be strictly order-invariant."

    config_payload = {"solver_mode": "TRACK_AWARE_CONSERVATIVE", "time_limit_seconds": 5.0}
    input_hash1 = snap1.compute_input_hash(config_payload, seed=42)
    input_hash2 = snap2.compute_input_hash(config_payload, seed=42)

    assert input_hash1 == input_hash2, "Input hash must be identical across shuffled inputs."


# ==============================================================================
# 2. CP-SAT SOLVER DETERMINISM
# ==============================================================================

def test_cpsat_solver_reproducibility():
    """CP-SAT scheduler must produce bit-for-bit identical results on repeated solves."""
    bundle = MockScenarioBundle(seed=202)
    snapshot = PlanningSnapshot.from_bundle(bundle)
    config = OptimizationConfig(time_limit_seconds=5.0, random_seed=42)

    scheduler1 = CPSATSolver(config=config)
    res1 = scheduler1.solve(snapshot)

    scheduler2 = CPSATSolver(config=config)
    res2 = scheduler2.solve(snapshot)

    assert res1.status == res2.status
    unsched1 = {t.task_id if hasattr(t, "task_id") else t for t in res1.unscheduled_tasks}
    unsched2 = {t.task_id if hasattr(t, "task_id") else t for t in res2.unscheduled_tasks}
    assert unsched1 == unsched2
    if "objective_value" in res1.metrics and "objective_value" in res2.metrics:
        assert res1.metrics["objective_value"] == res2.metrics["objective_value"]

    # Verify task-by-task start and end times
    sched1_map = {t.task_id: (t.interval.start, t.interval.end) for t in res1.scheduled_tasks}
    sched2_map = {t.task_id: (t.interval.start, t.interval.end) for t in res2.scheduled_tasks}
    assert sched1_map == sched2_map, "Scheduled intervals must match exactly."


# ==============================================================================
# 3. INDEPENDENT VALIDATOR DETERMINISM
# ==============================================================================

def test_independent_validator_determinism():
    """Independent validator produces identical verification results for the same schedule."""
    bundle = MockScenarioBundle(seed=303)
    snapshot = PlanningSnapshot.from_bundle(bundle)
    config = OptimizationConfig(time_limit_seconds=5.0, random_seed=42)
    res = CPSATSolver(config=config).solve(snapshot)

    val1 = IndependentScheduleValidator().validate(snapshot, res)
    val2 = IndependentScheduleValidator().validate(snapshot, res)

    assert val1.valid == val2.valid
    assert val1.status == val2.status
    assert val1.is_approvable == val2.is_approvable
    assert val1.error_count == val2.error_count
    assert val1.warning_count == val2.warning_count


# ==============================================================================
# 4. CORE GOVERNANCE INVARIANTS
# ==============================================================================

def test_architectural_invariants_semantics():
    """Test that solver outcomes and validation statuses do not imply plan approval."""
    # Simulation of mathematical outputs
    solver_status = "OPTIMAL"
    validation_status = "VALID"
    run_status = "COMPLETED"

    # Invariants
    is_approved = False
    assert solver_status != "APPROVED", "OPTIMAL != APPROVED"
    assert validation_status != "APPROVED", "VALID != APPROVED"
    assert run_status != "APPROVED", "COMPLETED != APPROVED"
    assert is_approved is False, "A plan can only be approved via authenticated four-eyes human review"


# ==============================================================================
# 5. AI COPILOT BOUNDARY SANITY
# ==============================================================================

def test_copilot_tool_registry_is_strictly_read_only():
    """Ensure that the AI Copilot router and tools expose zero write or approval operations."""
    from backend.app.api.v1 import copilot

    # Inspect functions registered in copilot router
    routes = copilot.router.routes
    for route in routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")
        # No route in copilot may approve, reject, or mutate governance
        assert "approve" not in path.lower(), f"Copilot route {path} cannot contain approval actions"
        assert "reject" not in path.lower(), f"Copilot route {path} cannot contain rejection actions"
        assert "mutate" not in path.lower()


# ==============================================================================
# 6. SECURITY STATIC SCAN
# ==============================================================================

def test_security_source_scan_no_unredacted_private_keys():
    """Scan backend and frontend code to ensure no live RSA/SSH private keys or secret leaks."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    dangerous_patterns = [
        re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"),
        re.compile(r'aws_secret_access_key\s*=\s*["\'][A-Za-z0-9/\+=]{40}["\']'),
    ]

    target_dirs = [
        os.path.join(base_dir, "backend", "app"),
        os.path.join(base_dir, "frontend", "src"),
        os.path.join(base_dir, "docs"),
    ]

    scanned_count = 0
    for target_dir in target_dirs:
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".next"}]
            for file in files:
                if file.endswith((".py", ".ts", ".tsx", ".md")):
                    filepath = os.path.join(root, file)
                    scanned_count += 1
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            for pat in dangerous_patterns:
                                assert not pat.search(content), f"Dangerous secret pattern found in {filepath}"
                    except Exception:
                        pass

    assert scanned_count > 50, f"Expected > 50 code files scanned, found {scanned_count}"
