#!/usr/bin/env python3
"""
Nova 2.5 Sonic spike: bidirectional speech-to-speech with our engine deciding questions via a tool.

    pip install aws_sdk_bedrock_runtime awscrt   (Python >= 3.12, separate venv is fine)
    python scripts/spikes/nova_sonic_spike.py --wav candidate_answer.wav --out sonic_reply.wav

Flow: system prompt (persona) + tool `get_next_question` -> user audio (16 kHz PCM) -> Sonic transcribes,
calls the tool -> we return the next question (stand-in for InterviewService) -> Sonic speaks it.
Prints transcripts, tool calls and latency (end of user audio -> first assistant audio chunk).
"""
import argparse
import asyncio
import base64
import json
import os
import time
import uuid
import wave

from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
from smithy_http.aio.crt import AWSCRTHTTPClient
from aws_sdk_bedrock_runtime.models import BidirectionalInputPayloadPart, InvokeModelWithBidirectionalStreamInputChunk

MODEL_ID = os.environ.get("SONIC_MODEL_ID", "amazon.nova-2-5-sonic")
REGION = os.environ.get("AWS_REGION", "us-east-1")

SYSTEM = (
    "You are Priya, a Staff Engineer on the payments platform team, running a 20-minute technical interview. "
    "Speak naturally and briefly, like a real person on a call. Never praise or evaluate answers out loud. "
    "IMPORTANT: you do not choose interview questions yourself. After the candidate finishes speaking, call the "
    "tool get_next_question with a one-line summary of what they said, then ask exactly the question it returns, "
    "in your own natural words, optionally with a three-word acknowledgement first."
)
TOOL = {
    "toolSpec": {
        "name": "get_next_question",
        "description": "Returns the next interview question decided by the interview engine.",
        "inputSchema": {"json": json.dumps({
            "type": "object",
            "properties": {"candidate_summary": {"type": "string"}},
            "required": ["candidate_summary"],
        })},
    }
}


