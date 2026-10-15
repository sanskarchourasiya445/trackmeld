from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.work_order_repo import WorkOrderRepository
from backend.app.schemas.operational_responses import WorkOrderResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.domain.enums import WorkOrderStatus, WorkDepartment, TaskPriority
from backend.app.core.auth import get_current_user, require_permission, AuthUser

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.get("", response_model=List[WorkOrderResponse])
async def list_work_orders(
    response: Response,
    scenario_id: Optional[str] = Query(None, description="Filter by operational scenario ID"),
    department: Optional[WorkDepartment] = Query(None, description="Filter by railway department"),
    status: Optional[WorkOrderStatus] = Query(None, description="Filter by lifecycle status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    mandatory: Optional[bool] = Query(None, description="Filter by mandatory flag"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> List[WorkOrderResponse]:
    """List work orders with multi-field filtering and pagination metadata."""
    repo = WorkOrderRepository(session)
    orders = await repo.filter_work_orders(
        scenario_id=scenario_id,
        department=department,
        status=status,
        priority=priority,
        mandatory=mandatory,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_work_orders(
        scenario_id=scenario_id,
        department=department,
        status=status,
        priority=priority,
        mandatory=mandatory,
    )

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [WorkOrderResponse.model_validate(wo) for wo in orders]


@router.get(
    "/{work_order_id}",
    response_model=WorkOrderResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_work_order(
    work_order_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> WorkOrderResponse:
    """Retrieve work order by ID or business work order number."""
    repo = WorkOrderRepository(session)
    order = await repo.get_by_id_or_number(work_order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "WORK_ORDER_NOT_FOUND",
                    "message": f"Work order '{work_order_id}' not found.",
                }
            },
        )
    return WorkOrderResponse.model_validate(order)
