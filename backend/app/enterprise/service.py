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
    PipelineLeaderboardResponse, RoundConfig, CandidateExamView, DsaRunRequest, ProjectRunRequest,
    ComprehensionAnswerRequest, InterviewAnswerRequest,
)
from backend.app.enterprise import runner
from backend.app.enterprise.runner import enabled_rounds, _aware


def composite_score(rounds: List[Dict[str, Any]], results: Dict[str, Any]) -> Optional[float]:
    """Weighted mean over scored rounds (round config `weight`, default 1). Unscored rounds don't count."""
    total = weight = 0.0
    for i, r in enumerate(rounds):
        res = results.get(str(i)) or {}
        if res.get("score") is None:
            continue
        w = float((r.get("config") or {}).get("weight") or 1.0)
        total += float(res["score"]) * w
        weight += w
    return round(total / weight, 1) if weight else None

DEFAULT_ROUNDS: List[Dict[str, Any]] = [
    {
        "round_type": "oa_dsa",
        "name": "Round 1: Company DSA Online Assessment",
        "time_limit_minutes": 35,
        "is_enabled": True,
        "config": {
            "problems_count": 2,
            "topics": ["arrays", "graphs", "dp"],
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
        "name": "Round 4: Code Comprehension (read, trace, find the bug)",
        "time_limit_minutes": 20,
        "is_enabled": True,
        "config": {
            "description": "Read unfamiliar production code without running it: explain it, trace its output, locate the bug."
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
            access_token="",  # the candidate's session token is theirs alone; they join via the invite link
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

    # ------------------------------------------------------------------ candidate side (ADR 0027)

    @staticmethod
    def _exam_view(candidate: CandidateAssessment, pipeline: AssessmentPipeline) -> CandidateExamView:
        rounds = [{"index": i, "round_type": r["round_type"], "name": r.get("name"),
                   "time_limit_minutes": r.get("time_limit_minutes")} for i, r in enumerate(enabled_rounds(pipeline))]
        return CandidateExamView(
            id=candidate.id, pipeline_id=candidate.pipeline_id, pipeline_title=pipeline.title,
            target_role=pipeline.target_role, candidate_name=candidate.candidate_name,
            candidate_email=candidate.candidate_email, access_token=candidate.access_token,
            token_expires_at=candidate.token_expires_at,
            status="completed" if candidate.status in ("completed", "flagged") else "in_progress",
            current_round_index=candidate.current_round_index, rounds=rounds,
            created_at=candidate.created_at, completed_at=candidate.completed_at,
        )

    @staticmethod
    async def _owned(db: AsyncSession, user: User, token: str, lock: bool = False) -> CandidateAssessment:
        q = (select(CandidateAssessment).options(selectinload(CandidateAssessment.pipeline))
             .where(CandidateAssessment.access_token == token))
        if lock:
            q = q.with_for_update()
        candidate = (await db.execute(q)).scalar_one_or_none()
        # Same 404 for "no such token" and "someone else's token": don't confirm a token exists.
        if not candidate or candidate.candidate_user_id != user.id:
            raise AppException("Assessment not found.", code="NOT_FOUND", status_code=404)
        exp = _aware(candidate.token_expires_at)
        if exp and exp < datetime.now(timezone.utc) and candidate.status != "completed":
            raise AppException("This assessment session link has expired.", code="TOKEN_EXPIRED", status_code=403)
        return candidate

    @staticmethod
    async def _provider(db: AsyncSession, pipeline: AssessmentPipeline) -> Any:
        """The hiring team's model pays for and runs their assessment's AI rounds."""
        try:
            from backend.app.providers.factory import ModelFactory
            from backend.app.providers.mock_provider import MockProvider
            provider = await ModelFactory.get_for_user(db, pipeline.created_by_user_id, task_type="evaluation")
        except Exception:
            return None
        # The offline mock is for local development, not for judging real candidates: use the curated question bank
        # and deterministic grading, and mark model-only rounds "not evaluated" instead of inventing a score.
        return None if isinstance(provider, MockProvider) else provider

    @classmethod
    async def enter_assessment(
        cls, db: AsyncSession, invite_token: str, data: CandidateEntryRequest, user: User
    ) -> CandidateExamView:
        """
        A signed-in candidate starts or resumes an assessment from the pipeline's invite link. The account's email
        is the identity, so typing someone else's email can no longer hand over their session.
        """
        if user.role in ("recruiter", "admin"):
            raise AppException("Sign in with a candidate account to take an assessment.",
                               code="CANDIDATE_ACCOUNT_REQUIRED", status_code=403)
        pipeline = (await db.execute(select(AssessmentPipeline).where(AssessmentPipeline.invite_token == invite_token))).scalar_one_or_none()
        if not pipeline:
            raise AppException("Invalid assessment invitation link or token expired", code="NOT_FOUND", status_code=404)
        if not pipeline.is_active:
            raise AppException("This assessment drive is no longer active", code="PIPELINE_INACTIVE", status_code=400)
        if not enabled_rounds(pipeline):
            raise AppException("This assessment has no rounds yet.", code="NO_ROUNDS", status_code=400)

        email_clean = (user.email or "").lower().strip()
        candidate = (await db.execute(select(CandidateAssessment).where(
            CandidateAssessment.pipeline_id == pipeline.id,
            or_(CandidateAssessment.candidate_user_id == user.id,
                func.lower(CandidateAssessment.candidate_email) == email_clean)))).scalars().first()
        now = datetime.now(timezone.utc)
        name = (data.candidate_name or getattr(user, "full_name", None) or email_clean.split("@")[0]).strip()[:150]
        if candidate:
            if candidate.candidate_user_id and candidate.candidate_user_id != user.id:
                raise AppException("This invitation belongs to another account.", code="NOT_FOUND", status_code=404)
            candidate.candidate_user_id = user.id
            if data.candidate_name:
                candidate.candidate_name = name
            if candidate.status == "invited":
                candidate.status = "in_progress"
            exp = _aware(candidate.token_expires_at)
            if candidate.status != "completed" and (not exp or exp < now):
                candidate.token_expires_at = now + timedelta(days=7)
                candidate.access_token = uuid.uuid4().hex
        else:
            candidate = CandidateAssessment(
                pipeline_id=pipeline.id, candidate_user_id=user.id, candidate_name=name, candidate_email=email_clean,
                access_token=uuid.uuid4().hex, token_expires_at=now + timedelta(days=7), status="in_progress",
                current_round_index=0, round_results={}, round_state={}, composite_score=None,
                integrity_signals={"status": "not_assessed"},
            )
            db.add(candidate)
        await db.commit()
        await db.refresh(candidate)
        return cls._exam_view(candidate, pipeline)

    @classmethod
    async def get_candidate_exam_by_token(
        cls, db: AsyncSession, token: str, user: Optional[User] = None
    ) -> CandidateExamView:
        """Invite token: public landing info. Candidate token: the owner's progress (no results)."""
        if user is not None:
            cand = (await db.execute(select(CandidateAssessment.id).where(CandidateAssessment.access_token == token))).scalar_one_or_none()
            if cand:
                candidate = await cls._owned(db, user, token)
                return cls._exam_view(candidate, candidate.pipeline)
        pipeline = (await db.execute(select(AssessmentPipeline).where(AssessmentPipeline.invite_token == token))).scalar_one_or_none()
        if not pipeline:
            raise AppException("Invalid assessment link or token expired", code="NOT_FOUND", status_code=404)
        rounds = [{"index": i, "round_type": r["round_type"], "name": r.get("name"),
                   "time_limit_minutes": r.get("time_limit_minutes")} for i, r in enumerate(enabled_rounds(pipeline))]
        return CandidateExamView(pipeline_id=pipeline.id, pipeline_title=pipeline.title, target_role=pipeline.target_role,
                                 status="entry_required", is_invite_token=True, requires_login=user is None, rounds=rounds)

    @classmethod
    async def get_current_round(cls, db: AsyncSession, user: User, token: str) -> Dict[str, Any]:
        candidate = await cls._owned(db, user, token, lock=True)
        entry = runner.ensure_round_started(candidate, candidate.pipeline)
        provider = None
        if entry["round_type"] == "tough_interview" and not entry.get("transcript"):
            provider = await cls._provider(db, candidate.pipeline)
            out = await runner.interview_turn(candidate, candidate.pipeline, None, provider)
        else:
            out = runner.public_round(candidate, candidate.pipeline, entry)
        await db.commit()
        return out

    @classmethod
    async def run_dsa(cls, db: AsyncSession, user: User, token: str, req: DsaRunRequest) -> Dict[str, Any]:
        candidate = await cls._owned(db, user, token, lock=True)
        out = await runner.run_dsa_samples(candidate, candidate.pipeline, req.problem_id, req.language, req.code)
        await db.commit()
        return out

    @classmethod
    async def run_project(cls, db: AsyncSession, user: User, token: str, req: ProjectRunRequest) -> Dict[str, Any]:
        candidate = await cls._owned(db, user, token, lock=True)
        out = await runner.run_project(candidate, candidate.pipeline, req.files)
        await db.commit()
        return out

    @classmethod
    async def answer_comprehension(cls, db: AsyncSession, user: User, token: str, req: ComprehensionAnswerRequest) -> Dict[str, Any]:
        candidate = await cls._owned(db, user, token, lock=True)
        provider = await cls._provider(db, candidate.pipeline)
        out = await runner.answer_comprehension(candidate, candidate.pipeline, req.question_id, req.answer, provider)
        await db.commit()
        return out

    @classmethod
    async def interview_answer(cls, db: AsyncSession, user: User, token: str, req: InterviewAnswerRequest) -> Dict[str, Any]:
        candidate = await cls._owned(db, user, token, lock=True)
        provider = await cls._provider(db, candidate.pipeline)
        out = await runner.interview_turn(candidate, candidate.pipeline, req.answer, provider)
        await db.commit()
        return out

    @classmethod
    async def submit_candidate_round(
        cls, db: AsyncSession, access_token: str, req: CandidateSubmitRoundRequest, user: User
    ) -> CandidateExamView:
        """
        Finalise the current round. Scores are computed here from server-assigned content only; the client can't
        pick the problem, skip ahead, resubmit, or supply a score. The response carries progress, never results.
        """
        candidate = await cls._owned(db, user, access_token, lock=True)
        pipeline = candidate.pipeline
        rounds = enabled_rounds(pipeline)
        if candidate.status in ("completed", "flagged") or candidate.current_round_index >= len(rounds):
            raise AppException("This assessment is already submitted.", code="ASSESSMENT_COMPLETED", status_code=409)
        if req.round_index != candidate.current_round_index:
            raise AppException("That round isn't the current one.", code="ROUND_OUT_OF_ORDER", status_code=409)
        rnd = rounds[req.round_index]
        if req.round_type != rnd["round_type"]:
            raise AppException("Round type doesn't match this round.", code="ROUND_MISMATCH", status_code=409)

        entry = runner.ensure_round_started(candidate, pipeline)
        now = datetime.now(timezone.utc)
        if rnd["round_type"] == "oa_dsa":
            # Keep the final code in server state so the oral round can cross-examine it.
            state = runner._state(candidate)
            e = state[str(req.round_index)]
            for pid, sol in (req.submission_data.get("solutions") or {}).items():
                if pid in e["problem_ids"] and isinstance(sol, dict) and isinstance(sol.get("code"), str):
                    e.setdefault("drafts", {})[pid] = {"language": str(sol.get("language") or "python"), "code": sol["code"][:65000]}
            runner._save(candidate, state)
            entry = e
            first = next(iter(e.get("drafts", {}).items()), None)
            if first:
                from backend.app.coding.problems import get_problem
                prob = get_problem(first[0])
                candidate.oa_problem_title = prob.title[:200] if prob else None
                candidate.oa_submitted_code = first[1]["code"]
        if req.resume_text:
            candidate.resume_text = req.resume_text[:20000]

        provider = await cls._provider(db, pipeline) if rnd["round_type"] in ("tough_interview",) else None
        score, status_, details = await runner.score_round(candidate, pipeline, entry, req.submission_data or {}, provider)
        started = datetime.fromisoformat(entry["started_at"])
        elapsed = int((now - started).total_seconds())
        overtime = now > runner.deadline_of(entry, rnd) + runner.ROUND_GRACE

        results = dict(candidate.round_results or {})
        results[str(req.round_index)] = {
            "round_type": rnd["round_type"], "name": rnd.get("name"), "score": score, "status": status_,
            "details": details, "elapsed_seconds": elapsed, "overtime": overtime, "submitted_at": now.isoformat(),
        }
        candidate.round_results = results

        # Telemetry analysis rewrites parts of integrity_signals (e.g. an int `window_blurs`), so the runner keeps its
        # own keys and never assumes their type.
        signals = dict(candidate.integrity_signals or {})

        def _bucket(key: str, kind: type):
            if not isinstance(signals.get(key), kind):
                signals[key] = kind()
            return signals[key]

        ev = req.integrity_events or {}
        if isinstance(ev.get("window_blurs"), int) and not isinstance(ev.get("window_blurs"), bool):
            _bucket("tab_switches_by_round", dict)[str(req.round_index)] = max(0, min(10_000, ev["window_blurs"]))
        if overtime:
            _bucket("overtime_rounds", list).append(req.round_index)
        if (details or {}).get("integrity_flags"):
            _bucket("sandbox_integrity", dict)[str(req.round_index)] = details["integrity_flags"]
        candidate.integrity_signals = signals

        if rnd["round_type"] in {"oa_dsa", "ai_project"}:
            code_for_telemetry = candidate.oa_submitted_code or ""
            try:
                from backend.app.integrity.telemetry_service import TelemetryService
                await TelemetryService.analyze_round_telemetry(candidate_assessment_id=candidate.id, round_key=str(req.round_index),
                                                               submitted_code=code_for_telemetry, db=db)
            except Exception:
                pass

        candidate.current_round_index = req.round_index + 1
        if candidate.current_round_index >= len(rounds):
            candidate.status = "completed"
            candidate.completed_at = now
            candidate.composite_score = composite_score(rounds, results)
        else:
            candidate.status = "in_progress"
        await db.commit()
        await db.refresh(candidate)
        return cls._exam_view(candidate, pipeline)

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

        # Ranked: completed + scored first by score desc; ties go to whoever finished first. Then everyone else.
        far = datetime.max.replace(tzinfo=timezone.utc)

        def sort_key(c: CandidateAssessment):
            ranked = c.status == "completed" and c.composite_score is not None
            return (0 if ranked else 1, -(c.composite_score or 0.0), _aware(c.completed_at) or far, _aware(c.created_at) or far)

        sorted_candidates = sorted(candidates, key=sort_key)
        rounds = enabled_rounds(pipeline)

        cand_responses = []
        rankings = []
        completed_scores = []
        rank = 0
        for c in sorted_candidates:
            ranked = c.status == "completed" and c.composite_score is not None
            if ranked:
                rank += 1
                completed_scores.append(c.composite_score)
            results = c.round_results or {}
            rankings.append({
                "rank": rank if ranked else None, "candidate_id": c.id, "candidate_name": c.candidate_name,
                "candidate_email": c.candidate_email, "status": c.status, "composite_score": c.composite_score,
                "rounds": [{"index": i, "name": r.get("name"), "round_type": r["round_type"],
                            "score": (results.get(str(i)) or {}).get("score"),
                            "status": (results.get(str(i)) or {}).get("status", "pending"),
                            "overtime": (results.get(str(i)) or {}).get("overtime", False)} for i, r in enumerate(rounds)],
                "integrity_signals": c.integrity_signals or {},
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            })
            cand_responses.append(
                CandidateAssessmentResponse(
                    id=c.id,
                    pipeline_id=c.pipeline_id,
                    pipeline_title=pipeline.title,
                    target_role=pipeline.target_role,
                    candidate_name=c.candidate_name,
                    candidate_email=c.candidate_email,
                    access_token="",
                    token_expires_at=c.token_expires_at,
                    status=c.status,
                    resume_text=c.resume_text,
                    oa_problem_title=c.oa_problem_title,
                    oa_submitted_code=c.oa_submitted_code,
                    current_round_index=c.current_round_index,
                    round_results=results,
                    composite_score=c.composite_score,
                    integrity_signals=c.integrity_signals or {},
                    rounds=rounds,
                    rank=rank if ranked else None,
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
            completed_candidates=sum(1 for c in candidates if c.status == "completed"),
            average_score=avg_score,
            candidates=cand_responses,
            rankings=rankings,
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
