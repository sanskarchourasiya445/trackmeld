"""Configuration models for the CP-SAT optimization engine."""

from typing import Optional
from pydantic import BaseModel, Field

from backend.app.domain.scheduling import PriorityConfig


class OptimizationConfig(BaseModel):
    """Configuration parameters bounding the CP-SAT solver."""

    time_limit_seconds: float = Field(
        default=30.0,
        gt=0.1,
        le=300.0,
        description="Maximum solver wall-clock execution time in seconds"
    )
    num_search_workers: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Number of parallel search workers. 1 enforces strict deterministic repeatability."
    )
    random_seed: int = Field(
        default=0,
        ge=0,
        description="Deterministic pseudorandom seed for solver restarts"
    )
    log_search_progress: bool = Field(
        default=False,
        description="Whether CP-SAT outputs verbose search log to stdout"
    )
    solver_version: str = Field(
        default="1.0.0",
        description="Version identifier of the solver implementation"
    )
    model_version: str = Field(
        default="1.0.0",
        description="Version identifier of the CP-SAT mathematical formulation"
    )
    priority_config: PriorityConfig = Field(
        default_factory=PriorityConfig,
        description="Configured priority scoring parameters and weights"
    )
    objective_scale: int = Field(
        default=1000,
        gt=0,
        description="Integer scaling multiplier for continuous priority scores"
    )
    duration_penalty_weight: int = Field(
        default=1,
        ge=0,
        description="Secondary penalty weight per minute of work duration for tighter packing"
    )

    model_config = {"frozen": True}
