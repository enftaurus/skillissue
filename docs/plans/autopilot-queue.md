# Autopilot Work Queue — Voice & Interview Realism

Branch: `autopilot/voice-realism` (based on `qa/audit-fixes-2026-11-05`).
The unattended runner (`~/.local/bin/skillissue-autopilot`, systemd timer 03:12 IST) picks the
**first unchecked item**, finishes it, runs the tests, commits, pushes this branch, then ticks the
box and adds a one-line note under "Log". Interactive sessions use the same queue.

Rules for every item: follow AGENTS.md; add/adjust tests; `pytest backend/tests` must pass
(ignore `test_byoc_end_to_end_live.py`); frontend `npx tsc --noEmit -p .` must pass when frontend
changes; never push anywhere except `autopilot/voice-realism`; never touch AWS IAM, credentials
or `.env`; keep live-LLM/voice spend small (short scripted runs only).

## Queue

### 1. Interview eval suite (real LLM)
- [x] 1a. `scripts/evals/interview_eval.py`: scripted candidates (clueless, overconfident-claims,
      strong, prompt-injector, rambler) × rounds (technical, behavioral, managerial, dsa) against
      the live API; save transcripts to `artifacts_e2e/evals/<timestamp>/`.
- [x] 1b. Deterministic checks per transcript: topic coverage, single question per turn, no praise
      phrases, no repeated questions, wrap-up honesty, turn budget respected.
- [x] 1c. LLM judge (evaluation model) scoring **realism vs AI slop** (1–5) with quoted evidence:
      sounds like a human senior interviewer, natural acknowledgements, references earlier
      answers, no generic filler. Output a markdown scorecard + JSON; record a baseline.

### 2. Interview realism (measure with the suite before/after)
- [x] 2a. Interviewer persona: name, role, team, company context; natural opener (small talk,
      agenda for the round), consistent voice across turns.
- [x] 2b. Realistic structure: intro → warm-up → core → deep dive → "any questions for me?" →
      close. Candidate questions answered in persona; not counted as answers.
- [x] 2c. Natural acknowledgements without praise ("Okay.", "Got it, so you…"), occasional
      callbacks to earlier answers, short thinking beats; ban list of slop phrases enforced in code.
- [x] 2d. Rambling handling: if an answer is very long and off-point, interviewer politely
      interrupts/redirects next turn.

### 3. Voice: Nova 2.5 Sonic hybrid (Bedrock) — see ADR 0025 once written
- [x] 3a. Spike in `scripts/spikes/nova_sonic_spike.py`: open a bidirectional stream to
      `amazon.nova-2-5-sonic` (us-east-1) with the default credential chain; send a system prompt
      + text turn; receive audio + transcript; demonstrate a tool call round-trip. Record findings
      (SDK, event schema, voices, latency) in `docs/product/nova-sonic-notes.md`.
- [x] 3b. ADR 0025: platform-provided voice (not BYOC), least-privilege IAM role for prod, per-user
      voice-minute quota, audio never stored, Sonic speaks; our engine decides questions via tool.
- [x] 3c. Backend: `/api/v1/voice/ws/{interview_id}` WebSocket relay (auth, per-user quota,
      interview ownership), Bedrock stream manager, `get_next_question` tool → existing
      `InterviewService.send_message`, transcripts persisted as normal messages.
- [x] 3d. Frontend: AudioWorklet mic capture (16 kHz PCM), streamed playback (24 kHz), barge-in,
      live captions, "Live voice" toggle with fallback to current push-to-talk.
- [x] 3e. STT upgrade for push-to-talk fallback: Voxtral (Bedrock) or Transcribe with tech-term
      vocabulary; benchmark accuracy vs faster-whisper base.en on the fixture WAVs.
- [ ] 3f. TTS fallback upgrade: Polly generative voices (Matthew/Ruth/Stephen, en-IN Kajal/Arjun/
      Kiara) when platform voice is enabled; honest availability flags.

### 4. Product features from the 2026-11-05 recommendations
- [x] 4a. Self-awareness index: track self-vs-AI rubric gap per dimension over time (from existing
      comparisons); API + dashboard card ("You overrate system design by 1.8, down from 3.2").
