from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.rule_repo import RailwayRuleRepository
from backend.app.schemas.responses import RuleResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import require_permission, AuthUser

router = APIRouter(prefix="/rules", tags=["Rules"])


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_rule_by_id(
    rule_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:reference")),
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
    response: Response,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:reference")),
) -> List[RuleResponse]:
    """List all extracted statutory and operating rules with pagination headers."""
    repo = RailwayRuleRepository(session)
    rules = await repo.list_all(limit=limit, offset=offset)
    total_count = await repo.count()

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [RuleResponse.model_validate(r) for r in rules]
