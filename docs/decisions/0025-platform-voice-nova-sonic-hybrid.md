# 0025. Platform-Provided Voice: Nova 2.5 Sonic Hybrid with Engine-Driven Questions

- **Status**: Accepted (prototype); production rollout pending the IAM work below
- **Date**: 2026-11-06
- **Deciders**: Product owner, Interview Engine
- **Supersedes (partially)**: 0019 for the live voice path; push-to-talk TTS/STT stays as the fallback

## Context
Push-to-talk (browser recording → faster-whisper → text → Edge/Polly TTS) works, but it feels turn-based: 1–3 s gaps, no barge-in, accent errors ("Redis" → "Rita's"). The product owner wants interviews that feel like real calls, with Skill Issue providing voice itself (not BYOC). The account has Nova 2.5 Sonic (speech-to-speech) on Bedrock, and the spike proved bidirectional streaming plus a tool round-trip (`docs/product/nova-sonic-notes.md`).

## Decision
1. **Live voice mode** uses Nova 2.5 Sonic over a backend WebSocket relay: browser ⇄ `/api/v1/voice/ws/{interview_id}` ⇄ Bedrock bidirectional stream.
2. **The engine stays in charge.** Sonic is instructed never to choose questions. Every candidate turn goes through the `get_next_question` tool, which calls `InterviewService.send_message` with the transcript, so persona, policy, budget, message kinds, closing phase and evaluation are identical to text mode. Sonic only speaks.
3. **Platform credentials, not BYOC, for voice.**
   - Production uses a dedicated IAM role with least privilege: `bedrock:InvokeModelWithBidirectionalStream` on the Sonic model ARN, plus `polly:SynthesizeSpeech` and `transcribe:StartStreamTranscription` for fallbacks.
   - **Root keys must never be used.**
   - Credentials come only from the default chain on the server and never reach the client.
4. **Cost and abuse controls:** a per-user daily voice-minute quota, a session cap (30 min), one live session per user, auth plus interview ownership checked on connect.
5. **Privacy:** audio is streamed, never stored. Only transcripts are persisted, as normal interview messages.
6. **Fallback:** if Sonic is unavailable or the quota is exhausted, the UI falls back to push-to-talk.

## Consequences
- New dependency set (`aws_sdk_bedrock_runtime`, `awscrt`, Python ≥ 3.12) for the voice relay. The relay's Bedrock client is created lazily, so the app still boots offline (Security Invariant #4).
- Long-lived WebSockets need sticky routing and graceful shutdown in production.
- Spend scales with voice minutes; quotas are mandatory before public launch.