- [x] 4b. Answer replay diff: on a retest, show old vs new answer to the same weakness side by side
      with rubric score, evidence quotes and what changed; API + UI on the evaluation page.
- [x] 4c. Delivery analytics from voice (no audio stored): filler words, hedging, words/min, long
      pauses, time-to-first-point from STT word timestamps; persisted per answer; shown in evaluation.
- [x] 4d. AI-coding flagship: verification metric from editor telemetry (ran tests after AI reply?
      pasted vs edited?), prompt/edit/test timeline replay, project template so new projects are
      cheap; add 2 more projects.
- [x] 4e. Evaluator credibility: "dispute this finding" with transcript evidence (re-judged, logged),
      visible evaluator confidence; evaluator consistency check (two runs, flag divergence).
- [ ] 4f. (BLOCKED, needs product-owner decision, see Log) Docker executor project mode (out-of-process harness) so project runs work in production.

### 6. Code comprehension round (USP, Google-level)
- [x] 6a. New interview category `code_comprehension`: candidate gets an unfamiliar, realistic
      multi-file snippet (concurrency, caching, parsers, distributed retries, ...) and must explain
      it, trace outputs for given inputs, find the planted bug(s), predict behaviour at scale and
      propose a review comment. Curated bank of >= 8 Google-level items with hidden answer keys,
      bug locations and grading rubric; difficulty tiers.
- [x] 6b. Grounded grading: answers checked against the answer key (bug line, traced output,
      complexity) deterministically where possible, LLM judge for explanations with evidence quotes;
      interviewer follows up like a reviewer ("which line?", "what happens if two threads...").
- [x] 6c. UI: read-only code viewer with file tabs, line numbers, click-to-reference lines in the
      answer, timer; results page with per-question correctness and the reveal.
- [ ] 6d. Evals: add comprehension personas to `scripts/evals/interview_eval.py`.

### 7. Landing page & UI/UX polish
- [x] 7a. Public landing page at `/` for signed-out visitors (dashboard stays for signed-in):
      hero with the tagline, animated interview/feedback demo, USPs (real-interview realism,
      code comprehension, AI-assisted coding, evidence-based feedback), how-it-works loop, CTA.
      Light theme per AGENTS.md, tasteful motion (reduced-motion respected), mobile-first.
- [ ] 7b. App-wide polish pass: consistent spacing/typography, skeleton loaders, page transitions,
      empty states, accessible focus states.

### 5. Edge-case bug hunt (repeat after each feature batch)
- [ ] 5a. Probe every interview/evaluation/coding/projects/audio endpoint with edge cases (empty,
      huge, unicode/RTL, concurrent double-submit, other user's IDs, completed/expired sessions,
      provider down). Fix what breaks, add regression tests, log findings in the QA report.

