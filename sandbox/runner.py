import asyncio
import logging
import os
import time
import uuid
import httpx
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

from sandbox.executor.schemas import ExecuteRequest, TestCase as ExecutorTestCase, CheckerType
from sandbox.executor.docker_manager import DockerSandboxManager
from backend.app.core.errors import SandboxExecutionError

logger = logging.getLogger("sandbox.runner")

@dataclass
class TestCase:
    stdin: str
    expected_stdout: str
    is_hidden: bool = False

@dataclass
class TestCaseResult:
    test_index: int
    passed: bool
    stdin: str
    expected_stdout: str
    actual_stdout: str
    stderr: str
    execution_time_ms: int
    is_hidden: bool = False
    diff: Optional[str] = None

@dataclass
class ExecutionResult:
    status: str  # 'accepted', 'wrong_answer', 'runtime_error', 'time_limit_exceeded', 'memory_limit_exceeded', 'output_limit_exceeded', 'compile_error', 'internal_error'
    stdout: str
    stderr: str
    execution_time_ms: int
    memory_kb: int
    test_results: List[TestCaseResult]
    total_passed: int
    total_tests: int
    compile_output: str = ""

class SandboxRunner:
    TIMEOUT_SECONDS = 3.0
    MAX_MEMORY_MB = 256

    @classmethod
    def get_execution_mode(cls) -> str:
        mode = os.environ.get("SANDBOX_EXECUTION_MODE", "persistent").lower()
        if mode not in ("persistent", "docker", "disabled", "mock"):
            mode = "persistent"
        return mode

    @classmethod
    def execute_submission(
        cls,
        language: str,
        code: str,
        test_cases: List[TestCase],
        checker_type: CheckerType = "exact",
        float_tolerance: float = 1e-6,
    ) -> ExecutionResult:
        mode = cls.get_execution_mode()
        env = os.environ.get("ENVIRONMENT", "development").lower()
        is_production = env == "production"

        # 1. Enforce Fail-Closed Policy in Production
        if is_production and mode not in ("persistent", "docker"):
            raise SandboxExecutionError(
                f"Production requires SANDBOX_EXECUTION_MODE='persistent' or 'docker'. Mode '{mode}' is disallowed in production."
            )

        # 2. Mock mode for unit tests only
        if mode == "mock":
            return cls._execute_mock(language, code, test_cases)

        # 3. Disabled mode
        if mode == "disabled":
            raise SandboxExecutionError("Code execution is currently disabled on this instance.")

        # 4. Real Persistent Sandbox Execution (Default & Production)
        executor_url = os.environ.get("EXECUTOR_URL")
        executor_secret = os.environ.get("EXECUTOR_SECRET", "dev-executor-secret-token-32chars-min!")

        job_id = str(uuid.uuid4())
        executor_test_cases = [
            ExecutorTestCase(
                stdin=tc.stdin,
                expected_stdout=tc.expected_stdout,
                is_hidden=tc.is_hidden,
            )
            for tc in test_cases
        ]
        exec_req = ExecuteRequest(
            job_id=job_id,
            language=language.lower(),  # type: ignore
            code=code,
            test_cases=executor_test_cases,
            checker_type=checker_type,
            float_tolerance=float_tolerance,
            time_limit_seconds=cls.TIMEOUT_SECONDS,
            memory_limit_mb=cls.MAX_MEMORY_MB,
        )

        if executor_url:
            # Delegate to persistent executor microservice
            return cls._call_remote_executor(executor_url, executor_secret, exec_req, test_cases)
        else:
            # Execute via persistent isolated sandbox supervisor
            return cls._call_local_isolated_sandbox(exec_req, test_cases)

    @classmethod
    def _call_remote_executor(
        cls,
        executor_url: str,
        executor_secret: str,
        exec_req: ExecuteRequest,
        test_cases: List[TestCase],
    ) -> ExecutionResult:
        endpoint = f"{executor_url.rstrip('/')}/execute"
        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(
                    endpoint,
                    json=exec_req.model_dump(),
                    headers={"X-Executor-Secret": executor_secret},
                )
                if res.status_code == 429:
                    raise SandboxExecutionError("Execution queue full. Please retry in a few seconds.")
                if res.status_code != 200:
                    raise SandboxExecutionError(f"Executor returned error {res.status_code}: {res.text}")
                data = res.json()
        except httpx.RequestError as e:
            raise SandboxExecutionError(f"Failed to communicate with sandbox executor at {executor_url}: {str(e)}")

        return cls._format_executor_response(data, test_cases)

    @classmethod
    def _call_local_isolated_sandbox(
        cls,
        exec_req: ExecuteRequest,
        test_cases: List[TestCase],
    ) -> ExecutionResult:
        from sandbox.executor.persistent_manager import PersistentSandboxManager
        mgr = PersistentSandboxManager()
        healthy, detail = mgr.is_healthy()
        if not healthy:
            raise SandboxExecutionError(
                f"Persistent isolated code executor is unavailable: {detail}."
            )

        resp = mgr.execute_job(exec_req)
        return cls._format_executor_response(resp.model_dump(), test_cases)


    @classmethod
    def _format_executor_response(cls, data: Dict[str, Any], test_cases: List[TestCase]) -> ExecutionResult:
        status_map = {
            "accepted": "passed",
            "wrong_answer": "failed",
            "runtime_error": "runtime_error",
            "time_limit_exceeded": "timeout",
            "memory_limit_exceeded": "memory_limit_exceeded",
            "output_limit_exceeded": "output_limit_exceeded",
            "compile_error": "compile_error",
            "internal_error": "runtime_error",
        }
        overall_status = status_map.get(data.get("status", "runtime_error"), "runtime_error")

        results: List[TestCaseResult] = []
        raw_test_results = data.get("test_results", [])
        
        for tr in raw_test_results:
            idx = tr.get("test_index", 1)
            t_status = tr.get("status", "failed")
            is_passed = t_status == "passed"
            is_hidden = tr.get("is_hidden", False)
            
            # Fetch corresponding expected stdout
            exp_stdout = "[HIDDEN]"
            inp_stdin = "[HIDDEN]"
            if not is_hidden and idx <= len(test_cases):
                exp_stdout = test_cases[idx - 1].expected_stdout
                inp_stdin = test_cases[idx - 1].stdin

            results.append(TestCaseResult(
                test_index=idx,
                passed=is_passed,
                stdin=inp_stdin,
                expected_stdout=exp_stdout,
                actual_stdout=tr.get("stdout", "") if not is_hidden else ("[MATCH]" if is_passed else "[MISMATCH]"),
                stderr=tr.get("stderr", "") if not is_hidden else "",
                execution_time_ms=tr.get("execution_time_ms", 0),
                is_hidden=is_hidden,
                diff=tr.get("diff"),
            ))

        total_passed = data.get("tests_passed", sum(1 for r in results if r.passed))
        total_tests = data.get("tests_total", len(test_cases))
        peak_mem_kb = max(1024, data.get("peak_memory_bytes", 0) // 1024)

        return ExecutionResult(
            status=overall_status,
            stdout="\n".join([r.actual_stdout for r in results if not r.is_hidden]),
            stderr="\n".join([r.stderr for r in results if r.stderr and not r.is_hidden]),
            execution_time_ms=data.get("execution_time_ms", 0),
            memory_kb=peak_mem_kb,
            test_results=results,
            total_passed=total_passed,
            total_tests=total_tests,
            compile_output=data.get("compile_output", ""),
        )

    @classmethod
    def _execute_mock(cls, language: str, code: str, test_cases: List[TestCase]) -> ExecutionResult:
        # Check for syntax error indicators in code
        if "syntax_error" in code.lower() or "compile_error" in code.lower():
            return ExecutionResult(
                status="compile_error",
                stdout="",
                stderr="Mock compiler error: syntax error on line 1",
                execution_time_ms=10,
                memory_kb=1024,
                test_results=[],
                total_passed=0,
                total_tests=len(test_cases),
                compile_output="Mock compiler error: syntax error on line 1",
            )

        # Check for timeout indicator
        if "while true" in code.lower() or "timeout" in code.lower():
            results = [
                TestCaseResult(
                    test_index=1,
                    passed=False,
                    stdin=test_cases[0].stdin if not test_cases[0].is_hidden else "[HIDDEN]",
                    expected_stdout=test_cases[0].expected_stdout if not test_cases[0].is_hidden else "[HIDDEN]",
                    actual_stdout="",
                    stderr="Execution exceeded timeout limit",
                    execution_time_ms=3000,
                    is_hidden=test_cases[0].is_hidden,
                )
            ]
            return ExecutionResult(
                status="timeout",
                stdout="",
                stderr="Execution exceeded timeout limit of 3.0s",
                execution_time_ms=3000,
                memory_kb=1024,
                test_results=results,
                total_passed=0,
                total_tests=len(test_cases),
            )

        results = []
        for idx, tc in enumerate(test_cases, start=1):
            results.append(TestCaseResult(
                test_index=idx,
                passed=True,
                stdin=tc.stdin if not tc.is_hidden else "[HIDDEN]",
                expected_stdout=tc.expected_stdout if not tc.is_hidden else "[HIDDEN]",
                actual_stdout=tc.expected_stdout if not tc.is_hidden else "[MATCH]",
                stderr="",
                execution_time_ms=15,
                is_hidden=tc.is_hidden,
            ))

        return ExecutionResult(
            status="passed",
            stdout=test_cases[0].expected_stdout if test_cases and not test_cases[0].is_hidden else "",
            stderr="",
            execution_time_ms=45,
            memory_kb=2048,
            test_results=results,
            total_passed=len(test_cases),
            total_tests=len(test_cases),
        )

    @classmethod
    def _execute_host_subprocess_dev_only(cls, language: str, code: str, test_cases: List[TestCase]) -> ExecutionResult:
        # Dev-only fallback behind explicit ALLOW_UNSAFE_HOST_EXECUTION=1
        import tempfile, subprocess, shutil, resource
        temp_dir = tempfile.mkdtemp(prefix="skillissue_unsafe_dev_")
        clean_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": temp_dir,
            "TMPDIR": temp_dir,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        try:
            lang = language.lower()
            if lang in ("python", "py"):
                src = os.path.join(temp_dir, "solution.py")
                with open(src, "w") as f:
                    f.write(code)
                cmd = ["python3", src]
            else:
                return ExecutionResult(
                    status="runtime_error",
                    stdout="",
                    stderr="Host dev runner only supports Python.",
                    execution_time_ms=0,
                    memory_kb=0,
                    test_results=[],
                    total_passed=0,
                    total_tests=len(test_cases),
                )

            results = []
            for idx, tc in enumerate(test_cases, start=1):
                p = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir,
                    env=clean_env,
                )
                try:
                    out, err = p.communicate(input=tc.stdin, timeout=cls.TIMEOUT_SECONDS)
                    passed = (p.returncode == 0) and (out.strip() == tc.expected_stdout.strip())
                    results.append(TestCaseResult(
                        test_index=idx,
                        passed=passed,
                        stdin=tc.stdin if not tc.is_hidden else "[HIDDEN]",
                        expected_stdout=tc.expected_stdout if not tc.is_hidden else "[HIDDEN]",
                        actual_stdout=out.strip() if not tc.is_hidden else ("[MATCH]" if passed else "[MISMATCH]"),
                        stderr=err if not tc.is_hidden else "",
                        execution_time_ms=10,
                        is_hidden=tc.is_hidden,
                    ))
                except subprocess.TimeoutExpired:
                    p.kill()
                    results.append(TestCaseResult(
                        test_index=idx,
                        passed=False,
                        stdin=tc.stdin if not tc.is_hidden else "[HIDDEN]",
                        expected_stdout=tc.expected_stdout if not tc.is_hidden else "[HIDDEN]",
                        actual_stdout="",
                        stderr="Timeout",
                        execution_time_ms=int(cls.TIMEOUT_SECONDS * 1000),
                        is_hidden=tc.is_hidden,
                    ))

            passed_count = sum(1 for r in results if r.passed)
            status = "passed" if passed_count == len(test_cases) else "failed"
            return ExecutionResult(
                status=status,
                stdout="",
                stderr="",
                execution_time_ms=20,
                memory_kb=1024,
                test_results=results,
                total_passed=passed_count,
                total_tests=len(test_cases),
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    async def execute_async(
        cls,
        language: str,
        code: str,
        test_cases: List[TestCase],
        checker_type: CheckerType = "exact",
        float_tolerance: float = 1e-6,
    ) -> ExecutionResult:
        return await asyncio.to_thread(
            cls.execute_submission,
            language,
            code,
            test_cases,
            checker_type,
            float_tolerance,
        )
