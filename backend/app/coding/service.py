from dataclasses import asdict
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models import CodingSubmission
from backend.app.coding.schemas import CodeRunRequest, CodeExecutionResponse, TestCaseResultResponse
from backend.app.coding.problems import get_problem, list_problems, CodingProblem
from sandbox.runner import SandboxRunner, TestCase
from backend.app.core.errors import EntityNotFoundError, AppException

class CodingService:
    @classmethod
    async def run_sample_tests(
        cls,
        data: CodeRunRequest
    ) -> CodeExecutionResponse:
        problem = get_problem(data.problem_id)
        if not problem:
            raise EntityNotFoundError("CodingProblem", data.problem_id)

        test_cases = [
            TestCase(stdin=tc["stdin"], expected_stdout=tc["expected_stdout"], is_hidden=False)
            for tc in problem.sample_test_cases
        ]

        result = await SandboxRunner.execute_async(
            language=data.language,
            code=data.code,
            test_cases=test_cases,
        )

        tc_responses = [
            TestCaseResultResponse(**asdict(r)) for r in result.test_results
        ]

        return CodeExecutionResponse(
            status=result.status,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time_ms=result.execution_time_ms,
            total_passed=result.total_passed,
            total_tests=result.total_tests,
            test_results=tc_responses,
        )

    @classmethod
    async def submit_solution(
        cls,
        db: AsyncSession,
        user_id: str,
        data: CodeRunRequest,
        interview_id: Optional[str] = None,
    ) -> CodingSubmission:
        problem = get_problem(data.problem_id)
        if not problem:
            raise EntityNotFoundError("CodingProblem", data.problem_id)

        test_cases = [
            TestCase(stdin=tc["stdin"], expected_stdout=tc["expected_stdout"], is_hidden=tc.get("is_hidden", False))
            for tc in problem.test_cases
        ]

        result = await SandboxRunner.execute_async(
            language=data.language,
            code=data.code,
            test_cases=test_cases,
        )

        test_results_dict = [asdict(r) for r in result.test_results]

        submission = CodingSubmission(
            user_id=user_id,
            interview_id=interview_id,
            problem_title=problem.title,
            language=data.language,
            code=data.code,
            status=result.status,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time_ms=result.execution_time_ms,
            memory_kb=result.memory_kb,
            test_results=test_results_dict,
        )
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        return submission

    @staticmethod
    async def list_user_submissions(db: AsyncSession, user_id: str) -> List[CodingSubmission]:
        res = await db.execute(
            select(CodingSubmission).where(CodingSubmission.user_id == user_id).order_by(CodingSubmission.created_at.desc())
        )
        return list(res.scalars().all())
