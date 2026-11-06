from typing import Optional, Tuple
from fastapi import APIRouter, Depends, File, UploadFile, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.database.models import User, CandidateAssessment
from backend.app.integrity.dependencies import get_integrity_actor
from backend.app.core.config import settings
from backend.app.audio.schemas import TtsRequest, SttResponse, VoiceListResponse
from backend.app.audio.service import AudioService
from backend.app.audio.delivery import delivery_metrics
from backend.app.core.logging import logger

router = APIRouter(prefix="/audio", tags=["Audio & Speech"])

async def require_audio_actor(
    actor: Tuple[Optional[User], Optional[CandidateAssessment]] = Depends(get_integrity_actor),
) -> Tuple[Optional[User], Optional[CandidateAssessment]]:
    """Audio synthesis/transcription costs CPU and provider credits: require a signed-in user
    or a valid enterprise candidate assessment token."""
    user, candidate = actor
    if user is None and candidate is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return actor


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(
    actor: Tuple[Optional[User], Optional[CandidateAssessment]] = Depends(get_integrity_actor),
    db: AsyncSession = Depends(get_db),
):
    """List voices, marking cloud voices the caller has no credentials for as unavailable."""
    user = actor[0]
    voices = await AudioService.get_voices_for_user(user.id if user else None, db)
    polly_ok = any(v.id == "aws-polly-matthew" and v.available for v in voices)
    return VoiceListResponse(voices=voices, default_voice="aws-polly-matthew" if polly_ok else "en-US-ChristopherNeural")

@router.post("/tts")
async def text_to_speech(
    payload: TtsRequest,
    actor: Tuple[Optional[User], Optional[CandidateAssessment]] = Depends(require_audio_actor),
    db: AsyncSession = Depends(get_db),
):
    """
    Synthesize text into studio-clarity MP3 audio stream.
    Compatible with all browsers (Firefox, Chrome, Safari, Edge) via standard HTML5 Audio.
    """
    current_user = actor[0]
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
                "Cache-Control": "private, max-age=3600",
            },
        )
    except Exception as e:
        logger.error(f"TTS endpoint error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech synthesis is temporarily unavailable.",
        )

@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    actor: Tuple[Optional[User], Optional[CandidateAssessment]] = Depends(require_audio_actor),
    db: AsyncSession = Depends(get_db),
):
    """
    Transcribe uploaded audio file (WebM, WAV, MP3, etc.) to text.
    Works seamlessly in Firefox where native Web Speech API is absent or broken.
    """
    current_user = actor[0]
    max_bytes = settings.AUDIO_MAX_UPLOAD_BYTES
    content = await audio.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Recording is too large (max {max_bytes // (1024 * 1024)} MB). Keep answers under a few minutes.",
        )
    if not content:
        return SttResponse(text="", language="en", duration_seconds=0.0)
    try:

        user_id = current_user.id if current_user else None
        words: list = []
        transcribed_text = await AudioService.transcribe_audio(
            audio_bytes=content,
            filename=audio.filename or "recording.webm",
            content_type=audio.content_type or "audio/webm",
            user_id=user_id,
            db=db,
            words_out=words,
        )
        metrics = delivery_metrics(transcribed_text, words=words or None)
        return SttResponse(text=transcribed_text, language="en",
                           duration_seconds=metrics.get("duration_s") if metrics else None, delivery=metrics)
    except Exception as e:
        logger.error(f"STT endpoint error: {type(e).__name__}: {e}")
        if "Invalid data" in str(e) or "InvalidDataError" in type(e).__name__:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not decode the recording. Try recording again.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Speech-to-text is temporarily unavailable. Type your answer instead.",
        )
