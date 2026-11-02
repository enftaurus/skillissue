# 19. Cross-Browser Cloud Neural Audio Pipeline (TTS & STT)

Date: 2026-11-02
Status: accepted

## Context

Candidate interview practice requires high-fidelity speech synthesis (TTS) for the AI interviewer and accurate speech-to-text (STT) for candidates speaking their responses.
Previously, the frontend relied solely on the browser's native Web Speech API (`window.speechSynthesis` and `window.webkitSpeechRecognition`).

In non-Chromium browsers—specifically **Mozilla Firefox** across Linux and Windows:
1. Firefox lacks an integrated remote neural speech synthesis cloud. Calling `speechSynthesis.speak()` delegates directly to the host operating system's local synthesizers (e.g. `espeak-ng` or legacy SAPI engines), producing robotic, scratchy, metallic audio with no prosody or clarity.
2. `webkitSpeechRecognition` is completely absent in Firefox. The Web Speech recognition API is disabled or non-functional, leaving Firefox users unable to record speech or see the microphone input button.

Candidates and engineering students preparing for technical interviews require clear, studio-grade voices across all platforms without robotic artifacts or browser incompatibilities.

## Decision

We replace the client-only Web Speech dependency with a unified, cross-browser Cloud Neural Audio architecture:

1. **Backend Text-to-Speech (`POST /api/v1/audio/tts`)**:
   - Accepts `{ text: string, voice?: string, rate?: string, pitch?: string }` and streams standard `audio/mpeg` binary audio.
   - Cleans markdown fences, brackets, and code blocks to optimize spoken prosody.
   - Tiered Provider Support:
     - Tier 1: Azure OpenAI Audio (`tts-1` / `tts-1-hd`) when configured by the candidate.
     - Tier 2: AWS Polly Neural (`Engine="neural"`, `VoiceId="Joanna"|"Matthew"|"Kajal"`) when AWS BYOC credentials are configured.
     - Tier 3: Vaani.dev / VaaniStack API (`https://api.vaanistack.com/v1/tts`) when configured.
     - Tier 4 (Universal Studio Default): Microsoft Azure Edge Neural Speech (`edge-tts`), streaming studio-clarity neural models (`en-US-ChristopherNeural`, `en-US-JennyNeural`, `en-IN-NeerjaNeural`, `en-IN-PrabhatNeural`, `en-GB-RyanNeural`) at zero cost with zero credentials needed.
   - The frontend plays standard HTML5 `<audio>` blobs (`URL.createObjectURL(blob)`), ensuring 100% audio fidelity and studio clarity in Firefox, Chrome, Safari, and Edge.

2. **Backend Speech-to-Text (`POST /api/v1/audio/stt`)**:
   - Accepts `multipart/form-data` audio file (`audio/webm`, `audio/wav`, `audio/mp4`, `audio/ogg`).
   - Prioritizes user's Azure Whisper or Vaani STT endpoints, with high-speed local `faster-whisper` (`tiny.en`, `int8`, CPU) fallback delivering sub-200ms transcriptions without internet dependency.

3. **Frontend Universal MediaRecorder & Audio Visualizer**:
   - `SpeechHandler` uses standard `navigator.mediaDevices.getUserMedia` and `MediaRecorder`, supported across all browsers.
   - Connected to Web Audio API `AudioContext` and `AnalyserNode` to drive real-time equalizer wave bars while the candidate speaks.
   - Candidate persona selector allows switching voices (`Christopher`, `Jenny`, `Neerja`, `Prabhat`, `Ryan`) with persistence in `localStorage`.

## Consequences

- **Clarity & Realism**: Eliminates robotic local `espeak-ng` audio in Firefox; both interviewer speech and candidate transcription achieve human-level fidelity.
- **Cross-Browser Parity**: Firefox, Chrome, Safari, and Edge have identical audio behavior and mic accessibility.
- **Security & Privacy**: Audio files are processed in ephemeral memory or wiped immediately after transcription; credentials are never exposed to browser bundles.
