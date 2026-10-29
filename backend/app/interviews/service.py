from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Interview, InterviewMessage, JobDescription, Resume
from backend.app.interviews.schemas import (
    InterviewCreateDomain, InterviewCreateJd, InterviewMessageCreate, HintResponse
)
from backend.app.interviews.prompts import build_interviewer_system_prompt
from backend.app.providers.factory import ModelFactory
from backend.app.providers.service import ProviderConfigService
from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.core.logging import logger

class InterviewService:
    @classmethod
    async def create_domain_interview(
        cls,
        db: AsyncSession,
        user_id: str,
        data: InterviewCreateDomain,
    ) -> Interview:
        # Verify provider configuration
        import os
        from backend.app.providers.service import ProviderConfigService
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        provider_config = await ProviderConfigService.get_config(db, user_id)
        if not is_test and (not provider_config or not provider_config.is_valid):
            raise AppException(
                "A verified AWS Bedrock account is required to start live AI interviews. "
                "Please configure your AWS credentials in Provider Onboarding (/onboarding/bedrock) or Settings.",
                code="BEDROCK_CONFIG_REQUIRED",
                status_code=400,
                details={"action": "onboarding_required", "setup_url": "/onboarding/bedrock"}
            )

        # Load resume if provided
        resume = None
        if data.resume_id:
            res_result = await db.execute(
                select(Resume).where(Resume.id == data.resume_id, Resume.user_id == user_id)
            )
            resume = res_result.scalar_one_or_none()
            if not resume:
                raise EntityNotFoundError("Resume", data.resume_id)

        title = f"{data.category.capitalize()} Interview: {', '.join(data.domain_skills[:3])}"
        interview = Interview(
            user_id=user_id,
            mode="domain",
            category=data.category,
            title=title,
            target_role=data.target_role or "Software Engineer",
            difficulty=data.difficulty or "intermediate",
            status="in_progress",
            domain_skills=data.domain_skills,
            resume_id=data.resume_id,
            coding_problem_id=data.coding_problem_id,
            target_duration_minutes=data.target_duration_minutes or 20,
        )
        db.add(interview)
        await db.flush()


        # Generate initial interview question via LangGraph agent
        from backend.app.interviews.agent.service import InterviewAgentService
        initial_question = await InterviewAgentService.start_interview(
            db=db,
            user_id=user_id,
            interview=interview,
            resume=resume,
            jd=None,
        )

        msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=initial_question,
            question_index=1,
            is_follow_up=False,
        )
        db.add(msg)
        await db.commit()

        return await cls.get_interview(db, user_id, interview.id)

    @classmethod
    async def create_jd_interview(
        cls,
        db: AsyncSession,
        user_id: str,
        data: InterviewCreateJd,
    ) -> Interview:
        # Verify provider configuration
        import os
        from backend.app.providers.service import ProviderConfigService
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        provider_config = await ProviderConfigService.get_config(db, user_id)
        if not is_test and (not provider_config or not provider_config.is_valid):
            raise AppException(
                "A verified AWS Bedrock account is required to start live AI interviews. "
                "Please configure your AWS credentials in Provider Onboarding (/onboarding/bedrock) or Settings.",
                code="BEDROCK_CONFIG_REQUIRED",
                status_code=400,
                details={"action": "onboarding_required", "setup_url": "/onboarding/bedrock"}
            )

        # Load JD
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == data.jd_id, JobDescription.user_id == user_id)
        )
        jd = jd_result.scalar_one_or_none()
        if not jd:
            raise EntityNotFoundError("JobDescription", data.jd_id)

        # Load optional resume
        resume = None
        if data.resume_id:
            res_result = await db.execute(
                select(Resume).where(Resume.id == data.resume_id, Resume.user_id == user_id)
            )
            resume = res_result.scalar_one_or_none()
            if not resume:
                raise EntityNotFoundError("Resume", data.resume_id)

        title = f"JD Interview: {jd.title}"
        if jd.company:
            title += f" @ {jd.company}"

        interview = Interview(
            user_id=user_id,
            mode="jd",
            category=data.category,
            title=title,
            target_role=jd.extracted_role or jd.title,
            difficulty=data.difficulty or "intermediate",
            status="in_progress",
            domain_skills=jd.extracted_skills,
            jd_id=jd.id,
            resume_id=data.resume_id,
            coding_problem_id=data.coding_problem_id,
            target_duration_minutes=data.target_duration_minutes or 20,
        )
        db.add(interview)
        await db.flush()

        # Generate initial interview question via LangGraph agent
        from backend.app.interviews.agent.service import InterviewAgentService
        initial_question = await InterviewAgentService.start_interview(
            db=db,
            user_id=user_id,
            interview=interview,
            resume=resume,
            jd=jd,
        )

        msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=initial_question,
            question_index=1,
            is_follow_up=False,
        )
        db.add(msg)
        await db.commit()

        return await cls.get_interview(db, user_id, interview.id)

    @classmethod
    async def send_message(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
        content: str,
        client_turn_id: Optional[str] = None,
    ) -> InterviewMessage:
        result = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id, Interview.user_id == user_id)
            .with_for_update()
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise EntityNotFoundError("Interview", interview_id)

        if interview.status != "in_progress":
            raise AppException("Interview is no longer active", code="INTERVIEW_NOT_ACTIVE")

        # 1. Turn idempotency check by client_turn_id
        if client_turn_id:
            existing_user_msg = (
                await db.execute(
                    select(InterviewMessage).where(
                        InterviewMessage.interview_id == interview_id,
                        InterviewMessage.client_turn_id == client_turn_id,
                    )
                )
            ).scalar_one_or_none()
            if existing_user_msg:
                # Find the assistant response that answered this turn
                subsequent_assistant_msg = (
                    await db.execute(
                        select(InterviewMessage).where(
                            InterviewMessage.interview_id == interview_id,
                            InterviewMessage.role == "assistant",
                            InterviewMessage.created_at >= existing_user_msg.created_at,
                            InterviewMessage.id != existing_user_msg.id,
                        ).order_by(InterviewMessage.created_at.asc())
                    )
                ).scalars().first()
                if subsequent_assistant_msg:
                    logger.info(f"Idempotent hit for client_turn_id={client_turn_id}. Returning existing assistant response.")
                    return subsequent_assistant_msg

        # 2. Duplicate submission protection within active turn
        last_msg = interview.messages[-1] if interview.messages else None
        if last_msg and last_msg.role == "user" and last_msg.content.strip() == content.strip():
            logger.info("Duplicate user message in active turn detected. Reusing existing message.")
            user_msg = last_msg
        else:
            # Save user message
            user_msg = InterviewMessage(
                interview_id=interview.id,
                role="user",
                content=content,
                client_turn_id=client_turn_id,
                question_index=len([m for m in interview.messages if m.role == "assistant"]),
                is_follow_up=False,
            )
            db.add(user_msg)
            await db.flush()

        # Check turn limit (auto-wrapup at 8 turns)
        candidate_turns = len([m for m in interview.messages if m.role == "user"])
        if candidate_turns >= 8:
            wrapup_text = (
                "That concludes our interview session. Thank you for your concrete explanations and trade-off walkthroughs. "
                "We now have enough diagnostic data to assess your engineering readiness across all rubric dimensions."
            )
            assistant_msg = InterviewMessage(
                interview_id=interview.id,
                role="assistant",
                content=wrapup_text,
                question_index=len([m for m in interview.messages if m.role == "assistant"]) + 1,
                is_follow_up=False,
            )
            interview.status = "completed"
            interview.completed_at = datetime.now(timezone.utc)
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # Load context for agent
        jd = None
        if interview.jd_id:
            jd_res = await db.execute(select(JobDescription).where(JobDescription.id == interview.jd_id, JobDescription.user_id == user_id))
            jd = jd_res.scalar_one_or_none()

        resume = None
        if interview.resume_id:
            res_res = await db.execute(select(Resume).where(Resume.id == interview.resume_id, Resume.user_id == user_id))
            resume = res_res.scalar_one_or_none()

        # Process turn through LangGraph agent
        from backend.app.interviews.agent.service import InterviewAgentService
        agent_result = await InterviewAgentService.process_turn(
            db=db,
            user_id=user_id,
            interview=interview,
            candidate_content=content,
            candidate_message_id=user_msg.id,
            client_turn_id=client_turn_id,
            resume=resume,
            jd=jd,
        )

        assistant_text = agent_result["assistant_content"]
        is_follow_up = (agent_result.get("next_action") == "ask_follow_up")
        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=assistant_text,
            question_index=len([m for m in interview.messages if m.role == "assistant"]) + 1,
            is_follow_up=is_follow_up,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        return assistant_msg

    @staticmethod
    def compute_grouped_transcript(messages: List[InterviewMessage]) -> List[dict]:
        turns: List[dict] = []
        sorted_msgs = sorted(messages, key=lambda m: (m.created_at or datetime.min, m.id))

        current_turn: Optional[dict] = None
        q_idx = 1

        for msg in sorted_msgs:
            if msg.role == "assistant":
                if current_turn:
                    turns.append(current_turn)
                current_turn = {
                    "question_index": q_idx,
                    "interviewer_question": msg.content,
                    "candidate_answer": "",
                    "is_follow_up": bool(msg.is_follow_up),
                    "assistant_message_id": msg.id,
                    "user_message_id": None,
                }
                q_idx += 1
            elif msg.role == "user" and current_turn:
                current_turn["candidate_answer"] = msg.content
                current_turn["user_message_id"] = msg.id
                turns.append(current_turn)
                current_turn = None

        if current_turn:
            turns.append(current_turn)

        return turns

    @staticmethod
    async def end_interview(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
        interview = await InterviewService.get_interview(db, user_id, interview_id)
        if interview.status == "in_progress":
            interview.status = "completed"
            interview.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(interview)
        return interview

    @classmethod
    async def get_interview(cls, db: AsyncSession, user_id: str, interview_id: str) -> Interview:
        result = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id, Interview.user_id == user_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise EntityNotFoundError("Interview", interview_id)
        interview.grouped_transcript = cls.compute_grouped_transcript(interview.messages)
        return interview

    @classmethod
    async def get_grouped_transcript(
        cls, db: AsyncSession, user_id: str, interview_id: str
    ) -> List[dict]:
        interview = await cls.get_interview(db, user_id, interview_id)
        return interview.grouped_transcript or []

    @staticmethod
    async def list_interviews(db: AsyncSession, user_id: str) -> List[Interview]:
        result = await db.execute(
            select(Interview)
            .where(Interview.user_id == user_id)
            .order_by(Interview.created_at.desc())
        )
        return list(result.scalars().all())

    @classmethod
    async def request_hint(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
        level: int,
        problem_id: Optional[str] = None,
        current_code: Optional[str] = None,
    ) -> HintResponse:
        interview = await cls.get_interview(db, user_id, interview_id)
        if interview.status != "in_progress":
            raise AppException("Cannot request hint on a completed interview", code="INTERVIEW_ALREADY_COMPLETED")

        if level not in (1, 2, 3):
            raise AppException("Hint level must be 1, 2, or 3", code="INVALID_HINT_LEVEL")

        target_prob_id = problem_id or interview.coding_problem_id
        problem = None
        if target_prob_id:
            from backend.app.coding.problems import get_problem
            problem = get_problem(target_prob_id)

        penalty_pct = 5 if level == 1 else (15 if level == 2 else 30)

        tier_instructions = {
            1: "Tier 1: Provide a clarifying question or subtle directional nudge without naming specific data structures or algorithms.",
            2: "Tier 2: Reveal the core algorithmic pattern or optimal data structure (e.g., Two-Pointer, Hash Map, DP state representation) and explain why it fits.",
            3: "Tier 3: Provide concrete pseudocode or structural step-by-step logic to implement the solution, but do not write finished code."
        }
        tier_desc = tier_instructions[level]

        prob_context = f"Problem: {problem.title}\nDescription: {problem.description}" if problem else f"Interview Category: {interview.category}"
        code_context = f"\nCandidate's Current Code:\n{current_code}" if current_code else ""

        prompt = (
            f"The candidate requested a Hint Level {level} during their technical coding round.\n"
            f"{tier_desc}\n\n"
            f"{prob_context}\n"
            f"{code_context}\n\n"
            "Provide the Socratic hint in 2-3 concise, direct sentences in a calm, professional engineering tone."
        )
        system_prompt = "You are a senior technical interviewer providing calibrated Socratic guidance to an engineering candidate."

        provider = await ModelFactory.get_for_user(db, user_id, task_type="coding")
        response = await provider.generate_text(prompt=prompt, system_prompt=system_prompt)
        hint_text = response.text.strip()

        prob_name = problem.title if problem else "Problem"
        user_msg = InterviewMessage(
            interview_id=interview.id,
            role="user",
            content=f"[Requested Level {level} Hint for {prob_name}]",
            question_index=len(interview.messages) + 1,
            is_follow_up=False,
        )
        db.add(user_msg)

        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=f"[Level {level} Hint]: {hint_text}",
            question_index=len(interview.messages) + 2,
            is_follow_up=False,
        )
        db.add(assistant_msg)

        interview.hint_level_used = max(interview.hint_level_used, level)
        if target_prob_id and not interview.coding_problem_id:
            interview.coding_problem_id = target_prob_id

        await db.commit()
        await db.refresh(assistant_msg)

        await ProviderConfigService.record_usage(
            db, user_id, response.input_tokens + response.output_tokens, response.estimated_cost_usd
        )

        return HintResponse(
            level=level,
            hint=hint_text,
            penalty_pct=penalty_pct,
            total_hint_level_used=interview.hint_level_used,
            message_id=assistant_msg.id,
        )

    @classmethod
    async def get_interview_state(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieves live inspectable state and memory representation for frontend/debug inspection.
        """
        interview = await cls.get_interview(db, user_id, interview_id)
        from backend.app.interviews.agent.service import InterviewAgentService
        return await InterviewAgentService.get_state_snapshot(db, user_id, interview)

    @classmethod
    async def submit_coding_turn(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
        language: str,
        code: str,
        run_mode: str = "submit",  # 'run' or 'submit'
        client_turn_id: Optional[str] = None,
        candidate_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes candidate code in isolated Docker sandbox, logs structured submission results,
        appends a formatted turn to the interview transcript, and invokes the LangGraph agent
        to discuss correctness, edge cases, and complexity.
        """
        result = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id, Interview.user_id == user_id)
            .with_for_update()
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise EntityNotFoundError("Interview", interview_id)

        if interview.status != "in_progress":
            raise AppException("Interview is no longer active", code="INTERVIEW_NOT_ACTIVE")

        problem_id = interview.coding_problem_id or "two-sum"

        # 1. Execute code via isolated coding service
        from backend.app.coding.service import CodingService
        from backend.app.coding.schemas import CodeRunRequest

        if run_mode == "run":
            exec_res = await CodingService.run_sample_tests(
                data=CodeRunRequest(problem_id=problem_id, language=language, code=code)
            )
            submission_data = {
                "status": exec_res.status,
                "tests_passed": exec_res.total_passed,
                "tests_total": exec_res.total_tests,
                "execution_time_ms": exec_res.execution_time_ms,
                "stdout": exec_res.stdout,
                "stderr": exec_res.stderr,
                "submission_id": None,
            }
        else:
            sub = await CodingService.submit_solution(
                db=db,
                user_id=user_id,
                data=CodeRunRequest(problem_id=problem_id, language=language, code=code),
                interview_id=interview.id,
            )
            interview.latest_submission_id = sub.id
            submission_data = {
                "status": sub.status,
                "tests_passed": sub.tests_passed,
                "tests_total": sub.tests_total,
                "execution_time_ms": sub.execution_time_ms,
                "stdout": sub.stdout,
                "stderr": sub.stderr,
                "submission_id": sub.id,
            }

        # 2. Format candidate message containing code & execution results
        status_label = submission_data["status"].upper()
        tests_summary = f"{submission_data['tests_passed']}/{submission_data['tests_total']} tests passed"
        diag_output = ""
        if submission_data["stderr"]:
            diag_output = f"\nError Output:\n```\n{submission_data['stderr'][:300]}\n```"
        elif submission_data["stdout"] and submission_data["status"] != "passed":
            diag_output = f"\nOutput:\n```\n{submission_data['stdout'][:300]}\n```"

        notes_part = f"\nCandidate Notes: {candidate_notes.strip()}" if candidate_notes else ""

        message_content = (
            f"[Candidate Code Submission — {language.upper()}]\n"
            f"```{language}\n{code}\n```\n"
            f"Execution Status: {status_label} ({tests_summary}){diag_output}{notes_part}"
        )

        user_msg = InterviewMessage(
            interview_id=interview.id,
            role="user",
            content=message_content,
            client_turn_id=client_turn_id,
            question_index=len([m for m in interview.messages if m.role == "assistant"]),
            is_follow_up=False,
        )
        db.add(user_msg)
        await db.flush()

        # 3. Invoke LangGraph agent with structured execution context
        from backend.app.interviews.agent.service import InterviewAgentService
        turn_result = await InterviewAgentService.process_turn(
            db=db,
            user_id=user_id,
            interview=interview,
            candidate_content=message_content,
            candidate_message_id=user_msg.id,
            client_turn_id=client_turn_id,
        )

        assistant_content = turn_result["assistant_content"]
        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=assistant_content,
            question_index=len([m for m in interview.messages if m.role == "assistant"]) + 1,
            is_follow_up=turn_result.get("is_follow_up", False),
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        return {
            "execution": submission_data,
            "assistant_message": assistant_msg,
        }


