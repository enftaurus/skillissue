import io
import pytest
import httpx
from backend.app.audio.service import clean_text_for_speech, AudioService

@pytest.mark.asyncio
async def test_clean_text_for_speech():
    raw = "Here is the plan:\n```python\nprint('hello')\n```\n[Level 1 Hint - Dynamic Programming] Use a memo table."
    cleaned = clean_text_for_speech(raw)
    assert "[code snippet omitted for audio]" in cleaned
    assert "```" not in cleaned
    assert "Hint: Use a memo table." in cleaned

@pytest.mark.asyncio
async def test_get_voices(client: httpx.AsyncClient):
    response = await client.get("/api/v1/audio/voices")
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert len(data["voices"]) >= 5
    assert data["default_voice"] == "en-US-ChristopherNeural"

@pytest.mark.asyncio
async def test_tts_endpoint(client: httpx.AsyncClient):
    response = await client.post(
        "/api/v1/audio/tts",
        json={
            "text": "Hello, welcome to your engineering interview.",
            "voice": "en-US-ChristopherNeural"
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert len(response.content) > 1000

@pytest.mark.asyncio
async def test_stt_endpoint(client: httpx.AsyncClient):
    # Synthesize a short audio clip
    audio_bytes = await AudioService.synthesize_speech("Hello world", voice="en-US-ChristopherNeural")
    assert len(audio_bytes) > 0

    files = {
        "audio": ("test.mp3", io.BytesIO(audio_bytes), "audio/mpeg")
    }
    response = await client.post("/api/v1/audio/stt", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert len(data["text"]) > 0
    assert "hello" in data["text"].lower()
