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
