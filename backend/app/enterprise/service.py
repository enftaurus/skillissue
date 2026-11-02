import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.database.models import AssessmentPipeline, CandidateAssessment, User
from backend.app.enterprise.schemas import (
    CreatePipelineRequest, AssessmentPipelineResponse, CandidateInviteRequest,
    CandidateAssessmentResponse, CandidateSubmitRoundRequest, PipelineLeaderboardResponse, RoundConfig
)

DEFAULT_ROUNDS: List[Dict[str, Any]] = [
    {
        "round_type": "oa_dsa",
        "name": "Round 1: Company DSA Online Assessment",
        "time_limit_minutes": 35,
        "is_enabled": True,
        "config": {
            "problems_count": 2,
            "topics": ["Array", "Graph", "Dynamic Programming"],
            "difficulty": "Medium-Hard"
        }
    },
    {
        "round_type": "ai_project",
        "name": "Round 2: AI-Assisted Machine Coding (Distributed Rate Limiter)",
        "time_limit_minutes": 30,
        "is_enabled": True,
        "config": {
            "project_id": "distributed-rate-limiter",
            "copilot_mode": "read_only",
            "eval_prompts": True
        }
    },
    {
        "round_type": "tough_interview",
        "name": "Round 3: Anti-Sycophancy Oral Technical Interview",
        "time_limit_minutes": 20,
        "is_enabled": True,
        "config": {
            "questions_count": 4,
            "probe_depth": 3,
            "anti_sycophancy": True
        }
    },
    {
        "round_type": "code_comprehension",
        "name": "Round 4: Architecture & Code Comprehension (Google-Style)",
        "time_limit_minutes": 20,
        "is_enabled": False,
        "config": {
            "badge": "Coming Soon",
            "description": "Analyze a 300-line production diff and detect race conditions without running code."
        }
    }
]

