"""High-level Optimization Planning Service.

Coordinates snapshot acquisition, CP-SAT mathematical model construction,
and bounded deterministic optimization execution.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.scheduling import ScheduleResult
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.cp_sat_solver import CPSATSolver


class OptimizationPlanningService:
    """Manages CP-SAT mathematical optimization runs on planning scenarios."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scenario_service = PlanningScenarioService(session)

    async def get_snapshot(self, scenario_id: str) -> Optional[PlanningSnapshot]:
        """Assemble an immutable planning snapshot for the given scenario."""
        bundle = await self.scenario_service.get_planning_bundle(scenario_id)
        if not bundle:
            return None
        return PlanningSnapshot.from_bundle(bundle)

    async def run_optimizer(
        self,
        scenario_id: str,
        config: Optional[OptimizationConfig] = None,
        validate_after_solve: bool = True,
    ) -> Optional[ScheduleResult]:
        """Execute CP-SAT mathematical optimization on the scenario snapshot, optionally running independent post-solve validation."""
        snapshot = await self.get_snapshot(scenario_id)
        if not snapshot:
            return None

        solver = CPSATSolver(config=config)
        result = solver.solve(snapshot, config=config)

        if validate_after_solve:
            from backend.app.services.validation import validate_schedule
            validation_res = validate_schedule(snapshot, result)
            result.validation = validation_res.model_dump()

        return result
