import asyncio
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Interview, Evaluation, SelfEvaluation, UserSkill, RetestSession, InterviewMessage
from backend.app.evaluations.schemas import (
    SelfEvaluationCreate, EvaluationComparisonResponse, DimensionComparison, QuestionComparison
)
from backend.app.evaluations.prompts import build_evaluation_prompt
from backend.app.core.config import settings
from backend.app.interviews.rubrics import get_rubric_for_category
from backend.app.providers.factory import ModelFactory
from backend.app.providers.service import ProviderConfigService
from backend.app.core.errors import EntityNotFoundError, AppException, ProviderError
from backend.app.core.logging import logger


def rubric_score_to_pct(score) -> float:
    """Map a 1-5 rubric score onto 0-100 so the floor is 0, not 20 (1 -> 0, 3 -> 50, 5 -> 100)."""
    try:
        v = float(score)
    except (TypeError, ValueError):
        v = 3.0
    v = max(1.0, min(5.0, v))
    return (v - 1.0) / 4.0 * 100.0

from backend.app.evaluations.credibility import candidate_text_of, confidence, evidence_check, merge_passes


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

        real_answers = [m for m in interview.messages if m.role == "user" and getattr(m, "kind", "answer") in ("answer", "code_submit")]
        if getattr(interview, "termination_reason", None) and not real_answers:
            return await cls._conduct_only_evaluation(db, user_id, interview)

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

        def validate_evaluation_schema(data: Any) -> bool:
            if not isinstance(data, dict):
                return False
            if "error" in data:
                return False
            dim_scores = data.get("dimension_scores")
            if not isinstance(dim_scores, dict) or not dim_scores:
                return False
            if "overall_score" not in data:
                return False
            try:
                float(data["overall_score"])
            except (ValueError, TypeError):
                return False
            return True

        provider = await ModelFactory.get_for_user(db, user_id, task_type="evaluation")
        second_pass: Optional[Dict[str, Any]] = None
        second_tokens = 0
        if settings.EVAL_CONSISTENCY_CHECK:
            # Two independent passes in parallel; disagreements are flagged and averaged.
            first_res, second_res = await asyncio.gather(
                provider.generate_json(prompt=user_prompt, system_prompt=system_prompt),
                provider.generate_json(prompt=user_prompt, system_prompt=system_prompt),
                return_exceptions=True,
            )
            if isinstance(first_res, Exception):
                raise first_res
            response = first_res
            if not isinstance(second_res, Exception):
                second_tokens = (second_res.input_tokens or 0) + (second_res.output_tokens or 0)
                sp = second_res.parsed_json or {}
                if not validate_evaluation_schema(response.parsed_json or {}) and validate_evaluation_schema(sp):
                    # First pass malformed, second valid: use it instead of spending a retry.
                    response, second_tokens = second_res, (first_res.input_tokens or 0) + (first_res.output_tokens or 0)
                elif isinstance(sp, dict) and isinstance(sp.get("dimension_scores"), dict):
                    second_pass = sp["dimension_scores"]
        else:
            response = await provider.generate_json(prompt=user_prompt, system_prompt=system_prompt)
        parsed = response.parsed_json or {}

        # D7: Validate model output against JSON schema; on failure retry once
        if not validate_evaluation_schema(parsed):
            logger.warning(f"Evaluation JSON failed initial schema validation for interview {interview_id}. Retrying once...")
            retry_system_prompt = system_prompt + (
                "\n\nCRITICAL RETRY INSTRUCTION: Your previous response violated the JSON schema. "
                "You MUST return strictly a JSON object conforming to the schema with 'overall_score' (number) and 'dimension_scores' (object)."
            )
            retry_response = await provider.generate_json(prompt=user_prompt, system_prompt=retry_system_prompt)
            parsed = retry_response.parsed_json or {}
            response = retry_response

        # If retry still fails schema validation, store status="not_evaluated" and score=None
        if not validate_evaluation_schema(parsed):
            logger.error(f"Evaluation failed schema validation after retry for interview {interview_id}. Storing status='not_evaluated'.")
            existing_res = await db.execute(
                select(Evaluation).where(Evaluation.interview_id == interview_id, Evaluation.user_id == user_id)
            )
            failed_eval = existing_res.scalar_one_or_none()
            if failed_eval:
                failed_eval.overall_score = None
                failed_eval.status = "not_evaluated"
                failed_eval.rubric_dimension_scores = {}
                failed_eval.uncertainty_notes = ["Model evaluation failed JSON schema validation after retry. Stored as not_evaluated."]
                failed_eval.raw_llm_response = response.text if response else None
            else:
                failed_eval = Evaluation(
                    interview_id=interview_id,
                    user_id=user_id,
                    overall_score=None,
                    status="not_evaluated",
                    rubric_dimension_scores={},
                    strengths=[],
                    weaknesses=[],
                    missing_concepts=[],
                    evidence_excerpts=[],
                    question_feedback=[],
                    suggested_corrections=[],
                    uncertainty_notes=["Model evaluation failed JSON schema validation after retry. Stored as not_evaluated."],
                    weakness_analysis=[],
                    raw_llm_response=response.text if response else None,
                    stored_transcript=transcript_text,
                    tokens_used=response.input_tokens + response.output_tokens if response else 0,
                    model_identifier=response.model_id if response else getattr(provider, "model_id", "unknown")
                )
                db.add(failed_eval)
            interview.status = "completed"
            await db.commit()
            await db.refresh(failed_eval)
            return failed_eval

        overall_score = float(parsed["overall_score"])
        dimension_scores, consistency = merge_passes(parsed.get("dimension_scores", {}), second_pass)

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
            total_weighted_score += rubric_score_to_pct(dim_val) * weight
            total_weight += weight
        if total_weight > 0:
            overall_score = round(total_weighted_score / total_weight, 1)

        strengths = parsed.get("strengths", [])
        weaknesses = parsed.get("weaknesses", [])
        missing_concepts = parsed.get("missing_concepts", [])
        evidence_excerpts = parsed.get("evidence_excerpts", [])
        suggested_corrections = parsed.get("suggested_corrections", [])
        uncertainty_notes = parsed.get("uncertainty_notes", [])
        if getattr(interview, "termination_reason", None):
            from backend.app.evaluations.conduct_penalty import apply_penalty
            (overall_score, dimension_scores, weaknesses, evidence_excerpts, suggested_corrections,
             uncertainty_notes) = apply_penalty(interview, overall_score, dimension_scores, weaknesses,
                                                evidence_excerpts, suggested_corrections, uncertainty_notes)

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
            quote_verified = False
            if turn_cand_text:
                if vq and vq.lower() in turn_cand_text.lower():
                    actual_quote = vq
                    quote_verified = True
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
                # False when the model's quote wasn't in the transcript and a sentence of the answer was substituted.
                "quote_verified": quote_verified,
                "critique": critique,
                "strong_answer_guide": guide,
                "targeted_resource": res,
            })

        # Fallback guarantee: Ensure EVERY question turn has an entry in question_feedback
        seen_q_indices = {item["question_index"] for item in verified_question_feedback}
        for turn in grouped_transcript:
            q_idx = turn["question_index"]
            if q_idx not in seen_q_indices and turn.get("candidate_answer"):
                cand_text = turn.get("candidate_answer", "").strip()
                default_score = 2 if overall_score < 40 else (3 if overall_score < 70 else 4)
                verified_question_feedback.append({
                    "question_index": q_idx,
                    "score": default_score,
                    "interviewer_question": turn.get("interviewer_question") or f"Question {q_idx}",
                    "candidate_answer": cand_text,
                    "verbatim_quote": cand_text[:120] if cand_text else None,
                    "critique": "Explanation provided was high-level or unverified; lacked concrete operational details.",
                    "strong_answer_guide": "A staff-level answer explains specific architectural mechanisms, cites trade-offs, and addresses edge-case failure modes.",
                    "targeted_resource": interview.domain_skills[0] if interview.domain_skills else "System Design",
                })

        verified_question_feedback.sort(key=lambda x: x["question_index"])

        import uuid as uuid_mod
        raw_weakness_analysis = parsed.get("weakness_analysis", [])
        verified_weakness_analysis = []
        for item in raw_weakness_analysis:
            if isinstance(item, dict) and item.get("topic"):
                verified_weakness_analysis.append({
                    "id": str(uuid_mod.uuid4()),
                    "topic": str(item.get("topic")).strip(),
                    "subtopic": str(item.get("subtopic")).strip() if item.get("subtopic") else None,
                    "evidence": str(item.get("evidence", "")).strip(),
                    "gap_explanation": str(item.get("gap_explanation", "")).strip(),
                    "learning_objective": str(item.get("learning_objective", f"Master {item.get('topic')}")).strip(),
                    "suggested_exercise": str(item.get("suggested_exercise")).strip() if item.get("suggested_exercise") else None,
                    "confidence": str(item.get("confidence", "medium")).lower(),
                    "status": "identified",
                })

        if not verified_weakness_analysis and weaknesses:
            for w in weaknesses[:4]:
                verified_weakness_analysis.append({
                    "id": str(uuid_mod.uuid4()),
                    "topic": w,
                    "subtopic": None,
                    "evidence": evidence_excerpts[0].get("quote", "") if evidence_excerpts else "Demonstrated in interview discussion",
                    "gap_explanation": w,
                    "learning_objective": f"Strengthen core fundamentals in {w}",
                    "suggested_exercise": f"Build a practical implementation addressing edge cases in {w}",
                    "confidence": "medium",
                    "status": "identified",
                })

        # Check if an evaluation already exists for this interview
        existing_res = await db.execute(
            select(Evaluation).where(Evaluation.interview_id == interview_id, Evaluation.user_id == user_id)
        )
        evaluation = existing_res.scalar_one_or_none()
        cand_text = candidate_text_of(interview)
        answers = [m for m in interview.messages if m.role == "user" and getattr(m, "kind", "answer") in ("answer", "code_submit")]
        credibility = {
            "consistency": consistency,
            "evidence": evidence_check(evidence_excerpts, cand_text),
            "question_quotes": {"total": len(verified_question_feedback),
                                "verified": sum(1 for q in verified_question_feedback if q.get("quote_verified"))},
        }
        credibility["confidence"] = confidence(
            len(answers), len(cand_text.split()), credibility["evidence"],
            credibility["question_quotes"]["verified"], credibility["question_quotes"]["total"], consistency)
        if consistency.get("divergent_dimensions"):
            uncertainty_notes = list(uncertainty_notes) + [
                f"Two independent grading passes disagreed on: {', '.join(consistency['divergent_dimensions'])}. Scores were averaged."]

        if evaluation:
            evaluation.status = "completed"
            evaluation.credibility = credibility
            evaluation.overall_score = overall_score
            evaluation.rubric_dimension_scores = dimension_scores
            evaluation.strengths = strengths
            evaluation.weaknesses = weaknesses
            evaluation.missing_concepts = missing_concepts
            evaluation.evidence_excerpts = evidence_excerpts
            evaluation.question_feedback = verified_question_feedback
            evaluation.weakness_analysis = verified_weakness_analysis
            evaluation.suggested_corrections = suggested_corrections
            evaluation.uncertainty_notes = uncertainty_notes
            evaluation.raw_llm_response = response.text
            evaluation.stored_transcript = transcript_text
            evaluation.tokens_used = response.input_tokens + response.output_tokens + second_tokens
            evaluation.model_identifier = response.model_id
        else:
            evaluation = Evaluation(
                interview_id=interview_id,
                user_id=user_id,
                status="completed",
                overall_score=overall_score,
                rubric_dimension_scores=dimension_scores,
                strengths=strengths,
                weaknesses=weaknesses,
                missing_concepts=missing_concepts,
                evidence_excerpts=evidence_excerpts,
                question_feedback=verified_question_feedback,
                weakness_analysis=verified_weakness_analysis,
                suggested_corrections=suggested_corrections,
                uncertainty_notes=uncertainty_notes,
                credibility=credibility,
                raw_llm_response=response.text,
                stored_transcript=transcript_text,
                tokens_used=response.input_tokens + response.output_tokens + second_tokens,
                model_identifier=response.model_id,
            )
            db.add(evaluation)

        # Mark interview completed if still in progress
        if interview.status == "in_progress":
            interview.status = "completed"

        # Update persistent UserSkill map for each evaluated rubric dimension using EMA
        for dim_id, dim_data in dimension_scores.items():
            dim_score_val = float(dim_data.get("score", 3))
            normalized_score = round(rubric_score_to_pct(dim_score_val), 1)
            await cls._update_user_skill(db, user_id, dim_id, normalized_score, evaluation.id)

        await db.commit()
        await db.refresh(evaluation)

        # Record tokens
        await ProviderConfigService.record_usage(
            db, user_id, response.input_tokens + response.output_tokens + second_tokens,
            response.estimated_cost_usd * (2 if second_tokens else 1)
        )

        return evaluation

    @classmethod
    async def _conduct_only_evaluation(cls, db: AsyncSession, user_id: str, interview: Interview) -> Evaluation:
        from backend.app.evaluations.conduct_penalty import conduct_only_fields
        fields = conduct_only_fields(interview, get_rubric_for_category(interview.category))
        transcript = "\n\n".join(f"{'Interviewer' if m.role == 'assistant' else 'Candidate'}: {m.content}" for m in interview.messages)
        evaluation = (await db.execute(select(Evaluation).where(Evaluation.interview_id == interview.id,
                                                                Evaluation.user_id == user_id))).scalar_one_or_none()
        if evaluation is None:
            evaluation = Evaluation(interview_id=interview.id, user_id=user_id)
            db.add(evaluation)
        for k, v in fields.items():
            setattr(evaluation, k, v)
        evaluation.status = "completed"
        evaluation.stored_transcript = transcript
        evaluation.raw_llm_response = ""
        evaluation.tokens_used = 0
        evaluation.model_identifier = "conduct-policy"
        evaluation.credibility = {"confidence": {"level": "high", "reasons": ["Ended under the conduct policy; the replies are quoted verbatim."]}}
        await db.commit()
        await db.refresh(evaluation)
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

        # Load interview transcript messages
        int_res = await db.execute(
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id == interview_id)
        )
        interview = int_res.scalar_one_or_none()
        if interview and interview.messages:
            from backend.app.interviews.service import InterviewService
            evaluation.transcript_turns = InterviewService.compute_grouped_transcript(interview.messages)
            if not evaluation.stored_transcript:
                lines = [f"{'Interviewer' if m.role == 'assistant' else 'Candidate'}: {m.content}" for m in interview.messages]
                evaluation.stored_transcript = "\n\n".join(lines)
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
            delta = (self_score - ai_score) if self_score is not None else None
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
            score_gap = (q_self_score - q_ai_score) if (q_ai_score is not None and q_self_score is not None) else None

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
            weakness_analysis=evaluation.weakness_analysis or [],
            stored_transcript=evaluation.stored_transcript,
            transcript_turns=grouped_transcript,
        )

    @staticmethod
    async def initiate_retest(
        db: AsyncSession,
        user_id: str,
        evaluation_id: str,
        weakness_topic: str,
        baseline_score: Optional[float] = None,
    ) -> RetestSession:
        eval_res = await db.execute(
            select(Evaluation).where(Evaluation.id == evaluation_id)
        )
        evaluation = eval_res.scalar_one_or_none()
        if not evaluation:
            raise EntityNotFoundError("Evaluation", evaluation_id)

        # Confirm interview belongs to user
        interview_res = await db.execute(
            select(Interview).where(Interview.id == evaluation.interview_id, Interview.user_id == user_id)
        )
        original_interview = interview_res.scalar_one_or_none()
        if not original_interview:
            raise AppException("Access denied or interview not found", code="FORBIDDEN", status_code=403)

        effective_baseline = baseline_score if baseline_score is not None else evaluation.overall_score

        # Provision a short, focused retest run by the real interview engine (persona, policy, budget).
        category = original_interview.category if original_interview.category in ("technical", "behavioral", "managerial") else "technical"
        retest_interview = Interview(
            user_id=user_id,
            mode="domain",
            category=category,
            title=f"Retest: {weakness_topic}",
            domain_skills=[weakness_topic],
            target_role=original_interview.target_role or "Software Engineer",
            difficulty=original_interview.difficulty or "intermediate",
            status="in_progress",
            target_duration_minutes=10,
        )
        db.add(retest_interview)
        await db.flush()

        from backend.app.interviews.agent.service import InterviewAgentService
        initial_q = await InterviewAgentService.start_interview(db=db, user_id=user_id, interview=retest_interview)
        db.add(InterviewMessage(
            interview_id=retest_interview.id,
            role="assistant",
            content=initial_q,
            question_index=1,
            kind="question",
        ))

        retest_session = RetestSession(
            user_id=user_id,
            original_interview_id=original_interview.id,
            original_evaluation_id=evaluation.id,
            retest_interview_id=retest_interview.id,
            weakness_topic=weakness_topic,
            baseline_score=effective_baseline,
            retest_score=0.0,
            delta_score=0.0,
            verified_improvements=[],
            status="in_progress",
        )
        db.add(retest_session)
        await db.commit()
        await db.refresh(retest_session)
        return retest_session

    @staticmethod
    async def get_retests_for_evaluation(
        db: AsyncSession,
        user_id: str,
        evaluation_id: str,
    ) -> List[RetestSession]:
        result = await db.execute(
            select(RetestSession)
            .where(RetestSession.original_evaluation_id == evaluation_id, RetestSession.user_id == user_id)
            .order_by(RetestSession.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def complete_retest_and_calculate_delta(
        db: AsyncSession,
        user_id: str,
        retest_session_id: str,
    ) -> RetestSession:
        result = await db.execute(
            select(RetestSession).where(RetestSession.id == retest_session_id, RetestSession.user_id == user_id)
        )
        retest_session = result.scalar_one_or_none()
        if not retest_session:
            raise EntityNotFoundError("RetestSession", retest_session_id)

        if not retest_session.retest_interview_id:
            raise AppException("No retest interview associated with this session", code="INVALID_STATE", status_code=400)

        eval_res = await db.execute(
            select(Evaluation).where(Evaluation.interview_id == retest_session.retest_interview_id)
        )
        retest_eval = eval_res.scalar_one_or_none()
        if not retest_eval:
            return retest_session

        retest_session.retest_score = retest_eval.overall_score
        retest_session.delta_score = round(retest_eval.overall_score - retest_session.baseline_score, 1)
        retest_session.status = "completed"
        improvements = list(retest_eval.strengths or [])
        if not improvements:
            improvements = ["Demonstrated clearer grasp of edge cases and reduced ambiguity under follow-up questioning."]
        retest_session.verified_improvements = improvements[:4]

        await db.commit()
        await db.refresh(retest_session)
        return retest_session
