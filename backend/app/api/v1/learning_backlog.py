from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.learning_backlog.schemas import (
    BacklogItemCreate,
    BacklogItemUpdate,
    BacklogItemResponse,
    QueueWeaknessRequest,
)
from backend.app.learning_backlog.service import LearningBacklogService

router = APIRouter(prefix="/learning-backlog", tags=["Learning Backlog"])

@router.get("", response_model=List[BacklogItemResponse])
async def list_backlog_items(
    status: Optional[str] = Query(None, pattern="^(queued|planned|in_progress|completed|dismissed)$"),
    topic: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List persistent learning backlog items for current user."""
    items = await LearningBacklogService.list_items(db, current_user.id, status=status, topic=topic)
    return items

@router.post("", response_model=BacklogItemResponse, status_code=status.HTTP_201_CREATED)
async def create_backlog_item(
    data: BacklogItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add an item to the learning backlog."""
    return await LearningBacklogService.create_item(db, current_user.id, data)

@router.post("/queue-weakness", response_model=BacklogItemResponse, status_code=status.HTTP_200_OK)
async def queue_interview_weakness(
    data: QueueWeaknessRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Action B: Queue an interview-derived weakness for later revisit.
    Does NOT allocate dates, generate calendar tasks, or modify existing sprints.
    Enforces deduplication: existing queued/planned items for this topic are updated rather than duplicated.
    """
    return await LearningBacklogService.queue_weakness(db, current_user.id, data)

@router.get("/{item_id}", response_model=BacklogItemResponse)
async def get_backlog_item(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningBacklogService.get_item(db, current_user.id, item_id)

@router.patch("/{item_id}", response_model=BacklogItemResponse)
async def update_backlog_item(
    item_id: str,
    data: BacklogItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningBacklogService.update_item(db, current_user.id, item_id, data)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backlog_item(
    item_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await LearningBacklogService.delete_item(db, current_user.id, item_id)
    return None
