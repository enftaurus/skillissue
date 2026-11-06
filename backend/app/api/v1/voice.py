"""Live voice WebSocket (ADR 0025). Auth is the first message so tokens never appear in URLs or logs."""
import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.auth.service import AuthService
from backend.app.core.config import settings
from backend.app.core.security import decode_access_token
from backend.app.database.models import Interview
from backend.app.database.session import AsyncSessionLocal
from backend.app.interviews.agent.policy import pick_persona
from backend.app.interviews.agent.service import detect_company
from backend.app.interviews.service import InterviewService
from backend.app.voice import relay as relay_mod

router = APIRouter(prefix="/voice", tags=["Live Voice"])


@router.get("/status")
async def voice_status():
    return {"enabled": settings.VOICE_LIVE_ENABLED, "model": settings.SONIC_MODEL_ID,
            "daily_minutes": settings.VOICE_DAILY_MINUTES}


async def _reject(ws: WebSocket, code: str, message: str) -> None:
    await ws.send_json({"type": "error", "code": code, "message": message})
    await ws.close(code=4400)


@router.websocket("/ws/{interview_id}")
async def live_voice(ws: WebSocket, interview_id: str):
    await ws.accept()
    if not settings.VOICE_LIVE_ENABLED:
        return await _reject(ws, "VOICE_DISABLED", "Live voice is disabled on this server.")
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError):
        return await _reject(ws, "AUTH_REQUIRED", "Authenticate first.")
    token = first.get("token") if first.get("type") == "auth" else None
    data = None
    try:
        data = decode_access_token(token) if token else None
    except Exception:
        data = None
    if not data or "sub" not in data or data.get("token_type", "access") != "access":
        return await _reject(ws, "AUTH_REQUIRED", "Invalid or expired session.")

    async with AsyncSessionLocal() as db:
        user = await AuthService.get_by_id(db, data["sub"])
        if not user or not user.is_active:
            return await _reject(ws, "AUTH_REQUIRED", "Invalid or expired session.")
        interview = (await db.execute(
            select(Interview).options(selectinload(Interview.messages))
            .where(Interview.id == interview_id, Interview.user_id == user.id)
        )).scalar_one_or_none()
        if interview is None:
            return await _reject(ws, "NOT_FOUND", "Interview not found.")
        if interview.status != "in_progress":
            return await _reject(ws, "INTERVIEW_NOT_ACTIVE", "This interview is over.")
        user_id = user.id
        persona = pick_persona(interview.id, interview.category, detect_company(interview))

    async def send_message(transcript: str, delivery=None):
        async with AsyncSessionLocal() as tdb:
            msg = await InterviewService.send_message(tdb, user_id, interview_id, transcript,
                                                      client_turn_id=str(uuid.uuid4()), delivery=delivery)
            await tdb.commit()
            return msg

    relay = relay_mod.VoiceRelay(ws, user_id, interview, persona, send_message, voice=first.get("voice"))
    try:
        await relay.run()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


@router.websocket("/assessment/{token}")
async def live_voice_assessment(ws: WebSocket, token: str):
    """
    Speech-to-speech for an assessment/simulation interview round. Same relay as interviews: Nova Sonic hears and
    speaks; the assessment runner decides every question, stores the transcript and grades it later.
    """
    from types import SimpleNamespace
    from backend.app.core.errors import AppException
    from backend.app.database.models import CandidateAssessment
    from backend.app.enterprise import runner
    from backend.app.enterprise.service import EnterpriseService

    await ws.accept()
    if not settings.VOICE_LIVE_ENABLED:
        return await _reject(ws, "VOICE_DISABLED", "Live voice is disabled on this server.")
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError):
        return await _reject(ws, "AUTH_REQUIRED", "Authenticate first.")
    jwt = first.get("token") if first.get("type") == "auth" else None
    try:
        data = decode_access_token(jwt) if jwt else None
    except Exception:
        data = None
    if not data or "sub" not in data or data.get("token_type", "access") != "access":
        return await _reject(ws, "AUTH_REQUIRED", "Invalid or expired session.")

    async with AsyncSessionLocal() as db:
        user = await AuthService.get_by_id(db, data["sub"])
        if not user or not user.is_active:
            return await _reject(ws, "AUTH_REQUIRED", "Invalid or expired session.")
        try:
            candidate = await EnterpriseService._owned(db, user, token, lock=True)
            entry = runner.ensure_round_started(candidate, candidate.pipeline)
            if entry["round_type"] != "tough_interview":
                return await _reject(ws, "WRONG_ROUND", "Voice is only for the interview round.")
            round_view = runner.public_round(candidate, candidate.pipeline, entry)
            if not round_view.get("current_question") and not round_view.get("interview_done"):
                provider = await EnterpriseService._provider(db, candidate.pipeline)
                round_view = await runner.interview_turn(candidate, candidate.pipeline, None, provider)
            await db.commit()
        except AppException as e:
            return await _reject(ws, e.code, e.message)
        if round_view.get("interview_done"):
            return await _reject(ws, "INTERVIEW_DONE", "That's all the questions. Submit the round.")
        user_id, minutes = user.id, int(round_view.get("time_limit_minutes") or 20)
        sim = (candidate.pipeline.oa_config or {}).get("simulation_id") or ""
        company = next((c for c in ("Google", "Uber", "OpenAI") if c.lower() in sim), None)
        persona = pick_persona(candidate.id, "technical", company)
        current = round_view["current_question"]

    # The relay reads the last assistant line from `interview.messages` to open the call.
    session_view = SimpleNamespace(messages=[SimpleNamespace(role="assistant", content=current)],
                                   category="technical", target_duration_minutes=minutes)

    async def send_message(transcript: str, delivery=None):
        async with AsyncSessionLocal() as tdb:
            # Only the id is needed; the ORM user from the closed session may be expired.
            cand = await EnterpriseService._owned(tdb, SimpleNamespace(id=user_id), token, lock=True)
            provider = await EnterpriseService._provider(tdb, cand.pipeline)
            view = await runner.interview_turn(cand, cand.pipeline, transcript, provider)
            await tdb.commit()
        last = (view.get("transcript") or [{}])[-1]
        if view.get("terminated"):
            return SimpleNamespace(content=last.get("question", ""), kind="terminated", id=None)
        if view.get("interview_done"):
            return SimpleNamespace(content="That's all my questions. Submit the round when you're ready.", kind="wrapup", id=None)
        return SimpleNamespace(content=view.get("current_question") or "", kind=last.get("kind") or "question", id=None)

    relay = relay_mod.VoiceRelay(ws, user_id, session_view, persona, send_message, voice=first.get("voice"))
    try:
        await relay.run()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
