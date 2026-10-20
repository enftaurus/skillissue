# Design Principles & Visual Identity — Skill Issue

> *"Your interview went badly. Good. Now we have data."*

Skill Issue is an authentic, rigorous career-readiness and technical interview preparation platform. It does not look or feel like a generic AI wrapper, an ordinary question bank, or a gamified enterprise portal. It pairs Gilfoyle-level engineering precision with Gen Z wit.

---

## 1. Visual Direction & Color Hierarchy

### Strict Light-Theme Invariant
The user interface is strictly light-themed. No dark-mode bleed, no dark cards pretending to be "hacker terminals," and no low-contrast gray-on-gray typography.

| Token | Hex | Role | Usage |
|---|---|---|---|
| **Canvas** | `#FAFAFA` | Page Background | Warm, tactile, off-white foundation that reduces eye strain. |
| **Surface** | `#FFFFFF` | Primary Panels | Clean white cards, editor trays, modals, and split view panes. |
| **Subsurface** | `#F4F4F5` | Secondary Surfaces | Inset wells, code output panes, active sidebar tabs, pills. |
| **Border Subtle** | `#E4E4E7` | Component Dividers | Hairline borders (1px) separating panels without visual noise. |
| **Border Strong** | `#D4D4D8` | Active Interactive | Focused inputs, hovered cards, and active navigation indicators. |
| **Ink Primary** | `#09090B` | Headlines & Core Text | Ultra-high contrast (19.5:1 ratio), crisp, unapologetic clarity. |
| **Ink Muted** | `#52525B` | Labels & Metadata | Subtitles, timestamps, parameter badges, and table headers. |
| **Accent Lime** | `#84CC16` | Brand Energy | Primary CTAs, active status dots, high-yield mastery tags. |
| **Accent Dark** | `#65A30D` | Focus & Hover | Button hover states, focus rings, and selection indicators. |
| **Danger / Gap** | `#EF4444` | Deficiencies | Missing concepts, incorrect complexity assertions, test failures. |

---

## 2. Layout & Information Architecture

### The Left-Rail Layout & Command Palette
- **Collapsible Slim Left Rail**:
  Replaces generic top navigation bars with an intentional desktop-first sidebar. Contains quick icons and keyboard shortcuts for:
  - Dashboard (`Cmd+1`)
  - DSA & Coding Arena (`Cmd+2`)
  - Mock Interviews (`Cmd+3`)
  - Planly Calendar (`Cmd+4`)
  - Analytics & Skill Map (`Cmd+5`)
  - Model Settings & BYOC (`Cmd+,`)
- **Global Command Palette (`Cmd+K` / `Ctrl+K`)**:
  Quickly jump to any problem, start a new interview, toggle focus mode, or check persistent skill scores without mouse navigation.

---

## 3. Brand Voice & Editorial Tone

1. **Direct, Dry, and Technically Competent**:
   We treat candidates as adult engineers capable of understanding failure modes.
2. **Never Sycophantic**:
   Never say *"Great job! That was a wonderful explanation!"*
   Instead: *"You identified the cache layer. Now explain why PostgreSQL was bottlenecked in the first place."*
3. **No Decorative Fluff**:
   If an element does not convey diagnostics, code execution, or progress, remove it.
4. **Evidence-Linked Accountability**:
   Critiques always link back to an exact candidate transcript sentence.

---

## 4. Key Workspaces

1. **Coding Arena (`CodingPracticePage`)**:
   Full Monaco Editor integration with split test case runners, masked hidden test status, and live output streaming.
2. **Interview Room (`InterviewSessionPage`)**:
   Distraction-free environment with voice waveform presence, question turn counters ("Question 3 of ~8"), docked editor, and three-tier Socratic hint ladder.
3. **Evaluation Breakdown (`EvaluationPage`)**:
   Diverging bar chart (Self vs AI), question-by-question accordion with verified quotes, and direct Gilfoyle feedback.
4. **Planly Calendar (`PlanlyPage`)**:
   Adaptive multi-day learning roadmap with interactive task checklists and non-mutating schedule shift previews.
