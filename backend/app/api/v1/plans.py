from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.plans.schemas import (
    PlanResponse, PlanTaskResponse, TaskToggleRequest, PlanAdaptRequest, PlanAdaptPreviewResponse,
    CreateCustomPlanRequest, TaskStatusUpdateRequest, TaskRescheduleRequest,
    AttachBacklogItemsRequest, SuggestedBacklogItemResponse, GeneratePlanFromEvaluationRequest,
    PlanRescheduleToTodayRequest, PlanReschedulePreviewResponse
)
from backend.app.plans.service import PlanService

router = APIRouter(prefix="/plans", tags=["Planly Improvement Plans"])

@router.post("/custom", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_topic_plan(
    data: CreateCustomPlanRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates a structured, dated study curriculum based on user-selected topics and schedule."""
    return await PlanService.create_custom_plan(db, current_user.id, data)

@router.post("/generate/{evaluation_id}", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan_from_evaluation(
    evaluation_id: str,
    req: Optional[GeneratePlanFromEvaluationRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    total_days = req.total_days if req else 7
    daily_minutes = req.daily_study_minutes if req else None
    target_date = req.target_date if req else None
    return await PlanService.create_plan_from_evaluation(
        db, current_user.id, evaluation_id, total_days=total_days, daily_study_minutes=daily_minutes, target_date=target_date
    )

@router.get("/active", response_model=Optional[PlanResponse])
async def get_active_plan(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.get_active_plan(db, current_user.id)

@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan_by_id(
    plan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.get_plan_by_id(db, current_user.id, plan_id)

@router.get("", response_model=List[PlanResponse])
async def list_plans(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.list_plans(db, current_user.id)

@router.post("/tasks/{task_id}/toggle", response_model=PlanTaskResponse)
async def toggle_task_completion(
    task_id: str,
    data: TaskToggleRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.toggle_task_completion(db, current_user.id, task_id, data.is_completed)

@router.put("/tasks/{task_id}/status", response_model=PlanTaskResponse)
async def update_task_status(
    task_id: str,
    data: TaskStatusUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.update_task_status(db, current_user.id, task_id, data.status)

@router.put("/tasks/{task_id}/reschedule", response_model=PlanTaskResponse)
async def reschedule_task(
    task_id: str,
    data: TaskRescheduleRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.reschedule_task(db, current_user.id, task_id, data.new_date)

@router.post("/{plan_id}/adapt/preview", response_model=PlanAdaptPreviewResponse)
async def preview_plan_schedule_adaptation(
    plan_id: str,
    data: PlanAdaptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.preview_adapt_plan(db, current_user.id, plan_id, data.days_behind)

@router.post("/{plan_id}/adapt", response_model=PlanResponse)
async def adapt_plan_schedule(
    plan_id: str,
    data: PlanAdaptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.adapt_plan(db, current_user.id, plan_id, data.days_behind)

@router.post("/{plan_id}/reschedule-to-today/preview", response_model=PlanReschedulePreviewResponse)
async def preview_reschedule_to_today(
    plan_id: str,
    data: Optional[PlanRescheduleToTodayRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Previews rescheduling uncompleted tasks to start from today, preserving completed progress."""
    start_date = data.start_date if data else None
    return await PlanService.preview_reschedule_to_today(db, current_user.id, plan_id, start_date)

@router.post("/{plan_id}/reschedule-to-today", response_model=PlanResponse)
async def reschedule_plan_to_today(
    plan_id: str,
    data: Optional[PlanRescheduleToTodayRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reschedules all remaining uncompleted tasks to start from today's date based on current progress."""
    start_date = data.start_date if data else None
    return await PlanService.reschedule_plan_to_today(db, current_user.id, plan_id, start_date)

@router.get("/{plan_id}/suggested-backlog", response_model=List[SuggestedBacklogItemResponse])
async def get_suggested_backlog(
    plan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Surfaces queued backlog items relevant to this sprint as suggestions."""
    return await PlanService.get_suggested_backlog(db, current_user.id, plan_id)

@router.post("/{plan_id}/backlog-items", response_model=PlanResponse)
async def attach_backlog_items_to_plan(
    plan_id: str,
    data: AttachBacklogItemsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly attaches selected backlog items to this sprint as dated tasks."""
    return await PlanService.attach_backlog_items(db, current_user.id, plan_id, data.backlog_item_ids)
