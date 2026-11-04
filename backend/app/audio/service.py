import asyncio
import io
import os
import re
import tempfile
import uuid
from typing import List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.audio.schemas import VoiceOption
from backend.app.providers.resolver import ModelResolver
from backend.app.providers.service import ProviderConfigService

# Global in-memory cache for faster-whisper model
_WHISPER_MODEL = None
_WHISPER_LOCK = asyncio.Lock()

AVAILABLE_VOICES: List[VoiceOption] = [
    VoiceOption(
        id="en-US-ChristopherNeural",
        name="Christopher (US Male)",
        gender="Male",
        accent="US",
        provider="edge-azure",
        description="Senior Staff Engineer & Hiring Manager. Authoritative, direct, crisp."
    ),
    VoiceOption(
        id="en-US-JennyNeural",
        name="Jenny (US Female)",
        gender="Female",
        accent="US",
        provider="edge-azure",
        description="Lead Systems Architect. Clear, precise, articulate."
    ),
    VoiceOption(
        id="en-IN-NeerjaNeural",
        name="Neerja (India Female)",
        gender="Female",
        accent="India",
        provider="edge-azure",
        description="Principal Systems Engineer. Authentic Indian English cadence and clarity."
    ),
    VoiceOption(
        id="en-IN-PrabhatNeural",
        name="Prabhat (India Male)",
        gender="Male",
        accent="India",
        provider="edge-azure",
        description="Senior Technical Lead. Natural Indian English rhythm, methodical and sharp."
    ),
    VoiceOption(
        id="en-GB-RyanNeural",
        name="Ryan (UK Male)",
        gender="Male",
        accent="UK",
        provider="edge-azure",
        description="Technical Lead. Dry, analytical, and measured British accent."
    ),
    VoiceOption(
        id="aws-polly-joanna",
        name="Joanna (AWS Polly Neural)",
        gender="Female",
        accent="US",
        provider="aws-polly",
        description="AWS Polly Neural conversational voice."
    ),
    VoiceOption(
        id="aws-polly-matthew",
        name="Matthew (AWS Polly Neural)",
        gender="Male",
        accent="US",
        provider="aws-polly",
        description="AWS Polly Neural male conversational voice."
    ),
    VoiceOption(
        id="aws-polly-kajal",
        name="Kajal (AWS Polly Neural)",
        gender="Female",
        accent="India",
        provider="aws-polly",
        description="AWS Polly Indian English Neural voice."
    ),
    VoiceOption(
        id="vaani-indic-priya",
        name="Priya (Vaani AI Research)",
        gender="Female",
        accent="India",
        provider="vaani",
        description="Vaani AI studio voice with fluent multilingual pronunciation."
    ),
    VoiceOption(
        id="azure-alloy",
        name="Alloy (Azure OpenAI)",
        gender="Neutral",
        accent="US",
        provider="azure-openai",
        description="Azure OpenAI tts-1 natural conversational model."
    ),
]

