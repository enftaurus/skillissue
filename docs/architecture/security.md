# Security Architecture & Threat Model — Skill Issue

## 1. Security Invariants

Skill Issue handles two sensitive categories of untrusted inputs:
1. **Third-party Cloud Credentials (BYOC)**: User-provided AWS Access Key ID, Secret Access Key, and Session Tokens.
2. **Untrusted Code Execution**: Arbitrary user-submitted Python, Java, and C++ code.

---

## 2. BYOC Credential Lifecycle & Encryption

### 2.1 Encryption at Rest
- All AWS secret keys are encrypted at rest using AES-256-GCM via `cryptography.fernet`.
- The encryption key is derived from the environment variable `SKILLISSUE_SECRET_KEY`.
- In production, this key should be loaded from a managed key management service (e.g. AWS KMS or Vault).
- Credential values are stored in the database in ciphertext only.

### 2.2 In-Transit Security
- Transmitted exclusively over TLS in deployed environments.
- API endpoints never accept credentials via query parameters or unencrypted payloads.

### 2.3 Protection from Leaks
- **Logging**: A custom logging filter ensures credentials, access keys, or bearer tokens are sanitized prior to emitting log records.
- **Frontend Masking**: Only the last 4 characters of an Access Key ID are returned to the client (`AKIA...4X9Z`). Secret access keys are never returned in any API response.
- **Error Messages**: Boto3/Bedrock errors (such as `AccessDeniedException` or `UnrecognizedClientException`) are caught and mapped to sanitized application-level error codes (`INVALID_CREDENTIALS`, `PERMISSION_DENIED`). Raw exceptions are never returned to the frontend.

---

## 3. Untrusted Code Sandbox Boundary

Untrusted candidate code presents severe threats: denial-of-service, escape to host, cryptomining, network scanning, or local credential theft.

### Isolation Rules
1. **No Root Execution**: Submissions execute under an unprivileged user (UID/GID 10001).
2. **Network Isolation**: Network access is completely disabled (`--net none` or network namespace unsharing).
3. **Resource Quotas**:
   - Execution Timeout: Hard limit of 5.0 seconds per testcase.
   - Memory Limit: 256 MB maximum resident set size.
   - CPU Time Limit: 2.0 CPU cores max.
   - Process / Thread Count: Capped via `pids-limit` / `ulimit -u` to prevent fork bombs.
4. **Filesystem Isolation**: Ephemeral tmpfs mounts with no access to host filesystem, Docker daemon, or environment variables containing server secrets.

---

## 4. Authentication & Multi-Tenant Isolation

1. **Password Hashing**: Passwords are hashed using bcrypt with salt. Plaintext passwords are never stored or logged.
2. **Stateless JWT**: Bearer tokens carry short expiration (60 minutes).
3. **Row-Level Tenant Isolation**: All database operations join on `user_id == current_user.id`. Cross-tenant data leakage is strictly prohibited.
4. **Data Purging**: Account deletion triggers cascading deletion across user profiles, interview transcripts, evaluations, resumes, and encrypted credentials.
