# ADR 0005: At-Rest Credential Encryption

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** The application stores AWS Access Keys and Secret Access Keys provided by users. In the event of an unauthorized database dump or log inspection, these secrets must remain unreadable.
- **Decision:** Encrypt all user credentials at rest using AES-256-GCM via the Python `cryptography.fernet` library. Derive the symmetric encryption key from the environment variable `ENCRYPTION_KEY`. Ensure that the frontend receives only masked identifiers (e.g., `AKIA...39FA`), and that secret keys are never returned or logged.
- **Alternatives Considered:**
  - *Plaintext storage in database*: Rejected as an extreme security vulnerability.
  - *Storing keys solely in browser local storage*: Rejected because the backend needs to perform Bedrock API calls securely without exposing the secret key over repeated client round-trips.
- **Rationale:** Server-side symmetric encryption with ephemeral memory decryption provides strong isolation, full tenant separation, and straightforward credential deletion upon account termination.
- **Consequences:** Backend needs `ENCRYPTION_KEY` configured in `.env`. Key rotation must re-encrypt database records.
- **Related Requirements:** PRD FR-14, Section 9.1; Master Prompt Section 8.
