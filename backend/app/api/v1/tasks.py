from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from backend.app.domain.enums import TaskStatus

router = APIRouter(prefix="/tasks", tags=["Maintenance Tasks"])


@router.get("", response_model=List[MaintenanceTaskResponse])
async def list_tasks(
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    work_order_id: Optional[str] = Query(None, description="Filter by work order ID"),
    section_id: Optional[str] = Query(None, description="Filter by block section ID"),
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filter by task status"),
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[MaintenanceTaskResponse]:
    """List maintenance tasks with optional filtering."""
    repo = MaintenanceTaskRepository(session)
    if work_order_id:
        tasks = await repo.list_by_work_order(work_order_id)
    elif section_id:
        tasks = await repo.list_by_section(section_id, scenario_id=scenario_id)
    elif status_filter:
        tasks = await repo.list_by_status(status_filter, scenario_id=scenario_id)
    elif scenario_id:
        tasks = await repo.list_by_scenario(scenario_id)
    else:
        tasks = await repo.list_all(limit=limit, offset=offset)
    return [MaintenanceTaskResponse.model_validate(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=MaintenanceTaskDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_task_details(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> MaintenanceTaskDetailResponse:
    """Retrieve detailed maintenance task information including dependencies, resources, and rules."""
    repo = MaintenanceTaskRepository(session)
    task = await repo.get_with_relations(task_id)
    if not task:
        # Check by task_code as well
        task_obj = await repo.get_by_code(task_id)
        if task_obj:
            task = await repo.get_with_relations(task_obj.task_id)
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
