import base64
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import docker
from docker.errors import DockerException, APIError
from docker.types import Ulimit

from sandbox.executor.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    TestResult,
    ExecutionStatus,
)
from sandbox.executor.judge import OutputJudge

logger = logging.getLogger("sandbox.docker_manager")

MAX_OUTPUT_BYTES = 1_048_576  # 1 MB max output limit to prevent host memory exhaustion
MAX_COMPILE_OUTPUT_CHARS = 2048

class DockerSandboxManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except DockerException as e:
            self.client = None
            self.docker_error = str(e)

        self.runtime = os.environ.get("SANDBOX_RUNTIME", "runc")
        
        # Locate seccomp profile
        base_dir = Path(__file__).resolve().parent.parent
        self.seccomp_path = str(base_dir / "seccomp.json")

    def is_healthy(self) -> Tuple[bool, str]:
        if not self.client:
            return False, f"Docker client unavailable: {getattr(self, 'docker_error', 'unknown error')}"
        try:
            self.client.ping()
            return True, "Docker daemon connected"
        except Exception as e:
            return False, f"Docker ping failed: {str(e)}"

    def _get_image_for_language(self, language: str) -> str:
        return f"skillissue-sandbox-{language}:latest"

    def _clean_compile_output(self, raw_output: str) -> str:
        cleaned = re.sub(r"/sandbox/", "", raw_output)
        return cleaned[:MAX_COMPILE_OUTPUT_CHARS]

    def _inject_file(self, container, filename: str, content: str):
        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        res = container.exec_run(
            ["sh", "-c", f'echo "{b64}" | base64 -d > /sandbox/{filename}'],
            user="10001:10001",
            workdir="/sandbox",
        )
        if res.exit_code != 0:
            raise RuntimeError(f"Failed to inject {filename} into sandbox tmpfs: {res.output}")

    def execute_job(self, request: ExecuteRequest) -> ExecuteResponse:
        if not self.client:
            return ExecuteResponse(
                job_id=request.job_id,
                status="internal_error",
                error_message=f"Docker is unavailable on executor: {getattr(self, 'docker_error', 'unknown')}",
                tests_total=len(request.test_cases),
            )

        image_tag = self._get_image_for_language(request.language)
        
        source_name = {
            "python": "solution.py",
            "cpp": "solution.cpp",
            "java": "Solution.java",
        }[request.language]

        # Memory limit: Java requires higher default headroom for JVM initialization
        memory_mb = max(request.memory_limit_mb, 512 if request.language == "java" else request.memory_limit_mb)
        
        # Tmpfs flags: python can be noexec, compiled binaries require exec
        exec_flag = "noexec" if request.language == "python" else "exec"
        tmpfs_opts = f"rw,{exec_flag},nosuid,size=64m,uid=10001,gid=10001,mode=0700"

        security_opt = ["no-new-privileges:true"]
        if os.path.exists(self.seccomp_path):
            try:
                with open(self.seccomp_path, "r") as f:
                    seccomp_spec = f.read()
                security_opt.append(f"seccomp={seccomp_spec}")
            except Exception:
                pass

        container = None
        start_time = time.time()
        try:
            # 1. Spawn isolated container with strict container policy
            container = self.client.containers.create(
                image=image_tag,
                command=["sleep", "60"],
                network_mode="none",
                read_only=True,
                user="10001:10001",
                cap_drop=["ALL"],
                security_opt=security_opt,
                mem_limit=f"{memory_mb}m",
                memswap_limit=f"{memory_mb}m",
                nano_cpus=int(1e9),  # 1 CPU core
                pids_limit=64,
                ulimits=[
                    Ulimit(name="nofile", soft=256, hard=256),
                    Ulimit(name="fsize", soft=10_485_760, hard=10_485_760),
                    Ulimit(name="core", soft=0, hard=0),
                ],
                tmpfs={"/sandbox": tmpfs_opts},
                environment={},
                init=True,
                labels={
                    "skillissue.sandbox": "1",
                    "skillissue.job": request.job_id,
                },
                working_dir="/sandbox",
            )
            container.start()

            # 2. Inject source code securely into tmpfs
            self._inject_file(container, source_name, request.code)

            # 3. Compile step (for C++ and Java)
            if request.language == "cpp":
                compile_res = container.exec_run(
                    "g++ -O3 -std=c++17 solution.cpp -o solution",
                    user="10001:10001",
                    workdir="/sandbox",
                )
                if compile_res.exit_code != 0:
                    compile_out = compile_res.output.decode("utf-8", errors="replace")
                    return ExecuteResponse(
                        job_id=request.job_id,
                        status="compile_error",
                        compile_output=self._clean_compile_output(compile_out),
                        tests_total=len(request.test_cases),
                    )
            elif request.language == "java":
                compile_res = container.exec_run(
                    "javac Solution.java",
                    user="10001:10001",
                    workdir="/sandbox",
                )
                if compile_res.exit_code != 0:
                    compile_out = compile_res.output.decode("utf-8", errors="replace")
                    return ExecuteResponse(
                        job_id=request.job_id,
                        status="compile_error",
                        compile_output=self._clean_compile_output(compile_out),
                        tests_total=len(request.test_cases),
                    )

            # Execution command for testcases
            exec_bin = {
                "python": "python3 /sandbox/solution.py",
                "cpp": "/sandbox/solution",
                "java": "java -Xmx256m -Xss1m -cp /sandbox Solution",
            }[request.language]

            test_results: List[TestResult] = []
            overall_status: ExecutionStatus = "accepted"

            # 4. Run test cases sequentially outside untrusted boundary
            for idx, tc in enumerate(request.test_cases, start=1):
                # Inject stdin if present
                in_file = f".in_{idx}"
                self._inject_file(container, in_file, tc.stdin)

                run_cmd = ["sh", "-c", f"{exec_bin} < /sandbox/{in_file}"]

                tc_start = time.time()
                deadline = tc_start + request.time_limit_seconds

                stdout_chunks = []
                stderr_chunks = []
                timed_out = False
                output_exceeded = False
                total_bytes = 0

                exec_stream = container.exec_run(
                    run_cmd,
                    stream=True,
                    demux=True,
                    user="10001:10001",
                    workdir="/sandbox",
                )

                def read_stream():
                    nonlocal timed_out, output_exceeded, total_bytes
                    try:
                        for out_c, err_c in exec_stream.output:
                            if time.time() > deadline:
                                timed_out = True
                                break
                            if out_c:
                                stdout_chunks.append(out_c)
                                total_bytes += len(out_c)
                            if err_c:
                                stderr_chunks.append(err_c)
                                total_bytes += len(err_c)
                            if total_bytes > MAX_OUTPUT_BYTES:
                                output_exceeded = True
                                break
                    except Exception:
                        pass

                reader_thread = threading.Thread(target=read_stream, daemon=True)
                reader_thread.start()
                reader_thread.join(timeout=request.time_limit_seconds + 0.5)

                if reader_thread.is_alive():
                    timed_out = True
                    try:
                        container.kill()
                    except Exception:
                        pass

                tc_elapsed_ms = int((time.time() - tc_start) * 1000)

                # Check container OOM status
                container.reload()
                is_oom = container.attrs.get("State", {}).get("OOMKilled", False)

                raw_stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
                raw_stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")

                if is_oom:
                    tc_status = "memory_limit_exceeded"
                    overall_status = "memory_limit_exceeded"
                elif output_exceeded:
                    tc_status = "output_limit_exceeded"
                    overall_status = "output_limit_exceeded"
                elif timed_out:
                    tc_status = "time_limit_exceeded"
                    overall_status = "time_limit_exceeded"
                else:
                    is_correct = OutputJudge.check(
                        actual=raw_stdout,
                        expected=tc.expected_stdout,
                        checker_type=request.checker_type,
                        float_tolerance=request.float_tolerance,
                    )
                    if is_correct:
                        tc_status = "passed"
                    else:
                        tc_status = "failed"
                        if overall_status == "accepted":
                            overall_status = "wrong_answer"

                diff = OutputJudge.make_diff(
                    actual=raw_stdout,
                    expected=tc.expected_stdout,
                    is_hidden=tc.is_hidden,
                ) if tc_status == "failed" else None

                reported_stdout = "" if tc.is_hidden else raw_stdout
                reported_stderr = "" if tc.is_hidden else raw_stderr

                test_results.append(TestResult(
                    test_index=idx,
                    status=tc_status,
                    stdout=reported_stdout,
                    stderr=reported_stderr,
                    execution_time_ms=tc_elapsed_ms,
                    is_hidden=tc.is_hidden,
                    diff=diff,
                ))

                if overall_status in ("memory_limit_exceeded", "output_limit_exceeded", "time_limit_exceeded"):
                    break

            passed_count = sum(1 for tr in test_results if tr.status == "passed")
            total_elapsed_ms = int((time.time() - start_time) * 1000)

            return ExecuteResponse(
                job_id=request.job_id,
                status=overall_status,
                execution_time_ms=total_elapsed_ms,
                tests_passed=passed_count,
                tests_total=len(request.test_cases),
                test_results=test_results,
            )

        except Exception as e:
            logger.exception("Supervisor execution failure")
            return ExecuteResponse(
                job_id=request.job_id,
                status="internal_error",
                error_message=f"Supervisor execution error: {str(e)}",
                tests_total=len(request.test_cases),
            )
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
