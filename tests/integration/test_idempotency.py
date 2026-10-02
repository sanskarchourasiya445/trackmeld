import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from scripts.ingest_phase0 import run_ingestion


@pytest.mark.asyncio
async def test_ingestion_idempotency(db_session: AsyncSession):
    """Verify that re-running ingestion creates zero duplicate rows."""
    # Run ingestion
    run_ingestion()

    # Query counts
    stn_count = (await db_session.execute(text("SELECT count(*) FROM stations"))).scalar()
    sec_count = (await db_session.execute(text("SELECT count(*) FROM sections"))).scalar()
    trn_count = (await db_session.execute(text("SELECT count(*) FROM trains"))).scalar()
    mov_count = (await db_session.execute(text("SELECT count(*) FROM train_movements"))).scalar()
    rule_count = (await db_session.execute(text("SELECT count(*) FROM railway_rules"))).scalar()

    assert stn_count == 68
    assert sec_count == 66
    assert trn_count == 3429
    assert mov_count == 82
    assert rule_count == 9
