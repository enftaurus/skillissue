from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.plans.schemas import (
    PlanResponse, PlanTaskResponse, TaskToggleRequest, PlanAdaptRequest
)
from backend.app.plans.service import PlanService

router = APIRouter(prefix="/plans", tags=["Planly Improvement Plans"])

@router.post("/generate/{evaluation_id}", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan_from_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.create_plan_from_evaluation(db, current_user.id, evaluation_id)

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

@router.post("/{plan_id}/adapt", response_model=PlanResponse)
async def adapt_plan_schedule(
    plan_id: str,
    data: PlanAdaptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await PlanService.adapt_plan(db, current_user.id, plan_id, data)
