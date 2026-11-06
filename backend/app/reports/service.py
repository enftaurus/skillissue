"""All of a user's past reports in one place. Every query is scoped to the signed-in user."""
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.errors import EntityNotFoundError
from backend.app.database.models import (AssessmentPipeline, CandidateAssessment, ComprehensionSession, Evaluation,
                                         Interview, ProjectSubmission)


def _iso(dt):
    return dt.isoformat() if dt else None


async def list_reports(db: AsyncSession, user_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    from backend.app.comprehension.bank import ITEMS_BY_ID
    from backend.app.projects.repository import get_project
    out: List[Dict[str, Any]] = []

    rows = (await db.execute(select(Evaluation, Interview).join(Interview, Interview.id == Evaluation.interview_id)
                             .where(Evaluation.user_id == user_id, Interview.user_id == user_id)
                             .order_by(Evaluation.created_at.desc()).limit(limit))).all()
    for ev, iv in rows:
        out.append({"kind": "interview", "id": iv.id, "title": iv.title, "subtitle": f"{iv.category.capitalize()} · {iv.target_role}",
                    "score": ev.overall_score, "status": "ended for conduct" if iv.termination_reason else ev.status,
                    "created_at": _iso(ev.created_at), "link": f"/evaluations/{iv.id}"})

    for s in (await db.execute(select(ProjectSubmission).where(ProjectSubmission.user_id == user_id)
                               .order_by(ProjectSubmission.created_at.desc()).limit(limit))).scalars():
        pa = s.prompt_analysis or {}
        p = get_project(s.project_id)
        tr = s.test_results or {}
        out.append({"kind": "ai_prompt", "id": s.id, "title": p.title if p else s.project_id,
                    "subtitle": f"Prompt grade {pa.get('grade', '—')} · {tr.get('passed_tests', 0)}/{tr.get('total_tests', 0)} tests · {s.prompts_count} prompts",
                    "score": pa.get("overall_score"), "status": s.status, "created_at": _iso(s.created_at),
                    "link": f"/reports/projects/{s.id}"})

    for c in (await db.execute(select(ComprehensionSession).where(ComprehensionSession.user_id == user_id,
                                                                  ComprehensionSession.status == "completed")
                               .order_by(ComprehensionSession.started_at.desc()).limit(limit))).scalars():
        item = ITEMS_BY_ID.get(c.item_id)
        out.append({"kind": "comprehension", "id": c.id, "title": item.title if item else c.item_id,
                    "subtitle": "Code comprehension", "score": c.score, "status": c.status,
                    "created_at": _iso(c.finished_at or c.started_at), "link": f"/comprehension/{c.id}"})

    sims = (await db.execute(select(CandidateAssessment).options(selectinload(CandidateAssessment.pipeline))
                             .join(AssessmentPipeline, AssessmentPipeline.id == CandidateAssessment.pipeline_id)
                             .where(CandidateAssessment.candidate_user_id == user_id,
                                    AssessmentPipeline.created_by_user_id == user_id,
                                    CandidateAssessment.status == "completed")
                             .order_by(CandidateAssessment.completed_at.desc()).limit(limit))).scalars().all()
    for c in sims:  # only the user's own practice simulations; enterprise results stay with the hiring team
        if not (c.pipeline.oa_config or {}).get("practice"):
            continue
        out.append({"kind": "simulation", "id": c.id, "title": c.pipeline.title, "subtitle": "Hiring simulation",
                    "score": c.composite_score, "status": c.status, "created_at": _iso(c.completed_at),
                    "link": f"/assess/take/{c.access_token}"})

    out.sort(key=lambda r: r["created_at"] or "", reverse=True)
    return out[:limit]


async def project_report(db: AsyncSession, user_id: str, submission_id: str) -> Dict[str, Any]:
    from backend.app.projects.repository import get_project
    s = (await db.execute(select(ProjectSubmission).where(ProjectSubmission.id == submission_id,
                                                          ProjectSubmission.user_id == user_id))).scalar_one_or_none()
    if s is None:
        raise EntityNotFoundError("ProjectSubmission", submission_id)
    p = get_project(s.project_id)
    tr = s.test_results or {}
    return {"id": s.id, "project_id": s.project_id, "project_title": p.title if p else s.project_id, "status": s.status,
            "passed_tests": tr.get("passed_tests", 0), "total_tests": tr.get("total_tests", 0),
            "prompts_count": s.prompts_count, "time_spent_seconds": s.time_spent_seconds,
            "prompt_analysis": s.prompt_analysis or {}, "created_at": _iso(s.created_at)}
