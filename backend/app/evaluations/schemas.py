from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class SelfEvaluationCreate(BaseModel):
    interview_id: str
    dimension_scores: Dict[str, int] = Field(description="Rubric dimension ID to 1-5 score")
    reflection: Optional[str] = ""

class SelfEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    interview_id: str
    dimension_scores: Dict[str, int]
    reflection: str
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
    interviewer_question: str
    candidate_answer: str
    verbatim_quote: str
    critique: str
    strong_answer_guide: str
    targeted_resource: Optional[str] = None

class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    interview_id: str
    overall_score: float
    rubric_dimension_scores: Dict[str, Dict[str, Any]]
    strengths: List[str]
    weaknesses: List[str]
    missing_concepts: List[str]
    evidence_excerpts: List[Dict[str, str]]
    question_feedback: List[QuestionFeedback] = []
    suggested_corrections: List[str]
    uncertainty_notes: List[str]
    tokens_used: int
    model_identifier: str
    created_at: datetime

class DimensionComparison(BaseModel):
    dimension_id: str
    dimension_name: str
    self_score: Optional[int] = None
    ai_score: int
    delta: Optional[int] = None
    evidence_quote: str
    explanation: str

class EvaluationComparisonResponse(BaseModel):
    interview_id: str
    overall_ai_score: float
    dimensions: List[DimensionComparison]
    self_reflection: str
    strengths: List[str]
    weaknesses: List[str]
    missing_concepts: List[str]