class Sonic:
    def __init__(self, voice: str):
        self.voice = voice
        self.prompt = str(uuid.uuid4())
        self.client = None
        self.stream = None
        self.audio_out = bytearray()
        self.events = []
        self.t_user_done = None
        self.t_first_audio = None

    async def send(self, event: dict):
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps({"event": event}).encode()))
        await self.stream.input_stream.send(chunk)

    async def open(self):
        # resolve() reads env vars, ~/.aws/config and ~/.aws/credentials (default credential chain).
        # Duplex event streams need the CRT transport (aiohttp can't do bidirectional streaming).
        self.client = AsyncBedrockRuntimeClient(config=await AsyncBedrockRuntimeConfig.resolve(
            region=REGION, transport=AWSCRTHTTPClient()))
        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=MODEL_ID))
        await self.send({"sessionStart": {"inferenceConfiguration": {"maxTokens": 1024, "topP": 0.9, "temperature": 0.7}}})
        await self.send({"promptStart": {
            "promptName": self.prompt,
            "textOutputConfiguration": {"mediaType": "text/plain"},
            "audioOutputConfiguration": {"mediaType": "audio/lpcm", "sampleRateHertz": 24000, "sampleSizeBits": 16,
                                         "channelCount": 1, "voiceId": self.voice, "encoding": "base64", "audioType": "SPEECH"},
            "toolUseOutputConfiguration": {"mediaType": "application/json"},
            "toolConfiguration": {"tools": [TOOL]},
        }})
        await self.text_block("SYSTEM", SYSTEM)

    async def text_block(self, role: str, text: str, interactive: bool = False):
        name = str(uuid.uuid4())
        await self.send({"contentStart": {"promptName": self.prompt, "contentName": name, "type": "TEXT",
                                          "interactive": interactive, "role": role,
                                          "textInputConfiguration": {"mediaType": "text/plain"}}})
        await self.send({"textInput": {"promptName": self.prompt, "contentName": name, "content": text}})
        await self.send({"contentEnd": {"promptName": self.prompt, "contentName": name}})

    async def audio_block(self, pcm16k: bytes):
        name = str(uuid.uuid4())
        await self.send({"contentStart": {"promptName": self.prompt, "contentName": name, "type": "AUDIO",
                                          "interactive": True, "role": "USER",
                                          "audioInputConfiguration": {"mediaType": "audio/lpcm", "sampleRateHertz": 16000,
                                                                      "sampleSizeBits": 16, "channelCount": 1,
                                                                      "audioType": "SPEECH", "encoding": "base64"}}})
        step = 3200  # 100 ms of 16 kHz mono 16-bit, streamed in real time like a mic
        for i in range(0, len(pcm16k), step):
            await self.send({"audioInput": {"promptName": self.prompt, "contentName": name,
                                            "content": base64.b64encode(pcm16k[i:i + step]).decode()}})
            await asyncio.sleep(0.1)
        # Trailing silence lets Sonic's turn detection fire.
        silence = b"\x00" * step
        for _ in range(15):
            await self.send({"audioInput": {"promptName": self.prompt, "contentName": name,
                                            "content": base64.b64encode(silence).decode()}})
            await asyncio.sleep(0.1)
        self.t_user_done = time.monotonic()
        return name

    async def tool_result(self, tool_use_id: str, result: dict):
        name = str(uuid.uuid4())
        await self.send({"contentStart": {"promptName": self.prompt, "contentName": name, "interactive": False,
                                          "type": "TOOL", "role": "TOOL",
                                          "toolResultInputConfiguration": {"toolUseId": tool_use_id, "type": "TEXT",
                                                                           "textInputConfiguration": {"mediaType": "text/plain"}}}})
        await self.send({"toolResult": {"promptName": self.prompt, "contentName": name, "content": json.dumps(result)}})
        await self.send({"contentEnd": {"promptName": self.prompt, "contentName": name}})

    async def close(self):
        await self.send({"promptEnd": {"promptName": self.prompt}})
        await self.send({"sessionEnd": {}})
        await self.stream.input_stream.close()

    async def read(self, done: asyncio.Event, next_question: str):
        _, output = await self.stream.await_output()
        role = None
        while not done.is_set():
            try:
                result = await asyncio.wait_for(output.receive(), timeout=25)
            except asyncio.TimeoutError:
                print("  [no output for 25s]")
                break
            if result is None:
                break
            data = json.loads(result.value.bytes_.decode())
            ev = data.get("event", {})
            kind = next(iter(ev), None)
            if kind == "contentStart":
                role = ev["contentStart"].get("role")
            elif kind == "textOutput":
                print(f"  [{ev['textOutput'].get('role', role)}] {ev['textOutput']['content']}")
                self.events.append(("text", ev["textOutput"].get("role", role), ev["textOutput"]["content"]))
            elif kind == "audioOutput":
                if self.t_first_audio is None and self.t_user_done is not None:
                    self.t_first_audio = time.monotonic()
                self.audio_out.extend(base64.b64decode(ev["audioOutput"]["content"]))
            elif kind == "toolUse":
                tu = ev["toolUse"]
                print(f"  [TOOL CALL] {tu['toolName']} {tu.get('content')}")
                self.events.append(("tool", tu["toolName"], tu.get("content")))
                await self.tool_result(tu["toolUseId"], {"question": next_question})
            elif kind == "completionEnd":
                done.set()
            elif kind not in ("completionStart", "contentEnd", "usageEvent"):
                print(f"  [{kind}] {str(ev)[:200]}")


def read_wav_16k(path: str) -> bytes:
    with wave.open(path, "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2, "need 16 kHz mono 16-bit"
        return w.readframes(w.getnframes())


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out", default="sonic_reply.wav")
    ap.add_argument("--voice", default="matthew")
    ap.add_argument("--question", default="You said Redis made it ten times faster. How did you actually measure that?")
    args = ap.parse_args()

    s = Sonic(args.voice)
    t0 = time.monotonic()
    await s.open()
    print(f"session open in {time.monotonic() - t0:.2f}s (model {MODEL_ID}, voice {args.voice})")
    done = asyncio.Event()
    reader = asyncio.create_task(s.read(done, args.question))
    await s.audio_block(read_wav_16k(args.wav))
    try:
        await asyncio.wait_for(done.wait(), timeout=40)
    except asyncio.TimeoutError:
        pass
    await asyncio.sleep(1.5)
    await s.close()
    reader.cancel()

    with wave.open(args.out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(bytes(s.audio_out))
    lat = (s.t_first_audio - s.t_user_done) if (s.t_first_audio and s.t_user_done) else None
    print(json.dumps({
        "assistant_audio_seconds": round(len(s.audio_out) / 48000, 2),
        "latency_end_of_speech_to_first_audio_s": round(lat, 2) if lat else None,
        "tool_calls": [e for e in s.events if e[0] == "tool"],
        "out": args.out,
    }, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
