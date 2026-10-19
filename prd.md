# Skill Issue — Product Requirements Document (PRD)

**Version:** 1.0 — First Draft  
**Status:** Discovery complete; ready for architecture and implementation planning  
**Product category:** AI-powered interview preparation and career-readiness platform  
**Initial audience:** Engineering students and individual learners aged 18+  
**Initial language:** English  
**Brand tagline:** *Your interview went badly. Good. Now we have data.*  
**Brand personality:** Gen Z humour × Gilfoyle-level engineering precision

---

## 1. Product overview

### 1.1 Vision

Skill Issue is an AI-powered career-readiness platform that helps students prepare for interviews, understand their weaknesses, improve through personalised practice, and measure whether they have actually improved.

Unlike a conventional mock-interview chatbot that asks questions and produces a score, Skill Issue creates a continuous improvement loop:

**Practise → Self-evaluate → Receive evidence-based feedback → Improve → Reassess → Measure progress.**

The platform should help users answer three questions:

1. What am I currently good at?
2. What specifically is holding me back?
3. What should I do next to become better?

### 1.2 Problem statement

Students frequently prepare for interviews through disconnected resources: question banks, coding platforms, videos, mock interviews and generic AI conversations.

These approaches often fail to connect practice with measurable progress. Students may not understand why an answer was weak, may misjudge their own performance, or may repeatedly practise without addressing the underlying weakness.

Skill Issue aims to connect interview simulation, self-assessment, structured evaluation, personalised improvement tasks and repeat assessments in one platform.

### 1.3 Product positioning

> Skill Issue is the interview coach that shows you the evidence, tells you what to fix, and lets you prove you've improved.

It is a learning and preparation tool, not an automated hiring decision-maker. Its scores are coaching estimates, not guarantees of interview success.

---

## 2. Goals and non-goals

### 2.1 Product goals

- Provide realistic, adaptive interview practice.
- Support both job-description-based and domain-based interviews.
- Help learners compare self-evaluation with structured AI evaluation.
- Generate actionable, multi-day improvement plans.
- Measure progress across comparable interview attempts.
- Support technical interviews, HR/behavioural interviews, DSA and managerial or role-specific interviews.
- Enable secure execution of coding questions in Python, Java and C++.
- Let users bring their own supported AI provider credentials (BYOC).
- Establish a reusable interview, evaluation and learner-profile engine for future placement preparation.
- Keep fixed infrastructure costs as low as practical.

### 2.2 Non-goals for the initial release

- Automated hiring decisions or candidate rejection.
- College placement-cell dashboards.
- Full recruitment management or job-application tracking.
- An Android or iOS application.
- Local AI model installation on students' machines.
- Audio recording and audio storage.
- AI-generated courses or complete lessons.
- Complex usage quotas, billing tiers and spending-limit management.
- Judge0 integration in the first implementation.
- LangGraph-based agent orchestration in the initial architecture.
- A requirement to reuse the previous Intrvyuuu implementation.

---

## 3. Target users and personas

### Persona A — The engineering student

An undergraduate student preparing for internships, campus placements and technical interviews.

**Needs**
- Realistic practice without scheduling a human interviewer.
- Questions tailored to a selected JD or chosen skills.
- Honest feedback on technical depth and communication.
- A clear plan for improving weak areas.
- Evidence of progress over time.

### Persona B — The domain-focused learner

A learner who wants to practise a specific set of skills, independent of one particular job posting.

**Needs**
- Select the skills to practise.
- Use resume-detected skills as convenient defaults.
- Change the selection before beginning.
- Practise repeatedly at increasing levels of difficulty.

### Persona C — The future placement-preparation user

A candidate preparing for a specific job opening or company.

**Needs**
- Understand the requirements of a job description.
- Practise relevant skills and interview questions.
- Identify gaps between current ability and the role's requirements.

This persona informs Phase 2. It does not introduce a separate interview engine.

---

## 4. Scope and release strategy

### Phase 1 — BYOC foundation

Establish the provider-configuration infrastructure and secure credential lifecycle.

