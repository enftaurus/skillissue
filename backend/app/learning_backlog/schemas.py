from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class BacklogItemCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=150)
    subtopic: Optional[str] = Field(default=None, max_length=150)
    source: str = Field(default="manual", max_length=50)  # 'interview_evaluation', 'manual', 'coding_practice'
    source_id: Optional[str] = Field(default=None, max_length=36)  # String(36) column
    reason: Optional[str] = Field(default="", max_length=4000)
    learning_objective: Optional[str] = Field(default=None, max_length=4000)
    suggested_exercise: Optional[str] = Field(default=None, max_length=4000)
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    notes: Optional[str] = Field(default=None, max_length=8000)

class QueueWeaknessRequest(BaseModel):
    interview_id: Optional[str] = Field(default=None, max_length=36)  # stored as source_id String(36)
    weakness_id: Optional[str] = Field(default=None, max_length=64)
    topic: str = Field(min_length=1, max_length=150)
    subtopic: Optional[str] = Field(default=None, max_length=150)
    evidence: Optional[str] = Field(default=None, max_length=4000)
    gap_explanation: Optional[str] = Field(default=None, max_length=4000)
    learning_objective: Optional[str] = Field(default=None, max_length=4000)
    suggested_exercise: Optional[str] = Field(default=None, max_length=4000)
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    notes: Optional[str] = Field(default=None, max_length=8000)

class BacklogItemUpdate(BaseModel):
    topic: Optional[str] = Field(default=None, min_length=1, max_length=150)
    subtopic: Optional[str] = Field(default=None, max_length=150)
    status: Optional[str] = Field(default=None, pattern="^(queued|planned|in_progress|completed|dismissed)$")
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    notes: Optional[str] = Field(default=None, max_length=8000)
    learning_objective: Optional[str] = Field(default=None, max_length=4000)
    suggested_exercise: Optional[str] = Field(default=None, max_length=4000)

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
