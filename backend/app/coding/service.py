from dataclasses import asdict
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models import CodingSubmission, Interview, UserSkill, utc_now
from backend.app.coding.schemas import CodeRunRequest, CodeExecutionResponse, TestCaseResultResponse
from backend.app.coding.problems import get_problem, list_problems, CodingProblem
from sandbox.runner import SandboxRunner, TestCase
from backend.app.core.errors import EntityNotFoundError, AppException

def sanitize_test_result_dict(r_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure hidden test inputs, outputs, and stack traces are never leaked."""
    clean = dict(r_dict)
    if clean.get("is_hidden"):
        clean["stdin"] = None
        clean["expected_stdout"] = None
        clean["actual_stdout"] = None
        clean["stderr"] = None
    return clean

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
            TestCaseResultResponse(**sanitize_test_result_dict(asdict(r))) for r in result.test_results
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

        # Validate interview ownership to prevent IDOR
        if interview_id:
            inv_res = await db.execute(
                select(Interview).where(Interview.id == interview_id, Interview.user_id == user_id)
            )
            if not inv_res.scalar_one_or_none():
                raise EntityNotFoundError("Interview", interview_id)

        test_cases = [
            TestCase(stdin=tc["stdin"], expected_stdout=tc["expected_stdout"], is_hidden=tc.get("is_hidden", False))
            for tc in problem.test_cases
        ]

        result = await SandboxRunner.execute_async(
            language=data.language,
            code=data.code,
            test_cases=test_cases,
        )

        # Sanitize test results before persisting and returning to candidate
        clean_results_dict = [sanitize_test_result_dict(asdict(r)) for r in result.test_results]

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
            tests_passed=result.total_passed,
            tests_total=result.total_tests,
            test_results=clean_results_dict,
        )
        db.add(submission)

        # If passed, update skill mastery map for the category
        if result.status == "passed" and problem.category:
            await cls._record_skill_progress(db, user_id, problem.category, score=100.0, ref_id=submission.id)

        await db.commit()
        await db.refresh(submission)
        return submission

    @classmethod
    async def _record_skill_progress(
        cls,
        db: AsyncSession,
        user_id: str,
        topic: str,
        score: float,
        ref_id: str
    ):
        """Update or insert UserSkill with exponential moving average."""
        skill_res = await db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.topic == topic)
        )
        skill = skill_res.scalar_one_or_none()
        if skill:
            # EMA with alpha = 0.3
            skill.score = round(0.7 * skill.score + 0.3 * score, 1)
            skill.confidence = min(1.0, round(skill.confidence + 0.1, 2))
            skill.last_seen = utc_now()
            skill.evidence_refs = (skill.evidence_refs or []) + [{"type": "coding", "id": ref_id, "score": score}]
        else:
            skill = UserSkill(
                user_id=user_id,
                topic=topic,
                score=score,
                confidence=0.5,
                last_seen=utc_now(),
                evidence_refs=[{"type": "coding", "id": ref_id, "score": score}]
            )
            db.add(skill)

    @staticmethod
    async def list_user_submissions(db: AsyncSession, user_id: str) -> List[CodingSubmission]:
        res = await db.execute(
            select(CodingSubmission).where(CodingSubmission.user_id == user_id).order_by(CodingSubmission.created_at.desc())
        )
        return list(res.scalars().all())
