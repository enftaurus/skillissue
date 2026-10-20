import os
import sys
import shutil
import subprocess
import signal
import time
import resource
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Generator

from sandbox.executor.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    TestResult,
    ExecutionStatus,
)
from sandbox.executor.judge import OutputJudge
from backend.app.core.logging import logger

MAX_OUTPUT_BYTES = 1_048_576  # 1 MB max output limit to prevent host memory exhaustion
MAX_COMPILE_OUTPUT_CHARS = 2048
BASE_SANDBOX_DIR = "/tmp/skillissue_sandbox"

class PersistentSandboxManager:
    """
    Persistent Sandbox Execution Supervisor using Bubblewrap (bwrap).
    
    Security Invariants:
    1. Unprivileged namespaces: unshare all (mount, net, pid, ipc, uts, user).
    2. Strict unprivileged identity: executes as nobody:nogroup (UID/GID 65534).
    3. Read-only rootfs (--ro-bind / /), isolated /dev and /proc, private /tmp tmpfs.
    4. Ephemeral job workspace bound strictly to /tmp/skillissue_sandbox/job_{id}.
    5. No network access (--unshare-net).
    6. Complete process tree teardown via process group SIGKILL.
    7. Hard resource limits: CPU timeout, memory limits, process-count bounds, output caps.
    """

    def __init__(self):
        Path(BASE_SANDBOX_DIR).mkdir(parents=True, exist_ok=True)
        # Purge any stale directories left behind by previous crashes or restarts
        try:
            for item in os.listdir(BASE_SANDBOX_DIR):
                item_path = os.path.join(BASE_SANDBOX_DIR, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up stale sandbox directories: {e}")

        self.isolate_bin = shutil.which("isolate")
        self.bwrap_bin = shutil.which("bwrap")
        self.python_bin = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else (shutil.which("python3") or sys.executable)
        self.gpp_bin = shutil.which("g++")
        self.javac_bin = shutil.which("javac")
        self.java_bin = shutil.which("java")

        if self.isolate_bin:
            self.runtime = "isolate"
        elif self.bwrap_bin:
            self.runtime = "bubblewrap"
        else:
            self.runtime = "posix_rlimit"

        logger.info(f"PersistentSandboxManager initialized with runtime: {self.runtime}")

    def is_healthy(self) -> Tuple[bool, str]:
        missing = []
        if not self.python_bin:
            missing.append("python3")
        if not self.gpp_bin:
            missing.append("g++")
        if not self.javac_bin or not self.java_bin:
            missing.append("openjdk (javac/java)")

        if missing:
            return False, f"Missing language toolchains on persistent executor: {', '.join(missing)}"

        return True, f"Persistent executor healthy. Runtime: {self.runtime}"

    def _clean_compile_output(self, raw_output: str, job_dir: str) -> str:
        cleaned = raw_output.replace(job_dir, "/sandbox")
        return cleaned[:MAX_COMPILE_OUTPUT_CHARS]

    def _wrap_bwrap(self, cmd: List[str], job_dir: str, max_procs: int = 64) -> List[str]:
        """
        Wrap command with hardened Bubblewrap isolation and process limiting.
        Applies ulimit -u (RLIMIT_NPROC) specifically to the unprivileged UID (65534).
        """
        if not self.bwrap_bin:
            return cmd

        bwrap_prefix = [
            self.bwrap_bin,
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--ro-bind", "/", "/",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--bind", job_dir, job_dir,
            "--chdir", job_dir,
            "--unshare-net",
            "--uid", "65534",
            "--gid", "65534",
        ]
        bash_wrapper = [
            "/bin/bash",
            "-c",
            f"ulimit -u {max_procs}; exec \"$@\"",
            "--",
        ] + cmd
        return bwrap_prefix + bash_wrapper

    def _compile_job(self, request: ExecuteRequest, job_dir: str) -> Tuple[bool, str]:
        """Compiles C++ and Java sources under strict sandboxing, process limits, and timeouts."""
        def _set_compile_limits():
            os.setsid()
            resource.setrlimit(resource.RLIMIT_CPU, (10, 12))
            resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
            if request.language != "java":
                try:
                    # 1GB virtual memory ceiling during compilation for C++ and Python
                    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
                except (ValueError, OSError):
                    pass

        if request.language == "python":
            source_file = os.path.join(job_dir, "solution.py")
            cmd = self._wrap_bwrap([self.python_bin, "-m", "py_compile", source_file], job_dir)
            timeout = 5.0
        elif request.language == "cpp":
            source_file = os.path.join(job_dir, "solution.cpp")
            binary_file = os.path.join(job_dir, "solution.out")
            raw_cmd = [
                self.gpp_bin,
                "-O2",
                "-std=c++20",
                "-fno-asm",
                "-Wall",
                source_file,
                "-o",
                binary_file,
            ]
            cmd = self._wrap_bwrap(raw_cmd, job_dir)
            timeout = 10.0
        elif request.language == "java":
            source_file = os.path.join(job_dir, "Solution.java")
            raw_cmd = [self.javac_bin, "-J-Xmx512m", source_file]
            cmd = self._wrap_bwrap(raw_cmd, job_dir)
            timeout = 10.0
        else:
            return False, f"Unsupported language: {request.language}"

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=job_dir,
                preexec_fn=_set_compile_limits,
            )
            raw_out, raw_err = proc.communicate(timeout=timeout)
            if proc.returncode != 0:
                err_text = raw_err.decode("utf-8", errors="replace")
                return False, self._clean_compile_output(err_text, job_dir)
            return True, ""
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
            return False, f"Compilation timed out after {int(timeout)} seconds."
        except Exception as e:
            return False, f"Compilation setup error: {str(e)}"

    def _get_run_command(self, request: ExecuteRequest, job_dir: str) -> List[str]:
        if request.language == "python":
            return [self.python_bin, "-u", "solution.py"]
        elif request.language == "cpp":
            return ["./solution.out"]
        elif request.language == "java":
            mem_mb = max(request.memory_limit_mb, 256)
            return [self.java_bin, f"-Xmx{mem_mb}m", "-Xms64m", "-XX:+UseSerialGC", "Solution"]
        return []

    def _execute_single_test(
        self,
        request: ExecuteRequest,
        job_dir: str,
        test_index: int,
        stdin_input: str,
        expected_output: str,
        is_hidden: bool,
    ) -> TestResult:
        run_cmd = self._get_run_command(request, job_dir)
        time_limit = request.time_limit_seconds
        mem_limit_bytes = int(request.memory_limit_mb * 1024 * 1024)

        isolated_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "PYTHONUNBUFFERED": "1",
            "HOME": job_dir,
            "TMPDIR": "/tmp",
        }

        cmd = self._wrap_bwrap(run_cmd, job_dir)

        def _set_resource_limits():
            os.setsid()
            resource.setrlimit(resource.RLIMIT_CPU, (int(time_limit) + 1, int(time_limit) + 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
            if request.language != "java":
                try:
                    effective_mem = max(mem_limit_bytes, 128 * 1024 * 1024)
                    resource.setrlimit(resource.RLIMIT_AS, (effective_mem, effective_mem))
                except (ValueError, OSError):
                    pass

        start_time = time.perf_counter()
        proc = None
        timed_out = False
        output_exceeded = False
        status: str = "failed"
        stdout_text = ""
        stderr_text = ""

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=job_dir,
                env=isolated_env,
                preexec_fn=_set_resource_limits,
            )

            try:
                raw_out, raw_err = proc.communicate(
                    input=stdin_input.encode("utf-8"),
                    timeout=time_limit,
                )
                if len(raw_out) > MAX_OUTPUT_BYTES or len(raw_err) > MAX_OUTPUT_BYTES:
                    output_exceeded = True

                stdout_text = raw_out.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
                stderr_text = raw_err.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
                try:
                    proc.kill()
                    proc.communicate(timeout=1.0)
                except Exception:
                    pass

        except Exception as e:
            stderr_text = f"Execution setup error: {str(e)}"
        finally:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Evaluate outcome
        if timed_out:
            status = "time_limit_exceeded"
        elif output_exceeded:
            status = "output_limit_exceeded"
            stderr_text = f"Output size exceeded limit of {MAX_OUTPUT_BYTES // (1024 * 1024)} MB.\n" + stderr_text
        elif proc and proc.returncode != 0:
            if proc.returncode == -signal.SIGXCPU or proc.returncode == 137:
                status = "time_limit_exceeded"
            elif proc.returncode == -signal.SIGSEGV:
                status = "runtime_error"
                stderr_text += "\n[Segmentation fault (core dumped)]"
            elif "MemoryError" in stderr_text or "std::bad_alloc" in stderr_text:
                status = "memory_limit_exceeded"
            else:
                status = "runtime_error"
        else:
            if "MemoryError" in stderr_text or "std::bad_alloc" in stderr_text:
                status = "memory_limit_exceeded"
            else:
                passed = OutputJudge.check(
                    actual=stdout_text,
                    expected=expected_output,
                    checker_type=request.checker_type,
                    float_tolerance=request.float_tolerance,
                )
                status = "passed" if passed else "failed"

        diff = None
        if status == "failed" and not is_hidden:
            diff = OutputJudge.make_diff(stdout_text, expected_output, is_hidden=False)

        return TestResult(
            test_index=test_index,
            status=status,
            stdout="" if is_hidden else stdout_text,
            stderr="" if is_hidden else stderr_text,
            execution_time_ms=elapsed_ms,
            is_hidden=is_hidden,
            diff=diff,
        )

    def execute_job_streaming(self, request: ExecuteRequest) -> Generator[Dict[str, Any], None, None]:
        """
        Executes submission and yields real incremental events as each test case runs.
        """
        # Sanitize job_id to prevent any directory traversal attacks
        safe_job_id = "".join(c for c in request.job_id if c.isalnum() or c in ("-", "_")) or "job"
        job_dir = os.path.join(BASE_SANDBOX_DIR, f"job_{safe_job_id}")
        os.makedirs(job_dir, exist_ok=True)

        yield {"event": "queued", "job_id": request.job_id}

        try:
            source_filename = {
                "python": "solution.py",
                "cpp": "solution.cpp",
                "java": "Solution.java",
            }[request.language]

            with open(os.path.join(job_dir, source_filename), "w", encoding="utf-8") as f:
                f.write(request.code)

            yield {"event": "compiling", "job_id": request.job_id}
            compile_ok, compile_err = self._compile_job(request, job_dir)

            if not compile_ok:
                resp = ExecuteResponse(
                    job_id=request.job_id,
                    status="compile_error",
                    compile_output=compile_err,
                    tests_total=len(request.test_cases),
                    tests_passed=0,
                )
                yield {"event": "done", "response": resp.model_dump()}
                return

            test_results: List[TestResult] = []
            overall_status: ExecutionStatus = "accepted"
            total_time_ms = 0

            for idx, tc in enumerate(request.test_cases, start=1):
                tr = self._execute_single_test(
                    request=request,
                    job_dir=job_dir,
                    test_index=idx,
                    stdin_input=tc.stdin,
                    expected_output=tc.expected_stdout,
                    is_hidden=tc.is_hidden,
                )
                test_results.append(tr)
                total_time_ms += tr.execution_time_ms

                yield {"event": "test_result", "result": tr.model_dump()}

                if tr.status != "passed" and overall_status == "accepted":
                    status_mapping = {
                        "failed": "wrong_answer",
                        "time_limit_exceeded": "time_limit_exceeded",
                        "memory_limit_exceeded": "memory_limit_exceeded",
                        "output_limit_exceeded": "output_limit_exceeded",
                        "runtime_error": "runtime_error",
                    }
                    overall_status = status_mapping.get(tr.status, "runtime_error")

            passed_count = sum(1 for tr in test_results if tr.status == "passed")
            final_resp = ExecuteResponse(
                job_id=request.job_id,
                status=overall_status,
                execution_time_ms=total_time_ms,
                tests_passed=passed_count,
                tests_total=len(request.test_cases),
                test_results=test_results,
            )
            yield {"event": "done", "response": final_resp.model_dump()}

        finally:
            shutil.rmtree(job_dir, ignore_errors=True)

    def execute_job(self, request: ExecuteRequest) -> ExecuteResponse:
        final_response: Optional[ExecuteResponse] = None
        for event in self.execute_job_streaming(request):
            if event.get("event") == "done":
                final_response = ExecuteResponse.model_validate(event.get("response"))

        if not final_response:
            return ExecuteResponse(
                job_id=request.job_id,
                status="internal_error",
                error_message="Sandbox execution finished without response",
                tests_total=len(request.test_cases),
            )
        return final_response
