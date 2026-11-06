"""
Platform speech-to-text via Amazon Transcribe streaming (ADR 0025): better accuracy on accents and
technical vocabulary than local faster-whisper base.en. Audio is decoded in memory and streamed;
nothing is stored.
"""
import asyncio
import io
from typing import List, Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger

CHUNK = 3200  # 100 ms of 16 kHz s16 mono


def decode_to_pcm16k(audio_bytes: bytes) -> bytes:
    """Decode any browser recording (webm/opus, mp4, ogg, wav, mp3) to 16 kHz mono s16 PCM."""
    import av

    out = bytearray()
    with av.open(io.BytesIO(audio_bytes)) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in container.decode(audio=0):
            for f in resampler.resample(frame):
                out.extend(bytes(f.planes[0])[: f.samples * 2])
        for f in resampler.resample(None) or []:
            out.extend(bytes(f.planes[0])[: f.samples * 2])
    return bytes(out)


async def transcribe_pcm(pcm: bytes, language_code: Optional[str] = None) -> str:
    from amazon_transcribe.client import TranscribeStreamingClient
    from amazon_transcribe.handlers import TranscriptResultStreamHandler

    final: List[str] = []

    class _Handler(TranscriptResultStreamHandler):
        async def handle_transcript_event(self, transcript_event):
            for result in transcript_event.transcript.results:
                if not result.is_partial and result.alternatives:
                    final.append(result.alternatives[0].transcript)

    client = TranscribeStreamingClient(region=settings.SONIC_REGION)
    stream = await client.start_stream_transcription(
        language_code=language_code or settings.TRANSCRIBE_LANGUAGE,
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    async def _send():
        for i in range(0, len(pcm), CHUNK):
            await stream.input_stream.send_audio_event(audio_chunk=pcm[i:i + CHUNK])
        await stream.input_stream.end_stream()

    handler = _Handler(stream.output_stream)
    await asyncio.gather(_send(), handler.handle_events())
    return " ".join(t.strip() for t in final if t.strip()).strip()


async def transcribe_with_aws(audio_bytes: bytes) -> str:
    pcm = await asyncio.to_thread(decode_to_pcm16k, audio_bytes)
    if len(pcm) < CHUNK:  # under 100 ms of audio
        return ""
    try:
        return await asyncio.wait_for(transcribe_pcm(pcm), timeout=30)
    except Exception as e:
        logger.info(f"Transcribe streaming unavailable, falling back: {type(e).__name__}: {str(e)[:150]}")
        raise
