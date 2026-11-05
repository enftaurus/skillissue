import asyncio
import io
import os
import re
import tempfile
import threading
import uuid
from typing import List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.audio.schemas import VoiceOption
from backend.app.providers.resolver import ModelResolver
from backend.app.providers.service import ProviderConfigService

# Global in-memory cache for faster-whisper model (loaded inside worker threads)
_WHISPER_MODEL = None
_WHISPER_LOCK = threading.Lock()

AVAILABLE_VOICES: List[VoiceOption] = [
    VoiceOption(
        id="aws-polly-matthew",
        name="Matthew (AWS Polly Generative)",
        gender="Male",
        accent="US",
        provider="aws-polly",
        description="Senior Staff Engineer & Hiring Manager. Authoritative, direct, crisp."
    ),
    VoiceOption(
        id="aws-polly-kajal",
        name="Kajal (AWS Polly Generative)",
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
        id="aws-polly-stephen",
        name="Stephen (AWS Polly Generative)",
        gender="Male",
        accent="US",
        provider="aws-polly",
        description="Generative engine. Calm, conversational senior-engineer delivery."
    ),
    VoiceOption(
        id="aws-polly-danielle",
        name="Danielle (AWS Polly Generative)",
        gender="Female",
        accent="US",
        provider="aws-polly",
        description="Generative engine. Warm, natural hiring-manager tone."
    ),
    VoiceOption(
        id="aws-polly-arjun",
        name="Arjun (AWS Polly Generative)",
        gender="Male",
        accent="India",
        provider="aws-polly",
        description="Generative engine. Natural Indian English."
    ),
    VoiceOption(
        id="aws-polly-kiara",
        name="Kiara (AWS Polly Generative)",
        gender="Female",
        accent="India",
        provider="aws-polly",
        description="Generative engine. Natural Indian English."
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

# Polly voices that support the generative engine (us-east-1); others fall back to neural.
GENERATIVE_POLLY_VOICES = {"matthew", "ruth", "stephen", "danielle", "joanna", "salli", "tiffany", "kenneth",
                           "nate", "kajal", "arjun", "kiara"}

_platform_aws: Optional[bool] = None


def platform_aws_available() -> bool:
    """True when the server itself has AWS credentials (default chain) and platform voice is enabled."""
    global _platform_aws
    if not settings.PLATFORM_VOICE_ENABLED:
        return False
    if _platform_aws is None:
        try:
            import boto3
            _platform_aws = boto3.Session().get_credentials() is not None
        except Exception:
            _platform_aws = False
    return _platform_aws


def clean_text_for_speech(raw_text: str) -> str:
    """Turn interviewer markdown into speakable text without losing technical meaning."""
    if not raw_text:
        return ""
    # Code blocks are on screen; say so instead of reading symbols.
    text = re.sub(r'```[\s\S]*?```', ' (code shown on screen) ', raw_text)
    # Markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Hint tags like [Level 1 Hint]: ...
    text = re.sub(r'\[Level (\d+)[^\]]*\]:?', r'Level \1 hint:', text)
    # Big-O and operators, before symbol stripping
    text = re.sub(r'\bO\(\s*([^)]+?)\s*\)', lambda m: 'O of ' + m.group(1), text)
    text = re.sub(r'(\w)\s*\^\s*2\b', r'\1 squared', text)
    text = re.sub(r'(\w)\s*\^\s*(\d+)', r'\1 to the \2', text)
    for sym, word in ((">=", " greater than or equal to "), ("<=", " less than or equal to "), ("!=", " not equal to "),
                      ("==", " equals "), ("->", " to "), ("=>", " gives "), ("≥", " at least "), ("≤", " at most ")):
        text = text.replace(sym, word)
    text = re.sub(r'(?<=\w)\s+>\s+(?=\w)', ' greater than ', text)
    text = re.sub(r'(?<=\w)\s+<\s+(?=\w)', ' less than ', text)
    # snake_case identifiers read as words
    text = re.sub(r'(?<=[A-Za-z0-9])_(?=[A-Za-z0-9])', ' ', text)
    # Markdown emphasis / headers / quotes / inline code ticks
    text = re.sub(r'[*~`#>]', '', text)
    text = re.sub(r'(?<!\w)_|_(?!\w)', '', text)
    # Bullets
    text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _get_whisper_model():
    """Lazy, thread-safe initialisation of the local faster-whisper singleton."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    with _WHISPER_LOCK:
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
    async def get_voices_for_user(cls, user_id: Optional[str], db: Optional[AsyncSession]) -> List[VoiceOption]:
        """Mark cloud voices unavailable when the caller has no credentials for that provider,
        so the UI never labels Edge audio as 'AWS Polly'."""
        has_aws = platform_aws_available() or bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"))
        has_azure = False
        if user_id and db:
            try:
                config = await ProviderConfigService.get_config(db, user_id)
                if config is not None:
                    creds = await ModelResolver.resolve_credentials(db, user_id)
                    has_aws = has_aws or bool(creds.provider_name == "bedrock" and creds.aws_access_key and creds.aws_secret_key)
                    has_azure = bool(creds.provider_name == "azure" and creds.azure_api_key and creds.azure_endpoint)
            except Exception as e:
                logger.info(f"Voice availability check fell back to defaults: {type(e).__name__}")
        voices: List[VoiceOption] = []
        for v in AVAILABLE_VOICES:
            available, reason = True, None
            if v.provider == "aws-polly" and not has_aws:
                available, reason = False, "Needs AWS (Bedrock) credentials"
            elif v.provider == "azure-openai" and not has_azure:
                available, reason = False, "Needs an Azure OpenAI provider with a TTS deployment"
            voices.append(v.model_copy(update={"available": available, "unavailable_reason": reason}))
        return voices

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
        clean_text = clean_text_for_speech(text)[:6000]
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
                    creds = await ModelResolver.resolve_credentials(db, user_id)
                    if creds.provider_name == "bedrock" and creds.aws_access_key and creds.aws_secret_key:
                        aws_access_key = creds.aws_access_key
                        aws_secret_key = creds.aws_secret_key
                        aws_session_token = creds.aws_session_token
                        aws_region = creds.aws_region or aws_region

                polly_voice = target_voice.replace("aws-polly-", "").capitalize()
                engine = "generative" if polly_voice.lower() in GENERATIVE_POLLY_VOICES else "neural"
                if aws_access_key and aws_secret_key:
                    polly_client = boto3.client(
                        "polly",
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key,
                        aws_session_token=aws_session_token,
                        region_name=aws_region
                    )
                elif platform_aws_available():
                    # Platform-provided voice (ADR 0025): server's default AWS credential chain.
                    polly_client = boto3.Session().client("polly", region_name=settings.SONIC_REGION)
                else:
                    polly_client = None

                if polly_client is not None:
                    def _polly() -> bytes:
                        resp = polly_client.synthesize_speech(
                            Engine=engine, VoiceId=polly_voice, OutputFormat="mp3", Text=clean_text[:3000]
                        )
                        return resp["AudioStream"].read()
                    return await asyncio.to_thread(_polly)
            except Exception as e:
                logger.warning(f"AWS Polly TTS synthesis failed, falling back to studio neural TTS: {e}")

        # 2. Check Azure OpenAI TTS
        if target_voice.startswith("azure-") and user_id and db:
            try:
                from openai import AzureOpenAI
                config = await ProviderConfigService.get_config(db, user_id)
                creds = await ModelResolver.resolve_credentials(db, user_id)
                if creds.provider_name == "azure" and creds.azure_api_key and creds.azure_endpoint:
                    azure_client = AzureOpenAI(
                        azure_endpoint=creds.azure_endpoint,
                        api_key=creds.azure_api_key,
                        api_version=creds.azure_api_version or "2024-06-01"
                    )
                    azure_voice = target_voice.replace("azure-", "")
                    speech_resp = await asyncio.to_thread(
                        azure_client.audio.speech.create,
                        model="tts-1", voice=azure_voice or "alloy", input=clean_text[:3000],
                    )
                    return speech_resp.content
            except Exception as e:
                logger.warning(f"Azure OpenAI Audio TTS failed, falling back to neural TTS: {e}")

        # 3. Check Vaani.dev / VaaniStack TTS
        if target_voice.startswith("vaani-") and settings.VAANI_API_KEY:
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
            communicate = edge_tts.Communicate(clean_text, chosen_voice, rate=rate, pitch=pitch)
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
            communicate = edge_tts.Communicate(clean_text, "en-US-ChristopherNeural")
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
        words_out: Optional[list] = None,
    ) -> str:
        """
        Transcribe audio bytes (WebM, WAV, MP3, etc.) into text.
        Supports Azure OpenAI Whisper, Vaani.dev STT, and local faster-whisper with domain vocabulary conditioning.
        """
        if not audio_bytes:
            return ""
        self_words = words_out if words_out is not None else []

        # 1. Try Azure OpenAI Whisper if user configured Azure
        if user_id and db:
            try:
                from openai import AzureOpenAI
                config = await ProviderConfigService.get_config(db, user_id)
                creds = await ModelResolver.resolve_credentials(db, user_id)
                if creds.provider_name == "azure" and creds.azure_api_key and creds.azure_endpoint:
                    azure_client = AzureOpenAI(
                        azure_endpoint=creds.azure_endpoint,
                        api_key=creds.azure_api_key,
                        api_version=creds.azure_api_version or "2024-06-01"
                    )
                    transcription = await asyncio.to_thread(
                        azure_client.audio.transcriptions.create,
                        model="whisper-1", file=(filename, audio_bytes, content_type),
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

        # 3. Opt-in platform Transcribe (benchmarked worse than whisper without a custom vocabulary)
        if settings.STT_PROVIDER == "transcribe" and platform_aws_available():
            try:
                from backend.app.audio.transcribe_aws import transcribe_with_aws
                text = await transcribe_with_aws(audio_bytes)
                if text:
                    return text
            except Exception:
                pass

        # 4. High-Speed Local Faster-Whisper with Domain Vocabulary Prompting
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
                    word_timestamps=True,
                )
                segs = list(segments)
                words = [(w.word, float(w.start), float(w.end)) for seg in segs for w in (seg.words or [])]
                return " ".join([seg.text for seg in segs]).strip(), words

            text, words = await asyncio.to_thread(_transcribe)
            self_words.extend(words)
            return text
        except Exception as e:
            logger.error(f"Local faster-whisper transcription error: {e}")
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
