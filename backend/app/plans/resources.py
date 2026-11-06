"""
Study resources that actually open.

Model-written URLs are often invented (plausible paths that 404). A link reaches a plan only if
  1. it is https on an allowlisted, reputable domain (also keeps the server from fetching arbitrary/internal hosts), and
  2. it answers with a non-error status right now (checked concurrently, cached for a day).
Tasks left with no verified link get links from a curated library (verified by tests/scripts).
"""
import asyncio
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from backend.app.core.logging import logger

ALLOWED_DOMAINS = {
    "docs.python.org", "developer.mozilla.org", "www.postgresql.org", "redis.io", "kubernetes.io", "docs.docker.com",
    "react.dev", "fastapi.tiangolo.com", "leetcode.com", "neetcode.io", "www.geeksforgeeks.org", "cp-algorithms.com",
    "en.wikipedia.org", "docs.aws.amazon.com", "aws.amazon.com", "martinfowler.com", "github.com", "www.youtube.com",
    "roadmap.sh", "www.freecodecamp.org", "www.w3schools.com", "docs.oracle.com", "en.cppreference.com", "go.dev",
    "doc.rust-lang.org", "nodejs.org", "www.mongodb.com", "kafka.apache.org", "nginx.org", "git-scm.com",
    "www.typescriptlang.org", "docs.djangoproject.com", "flask.palletsprojects.com", "dev.mysql.com", "sqlite.org",
    "www.sqlite.org", "jwt.io", "www.jwt.io", "owasp.org", "cheatsheetseries.owasp.org", "www.khanacademy.org", "ocw.mit.edu",
    "visualgo.net", "www.bigocheatsheet.com", "pages.cs.wisc.edu", "learn.microsoft.com", "cloud.google.com",
    "docs.github.com", "www.atlassian.com", "pytorch.org", "docs.pytorch.org", "scikit-learn.org", "numpy.org", "pandas.pydata.org",
}

