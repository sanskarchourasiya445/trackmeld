from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.db.session import get_db_session

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Basic service liveness probe."""
    return {
        "status": "ok",
        "service": "trackmeld-api",
    }


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def health_db_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Database connectivity and readiness check."""
    try:
        result = await session.execute(text("SELECT 1;"))
        scalar = result.scalar()
        if scalar == 1:
            return {
                "status": "ok",
                "database": "reachable",
            }
        raise Exception("Unexpected query result")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "DATABASE_UNREACHABLE",
                    "message": f"Database health check failed: {str(exc)}",
                }
            },
        )
