from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.task_repo import MaintenanceTaskRepository
from backend.app.schemas.operational_responses import (
    MaintenanceTaskResponse,
    MaintenanceTaskDetailResponse,
    TaskResourceRequirementResponse,
    TaskDependencyResponse,
)
from backend.app.schemas.common import ErrorResponse
from backend.app.domain.enums import TaskStatus, TaskPriority, TaskType
from backend.app.core.auth import get_current_user, require_permission, AuthUser

router = APIRouter(prefix="/tasks", tags=["Maintenance Tasks"])


@router.get("", response_model=List[MaintenanceTaskResponse])
async def list_tasks(
    response: Response,
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    work_order_id: Optional[str] = Query(None, description="Filter by work order ID"),
    section_id: Optional[str] = Query(None, description="Filter by block section ID"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    mandatory: Optional[bool] = Query(None, description="Filter by mandatory status"),
    requires_traffic_block: Optional[bool] = Query(None, description="Filter by traffic block requirement"),
    requires_power_block: Optional[bool] = Query(None, description="Filter by power block requirement"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> List[MaintenanceTaskResponse]:
    """List maintenance tasks with multi-field filtering and pagination metadata."""
    repo = MaintenanceTaskRepository(session)
    tasks = await repo.filter_tasks(
        scenario_id=scenario_id,
        section_id=section_id,
        work_order_id=work_order_id,
        status=status,
        priority=priority,
        task_type=task_type,
        mandatory=mandatory,
        requires_traffic_block=requires_traffic_block,
        requires_power_block=requires_power_block,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_tasks(
        scenario_id=scenario_id,
        section_id=section_id,
        work_order_id=work_order_id,
        status=status,
        priority=priority,
        task_type=task_type,
        mandatory=mandatory,
        requires_traffic_block=requires_traffic_block,
        requires_power_block=requires_power_block,
    )

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [MaintenanceTaskResponse.model_validate(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=MaintenanceTaskDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_task_details(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> MaintenanceTaskDetailResponse:
    """Retrieve detailed maintenance task information including dependencies, resources, and rules."""
    repo = MaintenanceTaskRepository(session)
    task = await repo.get_with_relations(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Maintenance task '{task_id}' not found.",
                }
            },
        )

    base_resp = MaintenanceTaskResponse.model_validate(task)
    return MaintenanceTaskDetailResponse(
        **base_resp.model_dump(),
        additional_section_ids=[s.section_id for s in task.affected_sections],
        rule_reference_ids=[r.rule_id for r in task.rule_references],
        resource_requirements=[
            TaskResourceRequirementResponse.model_validate(req)
            for req in task.resource_requirements
        ],
        predecessor_dependencies=[
            TaskDependencyResponse.model_validate(dep)
            for dep in task.incoming_dependencies
        ],
        successor_dependencies=[
            TaskDependencyResponse.model_validate(dep)
            for dep in task.outgoing_dependencies
        ],
    )
