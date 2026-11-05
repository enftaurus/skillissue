"""
Deterministic interview policy, enforced in code after any LLM suggestion.

The LLM may *suggest* an adaptive action, but these rules always win:
* At most MAX_FOLLOW_UPS_PER_TOPIC follow-ups per topic, then rotate to another selected skill.
* A non-answer ("idk", "yes", gibberish) is never met with the same question reworded:
  the first one gets a simpler question, the second moves on at lower difficulty.
* Only the turn budget ends an interview. Candidate text (including injections) never can.
* Interviewer output is reduced to a single question.
"""
import re
from typing import Dict, List, Optional, Tuple

from backend.app.interviews.constants import MAX_FOLLOW_UPS_PER_TOPIC

# ---------------------------------------------------------------- intent / quality

_REPEAT_RE = re.compile(
    r"\b(repeat (the |that |your )?(question|that|it)|say (that|it) again|come again|"
    r"(didn'?t|did not|couldn'?t) (hear|catch|get) (the |that |your )?(question|that)|pardon\??$|sorry,? what\??$)",
    re.I,
)
_CLARIFY_RE = re.compile(
    r"\b(what do you mean|what does that mean|can you (clarify|explain the question|rephrase)|"
    r"(could|can) you be more specific|not sure what you('re| are) asking|what exactly are you asking|rephrase)\b",
    re.I,
)
_SOLUTION_RE = re.compile(
    r"\b(just )?(tell|give|show) me the (answer|solution|code)\b|\bwhat('?s| is) the (right |correct )?answer\b|"
    r"\b(can|could) you (just )?(answer|solve) (it|this|that)( for me)?\b",
    re.I,
)
_INJECTION_RE = re.compile(
    r"\b(ignore|disregard|forget) (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)\b|"
    r"\b(system prompt|developer message|you are now|act as|grading mode|jailbreak)\b|"
    r"\b(give|score|rate) (me|this candidate|the candidate) (a )?(100|10/10|full marks|perfect)\b|"
    r"\bstrong hire\b",
    re.I,
)
_CONCEPT_Q_RE = re.compile(
    r"^\s*(what('?s| is| are| does)|how does|how do|explain|define)\b[^.]{0,80}\?*\s*$", re.I
)
_NON_ANSWER_RE = re.compile(
    r"^\s*(idk|i ?d(o|u)n'?t know|no idea|not sure|dunno|pass|skip|no clue|i forgot|forgot|"
    r"yes|yeah|yep|no|nope|ok(ay)?|k|hmm+|um+|uh+|hi|hello|hey|bye|thanks?|lol|\.+|\?+|-+)\s*[.!?]*\s*$",
    re.I,
)


def classify_intent(text: str) -> str:
    """'repeat_question' | 'clarify' | 'asks_for_solution' | 'injection' | 'concept_question' | 'non_answer' | 'answer'"""
    t = (text or "").strip()
    if not t:
        return "non_answer"
    words = t.split()
    if _INJECTION_RE.search(t):
        return "injection"
    if len(words) <= 14 and _REPEAT_RE.search(t):
        return "repeat_question"
    if len(words) <= 20 and _CLARIFY_RE.search(t):
        return "clarify"
    if len(words) <= 20 and _SOLUTION_RE.search(t):
        return "asks_for_solution"
    if _NON_ANSWER_RE.match(t) or _looks_like_gibberish(t):
        return "non_answer"
    if len(words) <= 12 and _CONCEPT_Q_RE.match(t):
        return "concept_question"
    return "answer"


