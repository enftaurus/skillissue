# ADR 0009: Recommended Model Lineup & Task-Based Routing

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** Following the BYOC strategy (ADR 0003), a concrete model lineup is needed to provide clear recommendations, accurate pricing, and targeted task routing without vendor lock-in.
- **Decision:** Adopt the following 4-tier model lineup on Amazon Bedrock:
  1. **Qwen3 32B** (`qwen.qwen3-32b-instruct-v1:0`): Primary default interview model (\$0.1545 in / \$0.618 out per 1M tokens). Use for conversational questions, adaptive follow-ups, system design, and first-pass evaluation.
  2. **Qwen3 Coder 30B A3B** (`qwen.qwen3-coder-30b-a3b-v1:0`): Coding specialist (\$0.1545 in / \$0.618 out per 1M tokens). Use for code explanations, debugging hints, complexity analysis, and implementation follow-ups.
  3. **Qwen3 Next 80B A3B** (`qwen.qwen3-next-80b-a3b-v1:0`): Stronger-model comparison (\$0.18 in / \$1.41 out per 1M tokens). Benchmark for nuanced evaluations, difficult trade-offs, and complex system design depth.
  4. **Kimi K3** (`moonshot.kimi-k3-v1:0`): Premium reasoning & vision experiment (\$3.30 in / \$16.50 out per 1M tokens). Specialized for complex architecture diagram analysis or screenshots.
  5. **Mock Qwen3 32B** (`mock-qwen3-32b`): Free local mock engine for offline development and CI.
- **Alternatives Considered:**
  - *Claude 3.5 Sonnet as default*: Rejected as primary default due to higher token costs (\$3.00/\$15.00 vs \$0.1545/\$0.618 for Qwen3 32B), which would deplete the \$20 student credit budget roughly 20x faster without proportional conversational benefit for routine mock rounds.
- **Rationale:** Qwen3 32B delivers superior economics (under \$0.005 per complete interview session) while matching human interviewer nuance and technical accuracy.
- **Consequences:** The application-owned model factory routes coding follow-up questions to `Qwen3 Coder 30B A3B` and conversational questions to `Qwen3 32B` while allowing the student to override the model in provider settings.
- **Related Requirements:** Master Prompt Section 7; Product Owner Explicit Direction.
