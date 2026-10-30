import re
from typing import Dict, Any, List, Optional
from backend.app.projects.schemas import PromptEvaluationItem, ProjectPromptAnalysisResponse

AMATEUR_PATTERNS = [
    r"^fix\b",
    r"fix it\b",
    r"fix my code\b",
    r"doesn'?t work\b",
    r"not working\b",
    r"why (is it )?broken\b",
    r"give me (the )?code\b",
    r"write (the )?code\b",
    r"code it (for me)?\b",
    r"solve (this|it)\b",
    r"what do i do\b",
    r"^help\b",
    r"^why\?*$",
]

TECHNICAL_KEYWORDS = [
    "redis", "sorted set", "zadd", "zremrangebyscore", "zcard", "sliding window",
    "ratelimit", "429", "retry-after", "timestamp", "expiration", "ttl",
    "priority", "backoff", "exponential", "dead-letter", "dlq", "dispatcher",
    "assertionerror", "test_", "sequence_id", "status", "retrying", "traceback"
]

def analyze_single_prompt(prompt_index: int, prompt_text: str, project_id: str) -> PromptEvaluationItem:
    cleaned = prompt_text.strip()
    words = cleaned.split()
    lower = cleaned.lower()

    # Check for amateur patterns
    matches_pattern = any(re.search(pat, lower) for pat in AMATEUR_PATTERNS)
    is_too_short = len(words) < 6 and not any(kw in lower for kw in TECHNICAL_KEYWORDS)
    contains_code_or_trace = "```" in cleaned or "assertion" in lower or "error" in lower or "test" in lower

    if (matches_pattern or is_too_short) and not contains_code_or_trace:
        is_amateur = True
        score = 25 if len(words) < 4 else 38
        critique = (
            "Extremely vague umbrella prompt. It supplies zero diagnostic context, "
            "omits file names and stack traces, and shifts the burden of debugging entirely to the AI."
        )
        tip = "Always mention the failing test name, the unexpected status or return value, and your hypothesis."
        
        if project_id == "distributed-rate-limiter":
            rewrite = (
                "In `src/limiter.py`, `test_blocks_requests_exceeding_limit` fails because the 6th request returns 200 instead of 429. "
                "How should I use `self.storage.zremrangebyscore` to evict expired timestamps before checking `zcard`?"
            )
        else:
            rewrite = (
                "In `src/dispatcher.py`, `test_priority_scheduling` returned the low-priority task first. "
                "How should I sort `self.queue` in `get_next_task()` using `(task.priority.value, task.sequence_id)`?"
            )
    elif any(kw in lower for kw in TECHNICAL_KEYWORDS) and len(words) >= 6:
        is_amateur = False
        score = 88 if "test" in lower or "src/" in lower else 78
        critique = (
            "Clear, domain-specific engineering prompt. References concrete architectural primitives or error conditions "
            "rather than asking for a blanket solution."
        )
        tip = "Include specific line numbers and the exact failure assertion diff to make iterations even faster."
        rewrite = f"Based on the system requirements in {project_id}: {cleaned} (Provide exact line numbers in your query)."
    else:
        is_amateur = False
        score = 62
        critique = (
            "Acceptable conversational query, but could be significantly sharper with explicit file references or test failure logs."
        )
        tip = "Prefix questions with the component you are examining (e.g. 'In src/limiter.py: ...')."
        rewrite = f"In the context of {project_id}, {cleaned} Specifically, how does this affect the CI/CD test harness?"

    return PromptEvaluationItem(
        prompt_index=prompt_index,
        user_prompt=cleaned,
        critique=critique,
        improvement_tip=tip,
        better_rewrite=rewrite,
        is_amateurish=is_amateur,
        score=score
    )

def evaluate_candidate_prompts(
    project_id: str,
    conversation_history: List[Dict[str, str]],
    final_test_passed: bool = False,
    time_spent_seconds: int = 0
) -> ProjectPromptAnalysisResponse:
    # Extract only user prompt turns
    user_prompts = [
        m.get("content", "") for m in conversation_history
        if m.get("role") == "user" and m.get("content", "").strip()
    ]

    if not user_prompts:
        return ProjectPromptAnalysisResponse(
            overall_score=70,
            grade="Autonomous (No Prompts Recorded)",
            rubric_breakdown={
                "context_specification": 15,
                "error_diagnostic_inclusion": 15,
                "problem_decomposition": 20,
                "engineering_autonomy": 20,
            },
            summary="You completed the challenge without asking questions to the pair-programming assistant. While autonomous execution is valuable, practice formulating precise architectural queries to accelerate debugging in collaborative pair-programming interviews.",
            evaluated_prompts=[],
            key_takeaways=[
                "Use the AI assistant to clarify architectural edge cases without treating it as a code generator.",
                "Paste test assertion failure diffs to quickly isolate algorithmic regressions.",
                "Specify target files and function names to get tightly scoped answers."
            ]
        )

    evaluated_items = [
        analyze_single_prompt(i + 1, p, project_id)
        for i, p in enumerate(user_prompts)
    ]

    avg_score = int(sum(item.score for item in evaluated_items) / len(evaluated_items))
    amateur_count = sum(1 for item in evaluated_items if item.is_amateurish)

    # Determine grade
    if avg_score >= 85:
        grade = "Senior Systems Thinker (High Precision)"
    elif avg_score >= 70:
        grade = "Competent Collaborator (Solid Context)"
    elif avg_score >= 50:
        grade = "Developing (Needs Precision & Error Logs)"
    else:
        grade = "Amateur Prompting (Vague / Blanket Requests)"

    # Rubric scores (out of 25 each)
    has_error_logs = any("assertion" in p.lower() or "fail" in p.lower() for p in user_prompts)
    has_file_refs = any("src/" in p or ".py" in p for p in user_prompts)

    context_spec = min(25, int(avg_score * 0.25) + (5 if has_file_refs else 0))
    error_diag = min(25, int(avg_score * 0.25) + (5 if has_error_logs else 0))
    decomp = min(25, int(avg_score * 0.25) + 3)
    autonomy = max(10, min(25, 25 - (amateur_count * 5)))

    overall = min(100, max(20, int((context_spec + error_diag + decomp + autonomy))))

    if amateur_count > 0:
        summary = (
            f"Detected {amateur_count} amateurish prompt(s) characterized by vague phrasing ('fix it', 'why is it broken') "
            f"without stack traces or file pointers. In senior engineering interviews, treat the AI pair programmer as a staff teammate: "
            f"frame questions with clear hypotheses, state observed vs expected behavior, and specify the relevant codebase files."
        )
    else:
        summary = (
            "Strong prompting methodology. You consistently referenced domain entities and focused on specific algorithmic components "
            "rather than dumping broad questions onto the assistant."
        )

    takeaways = [
        "Include the exact failing test name and assertion diff instead of saying 'it doesn't work'.",
        "Reference specific classes, methods, and file paths (e.g. `src/limiter.py:is_rate_limited`).",
        "Formulate a working hypothesis: ask 'Why does eviction fail when timestamps match?' rather than 'How do I fix this?'."
    ]

    return ProjectPromptAnalysisResponse(
        overall_score=overall,
        grade=grade,
        rubric_breakdown={
            "context_specification": context_spec,
            "error_diagnostic_inclusion": error_diag,
            "problem_decomposition": decomp,
            "engineering_autonomy": autonomy,
        },
        summary=summary,
        evaluated_prompts=evaluated_items,
        key_takeaways=takeaways
    )
