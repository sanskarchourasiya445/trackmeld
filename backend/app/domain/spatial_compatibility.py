"""Domain models and deterministic evaluation for track spatial compatibility.

Part of Phase 16G-A: Deterministic Track Spatial Compatibility Foundation.

Core Principle:
Rules classify compatibility -> Optimization schedules -> Independent Validator verifies.
This module classifies spatial compatibility between two occupants based strictly on
available spatial metadata (sections, tracks, adjacency, directions, adjacent_track_impact).
It never schedules or modifies solver behavior.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field

from backend.app.domain.enums import AdjacentTrackImpact


class SpatialCompatibilityStatus(str, Enum):
    """Overall deterministic status of spatial compatibility between two occupants."""
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SpatialCompatibilityReason(str, Enum):
    """Deterministic, machine-readable reason codes for spatial compatibility outcome."""
    SAME_TRACK_OVERLAP = "SAME_TRACK_OVERLAP"
    ADJACENT_TRACK_FULL_BLOCK = "ADJACENT_TRACK_FULL_BLOCK"
    WHOLE_SECTION_OCCUPANCY = "WHOLE_SECTION_OCCUPANCY"
    DIRECTION_CONFLICT = "DIRECTION_CONFLICT"
    DIFFERENT_TRACKS_INDEPENDENT = "DIFFERENT_TRACKS_INDEPENDENT"
    DIFFERENT_SECTIONS = "DIFFERENT_SECTIONS"
    NO_TEMPORAL_OVERLAP = "NO_TEMPORAL_OVERLAP"
    MISSING_TRACK_METADATA = "MISSING_TRACK_METADATA"
    MISSING_ADJACENCY_METADATA = "MISSING_ADJACENCY_METADATA"
    UNSPECIFIED_SPATIAL_RELATION = "UNSPECIFIED_SPATIAL_RELATION"
    UNKNOWN_SECTION = "UNKNOWN_SECTION"


class SpatialOccupantType(str, Enum):
    """Type of entity occupying a railway corridor resource."""
    TASK = "TASK"
    TRAIN_PASS = "TRAIN_PASS"
    TRAIN_MOVEMENT = "TRAIN_MOVEMENT"
    TRAIN_TRAVERSAL = "TRAIN_TRAVERSAL"


class SpatialOccupant(BaseModel):
    """Normalized spatial occupant representation for deterministic compatibility classification."""
    occupant_id: str = Field(..., description="Unique occupant identifier (task_id, pass_id, movement_id, traversal_id)")
    occupant_type: SpatialOccupantType = Field(..., description="Classification of the occupant")
    section_id: Optional[str] = Field(default=None, description="Block section ID if known")
    track_id: Optional[str] = Field(default=None, description="Assigned physical track ID; None means whole-section occupancy")
    start_time: datetime = Field(..., description="Start of temporal occupancy interval [start, end)")
    end_time: datetime = Field(..., description="End of temporal occupancy interval [start, end)")
    from_km: Optional[float] = Field(default=None, description="Start chainage km if known")
    to_km: Optional[float] = Field(default=None, description="End chainage km if known")
    adjacent_track_impact: Optional[Union[AdjacentTrackImpact, str]] = Field(
        default=None,
        description="For tasks: provisional adjacent-track impact classification"
    )
    direction: Optional[str] = Field(
        default=None,
        description="Direction of movement or nominal orientation: UP, DOWN, BIDIRECTIONAL"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or provenance")

    @classmethod
    def from_task(cls, task: Any, interval_override: Optional[tuple[datetime, datetime]] = None) -> "SpatialOccupant":
        """Construct a SpatialOccupant from a MaintenanceTask or task dict."""
        t_id = getattr(task, "task_id", None) or task.get("task_id")
        sec_id = getattr(task, "section_id", None) or task.get("section_id")
        trk_id = getattr(task, "track_id", None) or task.get("track_id")
        from_km = getattr(task, "from_km", None) or task.get("from_km")
        to_km = getattr(task, "to_km", None) or task.get("to_km")
        adj_impact = getattr(task, "adjacent_track_impact", None) or task.get("adjacent_track_impact")

        if interval_override:
            start_t, end_t = interval_override
        else:
            # Check scheduled/possession window
            start_val = getattr(task, "window_start", None) or task.get("window_start")
            end_val = getattr(task, "window_end", None) or task.get("window_end")
            if isinstance(start_val, str):
                start_t = datetime.fromisoformat(start_val)
            else:
                start_t = start_val
            if isinstance(end_val, str):
                end_t = datetime.fromisoformat(end_val)
            else:
                end_t = end_val

        return cls(
            occupant_id=t_id,
            occupant_type=SpatialOccupantType.TASK,
            section_id=sec_id,
            track_id=trk_id,
            start_time=start_t,
            end_time=end_t,
            from_km=from_km,
            to_km=to_km,
            adjacent_track_impact=adj_impact,
            direction=None,
        )

    @classmethod
    def from_train_pass(cls, train_pass: Any, direction: Optional[str] = None) -> "SpatialOccupant":
        """Construct a SpatialOccupant from a TrainPass."""
        p_id = getattr(train_pass, "pass_id", None) or train_pass.get("pass_id")
        sec_id = getattr(train_pass, "section_id", None) or train_pass.get("section_id")
        trk_id = getattr(train_pass, "track_id", None) or (train_pass.get("track_id") if isinstance(train_pass, dict) else None)
        
        if hasattr(train_pass, "interval") and train_pass.interval:
            entry_t = train_pass.interval.start
            exit_t = train_pass.interval.end
        else:
            entry_t = getattr(train_pass, "entry_time", None) or train_pass.get("entry_time")
            exit_t = getattr(train_pass, "exit_time", None) or train_pass.get("exit_time")

        if isinstance(entry_t, str):
            entry_t = datetime.fromisoformat(entry_t)
        if isinstance(exit_t, str):
            exit_t = datetime.fromisoformat(exit_t)

        return cls(
            occupant_id=p_id,
            occupant_type=SpatialOccupantType.TRAIN_PASS,
            section_id=sec_id,
            track_id=trk_id,
            start_time=entry_t,
            end_time=exit_t,
            direction=direction,
        )

    @classmethod
    def from_train_traversal(cls, traversal: Any, direction: Optional[str] = None) -> "SpatialOccupant":
        """Construct a SpatialOccupant from a TrainTraversal."""
        t_id = getattr(traversal, "traversal_id", None) or traversal.get("traversal_id")
        sec_id = getattr(traversal, "section_id", None) or traversal.get("section_id")
        trk_id = getattr(traversal, "traversal_track_id", None) or traversal.get("traversal_track_id")
        
        if hasattr(traversal, "interval") and traversal.interval:
            entry_t = traversal.interval.start
            exit_t = traversal.interval.end
        else:
            entry_t = getattr(traversal, "entry_time", None) or traversal.get("entry_time")
            exit_t = getattr(traversal, "exit_time", None) or traversal.get("exit_time")

        if isinstance(entry_t, str):
            entry_t = datetime.fromisoformat(entry_t)
        if isinstance(exit_t, str):
            exit_t = datetime.fromisoformat(exit_t)

        return cls(
            occupant_id=t_id,
            occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
            section_id=sec_id,
            track_id=trk_id,
            start_time=entry_t,
            end_time=exit_t,
            direction=direction,
        )


class TrackSpatialCompatibilityResult(BaseModel):
    """Outcome of deterministic track-aware spatial compatibility evaluation."""
    status: SpatialCompatibilityStatus = Field(..., description="Overall compatibility classification")
    reason: SpatialCompatibilityReason = Field(..., description="Machine-readable deterministic reason code")
    message: str = Field(..., description="Human-readable explanation of the spatial relation")
    occupant_1_id: str = Field(..., description="Identifier of the first evaluated occupant")
    occupant_2_id: str = Field(..., description="Identifier of the second evaluated occupant")
    requires_caution_order: bool = Field(default=False, description="True if simultaneous presence requires Caution Order on adjacent line")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Structured diagnostics and underlying facts")


def evaluate_spatial_compatibility(
    occupant_1: SpatialOccupant,
    occupant_2: SpatialOccupant,
    tracks_map: Dict[str, Any],
) -> TrackSpatialCompatibilityResult:
    """Evaluate deterministic spatial compatibility between two occupants.

    Rules evaluate in strict order:
    1. Temporal overlap check: disjoint intervals -> COMPATIBLE (NO_TEMPORAL_OVERLAP).
    2. Section validity check: missing section -> INSUFFICIENT_DATA (UNKNOWN_SECTION).
    3. Section identity check: different sections -> COMPATIBLE (DIFFERENT_SECTIONS).
    4. Whole-section occupancy check: track_id is NULL -> INCOMPATIBLE (WHOLE_SECTION_OCCUPANCY).
    5. Track metadata presence check: track not in tracks_map -> INSUFFICIENT_DATA (MISSING_TRACK_METADATA).
    6. Direction alignment check: mismatch with unidirectional track -> INCOMPATIBLE (DIRECTION_CONFLICT).
    7. Same-track conflict check: same track in same section -> INCOMPATIBLE (SAME_TRACK_OVERLAP).
    8. Different-track adjacency & safety check:
       - Missing adjacency metadata -> INSUFFICIENT_DATA (MISSING_ADJACENCY_METADATA).
       - Explicitly non-adjacent -> COMPATIBLE (DIFFERENT_TRACKS_INDEPENDENT).
       - Adjacent:
         - Task with null adjacent_track_impact -> INSUFFICIENT_DATA (UNSPECIFIED_SPATIAL_RELATION).
         - Task with FULL_TRAFFIC_BLOCK -> INCOMPATIBLE (ADJACENT_TRACK_FULL_BLOCK).
         - Task with CAUTION_ORDER -> COMPATIBLE (DIFFERENT_TRACKS_INDEPENDENT, requires_caution_order=True).
         - Otherwise (NONE or trains on adjacent lines) -> COMPATIBLE (DIFFERENT_TRACKS_INDEPENDENT, requires_caution_order=False).
    """
    occ1_id = occupant_1.occupant_id
    occ2_id = occupant_2.occupant_id

    # 1. Temporal overlap check [start, end)
    if occupant_1.end_time <= occupant_2.start_time or occupant_2.end_time <= occupant_1.start_time:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.COMPATIBLE,
            reason=SpatialCompatibilityReason.NO_TEMPORAL_OVERLAP,
            message="Occupants do not overlap in time.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={
                "occ1_interval": (occupant_1.start_time.isoformat(), occupant_1.end_time.isoformat()),
                "occ2_interval": (occupant_2.start_time.isoformat(), occupant_2.end_time.isoformat()),
            },
        )

    # 2. Section validity check
    if not occupant_1.section_id or not occupant_2.section_id:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INSUFFICIENT_DATA,
            reason=SpatialCompatibilityReason.UNKNOWN_SECTION,
            message="One or both occupants have unspecified section_id.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={
                "occ1_section_id": occupant_1.section_id,
                "occ2_section_id": occupant_2.section_id,
            },
        )

    # 3. Section identity check
    if occupant_1.section_id != occupant_2.section_id:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.COMPATIBLE,
            reason=SpatialCompatibilityReason.DIFFERENT_SECTIONS,
            message=f"Occupants are located in different sections ({occupant_1.section_id} vs {occupant_2.section_id}).",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={
                "occ1_section_id": occupant_1.section_id,
                "occ2_section_id": occupant_2.section_id,
            },
        )

    sec_id = occupant_1.section_id

    # 4. Whole-section occupancy check
    if occupant_1.track_id is None or occupant_2.track_id is None:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INCOMPATIBLE,
            reason=SpatialCompatibilityReason.WHOLE_SECTION_OCCUPANCY,
            message="At least one occupant has no assigned track_id, requiring whole-section exclusivity.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={
                "section_id": sec_id,
                "occ1_track_id": occupant_1.track_id,
                "occ2_track_id": occupant_2.track_id,
            },
        )

    # 5. Track metadata presence check
    trk1 = tracks_map.get(occupant_1.track_id)
    if trk1 is None:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INSUFFICIENT_DATA,
            reason=SpatialCompatibilityReason.MISSING_TRACK_METADATA,
            message=f"Track metadata missing from snapshot for occupant 1 track {occupant_1.track_id}.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"missing_track_id": occupant_1.track_id},
        )

    trk2 = tracks_map.get(occupant_2.track_id)
    if trk2 is None:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INSUFFICIENT_DATA,
            reason=SpatialCompatibilityReason.MISSING_TRACK_METADATA,
            message=f"Track metadata missing from snapshot for occupant 2 track {occupant_2.track_id}.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"missing_track_id": occupant_2.track_id},
        )

    # 6. Direction alignment check
    trk1_dir = getattr(trk1, "direction", None) or (trk1.get("direction") if isinstance(trk1, dict) else None)
    trk2_dir = getattr(trk2, "direction", None) or (trk2.get("direction") if isinstance(trk2, dict) else None)

    if occupant_1.direction in ("UP", "DOWN") and trk1_dir in ("UP", "DOWN") and occupant_1.direction != trk1_dir:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INCOMPATIBLE,
            reason=SpatialCompatibilityReason.DIRECTION_CONFLICT,
            message=f"Occupant 1 direction {occupant_1.direction} conflicts with track {occupant_1.track_id} direction {trk1_dir}.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"occupant_direction": occupant_1.direction, "track_direction": trk1_dir, "track_id": occupant_1.track_id},
        )

    if occupant_2.direction in ("UP", "DOWN") and trk2_dir in ("UP", "DOWN") and occupant_2.direction != trk2_dir:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INCOMPATIBLE,
            reason=SpatialCompatibilityReason.DIRECTION_CONFLICT,
            message=f"Occupant 2 direction {occupant_2.direction} conflicts with track {occupant_2.track_id} direction {trk2_dir}.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"occupant_direction": occupant_2.direction, "track_direction": trk2_dir, "track_id": occupant_2.track_id},
        )

    # 7. Same-track conflict check
    if occupant_1.track_id == occupant_2.track_id:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INCOMPATIBLE,
            reason=SpatialCompatibilityReason.SAME_TRACK_OVERLAP,
            message=f"Both occupants occupy the same physical track {occupant_1.track_id} in section {sec_id} concurrently.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"track_id": occupant_1.track_id, "section_id": sec_id},
        )

    # 8. Different tracks in the same section
    adj1 = getattr(trk1, "adjacent_track_ids", None) if not isinstance(trk1, dict) else trk1.get("adjacent_track_ids")
    adj2 = getattr(trk2, "adjacent_track_ids", None) if not isinstance(trk2, dict) else trk2.get("adjacent_track_ids")

    if adj1 is None or adj2 is None:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.INSUFFICIENT_DATA,
            reason=SpatialCompatibilityReason.MISSING_ADJACENCY_METADATA,
            message=f"Adjacency metadata is null/unspecified for tracks {occupant_1.track_id} or {occupant_2.track_id}.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"track_1_adjacent": adj1, "track_2_adjacent": adj2},
        )

    is_adjacent = (occupant_2.track_id in adj1) or (occupant_1.track_id in adj2)

    if not is_adjacent:
        # Separate, non-adjacent running lines
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.COMPATIBLE,
            reason=SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT,
            message=f"Tracks {occupant_1.track_id} and {occupant_2.track_id} are physically separate and non-adjacent in section {sec_id}.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=False,
            evidence={"track_1": occupant_1.track_id, "track_2": occupant_2.track_id, "is_adjacent": False},
        )

    # Adjacent running lines: inspect task adjacent_track_impact
    tasks_with_impact: List[tuple[SpatialOccupant, SpatialOccupant]] = []
    if occupant_1.occupant_type == SpatialOccupantType.TASK:
        tasks_with_impact.append((occupant_1, occupant_2))
    if occupant_2.occupant_type == SpatialOccupantType.TASK:
        tasks_with_impact.append((occupant_2, occupant_1))

    for task_occ, other_occ in tasks_with_impact:
        impact = task_occ.adjacent_track_impact
        # If task is on adjacent track but impact is unspecified
        if impact is None:
            return TrackSpatialCompatibilityResult(
                status=SpatialCompatibilityStatus.INSUFFICIENT_DATA,
                reason=SpatialCompatibilityReason.UNSPECIFIED_SPATIAL_RELATION,
                message=f"Task {task_occ.occupant_id} on track {task_occ.track_id} has unspecified adjacent_track_impact.",
                occupant_1_id=occ1_id,
                occupant_2_id=occ2_id,
                requires_caution_order=False,
                evidence={"task_id": task_occ.occupant_id, "adjacent_track_impact": None},
            )

        impact_str = impact.value if hasattr(impact, "value") else str(impact)
        if impact_str == AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value:
            return TrackSpatialCompatibilityResult(
                status=SpatialCompatibilityStatus.INCOMPATIBLE,
                reason=SpatialCompatibilityReason.ADJACENT_TRACK_FULL_BLOCK,
                message=f"Task {task_occ.occupant_id} on track {task_occ.track_id} requires FULL_TRAFFIC_BLOCK on adjacent track {other_occ.track_id}.",
                occupant_1_id=occ1_id,
                occupant_2_id=occ2_id,
                requires_caution_order=False,
                evidence={
                    "task_id": task_occ.occupant_id,
                    "blocking_track_id": task_occ.track_id,
                    "affected_adjacent_track_id": other_occ.track_id,
                    "adjacent_track_impact": impact_str,
                },
            )

    # Check for caution order
    has_caution = False
    for task_occ, _ in tasks_with_impact:
        impact = task_occ.adjacent_track_impact
        impact_str = impact.value if hasattr(impact, "value") else str(impact)
        if impact_str == AdjacentTrackImpact.CAUTION_ORDER.value:
            has_caution = True
            break

    if has_caution:
        return TrackSpatialCompatibilityResult(
            status=SpatialCompatibilityStatus.COMPATIBLE,
            reason=SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT,
            message=f"Tracks {occupant_1.track_id} and {occupant_2.track_id} are adjacent. Coexistence permitted under Caution Order / speed restriction on adjacent track.",
            occupant_1_id=occ1_id,
            occupant_2_id=occ2_id,
            requires_caution_order=True,
            evidence={"track_1": occupant_1.track_id, "track_2": occupant_2.track_id, "is_adjacent": True, "caution_order_required": True},
        )

    # Either both are trains on adjacent lines, or all tasks have AdjacentTrackImpact.NONE
    return TrackSpatialCompatibilityResult(
        status=SpatialCompatibilityStatus.COMPATIBLE,
        reason=SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT,
        message=f"Tracks {occupant_1.track_id} and {occupant_2.track_id} are adjacent running lines operating independently with no fouling.",
        occupant_1_id=occ1_id,
        occupant_2_id=occ2_id,
        requires_caution_order=False,
        evidence={"track_1": occupant_1.track_id, "track_2": occupant_2.track_id, "is_adjacent": True, "caution_order_required": False},
    )
