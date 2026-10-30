import os
import re
import time
import uuid
import shutil
import tempfile
import subprocess
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.database.models import ProjectSubmission, utc_now
from backend.app.projects.schemas import (
    ProjectTestRunResponse,
    ProjectTestCaseResult,
    ProjectSubmissionRequest,
    ProjectSubmissionResponse,
    ProjectPromptAnalysisResponse,
)
from backend.app.projects.repository import get_project
from backend.app.projects.prompt_evaluator import evaluate_candidate_prompts
from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.core.logging import logger

BASE_SANDBOX_DIR = "/tmp/skillissue_projects"

class ProjectService:
    @classmethod
    def _parse_pytest_output(cls, raw_output: str, duration_ms: int) -> ProjectTestRunResponse:
        """Parse pytest stdout/stderr into structured test results."""
        results: List[ProjectTestCaseResult] = []

        # Find individual test results e.g. tests/test_rate_limiter.py::test_allows_requests_under_limit PASSED
        pattern = re.compile(r"^(tests/[\w/.-]+::(\w+))\s+(PASSED|FAILED|ERROR)", re.MULTILINE)
        matches = pattern.findall(raw_output)

        # Extract failure messages from failure section
        failures_section = ""
        if "=== FAILURES ===" in raw_output:
            failures_section = raw_output.split("=== FAILURES ===")[1]
            if "=== short test summary info ===" in failures_section:
                failures_section = failures_section.split("=== short test summary info ===")[0]

        passed_count = 0
        failed_count = 0

        for full_name, func_name, test_status in matches:
            is_pass = test_status == "PASSED"
            if is_pass:
                passed_count += 1
                error_msg = None
                traceback = None
            else:
                failed_count += 1
                error_msg = f"Test assertion failed in {func_name}"
                traceback = None
                # Try to extract specific traceback for this test
                func_header = f"_{func_name}_"
                if func_header in failures_section:
                    part = failures_section.split(func_header)[1]
                    part = part.split("_____")[0]  # up to next failure header
                    traceback = part.strip()
                    # Find assertion error line
                    for line in traceback.splitlines():
                        if "AssertionError:" in line or "E   " in line:
                            error_msg = line.replace("E   ", "").strip()
                            break

            results.append(ProjectTestCaseResult(
                name=func_name,
                status="passed" if is_pass else "failed",
                duration_ms=0,
                error_message=error_msg,
                traceback=traceback,
            ))

        total_tests = passed_count + failed_count
        overall_status = "passed" if (failed_count == 0 and total_tests > 0) else "failed"
        if total_tests == 0 and "error" in raw_output.lower():
            overall_status = "error"

        return ProjectTestRunResponse(
            status=overall_status,
            total_tests=total_tests,
            passed_tests=passed_count,
            failed_tests=failed_count,
            duration_ms=duration_ms,
            test_results=results,
            raw_output=raw_output,
        )

    @classmethod
    def run_tests_in_sandbox(cls, project_id: str, files: Dict[str, str]) -> ProjectTestRunResponse:
        """
        Execute multi-file repository tests inside isolated sandbox.
        Ensures tests and hidden infrastructure cannot be modified or deleted by the client.
        """
        project = get_project(project_id)
        if not project:
            raise EntityNotFoundError("ProjectChallenge", project_id)

        os.makedirs(BASE_SANDBOX_DIR, exist_ok=True)
        job_dir = tempfile.mkdtemp(prefix=f"job_{project_id}_", dir=BASE_SANDBOX_DIR)

        t_start = time.time()
        try:
            # 1. First write all authoritative repository files (tests, configs, read-only modules)
            merged_files = dict(project.repository_files)
            # 2. Overlay client's edited files for permitted editable files only
            for path, content in files.items():
                if path in project.editable_files or path in project.repository_files:
                    # Prevent client from overwriting test files
                    if not path.startswith("tests/"):
                        merged_files[path] = content

            # Write merged files to ephemeral job_dir
            for rel_path, file_content in merged_files.items():
                dest_path = os.path.join(job_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(file_content)

            # Determine bwrap sandbox availability
            bwrap_bin = shutil.which("bwrap")
            env = dict(os.environ, PYTHONPATH=job_dir)

            if bwrap_bin:
                cmd = [
                    bwrap_bin,
                    "--unshare-all",
                    "--ro-bind", "/", "/",
                    "--dev", "/dev",
                    "--proc", "/proc",
                    "--tmpfs", "/tmp",
                    "--bind", job_dir, job_dir,
                    "--chdir", job_dir,
                    "--unshare-net",
                    "--uid", "65534",
                    "--gid", "65534",
                    "python3", "-m", "pytest", "-o", "pythonpath=.", "-v", "--tb=short", "tests/"
                ]
            else:
                cmd = ["pytest", "-o", "pythonpath=.", "-v", "--tb=short", "tests/"]

            proc = subprocess.run(
                cmd,
                cwd=job_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=12.0
            )
            raw_output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        except subprocess.TimeoutExpired:
            raw_output = "Execution timed out after 12.0s."
        except Exception as e:
            raw_output = f"Execution sandbox error: {str(e)}"
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)

        duration_ms = int((time.time() - t_start) * 1000)
        return cls._parse_pytest_output(raw_output, duration_ms)

    @classmethod
    async def submit_project(
        cls,
        db: AsyncSession,
        user_id: str,
        project_id: str,
        data: ProjectSubmissionRequest
    ) -> ProjectSubmissionResponse:
        project = get_project(project_id)
        if not project:
            raise EntityNotFoundError("ProjectChallenge", project_id)

        # 1. Run final verification CI/CD tests
        test_run = cls.run_tests_in_sandbox(project_id, data.files)
        final_passed = test_run.status == "passed" and test_run.failed_tests == 0

        # 2. Run prompt quality analysis
        prompt_analysis = evaluate_candidate_prompts(
            project_id=project_id,
            conversation_history=data.conversation_history,
            final_test_passed=final_passed,
            time_spent_seconds=data.time_spent_seconds,
        )

        # 3. Persist submission record
        sub_id = str(uuid.uuid4())
        submission = ProjectSubmission(
            id=sub_id,
            user_id=user_id,
            project_id=project_id,
            status="passed" if final_passed else "failed",
            files=data.files,
            test_results=test_run.model_dump(),
            prompt_analysis=prompt_analysis.model_dump(),
            prompts_count=len(prompt_analysis.evaluated_prompts),
            time_spent_seconds=data.time_spent_seconds,
            created_at=utc_now(),
        )
        db.add(submission)
        await db.commit()
        await db.refresh(submission)

        return ProjectSubmissionResponse(
            id=submission.id,
            project_id=project_id,
            status=submission.status,
            total_tests=test_run.total_tests,
            passed_tests=test_run.passed_tests,
            prompts_count=submission.prompts_count,
            prompt_analysis=prompt_analysis,
            time_spent_seconds=submission.time_spent_seconds,
            created_at=submission.created_at.isoformat(),
        )
