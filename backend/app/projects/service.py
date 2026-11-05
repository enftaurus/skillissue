import asyncio
import uuid
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
from backend.app.projects.sandbox import run_project_tests
from backend.app.projects.copilot import load_session_prompts, judge_prompts
from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.core.logging import logger

class ProjectService:
    @classmethod
    def run_tests_in_sandbox(cls, project_id: str, files: Dict[str, str]) -> ProjectTestRunResponse:
        """
        Execute the project's authoritative test suite against the candidate's editable files
        inside the hardened sandbox (see backend/app/projects/sandbox.py).
        """
        project = get_project(project_id)
        if not project:
            raise EntityNotFoundError("ProjectChallenge", project_id)

        run = run_project_tests(project.repository_files, project.editable_files, files)
        results: List[ProjectTestCaseResult] = [
            ProjectTestCaseResult(name=name, status="passed", duration_ms=0) for name in run.passed
        ] + [
            ProjectTestCaseResult(name=name, status="failed", duration_ms=0, error_message=msg, traceback=tb or None)
            for name, (msg, tb) in run.failed.items()
        ]
        return ProjectTestRunResponse(
            status=run.status,
            total_tests=len(results),
            passed_tests=len(run.passed),
            failed_tests=len(run.failed),
            duration_ms=run.duration_ms,
            test_results=results,
            raw_output=run.raw_output,
            integrity_flags=run.integrity_flags,
        )

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
        test_run = await asyncio.to_thread(cls.run_tests_in_sandbox, project_id, data.files)
        final_passed = test_run.status == "passed" and test_run.failed_tests == 0

        # 2. Run prompt quality analysis
        # Score the server-side copilot log; client-supplied history is ignored.
        server_history = await load_session_prompts(db, user_id, project_id)
        prompt_analysis = await judge_prompts(db, user_id, project_id, server_history, final_passed)

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
