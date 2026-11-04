"""Centralized configuration and thresholds for the integrity and explanation check engine.

Rule 3 (Integrity Policy): Signals flag for human review only and never alter
scores, pass/fail status, or rankings.
"""

from typing import List

# ==========================================
# 1. Triviality Gate Thresholds (Prompt 1)
# ==========================================
# If effective lines < 8 or zero control-flow constructs, discriminative_power=low.
TRIVIALITY_MIN_EFFECTIVE_LINES: int = 8
TRIVIALITY_CONTROL_CONSTRUCTS: List[str] = [
    "for", "while", "if", "elif", "else", "def", "class",
    "try", "except", "finally", "match", "case", "switch"
]

# ==========================================
# 2. Explanation Check Thresholds (Prompt 1)
# ==========================================
# Default per-question response limit in seconds
EXPLANATION_PER_QUESTION_TIME_LIMIT_SECONDS: int = 90
# Answers shorter than this degrade confidence to low
EXPLANATION_MIN_ANSWER_CHARS: int = 20
# Audio speech-to-text confidence below this degrades confidence to low
EXPLANATION_LOW_ASR_CONFIDENCE: float = 0.65
# Flag trigger threshold: consistency strictly below this triggers review flag (if confidence >= medium)
EXPLANATION_CONSISTENCY_FLAG_THRESHOLD: float = 0.35

# ==========================================
# 3. Editor Telemetry Thresholds (Prompt 2)
# ==========================================
# A single insert adding >= 80 characters or >= 5 lines that is not typing and not suggest
TELEMETRY_LARGE_INSERT_CHARS: int = 80
TELEMETRY_LARGE_INSERT_LINES: int = 5

# Window size for density and growth analysis
TELEMETRY_WINDOW_SECONDS: int = 30
TELEMETRY_ACTIVITY_DENSITY_LOW_THRESHOLD: int = 2
TELEMETRY_GROWTH_WITHOUT_ACTIVITY_CHARS: int = 80

# Read-then-type pattern: idle gap of >= 60s followed by >= 150 chars typed within 20s
TELEMETRY_READ_THEN_TYPE_PAUSE_SECONDS: float = 60.0
TELEMETRY_READ_THEN_TYPE_CHARS: int = 150
TELEMETRY_READ_THEN_TYPE_BURST_SECONDS: float = 20.0

# Blur / focus threshold: excessive blurred duration warning
TELEMETRY_HIGH_BLURRED_SECONDS_THRESHOLD: float = 120.0

# ==========================================
# 4. Minimum Evidence Gates (Prompt 2)
# ==========================================
# Below these thresholds, return {"status": "insufficient_data"} and raise ZERO flags
MIN_EVIDENCE_EFFECTIVE_LINES: int = 10
MIN_EVIDENCE_ACTIVE_TIME_SECONDS: float = 180.0  # 3 minutes
MIN_EVIDENCE_EDIT_EVENTS: int = 200

# ==========================================
# 5. Product Honesty Statement
# ==========================================
PRODUCT_HONESTY_NOTICE: str = (
    "These signals describe editing patterns. They cannot see other devices. "
    "Someone reading from a phone and typing by hand looks like ordinary typing. "
    "Short or simple solutions give weak signals. Use as a prompt for follow-up, not a verdict."
)
