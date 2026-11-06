# 0027. Enterprise assessments: signed-in candidates, server-assigned rounds, hidden results

- **Status**: Accepted
- **Date**: 2026-11-06

## Context
The audit of the enterprise exam (2026-11-06) found the candidate runner was mostly a façade, and that it leaked or
lost data:
- Anyone with the invite link could type an existing candidate's email and receive that candidate's session token.
- Every candidate endpoint returned `round_results`, `composite_score` and `integrity_signals`. The completion screen
  showed the composite score.
- The OA showed a hardcoded problem and never sent a problem id, so nothing was ever scored. Project, interview and
  comprehension rounds were free-text boxes or "Coming Soon". Composite scores were always `null`, so the leaderboard
  couldn't rank anyone.
- Rounds could be submitted out of order or resubmitted. The leaderboard returned every candidate's access token to
  recruiters.
- Explanation checks in assessment mode always used the offline mock, both for questions and for judging.

## Decision
1. **Identity.** Candidates take assessments as signed-in users. Entry binds the account
   (`candidate_assessments.candidate_user_id`). The email always comes from the account, and a recruiter's pre-invite
   for that email binds on first entry. Recruiter and admin accounts can't enter. Every candidate endpoint checks
   ownership and returns the same 404 for an unknown token and for someone else's token.
2. **Server-assigned content** (`round_state`), fixed on first open, with the round clock starting then:
   - coding: curated problems with real test suites, either fixed by the recruiter or drawn per candidate;
   - code comprehension: a bank item;
   - project: a repository with an authoritative test suite;
   - interview: N adaptive questions.
3. **Scoring on the server only.**
   - Coding: hidden tests in the sandbox.
   - Project: the project test suite, scored 0 on integrity flags.
   - Comprehension: the existing grader.
   - Interview: the hiring team's model grades a transcript in which candidate text is fenced. The score is scaled by
     the share of questions answered. With no real model (none configured, or the offline mock) the round is
     `not_evaluated`. It is never invented.
4. **Hidden results.** Candidates get `CandidateExamView`: progress plus the work itself. Sample-test output and
   comprehension follow-ups ("what about X?") are part of the work. Scores, verdicts, feedback, rubric data and
   integrity signals are not.
5. **Order.** Submissions are locked (`SELECT ... FOR UPDATE`) and must match the current round index and type.
   Overtime is recorded as a signal for recruiters, not a rejection.
6. **Leaderboard.** Completed, scored candidates are ranked by weighted composite (round `config.weight`, default 1).
   Ties go to the earlier finisher. In-progress candidates are unranked. Per-round scores and interview transcripts are
   visible to recruiters. Tokens are never returned to recruiters.
7. **Explanation checks** in assessment mode use the hiring team's model, and hook questions to names the candidate
   defined rather than imports.

## Consequences
- AI-graded rounds need the recruiter to connect a model. The portal warns when none is connected.
- The old anonymous name+email entry is gone. `scripts/verify_enterprise_assessment_playwright.py` covers the full
  recruiter → candidate → leaderboard path in a browser.
