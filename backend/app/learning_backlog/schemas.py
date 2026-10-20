from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class BacklogItemCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=150)
    subtopic: Optional[str] = Field(default=None, max_length=150)
    source: str = Field(default="manual", max_length=50)  # 'interview_evaluation', 'manual', 'coding_practice'
    source_id: Optional[str] = None
    reason: Optional[str] = ""
    learning_objective: Optional[str] = None
    suggested_exercise: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    notes: Optional[str] = None

class QueueWeaknessRequest(BaseModel):
    interview_id: Optional[str] = None
    weakness_id: Optional[str] = None
    topic: str = Field(min_length=1, max_length=150)
    subtopic: Optional[str] = None
    evidence: Optional[str] = None
    gap_explanation: Optional[str] = None
    learning_objective: Optional[str] = None
    suggested_exercise: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    notes: Optional[str] = None

class BacklogItemUpdate(BaseModel):
    topic: Optional[str] = Field(default=None, min_length=1, max_length=150)
    subtopic: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(queued|planned|in_progress|completed|dismissed)$")
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    notes: Optional[str] = None
    learning_objective: Optional[str] = None
    suggested_exercise: Optional[str] = None

class BacklogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    topic: str
    subtopic: Optional[str] = None
    source: str
    source_id: Optional[str] = None
    reason: str
    learning_objective: Optional[str] = None
    suggested_exercise: Optional[str] = None
    priority: str
    status: str
    notes: Optional[str] = None
    planned_plan_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_existing: Optional[bool] = False
