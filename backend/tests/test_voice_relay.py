"""Live voice relay tests with a fake Sonic session (no AWS calls)."""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.voice import relay as relay_mod
from backend.app.voice.sonic import SonicEvent


class FakeWS:
    def __init__(self, incoming):
        self.incoming = asyncio.Queue()
        for m in incoming:
            self.incoming.put_nowait(m)
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)

    async def receive_json(self):
        return await self.incoming.get()


class FakeSession:
    instances = []

    def __init__(self, voice=None):
        self.voice = voice or "matthew"
        self.events_q = asyncio.Queue()
        self.tool_results = []
        self.audio_chunks = 0
        self.opened = None
        FakeSession.instances.append(self)

    async def open(self, system_prompt, opening_line):
        self.opened = (system_prompt, opening_line)
        # Candidate speaks; Sonic's eager endpointing calls the tool before the transcript is complete.
        for ev in [SonicEvent("speech_start", role="user"),
                   SonicEvent("text", role="user", text="I built an order service"),
                   SonicEvent("tool_use", tool_use_id="t1", tool_name="get_next_question", tool_input={}),
                   SonicEvent("text", role="user", text="in FastAPI with Postgres."),
                   SonicEvent("speech_end", role="user")]:
            self.events_q.put_nowait(ev)

    async def send_audio(self, b64):
        self.audio_chunks += 1

    async def send_tool_result(self, tool_use_id, result):
        self.tool_results.append((tool_use_id, result))
        self.events_q.put_nowait(SonicEvent("text", role="assistant", text="Okay. " + result["say"], final=True))
        self.events_q.put_nowait(SonicEvent("audio", role="assistant", audio_b64="AAAA"))
        self.events_q.put_nowait(SonicEvent("turn_end"))

    async def events(self):
        while True:
            yield await self.events_q.get()

    async def close(self):
        pass


def _interview():
    msg = SimpleNamespace(role="assistant", content="Hi, I'm Priya. Tell me about something you built.", kind="question")
    return SimpleNamespace(id="iv1", category="technical", target_duration_minutes=20, messages=[msg])


PERSONA = {"name": "Priya", "title": "Staff Engineer", "team": "payments"}


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    monkeypatch.setattr(relay_mod, "SESSION_FACTORY", FakeSession)
    monkeypatch.setattr(relay_mod, "SETTLE_SECONDS", 0.2)
    relay_mod._ACTIVE_USERS.clear()
    relay_mod._USAGE_SECONDS.clear()
    FakeSession.instances.clear()


@pytest.mark.asyncio
async def test_turn_waits_for_full_transcript_and_goes_through_engine():
    seen = []

    async def send_message(transcript, delivery=None):
        seen.append(transcript)
        return SimpleNamespace(id="m2", content="How did you size the connection pool?", kind="question")

    ws = FakeWS([{"type": "audio", "data": "AAAA"}])
    relay = relay_mod.VoiceRelay(ws, "u1", _interview(), PERSONA, send_message)
    task = asyncio.create_task(relay.run())
    for _ in range(50):
        await asyncio.sleep(0.05)
        if any(p["type"] == "turn" for p in ws.sent):
            break
    await ws.incoming.put({"type": "stop"})
    await asyncio.wait_for(task, timeout=3)

    assert seen == ["I built an order service in FastAPI with Postgres."]  # not the partial transcript
    types = [p["type"] for p in ws.sent]
    assert types[0] == "ready"
    assert "interrupt" in types and "turn" in types and "audio" in types
    session = FakeSession.instances[0]
    assert session.tool_results[0][1] == {"say": "How did you size the connection pool?", "end_call": False}
    system_prompt, opening = session.opened
    assert "never decide interview questions" in system_prompt
    assert opening.startswith("Hi, I'm Priya")
    assert "u1" not in relay_mod._ACTIVE_USERS


@pytest.mark.asyncio
async def test_wrapup_ends_the_call():
    async def send_message(transcript, delivery=None):
        return SimpleNamespace(id="m9", content="Thanks for your time today. You'll hear back soon.", kind="wrapup")

    ws = FakeWS([])
    relay = relay_mod.VoiceRelay(ws, "u2", _interview(), PERSONA, send_message)
    await asyncio.wait_for(relay.run(), timeout=5)
    assert ws.sent[-1]["type"] == "completed"
    assert FakeSession.instances[0].tool_results[0][1]["end_call"] is True


@pytest.mark.asyncio
async def test_quota_and_single_session_guards(monkeypatch):
    async def send_message(t, delivery=None):
        raise AssertionError("should not be called")

    monkeypatch.setattr(settings, "VOICE_DAILY_MINUTES", 0)
    ws = FakeWS([])
    await relay_mod.VoiceRelay(ws, "u3", _interview(), PERSONA, send_message).run()
    assert ws.sent[0]["code"] == "VOICE_QUOTA_EXCEEDED"
    assert not FakeSession.instances[0].opened

    monkeypatch.setattr(settings, "VOICE_DAILY_MINUTES", 60)
    relay_mod._ACTIVE_USERS["u4"] = 1.0
    ws = FakeWS([])
    await relay_mod.VoiceRelay(ws, "u4", _interview(), PERSONA, send_message).run()
    assert ws.sent[0]["code"] == "VOICE_SESSION_ACTIVE"


def test_speakable_keeps_problem_statements_on_screen():
    text = "Noted. Now let's start today's session. Here is your question:\n\n### Two Sum\n\n```\n1 2\n```"
    said = relay_mod.speakable(text)
    assert "Two Sum" not in said and "on your screen" in said
    assert relay_mod.speakable("How is O(N^2) different?") == "How is O of N squared different?"


def test_ws_rejects_bad_token_and_disabled(monkeypatch):
    from backend.app.main import app
    client = TestClient(app)
    with client.websocket_connect("/api/v1/voice/ws/some-id") as ws:
        ws.send_json({"type": "auth", "token": "not-a-jwt"})
        assert ws.receive_json()["code"] == "AUTH_REQUIRED"
    monkeypatch.setattr(settings, "VOICE_LIVE_ENABLED", False)
    with client.websocket_connect("/api/v1/voice/ws/some-id") as ws:
        assert ws.receive_json()["code"] == "VOICE_DISABLED"


@pytest.mark.asyncio
async def test_duplicate_tool_call_for_same_utterance_is_silent():
    async def send_message(transcript, delivery=None):
        return SimpleNamespace(id="m3", content="Why Postgres over MySQL here?", kind="question")

    class DoubleCall(FakeSession):
        async def open(self, system_prompt, opening_line):
            await super().open(system_prompt, opening_line)
            self.events_q.put_nowait(SonicEvent("tool_use", tool_use_id="t2", tool_name="get_next_question", tool_input={}))
            self.events_q.put_nowait(SonicEvent("text", role="assistant", text='{ "interrupted" : true }', final=True))

    relay_mod.SESSION_FACTORY = DoubleCall
    ws = FakeWS([])
    relay = relay_mod.VoiceRelay(ws, "u5", _interview(), PERSONA, send_message)
    task = asyncio.create_task(relay.run())
    await asyncio.sleep(1.0)
    await ws.incoming.put({"type": "stop"})
    await asyncio.wait_for(task, timeout=3)
    results = dict(FakeSession.instances[0].tool_results)
    assert results["t1"]["say"] == "Why Postgres over MySQL here?" or results["t2"]["say"] == "Why Postgres over MySQL here?"
    assert "" in (results["t1"]["say"], results["t2"]["say"])
    assert not any("interrupted" in p.get("text", "") for p in ws.sent)
