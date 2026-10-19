import asyncio
import os
import resource
import shutil
import signal
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
    MAX_OUTPUT_CHARS = 65536  # 64 KB maximum captured output

    @classmethod
    def _set_resource_limits(cls, lang: str = "python"):
        """Set execution constraints for untrusted child process."""
        # Establish isolated session/process group
        try:
            os.setsid()
        except Exception:
            pass

        # CPU limit (seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (int(cls.TIMEOUT_SECONDS), int(cls.TIMEOUT_SECONDS) + 1))
        # Prevent core dumps
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # Address space limit (for Python and C++)
        if lang != "java":
            resource.setrlimit(resource.RLIMIT_AS, (cls.MAX_MEMORY_BYTES, cls.MAX_MEMORY_BYTES))
        # Limit process creation when running under dedicated container user
        if hasattr(resource, 'RLIMIT_NPROC') and os.getuid() == 0:
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
            except Exception:
                pass

    @classmethod
    def execute_submission(
        cls,
        language: str,
        code: str,
        test_cases: List[TestCase],
    ) -> ExecutionResult:
        lang = language.lower()
        temp_dir = tempfile.mkdtemp(prefix="skillissue_sandbox_")

        clean_env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "HOME": temp_dir,
            "TMPDIR": temp_dir,
            "PYTHONPATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

        try:
            # 1. Compile step (if required)
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
                    env=clean_env,
                    cwd=temp_dir,
                )
                if comp.returncode != 0:
                    return ExecutionResult(
                        status="compile_error",
                        stdout="",
                        stderr=comp.stderr[:cls.MAX_OUTPUT_CHARS],
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
                    env=clean_env,
                    cwd=temp_dir,
                )
                if comp.returncode != 0:
                    return ExecutionResult(
                        status="compile_error",
                        stdout="",
                        stderr=comp.stderr[:cls.MAX_OUTPUT_CHARS],
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

            # 2. Execute against all test cases with process group limits
            test_results: List[TestCaseResult] = []
            overall_status = "passed"
            all_stdout = []
            all_stderr = []
            max_time_ms = 0

            for idx, tc in enumerate(test_cases, start=1):
                start = time.time()
                timed_out = False
                stdout = ""
                stderr = ""
                returncode = 0

                p = subprocess.Popen(
                    exec_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir,
                    env=clean_env,
                    preexec_fn=lambda: cls._set_resource_limits(lang),
                )

                try:
                    stdout, stderr = p.communicate(input=tc.stdin, timeout=cls.TIMEOUT_SECONDS)
                    returncode = p.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    # Terminate the entire process tree using process group kill
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
                    try:
                        p.communicate(timeout=0.2)
                    except Exception:
                        pass
                    returncode = -9

                elapsed_ms = int((time.time() - start) * 1000)
                max_time_ms = max(max_time_ms, elapsed_ms)

                # Bound captured outputs
                stdout_bounded = (stdout or "")[:cls.MAX_OUTPUT_CHARS]
                stderr_bounded = (stderr or "")[:cls.MAX_OUTPUT_CHARS]

                if timed_out:
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

                stdout_clean = stdout_bounded.strip()
                expected_clean = tc.expected_stdout.strip()
                passed = (returncode == 0) and (stdout_clean == expected_clean)

                if not passed and overall_status == "passed":
                    overall_status = "runtime_error" if returncode != 0 else "failed"

                test_results.append(
                    TestCaseResult(
                        test_index=idx,
                        passed=passed,
                        stdin=tc.stdin if not tc.is_hidden else "[HIDDEN]",
                        expected_stdout=expected_clean if not tc.is_hidden else "[HIDDEN]",
                        actual_stdout=stdout_clean if not tc.is_hidden else ("[MATCH]" if passed else "[MISMATCH]"),
                        stderr=stderr_bounded,
                        execution_time_ms=elapsed_ms,
                        is_hidden=tc.is_hidden,
                    )
                )
                all_stdout.append(stdout_bounded)
                if stderr_bounded:
                    all_stderr.append(stderr_bounded)

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
