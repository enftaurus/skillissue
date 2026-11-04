"""Pure functions computing editor telemetry features over the event stream.
Fully deterministic and unit-tested.
"""

import math
from typing import Any, Dict, List, Tuple
from backend.app.integrity.config import (
    TELEMETRY_LARGE_INSERT_CHARS,
    TELEMETRY_LARGE_INSERT_LINES,
    TELEMETRY_WINDOW_SECONDS,
    TELEMETRY_ACTIVITY_DENSITY_LOW_THRESHOLD,
    TELEMETRY_GROWTH_WITHOUT_ACTIVITY_CHARS,
    TELEMETRY_READ_THEN_TYPE_PAUSE_SECONDS,
    TELEMETRY_READ_THEN_TYPE_CHARS,
    TELEMETRY_READ_THEN_TYPE_BURST_SECONDS,
)


def compute_typed_ratio(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate ratio of characters entered via typing vs paste vs suggest vs unattributed.

    Returns:
        dict with typed_ratio, typed_chars, paste_chars, suggest_chars, unattributed_chars, total_inserted_chars
    """
    typed_chars = 0
    paste_chars = 0
    suggest_chars = 0
    unattributed_chars = 0

    for e in events:
        ins = e.get("inserted_length", 0) or 0
        if ins <= 0:
            continue

        src = str(e.get("source", "typing")).lower()
        if src == "typing":
            typed_chars += ins
        elif src == "paste":
            paste_chars += ins
        elif src == "suggest":
            suggest_chars += ins
        else:
            unattributed_chars += ins

    total = typed_chars + paste_chars + suggest_chars + unattributed_chars
    ratio = round(typed_chars / max(1, total), 3) if total > 0 else 1.0

    return {
        "typed_ratio": ratio,
        "typed_chars": typed_chars,
        "paste_chars": paste_chars,
        "suggest_chars": suggest_chars,
        "unattributed_chars": unattributed_chars,
        "total_inserted_chars": total,
    }


def compute_large_inserts(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify changes adding >= 80 chars or >= 5 lines that are not typing and not suggest."""
    large_inserts = []

    for e in events:
        ins_len = e.get("inserted_length", 0) or 0
        line_delta = e.get("line_count_delta", 0) or 0
        src = str(e.get("source", "")).lower()

        # Typing and suggestions are expected to be normal editing
        if src in {"typing", "suggest"}:
            continue

        if ins_len >= TELEMETRY_LARGE_INSERT_CHARS or line_delta >= TELEMETRY_LARGE_INSERT_LINES:
            large_inserts.append({
                "timestamp": e.get("timestamp", 0),
                "inserted_chars": ins_len,
                "lines_added": line_delta,
                "source": src or "paste",
            })

    return large_inserts


def compute_activity_density(
    events: List[Dict[str, Any]],
    window_seconds: int = TELEMETRY_WINDOW_SECONDS,
) -> List[Dict[str, Any]]:
    """Compute count of key + cursor + selection + scroll + edit events per 30-second window."""
    if not events:
        return []

    timestamps = [e.get("timestamp", 0) for e in events]
    min_ts = min(timestamps)
    max_ts = max(timestamps)

    # Determine time base: if timestamps are ms (e.g. > 1e11), convert diff to seconds
    is_ms = min_ts > 10_000_000_000
    divisor = 1000.0 if is_ms else 1.0

    session_duration_s = max(1.0, (max_ts - min_ts) / divisor)
    num_windows = max(1, math.ceil(session_duration_s / window_seconds))

    window_counts = [0] * num_windows
    window_char_growth = [0] * num_windows

    for e in events:
        ts = e.get("timestamp", 0)
        offset_s = max(0.0, (ts - min_ts) / divisor)
        w_idx = min(num_windows - 1, int(offset_s // window_seconds))

        # Count events: key, cursor, selection, scroll, content_change, paste
        window_counts[w_idx] += 1
        ins = e.get("inserted_length", 0) or 0
        rem = e.get("removed_length", 0) or 0
        window_char_growth[w_idx] += (ins - rem)

    result = []
    for idx in range(num_windows):
        start_s = idx * window_seconds
        result.append({
            "window_index": idx,
            "start_seconds": start_s,
            "end_seconds": start_s + window_seconds,
            "event_count": window_counts[idx],
            "net_growth_chars": window_char_growth[idx],
        })

    return result


def compute_growth_without_activity(
    activity_density: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Identify windows where document grows by >= 80 chars while activity_density is near zero (<= 2)."""
    flagged_windows = []

    for w in activity_density:
        if (
            w.get("net_growth_chars", 0) >= TELEMETRY_GROWTH_WITHOUT_ACTIVITY_CHARS
            and w.get("event_count", 0) <= TELEMETRY_ACTIVITY_DENSITY_LOW_THRESHOLD
        ):
            flagged_windows.append(w)

    return flagged_windows


def compute_revision_ratio(
    events: List[Dict[str, Any]],
    final_length: int,
) -> float:
    """Calculate (removed + replaced characters) / max(1, final_length)."""
    removed_chars = 0

    for e in events:
        rem = e.get("removed_length", 0) or 0
        if rem > 0:
            removed_chars += rem

    ratio = round(removed_chars / max(1, final_length), 3)
    return ratio


def compute_cadence(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate coefficient of variation (std_dev / mean) of inter-key intervals inside typing bursts.

    Burst is defined as sequential typing key_down events with inter-key gap < 2000 ms.
    """
    key_events = [
        e for e in events
        if e.get("type") == "key_down" or (e.get("key_category") and e.get("key_category") != "shortcut")
    ]
    key_events.sort(key=lambda x: x.get("timestamp", 0))

    if len(key_events) < 5:
        return {"coefficient_of_variation": 0.0, "mean_iki_ms": 0.0, "std_iki_ms": 0.0, "burst_count": 0}

    is_ms = key_events[0].get("timestamp", 0) > 10_000_000_000
    multiplier = 1.0 if is_ms else 1000.0

    ikis: List[float] = []
    burst_count = 0
    in_burst = False

    for i in range(1, len(key_events)):
        delta_ms = (key_events[i].get("timestamp", 0) - key_events[i - 1].get("timestamp", 0)) * multiplier
        if 20.0 <= delta_ms <= 2000.0:
            ikis.append(delta_ms)
            if not in_burst:
                burst_count += 1
                in_burst = True
        else:
            in_burst = False

    if len(ikis) < 5:
        return {"coefficient_of_variation": 0.0, "mean_iki_ms": 0.0, "std_iki_ms": 0.0, "burst_count": burst_count}

    mean_iki = sum(ikis) / len(ikis)
    variance = sum((x - mean_iki) ** 2 for x in ikis) / len(ikis)
    std_iki = math.sqrt(variance)
    cv = round(std_iki / max(1.0, mean_iki), 3)

    return {
        "coefficient_of_variation": cv,
        "mean_iki_ms": round(mean_iki, 1),
        "std_iki_ms": round(std_iki, 1),
        "burst_count": burst_count,
        "sample_size": len(ikis),
    }


def compute_read_then_type(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect occurrences of an idle gap of >= 60s followed by >= 150 characters typed within 20s."""
    events_sorted = sorted(events, key=lambda x: x.get("timestamp", 0))
    if len(events_sorted) < 2:
        return []

    is_ms = events_sorted[0].get("timestamp", 0) > 10_000_000_000
    divisor = 1000.0 if is_ms else 1.0

    detected_episodes = []

    for i in range(1, len(events_sorted)):
        prev_ts = events_sorted[i - 1].get("timestamp", 0)
        curr_ts = events_sorted[i].get("timestamp", 0)
        gap_s = (curr_ts - prev_ts) / divisor

        # Idle pause of at least 60 seconds
        if gap_s >= TELEMETRY_READ_THEN_TYPE_PAUSE_SECONDS:
            # Check characters typed in the subsequent 20 seconds
            burst_chars = 0
            burst_end_ts = curr_ts + (TELEMETRY_READ_THEN_TYPE_BURST_SECONDS * divisor)

            for j in range(i, len(events_sorted)):
                ev = events_sorted[j]
                if ev.get("timestamp", 0) > burst_end_ts:
                    break
                src = str(ev.get("source", "typing")).lower()
                if src == "typing":
                    burst_chars += (ev.get("inserted_length", 0) or 0)

            if burst_chars >= TELEMETRY_READ_THEN_TYPE_CHARS:
                detected_episodes.append({
                    "pause_seconds": round(gap_s, 1),
                    "chars_typed_in_20s": burst_chars,
                    "timestamp": curr_ts,
                })

    return detected_episodes


def compute_focus_metrics(
    events: List[Dict[str, Any]],
    start_ts: float,
) -> Dict[str, Any]:
    """Compute blur count, total blurred seconds, hidden tab seconds, time to first input, active time vs wall time."""
    if not events:
        return {
            "blur_count": 0,
            "total_blurred_seconds": 0.0,
            "hidden_tab_seconds": 0.0,
            "seconds_to_first_input": 0.0,
            "active_time_seconds": 0.0,
            "wall_time_seconds": 0.0,
        }

    is_ms = start_ts > 10_000_000_000 or (events and events[0].get("timestamp", 0) > 10_000_000_000)
    divisor = 1000.0 if is_ms else 1.0

    timestamps = [e.get("timestamp", 0) for e in events]
    min_ts = min(timestamps)
    max_ts = max(timestamps)
    session_start = min(start_ts, min_ts) if start_ts > 0 else min_ts

    wall_time_seconds = max(1.0, (max_ts - session_start) / divisor)

    blur_count = 0
    total_blurred_s = 0.0
    hidden_tab_s = 0.0
    first_input_s = None

    last_blur_ts = None
    last_hidden_ts = None

    sorted_events = sorted(events, key=lambda x: x.get("timestamp", 0))

    for ev in sorted_events:
        ev_type = ev.get("type")
        ts = ev.get("timestamp", 0)

        # Detect first input
        if first_input_s is None:
            if ev_type in {"key_down", "content_change", "paste"}:
                first_input_s = max(0.0, (ts - session_start) / divisor)

        # Blur tracking
        if ev_type == "blur":
            blur_count += 1
            last_blur_ts = ts
        elif ev_type == "focus" and last_blur_ts is not None:
            total_blurred_s += max(0.0, (ts - last_blur_ts) / divisor)
            last_blur_ts = None

        # Visibility tracking
        if ev_type == "visibility_change" and ev.get("state") == "hidden":
            last_hidden_ts = ts
        elif ev_type == "visibility_change" and ev.get("state") == "visible" and last_hidden_ts is not None:
            hidden_tab_s += max(0.0, (ts - last_hidden_ts) / divisor)
            last_hidden_ts = None

    # Active time: wall time minus blurred duration
    active_time_seconds = max(0.0, wall_time_seconds - total_blurred_s)

    return {
        "blur_count": blur_count,
        "total_blurred_seconds": round(total_blurred_s, 1),
        "hidden_tab_seconds": round(hidden_tab_s, 1),
        "seconds_to_first_input": round(first_input_s or 0.0, 1),
        "active_time_seconds": round(active_time_seconds, 1),
        "wall_time_seconds": round(wall_time_seconds, 1),
    }


def extract_all_telemetry_features(
    events: List[Dict[str, Any]],
    client_start_ts: float,
    final_length: int,
) -> Dict[str, Any]:
    """Pure pipeline orchestrator that computes all 8 features from the event stream."""
    typed_data = compute_typed_ratio(events)
    large_ins = compute_large_inserts(events)
    density = compute_activity_density(events)
    growth_no_act = compute_growth_without_activity(density)
    revision = compute_revision_ratio(events, final_length)
    cad = compute_cadence(events)
    read_type = compute_read_then_type(events)
    focus = compute_focus_metrics(events, client_start_ts)

    return {
        "typed_ratio": typed_data["typed_ratio"],
        "typed_breakdown": typed_data,
        "large_inserts": large_ins,
        "large_insert_count": len(large_ins),
        "activity_density_series": density,
        "growth_without_activity_windows": growth_no_act,
        "growth_without_activity_count": len(growth_no_act),
        "revision_ratio": revision,
        "cadence": cad,
        "read_then_type_episodes": read_type,
        "read_then_type_count": len(read_type),
        "focus": focus,
    }