Deliverables:
- User authentication.
- Provider configuration storage.
- AWS Bedrock integration.
- Model/provider factory.
- Credential validation and error handling.
- Encrypted credential storage and deletion.
- A basic interface for configuring and testing a provider.

This phase establishes the technical foundation for the interview platform.

### Phase 2 — Interview beta and placement preparation

Build the student-facing interview experience and the reusable learner engine. Job-description-based preparation is added using the same core interview, evaluation and learner-profile services.

The work can proceed in parallel where dependencies allow.

Beta functionality includes:
- Interview setup and execution.
- Self-evaluation and AI evaluation.
- Voice input with text fallback.
- Coding rounds with Docker-based sandbox execution.
- Improvement plans and learning resources.
- Progress analytics.
- Job-description-based preparation.

**Access policy:** The application will be publicly hosted. The final beta invitation mechanism and cohort size will be decided after a working website exists; these are not prerequisites for starting development.

### Future phases

- Judge0 integration as a possible alternative coding-execution backend.
- Placement-cell and institutional dashboards.
- Additional model providers and authentication methods.
- Advanced usage controls, quotas and spending management.
- Additional languages and accessibility enhancements.
- Further evaluation and learning-effectiveness studies.

---

## 5. Core user journeys

### 5.1 Onboarding and model configuration

1. The user registers using email and password.
2. The user opens AI provider settings.
3. The user selects a supported provider and recommended model.
4. The user supplies the required AWS credentials.
5. The platform validates the credentials and checks model access.
6. The user sees a clear success or actionable error state.
7. The selected configuration becomes available to interview and evaluation services.

Users should receive clear instructions for creating least-privilege AWS IAM credentials. They must not be instructed to share root-account credentials.

### 5.2 Domain-based interview

1. The user chooses domain-based interview mode.
2. The user selects the skills they want to practise.
3. If a resume is uploaded, the system extracts relevant skills and preselects matching options.
4. The user reviews and modifies the selection.
5. The user selects an interview type and starts the session.
6. The interviewer asks relevant questions and adaptive follow-ups.
7. The user completes the interview.
8. The user evaluates their own performance.
9. The AI evaluation is revealed with evidence and actionable feedback.
10. The platform updates the learner profile and recommends next steps.

Resume upload is optional.

### 5.3 Job-description-based interview

1. The user supplies a specific job description.
2. The platform extracts relevant role requirements, skills and competencies.
3. The user reviews the extracted requirements and can correct extraction errors.
4. The system generates an interview focused on that JD.
5. Questions and follow-ups adapt to the JD and the candidate's answers.
6. The user completes self-evaluation and AI evaluation.
7. The platform identifies strengths and gaps against the selected JD.
8. The resulting improvement plan targets the most relevant gaps.

**Important:** JD-based mode does not require the user to select the same skills manually a second time. The selected JD defines the interview scope.

### 5.4 Improvement and reassessment

1. The system identifies weak rubric dimensions.
2. It creates a multi-day plan based on the user's stated daily availability.
3. Each day contains actionable tasks and relevant external resources.
4. The system adapts the plan when tasks are missed or reassessment results change.
5. The user repeats a comparable interview.
6. The platform compares results and shows which dimensions improved, remained stable or declined.

---

## 6. Functional requirements

### FR-01 — Authentication and user profile

- Email/password registration and login.
- Secure password storage and session management.
- User profile and learner history.
- Account deletion.
- English-only interface and English interview generation in the initial release.
- Adult users aged 18 and above.

### FR-02 — BYOC and model configuration

- AWS Bedrock is the first supported inference provider.
- Provider configuration is stored against the authenticated user.
- The backend selects the configured provider and model through a model factory.
- The platform recommends models based on measured quality, latency, availability and cost.
- Advanced users can choose from supported models.
- Credentials are validated before being used for interviews.
- Users can update or remove credentials.
- Invalid credentials, permission errors, unavailable models and throttling must produce useful error messages.

The initial architecture should support additional providers without requiring the interview engine to be rewritten.

The recommended model list must be benchmarked against actual Bedrock availability in supported regions. Model availability and pricing must not be assumed to be universal.

### FR-03 — Interview setup

The platform must support two setup modes.

