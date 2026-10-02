from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.rule_repo import RailwayRuleRepository
from backend.app.schemas.responses import RuleResponse
from backend.app.schemas.common import ErrorResponse

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_rule_by_id(
    rule_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RuleResponse:
    """Retrieve verbatim rule details by rule ID (e.g. RULE-STAT-RBP-1502C)."""
    repo = RailwayRuleRepository(session)
    rule = await repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Railway rule '{rule_id}' not found.",
                }
            },
        )
    return RuleResponse.model_validate(rule)


@router.get("", response_model=List[RuleResponse])
async def list_rules(
    session: AsyncSession = Depends(get_db_session),
) -> List[RuleResponse]:
    """List all extracted statutory and operating rules."""
    repo = RailwayRuleRepository(session)
    rules = await repo.list_all(limit=100)
    return [RuleResponse.model_validate(r) for r in rules]
