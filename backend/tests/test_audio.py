import io
import uuid
import pytest
import httpx
from backend.app.audio.service import clean_text_for_speech, AudioService

@pytest.mark.asyncio
async def test_clean_text_for_speech():
    raw = "Here is the plan:\n```python\nprint('hello')\n```\n[Level 1 Hint - Dynamic Programming] Use a memo table."
    cleaned = clean_text_for_speech(raw)
    assert "(code shown on screen)" in cleaned
    assert "```" not in cleaned
    assert "Level 1 hint: Use a memo table." in cleaned


def test_clean_text_keeps_technical_meaning():
    cleaned = clean_text_for_speech("Lookups are O(1), total O(N^2), and the loop runs while a > b in two_sum. ### Done **now**")
    assert "O of 1" in cleaned
    assert "O of N squared" in cleaned
    assert "a greater than b" in cleaned
    assert "two sum" in cleaned
    assert "#" not in cleaned and "*" not in cleaned

async def _auth_headers(client: httpx.AsyncClient) -> dict:
    email = f"audio_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_audio_endpoints_require_auth(client: httpx.AsyncClient):
    r = await client.post("/api/v1/audio/tts", json={"text": "free proxy?"})
    assert r.status_code == 401
    r = await client.post("/api/v1/audio/stt", files={"audio": ("a.wav", io.BytesIO(b"x" * 100), "audio/wav")})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stt_rejects_oversized_upload(client: httpx.AsyncClient, monkeypatch):
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "AUDIO_MAX_UPLOAD_BYTES", 1024)
    headers = await _auth_headers(client)
    r = await client.post("/api/v1/audio/stt", headers=headers, files={"audio": ("a.wav", io.BytesIO(b"x" * 4096), "audio/wav")})
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_stt_invalid_audio_is_400_without_internal_paths(client: httpx.AsyncClient):
    headers = await _auth_headers(client)
    r = await client.post("/api/v1/audio/stt", headers=headers, files={"audio": ("a.webm", io.BytesIO(b"\x00\x01garbage" * 300), "audio/webm")})
    assert r.status_code == 400
    assert "/tmp" not in r.text


@pytest.mark.asyncio
async def test_cloud_voices_marked_unavailable_without_credentials(client: httpx.AsyncClient, monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    headers = await _auth_headers(client)
    voices = (await client.get("/api/v1/audio/voices", headers=headers)).json()["voices"]
    polly = [v for v in voices if v["provider"] == "aws-polly"]
    edge = [v for v in voices if v["provider"] == "edge-azure"]
    assert polly and all(v["available"] is False for v in polly)
    assert edge and all(v["available"] is True for v in edge)


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
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/audio/tts",
        json={
            "text": "Hello, welcome to your engineering interview.",
            "voice": "en-US-ChristopherNeural"
        },
        headers=headers,
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
    headers = await _auth_headers(client)
    response = await client.post("/api/v1/audio/stt", files=files, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert len(data["text"]) > 0
    assert "hello" in data["text"].lower()
