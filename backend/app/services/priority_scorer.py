"""Configurable and explainable task priority scoring service.

Guarantees:
1. Transparent component breakdown for every scored task.
2. Configurable weights explicitly treated as experimental benchmark heuristics.
3. Strict normalization [0.0, 1.0] across all active features.
4. Pure and deterministic calculation with zero data mutations.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.app.domain.scheduling import (
    PriorityConfig,
    PriorityScore,
    PriorityComponent,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.enums import TaskPriority


class PriorityScorer:
    """Calculates explainable priority scores for maintenance tasks."""

    @classmethod
    def score_task(
        cls,
        task: Any,
        snapshot: PlanningSnapshot,
        config: Optional[PriorityConfig] = None,
    ) -> PriorityScore:
        """Calculate explainable priority score and full component breakdown for a task."""
        if config is None:
            config = PriorityConfig()

        task_id = getattr(task, "task_id", None) or task.get("task_id", "UNKNOWN")
        components: Dict[str, PriorityComponent] = {}

        # ---------------------------------------------------------------------
        # 1. Mandatory Feature
        # ---------------------------------------------------------------------
        is_mandatory = getattr(task, "mandatory", False) if hasattr(task, "mandatory") else task.get("mandatory", False)
        norm_mandatory = 1.0 if is_mandatory else 0.0
        contrib_mandatory = norm_mandatory * config.mandatory_weight
        components["mandatory"] = PriorityComponent(
            feature_name="mandatory",
            raw_value=is_mandatory,
            normalized_value=norm_mandatory,
            weight=config.mandatory_weight,
            contribution=round(contrib_mandatory, 4),
            description="Statutory or regulatory mandatory maintenance requisition.",
        )

        # ---------------------------------------------------------------------
        # 2. Urgency / Priority Level Feature
        # ---------------------------------------------------------------------
        if hasattr(task, "priority"):
            prio_val = getattr(task, "priority")
        elif isinstance(task, dict) and "priority" in task:
            prio_val = task["priority"]
        else:
            prio_val = TaskPriority.MEDIUM

        if hasattr(prio_val, "value"):
            prio_val = prio_val.value
        elif isinstance(prio_val, dict):
            prio_val = prio_val.get("value", "MEDIUM")

        urgency_mapping = {
            "CRITICAL": 1.0,
            "HIGH": 0.75,
            "MEDIUM": 0.50,
            "LOW": 0.25,
        }
        norm_urgency = urgency_mapping.get(str(prio_val).upper(), 0.50)
        contrib_urgency = norm_urgency * config.urgency_weight
        components["urgency"] = PriorityComponent(
            feature_name="urgency",
            raw_value=str(prio_val),
            normalized_value=norm_urgency,
            weight=config.urgency_weight,
            contribution=round(contrib_urgency, 4),
            description="Requisition operational priority level (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25).",
        )

        # ---------------------------------------------------------------------
        # 3. Window Tightness Feature
        # ---------------------------------------------------------------------
        w_start = getattr(task, "window_start", None) or task.get("window_start")
        w_end = getattr(task, "window_end", None) or task.get("window_end")
        est_dur = getattr(task, "estimated_duration_minutes", 60) or task.get("estimated_duration_minutes", 60)
        buf_before = getattr(task, "safety_buffer_before_minutes", 10) or task.get("safety_buffer_before_minutes", 10)
        buf_after = getattr(task, "safety_buffer_after_minutes", 10) or task.get("safety_buffer_after_minutes", 10)

        if isinstance(w_start, str):
            w_start = datetime.fromisoformat(w_start)
        if isinstance(w_end, str):
            w_end = datetime.fromisoformat(w_end)

        needed_dur = est_dur + buf_before + buf_after
        if w_start and w_end and w_end > w_start:
            window_minutes = (w_end - w_start).total_seconds() / 60.0
            norm_tightness = min(1.0, max(0.0, needed_dur / window_minutes))
        else:
            norm_tightness = 1.0

        contrib_tightness = norm_tightness * config.window_tightness_weight
        components["window_tightness"] = PriorityComponent(
            feature_name="window_tightness",
            raw_value=round(norm_tightness, 4),
            normalized_value=round(norm_tightness, 4),
            weight=config.window_tightness_weight,
            contribution=round(contrib_tightness, 4),
            description="Ratio of required possession duration to allowed execution window.",
        )

        # ---------------------------------------------------------------------
        # 4. Dependency Bottleneck Feature
        # ---------------------------------------------------------------------
        successors = snapshot.dependencies_by_predecessor.get(task_id, [])
        succ_count = len(successors)
        norm_dep = min(1.0, succ_count / 3.0)  # Max out at 3 or more waiting successors
        contrib_dep = norm_dep * config.dependency_weight
        components["dependency_bottleneck"] = PriorityComponent(
            feature_name="dependency_bottleneck",
            raw_value=succ_count,
            normalized_value=round(norm_dep, 4),
            weight=config.dependency_weight,
            contribution=round(contrib_dep, 4),
            description="Normalized count of downstream successor tasks waiting on completion of this task.",
        )

        # ---------------------------------------------------------------------
        # 5. Operational Impact Feature
        # ---------------------------------------------------------------------
        req_traffic = getattr(task, "requires_traffic_block", False) if hasattr(task, "requires_traffic_block") else task.get("requires_traffic_block", False)
        req_power = getattr(task, "requires_power_block", False) if hasattr(task, "requires_power_block") else task.get("requires_power_block", False)

        if req_traffic and req_power:
            norm_impact = 1.0
            impact_desc = "Requires simultaneous traffic block and 25 kV OHE power isolation."
        elif req_traffic:
            norm_impact = 0.75
            impact_desc = "Requires traffic block on primary track section."
        elif req_power:
            norm_impact = 0.50
            impact_desc = "Requires OHE power block."
        else:
            norm_impact = 0.20
            impact_desc = "Minimal track infrastructure occupancy."

        contrib_impact = norm_impact * config.operational_impact_weight
        components["operational_impact"] = PriorityComponent(
            feature_name="operational_impact",
            raw_value={"requires_traffic_block": req_traffic, "requires_power_block": req_power},
            normalized_value=norm_impact,
            weight=config.operational_impact_weight,
            contribution=round(contrib_impact, 4),
            description=impact_desc,
        )

        # ---------------------------------------------------------------------
        # Total Score Aggregation
        # ---------------------------------------------------------------------
        total_score = sum(c.contribution for c in components.values())

        return PriorityScore(
            task_id=task_id,
            total_score=round(total_score, 4),
            components=components,
            config_id=config.config_id,
            config_version=config.version,
        )

    @classmethod
    def score_all_tasks(
        cls,
        snapshot: PlanningSnapshot,
        config: Optional[PriorityConfig] = None,
    ) -> Dict[str, PriorityScore]:
        """Score all tasks in snapshot deterministically."""
        scores: Dict[str, PriorityScore] = {}
        for task in snapshot.tasks:
            task_id = getattr(task, "task_id", None) or task.get("task_id")
            scores[task_id] = cls.score_task(task, snapshot, config)
        return scores