**Domain-based**
- User-selected skills define the interview scope.
- Resume-detected skills are preselected when a resume is provided.
- The user can modify the selection.
- Resume upload remains optional.

**JD-based**
- The selected job description defines the interview scope.
- Requirements and skills are extracted from the JD.
- The user can review extracted requirements.
- Questions, follow-ups, evaluation and improvement tasks remain aligned with the JD.

### FR-04 — Interview types

The beta supports four interview categories:

1. **Technical interviews:** Concepts, explanations, applied knowledge and technical depth.
2. **HR/behavioural interviews:** Communication, experience, decision-making and behavioural examples.
3. **DSA interviews:** Problem solving, algorithm selection, complexity analysis and coding.
4. **Managerial/role-specific interviews:** Role-dependent scenarios, collaboration, trade-offs and decision-making.

These categories share one interview engine with configuration-specific question strategies and evaluation rubrics.

### FR-05 — Adaptive interviewing

- Questions must be relevant to the selected interview scope.
- Follow-up questions adapt to the candidate's previous answers.
- The system should request clarification when answers are incomplete or ambiguous.
- Question difficulty may adapt based on demonstrated performance.
- The interviewer should not reveal the complete answer immediately after a weak response.
- The interviewer should remain consistent with the chosen JD, domain and interview category.
- Session duration should target approximately 15–30 minutes.

### FR-06 — Voice and text interaction

- Support spoken interview responses where browser capabilities allow.
- Provide a text-based fallback.
- Display the recognised text so the candidate can correct errors.
- Avoid requiring raw audio uploads or recordings.
- Store interview transcripts, not raw audio.

Browser speech recognition varies by browser and may use an external speech service. The implementation must communicate relevant limitations and privacy implications rather than promise universal offline or free speech processing.

### FR-07 — Self-evaluation

After an interview, the user must be able to evaluate their own performance before seeing the AI's assessment.

The self-evaluation should cover relevant rubric dimensions, such as:
- Technical correctness.
- Depth of explanation.
- Structure and clarity.
- Problem-solving approach.
- Completeness of the answer.
- Communication and confidence where appropriate.

Not every dimension applies to every interview type. Confidence should not be treated as a substitute for correctness.

### FR-08 — AI evaluation

- Evaluate completed interviews against explicit rubrics.
- Use evidence from the transcript and coding results where applicable.
- Provide strengths, weaknesses, missing concepts and suggested improvements.
- Show supporting excerpts for important judgements.
- Provide uncertainty indicators when the evidence is insufficient.
- Compare AI assessment with self-assessment.
- Avoid unsupported claims about employability or hiring probability.

The evaluator should be implemented as a separate post-interview evaluation pass by default, rather than relying only on the interviewer to grade its own conversation. This is a proposed implementation choice to improve consistency.

### FR-09 — Question bank and generation

Use a hybrid approach:
- A curated question bank for consistency and repeatable assessments.
- AI-generated questions for personalisation and adaptive follow-ups.

Questions should be tagged by interview type, skills, difficulty and applicable rubric dimensions.

Repeated assessments should be comparable without simply repeating identical questions every time. Equivalent questions should assess the same underlying skills.

### FR-10 — Resume and JD processing

- Resume upload is optional.
- Extract relevant skills and project context from resumes.
- Use extracted information to personalise questions.
- In domain mode, preselect resume-detected skills.
- In JD mode, focus on requirements from the selected JD.
- Allow users to review and correct extracted information.
- Avoid inventing experience or qualifications that are not supported by the uploaded material.

### FR-11 — Personalised improvement plan

The platform's improvement-plan feature is called **Planly**.

Planly must:
- Use evaluation results to identify priority weaknesses.
- Generate a multi-day plan.
- Account for the user's available daily study time.
- Provide daily tasks and external learning resources.
- Adapt to missed days.
- Update priorities when new assessment evidence is available.
- Recommend reassessment when sufficient practice has occurred.

The initial release does not need to generate full lessons or course material. Resource links and actionable tasks are sufficient.

### FR-12 — Progress analytics

