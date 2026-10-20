from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Interview, Evaluation, SelfEvaluation, UserSkill
from backend.app.evaluations.schemas import (
    SelfEvaluationCreate, EvaluationComparisonResponse, DimensionComparison, QuestionComparison
)
from backend.app.evaluations.prompts import build_evaluation_prompt
from backend.app.interviews.rubrics import get_rubric_for_category
from backend.app.providers.factory import ModelFactory
from backend.app.providers.service import ProviderConfigService
from backend.app.core.errors import EntityNotFoundError, AppException, ProviderError
from backend.app.core.logging import logger

class EvaluationService:
    @staticmethod
    async def save_self_evaluation(
        db: AsyncSession,
        user_id: str,
        data: SelfEvaluationCreate,
    ) -> SelfEvaluation:
        # Check if interview exists and belongs to user
        result = await db.execute(
            select(Interview).where(Interview.id == data.interview_id, Interview.user_id == user_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise EntityNotFoundError("Interview", data.interview_id)

        # Convert question_evaluations to dicts if provided
        q_evals_data = [q.model_dump() for q in data.question_evaluations] if data.question_evaluations else None

        # Check if already self-evaluated
        existing = await db.execute(
            select(SelfEvaluation).where(SelfEvaluation.interview_id == data.interview_id)
        )
        self_eval = existing.scalar_one_or_none()
        if self_eval:
            self_eval.dimension_scores = data.dimension_scores or {}
            self_eval.reflection = data.reflection or ""
            if q_evals_data is not None:
                self_eval.question_evaluations = q_evals_data
        else:
            self_eval = SelfEvaluation(
                interview_id=data.interview_id,
                user_id=user_id,
                dimension_scores=data.dimension_scores or {},
                reflection=data.reflection or "",
                question_evaluations=q_evals_data,
            )
            db.add(self_eval)

        await db.commit()
        await db.refresh(self_eval)
        return self_eval

    @classmethod
    async def generate_ai_evaluation(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
    ) -> Evaluation:
        # Load interview with transcript messages
        result = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id, Interview.user_id == user_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise EntityNotFoundError("Interview", interview_id)

        if len(interview.messages) < 2:
            raise AppException("Interview has insufficient transcript to evaluate (at least 1 completed question/answer turn is required).", code="INSUFFICIENT_DATA")

        # Build transcript text
        transcript_lines = []
        for m in interview.messages:
            sender = "Interviewer" if m.role == "assistant" else "Candidate"
            transcript_lines.append(f"{sender}: {m.content}")
        transcript_text = "\n\n".join(transcript_lines)

        rubric = get_rubric_for_category(interview.category)
        system_prompt, user_prompt = build_evaluation_prompt(
            category=interview.category,
            target_role=interview.target_role,
            rubric=rubric,
            transcript_text=transcript_text,
            hint_level_used=interview.hint_level_used,
        )

        provider = await ModelFactory.get_for_user(db, user_id, task_type="evaluation")
        response = await provider.generate_json(prompt=user_prompt, system_prompt=system_prompt)
        parsed = response.parsed_json or {}

        # Strictly reject malformed output; never silently fabricate a 70.0 score
        if not parsed or "error" in parsed or not parsed.get("dimension_scores"):
            raise ProviderError(
                "Model failed to generate structured evaluation. No rubric dimension scores were produced.",
                code="EVALUATION_PARSING_FAILED"
            )

        if "overall_score" not in parsed:
            raise ProviderError(
                "Model evaluation missing overall_score field.",
                code="EVALUATION_SCHEMA_INVALID"
            )

        try:
            overall_score = float(parsed["overall_score"])
        except (ValueError, TypeError):
            raise ProviderError(
                "Model returned non-numeric overall_score.",
                code="EVALUATION_SCHEMA_INVALID"
            )

        dimension_scores = parsed.get("dimension_scores", {})

        # Apply hint penalty if candidate used hints
        if interview.hint_level_used > 0 and "problem_solving_rigor" in dimension_scores:
            penalty_factor = 0.95 if interview.hint_level_used == 1 else (0.85 if interview.hint_level_used == 2 else 0.70)
            orig_score = dimension_scores["problem_solving_rigor"].get("score", 3)
            adjusted_score = max(1, int(round(orig_score * penalty_factor)))
            dimension_scores["problem_solving_rigor"]["score"] = adjusted_score
            dimension_scores["problem_solving_rigor"]["explanation"] += (
                f" (Reflects Level {interview.hint_level_used} hint penalty)."
            )

        # Compute overall_score deterministically from rubric dimension scores and weights
        total_weighted_score = 0.0
        total_weight = 0.0
        for dim in rubric:
            dim_val = dimension_scores.get(dim.id, {}).get("score", 3)
            weight = getattr(dim, "weight", 1.0)
            total_weighted_score += (float(dim_val) / 5.0 * 100.0) * weight
            total_weight += weight
        if total_weight > 0:
            overall_score = round(total_weighted_score / total_weight, 1)

        strengths = parsed.get("strengths", [])
        weaknesses = parsed.get("weaknesses", [])
        missing_concepts = parsed.get("missing_concepts", [])
        evidence_excerpts = parsed.get("evidence_excerpts", [])
        suggested_corrections = parsed.get("suggested_corrections", [])
        uncertainty_notes = parsed.get("uncertainty_notes", [])

        # Parse & verify question_feedback verbatim quotes strictly against candidate transcript for that specific turn
        from backend.app.interviews.service import InterviewService
        grouped_transcript = InterviewService.compute_grouped_transcript(interview.messages)
        grouped_by_idx = {t["question_index"]: t for t in grouped_transcript}

        raw_qf = parsed.get("question_feedback", [])
        verified_question_feedback = []

        for item in raw_qf:
            if not isinstance(item, dict):
                continue
            q_idx = int(item.get("question_index", len(verified_question_feedback) + 1))
            iq = str(item.get("interviewer_question", ""))
            ca = str(item.get("candidate_answer", ""))
            vq = str(item.get("verbatim_quote", "")).strip() if item.get("verbatim_quote") else ""
            score_val = item.get("score")
            try:
                score_int = int(score_val) if score_val is not None else None
            except (ValueError, TypeError):
                score_int = None
            critique = str(item.get("critique", ""))
            guide = str(item.get("strong_answer_guide", ""))
            res = item.get("targeted_resource")

            # Ground strictly against candidate answer for this specific question turn
            turn = grouped_by_idx.get(q_idx)
            turn_cand_text = turn.get("candidate_answer", "").strip() if turn else ""

            actual_quote: Optional[str] = None
            if turn_cand_text:
                if vq and vq.lower() in turn_cand_text.lower():
                    actual_quote = vq
                else:
                    # Ground against actual candidate sentences in this specific turn
                    substantive_sentences = [
                        s.strip() for s in turn_cand_text.split(".") if len(s.strip()) > 15
                    ]
                    if substantive_sentences:
                        actual_quote = substantive_sentences[0]
                    else:
                        actual_quote = turn_cand_text[:120]
            else:
                actual_quote = None  # No candidate text for this turn; quote unavailable

            verified_question_feedback.append({
                "question_index": q_idx,
                "score": score_int,
                "interviewer_question": iq or (turn.get("interviewer_question") if turn else f"Question {q_idx}"),
                "candidate_answer": ca or turn_cand_text,
                "verbatim_quote": actual_quote,
                "critique": critique,
                "strong_answer_guide": guide,
                "targeted_resource": res,
            })

        # Check if an evaluation already exists for this interview
        existing_res = await db.execute(
            select(Evaluation).where(Evaluation.interview_id == interview_id, Evaluation.user_id == user_id)
        )
        evaluation = existing_res.scalar_one_or_none()
        if evaluation:
            evaluation.overall_score = overall_score
            evaluation.rubric_dimension_scores = dimension_scores
            evaluation.strengths = strengths
            evaluation.weaknesses = weaknesses
            evaluation.missing_concepts = missing_concepts
            evaluation.evidence_excerpts = evidence_excerpts
            evaluation.question_feedback = verified_question_feedback
            evaluation.suggested_corrections = suggested_corrections
            evaluation.uncertainty_notes = uncertainty_notes
            evaluation.raw_llm_response = response.text
            evaluation.tokens_used = response.input_tokens + response.output_tokens
            evaluation.model_identifier = response.model_id
        else:
            evaluation = Evaluation(
                interview_id=interview_id,
                user_id=user_id,
                overall_score=overall_score,
                rubric_dimension_scores=dimension_scores,
                strengths=strengths,
                weaknesses=weaknesses,
                missing_concepts=missing_concepts,
                evidence_excerpts=evidence_excerpts,
                question_feedback=verified_question_feedback,
                suggested_corrections=suggested_corrections,
                uncertainty_notes=uncertainty_notes,
                raw_llm_response=response.text,
                tokens_used=response.input_tokens + response.output_tokens,
                model_identifier=response.model_id,
            )
            db.add(evaluation)

        # Mark interview completed if still in progress
        if interview.status == "in_progress":
            interview.status = "completed"

        # Update persistent UserSkill map for each evaluated rubric dimension using EMA
        for dim_id, dim_data in dimension_scores.items():
            dim_score_val = float(dim_data.get("score", 3))
            normalized_score = round((dim_score_val / 5.0) * 100.0, 1)
            await cls._update_user_skill(db, user_id, dim_id, normalized_score, evaluation.id)

        await db.commit()
        await db.refresh(evaluation)

        # Record tokens
        await ProviderConfigService.record_usage(
            db, user_id, response.input_tokens + response.output_tokens, response.estimated_cost_usd
        )

        return evaluation

    @classmethod
    async def _update_user_skill(
        cls,
        db: AsyncSession,
        user_id: str,
        topic: str,
        score: float,
        eval_id: str,
    ) -> None:
        """Update or create persistent UserSkill with EMA (alpha=0.3) and confidence progression. Strictly idempotent per evaluation."""
        skill_res = await db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.topic == topic)
        )
        skill = skill_res.scalar_one_or_none()
        if skill:
            # Check if this evaluation ID was already applied to prevent duplicate EMA compounding
            existing_ref = next(
                (ref for ref in (skill.evidence_refs or []) if isinstance(ref, dict) and ref.get("id") == eval_id),
                None
            )
            if existing_ref:
                existing_ref["score"] = score
                return

            skill.score = round(0.7 * skill.score + 0.3 * score, 1)
            skill.confidence = min(1.0, round(skill.confidence + 0.1, 2))
            skill.last_seen = datetime.now(timezone.utc)
            skill.evidence_refs = (skill.evidence_refs or []) + [{"type": "evaluation", "id": eval_id, "score": score}]
        else:
            skill = UserSkill(
                user_id=user_id,
                topic=topic,
                score=score,
                confidence=0.5,
                last_seen=datetime.now(timezone.utc),
                evidence_refs=[{"type": "evaluation", "id": eval_id, "score": score}]
            )
            db.add(skill)


    @staticmethod
    async def get_evaluation(db: AsyncSession, user_id: str, interview_id: str) -> Evaluation:
        result = await db.execute(
            select(Evaluation).where(Evaluation.interview_id == interview_id, Evaluation.user_id == user_id)
        )
        evaluation = result.scalar_one_or_none()
        if not evaluation:
            raise EntityNotFoundError("Evaluation for interview", interview_id)
        return evaluation

    @classmethod
    async def get_comparison(
        cls,
        db: AsyncSession,
        user_id: str,
        interview_id: str,
    ) -> EvaluationComparisonResponse:
        evaluation = await cls.get_evaluation(db, user_id, interview_id)

        # Fetch candidate self-evaluation
        self_res = await db.execute(
            select(SelfEvaluation).where(SelfEvaluation.interview_id == interview_id, SelfEvaluation.user_id == user_id)
        )
        self_eval = self_res.scalar_one_or_none()
        self_scores = self_eval.dimension_scores if self_eval else {}
        self_reflection = self_eval.reflection if self_eval else ""

        # Fetch interview to get category and transcript
        int_res = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id)
        )
        interview = int_res.scalar_one_or_none()
        category = interview.category if interview else "technical"
        rubric_dims = {d.id: d.name for d in get_rubric_for_category(category)}

        comparisons: list[DimensionComparison] = []
        for dim_id, dim_data in evaluation.rubric_dimension_scores.items():
            ai_score = dim_data.get("score", 3)
            self_score = self_scores.get(dim_id)
            delta = (ai_score - self_score) if self_score is not None else None
            name = rubric_dims.get(dim_id, dim_id.replace("_", " ").title())

            comparisons.append(
                DimensionComparison(
                    dimension_id=dim_id,
                    dimension_name=name,
                    self_score=self_score,
                    ai_score=ai_score,
                    delta=delta,
                    evidence_quote=dim_data.get("evidence_quote", ""),
                    explanation=dim_data.get("explanation", ""),
                )
            )

        # Build question-level comparisons
        from backend.app.interviews.service import InterviewService
        grouped_transcript = InterviewService.compute_grouped_transcript(interview.messages) if interview else []
        grouped_by_idx = {t["question_index"]: t for t in grouped_transcript}

        q_self_by_idx = {q.get("question_index"): q for q in (self_eval.question_evaluations or [])} if self_eval and self_eval.question_evaluations else {}
        ai_qf_by_idx = {item.get("question_index"): item for item in (evaluation.question_feedback or [])}

        all_indices = sorted(set(list(q_self_by_idx.keys()) + list(ai_qf_by_idx.keys()) + list(grouped_by_idx.keys())))
        question_comparisons: List[QuestionComparison] = []

        for q_idx in all_indices:
            q_self = q_self_by_idx.get(q_idx, {})
            q_ai = ai_qf_by_idx.get(q_idx, {})
            q_turn = grouped_by_idx.get(q_idx, {})

            iq = q_ai.get("interviewer_question") or q_turn.get("interviewer_question") or f"Question {q_idx}"
            ca = q_ai.get("candidate_answer") or q_turn.get("candidate_answer") or ""
            q_self_score = q_self.get("score")
            q_ai_score = q_ai.get("score")
            score_gap = (q_ai_score - q_self_score) if (q_ai_score is not None and q_self_score is not None) else None

            question_comparisons.append(
                QuestionComparison(
                    question_index=q_idx,
                    interviewer_question=iq,
                    candidate_answer=ca,
                    self_score=q_self_score,
                    ai_score=q_ai_score,
                    score_gap=score_gap,
                    self_strengths=q_self.get("strengths"),
                    self_missed_points=q_self.get("missed_points"),
                    self_confidence=q_self.get("confidence"),
                    ai_verbatim_quote=q_ai.get("verbatim_quote"),
                    ai_critique=q_ai.get("critique"),
                    ai_guide=q_ai.get("strong_answer_guide"),
                    targeted_resource=q_ai.get("targeted_resource"),
                )
            )

        return EvaluationComparisonResponse(
            interview_id=interview_id,
            overall_ai_score=evaluation.overall_score,
            dimensions=comparisons,
            question_comparisons=question_comparisons,
            self_reflection=self_reflection,
            strengths=evaluation.strengths,
            weaknesses=evaluation.weaknesses,
            missing_concepts=evaluation.missing_concepts,
        )
