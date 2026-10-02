from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.repositories.base import BaseRepository


class ScenarioRepository(BaseRepository[OperationalScenarioModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OperationalScenarioModel, session)

    async def get_by_code(self, scenario_code: str) -> Optional[OperationalScenarioModel]:
        stmt = select(OperationalScenarioModel).where(OperationalScenarioModel.scenario_code == scenario_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, scenario: OperationalScenarioModel) -> OperationalScenarioModel:
        existing = await self.get_by_id(scenario.scenario_id)
        if existing:
            existing.scenario_code = scenario.scenario_code
            existing.name = scenario.name
            existing.description = scenario.description
            existing.planning_start = scenario.planning_start
            existing.planning_end = scenario.planning_end
            existing.generation_seed = scenario.generation_seed
            existing.dataset_version = scenario.dataset_version
            existing.classification = scenario.classification
            return existing
        else:
            self.session.add(scenario)
            return scenario
