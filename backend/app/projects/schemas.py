from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class ProjectSummary(BaseModel):
    id: str
    title: str
    slug: str
    difficulty: Literal["junior", "mid", "senior", "staff"]
    estimated_minutes: int = 25
    description: str
    tags: List[str] = []
    icon: str = "boxes"
    domain: str

class ProjectDetail(BaseModel):
    id: str
    title: str
    slug: str
    difficulty: Literal["junior", "mid", "senior", "staff"]
    estimated_minutes: int = 25
    description_markdown: str
    repository_files: Dict[str, str]
    editable_files: List[str]
    active_file: str
    instructions: str
    domain: str

class ProjectRunTestsRequest(BaseModel):
    files: Dict[str, str]

class ProjectTestCaseResult(BaseModel):
    name: str
    status: Literal["passed", "failed"]
    duration_ms: int = 0
    error_message: Optional[str] = None
    traceback: Optional[str] = None

class ProjectTestRunResponse(BaseModel):
    status: Literal["passed", "failed", "error"]
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration_ms: int
    test_results: List[ProjectTestCaseResult] = []
    raw_output: str = ""

class ProjectCopilotRequest(BaseModel):
    files: Dict[str, str]
    active_file: Optional[str] = None
    active_cursor_line: Optional[int] = None
    message: str
    conversation_history: List[Dict[str, str]] = []
    last_test_results: Optional[Dict[str, Any]] = None

class ProjectCopilotResponse(BaseModel):
    message: str
    code_suggestions: List[Dict[str, Any]] = []
    tokens_used: int = 0

class PromptEvaluationItem(BaseModel):
    prompt_index: int
    user_prompt: str
    critique: str
    improvement_tip: str
    better_rewrite: str
    is_amateurish: bool = False
    score: int = Field(ge=0, le=100)

class ProjectPromptAnalysisResponse(BaseModel):
    overall_score: int
    grade: str
    rubric_breakdown: Dict[str, int]
    summary: str
    evaluated_prompts: List[PromptEvaluationItem]
    key_takeaways: List[str]

class ProjectSubmissionRequest(BaseModel):
    files: Dict[str, str]
    conversation_history: List[Dict[str, str]] = []
    time_spent_seconds: int = 0

class ProjectSubmissionResponse(BaseModel):
    id: str
    project_id: str
    status: str
    total_tests: int
    passed_tests: int
    prompts_count: int
    prompt_analysis: ProjectPromptAnalysisResponse
    time_spent_seconds: int
    created_at: str
