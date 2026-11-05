from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


MAX_PROJECT_FILES = 20
MAX_FILE_BYTES = 200_000
MAX_TOTAL_BYTES = 600_000


def _check_files(files: Dict[str, str]) -> Dict[str, str]:
    if len(files) > MAX_PROJECT_FILES:
        raise ValueError(f"At most {MAX_PROJECT_FILES} files per request.")
    total = 0
    for path, content in files.items():
        size = len(content.encode("utf-8", "ignore"))
        if len(path) > 200:
            raise ValueError("File path too long.")
        if size > MAX_FILE_BYTES:
            raise ValueError(f"{path[:80]} is larger than {MAX_FILE_BYTES // 1000} KB.")
        total += size
    if total > MAX_TOTAL_BYTES:
        raise ValueError(f"Files exceed {MAX_TOTAL_BYTES // 1000} KB in total.")
    return files


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

    @field_validator("files")
    @classmethod
    def _limit_files(cls, v):
        return _check_files(v)

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
    integrity_flags: List[str] = []

class ProjectCopilotRequest(BaseModel):
    files: Dict[str, str]
    active_file: Optional[str] = Field(default=None, max_length=200)
    active_cursor_line: Optional[int] = None
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, max_length=200)
    last_test_results: Optional[Dict[str, Any]] = None

    @field_validator("files")
    @classmethod
    def _limit_files(cls, v):
        return _check_files(v)

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
    assessed: bool = True
    scoring_method: str = "heuristic"  # 'heuristic' | 'llm+heuristic' | 'none'
    integrity_flags: List[str] = []

class ProjectSubmissionRequest(BaseModel):
    files: Dict[str, str]
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, max_length=200)
    time_spent_seconds: int = Field(default=0, ge=0, le=24 * 3600)

    @field_validator("files")
    @classmethod
    def _limit_files(cls, v):
        return _check_files(v)

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
