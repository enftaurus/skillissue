from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.comprehension.bank import ITEMS, ITEMS_BY_ID, Item
from backend.app.comprehension.grading import grade_answer
from backend.app.core.errors import AppException, EntityNotFoundError
from backend.app.core.logging import logger
from backend.app.database.models import ComprehensionSession

MAX_ANSWER_CHARS = 4000
GRACE = timedelta(minutes=2)


def public_item(item: Item, include_questions: bool = True) -> Dict[str, Any]:
    data = {"id": item.id, "title": item.title, "difficulty": item.difficulty, "tags": item.tags,
            "context": item.context, "language": item.language, "estimated_minutes": item.estimated_minutes,
            "question_count": len(item.questions)}
    if include_questions:
        data["files"] = item.clean_files()
        data["questions"] = [{"id": q.id, "type": q.type, "prompt": q.prompt} for q in item.questions]
    return data


def reveal(item: Item) -> Dict[str, Any]:
    return {
        "bug_lines": [{"file": f, "line": ln} for f, ln in item.bug_lines()],
        "questions": {q.id: {"key_points": q.key_points, "expected_output": q.expected_output} for q in item.questions},
    }


def _session_payload(session: ComprehensionSession, item: Item) -> Dict[str, Any]:
    answers = {qid: {k: v for k, v in a.items() if k in ("answer", "follow_up", "follow_up_answer", "score", "verdict",
                                                          "feedback", "location_correct", "done")}
               for qid, a in (session.answers or {}).items()}
    data = {"id": session.id, "status": session.status, "score": session.score,
            "time_limit_minutes": session.time_limit_minutes, "started_at": session.started_at.isoformat(),
            "finished_at": session.finished_at.isoformat() if session.finished_at else None,
            "item": public_item(item), "answers": answers}
    if session.status == "completed":
        data["reveal"] = reveal(item)
    return data


class ComprehensionService:
    @staticmethod
    def list_items() -> List[Dict[str, Any]]:
        return [public_item(i, include_questions=False) for i in ITEMS]

    @staticmethod
    async def _get(db: AsyncSession, user_id: str, session_id: str) -> ComprehensionSession:
        s = (await db.execute(select(ComprehensionSession).where(
            ComprehensionSession.id == session_id, ComprehensionSession.user_id == user_id))).scalar_one_or_none()
        if s is None:
            raise EntityNotFoundError("ComprehensionSession", session_id)
        return s

    @classmethod
    async def start(cls, db: AsyncSession, user_id: str, item_id: str) -> Dict[str, Any]:
        item = ITEMS_BY_ID.get(item_id)
        if item is None:
            raise EntityNotFoundError("ComprehensionItem", item_id)
        s = ComprehensionSession(user_id=user_id, item_id=item.id, time_limit_minutes=item.estimated_minutes, answers={})
        db.add(s)
        await db.commit()
        await db.refresh(s)
        return _session_payload(s, item)

    @classmethod
    async def get(cls, db: AsyncSession, user_id: str, session_id: str) -> Dict[str, Any]:
        s = await cls._get(db, user_id, session_id)
        return _session_payload(s, ITEMS_BY_ID[s.item_id])

    @classmethod
    async def answer(cls, db: AsyncSession, user_id: str, session_id: str, question_id: str, answer: str,
                     provider: Any = None) -> Dict[str, Any]:
        s = await cls._get(db, user_id, session_id)
        if s.status != "in_progress":
            raise AppException("This session is finished.", code="SESSION_FINISHED")
        started = s.started_at if s.started_at.tzinfo else s.started_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > started + timedelta(minutes=s.time_limit_minutes) + GRACE:
            raise AppException("Time's up for this item. Finish the session to see the answers.", code="SESSION_EXPIRED")
        item = ITEMS_BY_ID[s.item_id]
        q = next((x for x in item.questions if x.id == question_id), None)
        if q is None:
            raise EntityNotFoundError("Question", question_id)
        text = (answer or "").replace("\x00", "").strip()
        if not text:
            raise AppException("Write an answer first.", code="EMPTY_ANSWER")
        if len(text) > MAX_ANSWER_CHARS:
            raise AppException(f"Keep answers under {MAX_ANSWER_CHARS} characters.", code="ANSWER_TOO_LONG")

        answers = dict(s.answers or {})
        prev = answers.get(q.id)
        if prev and prev.get("done"):
            raise AppException("You've already answered this question.", code="ALREADY_ANSWERED")

        if prev and prev.get("follow_up"):
            # The reviewer's follow-up: grade the combined answer and keep the better score.
            grade = await grade_answer(item, q, prev["answer"] + "\n" + text, provider)
            entry = {**prev, "follow_up_answer": text, "done": True,
                     "score": max(prev["score"], grade.score), "feedback": grade.feedback,
                     "verdict": grade.verdict if grade.score >= prev["score"] else prev["verdict"]}
            if grade.location_correct is not None:
                entry["location_correct"] = bool(prev.get("location_correct")) or grade.location_correct
        else:
            grade = await grade_answer(item, q, text, provider)
            entry = {"answer": text, "score": grade.score, "verdict": grade.verdict, "feedback": grade.feedback,
                     "location_correct": grade.location_correct, "follow_up": grade.follow_up,
                     "done": grade.follow_up is None}
        answers[q.id] = entry
        s.answers = answers
        flag_modified(s, "answers")
        await db.commit()
        return {"question_id": q.id, **{k: entry.get(k) for k in ("score", "verdict", "feedback", "location_correct",
                                                                     "follow_up", "done")}}

    @classmethod
    async def finish(cls, db: AsyncSession, user_id: str, session_id: str) -> Dict[str, Any]:
        s = await cls._get(db, user_id, session_id)
        item = ITEMS_BY_ID[s.item_id]
        if s.status != "completed":
            answers = s.answers or {}
            scores = [float((answers.get(q.id) or {}).get("score") or 0.0) for q in item.questions]
            s.score = round(100 * sum(scores) / len(scores), 1) if scores else 0.0
            s.status = "completed"
            s.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(s)
            logger.info(f"Comprehension session {s.id} finished: {s.score}")
        return _session_payload(s, item)

    @staticmethod
    async def history(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
        rows = (await db.execute(select(ComprehensionSession).where(ComprehensionSession.user_id == user_id)
                                 .order_by(ComprehensionSession.started_at.desc()).limit(50))).scalars().all()
        return [{"id": r.id, "item_id": r.item_id, "title": ITEMS_BY_ID[r.item_id].title if r.item_id in ITEMS_BY_ID else r.item_id,
                 "status": r.status, "score": r.score, "started_at": r.started_at.isoformat()} for r in rows]
