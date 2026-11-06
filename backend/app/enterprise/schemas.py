from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class RoundConfig(BaseModel):
    round_type: str = Field(pattern="^(oa_dsa|ai_project|tough_interview|code_comprehension)$")
    name: str
    time_limit_minutes: int = Field(default=30, ge=10, le=120)
    is_enabled: bool = True
    config: Dict[str, Any] = {}

class CreatePipelineRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    target_role: str = Field(default="Software Development Engineer", min_length=2, max_length=150)
    job_description: str = Field(min_length=10)
    rounds: List[RoundConfig] = Field(default_factory=list)
    oa_config: Dict[str, Any] = Field(default_factory=lambda: {"mode": "preset", "rating_min": 1200, "rating_max": 1600, "topic_tags": ["dp", "graphs"]})

class UpdatePipelineRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    target_role: Optional[str] = Field(default=None, min_length=2, max_length=150)
    job_description: Optional[str] = Field(default=None, min_length=10)
    rounds: Optional[List[RoundConfig]] = None
    oa_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class AssessmentPipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tenant_id: Optional[str] = None
    title: str
    target_role: str
    job_description: str
    rounds: List[Dict[str, Any]]
    oa_config: Dict[str, Any] = {}
    is_active: bool
    invite_token: str
    invite_url: str
    candidates_count: int = 0
    created_at: datetime
    updated_at: datetime

class CandidateInviteRequest(BaseModel):
    candidate_name: str = Field(min_length=2, max_length=150)
    candidate_email: EmailStr

class CandidateEntryRequest(BaseModel):
    # The candidate is the signed-in user; the email always comes from the account, never from this body.
    candidate_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    candidate_email: Optional[EmailStr] = None


class CandidateExamView(BaseModel):
    """What a candidate may see about their own assessment: progress, never results (ADR 0027)."""
    id: str = ""
    pipeline_id: str
    pipeline_title: Optional[str] = None
    target_role: Optional[str] = None
    candidate_name: str = ""
    candidate_email: str = ""
    access_token: str = ""
    token_expires_at: Optional[datetime] = None
    status: str  # entry_required | in_progress | completed
    current_round_index: int = 0
    rounds: List[Dict[str, Any]] = []
    is_invite_token: bool = False
    requires_login: bool = False
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DsaRunRequest(BaseModel):
    problem_id: str = Field(max_length=120)
    language: str = Field(pattern="^(python|java|cpp)$")
    code: str = Field(max_length=65000)


class ProjectRunRequest(BaseModel):
    files: Dict[str, str]


class ComprehensionAnswerRequest(BaseModel):
    question_id: str = Field(max_length=20)
    answer: str = Field(max_length=4000)


class InterviewAnswerRequest(BaseModel):
    answer: Optional[str] = Field(default=None, max_length=4000)

class CandidateAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    pipeline_id: str
    pipeline_title: Optional[str] = None
    target_role: Optional[str] = None
    candidate_name: str
    candidate_email: str
    access_token: str
    token_expires_at: Optional[datetime] = None
    status: str  # 'invited', 'in_progress', 'completed', 'flagged', 'entry_required', 'submitted_unscored', 'not_evaluated'
    resume_text: Optional[str] = None
    oa_problem_title: Optional[str] = None
    oa_submitted_code: Optional[str] = None
    current_round_index: int = 0
    round_results: Dict[str, Any] = {}
    composite_score: Optional[float] = None
    integrity_signals: Dict[str, Any] = {}
    rounds: List[Dict[str, Any]] = []
    is_invite_token: bool = False
    rank: Optional[int] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class CandidateSubmitRoundRequest(BaseModel):
    round_index: int = Field(ge=0, le=20)
    round_type: str = Field(max_length=40)
    resume_text: Optional[str] = None
    oa_problem_title: Optional[str] = None
    oa_submitted_code: Optional[str] = None
    submission_data: Dict[str, Any] = {}
    integrity_events: Dict[str, Any] = {}

class PipelineLeaderboardResponse(BaseModel):
    pipeline_id: str
    pipeline_title: str
    target_role: str
    total_candidates: int
    completed_candidates: int
    average_score: Optional[float] = None
    candidates: List[CandidateAssessmentResponse] = []
    rankings: List[Dict[str, Any]] = []