The learner dashboard must show:
- Interview history.
- Self-assessment versus AI-assessment comparisons.
- Skill-wise performance trends.
- Strengths and recurring weaknesses.
- Planly task completion.
- Reassessment results.
- Evidence supporting meaningful changes in scores.

Progress should be calculated using comparable rubrics and assessments. A higher score from a different or easier interview must not automatically be presented as proof of improvement.

### FR-13 — Coding interviews

The coding module supports:
- Python.
- Java.
- C++.

Features:
- In-browser code editor.
- Test cases and execution results.
- Timeouts and resource limits.
- Hints and follow-up questions.
- Evaluation of correctness, problem-solving and complexity.
- Integration with the shared learner profile and improvement plan.

**Execution architecture:** Docker-based sandbox service for the initial implementation, hosted separately from the main application. Judge0 may be considered later.

Untrusted code must never execute inside the normal API process or on the frontend.

### FR-14 — Data controls

- Retain progress while the account is active.
- Allow users to delete their account and associated data.
- Provide a way to delete individual interview records where practical.
- Store transcripts and structured evaluation results.
- Do not retain raw audio.
- Remove stored credentials when users remove their provider configuration or delete their accounts.
- Define retention and deletion behaviour for backups and operational logs before launch.

### FR-15 — Usage controls

Advanced quota systems, daily/monthly usage caps and a full cost-control policy are future scope.

This does not remove the need for baseline security protections, request validation, execution timeouts, session-duration limits, and defensive handling of abusive traffic or runaway requests.

The platform must not imply that IAM credentials automatically enforce a spending cap. AWS budget alerts are not necessarily hard spending stops, and the user must understand that distinction.

---

## 7. Evaluation framework

Evaluation quality is a core product requirement, not a later cosmetic improvement.

### 7.1 Rubric design

Each interview category must have a defined rubric. Criteria and scoring anchors should describe observable performance, not vague impressions.

For example, a technical explanation rubric could distinguish:
- Incorrect or unsupported answer.
- Partially correct answer with important omissions.
- Correct answer with adequate explanation.
- Correct, well-reasoned answer with relevant examples and trade-offs.

### 7.2 Evidence-backed scoring

For each important score:
- Identify the relevant rubric criterion.
- Provide the transcript excerpt or coding evidence supporting the assessment.
- Explain the gap between the answer and the expected performance.
- Give a concrete next step.

### 7.3 Benchmark validation

Before claiming that AI scores reliably represent interview ability:
- Create a benchmark set of interview responses.
- Obtain human ratings using the same rubric.
- Measure agreement between AI and human reviewers.
- Investigate systematic disagreement across skills and interview types.
- Test evaluator consistency across supported models.
- Re-run evaluation tests when prompts, rubrics or models change.

Human-reviewed benchmark data is required before making strong claims about evaluation validity.

### 7.4 Learning-effectiveness validation

A pilot should compare:
- Baseline performance.
- Self-evaluation accuracy.
- Completion of recommended practice tasks.
- Performance on a comparable final assessment.

The primary research question is whether the complete practice-and-improvement loop leads to measurable skill gains, not merely whether users like the feedback.

---

## 8. Technical architecture

### 8.1 Technology stack

| Layer | Proposed technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| UI | Tailwind CSS |
| Backend API | Python, FastAPI |
| Database | PostgreSQL |
| Initial LLM provider | Amazon Bedrock |
| LLM integration | LangChain provider-specific wrappers |
| Provider selection | Application-owned model factory |
| Coding execution | Isolated Docker-based sandbox service |
| Deployment | Publicly hosted web application |
| Authentication | Email/password |
| Model orchestration | Shared modular interview engine |

### 8.2 High-level architecture

```text
React + TypeScript Web Application
                 |
                 v
            FastAPI Backend
                 |
      +----------+-----------+
      |          |           |
      v          v           v
 Authentication  Interview   Learner Profile
 and BYOC        Engine      and Planly
      |          |
      v          v
 PostgreSQL   Model Factory
                 |
                 v
          Provider Wrapper
                 |
                 v
           Amazon Bedrock

FastAPI Backend
       |
       v
Private Sandbox API
       |
       v
Isolated Docker Execution Environment
       |
       v
Python / Java / C++ Results
```

