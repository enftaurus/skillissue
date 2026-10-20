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
    status: str = "passed"
    execution_time_ms: int = 0
    is_hidden: bool = False
    stdin: Optional[str] = None
    expected_stdout: Optional[str] = None
    actual_stdout: Optional[str] = None
    stderr: Optional[str] = None

class CodeExecutionResponse(BaseModel):
    status: str  # 'passed', 'failed', 'timeout', 'compile_error', 'runtime_error', 'output_limit_exceeded'
    stdout: str
    stderr: str
    execution_time_ms: int
    total_passed: int
    total_tests: int
    test_results: List[TestCaseResultResponse]

class CodingProblemPublic(BaseModel):
    id: str
    title: str
    difficulty: str  # 'easy', 'medium', 'hard'
    category: str    # 'arrays', 'strings', 'dp', 'graphs', 'trees', 'stack', etc.
    description: str
    input_format: str
    output_format: str
    constraints: List[str]
    starter_code: Dict[str, str]  # language: code template
    sample_test_cases: List[Dict[str, str]]

class CodingLimitsResponse(BaseModel):
    memory_limit_mb: int = 256
    time_limit_seconds: float = 3.0
    max_output_bytes: int = 1048576
    runtime: str = "runc"
    supported_languages: List[str] = ["python", "cpp", "java"]

class CodingSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    interview_id: Optional[str] = None
    problem_title: str
    language: str
    status: str
    execution_time_ms: int
    tests_passed: int = 0
    tests_total: int = 0
    total_passed: int = 0
    total_tests: int = 0
    test_results: List[TestCaseResultResponse] = []
    created_at: datetime
