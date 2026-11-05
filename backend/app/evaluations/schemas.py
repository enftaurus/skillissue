from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class QuestionSelfEvaluation(BaseModel):
    question_index: int
    interviewer_question: Optional[str] = None
    candidate_answer: Optional[str] = None
    score: int = Field(ge=1, le=5, description="Self rating from 1 to 5")
    strengths: Optional[str] = ""
    missed_points: Optional[str] = ""
    confidence: Optional[str] = "medium"

class SelfEvaluationCreate(BaseModel):
    interview_id: str
    dimension_scores: Optional[Dict[str, int]] = Field(default_factory=dict, description="Rubric dimension ID to 1-5 score")
    reflection: Optional[str] = ""
    question_evaluations: Optional[List[QuestionSelfEvaluation]] = Field(default_factory=list)

class SelfEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    interview_id: str
    dimension_scores: Dict[str, int]
    reflection: str
    question_evaluations: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

class EvaluationDimensionDetail(BaseModel):
    score: int
    max_score: int = 5
    explanation: str
    evidence_quote: str

class EvidenceExcerpt(BaseModel):
    quote: str
    critique: str

class QuestionFeedback(BaseModel):
    question_index: int
    score: Optional[int] = Field(default=None, ge=1, le=5)
    interviewer_question: str
    candidate_answer: str
    verbatim_quote: Optional[str] = None
    critique: str
    strong_answer_guide: str
    targeted_resource: Optional[str] = None

class WeaknessAnalysisItem(BaseModel):
    id: Optional[str] = None
    topic: str
    subtopic: Optional[str] = None
    evidence: str
    gap_explanation: str
    learning_objective: str
    suggested_exercise: Optional[str] = None
    confidence: str = "medium"  # 'high', 'medium', 'low'
    status: str = "identified"  # 'identified', 'added_to_plan', 'queued', 'dismissed'

class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    interview_id: str
    overall_score: Optional[float] = None
    status: str = "completed"
    rubric_dimension_scores: Dict[str, Dict[str, Any]]
    strengths: List[str]
    weaknesses: List[str]
    missing_concepts: List[str]
    evidence_excerpts: List[Dict[str, str]]
    question_feedback: List[QuestionFeedback] = []
    weakness_analysis: List[WeaknessAnalysisItem] = []
    suggested_corrections: List[str]
    uncertainty_notes: List[str]
    tokens_used: int
    model_identifier: str
    created_at: datetime
    stored_transcript: Optional[str] = None
    transcript_turns: Optional[List[Dict[str, Any]]] = None
    credibility: Optional[Dict[str, Any]] = None

class DimensionComparison(BaseModel):
    dimension_id: str
    dimension_name: str
    self_score: Optional[int] = None
    ai_score: int
    delta: Optional[int] = None
    evidence_quote: str
    explanation: str

class QuestionComparison(BaseModel):
    question_index: int
    interviewer_question: str
    candidate_answer: str
    self_score: Optional[int] = None
    ai_score: Optional[int] = None
    score_gap: Optional[int] = None
    self_strengths: Optional[str] = None
    self_missed_points: Optional[str] = None
    self_confidence: Optional[str] = None
    ai_verbatim_quote: Optional[str] = None
    ai_critique: Optional[str] = None
    ai_guide: Optional[str] = None
    targeted_resource: Optional[str] = None

class EvaluationComparisonResponse(BaseModel):
    interview_id: str
    overall_ai_score: Optional[float] = None
    dimensions: List[DimensionComparison]
    question_comparisons: List[QuestionComparison] = []
    self_reflection: str
    strengths: List[str]
    weaknesses: List[str]
    missing_concepts: List[str]
    weakness_analysis: List[WeaknessAnalysisItem] = []
    transcript_turns: Optional[List[Dict[str, Any]]] = None

class RetestInitiateRequest(BaseModel):
    weakness_topic: str
    baseline_score: Optional[float] = None

class RetestSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_interview_id: str
    original_evaluation_id: str
    retest_interview_id: Optional[str] = None
    weakness_topic: str
    baseline_score: float
    retest_score: float
    delta_score: float
    verified_improvements: List[str] = []
    status: str
    created_at: datetime


class DisputeCreate(BaseModel):
    dimension_id: str = Field(..., max_length=80)
    quote: str = Field(..., min_length=12, max_length=1500)
    argument: str = Field(..., min_length=10, max_length=1500)


class DisputeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    dimension_id: str
    decision: str
    old_score: Optional[int] = None
    new_score: Optional[int] = None
    reason: str
    created_at: datetime
