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
from backend.app.core.rate_limit import enforce_compute_rate_limit
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    CopilotToolSpec,
    EvidenceItem,
    EvidenceType,
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
    _rate_limit: None = Depends(enforce_compute_rate_limit),
) -> CopilotQueryResponse:
    """Submit natural language inquiry and receive evidence-grounded explanation.
    
    The Copilot operates strictly in read-only mode using typed tools.
    Any attempt to mutate schedules or authorize approvals is refused.
    """
    refusal = CopilotEngine.check_mutation_refusal(request.prompt)
    if refusal:
        return CopilotQueryResponse(
            query=request.prompt,
            answer=refusal,
            evidence=[
                EvidenceItem(
                    evidence_id="GOVERNANCE:READ_ONLY_GUARDRAIL",
                    evidence_type=EvidenceType.REFUSAL,
                    title="Read-Only Governance Boundary",
                    data={"rule": "COMPLETED_NOT_APPROVED", "authorized_roles": ["OPERATOR", "ADMIN"]},
                    source_reference="PRD::FR-032",
                )
            ],
            tool_calls_executed=[],
            provider_used="GOVERNANCE_GUARDRAIL",
        )

    try:
        return await CopilotEngine.explain(session=session, request=request)
    except (ConnectionRefusedError, OSError, Exception) as err:
        return CopilotQueryResponse(
            query=request.prompt,
            answer=(
                "**Database Offline Notice:** Live operational records could not be retrieved because "
                "the database service is currently offline or unreachable. "
                "In adherence to Indian Railways decision support boundaries, the Copilot cannot infer, speculate, "
                "or fabricate ungrounded answers without verified database records."
            ),
            evidence=[
                EvidenceItem(
                    evidence_id="SYSTEM:DB_OFFLINE",
                    evidence_type=EvidenceType.UNCERTAINTY,
                    title="Operational Database Offline",
                    data={"error": type(err).__name__, "status": "CONNECTION_REFUSED"},
                    source_reference="operational_database",
                )
            ],
            tool_calls_executed=[],
            provider_used="OFFLINE_TELEMETRY_ENGINE",
        )


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
