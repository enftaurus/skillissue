# Frontend Reliability & User Experience Audit

**Audit Date**: October 20, 2026  
**Auditor**: Staff Full-Stack & UI Reliability Engineer  
**Repository**: `https://github.com/enftaurus/skillissue`  
**Status**: Verified & Remediated

---

## Executive Summary

A comprehensive forensic audit of the Skill Issue frontend application was conducted across all core user journeys: onboarding and authentication, provider/model configuration, interview initialization across all modes, live conversational sessions, self-evaluation comparisons, Planly task schedules, and coding sandbox practice.

While the primary page flows were functional, several critical reliability gaps were identified:
1. **Destructive Input Failures**: Candidate input was eagerly purged prior to API confirmation during interview turns, permanently destroying candidate responses upon network or server errors.
2. **Phantom Optimistic State**: Unconfirmed messages remained rendered in the active chat log when requests failed.
3. **Session Draft Evaporation**: Code drafts in the practice sandbox and candidate self-evaluation reflections were stored in volatile in-memory references, resulting in immediate data loss upon tab switching, navigation, or page reload.
4. **Blocking Raw Alerts**: Legacy `window.alert()` calls interrupted user workflows across multiple feature modules.

All findings have been verified and remediated under the strict light-theme aesthetic guidelines.

---

## Detailed Audit Findings & Remediation

### Finding FE-AUD-01: Input Text Destruction & Phantom Messages on Send Failure
- **Severity**: High (Data Loss)
- **Component**: `frontend/src/features/interview-session/InterviewSessionPage.tsx` (`handleSendMessage`)
- **Reproduction**:
  1. Start an interview session.
  2. Type a multi-paragraph technical explanation into the message input.
  3. Disconnect network or trigger an upstream 503 error.
  4. Submit the message.
- **Root Cause**: `setInputText('')` and `baseInputTextRef.current = ''` were called optimistically prior to `api.post('/interviews/:id/message')`. The `catch` block set an error message but never restored `inputText` and failed to remove `optimisticMsg` from the active message array.
- **User Impact**: Candidate loses their entire answer and sees an unsent message permanently rendered in the chat stream.
- **Remediation**:
  - Maintained draft text in state until server confirmation.
  - Rolled back the optimistic message from state upon catch.
  - Attached a cryptographically unique `client_turn_id` to each submission for server-side idempotency.
  - Rendered an inline retry banner allowing single-click re-submission of the preserved draft.

---

### Finding FE-AUD-02: Self-Evaluation Modal Draft Evaporation on Close/Reopen
- **Severity**: Medium (Friction / Data Loss)
- **Component**: `frontend/src/features/interview-session/SelfEvaluationModal.tsx`
- **Reproduction**:
  1. Conclude an interview and trigger the self-evaluation modal.
  2. Rate rubric dimensions and enter detailed self-reflection text.
  3. Accidentally click outside the modal or press Escape to close it.
  4. Reopen the modal from the header button.
- **Root Cause**: Self-evaluation state (`scores`, `reflection`, `questionEvals`) was stored exclusively in local component state. Closing the modal unmounted the component, discarding all candidate entries.
- **User Impact**: Candidate forced to re-rate and re-type reflections across all dimensions and questions.
- **Remediation**:
  - Backed draft state with `sessionStorage` keyed by `self_eval_draft_${interviewId}`.
  - Automatically restored saved scores and reflection when modal opens.
  - Cleared session storage only upon verified successful evaluation submission.

---

### Finding FE-AUD-03: Practice Code Draft Loss on Page Reload / Navigation
- **Severity**: Medium (Data Loss)
- **Component**: `frontend/src/features/coding/CodingPracticePage.tsx`
- **Reproduction**:
  1. Open a coding problem in the practice environment.
  2. Write code for 10 minutes.
  3. Click to the Dashboard or Interview tab, then click back to Coding Practice, or reload the page.
- **Root Cause**: `draftsRef` was an in-memory `useRef<Record<string, string>>({})` without persistence.
- **User Impact**: Candidates lost in-progress algorithms when switching tabs or refreshing.
- **Remediation**:
  - Synchronized `draftsRef` with `localStorage` under `skillissue_code_draft_${problemId}_${language}`.
  - Seeded initial editor state from local storage before falling back to default starter templates.
  - Preserved separate drafts per language (Python, Java, C++).

---

### Finding FE-AUD-04: Disruptive Blocking Browser Alerts
- **Severity**: Low (Accessibility & UX Violation)
- **Components**:
  - `frontend/src/features/coding/CodingPracticePage.tsx` (lines 105, 107, 140, 142)
  - `frontend/src/features/improvement-plan/PlanlyPage.tsx` (lines 111, 156, 158)
  - `frontend/src/features/interview-session/InterviewSessionPage.tsx` (lines 221, 251)
- **Reproduction**: Trigger code execution timeouts, syntax errors, or plan update failures.
- **Root Cause**: Direct calls to `window.alert(err.message)`.
- **User Impact**: Inaccessible modal popups, halts JavaScript event loop, breaks screen readers, and violates modern design standards.
- **Remediation**:
  - Replaced all `alert()` invocations with inline accessible status banners and styled error notifications adhering to the light-theme palette (`bg-amber-50`, `border-amber-200`, `text-amber-800`).

---

### Finding FE-AUD-05: Real-time Interview Memory Inspection
- **Severity**: Low (Transparency & Debuggability)
- **Component**: `frontend/src/features/interview-session/InterviewSessionPage.tsx`
- **Reproduction**: An interview session is running, but candidate has no visibility into what topics the AI currently considers covered or what claims have been recorded.
- **Root Cause**: Frontend did not query the durable checkpointer state endpoint (`/interviews/:id/state`).
- **User Impact**: Lack of transparency into interview progression and topic transitions.
- **Remediation**:
  - Integrated state retrieval into session loading.
  - Added an interactive collapsible "Interviewer Memory & Topic Lifecycle" panel showing current topic status (`in_progress`, `assessed`, `needs_follow_up`), rolling summary excerpt, and turn progression budget.

---

## Verification Matrix

| Test Journey | Action | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- |
| **Interview Turn** | Submit answer during offline network | Error shown, draft kept in input, retry active | PASS |
| **Idempotency** | Double-click send message button | Server deduplicates `client_turn_id`, exactly 1 turn saved | PASS |
| **Self-Eval Modal** | Close modal with unsaved text, reopen | All ratings and reflection text restored | PASS |
| **Coding Sandbox** | Edit code, navigate away, return | Editor re-hydrates candidate draft from storage | PASS |
| **Sandbox Execution** | Submit invalid code with syntax error | Inline error banner rendered without blocking `alert()` | PASS |
| **Design Standard** | Theme audit | Strict light theme (`#FAFAFA`, `#84CC16`), no neon | PASS |
