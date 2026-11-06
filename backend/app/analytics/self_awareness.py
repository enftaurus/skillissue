"""Self-awareness index: how far a candidate's self-ratings are from the evidence-based evaluation."""
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models import Evaluation, Interview, SelfEvaluation
from backend.app.interviews.rubrics import RUBRICS_CATALOG


def _dimension_names() -> Dict[str, str]:
    return {d.id: d.name for dims in RUBRICS_CATALOG.values() for d in dims}


async def self_awareness_report(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    rows = (await db.execute(
        select(SelfEvaluation, Evaluation, Interview)
        .join(Evaluation, Evaluation.interview_id == SelfEvaluation.interview_id)
        .join(Interview, Interview.id == SelfEvaluation.interview_id)
        .where(SelfEvaluation.user_id == user_id, Evaluation.user_id == user_id, Interview.user_id == user_id,
               Evaluation.overall_score.isnot(None))
        .order_by(Evaluation.created_at.asc())
    )).all()
    names = _dimension_names()
    per_dim: Dict[str, List[Dict[str, Any]]] = {}
    sessions: List[Dict[str, Any]] = []
    for self_eval, ev, iv in rows:
        gaps = []
        for dim, self_score in (self_eval.dimension_scores or {}).items():
            ai = (ev.rubric_dimension_scores or {}).get(dim, {})
            ai_score = ai.get("score") if isinstance(ai, dict) else None
            if not isinstance(self_score, (int, float)) or not isinstance(ai_score, (int, float)):
                continue
            gap = float(self_score) - float(ai_score)
            gaps.append(abs(gap))
            per_dim.setdefault(dim, []).append({"interview_id": iv.id, "date": ev.created_at.isoformat(),
                                                "self": self_score, "ai": ai_score, "gap": gap})
        if gaps:
            sessions.append({"interview_id": iv.id, "title": iv.title, "date": ev.created_at.isoformat(),
                             "mean_abs_gap": round(sum(gaps) / len(gaps), 2)})

    dimensions = []
    for dim, series in per_dim.items():
        latest, first = series[-1]["gap"], series[0]["gap"]
        avg = sum(s["gap"] for s in series) / len(series)
        dimensions.append({
            "dimension_id": dim, "name": names.get(dim, dim.replace("_", " ").title()),
            "latest_gap": latest, "first_gap": first, "average_gap": round(avg, 2),
            "bias": "overrate" if avg > 0.5 else "underrate" if avg < -0.5 else "calibrated",
            "trend": round(abs(first) - abs(latest), 2) if len(series) > 1 else None,
            "samples": len(series), "series": series,
        })
    dimensions.sort(key=lambda d: -abs(d["latest_gap"]))
    index = round(sum(s["mean_abs_gap"] for s in sessions[-3:]) / len(sessions[-3:]), 2) if sessions else None
    headline = None
    if dimensions:
        d = dimensions[0]
        if d["bias"] == "calibrated":
            headline = "Your self-ratings match the evidence closely."
        else:
            direction = "overrate" if d["latest_gap"] > 0 else "underrate"
            trend = (f", down from {abs(d['first_gap']):.1f}" if d["trend"] and d["trend"] > 0 else
                     f", up from {abs(d['first_gap']):.1f}" if d["trend"] and d["trend"] < 0 else "")
            headline = f"You {direction} {d['name'].lower()} by {abs(d['latest_gap']):.1f} points{trend}."
    return {"index": index, "scale": "mean |self - evidence| on 1-5 rubrics over the last 3 sessions (0 = perfectly calibrated)",
            "headline": headline, "dimensions": dimensions, "sessions": sessions}
