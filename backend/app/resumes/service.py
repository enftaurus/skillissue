import io
from typing import List, Optional
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database.models import Resume
from backend.app.providers.factory import ModelFactory
from backend.app.core.errors import EntityNotFoundError, AppException

class ResumeService:
    @staticmethod
    def extract_text_from_bytes(file_name: str, content: bytes) -> str:
        if file_name.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(content))
                pages_text = [page.extract_text() or "" for page in reader.pages]
                return "\n".join(pages_text).strip()
            except Exception as e:
                raise AppException(f"Failed to read PDF resume: {str(e)}", code="PDF_PARSE_ERROR")
        else:
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1", errors="ignore")

    @classmethod
    async def process_resume(
        cls,
        db: AsyncSession,
        user_id: str,
        file_name: str,
        content: bytes,
    ) -> Resume:
        raw_text = cls.extract_text_from_bytes(file_name, content)
        if not raw_text or len(raw_text.strip()) < 10:
            raise AppException("Uploaded resume appears to be empty or unreadable.", code="EMPTY_RESUME")

        # Use ModelFactory to extract skills and project contexts
        provider = await ModelFactory.get_for_user(db, user_id, task_type="general")
        prompt = (
            "Analyze the following resume text. Extract a list of verified technical and soft skills, "
            "and identify key project contexts or experience points that can be probed in an interview.\n\n"
            f"RESUME TEXT:\n{raw_text[:4000]}\n\n"
            "Return JSON matching this schema: "
            '{"detected_skills": ["Python", "Docker", ...], "project_contexts": [{"name": "...", "tech": "...", "summary": "..."}]}'
        )
        system_prompt = "You are an expert technical recruiter analyzing a resume to extract factual candidate skills and project experience."

        response = await provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        parsed = response.parsed_json or {}

        detected_skills = parsed.get("detected_skills", [])
        if not detected_skills:
            # Fallback heuristic extraction
            detected_skills = [s for s in ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs"] if s.lower() in raw_text.lower()]

        projects = parsed.get("project_contexts", [])

        resume = Resume(
            user_id=user_id,
            file_name=file_name,
            extracted_text=raw_text,
            extracted_skills=detected_skills,
            projects_context=projects,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)
        return resume

    @staticmethod
    async def list_resumes(db: AsyncSession, user_id: str) -> List[Resume]:
        result = await db.execute(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_resume(db: AsyncSession, user_id: str, resume_id: str) -> Resume:
        result = await db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        resume = result.scalar_one_or_none()
        if not resume:
            raise EntityNotFoundError("Resume", resume_id)
        return resume

    @staticmethod
    async def delete_resume(db: AsyncSession, user_id: str, resume_id: str) -> bool:
        resume = await ResumeService.get_resume(db, user_id, resume_id)
        await db.delete(resume)
        await db.commit()
        return True
