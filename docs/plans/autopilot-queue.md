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
- [~] 3a. Spike in `scripts/spikes/nova_sonic_spike.py`: open a bidirectional stream to
      `amazon.nova-2-5-sonic` (us-east-1) with the default credential chain; send a system prompt
      + text turn; receive audio + transcript; demonstrate a tool call round-trip. Record findings
      (SDK, event schema, voices, latency) in `docs/product/nova-sonic-notes.md`.
- [ ] 3b. ADR 0025: platform-provided voice (not BYOC), least-privilege IAM role for prod, per-user
      voice-minute quota, audio never stored, Sonic speaks; our engine decides questions via tool.
- [ ] 3c. Backend: `/api/v1/voice/ws/{interview_id}` WebSocket relay (auth, per-user quota,
      interview ownership), Bedrock stream manager, `get_next_question` tool → existing
      `InterviewService.send_message`, transcripts persisted as normal messages.
- [ ] 3d. Frontend: AudioWorklet mic capture (16 kHz PCM), streamed playback (24 kHz), barge-in,
      live captions, "Live voice" toggle with fallback to current push-to-talk.
- [ ] 3e. STT upgrade for push-to-talk fallback: Voxtral (Bedrock) or Transcribe with tech-term
      vocabulary; benchmark accuracy vs faster-whisper base.en on the fixture WAVs.
- [ ] 3f. TTS fallback upgrade: Polly generative voices (Matthew/Ruth/Stephen, en-IN Kajal/Arjun/
      Kiara) when platform voice is enabled; honest availability flags.

### 4. Product features from the 2026-11-05 recommendations
- [ ] 4a. Self-awareness index: track self-vs-AI rubric gap per dimension over time (from existing
      comparisons); API + dashboard card ("You overrate system design by 1.8, down from 3.2").
- [ ] 4b. Answer replay diff: on a retest, show old vs new answer to the same weakness side by side
      with rubric score, evidence quotes and what changed; API + UI on the evaluation page.
- [ ] 4c. Delivery analytics from voice (no audio stored): filler words, hedging, words/min, long
      pauses, time-to-first-point from STT word timestamps; persisted per answer; shown in evaluation.
- [ ] 4d. AI-coding flagship: verification metric from editor telemetry (ran tests after AI reply?
      pasted vs edited?), prompt/edit/test timeline replay, project template so new projects are
      cheap; add 2 more projects.
- [ ] 4e. Evaluator credibility: "dispute this finding" with transcript evidence (re-judged, logged),
      visible evaluator confidence; evaluator consistency check (two runs, flag divergence).
- [ ] 4f. Docker executor project mode (out-of-process harness) so project runs work in production.

### 6. Code comprehension round (USP, Google-level)
- [ ] 6a. New interview category `code_comprehension`: candidate gets an unfamiliar, realistic
      multi-file snippet (concurrency, caching, parsers, distributed retries, ...) and must explain
      it, trace outputs for given inputs, find the planted bug(s), predict behaviour at scale and
      propose a review comment. Curated bank of >= 8 Google-level items with hidden answer keys,
      bug locations and grading rubric; difficulty tiers.
- [ ] 6b. Grounded grading: answers checked against the answer key (bug line, traced output,
      complexity) deterministically where possible, LLM judge for explanations with evidence quotes;
      interviewer follows up like a reviewer ("which line?", "what happens if two threads...").
- [ ] 6c. UI: read-only code viewer with file tabs, line numbers, click-to-reference lines in the
      answer, timer; results page with per-question correctness and the reveal.
- [ ] 6d. Evals: add comprehension personas to `scripts/evals/interview_eval.py`.

### 7. Landing page & UI/UX polish
- [ ] 7a. Public landing page at `/` for signed-out visitors (dashboard stays for signed-in):
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
