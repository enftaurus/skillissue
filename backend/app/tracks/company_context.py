"""
Company context for mock interviews: every company in the track registry (not just a hardcoded handful) gets a
calibrated interviewer, drawn from the same description, community tips and tagged problem list the tracks page shows.
"""
from collections import Counter
from typing import Any, Dict, List, Optional

from backend.app.tracks.company_registry import COMPANIES_50

TITLE_SEPARATOR = " · "
TITLE_SUFFIX = " mock interview"

_BY_SLUG = {c["slug"]: c for c in COMPANIES_50}
_BY_NAME = {c["name"].lower(): c for c in COMPANIES_50}

# Registry topic tags -> words the curated DSA picker understands (backend/app/coding/problems.py).
_TOPIC_WORDS = {
    "dynamic programming": "dp", "graph": "graph", "bfs": "bfs", "dfs": "dfs", "topological sort": "topological",
    "tree": "tree", "binary tree": "tree", "binary search": "binary search", "linked list": "linked list",
    "string": "string", "sliding window": "sliding", "stack": "stack", "queue": "queue", "design": "design",
    "array": "array", "hash table": "hash", "two pointers": "two pointer", "greedy": "greedy", "heap": "heap",
    "interval": "interval", "sorting": "sort", "matrix": "array", "trie": "string",
}


def get_company(slug: Optional[str]) -> Optional[Dict[str, Any]]:
    return _BY_SLUG.get((slug or "").lower().strip())


def company_title(company: Dict[str, Any], category: str) -> str:
    return f"{company['name']}{TITLE_SEPARATOR}{category.capitalize()}{TITLE_SUFFIX}"


def company_from_title(title: Optional[str]) -> Optional[Dict[str, Any]]:
    """Only titles this module wrote ("Uber · Dsa mock interview") count, so a skill named 'Oracle' never does."""
    t = title or ""
    if TITLE_SEPARATOR not in t or not t.endswith(TITLE_SUFFIX):
        return None
    return _BY_NAME.get(t.split(TITLE_SEPARATOR, 1)[0].strip().lower())


def company_by_name(name: Optional[str]) -> Optional[Dict[str, Any]]:
    n = (name or "").lower().strip()
    if not n:
        return None
    if n in _BY_NAME:
        return _BY_NAME[n]
    # "Uber Technologies Inc." -> Uber; longest registry name first so "Morgan Stanley" beats nothing shorter.
    for key in sorted(_BY_NAME, key=len, reverse=True):
        if n.startswith(key + " ") or n == key:
            return _BY_NAME[key]
    return None


def company_topics(company: Dict[str, Any], n: int = 4) -> List[str]:
    """The company's most frequent problem topics, weighted by how often each problem shows up."""
    weights: Counter = Counter()
    for p in company.get("problems") or []:
        for t in p.get("topics") or []:
            weights[t] += float(p.get("frequency") or 50)
    return [t for t, _ in weights.most_common(n)]


def picker_skills(company: Dict[str, Any]) -> List[str]:
    out = []
    for t in company_topics(company, 6):
        w = _TOPIC_WORDS.get(t.lower())
        if w and w not in out:
            out.append(w)
    return out


def calibration_block(company: Dict[str, Any], category: str) -> str:
    """Prompt block from registry data. Factual guidance only; the interviewer still follows every house rule."""
    topics = ", ".join(company_topics(company, 5))
    tips = "\n".join(f"- {t}" for t in (company.get("community_tips") or [])[:4])
    lines = [
        f"\n\nCOMPANY CALIBRATION: {company['name'].upper()} ({category.upper()} ROUND, {company.get('role_title', 'SWE')})",
        f"What this company evaluates: {company.get('description', '').strip()}",
    ]
    if category in ("dsa", "technical") and topics:
        lines.append(f"Their most frequent problem areas: {topics}. Prefer follow-ups in these areas.")
    if tips and category in ("dsa", "technical"):
        lines.append("Candidate-reported interview patterns (use as calibration, don't quote them):\n" + tips)
    lines.append(f"Behave like a {company['name']} interviewer would, but never claim to work there or use internal names.")
    return "\n".join(lines)
