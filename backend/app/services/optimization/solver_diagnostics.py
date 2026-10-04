"""Diagnostic telemetry models for CP-SAT optimization runs."""

from typing import Optional
from pydantic import BaseModel, Field


class SolverDiagnostics(BaseModel):
    """Detailed mathematical solver diagnostics."""

    status: str = Field(..., description="OPTIMAL, FEASIBLE, INFEASIBLE, or UNKNOWN")
    wall_time_seconds: float = Field(..., description="Elapsed wall-clock solve time")
    user_time_seconds: Optional[float] = Field(default=None, description="User CPU time")
    objective_value: Optional[float] = Field(default=None, description="Objective value found by solver")
    best_bound: Optional[float] = Field(default=None, description="Proved mathematical objective bound")
    optimality_gap: Optional[float] = Field(default=None, description="Absolute gap between objective and bound")
    optimality_gap_percentage: Optional[float] = Field(default=None, description="Percentage gap (0.0% for proven OPTIMAL)")
    num_booleans: int = Field(default=0, description="Total Boolean variables in model")
    num_integers: int = Field(default=0, description="Total Integer variables in model")
    num_constraints: int = Field(default=0, description="Total constraints posted in model")
    num_intervals: int = Field(default=0, description="Total interval variables in model")
    num_workers: int = Field(default=1, description="Worker threads used")
    random_seed: int = Field(default=0, description="Seed used for search")
    model_version: str = Field(default="1.0.0", description="Mathematical model formulation version")
    solver_version: str = Field(default="1.0.0", description="Solver engine wrapper version")
    solver_mode: str = Field(default="TRACK_AWARE_CONSERVATIVE", description="Spatial scheduling mode")
