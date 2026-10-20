from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class InterviewCreateDomain(BaseModel):
    category: str = Field(default="technical", pattern="^(technical|behavioral|dsa|managerial)$")
    domain_skills: List[str] = Field(min_length=1)
    target_role: Optional[str] = "Software Engineer"
    difficulty: Optional[str] = "intermediate"
    resume_id: Optional[str] = None
    coding_problem_id: Optional[str] = None
    target_duration_minutes: Optional[int] = 20

class InterviewCreateJd(BaseModel):
    category: str = Field(default="technical", pattern="^(technical|behavioral|dsa|managerial)$")
    jd_id: str
    difficulty: Optional[str] = "intermediate"
    resume_id: Optional[str] = None
    coding_problem_id: Optional[str] = None
    target_duration_minutes: Optional[int] = 20

class InterviewMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class HintRequest(BaseModel):
    level: int = Field(ge=1, le=3, description="Socratic hint tier: 1=clarifying nudge, 2=algorithmic pattern, 3=pseudocode/structure")
    problem_id: Optional[str] = None
    current_code: Optional[str] = None

class HintResponse(BaseModel):
    level: int
    hint: str
    penalty_pct: int
    total_hint_level_used: int
    message_id: str

class InterviewMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    interview_id: str
    role: str
    content: str
    question_index: int
    is_follow_up: bool
    created_at: datetime

class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    mode: str
    category: str
    title: str
    target_role: str
    difficulty: str
    status: str
    domain_skills: List[str]
    jd_id: Optional[str] = None
    resume_id: Optional[str] = None
    coding_problem_id: Optional[str] = None
    hint_level_used: int = 0
    target_duration_minutes: int
    created_at: datetime
    completed_at: Optional[datetime] = None

class InterviewDetailResponse(InterviewResponse):
    messages: List[InterviewMessageResponse]

