from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

class ScoreHistoryPoint(BaseModel):
    interview_id: str
    title: str
    category: str
    mode: str
    overall_score: float
    completed_at: datetime

class DimensionTrend(BaseModel):
    dimension_id: str
    dimension_name: str
    scores: List[float]
    latest_score: float
    average_score: float

class ReassessmentComparison(BaseModel):
    baseline_interview_id: str
    baseline_title: str
    baseline_date: datetime
    baseline_score: float
    reassessment_interview_id: str
    reassessment_title: str
    reassessment_date: datetime
    reassessment_score: float
    score_delta: float
    category: str
    is_comparable: bool
    improved_dimensions: List[str]
    stable_dimensions: List[str]
    declined_dimensions: List[str]

class AnalyticsDashboardResponse(BaseModel):
    total_interviews: int
    completed_interviews: int
    average_overall_score: float
    plan_tasks_completed: int
    plan_tasks_total: int
    planly_completion_rate: float
    score_history: List[ScoreHistoryPoint]
    dimension_trends: List[DimensionTrend]
    recurring_strengths: List[str]
    recurring_weaknesses: List[str]
    reassessments: List[ReassessmentComparison]
