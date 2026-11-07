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
from backend.app.core.errors import EntityNotFoundError, AppException, translate_model_error
from backend.app.core.logging import logger

def _assistant_kind(result: Dict[str, Any], default: str) -> str:
    if result.get("is_completed"):
        return "wrapup"
    if result.get("next_action") == "invite_questions":
        return "closing"
    return default


def _clip(text: str, limit: int) -> str:
    """Fit a derived string into its column (titles are built from user/JD text and used to 500 when too long)."""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


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
        picker_skills = list(data.domain_skills)
        from backend.app.tracks.company_context import (company_by_name, company_title, get_company,
                                                        picker_skills as company_skills)
        company = None
        company_name = (data.company_name or "").replace("\x00", "").strip() or None
        if data.company_slug:
            company = get_company(data.company_slug)
            if company is None:
                raise EntityNotFoundError("Company", data.company_slug)
        elif company_name:
            company = company_by_name(company_name)
        if company:
            company_name = company["name"]
            title = company_title(company, data.category)
            picker_skills = company_skills(company) + picker_skills
        elif company_name:
            title = f"{company_name} · {data.category.capitalize()} mock interview"
        coding_prob_id = data.coding_problem_id
        if data.category == "dsa" and not coding_prob_id:
            # Only curated problems have a full statement and real test cases. Live Codeforces
            # stubs have neither, so the interviewer can't discuss them and empty code "passes".
            from backend.app.coding.problems import pick_curated_interview_problem
            coding_prob_id = pick_curated_interview_problem(picker_skills, data.difficulty)

        interview = Interview(
            user_id=user_id,
            mode="domain",
            category=data.category,
            title=_clip(title, 255),
            target_role=_clip(data.target_role or "Software Engineer", 150),
            difficulty=data.difficulty or "intermediate",
            status="in_progress",
            domain_skills=data.domain_skills,
            resume_id=data.resume_id,
            coding_problem_id=coding_prob_id,
            target_duration_minutes=data.target_duration_minutes or 20,
            company_name=company_name,
            experience_level=data.experience_level,
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

        company_name = (data.company_name or "").replace("\x00", "").strip() or (jd.company or "").strip() or None
        experience_level = data.experience_level or (jd.extracted_experience or None)
        title = f"JD Interview: {jd.extracted_role or jd.title}"
        if company_name:
            title += f" @ {company_name}"

        coding_prob_id = data.coding_problem_id
        if data.category == "dsa" and not coding_prob_id:
            # Only curated problems have a full statement and real test cases. Live Codeforces
            # stubs have neither, so the interviewer can't discuss them and empty code "passes".
            from backend.app.coding.problems import pick_curated_interview_problem
            coding_prob_id = pick_curated_interview_problem(jd.extracted_skills, data.difficulty)

        interview = Interview(
            user_id=user_id,
            mode="jd",
            category=data.category,
            title=_clip(title, 255),
            target_role=_clip(jd.extracted_role or jd.title, 150),
            difficulty=data.difficulty or "intermediate",
            status="in_progress",
            domain_skills=jd.extracted_skills,
            jd_id=jd.id,
            resume_id=data.resume_id,
            coding_problem_id=coding_prob_id,
            target_duration_minutes=data.target_duration_minutes or 20,
            company_name=company_name,
            experience_level=experience_level,
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
        delivery: Optional[Dict[str, Any]] = None,
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

        # NUL bytes break Postgres text/JSONB (messages and the LangGraph checkpoint).
        content = (content or "").replace("\x00", "")
        if not content.strip():
            raise AppException("Write an answer first.", code="EMPTY_ANSWER")

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
            from backend.app.interviews.agent.policy import classify_intent
            intent = classify_intent(content)
            if intent in ("repeat_question", "clarify"):
                return await cls._answer_meta_request(db, user_id, interview, content, client_turn_id, intent)
            gated = await cls._conduct_gate(db, user_id, interview, content, client_turn_id, delivery)
            if gated is not None:
                return gated

            last_assistant = next((m for m in reversed(interview.messages) if m.role == "assistant"), None)
            user_kind = "candidate_question" if getattr(last_assistant, "kind", None) == "closing" else "answer"
            user_msg = InterviewMessage(
                interview_id=interview.id,
                role="user",
                content=content,
                client_turn_id=client_turn_id,
                question_index=len([m for m in interview.messages if m.role == "assistant"]),
                is_follow_up=False,
                kind=user_kind,
                delivery=delivery,
            )
            # Append to the loaded collection (not just db.add) so the turn count and the
            # agent's conversation history both include this answer.
            interview.messages.append(user_msg)
            await db.flush()

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
        try:
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
        except Exception:
            # Drop the unanswered candidate message so the client can resend the same draft.
            await db.rollback()
            raise

        assistant_text = agent_result["assistant_content"]
        is_follow_up = (agent_result.get("next_action") == "ask_follow_up")
        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=assistant_text,
            question_index=len([m for m in interview.messages if m.role == "assistant"]) + 1,
            is_follow_up=is_follow_up,
            kind=_assistant_kind(agent_result, default="question"),
        )
        interview.messages.append(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        return assistant_msg

    @classmethod
    async def _conduct_gate(cls, db: AsyncSession, user_id: str, interview: Interview, content: str,
                            client_turn_id: Optional[str], delivery: Optional[Dict[str, Any]]) -> Optional[InterviewMessage]:
        """
        Conduct policy (backend/app/interviews/conduct.py): warn once, then end the interview. Returns the
        interviewer's reply when it handled the turn, or None to let the normal engine answer.
        """
        from backend.app.interviews import conduct
        last_q = next((m.content for m in reversed(interview.messages)
                       if m.role == "assistant" and getattr(m, "kind", "question") in ("question", "code_feedback", "conduct_warning")), "")
        if "Back to my question:" in (last_q or ""):
            last_q = last_q.split("Back to my question:", 1)[1].strip()

        async def ask(system: str, prompt: str) -> str:
            from langchain_core.messages import HumanMessage, SystemMessage
            from backend.app.providers.model_client_factory import ModelClientFactory
            model = await ModelClientFactory.get_chat_model(db, user_id, task_type="interviewer")
            resp = await model.ainvoke([SystemMessage(content=system), HumanMessage(content=prompt)])
            raw = resp.content
            return raw if isinstance(raw, str) else str(raw)

        # Spoken answers arrive through speech recognition, and misheard words look like nonsense. For voice turns
        # only clear-cut patterns (abuse, profanity, cheating admissions) count; the model's off-topic call is skipped.
        verdict = await conduct.assess(content, last_q, None if delivery else ask)
        warnings = sum(1 for m in interview.messages if m.role == "assistant" and getattr(m, "kind", None) == "conduct_warning")
        action = conduct.decide(verdict, warnings)
        if action == "continue":
            return None
        idx = len([m for m in interview.messages if m.role == "assistant"])
        interview.messages.append(InterviewMessage(
            interview_id=interview.id, role="user", content=content, client_turn_id=client_turn_id,
            question_index=idx, is_follow_up=False, kind="misconduct", delivery=delivery,
        ))
        if action == "warn":
            reply, kind = conduct.warning_text(verdict, last_q), "conduct_warning"
        else:
            reply, kind = conduct.termination_text(verdict), "terminated"
            interview.status = "completed"
            interview.completed_at = datetime.now(timezone.utc)
            interview.termination_reason = conduct.termination_reason(verdict)
        assistant_msg = InterviewMessage(interview_id=interview.id, role="assistant", content=reply,
                                         question_index=idx + 1, is_follow_up=False, kind=kind)
        interview.messages.append(assistant_msg)
        logger.info(f"Conduct policy: interview {interview.id} -> {action} ({verdict.kind}: {verdict.reason})")
        await db.commit()
        await db.refresh(assistant_msg)
        return assistant_msg

    @classmethod
    async def _answer_meta_request(
        cls,
        db: AsyncSession,
        user_id: str,
        interview: Interview,
        content: str,
        client_turn_id: Optional[str],
        intent: str,
    ) -> InterviewMessage:
        """'Repeat the question' / 'what do you mean?' never consume a turn or reach the grader."""
        last_q = next(
            (m.content for m in reversed(interview.messages)
             if m.role == "assistant" and getattr(m, "kind", "question") in ("question", "code_feedback")),
            None,
        )
        if not last_q:
            last_q = next((m.content for m in reversed(interview.messages) if m.role == "assistant"), "")

        if intent == "repeat_question" or not last_q:
            reply = f"Sure. Here it is again:\n\n{last_q}" if last_q else "There's no question on the table yet."
        else:
            from langchain_core.messages import HumanMessage, SystemMessage
            from backend.app.providers.model_client_factory import ModelClientFactory
            from backend.app.interviews.prompts import sanitize_untrusted_input
            model = await ModelClientFactory.get_chat_model(db, user_id, task_type="interviewer")
            try:
                resp = await model.ainvoke([
                    SystemMessage(content="You are a senior engineering interviewer. Direct, no praise, no filler."),
                    HumanMessage(content=(
                        "The candidate asked you to clarify your last question. Rephrase it in plain words, keep the same "
                        "intent, and add one short example of what a good answer would touch on. Don't give the answer. "
                        "Two sentences max. End with the rephrased question.\n\nYour last question:\n"
                        + sanitize_untrusted_input(last_q, max_chars=3000)
                    )),
                ])
            except Exception as e:
                raise translate_model_error(e) from e
            raw = resp.content
            reply = (raw if isinstance(raw, str) else str(raw)).strip() or f"Put differently:\n\n{last_q}"

        assistant_idx = len([m for m in interview.messages if m.role == "assistant"])
        interview.messages.append(InterviewMessage(
            interview_id=interview.id, role="user", content=content, client_turn_id=client_turn_id,
            question_index=assistant_idx, is_follow_up=False, kind="meta",
        ))
        assistant_msg = InterviewMessage(
            interview_id=interview.id, role="assistant", content=reply,
            question_index=assistant_idx + 1, is_follow_up=False, kind="repeat",
        )
        interview.messages.append(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)
        return assistant_msg

    # Exchanges that are not interview questions/answers (kept in the raw transcript, not paired).
    _UNPAIRED_KINDS = {"meta", "repeat", "hint_request", "hint", "closing", "candidate_question", "wrapup",
                       "misconduct", "conduct_warning", "terminated"}

    @staticmethod
    def compute_grouped_transcript(messages: List[InterviewMessage]) -> List[dict]:
        """Pair each interviewer question with the candidate reply that follows it, in true
        chronological order. Hint and repeat/clarify exchanges are not paired."""
        turns: List[dict] = []
        current_turn: Optional[dict] = None
        q_idx = 1

        for msg in messages:  # relationship is ordered by created_at; appends keep chronology
            kind = getattr(msg, "kind", None)
            content = msg.content or ""
            if kind in InterviewService._UNPAIRED_KINDS or content.startswith(("[Requested Level", "[Level ")):
                continue
            if msg.role == "assistant":
                if current_turn:
                    turns.append(current_turn)
                current_turn = {
                    "question_index": q_idx,
                    "interviewer_question": content,
                    "candidate_answer": "",
                    "is_follow_up": bool(msg.is_follow_up),
                    "assistant_message_id": msg.id,
                    "user_message_id": None,
                }
                q_idx += 1
            elif msg.role == "user" and current_turn:
                current_turn["candidate_answer"] = content
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

        try:
            await db.refresh(interview, attribute_names=["messages"])
        except Exception:
            pass

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
        try:
            response = await provider.generate_text(prompt=prompt, system_prompt=system_prompt)
        except Exception as e:
            raise translate_model_error(e) from e
        hint_text = response.text.strip()

        prob_name = problem.title if problem else "Problem"
        assistant_idx = len([m for m in interview.messages if m.role == "assistant"])
        user_msg = InterviewMessage(
            interview_id=interview.id,
            role="user",
            content=f"[Requested Level {level} Hint for {prob_name}]",
            question_index=assistant_idx,
            is_follow_up=False,
            kind="hint_request",
        )
        interview.messages.append(user_msg)

        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=f"[Level {level} Hint]: {hint_text}",
            question_index=assistant_idx,
            is_follow_up=False,
            kind="hint",
        )
        interview.messages.append(assistant_msg)

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
        code = (code or "").replace("\x00", "")
        candidate_notes = candidate_notes.replace("\x00", "") if candidate_notes else candidate_notes

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
            # Sample runs don't consume the answer budget; submissions do.
            kind="code_submit" if run_mode == "submit" else "code_run",
        )
        interview.messages.append(user_msg)
        await db.flush()

        # 3. Invoke LangGraph agent with structured execution context
        from backend.app.interviews.agent.service import InterviewAgentService
        try:
            turn_result = await InterviewAgentService.process_turn(
                db=db,
                user_id=user_id,
                interview=interview,
                candidate_content=message_content,
                candidate_message_id=user_msg.id,
                client_turn_id=client_turn_id,
            )
        except Exception:
            await db.rollback()
            raise

        assistant_content = turn_result["assistant_content"]
        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=assistant_content,
            question_index=len([m for m in interview.messages if m.role == "assistant"]) + 1,
            is_follow_up=bool((turn_result.get("question_metadata") or {}).get("is_follow_up", False)),
            kind=_assistant_kind(turn_result, default="code_feedback"),
        )
        interview.messages.append(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        return {
            "execution": submission_data,
            "assistant_message": assistant_msg,
        }


