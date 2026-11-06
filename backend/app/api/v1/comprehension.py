from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import get_current_active_user
from backend.app.comprehension.service import ComprehensionService
from backend.app.core.rate_limit import rate_limit
from backend.app.database.models import User
from backend.app.database.session import get_db
from backend.app.providers.factory import ModelFactory

router = APIRouter(prefix="/comprehension", tags=["Code Comprehension"])


class StartRequest(BaseModel):
    item_id: str = Field(..., max_length=100)


class AnswerRequest(BaseModel):
    question_id: str = Field(..., max_length=20)
    answer: str = Field(..., max_length=8000)


@router.get("/items")
async def list_items(current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    return ComprehensionService.list_items()


@router.get("/history")
async def history(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    return await ComprehensionService.history(db, current_user.id)


@router.post("/sessions", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))])
async def start_session(data: StartRequest, current_user: User = Depends(get_current_active_user),
                        db: AsyncSession = Depends(get_db)):
    return await ComprehensionService.start(db, current_user.id, data.item_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, current_user: User = Depends(get_current_active_user),
                      db: AsyncSession = Depends(get_db)):
    return await ComprehensionService.get(db, current_user.id, session_id)


@router.post("/sessions/{session_id}/answer", dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))])
async def answer(session_id: str, data: AnswerRequest, current_user: User = Depends(get_current_active_user),
                 db: AsyncSession = Depends(get_db)):
    try:
        provider = await ModelFactory.get_for_user(db, current_user.id, task_type="evaluation")
    except Exception:
        provider = None  # deterministic + keyword grading still works offline
    return await ComprehensionService.answer(db, current_user.id, session_id, data.question_id, data.answer, provider)


@router.post("/sessions/{session_id}/finish")
async def finish(session_id: str, current_user: User = Depends(get_current_active_user),
                 db: AsyncSession = Depends(get_db)):
    return await ComprehensionService.finish(db, current_user.id, session_id)
