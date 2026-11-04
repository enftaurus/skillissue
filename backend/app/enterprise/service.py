import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.errors import EntityNotFoundError, AppException, AuthorizationError
from backend.app.database.models import AssessmentPipeline, CandidateAssessment, User
from backend.app.enterprise.schemas import (
    CreatePipelineRequest, UpdatePipelineRequest, AssessmentPipelineResponse,
    CandidateInviteRequest, CandidateEntryRequest,
    CandidateAssessmentResponse, CandidateSubmitRoundRequest,
    PipelineLeaderboardResponse, RoundConfig
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

def check_pipeline_tenant_access(pipeline: AssessmentPipeline, user: User, action: str = "access") -> None:
    """
    D5: Strict tenant isolation.
    - Admins can access and manage all pipelines.
    - Recruiters can only access and manage pipelines belonging to their tenant.
    - If pipeline has no tenant_id, only creator can access.
    - Otherwise raises 403 Forbidden.
    """
    if user.role == "admin":
        return

    if user.role == "recruiter":
        if user.tenant_id:
            if pipeline.tenant_id == user.tenant_id:
                return
            if pipeline.tenant_id is None and pipeline.created_by_user_id == user.id:
                return
            raise AuthorizationError(f"Permission denied: you cannot {action} resources belonging to another organisation")
        else:
            if pipeline.created_by_user_id == user.id:
                return
            raise AuthorizationError(f"Permission denied: you cannot {action} this assessment pipeline")

    raise AuthorizationError(f"Permission denied: recruiter or administrative privileges required to {action} pipelines")

class EnterpriseService:
    @classmethod
    async def create_pipeline(
        cls, db: AsyncSession, user: User, data: CreatePipelineRequest
    ) -> AssessmentPipelineResponse:
        invite_token = uuid.uuid4().hex[:12]
        rounds_data = [r.model_dump() for r in data.rounds] if data.rounds else DEFAULT_ROUNDS

        pipeline = AssessmentPipeline(
            created_by_user_id=user.id,
            tenant_id=user.tenant_id,
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
            tenant_id=pipeline.tenant_id,
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
        cls, db: AsyncSession, user: User
    ) -> List[AssessmentPipelineResponse]:
        """
        D5: Recruiters only see pipelines in their tenant; admins see all.
        """
        query = select(AssessmentPipeline).options(selectinload(AssessmentPipeline.candidates))

        if user.role != "admin":
            if user.tenant_id:
                query = query.where(
                    or_(
                        AssessmentPipeline.tenant_id == user.tenant_id,
                        and_(AssessmentPipeline.tenant_id.is_(None), AssessmentPipeline.created_by_user_id == user.id)
                    )
                )
            else:
                query = query.where(AssessmentPipeline.created_by_user_id == user.id)

        query = query.order_by(AssessmentPipeline.created_at.desc())
        result = await db.execute(query)
        pipelines = list(result.scalars().all())

        responses = []
        for p in pipelines:
            responses.append(
                AssessmentPipelineResponse(
                    id=p.id,
                    tenant_id=p.tenant_id,
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
        cls, db: AsyncSession, user: User, pipeline_id: str
    ) -> AssessmentPipelineResponse:
        result = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(AssessmentPipeline.id == pipeline_id)
        )
        p = result.scalar_one_or_none()
        if not p:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        check_pipeline_tenant_access(p, user, action="view")

        return AssessmentPipelineResponse(
            id=p.id,
            tenant_id=p.tenant_id,
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
    async def update_pipeline(
        cls, db: AsyncSession, user: User, pipeline_id: str, data: UpdatePipelineRequest
    ) -> AssessmentPipelineResponse:
        result = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(AssessmentPipeline.id == pipeline_id)
        )
        p = result.scalar_one_or_none()
        if not p:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        check_pipeline_tenant_access(p, user, action="edit")

        if data.title is not None:
            p.title = data.title
        if data.target_role is not None:
            p.target_role = data.target_role
        if data.job_description is not None:
            p.job_description = data.job_description
        if data.rounds is not None:
            p.rounds = [r.model_dump() for r in data.rounds]
        if data.oa_config is not None:
            p.oa_config = data.oa_config
        if data.is_active is not None:
            p.is_active = data.is_active

        await db.commit()
        await db.refresh(p)

        return AssessmentPipelineResponse(
            id=p.id,
            tenant_id=p.tenant_id,
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
        cls, db: AsyncSession, user: User, pipeline_id: str, data: CandidateInviteRequest
    ) -> CandidateAssessmentResponse:
        p_res = await db.execute(
            select(AssessmentPipeline).where(AssessmentPipeline.id == pipeline_id)
        )
        pipeline = p_res.scalar_one_or_none()
        if not pipeline:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        check_pipeline_tenant_access(pipeline, user, action="invite candidates to")

        # One assessment per (pipeline, email)
        email_clean = data.candidate_email.lower().strip()
        existing_res = await db.execute(
            select(CandidateAssessment).where(
                CandidateAssessment.pipeline_id == pipeline.id,
                func.lower(CandidateAssessment.candidate_email) == email_clean
            )
        )
        candidate = existing_res.scalar_one_or_none()

        expires = datetime.now(timezone.utc) + timedelta(days=7)
        if candidate:
            candidate.candidate_name = data.candidate_name.strip()
            candidate.token_expires_at = expires
        else:
            access_token = uuid.uuid4().hex
            candidate = CandidateAssessment(
                pipeline_id=pipeline.id,
                candidate_name=data.candidate_name.strip(),
                candidate_email=email_clean,
                access_token=access_token,
                token_expires_at=expires,
                status="invited",
                current_round_index=0,
                round_results={},
                composite_score=None,
                integrity_signals={"status": "not_assessed"}
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
            token_expires_at=candidate.token_expires_at,
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
    async def enter_assessment(
        cls, db: AsyncSession, invite_token: str, data: CandidateEntryRequest
    ) -> CandidateAssessmentResponse:
        """
        D4: Candidate supplies their own name & email when entering an assessment.
        One assessment per (pipeline, email).
        Each candidate gets their own access_token with an expiry.
        Do NOT create any guest user account in users table.
        """
        pipe_res = await db.execute(
            select(AssessmentPipeline).where(AssessmentPipeline.invite_token == invite_token)
        )
        pipeline = pipe_res.scalar_one_or_none()
        if not pipeline:
            raise AppException("Invalid assessment invitation link or token expired", code="NOT_FOUND", status_code=404)

        if not pipeline.is_active:
            raise AppException("This assessment drive is no longer active", code="PIPELINE_INACTIVE", status_code=400)

        email_clean = data.candidate_email.lower().strip()
        cand_res = await db.execute(
            select(CandidateAssessment).where(
                CandidateAssessment.pipeline_id == pipeline.id,
                func.lower(CandidateAssessment.candidate_email) == email_clean
            )
        )
        candidate = cand_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)

        if candidate:
            candidate.candidate_name = data.candidate_name.strip()
            # If expired, refresh token & expiration
            if not candidate.token_expires_at or candidate.token_expires_at < now:
                candidate.token_expires_at = expires
                candidate.access_token = uuid.uuid4().hex
        else:
            access_token = uuid.uuid4().hex
            candidate = CandidateAssessment(
                pipeline_id=pipeline.id,
                candidate_name=data.candidate_name.strip(),
                candidate_email=email_clean,
                access_token=access_token,
                token_expires_at=expires,
                status="in_progress",
                current_round_index=0,
                round_results={},
                composite_score=None,
                integrity_signals={"status": "not_assessed"}
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
            token_expires_at=candidate.token_expires_at,
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

    @classmethod
    async def get_candidate_exam_by_token(
        cls, db: AsyncSession, token: str
    ) -> CandidateAssessmentResponse:
        """
        D4: Never auto-create guest candidates with placeholder emails.
        - If token is candidate access_token: verify expiry and return candidate assessment.
        - If token is pipeline invite_token: return metadata requiring candidate entry.
        """
        # 1. Check if token is candidate access_token
        cand_res = await db.execute(
            select(CandidateAssessment)
            .options(selectinload(CandidateAssessment.pipeline))
            .where(CandidateAssessment.access_token == token)
        )
        candidate = cand_res.scalar_one_or_none()

        if candidate:
            now = datetime.now(timezone.utc)
            if candidate.token_expires_at and candidate.token_expires_at < now:
                raise AppException("This assessment session link has expired.", code="TOKEN_EXPIRED", status_code=403)

            pipeline = candidate.pipeline
            return CandidateAssessmentResponse(
                id=candidate.id,
                pipeline_id=candidate.pipeline_id,
                pipeline_title=pipeline.title,
                target_role=pipeline.target_role,
                candidate_name=candidate.candidate_name,
                candidate_email=candidate.candidate_email,
                access_token=candidate.access_token,
                token_expires_at=candidate.token_expires_at,
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

        # 2. Check if token is pipeline general invite token
        pipe_res = await db.execute(
            select(AssessmentPipeline).where(AssessmentPipeline.invite_token == token)
        )
        pipeline = pipe_res.scalar_one_or_none()
        if not pipeline:
            raise AppException("Invalid assessment link or token expired", code="NOT_FOUND", status_code=404)

        # Do NOT auto-create a guest candidate. Return pipeline info indicating entry required.
        return CandidateAssessmentResponse(
            id="",
            pipeline_id=pipeline.id,
            pipeline_title=pipeline.title,
            target_role=pipeline.target_role,
            candidate_name="",
            candidate_email="",
            access_token="",
            token_expires_at=None,
            status="entry_required",
            is_invite_token=True,
            rounds=[r for r in (pipeline.rounds or []) if r.get("is_enabled", True)],
            created_at=None,
            completed_at=None
        )

    @classmethod
    async def submit_candidate_round(
        cls, db: AsyncSession, access_token: str, req: CandidateSubmitRoundRequest
    ) -> CandidateAssessmentResponse:
        """
        D2 & D3: Server-side score computation only.
        - Never read client-supplied req.submission_data['score'].
        - For DSA rounds: execute against real sandbox test cases.
        - For unscored rounds: score=None, status="submitted_unscored".
        - Integrity signals contain only {"status": "not_assessed"} and NEVER alter status or score.
        """
        cand_res = await db.execute(
            select(CandidateAssessment)
            .options(selectinload(CandidateAssessment.pipeline))
            .where(CandidateAssessment.access_token == access_token)
        )
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise AppException("Invalid assessment token", code="NOT_FOUND", status_code=404)

        now = datetime.now(timezone.utc)
        if candidate.token_expires_at and candidate.token_expires_at < now:
            raise AppException("This assessment session link has expired.", code="TOKEN_EXPIRED", status_code=403)

        pipeline = candidate.pipeline
        enabled_rounds = [r for r in (pipeline.rounds or []) if r.get("is_enabled", True)]

        # D2: Server-side scoring (NEVER trust client-supplied score)
        round_score: Optional[float] = None
        round_status: str = "submitted_unscored"
        execution_details: Dict[str, Any] = {}

        if req.round_type == "oa_dsa":
            code = req.submission_data.get("code") or req.oa_submitted_code or candidate.oa_submitted_code
            prob_id = req.submission_data.get("problem_id")
            if code and prob_id:
                try:
                    from backend.app.coding.problems import get_problem
                    from sandbox.runner import SandboxRunner, TestCase
                    problem = get_problem(prob_id)
                    if problem and problem.test_cases:
                        test_cases = [
                            TestCase(stdin=tc["stdin"], expected_stdout=tc["expected_stdout"], is_hidden=tc.get("is_hidden", False))
                            for tc in problem.test_cases
                        ]
                        exec_res = await SandboxRunner.execute_async(
                            language=req.submission_data.get("language", "python"),
                            code=code,
                            test_cases=test_cases
                        )
                        if exec_res.total_tests > 0:
                            round_score = round((exec_res.total_passed / exec_res.total_tests) * 100.0, 1)
                            round_status = "scored"
                            execution_details = {
                                "tests_passed": exec_res.total_passed,
                                "tests_total": exec_res.total_tests,
                                "execution_time_ms": exec_res.execution_time_ms
                            }
                except Exception:
                    round_score = None
                    round_status = "submitted_unscored"

        # Update round results
        results = dict(candidate.round_results or {})
        results[str(req.round_index)] = {
            "round_type": req.round_type,
            "score": round_score,
            "status": round_status,
            "execution": execution_details,
            "submitted_at": now.isoformat()
        }
        candidate.round_results = results

        # D3: Integrity Policy - signals are flag-only, no fixed divergence, never alter status or score
        candidate.integrity_signals = {"status": "not_assessed"}

        # Store resume text and submitted OA code for Stage 3 oral cross-exam
        if req.resume_text:
            candidate.resume_text = req.resume_text
        if req.oa_problem_title:
            candidate.oa_problem_title = req.oa_problem_title
        if req.oa_submitted_code:
            candidate.oa_submitted_code = req.oa_submitted_code

        # Advance to next round or complete
        candidate.current_round_index = req.round_index + 1
        if candidate.current_round_index >= len(enabled_rounds):
            candidate.status = "completed"
            candidate.completed_at = now
            # Compute composite score ONLY from scored rounds
            scored_list = [r_data["score"] for r_data in results.values() if r_data.get("score") is not None]
            if scored_list:
                candidate.composite_score = round(sum(scored_list) / len(scored_list), 1)
            else:
                candidate.composite_score = None
        else:
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
            token_expires_at=candidate.token_expires_at,
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
        cls, db: AsyncSession, user: User, pipeline_id: str
    ) -> PipelineLeaderboardResponse:
        p_res = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(AssessmentPipeline.id == pipeline_id)
        )
        pipeline = p_res.scalar_one_or_none()
        if not pipeline:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        check_pipeline_tenant_access(pipeline, user, action="view candidate results for")

        candidates = pipeline.candidates or []

        # Sort by composite_score desc (handling None scores safely)
        def sort_key(c: CandidateAssessment):
            sc = c.composite_score if c.composite_score is not None else -1.0
            dt = c.created_at.timestamp() if c.created_at else 0.0
            return (sc, dt)

        sorted_candidates = sorted(candidates, key=sort_key, reverse=True)

        cand_responses = []
        completed_scores = []
        for c in sorted_candidates:
            if c.composite_score is not None and c.status == "completed":
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
                    token_expires_at=c.token_expires_at,
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

        avg_score = round(sum(completed_scores) / max(1, len(completed_scores)), 1) if completed_scores else None

        return PipelineLeaderboardResponse(
            pipeline_id=pipeline.id,
            pipeline_title=pipeline.title,
            target_role=pipeline.target_role,
            total_candidates=len(candidates),
            completed_candidates=len(completed_scores),
            average_score=avg_score,
            candidates=cand_responses
        )

    @classmethod
    async def export_pipeline_candidates(
        cls, db: AsyncSession, user: User, pipeline_id: str
    ) -> Dict[str, Any]:
        """
        D5: Export candidate assessments, protected by tenant isolation.
        """
        p_res = await db.execute(
            select(AssessmentPipeline)
            .options(selectinload(AssessmentPipeline.candidates))
            .where(AssessmentPipeline.id == pipeline_id)
        )
        pipeline = p_res.scalar_one_or_none()
        if not pipeline:
            raise EntityNotFoundError("AssessmentPipeline", pipeline_id)

        check_pipeline_tenant_access(pipeline, user, action="export candidate data for")

        candidates_data = []
        for c in pipeline.candidates or []:
            candidates_data.append({
                "id": c.id,
                "candidate_name": c.candidate_name,
                "candidate_email": c.candidate_email,
                "status": c.status,
                "composite_score": c.composite_score,
                "round_results": c.round_results or {},
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            })

        return {
            "pipeline_id": pipeline.id,
            "title": pipeline.title,
            "tenant_id": pipeline.tenant_id,
            "total_candidates": len(candidates_data),
            "candidates": candidates_data
        }