def clean_text_for_speech(raw_text: str) -> str:
    """Strip markdown symbols, code fences, and bracketed metadata for natural prosody."""
    if not raw_text:
        return ""
    # Strip markdown code blocks ```...```
    text = re.sub(r'```[\s\S]*?```', ' [code snippet omitted for audio] ', raw_text)
    # Strip markdown bold/italics
    text = re.sub(r'[*_~`#]', '', text)
    # Strip bracketed hint tags like [Level 1 Hint - Socratic Direction]
    text = re.sub(r'\[Level \d+.*?\]', 'Hint: ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_whisper_model():
    """Lazy initialize local faster-whisper singleton model."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Initializing faster-whisper (tiny.en, cpu, int8)...")
            _WHISPER_MODEL = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logger.info("faster-whisper model successfully loaded.")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper: {e}")
            raise
    return _WHISPER_MODEL

class AudioService:
    @classmethod
    def get_voices(cls) -> List[VoiceOption]:
        return AVAILABLE_VOICES

    @classmethod
    async def synthesize_speech(
        cls,
        text: str,
        voice: Optional[str] = "en-US-ChristopherNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> bytes:
        """
        Synthesize text to high-clarity MP3 audio bytes.
        Prioritizes:
          1. Azure OpenAI Audio (if Azure credentials + azure voice configured)
          2. AWS Polly Neural (if AWS credentials + aws-polly voice configured)
          3. Vaani.dev API (if VAANI_API_KEY + vaani voice configured)
          4. Edge Neural Speech (Universal studio clarity fallback)
        """
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            clean_text = "No content to read."

        target_voice = voice or "en-US-ChristopherNeural"

        # 1. Check AWS Polly Neural
        if target_voice.startswith("aws-polly-") and user_id and db:
            try:
                import boto3
                config = await ProviderConfigService.get_config(db, user_id)
                creds = await ModelResolver.resolve_credentials(config, user_id)
                if creds.provider_name == "bedrock" and creds.aws_access_key and creds.aws_secret_key:
                    polly_voice = target_voice.replace("aws-polly-", "").capitalize()
                    polly_client = boto3.client(
                        "polly",
                        aws_access_key_id=creds.aws_access_key,
                        aws_secret_access_key=creds.aws_secret_key,
                        aws_session_token=creds.aws_session_token,
                        region_name=creds.aws_region or "us-east-1"
                    )
                    polly_resp = polly_client.synthesize_speech(
                        Engine="neural",
                        VoiceId=polly_voice,
                        OutputFormat="mp3",
                        Text=clean_text[:3000]
                    )
                    return polly_resp["AudioStream"].read()
            except Exception as e:
                logger.warning(f"AWS Polly TTS synthesis failed, falling back to neural TTS: {e}")

        # 2. Check Azure OpenAI TTS
        if target_voice.startswith("azure-") and user_id and db:
            try:
                from openai import AzureOpenAI
                config = await ProviderConfigService.get_config(db, user_id)
                creds = await ModelResolver.resolve_credentials(config, user_id)
                if creds.provider_name == "azure" and creds.azure_api_key and creds.azure_endpoint:
                    azure_client = AzureOpenAI(
                        azure_endpoint=creds.azure_endpoint,
                        api_key=creds.azure_api_key,
                        api_version=creds.azure_api_version or "2024-06-01"
                    )
                    azure_voice = target_voice.replace("azure-", "")
                    speech_resp = azure_client.audio.speech.create(
                        model="tts-1",
                        voice=azure_voice or "alloy",
                        input=clean_text[:3000]
                    )
                    return speech_resp.content
            except Exception as e:
                logger.warning(f"Azure OpenAI Audio TTS failed, falling back to neural TTS: {e}")

        # 3. Check Vaani.dev / VaaniStack TTS
        if (target_voice.startswith("vaani-") or settings.VAANI_API_KEY) and settings.VAANI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.VAANI_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "text": clean_text[:3000],
                    "voice": "priya",
                    "language": "en",
                    "format": "mp3"
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{settings.VAANI_API_URL}/tts", json=payload, headers=headers)
                    if resp.status_code == 200 and resp.content:
                        return resp.content
            except Exception as e:
                logger.warning(f"Vaani TTS API failed, falling back to neural TTS: {e}")

        # 4. Universal High-Clarity Studio Neural Fallback (Edge Neural Engine)
        # Maps requested voice to valid Microsoft Azure neural voices
        neural_voice_map = {
            "en-US-ChristopherNeural": "en-US-ChristopherNeural",
            "en-US-JennyNeural": "en-US-JennyNeural",
            "en-IN-NeerjaNeural": "en-IN-NeerjaNeural",
            "en-IN-PrabhatNeural": "en-IN-PrabhatNeural",
            "en-GB-RyanNeural": "en-GB-RyanNeural",
            "aws-polly-joanna": "en-US-JennyNeural",
            "aws-polly-matthew": "en-US-ChristopherNeural",
            "aws-polly-kajal": "en-IN-NeerjaNeural",
            "vaani-indic-priya": "en-IN-NeerjaNeural",
            "azure-alloy": "en-US-ChristopherNeural",
        }
        chosen_voice = neural_voice_map.get(target_voice, "en-US-ChristopherNeural")

        try:
            import edge_tts
            communicate = edge_tts.Communicate(clean_text[:4000], chosen_voice, rate=rate, pitch=pitch)
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])
            if audio_buffer:
                return bytes(audio_buffer)
        except Exception as e:
            logger.error(f"Edge TTS synthesis error for voice {chosen_voice}: {e}")

        # Fallback to default Christopher voice if selected voice failed
        try:
            import edge_tts
            communicate = edge_tts.Communicate(clean_text[:4000], "en-US-ChristopherNeural")
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])
            if audio_buffer:
                return bytes(audio_buffer)
        except Exception as e:
            logger.error(f"Ultimate fallback TTS error: {e}")
            raise

        raise RuntimeError("Failed to synthesize speech using all available neural engines.")

    @classmethod
    async def transcribe_audio(
        cls,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        content_type: str = "audio/webm",
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """
        Transcribe audio bytes (WebM, WAV, MP3, etc.) into text.
        Supports Azure OpenAI Whisper, Vaani.dev STT, and local faster-whisper.
        """
        if not audio_bytes:
            return ""

        # 1. Try Azure OpenAI Whisper if user configured Azure
        if user_id and db:
            try:
                from openai import AzureOpenAI
                config = await ProviderConfigService.get_config(db, user_id)
                creds = await ModelResolver.resolve_credentials(config, user_id)
                if creds.provider_name == "azure" and creds.azure_api_key and creds.azure_endpoint:
                    azure_client = AzureOpenAI(
                        azure_endpoint=creds.azure_endpoint,
                        api_key=creds.azure_api_key,
                        api_version=creds.azure_api_version or "2024-06-01"
                    )
                    transcription = azure_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=(filename, audio_bytes, content_type)
                    )
                    if hasattr(transcription, "text") and transcription.text:
                        return transcription.text.strip()
            except Exception as e:
                logger.info(f"Azure Whisper STT unavailable or bypassed, using fast local whisper: {e}")

        # 2. Try Vaani STT if configured
        if settings.VAANI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.VAANI_API_KEY}"}
                files = {"audio": (filename, audio_bytes, content_type)}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(f"{settings.VAANI_API_URL}/stt", files=files, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("text") or data.get("transcript") or ""
                        if text:
                            return text.strip()
            except Exception as e:
                logger.warning(f"Vaani STT API failed: {e}")

        # 3. High-Speed Local Faster-Whisper
        # Determine appropriate file extension
        ext = ".webm"
        if "wav" in content_type or filename.endswith(".wav"):
            ext = ".wav"
        elif "mp3" in content_type or filename.endswith(".mp3"):
            ext = ".mp3"
        elif "mp4" in content_type or "m4a" in content_type or filename.endswith(".mp4") or filename.endswith(".m4a"):
            ext = ".m4a"
        elif "ogg" in content_type or filename.endswith(".ogg"):
            ext = ".ogg"

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            # Run faster-whisper in a thread pool with VAD noise filtering and multi-accent support
            def _transcribe():
                model = _get_whisper_model()
                segments, info = model.transcribe(
                    temp_path,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400),
                )
                return " ".join([seg.text for seg in segments]).strip()


            result = await asyncio.to_thread(_transcribe)
            return result
        except Exception as e:
            logger.error(f"Local faster-whisper transcription error: {e}")
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
