# 0022. Post-Code Explanation Checks, Editor Activity Telemetry & Recruiter Replay View

- **Status**: Accepted
- **Date**: 2026-11-04
- **Deciders**: Systems & Integrity Architecture Team
- **Consulted**: Security, Product, Enterprise Engineering

---

## Context

When candidates submit code in online assessments (OA) or coding practice, traditional platforms either attempt heavy-handed proctoring (webcams, screen recording, lockdown browsers) which generates student anxiety and false accusations, or blindly trust client-side score reports. Furthermore, with LLMs capable of generating code solutions instantly, code alone cannot prove computational understanding.

We need an evidence-based, human-centered integrity mechanism that:
1. Verifies authentic candidate understanding of submitted code via grounded follow-up cross-examination.
2. Captures non-invasive keystroke activity telemetry from the editor without logging raw sensitive characters.
3. Provides recruiters with a playback scrubber replay view and pure activity metrics.
4. Strictly adheres to Rule 3 (Integrity Policy): Signals flag for human review only and NEVER alter scores, pass/fail status, or rankings.

---

## Decisions

### 1. Post-Code Explanation Check (Cross-Examination)
- After submitting code for an OA or coding round, the system deterministically analyzes triviality (effective lines $\ge 8$, control-flow constructs).
- Trivial solutions cap confidence at `low` and ask fewer questions.
- Generates 3 follow-up questions (rationale, mutation, behaviour) with code references strictly grounded in actual code tokens.
- Collects candidate text or voice responses with per-question countdown enforcement (default 90s).
- Server-side LLM judge grades accuracy, consistency, and depth (0-4), citing verbatim evidence quotes ($\le 200$ chars).
- Normalizes server-side `explanation_consistency` (0.0 to 1.0). The LLM judge never decides final scores or verdicts.
- Emits review flag `EXPLANATION_MISMATCH` only in assessment mode if `confidence >= medium` and `consistency < 0.35`. In practice mode, returns coaching feedback only.

### 2. Editor Activity Telemetry
- Captures key categories (`printable`, `enter`, `tab`, `backspace_delete`, `arrow_navigation`, `shortcut` — never raw characters), document deltas (`range_offset`, `range_length`, `inserted_text`), cursor, selection, blur/focus, document visibility, and Monaco suggest completion (`source="suggest"`).
- Ingests in batches every 5s with monotonic sequence numbers (`seq`), rejecting replayed or out-of-order batches.
- Reconstructs document state from deltas and verifies against submitted code SHA-256 hash.
- Extracts 8 pure telemetry features: `typed_ratio`, `large_inserts`, `activity_density`, `growth_without_activity`, `revision_ratio`, `cadence` (burst CV), `read_then_type`, and `focus`.
- Minimum Evidence Gate: Requires $\ge 10$ effective lines, $\ge 180$s active time, and $\ge 200$ edit events; otherwise outputs `insufficient_data` and raises zero flags.
- Multi-Family Correlation: Single family triggers `low` confidence; $\ge 2$ independent families trigger `medium` confidence; never emits `high` confidence in this release.

### 3. Recruiter Replay View
- Read-only Monaco editor displaying reconstructed text at timestamp $t$.
- Interactive timeline scrubber with speed controls (1x to 8x).
- Visual activity density strip with color-coded markers for typing, large inserts/pastes, window blurs, and long pauses ($\ge 60$s) with click-to-jump.
- Side panel detailing features, grounded review flags with evidence, and the prominent Product Honesty Disclaimer.

---

## Consequences & Trade-Offs

- **No Secret Leaks**: Sanitized keystrokes ensure passwords or accidental secrets typed in comments are not persisted as raw characters.
- **Fail-Closed on Tampering**: Monotonic sequence checks reject replayed or intercepted batches.
- **Fairness & Humility**: The product honesty disclaimer prevents automated bias and over-reliance on heuristics by emphasizing that reading off a secondary device looks like ordinary typing.
- **Zero Impact on Candidate Scores**: Flags remain advisory review prompts for hiring managers and recruiters.
