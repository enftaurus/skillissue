from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

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

class AssessmentPipelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
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
    candidate_email: str = Field(min_length=5, max_length=255)

class CandidateAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    pipeline_id: str
    pipeline_title: Optional[str] = None
    target_role: Optional[str] = None
    candidate_name: str
    candidate_email: str
    access_token: str
    status: str  # 'invited', 'in_progress', 'completed', 'flagged'
    resume_text: Optional[str] = None
    oa_problem_title: Optional[str] = None
    oa_submitted_code: Optional[str] = None
    current_round_index: int
    round_results: Dict[str, Any] = {}
    composite_score: float = 0.0
    integrity_signals: Dict[str, Any] = {}
    rounds: List[Dict[str, Any]] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

class CandidateSubmitRoundRequest(BaseModel):
    round_index: int
    round_type: str
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
    average_score: float
    candidates: List[CandidateAssessmentResponse] = []

