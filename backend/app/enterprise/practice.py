"""
Company hiring simulations as personal practice drives (ADR 0027 addendum).

A simulation is an assessment pipeline the user owns and takes themselves, run by the same server-side runner as
enterprise drives. The only difference is who may read the results: for practice drives the candidate gets the full
report once every round is submitted. AI rounds use the user's own model (they own the pipeline).
"""
import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.errors import AppException, EntityNotFoundError
from backend.app.database.models import AssessmentPipeline, CandidateAssessment, User
from backend.app.enterprise.runner import enabled_rounds


def is_practice(pipeline: AssessmentPipeline) -> bool:
    return bool((pipeline.oa_config or {}).get("practice"))


def _job_description(sim: Dict[str, Any], company: Dict[str, Any]) -> str:
    tips = "\n".join(f"- {t}" for t in (company.get("community_tips") or [])[:4])
    return (f"{sim['company']}-style hiring simulation for {company.get('role_title', 'Software Engineer')}.\n"
            f"What {sim['company']} evaluates: {company.get('description', '')}\n"
            f"Interview patterns candidates report:\n{tips}\n"
            "Run it like a real loop at that bar. Never claim to work at the company.")


async def start_simulation(db: AsyncSession, user: User, sim_id: str) -> Dict[str, Any]:
    from backend.app.enterprise.schemas import CandidateEntryRequest
    from backend.app.enterprise.service import EnterpriseService
    from backend.app.tracks.company_context import get_company
    from backend.app.tracks.company_registry import CompanyRegistry

    sim = CompanyRegistry.get_simulation_by_id(sim_id)
    if not sim:
        raise EntityNotFoundError("PlacementSimulation", sim_id)
    if user.role in ("recruiter", "admin"):
        raise AppException("Simulations are for candidate accounts.", code="CANDIDATE_ACCOUNT_REQUIRED", status_code=403)

    # Resume an unfinished attempt instead of starting a second one.
    mine = (await db.execute(
        select(CandidateAssessment).options(selectinload(CandidateAssessment.pipeline))
        .join(AssessmentPipeline, AssessmentPipeline.id == CandidateAssessment.pipeline_id)
        .where(CandidateAssessment.candidate_user_id == user.id, AssessmentPipeline.created_by_user_id == user.id)
        .order_by(CandidateAssessment.created_at.desc()))).scalars().all()
    for c in mine:
        oa = c.pipeline.oa_config or {}
        if oa.get("practice") and oa.get("simulation_id") == sim_id and c.status not in ("completed", "flagged"):
            return {"access_token": c.access_token, "resumed": True}

    company = get_company(sim.get("company_slug")) or {"description": "", "community_tips": [], "role_title": "Software Engineer"}
    pipeline = AssessmentPipeline(
        created_by_user_id=user.id, tenant_id=None, title=sim["title"],
        target_role=company.get("role_title", "Software Engineer")[:150],
        job_description=_job_description(sim, company),
        rounds=[{"round_type": r["type"], "name": r["name"], "time_limit_minutes": r["time_limit"], "is_enabled": True,
                 "config": dict(r.get("config") or {})} for r in sim["rounds"]],
        oa_config={"practice": True, "simulation_id": sim_id}, is_active=True, invite_token=uuid.uuid4().hex[:12],
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    view = await EnterpriseService.enter_assessment(db, pipeline.invite_token, CandidateEntryRequest(), user)
    return {"access_token": view.access_token, "resumed": False}


def practice_report(candidate: CandidateAssessment) -> Dict[str, Any]:
    """Full results for the candidate's own practice drive, plus the answer keys they can now learn from."""
    from backend.app.comprehension.bank import ITEMS_BY_ID
    from backend.app.comprehension.service import reveal
    pipeline = candidate.pipeline
    if not is_practice(pipeline):
        raise AppException("Results for this assessment go to the hiring team.", code="RESULTS_HIDDEN", status_code=403)
    if candidate.status not in ("completed", "flagged"):
        raise AppException("Finish every round to see your report.", code="NOT_FINISHED", status_code=409)
    results = candidate.round_results or {}
    rounds = []
    for i, r in enumerate(enabled_rounds(pipeline)):
        res = dict(results.get(str(i)) or {})
        details = dict(res.get("details") or {})
        if r["round_type"] == "code_comprehension" and details.get("item_id") in ITEMS_BY_ID:
            details["answer_key"] = reveal(ITEMS_BY_ID[details["item_id"]])
        rounds.append({"index": i, "name": r.get("name"), "round_type": r["round_type"], "score": res.get("score"),
                       "status": res.get("status", "pending"), "elapsed_seconds": res.get("elapsed_seconds"),
                       "overtime": res.get("overtime", False), "details": details})
    return {"pipeline_title": pipeline.title, "composite_score": candidate.composite_score, "rounds": rounds,
            "completed_at": candidate.completed_at.isoformat() if candidate.completed_at else None}
