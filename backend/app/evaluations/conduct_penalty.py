"""How an interview ended under the conduct policy shows up in its evaluation (backend/app/interviews/conduct.py)."""
from typing import Any, Dict, List, Tuple

CONDUCT_SCORE_CAP = 25.0


def misconduct_quotes(interview) -> List[str]:
    return [m.content for m in interview.messages if m.role == "user" and getattr(m, "kind", None) == "misconduct"]


def conduct_weakness(interview) -> str:
    return (f"Professional conduct: the interviewer ended the interview early ({interview.termination_reason}). "
            "In a real hiring loop this is an automatic rejection regardless of technical answers.")


def apply_penalty(interview, overall_score: float, dimension_scores: Dict[str, Dict[str, Any]], weaknesses: List[str],
                  evidence_excerpts: List[Dict[str, str]], suggested_corrections: List[str],
                  uncertainty_notes: List[str]) -> Tuple[float, Dict, List, List, List, List]:
    quotes = misconduct_quotes(interview)
    for dim_id, d in dimension_scores.items():
        if "communicat" in dim_id or "professional" in dim_id:
            d["score"] = 1
            d["explanation"] = (d.get("explanation") or "") + " (Capped at 1: interview ended for conduct.)"
    weaknesses = [conduct_weakness(interview)] + list(weaknesses)
    evidence_excerpts = [{"quote": q, "critique": "This reply triggered the conduct policy."} for q in quotes[-2:]] + list(evidence_excerpts)
    suggested_corrections = ["Treat every round as the real thing: stay on the question, keep it professional, and "
                             "never claim someone else's work. If you don't know, say so and reason out loud."] + list(suggested_corrections)
    uncertainty_notes = list(uncertainty_notes) + [f"Overall score capped at {CONDUCT_SCORE_CAP:.0f}% because the interview "
                                                   "was ended under the conduct policy."]
    return min(overall_score, CONDUCT_SCORE_CAP), dimension_scores, weaknesses, evidence_excerpts, suggested_corrections, uncertainty_notes


def conduct_only_fields(interview, rubric) -> Dict[str, Any]:
    """Evaluation for an interview ended before any real answer: nothing technical to grade, no model call."""
    quotes = misconduct_quotes(interview)
    dims = {d.id: {"score": 1, "max_score": 5, "explanation": "Not assessable: the interview was ended for conduct before "
                   "any real answer.", "evidence_quote": quotes[0] if quotes else ""} for d in rubric}
    return {
        "overall_score": 0.0, "rubric_dimension_scores": dims, "strengths": [],
        "weaknesses": [conduct_weakness(interview)], "missing_concepts": [],
        "evidence_excerpts": [{"quote": q, "critique": "This reply triggered the conduct policy."} for q in quotes],
        "question_feedback": [], "weakness_analysis": [],
        "suggested_corrections": ["Treat every round as the real thing: answer the question asked, keep it professional, "
                                  "and if you don't know, say so and reason out loud."],
        "uncertainty_notes": ["No technical answers were given, so only conduct was assessed."],
    }