# keyword regex -> curated links (every URL here is checked by scripts/verify_plan_resources.py)
CURATED: List[Tuple[str, List[Dict[str, str]]]] = [
    (r"dynamic programming|\bdp\b|memoi", [
        {"title": "Dynamic Programming (cp-algorithms)", "url": "https://cp-algorithms.com/dynamic_programming/intro-to-dp.html", "type": "article"},
        {"title": "NeetCode roadmap", "url": "https://neetcode.io/roadmap", "type": "practice"}]),
    (r"graph|bfs|dfs|topolog|dijkstra|shortest path", [
        {"title": "Breadth-first search (cp-algorithms)", "url": "https://cp-algorithms.com/graph/breadth-first-search.html", "type": "article"},
        {"title": "Depth-first search (cp-algorithms)", "url": "https://cp-algorithms.com/graph/depth-first-search.html", "type": "article"},
        {"title": "Graph visualisations (VisuAlgo)", "url": "https://visualgo.net/en/dfsbfs", "type": "interactive"}]),
    (r"tree|bst|heap|trie", [
        {"title": "Binary search tree (VisuAlgo)", "url": "https://visualgo.net/en/bst", "type": "interactive"},
        {"title": "Heap (VisuAlgo)", "url": "https://visualgo.net/en/heap", "type": "interactive"}]),
    (r"array|string|hash|two pointer|sliding window|sort|binary search|dsa|algorithm|data structure|leetcode", [
        {"title": "Big-O cheat sheet", "url": "https://www.bigocheatsheet.com/", "type": "reference"},
        {"title": "NeetCode roadmap", "url": "https://neetcode.io/roadmap", "type": "practice"},
        {"title": "Sorting (VisuAlgo)", "url": "https://visualgo.net/en/sorting", "type": "interactive"}]),
    (r"system design|scalab|distributed|load balanc|cach|sharding|microservice|rate limit|consistent hash", [
        {"title": "System design primer", "url": "https://github.com/donnemartin/system-design-primer", "type": "guide"},
        {"title": "Backend roadmap", "url": "https://roadmap.sh/backend", "type": "roadmap"},
        {"title": "Microservices (Martin Fowler)", "url": "https://martinfowler.com/articles/microservices.html", "type": "article"}]),
    (r"postgres|sql|database|dbms|index|transaction|normaliz", [
        {"title": "PostgreSQL tutorial (official)", "url": "https://www.postgresql.org/docs/current/tutorial.html", "type": "documentation"},
        {"title": "PostgreSQL indexes (official)", "url": "https://www.postgresql.org/docs/current/indexes.html", "type": "documentation"},
        {"title": "SQL tutorial (W3Schools)", "url": "https://www.w3schools.com/sql/", "type": "tutorial"},
        {"title": "PostgreSQL transactions (official)", "url": "https://www.postgresql.org/docs/current/tutorial-transactions.html", "type": "documentation"},
        {"title": "Database normalization (Wikipedia)", "url": "https://en.wikipedia.org/wiki/Database_normalization", "type": "article"},
        {"title": "SQLite query planner", "url": "https://www.sqlite.org/queryplanner.html", "type": "article"}]),
    (r"redis", [{"title": "Redis docs", "url": "https://redis.io/docs/latest/", "type": "documentation"}]),
    (r"python|fastapi|django|flask", [
        {"title": "The Python tutorial (official)", "url": "https://docs.python.org/3/tutorial/", "type": "documentation"},
        {"title": "FastAPI tutorial", "url": "https://fastapi.tiangolo.com/tutorial/", "type": "documentation"}]),
    (r"javascript|typescript|react|frontend|web|html|css|node", [
        {"title": "JavaScript guide (MDN)", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "type": "documentation"},
        {"title": "React docs", "url": "https://react.dev/learn", "type": "documentation"},
        {"title": "TypeScript handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "type": "documentation"}]),
    (r"docker|kubernetes|container|devops|deploy", [
        {"title": "Docker get started", "url": "https://docs.docker.com/get-started/", "type": "documentation"},
        {"title": "Kubernetes basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "type": "tutorial"}]),
    (r"operating system|\bos\b|process|thread|concurren|deadlock|memory|schedul", [
        {"title": "Operating Systems: Three Easy Pieces", "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/", "type": "book"},
        {"title": "MIT 6.004 / OCW", "url": "https://ocw.mit.edu/", "type": "course"}]),
    (r"network|http|tcp|dns|rest|api", [
        {"title": "HTTP overview (MDN)", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview", "type": "documentation"},
        {"title": "REST API design (Microsoft)", "url": "https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design", "type": "guide"}]),
    (r"security|auth|jwt|oauth|owasp", [
        {"title": "OWASP cheat sheets", "url": "https://cheatsheetseries.owasp.org/", "type": "reference"},
        {"title": "Introduction to JWT", "url": "https://www.jwt.io/introduction", "type": "article"}]),
    (r"java\b|spring|jvm", [{"title": "Java tutorials (Oracle)", "url": "https://docs.oracle.com/javase/tutorial/", "type": "documentation"}]),
    (r"c\+\+|cpp|stl", [{"title": "C++ reference", "url": "https://en.cppreference.com/w/", "type": "reference"}]),
    (r"git\b|version control", [{"title": "Pro Git book", "url": "https://git-scm.com/book/en/v2", "type": "book"}]),
    (r"machine learning|\bml\b|deep learning|pytorch|neural", [
        {"title": "scikit-learn user guide", "url": "https://scikit-learn.org/stable/user_guide.html", "type": "documentation"},
        {"title": "PyTorch tutorials", "url": "https://docs.pytorch.org/tutorials/", "type": "tutorial"}]),
    (r"behavio|leadership|star|communication|soft skill|hr", [
        {"title": "Interviewing guide (freeCodeCamp)", "url": "https://www.freecodecamp.org/news/tag/interviewing/", "type": "article"}]),
]
GENERIC = [{"title": "Developer roadmaps", "url": "https://roadmap.sh/", "type": "roadmap"},
           {"title": "NeetCode roadmap", "url": "https://neetcode.io/roadmap", "type": "practice"}]

_CACHE: Dict[str, Tuple[bool, float]] = {}
_TTL = 24 * 3600
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SkillIssueLinkCheck/1.0)", "Accept": "text/html,*/*"}


def allowed(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    return u.scheme == "https" and (u.hostname or "").lower() in ALLOWED_DOMAINS and not u.username and u.port in (None, 443)


async def _check(client: httpx.AsyncClient, url: str) -> bool:
    hit = _CACHE.get(url)
    if hit and time.time() - hit[1] < _TTL:
        return hit[0]
    ok = False
    try:
        r = await client.get(url)
        # Must land on an allowlisted host too (no open-redirect hops to unknown sites).
        ok = r.status_code < 400 and allowed(str(r.url))
    except Exception:
        ok = False
    _CACHE[url] = (ok, time.time())
    return ok


def _curated_urls() -> set:
    return {l["url"] for _, ls in CURATED for l in ls} | {l["url"] for l in GENERIC}


async def verify(urls: Iterable[str]) -> Dict[str, bool]:
    todo = list(dict.fromkeys(u for u in urls if allowed(u)))
    if not todo:
        return {}
    if os.environ.get("PLANLY_OFFLINE_LINKS") == "1":
        # Tests/offline: no network. Curated links are verified separately; model links are never trusted unchecked.
        cur = _curated_urls()
        return {u: u in cur for u in todo}
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, max_redirects=4, headers=_HEADERS) as client:
        results = await asyncio.gather(*(_check(client, u) for u in todo))
    return dict(zip(todo, results))


def curated_for(*texts: Optional[str], limit: int = 2) -> List[Dict[str, str]]:
    blob = " ".join(t for t in texts if t).lower()
    out: List[Dict[str, str]] = []
    for pattern, links in CURATED:
        if re.search(pattern, blob):
            out.extend(l for l in links if l not in out)
        if len(out) >= limit:
            break
    return (out or GENERIC)[:limit]


def _clean(raw: Any) -> List[Dict[str, str]]:
    out = []
    for r in raw if isinstance(raw, list) else []:
        if isinstance(r, dict) and isinstance(r.get("url"), str):
            out.append({"title": str(r.get("title") or "Resource")[:200], "url": r["url"].strip()[:500],
                        "type": str(r.get("type") or "article")[:30]})
    return out


async def resolve_for_tasks(tasks: List[Dict[str, Any]], topic: str) -> List[List[Dict[str, str]]]:
    """Per task: model links that are allowlisted AND reachable now, else verified curated links. Never invented."""
    proposed = [_clean(t.get("external_resources")) for t in tasks]
    # Wider curated pool per task, rotated by day so consecutive days don't repeat the same two links.
    curated = []
    for i, t in enumerate(tasks):
        pool = curated_for(t.get("title"), t.get("subtopic"), t.get("description"), topic, limit=6)
        k = (2 * i) % len(pool) if pool else 0
        curated.append((pool[k:] + pool[:k])[:2])
    status = await verify([r["url"] for lst in proposed + curated for r in lst])
    dropped = sum(1 for lst in proposed for r in lst if not status.get(r["url"]))
    if dropped:
        logger.info(f"Planly: dropped {dropped} unreachable or non-allowlisted resource links")
    out = []
    for p, c in zip(proposed, curated):
        good = [r for r in p if status.get(r["url"])][:3]
        if not good:
            good = [r for r in c if status.get(r["url"])]
        out.append(good)
    return out