This is a logical architecture. The first release should remain a modular monolith for ordinary application services. The coding sandbox is separated because executing untrusted code presents a distinct security risk.

### 8.3 BYOC model factory

The backend should:
- Load the authenticated user's provider configuration.
- Resolve the provider through an explicit, trusted mapping.
- Instantiate the corresponding provider wrapper.
- Apply the user's supported model selection.
- Handle provider-specific errors consistently.
- Return structured results to interview and evaluation services.

Do not allow database values to trigger arbitrary dynamic imports or arbitrary class construction.

LiteLLM is not part of the chosen initial architecture. LangGraph is also excluded from the initial release; introduce orchestration complexity only if a demonstrated requirement justifies it.

### 8.4 Data model — initial entities

The database will need entities equivalent to:

- `users`
- `user_profiles`
- `provider_configs`
- `resumes`
- `job_descriptions`
- `skills`
- `interview_sessions`
- `interview_questions`
- `interview_responses`
- `self_evaluations`
- `ai_evaluations`
- `rubrics`
- `improvement_plans`
- `plan_tasks`
- `assessment_results`
- `coding_submissions`
- `audit_events`

Exact schemas and relationships should be designed during technical planning. This list is a starting point, not a final migration specification.

---

## 9. Security, privacy and reliability

### 9.1 BYOC credential security

- Encrypt provider credentials at rest using managed key infrastructure.
- Never log raw credentials or expose them in API responses.
- Mask secrets in the interface.
- Enforce user-level tenant isolation.
- Use least-privilege IAM permissions.
- Provide credential removal and rotation paths.
- Keep secrets out of prompts, transcripts and evaluation output.
- Validate credentials without exposing sensitive error details.

### 9.2 Coding sandbox security

The coding sandbox must:
- Run code in isolated, ephemeral environments.
- Use non-root execution.
- Avoid privileged containers.
- Avoid exposing the Docker daemon or Docker socket to the public frontend.
- Disable network access for untrusted code by default.
- Apply CPU, memory, process-count and wall-clock limits.
- Prevent access to host files, credentials and application secrets.
- Clean up containers and temporary files after execution.
- Record execution status and resource-limit failures safely.

Docker containers alone are not a complete security boundary against hostile code. The deployment should evaluate stronger isolation, such as dedicated VMs or microVMs, for public untrusted execution.

### 9.3 Data privacy

- Store transcripts, not raw audio.
- Restrict access to resumes and interview data.
- Allow user-initiated deletion.
- Define backup deletion and retention procedures.
- Do not use private learner data for unrelated purposes without appropriate disclosure and consent.

### 9.4 Reliability

- Handle interrupted interviews and failed model calls.
- Preserve completed responses when a recoverable failure occurs.
- Show clear retry or resume options.
- Avoid duplicating evaluation records on retry.
- Keep model failures distinct from user-performance failures.

---

## 10. Non-functional requirements

### Performance
- The interface should remain responsive while model calls execute.
- Long-running interview and coding operations should report their status.
- Timeouts and retries must be bounded.

### Security
- Secrets and user data must be protected in transit and at rest.
- Coding execution must be isolated.
- Authentication and authorisation must be enforced on every protected operation.

### Maintainability
- Interview types must be configurable.
- Rubrics and prompts must be versioned.
- Model providers must be replaceable through the factory abstraction.
- The same learner-profile and evaluation services must serve domain and JD modes.

### Cost
- Prefer low-cost models that meet measured quality requirements.
- BYOC should cover supported inference charges for users' own model calls.
- The platform must account separately for hosting, database, email, monitoring and sandbox costs.
- Avoid assuming that BYOC makes the entire service free to operate.

### Accessibility and usability
- Provide text fallback for voice interaction.
- Make errors understandable to students.
- Do not rely solely on colour to communicate performance.
- Ensure users can correct extracted skills and JD requirements.

---

## 11. Success metrics

### Product activation
- Percentage of registered users who successfully configure a provider.
- Percentage who complete their first interview.
- Time from registration to first completed interview.

