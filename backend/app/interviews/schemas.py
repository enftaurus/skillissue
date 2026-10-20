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
    client_turn_id: Optional[str] = Field(default=None, max_length=64)

class CodingTurnRequest(BaseModel):
    language: str = Field(default="python", pattern="^(python|cpp|java)$")
    code: str = Field(min_length=1, max_length=50000)
    run_mode: str = Field(default="submit", pattern="^(run|submit)$")
    client_turn_id: Optional[str] = None
    candidate_notes: Optional[str] = None

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
    client_turn_id: Optional[str] = None
    created_at: datetime

class CodingTurnResponse(BaseModel):
    execution: Dict[str, Any]
    assistant_message: InterviewMessageResponse

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
    latest_submission_id: Optional[str] = None
    hint_level_used: int = 0
    target_duration_minutes: int
    current_summary: str = ""
    covered_topics: List[str] = []
    topic_statuses: Dict[str, str] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None

class QuestionTurnResponse(BaseModel):
    question_index: int
    interviewer_question: str
    candidate_answer: str = ""
    is_follow_up: bool = False
    assistant_message_id: Optional[str] = None
    user_message_id: Optional[str] = None

class InterviewDetailResponse(InterviewResponse):
    messages: List[InterviewMessageResponse]
    grouped_transcript: Optional[List[QuestionTurnResponse]] = None

class InterviewStateResponse(BaseModel):
    interview_id: str
    status: str
    difficulty: str
    current_topic: str
    covered_topics: List[str] = []
    topic_statuses: Dict[str, str] = {}
    running_summary: str = ""
    candidate_evidence: List[Dict[str, Any]] = []
    turn_count: int = 0
    max_turns: int = 8
