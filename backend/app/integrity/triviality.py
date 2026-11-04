"""Server-side deterministic triviality gate for code submissions.

Counts effective lines and control-flow constructs to establish discriminative power.
"""

import re
from typing import Any, Dict, List, Set
from backend.app.integrity.config import (
    TRIVIALITY_MIN_EFFECTIVE_LINES,
    TRIVIALITY_CONTROL_CONSTRUCTS,
)


def count_effective_lines(code: str) -> int:
    """Count non-blank and non-comment lines."""
    count = 0
    in_block_comment = False

    for line in code.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue

        # Check block comments /* ... */
        if "/*" in trimmed:
            in_block_comment = True
        if in_block_comment:
            if "*/" in trimmed:
                in_block_comment = False
            continue

        # Check single-line comments (# or //)
        if trimmed.startswith("#") or trimmed.startswith("//"):
            continue

        count += 1
    return count


def detect_control_flow_constructs(code: str) -> List[str]:
    """Identify distinct control-flow keywords and constructs used in the code."""
    found: Set[str] = set()

    for keyword in TRIVIALITY_CONTROL_CONSTRUCTS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, code):
            found.add(keyword)

    # Detect recursive call pattern: def foo(...) calling foo(...)
    func_defs = re.findall(r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
    for fn in func_defs:
        # Match function name called elsewhere in the body
        calls = len(re.findall(rf"\b{fn}\s*\(", code))
        if calls > 1:
            found.add("recursion")

    return sorted(list(found))


def analyze_triviality(code: str) -> Dict[str, Any]:
    """Evaluate whether candidate solution is trivial or structurally substantial.

    Returns:
        dict containing:
        - effective_lines: int
        - constructs: list[str]
        - is_trivial: bool
        - discriminative_power: "low" | "normal"
        - target_questions: int (1 for low power, 3 for normal power)
    """
    effective_lines = count_effective_lines(code or "")
    constructs = detect_control_flow_constructs(code or "")

    is_trivial = (
        effective_lines < TRIVIALITY_MIN_EFFECTIVE_LINES
        or len(constructs) == 0
    )

    discriminative_power = "low" if is_trivial else "normal"
    target_questions = 1 if is_trivial else 3

    return {
        "effective_lines": effective_lines,
        "constructs": constructs,
        "has_control_flow": len(constructs) > 0,
        "is_trivial": is_trivial,
        "discriminative_power": discriminative_power,
        "target_questions": target_questions,
    }
