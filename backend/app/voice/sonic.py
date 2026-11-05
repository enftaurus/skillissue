"""
Thin async wrapper over a Nova Sonic bidirectional stream (see docs/product/nova-sonic-notes.md).

The SDK is imported lazily so the API boots without it (offline dev, Security Invariant #4).
Credentials come only from the server's default AWS chain and never reach the browser.
"""
import base64
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from backend.app.core.config import settings


class VoiceUnavailable(Exception):
    """Live voice can't be used (SDK missing, no credentials, model access denied)."""


@dataclass
class SonicEvent:
    kind: str  # 'audio' | 'text' | 'tool_use' | 'speech_start' | 'speech_end' | 'turn_end' | 'error'
    role: Optional[str] = None
    text: str = ""
    audio_b64: str = ""
    tool_use_id: str = ""
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    final: bool = True


TOOL_SPEC = {
    "toolSpec": {
        "name": "get_next_question",
        "description": "Records what the candidate just said and returns exactly what the interviewer must say next.",
        "inputSchema": {"json": json.dumps({
            "type": "object",
            "properties": {"candidate_summary": {"type": "string", "description": "One line: what the candidate said."}},
            "required": ["candidate_summary"],
        })},
    }
}


class SonicSession:
    """One live interview = one bidirectional stream."""

    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or settings.SONIC_DEFAULT_VOICE
        self.prompt_name = str(uuid.uuid4())
        self.audio_content = str(uuid.uuid4())
        self._stream = None
        self._stage: Dict[str, bool] = {}
        self._role: Optional[str] = None
        self._final = True

    async def open(self, system_prompt: str, opening_line: str) -> None:
        try:
            from aws_sdk_bedrock_runtime.client import (
                AsyncBedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput,
            )
            from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
            from smithy_http.aio.crt import AWSCRTHTTPClient
        except ImportError as e:  # pragma: no cover - depends on optional deps
            raise VoiceUnavailable("Live voice SDK is not installed on this server.") from e
        try:
            config = await AsyncBedrockRuntimeConfig.resolve(region=settings.SONIC_REGION, transport=AWSCRTHTTPClient())
            client = AsyncBedrockRuntimeClient(config=config)
            self._stream = await client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=settings.SONIC_MODEL_ID))
        except Exception as e:
            raise VoiceUnavailable(f"Could not open a live voice session ({type(e).__name__}).") from e

        await self._send({"sessionStart": {"inferenceConfiguration": {"maxTokens": 1024, "topP": 0.9, "temperature": 0.6}}})
        await self._send({"promptStart": {
            "promptName": self.prompt_name,
            "textOutputConfiguration": {"mediaType": "text/plain"},
            "audioOutputConfiguration": {"mediaType": "audio/lpcm", "sampleRateHertz": 24000, "sampleSizeBits": 16,
                                         "channelCount": 1, "voiceId": self.voice, "encoding": "base64",
                                         "audioType": "SPEECH"},
            "toolUseOutputConfiguration": {"mediaType": "application/json"},
            "toolConfiguration": {"tools": [TOOL_SPEC]},
        }})
        await self._text_block("SYSTEM", system_prompt)
        # Kick off the call: the interviewer speaks the engine's current question first.
        await self._text_block("USER", f"(The candidate has joined the call. Say your opening now: {opening_line})",
                               interactive=True)
        await self._send({"contentStart": {
            "promptName": self.prompt_name, "contentName": self.audio_content, "type": "AUDIO", "interactive": True,
            "role": "USER",
            "audioInputConfiguration": {"mediaType": "audio/lpcm", "sampleRateHertz": 16000, "sampleSizeBits": 16,
                                        "channelCount": 1, "audioType": "SPEECH", "encoding": "base64"},
        }})

    async def send_audio(self, pcm16k_b64: str) -> None:
        await self._send({"audioInput": {"promptName": self.prompt_name, "contentName": self.audio_content,
                                         "content": pcm16k_b64}})

    async def send_tool_result(self, tool_use_id: str, result: Dict[str, Any]) -> None:
        name = str(uuid.uuid4())
        await self._send({"contentStart": {
            "promptName": self.prompt_name, "contentName": name, "interactive": False, "type": "TOOL", "role": "TOOL",
            "toolResultInputConfiguration": {"toolUseId": tool_use_id, "type": "TEXT",
                                             "textInputConfiguration": {"mediaType": "text/plain"}},
        }})
        await self._send({"toolResult": {"promptName": self.prompt_name, "contentName": name, "content": json.dumps(result)}})
        await self._send({"contentEnd": {"promptName": self.prompt_name, "contentName": name}})

    async def events(self) -> AsyncIterator[SonicEvent]:
        _, output = await self._stream.await_output()
        while True:
            result = await output.receive()
            if result is None:
                return
            try:
                data = json.loads(result.value.bytes_.decode())
            except Exception:
                continue
            ev = data.get("event", {})
            kind = next(iter(ev), None)
            body = ev.get(kind, {}) if kind else {}
            if kind == "contentStart":
                self._role = body.get("role")
                stage = ""
                try:
                    stage = json.loads(body.get("additionalModelFields") or "{}").get("generationStage", "")
                except Exception:
                    pass
                self._final = stage != "SPECULATIVE"
            elif kind == "textOutput":
                yield SonicEvent("text", role=(body.get("role") or self._role or "").lower(), text=body.get("content", ""),
                                 final=self._final)
            elif kind == "audioOutput":
                yield SonicEvent("audio", role="assistant", audio_b64=body.get("content", ""))
            elif kind == "toolUse":
                try:
                    tool_input = json.loads(body.get("content") or "{}")
                except Exception:
                    tool_input = {}
                yield SonicEvent("tool_use", tool_use_id=body.get("toolUseId", ""), tool_name=body.get("toolName", ""),
                                 tool_input=tool_input)
            elif kind == "userSpeechStart":
                yield SonicEvent("speech_start", role="user")
            elif kind == "userSpeechEnd":
                yield SonicEvent("speech_end", role="user")
            elif kind == "completionEnd":
                yield SonicEvent("turn_end")

    async def close(self) -> None:
        if self._stream is None:
            return
        try:
            await self._send({"contentEnd": {"promptName": self.prompt_name, "contentName": self.audio_content}})
            await self._send({"promptEnd": {"promptName": self.prompt_name}})
            await self._send({"sessionEnd": {}})
            await self._stream.input_stream.close()
        except Exception:
            pass
        self._stream = None

    async def _text_block(self, role: str, text: str, interactive: bool = False) -> None:
        name = str(uuid.uuid4())
        await self._send({"contentStart": {"promptName": self.prompt_name, "contentName": name, "type": "TEXT",
                                           "interactive": interactive, "role": role,
                                           "textInputConfiguration": {"mediaType": "text/plain"}}})
        await self._send({"textInput": {"promptName": self.prompt_name, "contentName": name, "content": text}})
        await self._send({"contentEnd": {"promptName": self.prompt_name, "contentName": name}})

    async def _send(self, event: Dict[str, Any]) -> None:
        from aws_sdk_bedrock_runtime.models import BidirectionalInputPayloadPart, InvokeModelWithBidirectionalStreamInputChunk
        await self._stream.input_stream.send(InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps({"event": event}).encode())))
