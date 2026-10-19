import asyncio
import os
import resource
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

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

@dataclass
class ExecutionResult:
    status: str  # 'passed', 'failed', 'timeout', 'compile_error', 'runtime_error'
    stdout: str
    stderr: str
    execution_time_ms: int
    memory_kb: int
    test_results: List[TestCaseResult]
    total_passed: int
    total_tests: int

class SandboxRunner:
    TIMEOUT_SECONDS = 4.0
    MAX_MEMORY_BYTES = 512 * 1024 * 1024  # 512 MB to support JVM initialization

    @classmethod
    def _set_resource_limits(cls, lang: str = "python"):
        """Set execution constraints for untrusted child process."""
        # CPU limit (seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (int(cls.TIMEOUT_SECONDS), int(cls.TIMEOUT_SECONDS) + 1))
        # Prevent core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # Address space limit (for Python and C++)
        if lang != "java":
            resource.setrlimit(resource.RLIMIT_AS, (cls.MAX_MEMORY_BYTES, cls.MAX_MEMORY_BYTES))

    @classmethod
    def execute_submission(
        cls,
        language: str,
        code: str,
        test_cases: List[TestCase],
    ) -> ExecutionResult:
        lang = language.lower()
        temp_dir = tempfile.mkdtemp(prefix="skillissue_sandbox_")

        try:
            # 1. Compile step (if required)
            compile_err = None
            if lang in ("cpp", "c++"):
                src_path = os.path.join(temp_dir, "solution.cpp")
                bin_path = os.path.join(temp_dir, "solution")
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(code)

                comp = subprocess.run(
                    ["g++", "-O2", "-std=c++17", "-o", bin_path, src_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if comp.returncode != 0:
                    return ExecutionResult(
                        status="compile_error",
                        stdout="",
                        stderr=comp.stderr,
                        execution_time_ms=0,
                        memory_kb=0,
                        test_results=[],
                        total_passed=0,
                        total_tests=len(test_cases),
                    )
                exec_cmd = [bin_path]

            elif lang == "java":
                src_path = os.path.join(temp_dir, "Solution.java")
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(code)

                comp = subprocess.run(
                    ["javac", src_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if comp.returncode != 0:
                    return ExecutionResult(
                        status="compile_error",
                        stdout="",
                        stderr=comp.stderr,
                        execution_time_ms=0,
                        memory_kb=0,
                        test_results=[],
                        total_passed=0,
                        total_tests=len(test_cases),
                    )
                exec_cmd = ["java", "-Xmx128m", "-XX:ReservedCodeCacheSize=32m", "-cp", temp_dir, "Solution"]

            elif lang in ("python", "py"):
                src_path = os.path.join(temp_dir, "solution.py")
                with open(src_path, "w", encoding="utf-8") as f:
                    f.write(code)
                exec_cmd = ["python3", src_path]
            else:
                return ExecutionResult(
                    status="runtime_error",
                    stdout="",
                    stderr=f"Unsupported language: {language}. Supported: python, java, cpp",
                    execution_time_ms=0,
                    memory_kb=0,
                    test_results=[],
                    total_passed=0,
                    total_tests=len(test_cases),
                )

            # 2. Execute against all test cases
            test_results: List[TestCaseResult] = []
            overall_status = "passed"
            all_stdout = []
            all_stderr = []
            max_time_ms = 0

            for idx, tc in enumerate(test_cases, start=1):
                start = time.time()
                try:
                    proc = subprocess.run(
                        exec_cmd,
                        input=tc.stdin,
                        capture_output=True,
                        text=True,
                        timeout=cls.TIMEOUT_SECONDS,
                        cwd=temp_dir,
                        preexec_fn=lambda: cls._set_resource_limits(lang),
                    )
                    elapsed_ms = int((time.time() - start) * 1000)
                    max_time_ms = max(max_time_ms, elapsed_ms)

                    stdout_clean = proc.stdout.strip()
                    expected_clean = tc.expected_stdout.strip()
                    passed = (proc.returncode == 0) and (stdout_clean == expected_clean)

                    if not passed and overall_status == "passed":
                        overall_status = "runtime_error" if proc.returncode != 0 else "failed"

                    test_results.append(
                        TestCaseResult(
                            test_index=idx,
                            passed=passed,
                            stdin=tc.stdin if not tc.is_hidden else "[HIDDEN]",
                            expected_stdout=expected_clean if not tc.is_hidden else "[HIDDEN]",
                            actual_stdout=stdout_clean if not tc.is_hidden else ("[MATCH]" if passed else "[MISMATCH]"),
                            stderr=proc.stderr,
                            execution_time_ms=elapsed_ms,
                            is_hidden=tc.is_hidden,
                        )
                    )
                    all_stdout.append(proc.stdout)
                    if proc.stderr:
                        all_stderr.append(proc.stderr)

                except subprocess.TimeoutExpired:
                    overall_status = "timeout"
                    test_results.append(
                        TestCaseResult(
                            test_index=idx,
                            passed=False,
                            stdin=tc.stdin if not tc.is_hidden else "[HIDDEN]",
                            expected_stdout=tc.expected_stdout if not tc.is_hidden else "[HIDDEN]",
                            actual_stdout="[EXECUTION_TIMEOUT]",
                            stderr=f"Execution exceeded timeout limit of {cls.TIMEOUT_SECONDS}s",
                            execution_time_ms=int(cls.TIMEOUT_SECONDS * 1000),
                            is_hidden=tc.is_hidden,
                        )
                    )
                    break

            total_passed = len([t for t in test_results if t.passed])

            return ExecutionResult(
                status=overall_status,
                stdout="\n".join(all_stdout),
                stderr="\n".join(all_stderr),
                execution_time_ms=max_time_ms,
                memory_kb=1024,
                test_results=test_results,
                total_passed=total_passed,
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
    ) -> ExecutionResult:
        return await asyncio.to_thread(cls.execute_submission, language, code, test_cases)
