from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import security_scheme
from backend.app.core.security import decode_access_token
from backend.app.auth.service import AuthService
from backend.app.audio.schemas import TtsRequest, SttResponse, VoiceListResponse
from backend.app.audio.service import AudioService
from backend.app.core.logging import logger

router = APIRouter(prefix="/audio", tags=["Audio & Speech"])

async def get_optional_user(
    credentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None
    try:
        data = decode_access_token(credentials.credentials)
        if not data or "sub" not in data or data.get("token_type") != "access":
            return None
        return await AuthService.get_by_id(db, data["sub"])
    except Exception:
        return None

@router.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """List available studio neural voices and configured providers."""
    voices = AudioService.get_voices()
    return VoiceListResponse(voices=voices, default_voice="en-US-ChristopherNeural")

@router.post("/tts")
async def text_to_speech(
    payload: TtsRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Synthesize text into studio-clarity MP3 audio stream.
    Compatible with all browsers (Firefox, Chrome, Safari, Edge) via standard HTML5 Audio.
    """
    try:
        user_id = current_user.id if current_user else None
        audio_bytes = await AudioService.synthesize_speech(
            text=payload.text,
            voice=payload.voice,
            rate=payload.rate or "+0%",
            pitch=payload.pitch or "+0Hz",
            user_id=user_id,
            db=db,
        )
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Type": "audio/mpeg",
                "Content-Disposition": 'inline; filename="speech.mp3"',
                "Cache-Control": "public, max-age=3600",
            },
        )
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}",
        )

@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Transcribe uploaded audio file (WebM, WAV, MP3, etc.) to text.
    Works seamlessly in Firefox where native Web Speech API is absent or broken.
    """
    try:
        content = await audio.read()
        if not content:
            return SttResponse(text="", language="en", duration_seconds=0.0)

        user_id = current_user.id if current_user else None
        transcribed_text = await AudioService.transcribe_audio(
            audio_bytes=content,
            filename=audio.filename or "recording.webm",
            content_type=audio.content_type or "audio/webm",
            user_id=user_id,
            db=db,
        )
        return SttResponse(text=transcribed_text, language="en")
    except Exception as e:
        logger.error(f"STT endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech-to-text transcription failed: {str(e)}",
        )
