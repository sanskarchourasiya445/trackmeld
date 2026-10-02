from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.work_order_repo import WorkOrderRepository
from backend.app.schemas.operational_responses import WorkOrderResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.domain.enums import WorkOrderStatus, WorkDepartment

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.get("", response_model=List[WorkOrderResponse])
async def list_work_orders(
    scenario_id: Optional[str] = Query(None, description="Filter by operational scenario ID"),
    department: Optional[WorkDepartment] = Query(None, description="Filter by railway department"),
    status_filter: Optional[WorkOrderStatus] = Query(None, alias="status", description="Filter by lifecycle status"),
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[WorkOrderResponse]:
    """List work orders with optional filtering by scenario, department, and status."""
    repo = WorkOrderRepository(session)
    if department:
        orders = await repo.list_by_department(department, scenario_id=scenario_id)
    elif status_filter:
        orders = await repo.list_by_status(status_filter, scenario_id=scenario_id)
    elif scenario_id:
        orders = await repo.list_by_scenario(scenario_id)
    else:
        orders = await repo.list_all(limit=limit, offset=offset)
    return [WorkOrderResponse.model_validate(wo) for wo in orders]


@router.get(
    "/{work_order_id}",
    response_model=WorkOrderResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_work_order(
    work_order_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> WorkOrderResponse:
    """Retrieve work order by ID or business work order number."""
    repo = WorkOrderRepository(session)
    order = await repo.get_by_id(work_order_id)
    if not order:
        order = await repo.get_by_number(work_order_id)
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