class EnterpriseService:
    @classmethod
    async def create_pipeline(
        cls, db: AsyncSession, user_id: str, data: CreatePipelineRequest
    ) -> AssessmentPipelineResponse:
        invite_token = uuid.uuid4().hex[:12]
        
        rounds_data = [r.model_dump() for r in data.rounds] if data.rounds else DEFAULT_ROUNDS

        pipeline = AssessmentPipeline(
            created_by_user_id=user_id,
            title=data.title,
            target_role=data.target_role,
            job_description=data.job_description,
            rounds=rounds_data,
            oa_config=data.oa_config or {},
            is_active=True,
            invite_token=invite_token
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)

        return AssessmentPipelineResponse(
            id=pipeline.id,
            title=pipeline.title,
            target_role=pipeline.target_role,
            job_description=pipeline.job_description,
            rounds=pipeline.rounds or [],
            oa_config=pipeline.oa_config or {},
            is_active=pipeline.is_active,
            invite_token=pipeline.invite_token,
            invite_url=f"/assess/take/{pipeline.invite_token}",
            candidates_count=0,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at
        )

    @classmethod
    async def list_pipelines(
        cls, db: AsyncSession, user_id: str
    ) -> List[AssessmentPipelineResponse]:
        result = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(AssessmentPipeline.created_by_user_id == user_id)
            .order_by(AssessmentPipeline.created_at.desc())
        )
        pipelines = list(result.scalars().all())

        responses = []
        for p in pipelines:
            responses.append(
                AssessmentPipelineResponse(
                    id=p.id,
                    title=p.title,
                    target_role=p.target_role,
                    job_description=p.job_description,
                    rounds=p.rounds or [],
                    oa_config=p.oa_config or {},
                    is_active=p.is_active,
                    invite_token=p.invite_token,
                    invite_url=f"/assess/take/{p.invite_token}",
                    candidates_count=len(p.candidates or []),
                    created_at=p.created_at,
                    updated_at=p.updated_at
                )
            )
        return responses

    @classmethod
    async def get_pipeline_by_id(
        cls, db: AsyncSession, user_id: str, pipeline_id: str
    ) -> AssessmentPipelineResponse:
        result = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(AssessmentPipeline.id == pipeline_id, AssessmentPipeline.created_by_user_id == user_id)
        )
        p = result.scalar_one_or_none()
        if not p:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        return AssessmentPipelineResponse(
            id=p.id,
            title=p.title,
            target_role=p.target_role,
            job_description=p.job_description,
            rounds=p.rounds or [],
            oa_config=p.oa_config or {},
            is_active=p.is_active,
            invite_token=p.invite_token,
            invite_url=f"/assess/take/{p.invite_token}",
            candidates_count=len(p.candidates or []),
            created_at=p.created_at,
            updated_at=p.updated_at
        )

    @classmethod
    async def invite_candidate(
        cls, db: AsyncSession, user_id: str, pipeline_id: str, data: CandidateInviteRequest
    ) -> CandidateAssessmentResponse:
        p_res = await db.execute(
            select(AssessmentPipeline).where(
                AssessmentPipeline.id == pipeline_id,
                AssessmentPipeline.created_by_user_id == user_id
            )
        )
        pipeline = p_res.scalar_one_or_none()
        if not pipeline:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        access_token = uuid.uuid4().hex
        candidate = CandidateAssessment(
            pipeline_id=pipeline.id,
            candidate_name=data.candidate_name,
            candidate_email=data.candidate_email,
            access_token=access_token,
            status="invited",
            current_round_index=0,
            round_results={},
            composite_score=0.0,
            integrity_signals={"window_blurs": 0, "copy_paste_count": 0, "speech_code_divergence": 0.0}
        )
        db.add(candidate)
        await db.commit()
        await db.refresh(candidate)

        return CandidateAssessmentResponse(
            id=candidate.id,
            pipeline_id=candidate.pipeline_id,
            pipeline_title=pipeline.title,
            target_role=pipeline.target_role,
            candidate_name=candidate.candidate_name,
            candidate_email=candidate.candidate_email,
            access_token=candidate.access_token,
            status=candidate.status,
            resume_text=candidate.resume_text,
            oa_problem_title=candidate.oa_problem_title,
            oa_submitted_code=candidate.oa_submitted_code,
            current_round_index=candidate.current_round_index,
            round_results=candidate.round_results or {},
            composite_score=candidate.composite_score,
            integrity_signals=candidate.integrity_signals or {},
            rounds=pipeline.rounds or [],
            created_at=candidate.created_at,
            completed_at=candidate.completed_at
        )

    @classmethod
    async def get_candidate_exam_by_token(
        cls, db: AsyncSession, token: str
    ) -> CandidateAssessmentResponse:
        # Check if token is candidate access_token or general pipeline invite_token
        cand_res = await db.execute(
            select(CandidateAssessment)
            .options(selectinload(CandidateAssessment.pipeline))
            .where(CandidateAssessment.access_token == token)
        )
        candidate = cand_res.scalar_one_or_none()

        if candidate:
            pipeline = candidate.pipeline
            return CandidateAssessmentResponse(
                id=candidate.id,
                pipeline_id=candidate.pipeline_id,
                pipeline_title=pipeline.title,
                target_role=pipeline.target_role,
                candidate_name=candidate.candidate_name,
                candidate_email=candidate.candidate_email,
                access_token=candidate.access_token,
                status=candidate.status,
                resume_text=candidate.resume_text,
                oa_problem_title=candidate.oa_problem_title,
                oa_submitted_code=candidate.oa_submitted_code,
                current_round_index=candidate.current_round_index,
                round_results=candidate.round_results or {},
                composite_score=candidate.composite_score,
                integrity_signals=candidate.integrity_signals or {},
                rounds=[r for r in (pipeline.rounds or []) if r.get("is_enabled", True)],
                created_at=candidate.created_at,
                completed_at=candidate.completed_at
            )

        # Check if pipeline general invite token
        pipe_res = await db.execute(
            select(AssessmentPipeline).where(AssessmentPipeline.invite_token == token)
        )
        pipeline = pipe_res.scalar_one_or_none()
        if not pipeline:
            raise AppException("Invalid assessment link or token expired", code="NOT_FOUND", status_code=404)

        # Create quick guest candidate
        new_token = uuid.uuid4().hex
        guest_cand = CandidateAssessment(
            pipeline_id=pipeline.id,
            candidate_name="Assessment Candidate",
            candidate_email=f"candidate_{new_token[:6]}@example.com",
            access_token=new_token,
            status="in_progress",
            current_round_index=0,
            round_results={},
            composite_score=0.0,
            integrity_signals={"window_blurs": 0, "copy_paste_count": 0, "speech_code_divergence": 0.0}
        )
        db.add(guest_cand)
        await db.commit()
        await db.refresh(guest_cand)

        return CandidateAssessmentResponse(
            id=guest_cand.id,
            pipeline_id=guest_cand.pipeline_id,
            pipeline_title=pipeline.title,
            target_role=pipeline.target_role,
            candidate_name=guest_cand.candidate_name,
            candidate_email=guest_cand.candidate_email,
            access_token=guest_cand.access_token,
            status=guest_cand.status,
            current_round_index=guest_cand.current_round_index,
            round_results={},
            composite_score=0.0,
            integrity_signals=guest_cand.integrity_signals,
            rounds=[r for r in (pipeline.rounds or []) if r.get("is_enabled", True)],
            created_at=guest_cand.created_at,
            completed_at=None
        )

    @classmethod
    async def submit_candidate_round(
        cls, db: AsyncSession, access_token: str, req: CandidateSubmitRoundRequest
    ) -> CandidateAssessmentResponse:
        cand_res = await db.execute(
            select(CandidateAssessment)
            .options(selectinload(CandidateAssessment.pipeline))
            .where(CandidateAssessment.access_token == access_token)
        )
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise AppException("Invalid assessment token", code="NOT_FOUND", status_code=404)

        pipeline = candidate.pipeline
        enabled_rounds = [r for r in (pipeline.rounds or []) if r.get("is_enabled", True)]

        # Update round results
        results = dict(candidate.round_results or {})
        round_score = float(req.submission_data.get("score", 75.0))
        results[str(req.round_index)] = {
            "round_type": req.round_type,
            "score": round_score,
            "submission": req.submission_data,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        candidate.round_results = results

        # Update integrity signals
        signals = dict(candidate.integrity_signals or {})
        blurs = signals.get("window_blurs", 0) + int(req.integrity_events.get("window_blurs", 0))
        pastes = signals.get("copy_paste_count", 0) + int(req.integrity_events.get("copy_paste_count", 0))
        signals["window_blurs"] = blurs
        signals["copy_paste_count"] = pastes

        # Divergence check: Scored high on code in minutes but low oral or high tab blurs
        if blurs >= 4 or pastes >= 8:
            signals["speech_code_divergence"] = 0.82
            candidate.status = "flagged"
        else:
            signals["speech_code_divergence"] = 0.15

        candidate.integrity_signals = signals

        # Update resume and OA submitted code if supplied
        if req.resume_text:
            candidate.resume_text = req.resume_text
        if req.oa_problem_title:
            candidate.oa_problem_title = req.oa_problem_title
        if req.oa_submitted_code:
            candidate.oa_submitted_code = req.oa_submitted_code

        # Advance to next round or complete
        candidate.current_round_index = req.round_index + 1
        if candidate.current_round_index >= len(enabled_rounds):
            # Calculate composite score across all completed rounds
            scores = [r_data.get("score", 0.0) for r_data in results.values()]
            candidate.composite_score = round(sum(scores) / max(1, len(scores)), 1)
            if candidate.status != "flagged":
                candidate.status = "completed"
            candidate.completed_at = datetime.now(timezone.utc)
        else:
            if candidate.status != "flagged":
                candidate.status = "in_progress"

        await db.commit()
        await db.refresh(candidate)

        return CandidateAssessmentResponse(
            id=candidate.id,
            pipeline_id=candidate.pipeline_id,
            pipeline_title=pipeline.title,
            target_role=pipeline.target_role,
            candidate_name=candidate.candidate_name,
            candidate_email=candidate.candidate_email,
            access_token=candidate.access_token,
            status=candidate.status,
            resume_text=candidate.resume_text,
            oa_problem_title=candidate.oa_problem_title,
            oa_submitted_code=candidate.oa_submitted_code,
            current_round_index=candidate.current_round_index,
            round_results=candidate.round_results,
            composite_score=candidate.composite_score,
            integrity_signals=candidate.integrity_signals,
            rounds=enabled_rounds,
            created_at=candidate.created_at,
            completed_at=candidate.completed_at
        )

    @classmethod
    async def get_pipeline_leaderboard(
        cls, db: AsyncSession, user_id: str, pipeline_id: str
    ) -> PipelineLeaderboardResponse:
        p_res = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(
                AssessmentPipeline.id == pipeline_id,
                AssessmentPipeline.created_by_user_id == user_id
            )
        )
        pipeline = p_res.scalar_one_or_none()
        if not pipeline:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        candidates = pipeline.candidates or []
        # Sort by composite_score desc
        sorted_candidates = sorted(candidates, key=lambda c: (c.composite_score, c.created_at), reverse=True)

        cand_responses = []
        completed_scores = []
        for c in sorted_candidates:
            if c.status in ("completed", "flagged"):
                completed_scores.append(c.composite_score)
            cand_responses.append(
                CandidateAssessmentResponse(
                    id=c.id,
                    pipeline_id=c.pipeline_id,
                    pipeline_title=pipeline.title,
                    target_role=pipeline.target_role,
                    candidate_name=c.candidate_name,
                    candidate_email=c.candidate_email,
                    access_token=c.access_token,
                    status=c.status,
                    resume_text=c.resume_text,
                    oa_problem_title=c.oa_problem_title,
                    oa_submitted_code=c.oa_submitted_code,
                    current_round_index=c.current_round_index,
                    round_results=c.round_results or {},
                    composite_score=c.composite_score,
                    integrity_signals=c.integrity_signals or {},
                    rounds=pipeline.rounds or [],
                    created_at=c.created_at,
                    completed_at=c.completed_at
                )
            )

        avg_score = round(sum(completed_scores) / max(1, len(completed_scores)), 1) if completed_scores else 0.0

        return PipelineLeaderboardResponse(
            pipeline_id=pipeline.id,
            pipeline_title=pipeline.title,
            target_role=pipeline.target_role,
            total_candidates=len(candidates),
            completed_candidates=len(completed_scores),
            average_score=avg_score,
            candidates=cand_responses
        )
