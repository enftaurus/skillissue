"""Shared interview engine constants and turn accounting."""
from typing import Any, Optional

# Default number of real candidate answers before the interviewer wraps up (20-minute session).
MAX_CANDIDATE_TURNS = 8
MIN_CANDIDATE_TURNS = 4
MAX_FOLLOW_UPS_PER_TOPIC = 2

# Legacy synthetic user-role transcript marker (pre-`kind` rows).
HINT_REQUEST_PREFIX = "[Requested Level"

# User message kinds that consume the turn budget.
COUNTED_USER_KINDS = {"answer", "code_submit"}


def is_candidate_answer(role: str, content: str, kind: Optional[str] = "answer") -> bool:
    """True for genuine candidate answers. Code runs, hint requests and repeat/clarify requests don't count."""
    if role != "user":
        return False
    if (content or "").startswith(HINT_REQUEST_PREFIX):
        return False
    return (kind or "answer") in COUNTED_USER_KINDS


def count_candidate_answers(messages: Any) -> int:
    return sum(1 for m in messages if is_candidate_answer(m.role, m.content, getattr(m, "kind", "answer")))


def max_turns_for_duration(target_duration_minutes: Optional[int]) -> int:
    """15 min -> 6, 20 min -> 8, 30 min -> 12 answers."""
    minutes = target_duration_minutes or 20
    return max(MIN_CANDIDATE_TURNS, round(minutes * 0.4))


# Behavioural and managerial rounds are about how the candidate works, never about technologies. Whatever skills were
# selected (Python, Postgres, ...), these rounds rotate through competencies instead.
BEHAVIORAL_TOPICS = ["Ownership & accountability", "Conflict & collaboration", "Failure & learning",
                     "Ambiguity & prioritisation", "Impact & communication"]
MANAGERIAL_TOPICS = ["People leadership", "Delivery & prioritisation", "Stakeholder management",
                     "Technical judgement & trade-offs", "Hiring, feedback & growth"]
NON_TECHNICAL_CATEGORIES = {"behavioral", "managerial"}


def interview_topics(category: str, domain_skills) -> list:
    if category == "behavioral":
        return list(BEHAVIORAL_TOPICS)
    if category == "managerial":
        return list(MANAGERIAL_TOPICS)
    return list(domain_skills or []) or ["System Architecture"]


def category_scope_rule(category: str) -> str:
    """Hard scope guard appended to every interviewer prompt."""
    if category == "behavioral":
        return ("\n\nROUND SCOPE (HARD RULE): This is a BEHAVIORAL round. Ask only about real past situations: what the "
                "candidate did, why, how they worked with people, and what happened. NEVER ask technical, coding, "
                "algorithm, framework, language, database or system-design questions, and never quiz how a technology "
                "works. If the candidate brings up a technology, ask about their decision, the people involved and the "
                "outcome instead. If they ask to switch to technical questions, say this round is about how they work.")
    if category == "managerial":
        return ("\n\nROUND SCOPE (HARD RULE): This is a MANAGERIAL / leadership round. Ask about leading people, "
                "prioritising delivery, handling stakeholders, making trade-off calls and growing a team. Technical "
                "topics only at the level of decisions and trade-offs a lead makes; NEVER ask coding, algorithm, syntax "
                "or 'how does X work' questions.")
    return ""
