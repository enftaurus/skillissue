from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class CreateCustomPlanRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=150, description="What you want to learn, e.g. Operating Systems, DBMS, DSA, System Design")
    goal: str = Field(default="interview_prep", pattern="^(fundamentals|interview_prep|mastery)$")
    daily_study_minutes: int = Field(default=45, ge=15, le=180)
    schedule_days: List[str] = Field(default=["monday", "tuesday", "wednesday", "thursday", "friday"])
    current_level: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced)$")
    deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None

class PlanTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    plan_id: str
    day_number: int
    title: str
    description: str
    subtopic: Optional[str] = None
    task_type: str
    estimated_minutes: int
    scheduled_date: Optional[datetime] = None
    status: str = "upcoming"  # 'upcoming', 'in_progress', 'completed', 'skipped'
    external_resources: List[Dict[str, str]] = []
    is_completed: bool
    completed_at: Optional[datetime] = None

class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    evaluation_id: Optional[str] = None
    title: str
    topic: Optional[str] = None
    goal: Optional[str] = None
    target_role: str
    target_skills: List[str]
    schedule_days: List[str] = []
    current_level: str = "intermediate"
    status: str
    total_days: int
    current_day: int
    daily_study_minutes: int
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    tasks: List[PlanTaskResponse]
    created_at: datetime
    updated_at: datetime

class TaskToggleRequest(BaseModel):
    is_completed: bool

class TaskStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(upcoming|in_progress|completed|skipped)$")

class TaskRescheduleRequest(BaseModel):
    new_date: datetime

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

class AttachBacklogItemsRequest(BaseModel):
    backlog_item_ids: List[str]

class SuggestedBacklogItemResponse(BaseModel):
    id: str
    topic: str
    subtopic: Optional[str] = None
    reason: str
    source: str
    source_id: Optional[str] = None
    priority: str
    status: str
    suggested_reason: str
