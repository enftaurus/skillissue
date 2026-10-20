from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

CheckerType = Literal["exact", "token", "float", "custom"]
ExecutionStatus = Literal[
    "accepted",
    "wrong_answer",
    "runtime_error",
    "time_limit_exceeded",
    "memory_limit_exceeded",
    "output_limit_exceeded",
    "compile_error",
    "internal_error",
]

class TestCase(BaseModel):
    stdin: str = ""
    expected_stdout: str = ""
    is_hidden: bool = False

class ExecuteRequest(BaseModel):
    job_id: str
    language: Literal["python", "java", "cpp"]
    code: str = Field(..., max_length=65536)
    test_cases: List[TestCase]
    checker_type: CheckerType = "exact"
    float_tolerance: float = 1e-6
    time_limit_seconds: float = Field(default=3.0, ge=0.5, le=10.0)
    memory_limit_mb: int = Field(default=256, ge=64, le=1024)

class TestResult(BaseModel):
    test_index: int
    status: Literal["passed", "failed", "time_limit_exceeded", "memory_limit_exceeded", "output_limit_exceeded", "runtime_error"]
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: int = 0
    is_hidden: bool = False
    diff: Optional[str] = None

class ExecuteResponse(BaseModel):
    job_id: str
    status: ExecutionStatus
    execution_time_ms: int = 0
    peak_memory_bytes: int = 0
    tests_passed: int = 0
    tests_total: int = 0
    compile_output: str = ""
    test_results: List[TestResult] = []
    error_message: Optional[str] = None
