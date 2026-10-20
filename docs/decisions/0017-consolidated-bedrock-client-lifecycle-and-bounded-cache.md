# ADR 0017: Consolidated Bedrock Client Lifecycle, Bounded LRU Cache, and Zero-Decryption Cache Hits

## Status
Accepted

## Date
2026-10-20

## Context
Previously, AI features across Skill Issue had fragmented client lifecycle paths:
1. `ModelFactory` and `ModelClientFactory` implemented duplicate resolution logic.
2. Every inference request queried PostgreSQL for `ProviderConfig` and executed Fernet/AES-GCM decryption of AWS credentials just to discover that an existing client was cached.
3. Cache keys included transient task names (`task_type`), creating unnecessary duplicate clients when effective parameters (model, Region, temperature, tokens) were identical.
4. Client caching lacked hard capacity bounds, LRU eviction, and configuration version invalidation across multi-worker application deployments.
5. In concurrent requests, usage reporting suffered from read-modify-write race conditions when updating monthly token usage and spend totals.

---

## Decision

### 1. Unified Client Creation & Resolution Path
- **Consolidated Engine**: Both LangChain `BaseChatModel` and application `BaseProvider` (`AmazonBedrockProvider`) route through `ModelClientFactory` and `ModelResolver`.
- **Facade Delegation**: Legacy `ModelFactory.get_for_user` delegates directly to `ModelClientFactory.get_provider`.
- **Cached Runtime Boto3 Client**: `AmazonBedrockProvider` retains and reuses its `boto3.client("bedrock-runtime")` rather than rebuilding it on every invocation.

### 2. Zero DB Query & Zero Decryption on Cache Hit
- **Decoupled Metadata vs Secret Decryption**: `ModelResolver.get_config_metadata()` retrieves a lightweight, unencrypted configuration snapshot (`UserConfigMetadata`) cached with a short bounded TTL (`METADATA_TTL_SECONDS = 30.0s`).
- **Early Hit Short-Circuit**: When a client exists in `_CLIENT_CACHE` for the effective configuration key, it is returned immediately. PostgreSQL is NOT queried, and AWS secrets are NOT decrypted.
- **Cache Miss Decryption**: Credentials are decrypted strictly on cache miss (`ModelResolver.resolve_credentials`).

### 3. Effective Construction Key & Tenant Isolation
- **ClientCacheKey**: Keyed by `(client_type, user_id, config_version, region, model_id, temperature, max_tokens)`.
- **Tenant Isolation**: Keys strictly contain `user_id`; users never share client instances even if model and Region match.
- **Task Generalization**: Tasks with identical effective models and settings (e.g. interviewer and coding practice on Nova Lite) share the exact same client instance.

### 4. Explicit Consistency Guarantee & Cross-Worker Invalidation
- **Consistency Strategy**: Persisted configuration-version check with bounded staleness guarantee.
- **Local Invalidation (0 ms)**: `save_config` and `delete_credentials` increment `config_version` in PostgreSQL and immediately purge local cache entries via `clear_cache_for_user(user_id)`. Subsequent requests on the same worker immediately read the new version and decrypt updated credentials.
- **Cross-Worker Staleness Bound (<= 30s)**: Other worker processes in multi-replica deployments poll PostgreSQL on TTL expiry (`METADATA_TTL_SECONDS = 30.0s`). Because `ClientCacheKey` embeds `config_version`, any version bump triggers an automatic cache miss on the replica worker, which evicts the old client and initializes the new one.
- **Database Read Implications**:
  - Cache Hit within 30s window: 0 database lookups, 0 cryptographic operations.
  - Periodic Refresh: 1 lightweight indexed single-row SELECT query per active user every 30s.
  - Credential Rotation: 1 atomic SQL UPDATE to increment `config_version`, followed by 1 decryption operation upon the subsequent cache miss.

### 5. Bounded Cache with Idle Expiry & LRU Eviction
- **BoundedClientCache**: Hard capacity limit (default 128 clients) and idle TTL (default 300s / 5 minutes).
- **Eviction**: Automatically purges expired idle entries and applies least-recently-used (LRU) eviction when capacity is reached.
- **Process Memory Hygiene**: Explicitly documents that SDK clients hold credentials in process memory, mitigated by bounded cache size and idle eviction.

### 6. Atomic Usage Accounting
- **Atomic SQL Expressions**: `record_usage` uses `UPDATE provider_configs SET monthly_tokens_used = monthly_tokens_used + :tokens, ...` to eliminate race conditions under concurrent requests.
- **Pre-Inference Budget Checking**: Enforces monthly token and cost limits prior to invoking inference.

### 7. Explicit Error Mapping Without Silent Fallbacks
- **Typed Error Mapping**: `ClientError` codes (`UnrecognizedClientException`, `ExpiredTokenException`, `AccessDeniedException`, `ThrottlingException`, `ResourceNotFoundException`, `ValidationException`) map directly to typed `ProviderError` instances.
- **No Mock Degradation**: Production workflows fail closed with actionable error guidance instead of silently substituting mock models.

---

## Consequences & Trade-offs

### Positive
- Substantial latency reduction on inference turns by eliminating DB round-trips and cryptographic decryption on cache hits.
- Clear, mathematically bounded staleness window (<= 30s) across multi-worker architectures without requiring operational dependencies on Redis or pub/sub daemons.
- Hard bound on memory footprint preventing memory leaks or unbounded credential retention.
- Completely race-free usage and budget tracking under concurrent candidate turns.
- Clean architectural consolidation onto a single provider resolution stack.

### Trade-offs & Mitigations
- In multi-worker deployments without distributed pub/sub, credential updates may take up to 30 seconds to reflect on alternate workers. This is acceptable for credential rotations and mitigated by immediate (0ms) invalidation on the initiating worker.
