from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models import JobDescription
from backend.app.job_descriptions.schemas import JobDescriptionCreate, JobDescriptionUpdate
from backend.app.providers.factory import ModelFactory
from backend.app.core.errors import EntityNotFoundError, AppException

class JobDescriptionService:
    @classmethod
    async def create_and_extract(
        cls,
        db: AsyncSession,
        user_id: str,
        data: JobDescriptionCreate
    ) -> JobDescription:
        provider = await ModelFactory.get_for_user(db, user_id, task_type="general")
        prompt = (
            "Analyze the following job description. Extract the primary role title, key required skills, "
            "and core technical/behavioral requirements.\n\n"
            f"JOB DESCRIPTION:\n{data.raw_text[:5000]}\n\n"
            "Return JSON matching this exact structure: "
            '{"role": "...", "extracted_skills": ["Python", "SQL", ...], "extracted_requirements": ["3+ years experience with ...", "..."], "recommended_focus": "..."}'
        )
        system_prompt = "You are a senior hiring manager extracting structured requirements from a job posting for interview targeting."

        response = await provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        parsed = response.parsed_json or {}

        role = parsed.get("role") or data.title
        skills = parsed.get("extracted_skills", [])
        if not skills:
            skills = ["Backend Development", "System Design", "Problem Solving"]
        requirements = parsed.get("extracted_requirements", [])

        jd = JobDescription(
            user_id=user_id,
            title=data.title,
            company=data.company or "",
            raw_text=data.raw_text,
            extracted_role=role,
            extracted_skills=skills,
            extracted_requirements=requirements,
        )
        db.add(jd)
        await db.commit()
        await db.refresh(jd)
        return jd

    @staticmethod
    async def list_jds(db: AsyncSession, user_id: str) -> List[JobDescription]:
        result = await db.execute(
            select(JobDescription).where(JobDescription.user_id == user_id).order_by(JobDescription.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_jd(db: AsyncSession, user_id: str, jd_id: str) -> JobDescription:
        result = await db.execute(
            select(JobDescription).where(JobDescription.id == jd_id, JobDescription.user_id == user_id)
        )
        jd = result.scalar_one_or_none()
        if not jd:
            raise EntityNotFoundError("JobDescription", jd_id)
        return jd

    @staticmethod
    async def update_jd(
        db: AsyncSession,
        user_id: str,
        jd_id: str,
        data: JobDescriptionUpdate
    ) -> JobDescription:
        jd = await JobDescriptionService.get_jd(db, user_id, jd_id)
        if data.title is not None:
            jd.title = data.title
        if data.company is not None:
            jd.company = data.company
        if data.extracted_role is not None:
            jd.extracted_role = data.extracted_role
        if data.extracted_skills is not None:
            jd.extracted_skills = data.extracted_skills
        if data.extracted_requirements is not None:
            jd.extracted_requirements = data.extracted_requirements

        await db.commit()
        await db.refresh(jd)
        return jd

    @staticmethod
    async def delete_jd(db: AsyncSession, user_id: str, jd_id: str) -> bool:
        jd = await JobDescriptionService.get_jd(db, user_id, jd_id)
        await db.delete(jd)
        await db.commit()
        return True
