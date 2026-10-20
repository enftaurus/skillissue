from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Interview, Evaluation, SelfEvaluation, UserSkill
from backend.app.evaluations.schemas import (
    SelfEvaluationCreate, EvaluationComparisonResponse, DimensionComparison
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

        # Check if already self-evaluated
        existing = await db.execute(
            select(SelfEvaluation).where(SelfEvaluation.interview_id == data.interview_id)
        )
        self_eval = existing.scalar_one_or_none()
        if self_eval:
            self_eval.dimension_scores = data.dimension_scores
            self_eval.reflection = data.reflection or ""
        else:
            self_eval = SelfEvaluation(
                interview_id=data.interview_id,
                user_id=user_id,
                dimension_scores=data.dimension_scores,
                reflection=data.reflection or "",
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

        strengths = parsed.get("strengths", [])
        weaknesses = parsed.get("weaknesses", [])
        missing_concepts = parsed.get("missing_concepts", [])
        evidence_excerpts = parsed.get("evidence_excerpts", [])
        suggested_corrections = parsed.get("suggested_corrections", [])
        uncertainty_notes = parsed.get("uncertainty_notes", [])

        # Parse & verify question_feedback verbatim quotes against candidate transcript
        candidate_turns = [m.content for m in interview.messages if m.role == "user"]
        candidate_full_text = " ".join(candidate_turns)
        raw_qf = parsed.get("question_feedback", [])
        verified_question_feedback = []

        for item in raw_qf:
            if not isinstance(item, dict):
                continue
            q_idx = int(item.get("question_index", len(verified_question_feedback) + 1))
            iq = str(item.get("interviewer_question", ""))
            ca = str(item.get("candidate_answer", ""))
            vq = str(item.get("verbatim_quote", "")).strip()
            critique = str(item.get("critique", ""))
            guide = str(item.get("strong_answer_guide", ""))
            res = item.get("targeted_resource")

            # Validate that verbatim quote actually exists in candidate's responses
            if vq and vq.lower() in candidate_full_text.lower():
                actual_quote = vq
            elif 0 <= (q_idx - 1) < len(candidate_turns):
                # Extract first substantive sentence from corresponding candidate response
                cand_turn = candidate_turns[q_idx - 1]
                sentences = [s.strip() for s in cand_turn.split(".") if len(s.strip()) > 10]
                actual_quote = sentences[0] if sentences else cand_turn[:120]
            elif candidate_turns:
                actual_quote = candidate_turns[0][:120]
            else:
                actual_quote = vq

            verified_question_feedback.append({
                "question_index": q_idx,
                "interviewer_question": iq,
                "candidate_answer": ca,
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
        """Update or create persistent UserSkill with EMA (alpha=0.3) and confidence progression."""
        skill_res = await db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.topic == topic)
        )
        skill = skill_res.scalar_one_or_none()
        if skill:
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

        # Fetch interview category to get friendly dimension names
        int_res = await db.execute(select(Interview).where(Interview.id == interview_id))
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

        return EvaluationComparisonResponse(
            interview_id=interview_id,
            overall_ai_score=evaluation.overall_score,
            dimensions=comparisons,
            self_reflection=self_reflection,
            strengths=evaluation.strengths,
            weaknesses=evaluation.weaknesses,
            missing_concepts=evaluation.missing_concepts,
        )
