"""
Spoken-delivery metrics computed from a transcript plus timing. Audio is never stored; only these
numbers are kept with the answer.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

FILLERS = ["um", "uh", "erm", "hmm", "you know", "i mean", "basically", "actually", "literally", "sort of", "kind of"]
HEDGES = ["i think", "i guess", "maybe", "probably", "i'm not sure", "im not sure", "i believe", "perhaps", "somewhat", "i suppose"]
LONG_PAUSE_S = 1.5


def _count(text: str, phrases: List[str]) -> Dict[str, int]:
    cleaned = re.sub(r"[^a-z0-9' ]+", " ", (text or "").lower())
    low = f" {cleaned} "
    out = {}
    for p in phrases:
        if p == "like":
            continue
        n = len(re.findall(rf"(?<=\s){re.escape(p)}(?=\s)", low))
        if n:
            out[p] = n
    # "like" as a filler: "like" between commas or followed by another filler-ish pause marker
    if "like" in phrases:
        like = len(re.findall(r"(?:^|[,.]\s*)like\b|\blike,", (text or "").lower()))
        if like:
            out["like"] = like
    return out


def delivery_metrics(text: str, duration_s: Optional[float] = None,
                     words: Optional[List[Tuple[str, float, float]]] = None) -> Optional[Dict[str, Any]]:
    """words: optional [(word, start_s, end_s)] from STT. Returns None when there's nothing to measure."""
    tokens = re.findall(r"[A-Za-z0-9']+", text or "")
    if not tokens:
        return None
    if words:
        duration_s = max(duration_s or 0.0, words[-1][2] - min(w[1] for w in words))
    fillers = _count(text, FILLERS + ["like"])
    hedges = _count(text, HEDGES)
    filler_total = sum(fillers.values())
    metrics: Dict[str, Any] = {
        "words": len(tokens),
        "filler_count": filler_total,
        "fillers": fillers,
        "hedge_count": sum(hedges.values()),
        "hedges": hedges,
    }
    if duration_s and duration_s > 0.5:
        minutes = duration_s / 60.0
        metrics["duration_s"] = round(duration_s, 1)
        metrics["words_per_minute"] = round(len(tokens) / minutes)
        metrics["fillers_per_minute"] = round(filler_total / minutes, 1)
    if words and len(words) > 1:
        gaps = [(words[i + 1][1] - words[i][2]) for i in range(len(words) - 1)]
        long_gaps = [g for g in gaps if g >= LONG_PAUSE_S]
        metrics["long_pauses"] = len(long_gaps)
        metrics["longest_pause_s"] = round(max(gaps), 1) if gaps else 0.0
        filler_words = {w for f in FILLERS + ["like"] for w in f.split()}
        first_content = next((w for w in words if w[0].strip(" ,.?!").lower() not in filler_words), None)
        if first_content:
            metrics["time_to_first_point_s"] = round(first_content[1] - words[0][1], 1)
    return metrics


def summarize_delivery(per_answer: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    rows = [m for m in per_answer if m]
    if not rows:
        return None
    timed = [m for m in rows if m.get("words_per_minute")]
    total_fillers: Dict[str, int] = {}
    for m in rows:
        for k, v in (m.get("fillers") or {}).items():
            total_fillers[k] = total_fillers.get(k, 0) + v
    hedges = sum(m.get("hedge_count", 0) for m in rows)
    out: Dict[str, Any] = {
        "answers_measured": len(rows),
        "avg_words_per_minute": round(sum(m["words_per_minute"] for m in timed) / len(timed)) if timed else None,
        "fillers_per_minute": round(sum(m.get("fillers_per_minute", 0) for m in timed) / len(timed), 1) if timed else None,
        "top_fillers": sorted(total_fillers.items(), key=lambda kv: -kv[1])[:3],
        "hedges": hedges,
        "longest_pause_s": max((m.get("longest_pause_s", 0) for m in rows), default=0),
    }
    notes = []
    wpm = out["avg_words_per_minute"]
    if wpm and wpm > 175:
        notes.append(f"Fast delivery ({wpm} wpm). Slow down on the key point so it lands.")
    elif wpm and wpm < 100:
        notes.append(f"Slow delivery ({wpm} wpm). Lead with the answer, then explain.")
    if out["fillers_per_minute"] and out["fillers_per_minute"] > 4:
        notes.append(f"{out['fillers_per_minute']} fillers a minute; '{out['top_fillers'][0][0]}' most often. Pause silently instead.")
    if hedges >= max(3, len(rows)):
        notes.append(f"{hedges} hedges ('I think', 'I guess'). Commit to an answer, then state your assumptions.")
    out["notes"] = notes
    return out


def merge_delivery(parts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Combine metrics from several recordings that make up one answer (client-supplied, sanitized)."""
    rows = [p for p in (parts or [])[:10] if isinstance(p, dict)]
    if not rows:
        return None

    def num(v, lo=0.0, hi=1e6):
        try:
            return max(lo, min(hi, float(v)))
        except (TypeError, ValueError):
            return 0.0

    def counts(key):
        out: Dict[str, int] = {}
        for r in rows:
            for k, v in (r.get(key) or {}).items():
                if isinstance(k, str) and len(k) <= 20:
                    out[k] = out.get(k, 0) + int(num(v, 0, 500))
        return out

    words = int(sum(num(r.get("words"), 0, 5000) for r in rows))
    duration = sum(num(r.get("duration_s"), 0, 900) for r in rows)
    fillers, hedges = counts("fillers"), counts("hedges")
    merged: Dict[str, Any] = {"words": words, "fillers": fillers, "filler_count": sum(fillers.values()),
                              "hedges": hedges, "hedge_count": sum(hedges.values())}
    if duration > 0.5:
        merged["duration_s"] = round(duration, 1)
        merged["words_per_minute"] = round(words / (duration / 60))
        merged["fillers_per_minute"] = round(merged["filler_count"] / (duration / 60), 1)
    pauses = [r for r in rows if "longest_pause_s" in r]
    if pauses:
        merged["long_pauses"] = int(sum(num(r.get("long_pauses"), 0, 500) for r in pauses))
        merged["longest_pause_s"] = round(max(num(r.get("longest_pause_s"), 0, 900) for r in pauses), 1)
    if "time_to_first_point_s" in rows[0]:
        merged["time_to_first_point_s"] = round(num(rows[0]["time_to_first_point_s"], 0, 900), 1)
    return merged
