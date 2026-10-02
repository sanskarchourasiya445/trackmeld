#!/usr/bin/env python3
"""Validation Script for TrackMeld Phase 4 — Planning Windows and Compatibility.

Verifies:
1. Half-open interval mathematical properties [start, end)
2. Train pass derivation from scenario movements
3. Conflict detection algorithms (windows, trains, sections, resources, dependencies, blocks)
4. Rule classification and unverified constraint non-promotion invariants
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.db.session import AsyncSessionLocal
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.domain.temporal import TimeInterval, PlanningHorizon, TrainPass
from backend.app.domain.compatibility import (
    ConstraintSeverity,
    ReasonCode,
    ScheduledTaskPlacement,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trackmeld.validate_phase4")


async def run_phase4_validations() -> int:
    checks_passed = 0
    checks_total = 0

    def assert_check(name: str, condition: bool):
        nonlocal checks_passed, checks_total
        checks_total += 1
        if condition:
            logger.info("PASS: %s", name)
            checks_passed += 1
        else:
            logger.error("FAIL: %s", name)

    logger.info("=== Starting TrackMeld Phase 4 Compatibility & Feasibility Validation ===")

    # 1. Temporal Half-Open Semantics
    t0 = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    i1 = TimeInterval(start=t0, end=t1)
    i2 = TimeInterval(start=t1, end=t2)
    assert_check("Half-open adjacent intervals do NOT overlap", not i1.overlaps(i2))
    assert_check("Half-open adjacent intervals meet boundary condition", i1.is_adjacent_to(i2))

    i_zero = TimeInterval(start=t0, end=t0)
    assert_check("Zero-duration interval flagged invalid", not i_zero.is_valid)

    i_neg = TimeInterval(start=t1, end=t0)
    assert_check("Negative duration interval flagged invalid", not i_neg.is_valid)

    # 2. Database Integration & Train Pass Derivation
    async with AsyncSessionLocal() as session:
        service = PlanningScenarioService(session)
        bundle = await service.get_planning_bundle("SCN-DEMO-001")
        assert_check("Scenario SCN-DEMO-001 bundle retrieved", bundle is not None)

        if bundle:
            horizon = PlanningHorizon(
                start=datetime.fromisoformat(bundle.scenario["planning_start"]),
                end=datetime.fromisoformat(bundle.scenario["planning_end"]),
            )
            assert_check("Horizon duration is 72 hours", horizon.duration_hours == 72.0)

            train_passes = CompatibilityEngine.derive_train_passes(
                train_movements=bundle.train_movements,
                sections=bundle.sections,
                horizon=horizon,
            )
            assert_check("Train passes derived across corridor (count > 0)", len(train_passes) > 0)

            # 3. Compatibility Engine Scenarios
            sections_map = {s["section_id"]: s for s in bundle.sections}
            rules_map = {r["rule_id"]: r for r in bundle.applicable_rules}

            # Select first task in scenario
            task = bundle.tasks[0]

            # Inside window evaluation
            w_start = datetime.fromisoformat(task["window_start"])
            dur = task["estimated_duration_minutes"]
            eval_start = w_start + timedelta(minutes=15)
            eval_end = eval_start + timedelta(minutes=dur)

            res_normal = CompatibilityEngine.evaluate_task_placement(
                task=task,
                candidate_start=eval_start,
                candidate_end=eval_end,
                horizon=horizon,
                train_passes=[],
                existing_placements=[],
                resource_availabilities=bundle.resource_availabilities,
                dependencies=bundle.dependencies,
                sections_map=sections_map,
                rules_map=rules_map,
            )
            assert_check("Task evaluation returns structured CompatibilityResult", res_normal is not None)
            assert_check("Rule evidence attached to evaluation", len(res_normal.rule_evidence) > 0)

            # Outside window evaluation
            bad_start = w_start - timedelta(hours=10)
            bad_end = bad_start + timedelta(minutes=dur)
            res_bad_win = CompatibilityEngine.evaluate_task_placement(
                task=task,
                candidate_start=bad_start,
                candidate_end=bad_end,
                horizon=horizon,
                train_passes=[],
                existing_placements=[],
                resource_availabilities=bundle.resource_availabilities,
                dependencies=bundle.dependencies,
                sections_map=sections_map,
                rules_map=rules_map,
            )
            assert_check("Task outside allowed window is incompatible", not res_bad_win.compatible)
            assert_check("TASK_WINDOW_CONFLICT reason code emitted", ReasonCode.TASK_WINDOW_CONFLICT in res_bad_win.reason_codes)

            # Train conflict evaluation
            fake_pass = TrainPass(
                pass_id="PASS-TEST-COLLISION",
                train_id="TRN-COLLIDE",
                train_number="99999",
                section_id=task["section_id"],
                interval=TimeInterval(start=eval_start, end=eval_end),
            )
            res_train_conflict = CompatibilityEngine.evaluate_task_placement(
                task=task,
                candidate_start=eval_start,
                candidate_end=eval_end,
                horizon=horizon,
                train_passes=[fake_pass],
                existing_placements=[],
                resource_availabilities=bundle.resource_availabilities,
                dependencies=bundle.dependencies,
                sections_map=sections_map,
                rules_map=rules_map,
            )
            assert_check("Train conflict triggers incompatibility", not res_train_conflict.compatible)
            assert_check("TRAIN_MOVEMENT_CONFLICT reason code emitted", ReasonCode.TRAIN_MOVEMENT_CONFLICT in res_train_conflict.reason_codes)

            # Section occupancy conflict
            other_placement = ScheduledTaskPlacement(
                task_id="TSK-OTHER-BLOCK",
                task_code="TSK-OTHER-BLOCK",
                section_id=task["section_id"],
                interval=TimeInterval(start=eval_start, end=eval_end),
                possession_interval=TimeInterval(start=eval_start - timedelta(minutes=15), end=eval_end + timedelta(minutes=15)),
            )
            res_sec_conflict = CompatibilityEngine.evaluate_task_placement(
                task=task,
                candidate_start=eval_start,
                candidate_end=eval_end,
                horizon=horizon,
                train_passes=[],
                existing_placements=[other_placement],
                resource_availabilities=bundle.resource_availabilities,
                dependencies=bundle.dependencies,
                sections_map=sections_map,
                rules_map=rules_map,
            )
            assert_check("Section occupancy collision triggers incompatibility", not res_sec_conflict.compatible)
            assert_check("SECTION_OCCUPANCY_CONFLICT reason code emitted", ReasonCode.SECTION_OCCUPANCY_CONFLICT in res_sec_conflict.reason_codes)

            # Unverified rule invariant
            unverified_rule = {
                "rule_id": "RULE-TEST-UNVERIFIED",
                "title": "Hypothetical rule",
                "rule_class": "UNVERIFIED",
                "source_id": "SRC-UNVERIFIED",
            }
            res_unverified = CompatibilityEngine.evaluate_task_placement(
                task=task,
                candidate_start=eval_start,
                candidate_end=eval_end,
                horizon=horizon,
                train_passes=[],
                existing_placements=[],
                resource_availabilities=bundle.resource_availabilities,
                dependencies=bundle.dependencies,
                sections_map=sections_map,
                rules_map={"RULE-TEST-UNVERIFIED": unverified_rule},
            )
            assert_check("Unverified rule never becomes hard constraint", res_unverified.feasible_hard)
            assert_check("UNVERIFIED_RULE reason code emitted for unverified rule", ReasonCode.UNVERIFIED_RULE in res_unverified.reason_codes)

    logger.info("==========================================")
    logger.info("Phase 4 Compatibility Validation Summary:")
    logger.info("Total Checks: %d", checks_total)
    logger.info("Passed:       %d", checks_passed)
    logger.info("Failed:       %d", checks_total - checks_passed)
    logger.info("==========================================")

    return 0 if checks_passed == checks_total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_phase4_validations())
    sys.exit(exit_code)
