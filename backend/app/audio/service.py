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
        id="aws-polly-matthew",
        name="Matthew (AWS Polly Neural)",
        gender="Male",
        accent="US",
        provider="aws-polly",
        description="Senior Staff Engineer & Hiring Manager. Authoritative, direct, crisp."
    ),
    VoiceOption(
        id="aws-polly-kajal",
        name="Kajal (AWS Polly Neural)",
        gender="Female",
        accent="India",
        provider="aws-polly",
        description="Principal Systems Architect. Natural Indian English rhythm, methodical and sharp."
    ),
    VoiceOption(
        id="aws-polly-ruth",
        name="Ruth (AWS Polly Generative)",
        gender="Female",
        accent="US",
        provider="aws-polly",
        description="AWS Polly Generative Engine. Ultra-realistic conversational human prosody."
    ),
    VoiceOption(
        id="aws-polly-arthur",
        name="Arthur (AWS Polly Neural)",
        gender="Male",
        accent="UK",
        provider="aws-polly",
        description="Technical Lead. Dry, analytical, and measured British accent."
    ),
    VoiceOption(
        id="en-US-ChristopherNeural",
        name="Christopher (Studio Neural)",
        gender="Male",
        accent="US",
        provider="edge-azure",
        description="Senior Staff Engineer & Hiring Manager. Direct, crisp, zero artificial praise."
    ),
    VoiceOption(
        id="en-US-JennyNeural",
        name="Jenny (Studio Neural)",
        gender="Female",
        accent="US",
        provider="edge-azure",
        description="Lead Systems Architect. Clear, precise, articulate."
    ),
    VoiceOption(
        id="en-IN-PrabhatNeural",
        name="Prabhat (Studio Neural)",
        gender="Male",
        accent="India",
        provider="edge-azure",
        description="Senior Technical Lead. Natural Indian English rhythm, methodical and sharp."
    ),
    VoiceOption(
        id="en-IN-NeerjaNeural",
        name="Neerja (Studio Neural)",
        gender="Female",
        accent="India",
        provider="edge-azure",
        description="Principal Systems Engineer. Authentic Indian English cadence and clarity."
    ),
    VoiceOption(
        id="en-GB-RyanNeural",
        name="Ryan (Studio Neural)",
        gender="Male",
        accent="UK",
        provider="edge-azure",
        description="Technical Lead. Dry, analytical, and measured British accent."
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
    # Strip markdown code blocks ```...``` replacing with a spoken placeholder
    text = re.sub(r'```[\s\S]*?```', ' [code snippet omitted for audio] ', raw_text)
    # Strip markdown URLs [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Strip markdown bold/italics/headers
    text = re.sub(r'[*_~`#>]', '', text)
    # Strip bracketed hint tags like [Level 1 Hint - Socratic Direction]
    text = re.sub(r'\[Level \d+.*?\]', 'Hint: ', text)
    # Clean up multi-dashes or bullets
    text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_whisper_model():
    """Lazy initialize local faster-whisper singleton model."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Initializing faster-whisper (base.en, cpu, int8)...")
            try:
                _WHISPER_MODEL = WhisperModel("base.en", device="cpu", compute_type="int8")
            except Exception:
                logger.info("Falling back to tiny.en...")
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
        if target_voice.startswith("aws-polly-"):
            try:
                import boto3
                aws_access_key = None
                aws_secret_key = None
                aws_session_token = None
                aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

                # Check database credentials if available
                if user_id and db:
                    config = await ProviderConfigService.get_config(db, user_id)
                    creds = await ModelResolver.resolve_credentials(config, user_id)
                    if creds.provider_name == "bedrock" and creds.aws_access_key and creds.aws_secret_key:
                        aws_access_key = creds.aws_access_key
                        aws_secret_key = creds.aws_secret_key
                        aws_session_token = creds.aws_session_token
                        aws_region = creds.aws_region or aws_region

                # Check environment / AWS CLI variables
                if not aws_access_key:
                    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
                    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
                    aws_session_token = os.environ.get("AWS_SESSION_TOKEN")

                if aws_access_key and aws_secret_key:
                    polly_voice = target_voice.replace("aws-polly-", "").capitalize()
                    engine = "generative" if polly_voice.lower() in ("ruth", "danielle") else "neural"
                    polly_client = boto3.client(
                        "polly",
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key,
                        aws_session_token=aws_session_token,
                        region_name=aws_region
                    )
                    polly_resp = polly_client.synthesize_speech(
                        Engine=engine,
                        VoiceId=polly_voice,
                        OutputFormat="mp3",
                        Text=clean_text[:3000]
                    )
                    return polly_resp["AudioStream"].read()
            except Exception as e:
                logger.warning(f"AWS Polly TTS synthesis failed, falling back to studio neural TTS: {e}")

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
        neural_voice_map = {
            "aws-polly-matthew": "en-US-ChristopherNeural",
            "aws-polly-kajal": "en-IN-NeerjaNeural",
            "aws-polly-ruth": "en-US-JennyNeural",
            "aws-polly-arthur": "en-GB-RyanNeural",
            "aws-polly-joanna": "en-US-JennyNeural",
            "en-US-ChristopherNeural": "en-US-ChristopherNeural",
            "en-US-JennyNeural": "en-US-JennyNeural",
            "en-IN-PrabhatNeural": "en-IN-PrabhatNeural",
            "en-IN-NeerjaNeural": "en-IN-NeerjaNeural",
            "en-GB-RyanNeural": "en-GB-RyanNeural",
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
        Supports Azure OpenAI Whisper, Vaani.dev STT, and local faster-whisper with domain vocabulary conditioning.
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

        # 3. High-Speed Local Faster-Whisper with Domain Vocabulary Prompting
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

            def _transcribe():
                model = _get_whisper_model()
                initial_prompt = (
                    "Technical engineering interview: LeetCode, DSA, Big-O notation, O(1), O(N), O(N^2), "
                    "O(N log N), dynamic programming, memoization, recursion, two pointers, sliding window, "
                    "hash map, dictionary, binary search, tree, graph, Python, FastAPI, Redis, PostgreSQL, "
                    "latency, throughput."
                )
                segments, info = model.transcribe(
                    temp_path,
                    initial_prompt=initial_prompt,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300),
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
