from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import DataClass


class OperationalScenario(BaseModel):
    """Scoped operational planning scenario grouping synthetic maintenance and resource records."""
    scenario_id: str = Field(..., description="Unique scenario identifier (e.g. SCN-DEMO-WEEK-01)")
    scenario_code: str = Field(..., description="Short business key for the scenario")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="Scenario planning objectives and description")
    planning_start: datetime = Field(..., description="Planning horizon start (UTC)")
    planning_end: datetime = Field(..., description="Planning horizon end (UTC)")
    generation_seed: int = Field(default=20261001, description="Deterministic pseudo-random generator seed")
    dataset_version: str = Field(default="v1.0-synthetic", description="Version of the generator used")
    classification: DataClass = Field(default=DataClass.SYNTHETIC, description="Must remain SYNTHETIC")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_horizon(self) -> "OperationalScenario":
        if self.planning_start >= self.planning_end:
            raise ValueError(
                f"planning_start ({self.planning_start}) must precede planning_end ({self.planning_end})"
            )
        return self
