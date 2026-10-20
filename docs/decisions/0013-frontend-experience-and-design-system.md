# ADR 0013: Frontend Experience, Design System, Monaco Workspace & Calibrated Analytics

- **Status**: accepted
- **Date**: 2026-10-20
- **Author**: Staff Frontend & Product Engineer

---

## 1. Context

Skill Issue is an engineering interview preparation and career-readiness platform. As mandated in the PRD, `AGENTS.md`, and the Staff Engineering Brief, the frontend must deliver an authentic, polished experience characterized by:
- A strict **light theme** (warm white `#FAFAFA`/`#F4F4F5`, dark ink `#09090B`/`#18181B`, restrained acid-lime `#84CC16`/`#65A30D` accents, subtle `#E4E4E7` borders).
- Gen Z wit meets Gilfoyle-level engineering precision: concise, dry, technically exacting, with zero generic AI praise.
- Real developer ergonomics: keyboard shortcuts (`Cmd+K` command palette, `Cmd+1..5` navigation jumps, spacebar push-to-talk in audio sessions), Monaco Editor split-pane coding workspace, and live animated audio presence.
- Clear evidence-based evaluation: diverging delta charts (self-assessment vs AI calibration) and per-question verbatim transcript feedback accordions.
- Adaptive planning: transparent schedule shifting preview showing task offset before confirmation.

Prior UI iterations used generic card grids and lacked real code editor capabilities, diverging calibration charts, or persistent skill visualizations.

---

## 2. Decision

We have established and implemented the following frontend architecture:

1. **Design System & Collapsible Left Rail**:
   - Implemented `Sidebar.tsx`: a slim 64px collapsible icon rail expanding to 240px with keyboard tooltips (`Cmd+1..5`) and a live BYOC Bedrock credential health pill.
   - Implemented `CommandPalette.tsx`: global `Cmd+K`/`Ctrl+K` modal offering instantaneous navigation jumps, interview launching, and BYOC configuration.
   - Enforced strict light theme in `docs/design/principles.md` and Tailwind tokens (`surface-warm`, `surface-subtle`, `ink`, `ink-muted`, `lime-500/600`).

2. **Monaco Code Editor & Split Workspace**:
   - Embedded `@monaco-editor/react` in `CodingPracticePage.tsx` and `InterviewSessionPage.tsx` with light theme `vs`, font ligatures, line numbers, and minimap controls.
   - Built resizable dual-pane layout using `react-resizable-panels` (`Group`, `Panel`, `Separator`).
   - Added persistent draft memory across language switches (`python`, `java`, `cpp`).

3. **Audio Waveform Presence**:
   - Built `AudioWaveform.tsx`: a 5-bar animated audio visualizer reflecting AI speech synthesis state and mic input suppression during turn-taking.

4. **Calibrated Diverging Evaluation Visualizations**:
   - In `EvaluationPage.tsx`, integrated Recharts horizontal Diverging Bar Chart (`[-3, +3]`) displaying Candidate Self-Score vs AI Evaluator Delta, alongside side-by-side grouped bars (1–5 scale).
   - Built Per-Question Verbatim Feedback Accordion with `ShieldCheck` transcript-grounded badges, candidate quote callouts, Gilfoyle critiques, and Staff-level model answers.

5. **Planly Live Shift Preview**:
   - In `PlanlyPage.tsx`, integrated `POST /api/v1/plans/{plan_id}/adapt/preview` to render a real-time diff of preserved completed milestones vs advanced tasks (`Day X → Day Y`) before applying schedule adjustments.

6. **Persistent Skill Map Analytics**:
   - In `ProgressAnalyticsPage.tsx`, rendered calibrated Exponential Moving Average (`score/100`) and confidence meters (`confidence%`), backed by expandable evidence history drawers.

---

## 3. Alternatives Considered

- **Dark Theme / Neon Terminal UI**: Rejected per PRD and `AGENTS.md` ("Strictly Light Theme"). Developer tools often overuse dark mode; a warm, typography-first light palette communicates precision and clarity.
- **Custom Textarea instead of Monaco**: Rejected. Candidates practicing for technical interviews expect real IDE behaviors (indentation, bracket matching, syntax highlighting, keyboard shortcuts).
- **Static Evaluation Grids**: Rejected in favor of diverging delta charts and expandable transcript grounding. Blindspots cannot be addressed without comparing self-perception directly against calibrated rubrics.

---

## 4. Consequences & Verification

- **TypeScript Compilation**: `npm --prefix frontend run build` completes with 0 errors in under 3.0s.
- **Visual Cohesion**: All pages (`/`, `/interviews/:id`, `/coding`, `/evaluations/:id`, `/planly`, `/analytics`) share identical typography, spacing, and component paradigms.
- **Security**: No secrets or decrypted IAM keys are accessible to client scripts or bundles.
