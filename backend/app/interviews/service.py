from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Interview, InterviewMessage, JobDescription, Resume
from backend.app.interviews.schemas import (
    InterviewCreateDomain, InterviewCreateJd, InterviewMessageCreate
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
        # Load resume if provided
        resume = None
        if data.resume_id:
            res_result = await db.execute(
                select(Resume).where(Resume.id == data.resume_id, Resume.user_id == user_id)
            )
            resume = res_result.scalar_one_or_none()

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
            target_duration_minutes=data.target_duration_minutes or 20,
        )
        db.add(interview)
        await db.flush()

        # Build system prompt
        system_prompt = build_interviewer_system_prompt(
            category=interview.category,
            target_role=interview.target_role,
            difficulty=interview.difficulty,
            domain_skills=interview.domain_skills,
            resume_skills=resume.extracted_skills if resume else None,
            resume_projects=resume.projects_context if resume else None,
        )

        # Generate initial interview question
        provider = await ModelFactory.get_for_user(db, user_id, task_type="general")
        first_q_prompt = (
            f"The candidate is ready for a {interview.difficulty}-level {interview.category} interview "
            f"for the role of {interview.target_role}. Start the interview directly with your first question. "
            "Ask exactly ONE short, direct question about their engineering background or a concrete technical decision."
        )

        response = await provider.generate_text(prompt=first_q_prompt, system_prompt=system_prompt)
        initial_question = response.text.strip()

        msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=initial_question,
            question_index=1,
            is_follow_up=False,
        )
        db.add(msg)
        await db.commit()

        # Record token usage
        await ProviderConfigService.record_usage(
            db, user_id, response.input_tokens + response.output_tokens, response.estimated_cost_usd
        )

        return await cls.get_interview(db, user_id, interview.id)

    @classmethod
    async def create_jd_interview(
        cls,
        db: AsyncSession,
        user_id: str,
        data: InterviewCreateJd,
    ) -> Interview:
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
            target_duration_minutes=data.target_duration_minutes or 20,
        )
        db.add(interview)
        await db.flush()

        # Build system prompt focused on JD
        system_prompt = build_interviewer_system_prompt(
            category=interview.category,
            target_role=interview.target_role,
            difficulty=interview.difficulty,
            jd_role=jd.extracted_role or jd.title,
            jd_skills=jd.extracted_skills,
            jd_requirements=jd.extracted_requirements,
            resume_skills=resume.extracted_skills if resume else None,
            resume_projects=resume.projects_context if resume else None,
        )

        provider = await ModelFactory.get_for_user(db, user_id, task_type="general")
        first_q_prompt = (
            f"The candidate is interviewing for the {jd.extracted_role or jd.title} position based on the provided Job Description. "
            "Start the interview directly with your first question. Ask ONE short, direct question exploring their practical experience "
            f"with one of the primary requirements: {jd.extracted_skills[:3] if jd.extracted_skills else jd.title}."
        )

        response = await provider.generate_text(prompt=first_q_prompt, system_prompt=system_prompt)
        initial_question = response.text.strip()

        msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=initial_question,
            question_index=1,
            is_follow_up=False,
        )
        db.add(msg)
        await db.commit()

        # Record token usage
        await ProviderConfigService.record_usage(
            db, user_id, response.input_tokens + response.output_tokens, response.estimated_cost_usd
        )

        return await cls.get_interview(db, user_id, interview.id)

    @classmethod
    async def send_message(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
        content: str,
    ) -> InterviewMessage:
        interview = await cls.get_interview(db, user_id, interview_id)
        if interview.status != "in_progress":
            raise AppException("Interview is no longer active", code="INTERVIEW_NOT_ACTIVE")

        # Save user message
        user_msg = InterviewMessage(
            interview_id=interview.id,
            role="user",
            content=content,
            question_index=len([m for m in interview.messages if m.role == "assistant"]),
            is_follow_up=False,
        )
        db.add(user_msg)
        await db.flush()

        # Load context for prompt
        jd = None
        if interview.jd_id:
            jd_res = await db.execute(select(JobDescription).where(JobDescription.id == interview.jd_id))
            jd = jd_res.scalar_one_or_none()

        resume = None
        if interview.resume_id:
            res_res = await db.execute(select(Resume).where(Resume.id == interview.resume_id))
            resume = res_res.scalar_one_or_none()

        system_prompt = build_interviewer_system_prompt(
            category=interview.category,
            target_role=interview.target_role,
            difficulty=interview.difficulty,
            domain_skills=interview.domain_skills if interview.mode == "domain" else None,
            jd_role=jd.extracted_role if jd else None,
            jd_skills=jd.extracted_skills if jd else None,
            jd_requirements=jd.extracted_requirements if jd else None,
            resume_skills=resume.extracted_skills if resume else None,
            resume_projects=resume.projects_context if resume else None,
        )

        # Build conversation history
        history = []
        for m in interview.messages:
            history.append({"role": m.role, "content": m.content})
        history.append({"role": "user", "content": content})

        # Determine task type (for coding rounds, we can route to Qwen3 Coder)
        task_type = "coding" if interview.category == "dsa" else "general"
        provider = await ModelFactory.get_for_user(db, user_id, task_type=task_type)

        prompt = (
            "The candidate provided the following response:\n"
            "<untrusted_candidate_answer>\n"
            f"{content}\n"
            "</untrusted_candidate_answer>\n\n"
            "Respond as the interviewer. Remember:\n"
            "- Ask EXACTLY ONE question.\n"
            "- If their claim is unverified or vague, ask a skeptical follow-up ('How did you measure that?', 'What was the specific bottleneck?').\n"
            "- If their answer was solid, probe a concrete edge case or pivot to the next architectural trade-off.\n"
            "- Keep your response under 3 sentences."
        )

        response = await provider.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            conversation_history=history,
            max_tokens=600,
            temperature=0.6,
        )

        assistant_text = response.text.strip()
        assistant_msg = InterviewMessage(
            interview_id=interview.id,
            role="assistant",
            content=assistant_text,
            question_index=len([m for m in interview.messages if m.role == "assistant"]) + 1,
            is_follow_up=True if "?" in content or len(history) % 2 == 0 else False,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        # Record tokens
        await ProviderConfigService.record_usage(
            db, user_id, response.input_tokens + response.output_tokens, response.estimated_cost_usd
        )

        return assistant_msg

    @staticmethod
    async def end_interview(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
        interview = await InterviewService.get_interview(db, user_id, interview_id)
        if interview.status == "in_progress":
            interview.status = "completed"
            interview.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(interview)
        return interview

    @staticmethod
    async def get_interview(db: AsyncSession, user_id: str, interview_id: str) -> Interview:
        result = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id, Interview.user_id == user_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise EntityNotFoundError("Interview", interview_id)
        return interview

    @staticmethod
    async def list_interviews(db: AsyncSession, user_id: str) -> List[Interview]:
        result = await db.execute(
            select(Interview)
            .where(Interview.user_id == user_id)
            .order_by(Interview.created_at.desc())
        )
        return list(result.scalars().all())
