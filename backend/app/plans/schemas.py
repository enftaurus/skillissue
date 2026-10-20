from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class PlanTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    plan_id: str
    day_number: int
    title: str
    description: str
    task_type: str
    estimated_minutes: int
    external_resources: List[Dict[str, str]]
    is_completed: bool
    completed_at: Optional[datetime] = None

class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    evaluation_id: Optional[str] = None
    title: str
    target_role: str
    target_skills: List[str]
    status: str
    total_days: int
    current_day: int
    daily_study_minutes: int
    tasks: List[PlanTaskResponse]
    created_at: datetime
    updated_at: datetime

class TaskToggleRequest(BaseModel):
    is_completed: bool

class PlanAdaptRequest(BaseModel):
    days_behind: int = Field(default=1, ge=1, le=14)

class TaskShiftPreview(BaseModel):
    task_id: str
    title: str
    current_day: int
    new_day: int
    task_type: str

class PlanAdaptPreviewResponse(BaseModel):
    plan_id: str
    days_behind: int
    current_total_days: int
    new_total_days: int
    shifted_tasks: List[TaskShiftPreview]

