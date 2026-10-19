from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class CodeRunRequest(BaseModel):
    problem_id: str
    language: str = Field(pattern="^(python|java|cpp)$")
    code: str = Field(min_length=1)

class TestCaseResultResponse(BaseModel):
    test_index: int
    passed: bool
    stdin: str
    expected_stdout: str
    actual_stdout: str
    stderr: str
    execution_time_ms: int
    is_hidden: bool

class CodeExecutionResponse(BaseModel):
    status: str  # 'passed', 'failed', 'timeout', 'compile_error', 'runtime_error'
    stdout: str
    stderr: str
    execution_time_ms: int
    total_passed: int
    total_tests: int
    test_results: List[TestCaseResultResponse]

class CodingSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    interview_id: Optional[str] = None
    problem_title: str
    language: str
    status: str
    execution_time_ms: int
    total_passed: int = 0
    total_tests: int = 0
    created_at: datetime
