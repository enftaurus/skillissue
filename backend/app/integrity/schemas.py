"""Pydantic schemas for explanation check and editor telemetry features."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# 1. Explanation Check Schemas
# ==========================================

class ExplanationQuestion(BaseModel):
    type: str = Field(description="'rationale' | 'mutation' | 'behaviour'")
    text: str = Field(description="The question prompt for the candidate")
    code_reference: str = Field(description="Exact substring or token present in candidate code")


class CreateExplanationCheckRequest(BaseModel):
    submission_ref: str = Field(description="Identifier or hash of the code submission")
    mode: str = Field(default="practice", description="'practice' | 'assessment'")
    candidate_assessment_id: Optional[str] = Field(default=None, description="Assessment ID if assessment mode")
    round_key: str = Field(default="oa_dsa", description="Key identifying the round")
    problem_title: Optional[str] = Field(default=None, description="Optional problem title")
    problem_statement: Optional[str] = Field(default=None, description="Optional problem statement")


class ExplanationAnswerItem(BaseModel):
    question_index: int = Field(ge=0, description="0-indexed question position")
    text: str = Field(description="Candidate's spoken or written answer")
    answered_at: Optional[datetime] = Field(default=None)
    seconds_to_first_input: float = Field(default=0.0, description="Time to first keystroke/audio in seconds")
    input_mode: str = Field(default="text", description="'text' | 'voice'")
    asr_confidence: Optional[float] = Field(default=None, description="Confidence if transcribed via ASR")


class SubmitAnswersRequest(BaseModel):
    answers: List[ExplanationAnswerItem]
    total_seconds_taken: Optional[float] = Field(default=None, description="Total duration for answer round")


class QuestionJudgeDetail(BaseModel):
    question_index: int
    accuracy: int = Field(ge=0, le=4)
    consistency: int = Field(ge=0, le=4)
    depth: int = Field(ge=0, le=4)
    evidence_quote: str = Field(max_length=250)
    code_reference: str
    critique: Optional[str] = None


class ExplanationEvaluationPayload(BaseModel):
    question_evaluations: List[QuestionJudgeDetail]
    explanation_consistency: float = Field(ge=0.0, le=1.0)
    average_accuracy: float = Field(ge=0.0, le=4.0)
    average_depth: float = Field(ge=0.0, le=4.0)
    coaching_what_went_well: List[str] = Field(default_factory=list)
    coaching_what_to_revisit: List[str] = Field(default_factory=list)


class ExplanationCheckPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    round_key: str
    submission_ref: str
    mode: str
    status: str
    discriminative_power: str
    questions: List[ExplanationQuestion]
    time_limit_per_question: int
    # Candidate view fields
    coaching: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class ExplanationCheckDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    candidate_assessment_id: Optional[str] = None
    round_key: str
    submission_ref: str
    mode: str
    status: str
    confidence: Optional[str] = None
    discriminative_power: str
    questions: List[Dict[str, Any]]
    answers: List[Dict[str, Any]]
    evaluation: Optional[Dict[str, Any]] = None
    model_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    answered_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None


# ==========================================
# 2. Editor Telemetry Schemas
# ==========================================

class TelemetryEventItem(BaseModel):
    type: str = Field(description="content_change | paste | key_down | cursor | selection | scroll | blur | focus | visibility | mouse")
    timestamp: float = Field(description="Epoch ms or session offset ms")
    key_category: Optional[str] = Field(default=None, description="printable | backspace_delete | enter | tab | arrow_navigation | shortcut")
    source: Optional[str] = Field(default="typing", description="typing | paste | suggest | unattributed")
    inserted_length: Optional[int] = 0
    removed_length: Optional[int] = 0
    line_count_delta: Optional[int] = 0
    range_offset: Optional[int] = None
    range_length: Optional[int] = None
    inserted_text: Optional[str] = None
    cursor_reason: Optional[str] = None
    mouse_moves_count: Optional[int] = None


class EditorTelemetryBatchRequest(BaseModel):
    round_key: str
    seq: int = Field(ge=0, description="Monotonically increasing sequence number")
    client_start_ts: float = Field(description="Session start timestamp")
    events: List[Dict[str, Any]] = Field(description="List of raw editor events")


class EditorTelemetryReplayResponse(BaseModel):
    candidate_assessment_id: str
    round_key: str
    total_batches: int
    total_events: int
    reconstructed_code: str
    code_hash_match: bool
    features: Dict[str, Any]
    flags: List[Dict[str, Any]]
    activity_density_series: List[Dict[str, Any]]
    timeline_markers: List[Dict[str, Any]]
    timeline: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    product_honesty: str
