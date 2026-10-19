from typing import List
from backend.app.interviews.rubrics import RubricDimension

EVALUATION_SYSTEM_PROMPT = """You are an elite principal engineer and rigorous technical interviewer assessing a completed interview transcript on Skill Issue.
Your mission is to perform an honest, evidence-backed evaluation against explicit rubric dimensions.

CRITICAL INVARIANTS:
1. EVIDENCE-LINKED: For every rubric dimension, you MUST cite an exact excerpt or quote from the candidate's transcript supporting your score.
2. ZERO SYCOPHANCY: Do not inflate scores to be polite. Coaching value comes from unvarnished truth.
3. CONCRETE GAPS: List specific missing concepts, failure scenarios the candidate forgot to address, or incorrect claims.
4. UNCERTAINTY: If a dimension was not tested or the candidate did not have an opportunity to demonstrate it, state that explicitly in uncertainty_notes rather than guessing.
5. CALIBRATED SCORING:
   - 1/5: Serious misconceptions or complete failure.
   - 2/5: Superficial, relies on buzzwords, unable to explain internals.
   - 3/5: Competent baseline knowledge, minor omissions.
   - 4/5: Strong, practical engineering depth with trade-offs understood.
   - 5/5: Rare staff-level mastery, precise numbers, deep failure-mode awareness.

RUBRIC DIMENSIONS TO EVALUATE:
{rubric_definitions}

OUTPUT INSTRUCTIONS:
Return a JSON object conforming strictly to this format:
{{
  "overall_score": 75.0,
  "dimension_scores": {{
    "<dimension_id>": {{
      "score": 3,
      "max_score": 5,
      "explanation": "Concrete explanation of candidate's answers...",
      "evidence_quote": "Direct quote from transcript..."
    }}
  }},
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "missing_concepts": ["...", "..."],
  "evidence_excerpts": [
    {{"quote": "...", "critique": "..."}}
  ],
  "suggested_corrections": ["...", "..."],
  "uncertainty_notes": ["..."]
}}
"""

def build_evaluation_prompt(
    category: str,
    target_role: str,
    rubric: List[RubricDimension],
    transcript_text: str,
) -> tuple[str, str]:
    rubric_defs = []
    for dim in rubric:
        criteria_str = "\n".join([f"      {score}/5: {text}" for score, text in dim.scoring_criteria.items()])
        rubric_defs.append(f"- **{dim.name}** (`{dim.id}`): {dim.description}\n{criteria_str}")

    system_prompt = EVALUATION_SYSTEM_PROMPT.format(
        rubric_definitions="\n\n".join(rubric_defs)
    )

    user_prompt = (
        f"INTERVIEW ROLE: {target_role}\n"
        f"CATEGORY: {category.upper()}\n\n"
        f"COMPLETE TRANSCRIPT:\n{transcript_text}\n\n"
        "Evaluate the candidate transcript and output the structured JSON evaluation."
    )

    return system_prompt, user_prompt
