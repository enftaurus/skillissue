# ADR 0011: Auth Session Management, Outside-Sandbox Hardening, Judging Masking, and User Skills

## Status
Accepted

## Date
2026-10-20

## Context
Following the implementation of the isolated Docker execution microservice (ADR 0010), a comprehensive engineering pass on API correctness, data protection, and authentication security was required per Section 1.8 and Section 2 of the engineering brief. Key concerns addressed included:
1. **Hidden Test Leakage**: The coding problem endpoints and test run results previously risked exposing hidden verification tests, expected outputs, or stack traces to candidates.
2. **Timing Attacks on Authentication**: Non-existent user logins returned immediately without hashing comparisons, enabling email address enumeration.
3. **Session Revocation**: JWT access tokens lacked active revocation upon user logout or password changes, and refresh tokens were not isolated in HttpOnly cookies.
4. **Tenant Key Isolation**: Credential encryption used a single global key without per-user salt derivation, violating tenant cryptographic isolation.
5. **BYOC Spend Safeguards & Region Restrictions**: AWS Bedrock usage lacked hard spending caps and allowed unvetted regions.
6. **XSS & Injection Protections**: Planly external resource URLs and candidate interview transcript data required strict protocol sanitization and untrusted XML delimiters.

## Decision
1. **Judging & Coding API Protection**:
   - Introduce `CodingProblemPublic` schema excluding hidden test cases. Require authentication for problem access.
   - For hidden test executions, mask `stdin`, `expected_stdout`, `actual_stdout`, and `stderr`, exposing only test index, boolean verdict, and status.
   - Add `GET /api/v1/coding/limits` exposing real resource limits (256MB memory, 3.0s CPU time, 1MB output cap, runtime `runc`).
   - Expand coding problem library from 3 to 15 standard algorithm problems with multi-language templates.
2. **Authentication & Session Revocation**:
   - Enforce constant-time password verification via `dummy_verify_password` against a precomputed bcrypt hash on unknown email lookups.
   - Introduce short-lived access tokens (15 minutes) and 7-day refresh tokens stored in `HttpOnly`, `SameSite=Strict` cookies.
   - Add `token_version` to `User`. On `POST /api/v1/auth/logout`, increment `token_version` to immediately invalidate all outstanding access and refresh tokens.
3. **Tenant-Isolated Cryptographic Derivation**:
   - Derive per-user Data Encryption Keys (DEK) using PBKDF2/HKDF with `user_id` as salt over the master `ENCRYPTION_KEY`, ensuring cross-tenant cryptographic isolation for BYOC credentials.
4. **AWS Region Allowlist & Spend Budgets**:
   - Constrain AWS regions strictly to `{"us-east-1", "us-west-2", "ap-south-1", "ap-southeast-2"}`.
   - Enforce configurable monthly token and cost limits with immediate 429 cut-offs.
5. **Rate Limiting & Security Headers**:
   - Implement thread-safe sliding window rate limiting on authentication, LLM messaging, and code execution endpoints.
   - Add strict security headers (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy`) and disable OpenAPI docs outside development.
6. **Prompt Injection & XSS Guardrails**:
   - Wrap diagnostic evaluation data inside `<untrusted_evaluation_data>` XML tags.
   - Strictly validate Planly URLs to `http://` and `https://` schemes.
7. **User Skill State**:
   - Add `user_skills` table with unique constraint on `(user_id, topic)` for persistent skill tracking via exponential moving average.

## Consequences & Trade-offs
- Refresh tokens require clients to handle cookie storage or use the refresh endpoint when access tokens expire after 15 minutes.
- Rate limiting introduces small memory overhead for in-flight sliding window request timestamps.
- Constant-time verification on unknown emails incurs standard bcrypt computation cost (~100ms) on invalid logins, which is an intentional security trade-off to stop email enumeration.

## Related Requirements
- `prd.md`: Section 4 (Security Architecture), Section 5 (Coding Practice Sandbox), Section 6 (Planly).
- `docs/architecture/security.md`.
