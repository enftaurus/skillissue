from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

class CompanyProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    slug: str
    leetcode_url: str = ""
    difficulty: str  # EASY, MEDIUM, HARD
    frequency_score: float
    acceptance_rate: float
    topics: List[str] = []
    order_index: int
    is_unlocked: bool = False
    is_solved: bool = False

    @model_validator(mode="after")
    def ensure_leetcode_url(self) -> "CompanyProblemSummary":
        if not self.leetcode_url and self.slug:
            self.leetcode_url = f"https://leetcode.com/problems/{self.slug}/"
        return self

class ToggleProblemSolvedResponse(BaseModel):
    problem_id: str
    is_solved: bool
    unlocked_new_problem: bool = False
    new_unlocked_problem_title: Optional[str] = None
    unlocked_count: int
    solved_count: int

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

class SimulationRound(BaseModel):
    round_number: int
    name: str
    type: str  # 'oa_dsa', 'ai_project', 'tough_interview'
    time_limit: int
    problem: str
    description: str

class PresetSimulationResponse(BaseModel):
    id: str
    company: str
    title: str
    tier: str
    logo_icon: str
    tagline: str
    duration_minutes: int
    rounds: List[SimulationRound]

