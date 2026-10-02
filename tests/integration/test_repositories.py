import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.repositories import (
    StationRepository,
    SectionRepository,
    TrainRepository,
    TrainMovementRepository,
    RailwayRuleRepository,
    InfrastructureRepository,
)
from backend.app.domain.enums import DataClass, RuleClass


@pytest.mark.asyncio
async def test_station_repository(db_session: AsyncSession):
    repo = StationRepository(db_session)
    stn = await repo.get_by_code("NDLS")
    assert stn is not None
    assert stn.station_name == "New Delhi"
    assert stn.classification == DataClass.REAL
    assert stn.source_id == "SRC-TAG-2023-TBL-01"


@pytest.mark.asyncio
async def test_section_repository(db_session: AsyncSession):
    repo = SectionRepository(db_session)
    sec = await repo.get_by_code("NDLS-GZB")
    assert sec is not None
    assert sec.from_station_code == "NDLS"
    assert sec.to_station_code == "GZB"
    assert sec.length_km == 25.0
    assert sec.classification == DataClass.DERIVED


@pytest.mark.asyncio
async def test_train_repository(db_session: AsyncSession):
    repo = TrainRepository(db_session)
    train = await repo.get_by_number("12301")
    assert train is not None
    assert "Rajdhani" in train.train_name
    assert train.classification == DataClass.REAL


@pytest.mark.asyncio
async def test_movement_repository(db_session: AsyncSession):
    repo = TrainMovementRepository(db_session)
    movements = await repo.list_by_train("TRN-12301")
    assert len(movements) >= 1
    assert movements[0].stop_sequence == 1
    assert movements[0].classification == DataClass.REAL


@pytest.mark.asyncio
async def test_railway_rule_repository(db_session: AsyncSession):
    repo = RailwayRuleRepository(db_session)
    rule = await repo.get_by_id("RULE-STAT-RBP-1502C")
    assert rule is not None
    assert "Rolling Block Programme" in rule.title
    assert rule.safety_critical is True
    assert rule.rule_class == RuleClass.VERIFIED_SOURCE


@pytest.mark.asyncio
async def test_infrastructure_repository(db_session: AsyncSession):
    repo = InfrastructureRepository(db_session)
    specs = await repo.list_specs()
    assert len(specs) == 3
    corrs = await repo.list_corridors()
    assert len(corrs) == 4
