"""
API endpoints for TrackMeld Read-Only Copilot & Decision Support.

Exposes:
- POST /api/v1/copilot/explain: Submit inquiry and receive evidence-grounded explanation
- GET /api/v1/copilot/tools: Retrieve specifications of available typed read-only tools
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, AuthUser
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    CopilotToolSpec,
)
from backend.app.services.copilot import CopilotEngine, CopilotToolRegistry

router = APIRouter(prefix="/copilot", tags=["AI Copilot & Decision Support"])


@router.post(
    "/explain",
    response_model=CopilotQueryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def explain_decision(
    request: CopilotQueryRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> CopilotQueryResponse:
    """Submit natural language inquiry and receive evidence-grounded explanation.
    
    The Copilot operates strictly in read-only mode using typed tools.
    Any attempt to mutate schedules or authorize approvals is refused.
    """
    return await CopilotEngine.explain(session=session, request=request)


@router.get(
    "/tools",
    response_model=List[CopilotToolSpec],
    status_code=status.HTTP_200_OK,
)
async def list_copilot_tools(
    current_user: AuthUser = Depends(get_current_user),
) -> List[CopilotToolSpec]:
    """Retrieve specifications of all typed read-only tools available to the Copilot."""
    return CopilotToolRegistry.list_tools()
