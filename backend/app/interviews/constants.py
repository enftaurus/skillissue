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
