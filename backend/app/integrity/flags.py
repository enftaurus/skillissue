"""Integrity flag evaluation module.

Turns telemetry and explanation features into human-review-only flags.
Strictly adheres to Rule 3 (Integrity Policy):
- Review flags are prompts for follow-up, never automatic verdicts.
- Scores, pass/fail status, and rankings are NEVER modified by flags.
- Minimum evidence thresholds ensure small solutions produce silence, not noise.
- Multi-family correlation rules govern confidence (never emits high in this release).
"""

from typing import Any, Dict, List, Optional, Set
from backend.app.integrity.config import (
    MIN_EVIDENCE_EFFECTIVE_LINES,
    MIN_EVIDENCE_ACTIVE_TIME_SECONDS,
    MIN_EVIDENCE_EDIT_EVENTS,
    TELEMETRY_HIGH_BLURRED_SECONDS_THRESHOLD,
    PRODUCT_HONESTY_NOTICE,
)


def evaluate_telemetry_flags(
    features: Dict[str, Any],
    effective_lines: int,
    total_events: int,
    code_hash_match: bool,
    missing_batches_count: int = 0,
    explanation_mismatch: bool = False,
) -> Dict[str, Any]:
    """Turn telemetry features into review flags using multi-family correlation and minimum evidence gates.

    Returns:
        dict containing:
        - status: "evaluated" | "insufficient_data"
        - reason: Optional[str]
        - flags: list[dict]
        - triggered_families: list[str]
        - overall_confidence: "low" | "medium" | null
        - product_honesty: str
    """
    focus = features.get("focus") or {}
    active_time_s = focus.get("active_time_seconds", 0.0)

    # ==========================================
    # 1. MINIMUM EVIDENCE GATE
    # ==========================================
    # If effective code is under 10 lines, or active time is under 3 minutes,
    # or there are fewer than 200 edit events, return insufficient_data and raise ZERO flags.
    if (
        effective_lines < MIN_EVIDENCE_EFFECTIVE_LINES
        or active_time_s < MIN_EVIDENCE_ACTIVE_TIME_SECONDS
        or total_events < MIN_EVIDENCE_EDIT_EVENTS
    ):
        reasons = []
        if effective_lines < MIN_EVIDENCE_EFFECTIVE_LINES:
            reasons.append(f"Solution length ({effective_lines} effective lines) is under the minimum threshold of {MIN_EVIDENCE_EFFECTIVE_LINES} lines.")
        if active_time_s < MIN_EVIDENCE_ACTIVE_TIME_SECONDS:
            reasons.append(f"Active editing time ({round(active_time_s)}s) is under the 3-minute minimum baseline.")
        if total_events < MIN_EVIDENCE_EDIT_EVENTS:
            reasons.append(f"Recorded event sample ({total_events} events) is below the minimum 200-event reliability gate.")

        return {
            "status": "insufficient_data",
            "reason": " ".join(reasons) or "Insufficient telemetry sample for reliable signal extraction.",
            "flags": [],
            "triggered_families": [],
            "overall_confidence": None,
            "product_honesty": PRODUCT_HONESTY_NOTICE,
        }

    # ==========================================
    # 2. FEATURE INSPECTION & FAMILY IDENTIFICATION
    # ==========================================
    flags: List[Dict[str, Any]] = []
    triggered_families: Set[str] = set()

    large_inserts = features.get("large_inserts") or []
    growth_no_activity = features.get("growth_without_activity_windows") or []
    typed_ratio = features.get("typed_ratio", 1.0)
    read_then_type_episodes = features.get("read_then_type_episodes") or []
    total_blurred_s = focus.get("total_blurred_seconds", 0.0)

    # Family 1: insertion_source (large_insert, growth_without_activity, low typed_ratio)
    has_large_insert = len(large_inserts) > 0
    has_growth_no_act = len(growth_no_activity) > 0

    if has_large_insert:
        triggered_families.add("insertion_source")
        total_pasted_chars = sum(i.get("inserted_chars", 0) for i in large_inserts)
        flags.append({
            "code": "LARGE_UNTYPED_INSERT",
            "severity": "review",
            "family": "insertion_source",
            "evidence": {
                "untyped_insert_count": len(large_inserts),
                "total_untyped_chars": total_pasted_chars,
                "first_insert_timestamp": large_inserts[0].get("timestamp"),
                "sample_sizes": [i.get("inserted_chars") for i in large_inserts[:3]],
            },
            "limits": (
                "Candidate may have written boilerplate or algorithm scaffolding in an external scratchpad. "
                "Does not prove unauthorized assistance."
            ),
        })

    if has_growth_no_act:
        triggered_families.add("insertion_source")
        flags.append({
            "code": "GROWTH_WITHOUT_ACTIVITY",
            "severity": "review",
            "family": "insertion_source",
            "evidence": {
                "flagged_windows_count": len(growth_no_activity),
                "windows": growth_no_activity[:3],
            },
            "limits": "Document content expanded without active typing or navigation events. May reflect background paste or sync.",
        })

    # Family 2: cadence (read_then_type, low revision_ratio, flat cadence)
    if len(read_then_type_episodes) > 0:
        triggered_families.add("cadence")
        flags.append({
            "code": "READ_THEN_TYPE_PATTERN",
            "severity": "review",
            "family": "cadence",
            "evidence": {
                "episode_count": len(read_then_type_episodes),
                "episodes": read_then_type_episodes[:3],
            },
            "limits": (
                "Candidate paused for >= 60 seconds followed by high-speed typing burst. "
                "Candidate may have planned solution on paper or whiteboard before typing."
            ),
        })

    # Family 3: focus (high blurred duration)
    if total_blurred_s > TELEMETRY_HIGH_BLURRED_SECONDS_THRESHOLD:
        triggered_families.add("focus")
        flags.append({
            "code": "HIGH_BLURRED_TIME",
            "severity": "info",
            "family": "focus",
            "evidence": {
                "total_blurred_seconds": total_blurred_s,
                "blur_count": focus.get("blur_count", 0),
            },
            "limits": "Candidate switched windows or tabs. Multi-monitor setups and system popups frequently trigger this without malice.",
        })

    # Info flag: telemetry completeness
    if not code_hash_match or missing_batches_count > 0:
        flags.append({
            "code": "TELEMETRY_INCOMPLETE",
            "severity": "info",
            "family": "completeness",
            "evidence": {
                "hash_match": code_hash_match,
                "missing_batches": missing_batches_count,
            },
            "limits": "Reconstructed editor deltas did not perfectly match submitted code. Client network dropouts or browser throttling may cause lost packets.",
        })

    # Family 4: explanation (from explanation check cross-exam)
    if explanation_mismatch:
        triggered_families.add("explanation")

    # ==========================================
    # 3. MULTI-FAMILY CONFIDENCE RULES
    # ==========================================
    # - Single family: low confidence
    # - Two or more independent families: medium confidence
    # - NEVER emit high in this release (signals not yet validated against real outcomes)
    # - READ_THEN_TYPE_PATTERN alone is ALWAYS low
    num_families = len(triggered_families)
    if num_families >= 2:
        overall_confidence = "medium"
    elif num_families == 1:
        overall_confidence = "low"
    else:
        overall_confidence = None

    # Attach computed confidence to each review flag
    for f in flags:
        if f.get("severity") == "review":
            if f.get("code") == "READ_THEN_TYPE_PATTERN" and num_families == 1:
                f["confidence"] = "low"
            else:
                f["confidence"] = overall_confidence or "low"
        else:
            f["confidence"] = "info"

    return {
        "status": "evaluated",
        "flags": flags,
        "triggered_families": sorted(list(triggered_families)),
        "overall_confidence": overall_confidence,
        "product_honesty": PRODUCT_HONESTY_NOTICE,
    }
