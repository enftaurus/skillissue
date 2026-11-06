"""Explanation Check service: question generation, code ground verification,
structured LLM judging, deterministic confidence scoring, and review flagging.

Rule 3 (Integrity Policy): Signals flag for human review only and never alter
scores, pass/fail status, rankings, or invitations.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.app.core.errors import NotFoundError, AuthorizationError, ValidationError
from backend.app.database.models import (
    ExplanationCheck,
    CandidateAssessment,
    CodingSubmission,
    User,
    AssessmentPipeline,
    utc_now,
)
from backend.app.integrity.config import (
    EXPLANATION_PER_QUESTION_TIME_LIMIT_SECONDS,
    EXPLANATION_MIN_ANSWER_CHARS,
    EXPLANATION_LOW_ASR_CONFIDENCE,
    EXPLANATION_CONSISTENCY_FLAG_THRESHOLD,
    PRODUCT_HONESTY_NOTICE,
)
from backend.app.integrity.triviality import analyze_triviality
from backend.app.integrity.prompts import (
    build_question_generation_prompt,
    build_judge_prompt,
)
from backend.app.integrity.schemas import (
    ExplanationQuestion,
    CreateExplanationCheckRequest,
    SubmitAnswersRequest,
)
from backend.app.providers.factory import ModelFactory
from backend.app.providers.mock_provider import MockProvider

logger = logging.getLogger("skillissue.integrity")


class ExplanationService:

    @staticmethod
    async def create_explanation_check(
        req: CreateExplanationCheckRequest,
        db: AsyncSession,
        current_user: Optional[User] = None,
        candidate_assessment: Optional[CandidateAssessment] = None,
    ) -> ExplanationCheck:
        """Create explanation check, inspect code, run triviality gate, generate questions."""
        code: str = ""
        problem_title: str = req.problem_title or "Algorithmic Implementation"
        problem_statement: str = req.problem_statement or problem_title

        # 1. Load code securely from server records (NEVER trust code from request body)
        if req.mode == "assessment" or candidate_assessment or req.candidate_assessment_id:
            ca_id = candidate_assessment.id if candidate_assessment else req.candidate_assessment_id
            query = select(CandidateAssessment).where(CandidateAssessment.id == ca_id)
            res = await db.execute(query)
            ca = res.scalar_one_or_none()
            if not ca:
                raise NotFoundError("Candidate assessment not found")
            candidate_assessment = ca

            # Look for code in round_results or oa_submitted_code
            round_data = (ca.round_results or {}).get(str(req.round_key)) or {}
            sub = round_data.get("submission") or {}
            code = (
                sub.get("code")
                or sub.get("oa_submitted_code")
                or ca.oa_submitted_code
                or ""
            )
            problem_title = ca.oa_problem_title or problem_title
            problem_statement = f"Problem: {problem_title}"
        else:
            # Practice mode in student portal: load from CodingSubmission
            if not current_user:
                raise AuthorizationError("Authentication required for practice mode")

            query = select(CodingSubmission).where(
                CodingSubmission.id == req.submission_ref,
                CodingSubmission.user_id == current_user.id,
            )
            res = await db.execute(query)
            sub = res.scalar_one_or_none()
            if not sub:
                raise NotFoundError("Coding submission not found or does not belong to user")
            code = sub.code
            problem_title = sub.problem_title or problem_title
            problem_statement = f"Problem: {problem_title}"

        if not code or not code.strip():
            raise ValidationError("No valid candidate code found for this submission reference")

        # 2. Run deterministic Triviality Gate
        triviality = analyze_triviality(code)
        target_questions = triviality["target_questions"]
        discriminative_power = triviality["discriminative_power"]

        # 3. Generate questions via LLM provider layer
        questions = await ExplanationService._generate_and_verify_questions(
            problem=problem_statement,
            code=code,
            n_questions=target_questions,
            user=current_user,
            db=db,
            candidate_assessment_id=candidate_assessment.id if candidate_assessment else None,
        )

        # 4. Save ExplanationCheck record
        check = ExplanationCheck(
            user_id=current_user.id if current_user else None,
            candidate_assessment_id=candidate_assessment.id if candidate_assessment else None,
            round_key=req.round_key,
            submission_ref=req.submission_ref,
            mode=req.mode,
            status="pending",
            questions=[q.model_dump() for q in questions],
            answers=[],
            evaluation=None,
            confidence=None,
            discriminative_power=discriminative_power,
            model_info=None,
        )
        db.add(check)
        await db.commit()
        await db.refresh(check)
        return check

    @staticmethod
    async def _resolve_provider(db: AsyncSession, user: Optional[User], candidate_assessment_id: Optional[str]):
        """Practice: the user's model. Assessment: the hiring team's model (they own the drive). Else offline mock."""
        try:
            if user:
                return await ModelFactory.get_for_user(db, user.id)
            if candidate_assessment_id:
                from backend.app.database.models import AssessmentPipeline
                owner = (await db.execute(
                    select(AssessmentPipeline.created_by_user_id)
                    .join(CandidateAssessment, CandidateAssessment.pipeline_id == AssessmentPipeline.id)
                    .where(CandidateAssessment.id == candidate_assessment_id))).scalar_one_or_none()
                if owner:
                    return await ModelFactory.get_for_user(db, owner)
        except Exception:
            pass
        return MockProvider()

    @staticmethod
    async def _generate_and_verify_questions(
        problem: str,
        code: str,
        n_questions: int,
        user: Optional[User],
        db: AsyncSession,
        candidate_assessment_id: Optional[str] = None,
    ) -> List[ExplanationQuestion]:
        """Generate questions and verify code_reference occurs verbatim in code. Retry once if not."""
        provider = await ExplanationService._resolve_provider(db, user, candidate_assessment_id)

        prompt = build_question_generation_prompt(problem, code, n_questions)

        # Attempt 1
        raw_res = await provider.generate_json(
            prompt=prompt["user_message"],
            system_prompt=prompt["system_prompt"],
        )
        parsed = raw_res.parsed_json or {}
        raw_questions = parsed.get("questions", [])

        verified, all_valid = ExplanationService._verify_code_references(raw_questions, code)

        if not all_valid:
            logger.warning("[ExplanationService] Code reference verification failed on attempt 1. Retrying once...")
            # Attempt 2 with explicit reminder
            retry_prompt = prompt["user_message"] + "\n\nCRITICAL: Every 'code_reference' MUST be an exact substring from <candidate_code>."
            raw_res = await provider.generate_json(
                prompt=retry_prompt,
                system_prompt=prompt["system_prompt"],
            )
            parsed = raw_res.parsed_json or {}
            raw_questions = parsed.get("questions", [])
            verified, all_valid = ExplanationService._verify_code_references(raw_questions, code)

        if not verified or len(verified) == 0:
            logger.warning("[ExplanationService] Generating grounded template fallback questions.")
            verified = ExplanationService._generate_grounded_fallback_questions(code, problem, n_questions)

        return verified[:n_questions]

    @staticmethod
    def _verify_code_references(raw_questions: List[Dict[str, Any]], code: str) -> Tuple[List[ExplanationQuestion], bool]:
        """Verify each question's code_reference exists in candidate code."""
        verified: List[ExplanationQuestion] = []
        all_valid = True

        for item in raw_questions:
            if not isinstance(item, dict):
                continue
            q_type = str(item.get("type", "rationale")).lower()
            text = str(item.get("text", "")).strip()
            ref = str(item.get("code_reference", "")).strip()

            if not text:
                continue

            # Verify substring presence in code (case-insensitive fallback check)
            if ref and (ref in code or ref.lower() in code.lower()):
                verified.append(ExplanationQuestion(type=q_type, text=text, code_reference=ref))
            else:
                # Missing or fabricated code_reference
                all_valid = False

        return verified, all_valid

    @staticmethod
    def _salient_identifiers(code: str) -> Tuple[str, str]:
        """
        The two names a reviewer would ask about: functions and variables the candidate defined and uses most.
        Imported modules, builtins and I/O plumbing (`sys`, `input`, `print`, `main`) are never the interesting part.
        """
        noise = {"def", "class", "return", "import", "from", "for", "while", "if", "else", "elif", "in", "and", "or",
                 "not", "True", "False", "None", "self", "sys", "stdin", "stdout", "input", "print", "main", "range",
                 "len", "int", "str", "list", "dict", "set", "map", "split", "read", "readline", "strip", "append",
                 "enumerate", "sorted", "min", "max", "sum", "std", "cin", "cout", "endl", "include", "using",
                 "namespace", "public", "static", "void", "String", "System", "out", "println", "Scanner", "args",
                 "nextInt", "vector", "auto", "const", "bits", "stdc"}
        imported = set(re.findall(r"^\s*(?:import|from)\s+([\w.]+)", code, re.M))
        imported |= {n.strip() for m in re.findall(r"^\s*from\s+\S+\s+import\s+(.+)$", code, re.M) for n in m.split(",")}
        defined = re.findall(r"\bdef\s+([A-Za-z_]\w*)", code) + re.findall(r"(?:^|[;{(])\s*(?:[A-Za-z_][\w<>:]*\s+)?([A-Za-z_]\w*)\s*(?:\[[^\]]*\]|\([^)]*\))?\s*[+\-*/]?=(?!=)", code, re.M)
        counts: Dict[str, int] = {}
        for name in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{1,}\b", code):
            counts[name] = counts.get(name, 0) + 1
        ranked = [n for n in dict.fromkeys(defined) if n not in noise and n not in imported and len(n) > 1]
        ranked.sort(key=lambda n: -counts.get(n, 0))
        if not ranked:
            ranked = [n for n, _ in sorted(counts.items(), key=lambda kv: -kv[1]) if n not in noise and n not in imported and len(n) > 2]
        primary = ranked[0] if ranked else "solution"
        return primary, (ranked[1] if len(ranked) > 1 else primary)

    @staticmethod
    def _generate_grounded_fallback_questions(code: str, problem: str, n_questions: int) -> List[ExplanationQuestion]:
        """Template-based questions grounded in actual code identifiers extracted from code."""
        primary_ref, secondary_ref = ExplanationService._salient_identifiers(code)
        questions = [
            ExplanationQuestion(
                type="rationale",
                text=f"Why did you choose your specific data structures and approach around '{primary_ref}' rather than a simpler iterative or recursive alternative?",
                code_reference=primary_ref,
            ),
            ExplanationQuestion(
                type="mutation",
                text=f"If the problem constraints were modified to allow duplicate elements or streaming input, what exact lines around '{secondary_ref}' would require changes?",
                code_reference=secondary_ref,
            ),
            ExplanationQuestion(
                type="behaviour",
                text=f"Walk me through how '{primary_ref}' behaves on an empty input or single-element boundary case.",
                code_reference=primary_ref,
            ),
        ]
        return questions[:n_questions]

    @staticmethod
    async def submit_answers(
        check_id: str,
        req: SubmitAnswersRequest,
        db: AsyncSession,
        current_user: Optional[User] = None,
        candidate_assessment: Optional[CandidateAssessment] = None,
    ) -> ExplanationCheck:
        """Submit candidate answers, enforce one-time submission, enforce time limits, and run LLM judge."""
        query = select(ExplanationCheck).where(ExplanationCheck.id == check_id)
        res = await db.execute(query)
        check = res.scalar_one_or_none()
        if not check:
            raise NotFoundError("Explanation check not found")

        # Check authorization
        if check.candidate_assessment_id:
            if candidate_assessment and check.candidate_assessment_id != candidate_assessment.id:
                raise AuthorizationError("Access denied to this assessment's explanation check")
        elif check.user_id:
            if not current_user or check.user_id != current_user.id:
                raise AuthorizationError("Access denied to this explanation check")

        # 1. Enforce single submission: reject repeated answers
        if check.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ANSWERS_ALREADY_SUBMITTED: Explanation answers have already been submitted and cannot be modified.",
            )

        # 2. Enforce per-question time limit (default 90s per question + 30s grace)
        now = utc_now()
        time_limit_seconds = (len(check.questions) * EXPLANATION_PER_QUESTION_TIME_LIMIT_SECONDS) + 30
        elapsed_seconds = (now - check.created_at).total_seconds()
        if elapsed_seconds > time_limit_seconds:
            logger.warning(f"[ExplanationCheck] Answers submitted late: {elapsed_seconds}s > {time_limit_seconds}s.")
            check.status = "answered"
            check.answered_at = now
            check.answers = [a.model_dump(mode="json") for a in req.answers]
            check.confidence = "low"
            check.evaluation = {
                "error": "SUBMISSION_TIMEOUT",
                "message": "Answers were submitted past the allotted time limit.",
                "explanation_consistency": 0.0,
            }
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SUBMISSION_TIMEOUT: Allotted response window for explanation check has expired.",
            )

        check.status = "answered"
        check.answered_at = now
        check.answers = [a.model_dump(mode="json") for a in req.answers]

        # 3. Load code for judging
        code = await ExplanationService._load_code_for_check(check, db)

        # 4. Run LLM Judge
        try:
            await ExplanationService._evaluate_with_judge(check, code, current_user, db)
        except Exception as e:
            logger.exception(f"[ExplanationService] Evaluation failed: {e}")
            check.status = "not_evaluated"
            check.evaluation = None
            check.confidence = None

        await db.commit()
        await db.refresh(check)
        return check

    @staticmethod
    async def _load_code_for_check(check: ExplanationCheck, db: AsyncSession) -> str:
        """Load code for this explanation check from database."""
        if check.candidate_assessment_id:
            q = select(CandidateAssessment).where(CandidateAssessment.id == check.candidate_assessment_id)
            res = await db.execute(q)
            ca = res.scalar_one_or_none()
            if ca:
                round_data = (ca.round_results or {}).get(str(check.round_key)) or {}
                sub = round_data.get("submission") or {}
                return (
                    sub.get("code")
                    or sub.get("oa_submitted_code")
                    or ca.oa_submitted_code
                    or ""
                )
        elif check.user_id:
            q = select(CodingSubmission).where(CodingSubmission.id == check.submission_ref)
            res = await db.execute(q)
            cs = res.scalar_one_or_none()
            if cs:
                return cs.code or ""
        return ""

    @staticmethod
    async def _evaluate_with_judge(
        check: ExplanationCheck,
        code: str,
        user: Optional[User],
        db: AsyncSession,
    ) -> None:
        """Evaluate candidate answers against code using LLM judge, and compute metrics on server."""
        provider = await ExplanationService._resolve_provider(db, user, check.candidate_assessment_id)

        qa_pairs = []
        for q in check.questions:
            q_idx = len(qa_pairs)
            # Find matching answer
            matched_ans = next((a for a in check.answers if a.get("question_index") == q_idx), None)
            qa_pairs.append({
                "type": q.get("type", "rationale"),
                "question_text": q.get("text", ""),
                "answer_text": matched_ans.get("text", "") if matched_ans else "",
            })

        judge_prompt = build_judge_prompt(
            problem=f"Challenge ({check.round_key})",
            code=code,
            qa_pairs=qa_pairs,
        )

        res = await provider.generate_json(
            prompt=judge_prompt["user_message"],
            system_prompt=judge_prompt["system_prompt"],
        )
        parsed = res.parsed_json or {}
        q_evals = parsed.get("question_evaluations", [])

        if not q_evals:
            # Retry once
            logger.warning("[ExplanationJudge] Empty evaluations returned, retrying judge once...")
            res = await provider.generate_json(
                prompt=judge_prompt["user_message"] + "\n\nCRITICAL: Return question_evaluations matching schema.",
                system_prompt=judge_prompt["system_prompt"],
            )
            parsed = res.parsed_json or {}
            q_evals = parsed.get("question_evaluations", [])

        if not q_evals:
            check.status = "not_evaluated"
            check.evaluation = None
            check.confidence = None
            return

        # ==========================================
        # 5. SERVER-SIDE METRICS DERIVATION
        # ==========================================
        # The LLM judge NEVER decides the final score or verdict.
        total_consistency = 0.0
        total_accuracy = 0.0
        total_depth = 0.0
        valid_eval_count = 0

        verified_q_evals = []
        for idx, item in enumerate(q_evals):
            acc = max(0, min(4, int(item.get("accuracy", 2))))
            cons = max(0, min(4, int(item.get("consistency", 2))))
            dep = max(0, min(4, int(item.get("depth", 2))))
            quote = str(item.get("evidence_quote", ""))[:200]
            ref = str(item.get("code_reference", ""))
            critique = str(item.get("critique", ""))

            total_consistency += cons
            total_accuracy += acc
            total_depth += dep
            valid_eval_count += 1

            verified_q_evals.append({
                "question_index": idx,
                "accuracy": acc,
                "consistency": cons,
                "depth": dep,
                "evidence_quote": quote,
                "code_reference": ref,
                "critique": critique,
            })

        num_questions = max(1, len(check.questions))
        # Normalized 0.0 to 1.0 consistency score
        explanation_consistency = round(total_consistency / (4.0 * num_questions), 3)
        avg_accuracy = round(total_accuracy / (4.0 * num_questions), 3)
        avg_depth = round(total_depth / (4.0 * num_questions), 3)

        # Confidence Computation:
        # Drops to low when: discriminative_power is low, answers are very short,
        # ASR confidence is low, or fewer than 2 questions were answered.
        confidence = "medium"
        answered_non_empty = [a for a in check.answers if len(str(a.get("text", "")).strip()) >= EXPLANATION_MIN_ANSWER_CHARS]
        asr_confidences = [a.get("asr_confidence") for a in check.answers if a.get("asr_confidence") is not None]

        if check.discriminative_power == "low":
            confidence = "low"
        elif len(answered_non_empty) < 2 and num_questions >= 2:
            confidence = "low"
        elif asr_confidences and (sum(asr_confidences) / len(asr_confidences)) < EXPLANATION_LOW_ASR_CONFIDENCE:
            confidence = "low"
        elif len(verified_q_evals) >= 3 and len(answered_non_empty) >= 3 and avg_depth >= 0.7:
            # High confidence only on substantial answers across all questions
            confidence = "high"

        check.status = "evaluated"
        check.evaluated_at = utc_now()
        check.confidence = confidence
        check.model_info = {
            "model_id": res.model_id,
            "tokens_used": (res.input_tokens or 0) + (res.output_tokens or 0),
        }
        check.evaluation = {
            "question_evaluations": verified_q_evals,
            "explanation_consistency": explanation_consistency,
            "average_accuracy": avg_accuracy,
            "average_depth": avg_depth,
            "coaching_what_went_well": parsed.get("coaching_what_went_well", ["Explained implementation mechanics"]),
            "coaching_what_to_revisit": parsed.get("coaching_what_to_revisit", ["Review alternative edge case trade-offs"]),
        }

        # ==========================================
        # 6. FLAGGING (Assessment Mode Only)
        # ==========================================
        # Rule 3 (Integrity Policy): Signals flag for human review only and never
        # alter scores, pass/fail status, or rankings.
        if check.mode == "assessment" and check.candidate_assessment_id:
            await ExplanationService._apply_assessment_review_flag(
                check=check,
                db=db,
            )

    @staticmethod
    async def _apply_assessment_review_flag(check: ExplanationCheck, db: AsyncSession) -> None:
        """Add review flag to CandidateAssessment ONLY if confidence >= medium and consistency < threshold."""
        q = select(CandidateAssessment).where(CandidateAssessment.id == check.candidate_assessment_id)
        res = await db.execute(q)
        ca = res.scalar_one_or_none()
        if not ca:
            return

        current_signals = dict(ca.integrity_signals or {})
        existing_flags = list(current_signals.get("flags") or [])

        eval_data = check.evaluation or {}
        consistency = eval_data.get("explanation_consistency", 1.0)
        confidence = check.confidence or "low"

        # Check conditions: confidence at least medium AND consistency below threshold (default 0.35)
        if confidence in {"medium", "high"} and consistency < EXPLANATION_CONSISTENCY_FLAG_THRESHOLD:
            # Extract evidence
            evidence_items = []
            q_evals = eval_data.get("question_evaluations", [])
            for q_dict in check.questions:
                q_idx = len(evidence_items)
                ev = next((e for e in q_evals if e.get("question_index") == q_idx), {})
                ans = next((a for a in check.answers if a.get("question_index") == q_idx), {})
                evidence_items.append({
                    "question": q_dict.get("text", ""),
                    "answer_excerpt": ev.get("evidence_quote") or str(ans.get("text", ""))[:150],
                    "code_reference": ev.get("code_reference") or q_dict.get("code_reference", ""),
                })

            review_flag = {
                "code": "EXPLANATION_MISMATCH",
                "severity": "review",
                "confidence": confidence,
                "evidence": evidence_items,
                "limits": "This signal can be wrong, especially on short solutions or with nervous candidates; it is a prompt to look, not a finding.",
            }

            # Avoid duplicates
            if not any(f.get("code") == "EXPLANATION_MISMATCH" for f in existing_flags):
                existing_flags.append(review_flag)

            current_signals["flags"] = existing_flags
            current_signals["status"] = "evaluated"
            current_signals["explanation_check"] = {
                "status": "evaluated",
                "consistency": consistency,
                "confidence": confidence,
            }
        else:
            if not existing_flags:
                current_signals["status"] = "insufficient_data" if confidence == "low" else "evaluated"
            current_signals["explanation_check"] = {
                "status": "insufficient_data" if confidence == "low" else "evaluated",
                "consistency": consistency,
                "confidence": confidence,
            }

        current_signals["product_honesty"] = PRODUCT_HONESTY_NOTICE
        ca.integrity_signals = current_signals
        # NOTE: round_results scores, pass/fail status, and rankings are explicitly left UNTOUCHED!

    @staticmethod
    async def get_explanation_check(
        check_id: str,
        db: AsyncSession,
        current_user: Optional[User] = None,
        candidate_assessment: Optional[CandidateAssessment] = None,
    ) -> Dict[str, Any]:
        """Fetch explanation check respecting candidate vs recruiter view and tenant isolation."""
        q = select(ExplanationCheck).where(ExplanationCheck.id == check_id)
        res = await db.execute(q)
        check = res.scalar_one_or_none()
        if not check:
            raise NotFoundError("Explanation check not found")

        # Assessment Mode vs Practice Mode views
        is_candidate_view = False
        if candidate_assessment:
            if check.candidate_assessment_id != candidate_assessment.id:
                raise AuthorizationError("Access denied: assessment link mismatch")
            is_candidate_view = True
        elif current_user:
            if current_user.role == "candidate":
                if check.user_id != current_user.id and check.candidate_assessment_id:
                    raise AuthorizationError("Access denied: candidate cannot view other candidates")
                is_candidate_view = True
            elif current_user.role == "recruiter":
                # Recruiter view: enforce tenant isolation
                if check.candidate_assessment_id:
                    pipe_q = (
                        select(AssessmentPipeline)
                        .join(CandidateAssessment, CandidateAssessment.pipeline_id == AssessmentPipeline.id)
                        .where(CandidateAssessment.id == check.candidate_assessment_id)
                    )
                    pipe_res = await db.execute(pipe_q)
                    pipeline = pipe_res.scalar_one_or_none()
                    if not pipeline or pipeline.tenant_id != current_user.tenant_id:
                        raise AuthorizationError("Access denied: assessment belongs to another organisation")
                else:
                    if check.user_id != current_user.id:
                        raise AuthorizationError("Access denied: practice check belongs to another user")

        if is_candidate_view:
            if check.mode == "assessment":
                # Candidate in assessment mode sees only neutral submission status
                return {
                    "id": check.id,
                    "round_key": check.round_key,
                    "submission_ref": check.submission_ref,
                    "mode": check.mode,
                    "status": "submitted" if check.status in {"answered", "evaluated"} else check.status,
                    "discriminative_power": check.discriminative_power,
                    "questions": check.questions,
                    "time_limit_per_question": EXPLANATION_PER_QUESTION_TIME_LIMIT_SECONDS,
                    "message": "Thanks, your answers are submitted.",
                    "coaching": None,
                }
            else:
                # Candidate in practice mode sees coaching feedback
                coaching_info = None
                if check.evaluation:
                    coaching_info = {
                        "what_went_well": check.evaluation.get("coaching_what_went_well", []),
                        "what_to_revisit": check.evaluation.get("coaching_what_to_revisit", []),
                        "consistency_rating": "Strong explanation" if check.evaluation.get("explanation_consistency", 0) >= 0.7 else "Review alignment",
                    }
                return {
                    "id": check.id,
                    "round_key": check.round_key,
                    "submission_ref": check.submission_ref,
                    "mode": check.mode,
                    "status": check.status,
                    "discriminative_power": check.discriminative_power,
                    "questions": check.questions,
                    "time_limit_per_question": EXPLANATION_PER_QUESTION_TIME_LIMIT_SECONDS,
                    "coaching": coaching_info,
                    "message": "Coaching feedback generated.",
                }

        # Recruiter / Admin Full View
        return {
            "id": check.id,
            "user_id": check.user_id,
            "candidate_assessment_id": check.candidate_assessment_id,
            "round_key": check.round_key,
            "submission_ref": check.submission_ref,
            "mode": check.mode,
            "status": check.status,
            "confidence": check.confidence,
            "discriminative_power": check.discriminative_power,
            "questions": check.questions,
            "answers": check.answers,
            "evaluation": check.evaluation,
            "model_info": check.model_info,
            "created_at": check.created_at,
            "answered_at": check.answered_at,
            "evaluated_at": check.evaluated_at,
        }
