from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class CompanyProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    slug: str
    difficulty: str  # EASY, MEDIUM, HARD
    frequency_score: float
    acceptance_rate: float
    topics: List[str] = []
    order_index: int
    is_unlocked: bool = False
    is_solved: bool = False

class CompanyProblemDetail(CompanyProblemSummary):
    description: str
    starter_code: Dict[str, str] = {}
    test_cases: List[Dict[str, Any]] = []

class CompanyTrackSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
    tier: str  # 'gold', 'silver', 'bronze'
    role_title: str
    description: str
    community_tips: List[str] = []
    total_problems: int
    unlocked_count: int
    solved_count: int
    logo_icon: str
    is_gold_mine: bool = False

class CompanyTrackDetail(CompanyTrackSummary):
    problems: List[CompanyProblemSummary] = []

class SolveCompanyProblemRequest(BaseModel):
    language: str = Field(default="python", pattern="^(python|java|cpp)$")
    code: str = Field(min_length=1)

class SolveCompanyProblemResponse(BaseModel):
    status: str  # passed, failed, runtime_error
    tests_passed: int
    tests_total: int
    stdout: str = ""
    stderr: str = ""
    unlocked_new_problem: bool = False
    new_unlocked_problem_title: Optional[str] = None
    total_unlocked: int
    total_solved: int