def _looks_like_gibberish(t: str) -> bool:
    words = re.findall(r"[a-zA-Z]+", t)
    if not words or len(t.split()) > 6:
        return False
    vowel_less = sum(1 for w in words if len(w) >= 4 and not re.search(r"[aeiouy]", w, re.I))
    keyboard = sum(1 for w in words if w.lower() in {"asdf", "asdfgh", "qwerty", "zxcv", "jkl", "hjkl", "lol", "xyz"})
    return (vowel_less + keyboard) >= max(1, len(words) // 2)


def answer_quality_fallback(text: str, intent: str) -> str:
    """Heuristic quality when no LLM assessment is available."""
    if intent in ("non_answer", "asks_for_solution", "injection"):
        return "non_answer"
    if intent == "concept_question":
        return "weak"
    n = len((text or "").split())
    if n < 12:
        return "weak"
    if n < 40:
        return "adequate"
    return "strong"


# ---------------------------------------------------------------- adaptive policy

def _rotate_topic(current: str, skills: List[str], statuses: Dict[str, str], asked: Dict[str, int]) -> str:
    candidates = [s for s in skills if s != current]
    if not candidates:
        return current
    fresh = [s for s in candidates if statuses.get(s) in (None, "not_started")]
    if fresh:
        return fresh[0]
    # Every topic touched: revisit the least-probed one.
    return min(candidates, key=lambda s: (asked.get(s, 0), skills.index(s)))


def apply_turn_policy(
    *,
    suggested_action: str,
    suggested_delta: int,
    quality: str,
    intent: str,
    current_topic: str,
    domain_skills: List[str],
    topic_statuses: Dict[str, str],
    topic_follow_ups: Dict[str, int],
    topic_struggles: Dict[str, int],
    topic_questions: Dict[str, int],
) -> Tuple[str, int, str, str]:
    """Return (action, difficulty_delta, next_topic, reason). Mutates the counters in place."""
    action = suggested_action if suggested_action in (
        "ask_follow_up", "next_topic", "increase_difficulty", "decrease_difficulty") else "next_topic"
    delta = max(-1, min(1, int(suggested_delta or 0)))
    reason = ""

    struggling = quality == "non_answer"
    if struggling:
        topic_struggles[current_topic] = topic_struggles.get(current_topic, 0) + 1

    follow_ups = topic_follow_ups.get(current_topic, 0)
    has_other_topics = any(s != current_topic for s in domain_skills)

    if struggling and topic_struggles[current_topic] >= 2:
        action, delta = "next_topic", -1
        reason = f"Two non-answers on '{current_topic}'. Moving on at lower difficulty instead of re-asking."
    elif struggling:
        action, delta = "decrease_difficulty", -1
        reason = f"Non-answer on '{current_topic}'. Asking a simpler, more fundamental question."
    elif action == "ask_follow_up" and follow_ups >= MAX_FOLLOW_UPS_PER_TOPIC:
        action = "next_topic" if has_other_topics else "increase_difficulty"
        reason = f"Follow-up cap ({MAX_FOLLOW_UPS_PER_TOPIC}) reached on '{current_topic}'."
    elif quality == "strong" and action == "ask_follow_up" and follow_ups >= 1:
        action = "next_topic" if has_other_topics else "increase_difficulty"
        delta = max(delta, 0)
        reason = f"Solid depth on '{current_topic}'. Covering the next competency."

    if action == "next_topic" and not has_other_topics:
        action = "increase_difficulty" if not struggling else "decrease_difficulty"

    if action == "ask_follow_up":
        topic_follow_ups[current_topic] = follow_ups + 1
        topic_statuses[current_topic] = "needs_follow_up"
        next_topic = current_topic
    elif action == "next_topic":
        topic_statuses[current_topic] = "assessed"
        next_topic = _rotate_topic(current_topic, domain_skills, topic_statuses, topic_questions)
        topic_statuses[next_topic] = "in_progress"
        topic_follow_ups[next_topic] = 0
        topic_struggles[next_topic] = 0
    else:  # difficulty change on the same topic, fresh angle (not a follow-up)
        next_topic = current_topic
        topic_statuses[current_topic] = "in_progress"

    if action == "increase_difficulty":
        delta = 1
    elif action == "decrease_difficulty":
        delta = -1
    topic_questions[next_topic] = topic_questions.get(next_topic, 0) + 1
    return action, delta, next_topic, reason or f"Policy accepted suggested action '{action}'."


# ---------------------------------------------------------------- output hygiene

_COMPOUND_SPLIT_RE = re.compile(r"[,;]?\s+(?:and|or)\s+(?=(?:how|what|why|which|where|when|who|did|do|does|can|could|would|is|are|was|were)\b)", re.I)


def enforce_single_question(text: str) -> str:
    """Reduce interviewer output to at most one question. Preamble sentences stay."""
    if not text or "```" in text or "### " in text:
        return text  # problem statements / code are left untouched
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    out: List[str] = []
    for s in sentences:
        if s.endswith("?"):
            parts = _COMPOUND_SPLIT_RE.split(s, maxsplit=1)
            q = parts[0].rstrip(" ,;")
            if not q.endswith("?"):
                q += "?"
            out.append(q)
            break
        out.append(s)
    result = " ".join(out).strip()
    return result or text


def _tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


def too_similar(a: str, b: str, threshold: float = 0.6) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= threshold


# ---------------------------------------------------------------- wrap-up

def build_wrapup_message(answer_log: Optional[List[Dict[str, str]]]) -> str:
    log = answer_log or []
    total = len(log)
    non_answers = sum(1 for a in log if a.get("quality") == "non_answer")
    weak = sum(1 for a in log if a.get("quality") == "weak")
    if total and non_answers / total >= 0.5:
        body = (f"{non_answers} of {total} answers were 'I don't know' or equivalent. That's not a verdict, it's a map: "
                "the evaluation will show exactly which fundamentals to fix first.")
    elif total and (non_answers + weak) / total >= 0.5:
        body = "Several answers stayed at the surface without numbers or trade-offs. The evaluation will point to the specific gaps."
    else:
        body = "The evaluation will compare what you said against the rubric, evidence quoted."
    return f"That's time for this round. {body} Rate yourself first with End & Self-Evaluate, then compare."


# ---------------------------------------------------------------- DSA helpers

def detect_brute_force(code: str) -> bool:
    """Nested iteration without a hash/set lookup or two-pointer pattern (indentation-aware)."""
    lines = [l for l in (code or "").splitlines() if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
    loop_re = re.compile(r"^\s*(for|while)\b|\bfor\s*\(")
    loop_indents: List[int] = []
    nested = False
    for line in lines:
        indent = len(line) - len(line.lstrip())
        loop_indents = [i for i in loop_indents if i < indent]
        if loop_re.search(line):
            if loop_indents:
                nested = True
                break
            loop_indents.append(indent)
    if not nested:
        # brace languages on one line, e.g. for(...) for(...)
        joined = " ".join(lines)
        nested = bool(re.search(r"for\s*\([^)]*\)\s*\{?[^}]*for\s*\(", joined))
    lower = "\n".join(lines).lower()
    has_hash = bool(re.search(r"\b(dict|set|hashmap|hashset|unordered_map|unordered_set|map<|counter|defaultdict|seen|lookup)\b|\{\}", lower))
    has_two_ptr = bool(re.search(r"\b(left|right|lo|hi|low|high|start|end|ptr)\b", lower) and re.search(r"(\+= 1|-= 1|\+\+|--)", lower))
    return nested and not (has_hash or has_two_ptr)