### Engagement
- Completed interviews per active learner.
- Planly task completion rate.
- Percentage of learners returning for reassessment.

### Learning outcomes
- Change in comparable rubric scores between baseline and reassessment.
- Change in agreement between self-evaluation and human-reviewed assessment.
- Improvement by individual rubric dimension.
- Percentage of learners improving on at least one targeted weakness.

### Evaluation quality
- Agreement between AI and human reviewers.
- Evaluator consistency across repeated runs and supported models.
- Frequency of unsupported or evidence-free feedback.
- Rate of rubric and evaluation regression after changes.

### Reliability and cost
- Interview completion rate.
- Model-call failure rate.
- Coding execution failure rate.
- Infrastructure and sandbox cost per completed interview.
- Credential-validation success rate.

Targets should be established after baseline measurements and pilot testing rather than invented before usage data exists.

---

## 12. Beta acceptance criteria

The beta is ready for controlled testing when:

1. A user can register, log in and configure a supported Bedrock model.
2. Credentials are encrypted, masked, isolated by user and removable.
3. The user can complete a domain-based interview.
4. The user can complete a JD-based interview without separately reselecting the JD's skills.
5. Resume-detected skills are preselected in domain mode and can be changed.
6. Technical, HR/behavioural, DSA and managerial/role-specific interview configurations are supported.
7. Adaptive follow-ups work across supported interview types.
8. Users can use voice where supported and always have a text fallback.
9. Users can self-evaluate before viewing AI evaluation.
10. AI feedback includes rubric-based scores, evidence and actionable next steps.
11. Planly creates and adapts a multi-day improvement plan.
12. Progress is retained and comparable assessments can be reviewed.
13. Python, Java and C++ code can execute in the isolated sandbox.
14. Account and interview-data deletion flows are implemented and tested.
15. Human-reviewed benchmark testing has been conducted before making strong claims about evaluation validity.
16. Security testing covers credential handling, access control and sandbox isolation.

The first beta should prioritise a reliable end-to-end learning loop over a large number of polished secondary features.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| AI scores are inconsistent | Human-reviewed benchmarks, rubric versioning and regression tests |
| Feedback is generic or unsupported | Evidence-linked scoring and concrete corrective actions |
| Users overtrust AI scores | Explain uncertainty and position scores as coaching estimates |
| BYOC onboarding is too complex | Guided setup, credential validation and clear error messages |
| Users misunderstand AWS spending | Explain that IAM access does not automatically create a spending cap |
| Malicious code compromises infrastructure | Isolated sandbox service, strict resource controls and stronger isolation where needed |
| Users stop after one interview | Personalised Planly tasks and reassessment prompts |
| Model availability or pricing changes | Configurable recommendations and provider-specific validation |
| Infrastructure costs grow unexpectedly | Measure cost per interview and optimise infrastructure separately from inference |

---

## 14. Open decisions and assumptions

The following are not blockers for starting the initial architecture, but should be resolved before the relevant feature is implemented.

1. **Provider authentication:** Exact AWS credential format and supported authentication mechanisms.
2. **Model recommendations:** Which currently available Bedrock models meet quality and cost targets.
3. **Session recovery:** Proposed default is to resume recoverable sessions and preserve completed responses; restart only when recovery is not possible.
4. **Evaluation execution:** Proposed default is a separate post-interview evaluation pass.
5. **Beta launch gate:** Proposed default is a reliable end-to-end user journey plus baseline security and human-reviewed evaluation validation; visual polish is secondary.
6. **Invitation policy:** Final mechanism and cohort size to be decided after the working website exists.
7. **Operational quotas:** Advanced numeric usage limits and cost-management features remain future scope.
8. **Coding isolation:** Final decision on Docker-in-VM versus stronger sandbox isolation must account for security, cost and expected usage.
9. **Privacy policy:** Final retention, backup deletion, and external speech-service disclosures must be documented before launch.

---

## 15. Product principle

Skill Issue should never confuse *looking prepared* with *becoming better prepared*.

The product should make a learner's weaknesses understandable, the next action obvious, and the improvement measurable.

**Practice. Debug. Improve. Rerun.**

