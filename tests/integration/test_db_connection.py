import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_database_connectivity(db_session: AsyncSession):
    """Verify async PostgreSQL connection and database name."""
    result = await db_session.execute(text("SELECT current_database();"))
    db_name = result.scalar()
    assert db_name == "trackmeld"