## Log
- 2026-11-06 00:20 IST: queue created; branch cut from `qa/audit-fixes-2026-11-05`; autopilot timer installed (03:12 IST).
- 2026-11-06 00:25 IST: interactive session claimed item 1 ([~]).
- 2026-11-06 00:30 IST: eval suite done (scripts/evals/interview_eval.py). Baseline (10 runs): checks pass 100%; realism 3.11, adaptivity 3.33, no-slop 3.89, rigor 3.44. Weak: templated wrap-ups, ramblers not redirected, definitional questions for stuck candidates, boasts not challenged. Interactive session claimed item 2.
- 2026-11-06 00:55 IST: item 2 done. Persona + agenda opener, 'any questions for me?' closing phase (not counted), in-persona honest close, rambling interrupts, scenario-based simplification, one-time switch offer then early close, natural topic bridges, deeper follow-ups for strong answers, slop stripping; eval now simulates strong/overconfident/rambler candidates with an LLM. Eval (10 runs): realism 4.1, adaptivity 4.2, no-slop 4.5, rigor 4.1 (baseline 3.1/3.3/3.9/3.4). Weak spot: managerial/clueless adaptivity 2. Interactive session claimed 3a.
- 2026-11-06 01:05 IST: 3a spike works (Sonic transcribes, calls get_next_question, speaks our question; first audio <1.5 s; needs aws_sdk_bedrock_runtime + awscrt). Notes in docs/product/nova-sonic-notes.md. 3b ADR 0025 written. Interactive session claimed 3c.
- 2026-11-06 01:25 IST: 3c done. /api/v1/voice/ws/{id} relay (first-message auth, ownership/status checks, one session per user, daily quota, 30-min cap), turn settling + duplicate tool-call suppression for Sonic's eager endpointing, every turn through InterviewService.send_message. Live test: opener spoken, answer -> engine question spoken (3.5 s), turn persisted. Interactive session claimed 3d.
- 2026-11-06 01:35 IST: 3d done. Browser live voice: AudioWorklet 16 kHz capture, gapless 24 kHz playback with instant barge-in stop, captions, state + level UI, typing/push-to-talk paused during the call; Vite proxy ws enabled. Playwright (fake mic): call connected, 4 engine turns in 45 s.
- 2026-11-06 01:45 IST: interactive session claimed 6a-6c (code comprehension). Autopilot runner now waits while an interactive session is actively writing in this repo.
- 2026-11-06 02:10 IST: 6a-6c done. 9 Google-style items (TTL/LRU cache, token bucket, quota race, retry, keyset pagination, consistent hashing, async fan-out, closures/defaults, build order) x 3-4 questions; trace keys verified by execution in tests; deterministic trace/location/numeric grading + LLM judge with non-revealing reviewer follow-ups; /comprehension UI with clickable line refs, timer, reveal. Tailwind animations defined (were no-ops). Interactive session claimed 7a.
- 2026-11-06 02:20 IST: 7a done. Public landing at / for signed-out visitors (and /welcome): animated live-interview hero, rounds marquee, 4 USPs, interactive code-reading demo, loop, real-eval proof, CTA; scroll reveal, reduced motion, no h-scroll at 390 px; signed-in / still shows the dashboard; 401 redirect skips public pages.
- 2026-11-06 02:30 IST: 4a done. /api/v1/analytics/self-awareness (per-dimension self-vs-evidence gap, bias, trend, index over last 3 sessions, headline) + dashboard card.
- 2026-11-06 02:45 IST: 5a first pass: scripts/evals/edge_probe.py; fixed E1-E6 (see QA report Round 3), incl. 500 for every user without a provider. Re-run the probe after each feature batch (keep 5a unchecked for that).
- 2026-11-06 03:20 IST: 3e done. Benchmarked whisper base.en vs small.en vs Transcribe (see docs/product/nova-sonic-notes.md): kept base.en + prompt; Transcribe opt-in via STT_PROVIDER. Verified platform Polly voices live.
- 2026-11-06 03:35 IST: 4b done. GET /evaluations/retests/{id}/diff (original vs retest answer on the weakness, scores, quotes, rubric deltas, LLM what-changed summary with fallback) + 'Compare your answers' panel; retests now opened by the real interview engine in the original round's category.
- 2026-11-06 03:55 IST: 4c done. Delivery metrics (pace, fillers incl. comma-'like', hedges, long pauses, time-to-first-point) from whisper word timestamps (push-to-talk) and Sonic speech timing (live voice); stored per answer (migration 0018, numbers only, never scored); GET /interviews/{id}/delivery + 'How you sounded' card.
- 2026-11-06 04:15 IST: 4d done. make_project template + 2 projects (idempotent payments, webhook signatures) with server-side reference solutions verified in tests; project_events log (migration 0019); verification metrics (tests run after assistant replies) in submit analysis + flags; GET /projects/{id}/timeline. Fixed sandbox integrity check rejecting parametrized tests.
- 2026-11-06 04:40 IST: 4e done. Two parallel grading passes (divergence flagged + averaged), evidence verification (quote_verified flag; old code silently substituted unverified quotes), confidence level with reasons, evidence-backed disputes (verbatim quote required, +/-2 cap, 1 per dimension, max 3, logged; migration 0020) + UI.
- 2026-11-06 05:00 IST: 4f BLOCKED. Added executor /execute-project + API dispatch (used when the API has no bwrap and EXECUTOR_URL is set; runner shipped in the executor image). But bubblewrap inside the Docker executor can't mount /proc ('Operation not permitted'), which ALSO breaks the existing /execute path for every DSA run under compose. Fix needs either security_opt systempaths=unconfined on the executor, a runner without a private /proc, or gVisor; the auto-mode classifier (correctly) refused to loosen container security without the owner's say. Do not attempt again unattended.
