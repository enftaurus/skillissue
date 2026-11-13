"""
Coerce the evaluation model's JSON into the shapes the rest of the app (and the response schemas) rely on.

The model is untrusted: scores arrive as "4", "four", 4.6, NaN, 9 or true; lists arrive as strings or lists of
dicts; targeted resources arrive as objects. Any of those used to 500 the generate call or, worse, every later
GET of the evaluation (response validation). NaN scores in particular slipped through min/max clamping as a 5.
"""
import math
import re
from typing import Any, Dict, List, Optional

MAX_LIST_ITEMS = 20
MAX_ITEM_CHARS = 2000


def coerce_score(value: Any) -> Optional[int]:
    """A 1-5 integer rubric score, or None when the value isn't a usable number."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:/\s*5)?\s*", value)
        if not m:
            return None
        value = m.group(1)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return int(max(1.0, min(5.0, v)) + 0.5)


def clean_text(value: Any, limit: int = MAX_ITEM_CHARS) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = next((value[k] for k in ("text", "title", "name", "quote", "topic", "url") if value.get(k)), "")
        if isinstance(value, (dict, list)):
            return ""
    elif isinstance(value, list):
        value = ", ".join(s for s in (clean_text(v, limit) for v in value) if s)
    return str(value).replace("\x00", "").strip()[:limit]


def str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out = [clean_text(v) for v in value[:MAX_LIST_ITEMS]]
    return [s for s in out if s]


def excerpt_list(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    out = []
    for e in value[:MAX_LIST_ITEMS]:
        if isinstance(e, dict):
            quote, critique = clean_text(e.get("quote")), clean_text(e.get("critique"))
        elif isinstance(e, str):
            quote, critique = clean_text(e), ""
        else:
            continue
        if quote:
            out.append({"quote": quote, "critique": critique})
    return out


def dimension_scores(value: Any) -> Dict[str, Dict[str, Any]]:
    """dim_id -> {"score": int 1-5 (omitted if unusable), "explanation": str, "evidence_quote": str, ...}."""
    if not isinstance(value, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for dim, data in value.items():
        dim = clean_text(dim, 80)
        if not dim:
            continue
        if not isinstance(data, dict):
            data = {"score": data}
        d = {k: v for k, v in data.items() if k not in ("score", "explanation", "evidence_quote")}
        score = coerce_score(data.get("score"))
        if score is not None:
            d["score"] = score
        d["explanation"] = clean_text(data.get("explanation"))
        d["evidence_quote"] = clean_text(data.get("evidence_quote"))
        out[dim] = d
    return out


def question_index(value: Any, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)) and math.isfinite(value):
        return int(value)
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else fallback


def sanitize_evaluation(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the model output with every field the service reads coerced to a safe shape."""
    p = dict(parsed)
    p["dimension_scores"] = dimension_scores(parsed.get("dimension_scores"))
    for key in ("strengths", "weaknesses", "missing_concepts", "suggested_corrections", "uncertainty_notes"):
        p[key] = str_list(parsed.get(key))
    p["evidence_excerpts"] = excerpt_list(parsed.get("evidence_excerpts"))
    qf = parsed.get("question_feedback")
    p["question_feedback"] = [q for q in qf[:50] if isinstance(q, dict)] if isinstance(qf, list) else []
    wa = parsed.get("weakness_analysis")
    p["weakness_analysis"] = [w for w in wa[:MAX_LIST_ITEMS] if isinstance(w, dict)] if isinstance(wa, list) else []
    return p
