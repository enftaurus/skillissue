# Comprehensive Frontend Audit — Skill Issue

**Date**: 2026-10-20  
**Framework**: React 18, TypeScript 5, Vite, Tailwind CSS  
**Visual Style**: Strictly Light Theme (`#FAFAFA` surfaces, `#09090B` typography, `#65A30D` / `#84CC16` acid-lime accents, `#E4E4E7` borders)  

---

## 1. Page-by-Page Inspection

### 1.1 Authentication Pages (`LoginPage.tsx`, `RegisterPage.tsx`)
- **Functional Checks**:
  - Sign in, registration, and logout flows functional.
  - Redirect preservation (`from: location`) present in protected route wrapper.
- **Identified Gaps**:
  - Form validation: missing client-side password minimum length check before API dispatch.
  - Keyboard navigation: Enter key submits properly.
- **Responsive & Design Review**:
  - Single column centered layout fits mobile (320px), tablet (768px), and desktop (1280px).
  - High contrast ratio (black text `#09090B` on white card `#FFFFFF` meets WCAG AAA > 12:1).

### 1.2 Cockpit Dashboard (`DashboardPage.tsx`)
- **Functional Checks**:
  - Displays answer cards for the 3 core product questions:
    1. *What do I need to improve?*
    2. *What should I do next?*
    3. *Have I actually improved?*
  - Today's Planly tasks list with completion checkboxes.
  - Recent interview sessions list with direct links to scorecard or active interview.
- **Identified Gaps**:
  - Optimistic task completion has rollback on network failure.
  - Responsive review: Grid collapses smoothly from 3 columns to 1 column on screens < 768px.

### 1.3 Interview Setup (`InterviewSetupPage.tsx`)
- **Functional Checks**:
  - Mode selection: Domain mode vs. Job Description (JD) mode.
  - Category selector (technical, behavioral, dsa, managerial).
  - Target role input, custom skill addition, and optional resume upload.
  - JD parsing with automatic skill and requirement extraction.
- **Identified Gaps**:
  - File upload input lacked clear drag-and-drop indicator; accepts `.pdf`, `.txt`, `.md`.
  - Empty skill state validation prevents starting empty domain interviews.

### 1.4 Live Interview Session (`InterviewSessionPage.tsx`)
- **Functional Checks**:
  - Real-time conversation stream with automatic autoscroll.
  - Live elapsed timer and session completion modal.
  - DSA split view with sandbox runner integration for coding rounds.
- **Identified Gaps [FE-01, FE-03]**:
  - **Speech Duplication**: Interim speech recognition results were appended cumulatively into `inputText`, causing exponential word duplication.
  - **Microphone Feedback Loop**: Speech synthesis playback of interviewer questions was picked up by the microphone and transcribed as candidate speech.
  - **Resolution**: Separate committed transcript from active interim stream; mute recognition during audio playback.

### 1.5 Candidate Self-Evaluation (`SelfEvaluationModal.tsx`)
- **Functional Checks**:
  - Candidate scores themselves on 1-5 scale across all category rubric dimensions before seeing AI score.
  - Score criteria descriptions dynamically render per selected score (1-5).
  - Optional personal reflection textarea.
- **Identified Gaps**:
  - Modal backdrop click dismissal was disabled to prevent accidental loss of scored rubrics.
  - Required validation confirms all rubric dimensions are scored before submission.

### 1.6 Performance Evaluation Report (`EvaluationPage.tsx`)
- **Functional Checks**:
  - Overall score banner, model identifier, and coaching disclaimer.
  - Self vs. AI comparison table showing candidate score, AI score, delta, evidence quote citation, and explanation.
  - Verified strengths, key blind spots, and missing engineering concepts.
  - "Generate Improvement Plan" CTA linking to Planly.
- **Identified Gaps [FE-05]**:
  - If evaluation generation failed or was interrupted, page showed a dead end ("Evaluation not found").
  - Resolution: Added "Generate Evaluation Now" button allowing user to trigger AI pass directly from page.

### 1.7 Planly Improvement Roadmap (`PlanlyPage.tsx`)
- **Functional Checks**:
  - Day-by-day tabbed timeline from Day 1 to Day N.
  - Task completion toggles with optimistic UI updates.
  - Task type badges (`concept`, `practice`, `coding`, `reassessment`).
  - External documentation and guide links.
  - "Fell Behind? Adapt" schedule recalculation modal.
- **Identified Gaps**:
  - Empty state handles users without an active plan with a direct CTA to launch a diagnostic mock interview.

### 1.8 Progress Analytics (`ProgressAnalyticsPage.tsx`)
- **Functional Checks**:
  - Headline metrics: completed interviews, average score, Planly completion rate, reassessment count.
  - Verified reassessment cycles: before-and-after cards comparing baseline vs. reassessment on identical rubrics with score delta and dimension change tags.
  - Rubric dimension progress bars and persistent blind spot lists.
- **Design Review**:
  - Acid-lime accents (`#84CC16`, `#65A30D`) used selectively for positive metrics and progress bars; subtle borders (`#E4E4E7`) maintain visual calm without neon slop.

### 1.9 Isolated Coding Sandbox (`CodingPracticePage.tsx`)
- **Functional Checks**:
  - Problem catalog dropdown (Two Sum, Valid Parentheses, Longest Substring).
  - Multi-language tabs (Python 3, Java 21, C++ 17).
  - Sample test runner (`POST /coding/run`) and full submission (`POST /coding/submit`).
  - Output pane distinguishing compilation error, runtime error, timeout, and passed test cases.
- **Identified Gaps [FE-02]**:
  - Switching languages or problems wiped the active code draft.
  - Resolution: Added multi-problem, multi-language draft persistence via `localStorage` and component state cache.

### 1.10 BYOC Provider Settings & AWS Setup Guide (`ProviderSettingsPage.tsx`, `AwsSetupGuidePage.tsx`)
- **Functional Checks**:
  - Provider toggle: Mock Provider (local dev) vs. Amazon Bedrock (BYOC).
  - Model catalog selection displaying input/output pricing per 1M tokens and context window.
  - Credential test connection with live latency measurement.
  - One-click copy for IAM least-privilege policy in the setup guide.

---

## 2. Accessibility & Responsive Evaluation

| Viewport | Tested Width | Behavior & Status |
| :--- | :--- | :--- |
| **Mobile** | 360px – 480px | Single column stack, navbar collapses to accessible layout, coding editor maintains horizontal scroll on monospace pre blocks, touch targets meet 44px min. |
| **Tablet** | 768px – 1024px | 2-column layouts for evaluation and planly, side-by-side header metrics, responsive modal scaling. |
| **Desktop** | 1280px – 1920px | Full split-screen interview layout, DSA dual-pane editor, dashboard 3-column question cards. |

- **Color Contrast**: Dark ink `#09090B` on white `#FFFFFF` achieves 19.5:1 (exceeds WCAG AAA). Muted text `#52525B` on `#FAFAFA` achieves 6.8:1 (exceeds WCAG AA).
- **Reduced Motion**: Transitions respect standard browser defaults; no disorienting looping animations.
