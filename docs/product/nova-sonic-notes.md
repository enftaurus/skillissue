# Nova 2.5 Sonic: spike findings (2026-11-06)

Spike: `scripts/spikes/nova_sonic_spike.py`.

## Setup that works
- Model `amazon.nova-2-5-sonic`, `us-east-1`. The account also lists `amazon.nova-2-sonic-v1:0`.
- SDK: `aws_sdk_bedrock_runtime` 0.12 plus `awscrt` (Python ≥ 3.12). boto3 cannot do this operation.
- Config: `await AsyncBedrockRuntimeConfig.resolve(region=..., transport=AWSCRTHTTPClient())`.
  - The config can't be constructed directly; `resolve()` reads env vars and `~/.aws/{config,credentials}`.
  - The default aiohttp transport raises `UnsupportedTransportError` for duplex streams, so the CRT transport is required.
- Events (JSON inside `BidirectionalInputPayloadPart.bytes_`), in order:
  1. `sessionStart`
  2. `promptStart`: text, audio and tool output config, `voiceId`, `toolConfiguration`
  3. SYSTEM `contentStart` / `textInput` / `contentEnd`
  4. USER `contentStart` (AUDIO, interactive), then `audioInput` chunks (base64 16 kHz mono s16 LPCM, 100 ms each)
  5. `toolResult` blocks (TOOL role) answering `toolUse`
  6. `promptEnd`, `sessionEnd`
- Output events:
  - `completionStart`, `contentStart` (role)
  - `textOutput` (USER transcript and ASSISTANT text; assistant text arrives twice: a speculative stage, then the final one)
  - `audioOutput` (base64 24 kHz s16 LPCM)
  - `toolUse` (`toolName`, `toolUseId`, `content` JSON)
  - `userSpeechStart` / `userSpeechEnd` with audio offsets
  - `contentEnd`, `completionEnd`, `usageEvent`

## Results
- Spoken candidate answer → Sonic transcript: "i think redis made it like ten x faster i guess". It got "Redis" right; our faster-whisper base.en heard "Rita's".
- **The tool round-trip works.** Sonic called `get_next_question`, then spoke our engine's question naturally:
  "Got it. You mentioned Redis made it ten times faster. How did you actually measure that?" (5.2 s of audio).
- **Latency:** the first assistant audio arrived while we were still streaming trailing silence, i.e. well under 1.5 s after end of speech. Measure precisely from `userSpeechEnd` in the real relay.

## Issues to handle in the relay (3c)
- **Turn detection is eager.** It fired on the pause after "I don't really know." and called the tool on a partial answer. Options: buffer until `userSpeechEnd` plus about 700 ms before answering the tool; merge consecutive user turns; tune endpointing if the model exposes it.
- **De-duplicate assistant text:** keep only the final generation stage for captions and transcripts.
- **Sessions are long-lived streams:** one per live interview, with a hard cap (e.g. 30 min) and reconnect logic.
- **Barge-in:** when `userSpeechStart` arrives during assistant audio, the client must stop playback immediately.

## Hybrid contract (our engine stays in charge)
- The system prompt carries the interviewer persona. Sonic is told it never picks questions.
- Tool `get_next_question(candidate_summary)`: the relay persists the *transcribed* user turn through
  `InterviewService.send_message` (same policy, budget, kinds, evaluation) and returns the engine's reply text.
  Sonic speaks it, optionally with a short acknowledgement.
- The wrap-up, repeat/clarify and closing phases all come from the engine, unchanged.
