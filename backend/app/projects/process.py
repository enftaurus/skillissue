"""
Process signals for AI-assisted projects: did the candidate verify the assistant's suggestions?

All inputs are server-side records (copilot turns, test runs, submissions), never client claims.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models import ProjectCopilotTurn, ProjectEvent, ProjectSubmission


async def log_event(db: AsyncSession, user_id: str, project_id: str, kind: str, payload: Dict[str, Any]) -> None:
    db.add(ProjectEvent(user_id=user_id, project_id=project_id, kind=kind, payload=payload))
    await db.commit()


async def _since_last_submission(db: AsyncSession, user_id: str, project_id: str) -> Optional[datetime]:
    return (await db.execute(
        select(ProjectSubmission.created_at)
        .where(ProjectSubmission.user_id == user_id, ProjectSubmission.project_id == project_id)
        .order_by(ProjectSubmission.created_at.desc()).limit(1)
    )).scalar_one_or_none()


async def session_timeline(db: AsyncSession, user_id: str, project_id: str, since: Optional[datetime] = None,
                           include_since: bool = False) -> List[Dict[str, Any]]:
    """Chronological prompt / reply / test-run / submit events for the current attempt."""
    if since is None:
        since = await _since_last_submission(db, user_id, project_id)
    tq = select(ProjectCopilotTurn).where(ProjectCopilotTurn.user_id == user_id, ProjectCopilotTurn.project_id == project_id)
    eq = select(ProjectEvent).where(ProjectEvent.user_id == user_id, ProjectEvent.project_id == project_id)
    if since is not None:
        tq = tq.where(ProjectCopilotTurn.created_at > since)
        eq = eq.where(ProjectEvent.created_at >= since if include_since else ProjectEvent.created_at > since)
    events: List[Dict[str, Any]] = []
    for t in (await db.execute(tq)).scalars().all():
        events.append({"at": t.created_at, "kind": "prompt", "text": t.prompt[:300],
                       "reply_has_code": "```" in (t.response or ""), "tests": f"{t.tests_passed}/{t.tests_total}" if t.tests_total else None})
    for e in (await db.execute(eq)).scalars().all():
        events.append({"at": e.created_at, "kind": e.kind, **{k: v for k, v in (e.payload or {}).items() if k in ("passed", "total", "status")}})
    events.sort(key=lambda e: e["at"])
    for e in events:
        e["at"] = e["at"].isoformat()
    return events


def verification_metrics(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    prompts = [i for i, e in enumerate(timeline) if e["kind"] == "prompt"]
    verified = 0
    for n, idx in enumerate(prompts):
        nxt = prompts[n + 1] if n + 1 < len(prompts) else len(timeline)
        if any(e["kind"] == "test_run" for e in timeline[idx + 1:nxt]):
            verified += 1
    runs = [e for e in timeline if e["kind"] == "test_run"]
    passes = [e for e in runs if e.get("status") == "passed"]
    submitted_green = any(e["kind"] == "submit" and e.get("status") == "passed" for e in timeline)
    return {
        "prompts": len(prompts),
        "test_runs": len(runs),
        "verified_replies": verified,
        "verification_rate": round(verified / len(prompts), 2) if prompts else None,
        "submitted_without_running_tests": any(e["kind"] == "submit" for e in timeline) and not runs,
        "first_green_after_runs": (runs.index(passes[0]) + 1) if passes else None,
        "submitted_green": submitted_green,
    }


def process_flags(m: Dict[str, Any]) -> List[str]:
    flags = []
    if m["prompts"] >= 2 and (m["verification_rate"] or 0) < 0.5:
        flags.append(f"Ran tests after only {m['verified_replies']} of {m['prompts']} assistant replies; verify suggestions before moving on.")
    if m["submitted_without_running_tests"]:
        flags.append("Submitted without running the test suite even once.")
    return flags
