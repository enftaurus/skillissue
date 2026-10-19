import json
import re
from typing import Any, Dict, List, Optional
from backend.app.providers.base import BaseProvider, ProviderResponse

class MockProvider(BaseProvider):
    """
    High-fidelity deterministic local provider for offline development,
    testing, and CI without requiring real AWS credentials or incurring costs.
    Generates realistic, dry, Gilfoyle-style questions, follow-ups, evaluations, and Planly tasks.
    """
    def __init__(self, model_id: str = "mock-qwen3-32b"):
        super().__init__(model_id)

    async def validate_credentials(self) -> bool:
        return True

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        # Determine conversational turn context
        history_len = len(conversation_history) if conversation_history else 0
        prompt_lower = prompt.lower()
        last_user_message = ""
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "").lower()
                    break

        # Adaptive follow-up simulation
        if "redis" in last_user_message or "redis" in prompt_lower:
            text = "You mentioned using Redis for caching. What specific eviction policy did you configure, and how did you verify that memory wouldn't be exhausted under peak throughput?"
        elif "fastapi" in last_user_message or "fastapi" in prompt_lower or "python" in last_user_message:
            text = "FastAPI handles concurrency with async event loops. Did your route handlers perform any blocking I/O or CPU-bound transformations that could block the main event loop thread?"
        elif "postgres" in last_user_message or "database" in last_user_message or "sql" in last_user_message:
            text = "When your queries started slowing down, what did the EXPLAIN ANALYZE show? Was it a sequential scan or index contention?"
        elif "kafka" in last_user_message or "queue" in last_user_message:
            text = "What was your consumer failure recovery strategy? If a downstream consumer dies mid-batch, did you risk duplicate processing or dropped events?"
        elif "faster" in last_user_message or "10x" in last_user_message or "improved" in last_user_message:
            text = "You said that made it faster. How exactly did you measure that latency delta, and what were your p95 and p99 figures?"
        elif history_len == 0:
            text = "Let's dive into your architecture. Looking at your background, pick one backend system you designed and explain the primary failure mode you had to engineer around."
        elif history_len <= 3:
            text = "That's a clean high-level view. Now let's get into the concrete trade-offs: what was the single biggest bottleneck you ran into, and why not choose an off-the-shelf message queue?"
        elif history_len <= 6:
            text = "What would happen if the upstream service starts returning 504 Gateway Timeouts under a traffic surge? How does your client back off?"
        else:
            text = "Understood. Let's wrap up with one operational question: if you received an alert at 3 AM that your service error rate spiked to 15%, what are the first three telemetry metrics you would pull up?"

        in_tokens = max(50, len(prompt.split()) * 2)
        out_tokens = max(30, len(text.split()) * 2)

        return ProviderResponse(
            text=text,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            estimated_cost_usd=0.0,
            model_id=self.model_id
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        prompt_lower = prompt.lower()
        sys_lower = (system_prompt or "").lower()

        # 1. Job Description Parsing
        if "job description" in prompt_lower or "extract skills" in prompt_lower or "requirements" in prompt_lower:
            parsed = {
                "role": "Backend Software Engineer",
                "extracted_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Distributed Systems", "REST APIs"],
                "extracted_requirements": [
                    "3+ years experience building concurrent backend services in Python or Go",
                    "Deep understanding of relational database schema design, indexing, and query optimization in PostgreSQL",
                    "Practical experience deploying containerized microservices in Docker/Kubernetes",
                    "Solid grasp of asynchronous programming, message queues, and caching strategies"
                ],
                "recommended_focus": "Distributed system reliability, concurrency, and database query optimization."
            }

        # 2. Resume Parsing
        elif "resume" in prompt_lower or "extract resume" in prompt_lower:
            parsed = {
                "detected_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Git", "Redis", "SQLAlchemy", "Linux"],
                "project_contexts": [
                    {"name": "Skill Issue Core API", "tech": "Python, FastAPI, Postgres", "summary": "Engineered modular interview prep engine with AES-256 credential encryption and sandbox isolation."}
                ]
            }

        # 3. Post-Interview Evaluation
        elif "evaluat" in prompt_lower or "rubric" in prompt_lower or "score" in sys_lower:
            parsed = {
                "overall_score": 78.5,
                "dimension_scores": {
                    "technical_depth": {
                        "score": 4,
                        "max_score": 5,
                        "explanation": "Demonstrated sound understanding of async I/O and database transactions, though lacked concrete p99 latency measurement methodology.",
                        "evidence_quote": "We used Redis for caching to speed up user session lookups."
                    },
                    "system_design_tradeoffs": {
                        "score": 3,
                        "max_score": 5,
                        "explanation": "Identified cache invalidation as a risk, but did not address network partition or failover modes.",
                        "evidence_quote": "If the cache goes down we just fall back to Postgres queries."
                    },
                    "communication_clarity": {
                        "score": 4,
                        "max_score": 5,
                        "explanation": "Direct and concise responses without filler words. Stayed focused on the technical mechanisms.",
                        "evidence_quote": "We configured EXPLAIN ANALYZE to identify unindexed foreign key lookups."
                    },
                    "problem_solving_rigor": {
                        "score": 4,
                        "max_score": 5,
                        "explanation": "Methodical debugging approach when asked about concurrency contention.",
                        "evidence_quote": "We isolated the blocking database transaction with connection pool telemetry."
                    }
                },
                "strengths": [
                    "Strong mental model of asynchronous programming and database indexing fundamentals.",
                    "Comfortable acknowledging boundaries of design decisions rather than bluffing.",
                    "Direct communication style suited for senior engineering discussions."
                ],
                "weaknesses": [
                    "Relies on vague claims of 'speed improvements' without citing quantitative benchmark numbers (p95/p99 latency, RPS).",
                    "Overlooked cache stampede risks when cache keys expire under heavy traffic spikes.",
                    "Did not specify worker health check failure thresholds."
                ],
                "missing_concepts": [
                    "Cache-aside pattern vs write-through caching trade-offs",
                    "Distributed locks and mutex semantics in concurrent workers",
                    "Telemetry telemetry metrics (p95 latency, saturations, error budgets)"
                ],
                "evidence_excerpts": [
                    {"quote": "We added Redis and it made everything 10x faster.", "critique": "Unverified quantitative claim; could not explain benchmark baseline."},
                    {"quote": "We used EXPLAIN ANALYZE to spot the sequential scan.", "critique": "Solid concrete debugging methodology."}
                ],
                "suggested_corrections": [
                    "Whenever claiming a performance win in an interview, state the metric: 'Reduced median latency from 140ms to 18ms under 2,000 req/sec'.",
                    "Proactively address cache failure modes: mention circuit breakers, stale-while-revalidate, or rate limiters."
                ],
                "uncertainty_notes": [
                    "DSA algorithmic complexity was not tested in this round; recommend a dedicated DSA session."
                ]
            }

        # 4. Planly Multi-Day Improvement Plan
        elif "plan" in prompt_lower or "improvement" in prompt_lower or "planly" in sys_lower:
            parsed = {
                "title": "7-Day High-Throughput Reliability & Systems Sprint",
                "target_role": "Backend Software Engineer",
                "daily_study_minutes": 45,
                "total_days": 7,
                "tasks": [
                    {
                        "day_number": 1,
                        "title": "Mastering Database Query Execution & Indexing",
                        "description": "Analyze EXPLAIN ANALYZE output for B-Tree vs Hash indexes, composite indexes, and index selectivity.",
                        "task_type": "concept",
                        "estimated_minutes": 40,
                        "external_resources": [
                            {"title": "PostgreSQL Official Documentation: Using EXPLAIN", "url": "https://www.postgresql.org/docs/current/using-explain.html", "type": "documentation"},
                            {"title": "Use The Index, Luke: SQL Indexing Guide", "url": "https://use-the-index-luke.com/", "type": "guide"}
                        ]
                    },
                    {
                        "day_number": 2,
                        "title": "Caching Strategies & The Cache Stampede Problem",
                        "description": "Implement a cache-aside wrapper in Python with probabilistic early expiration (XFetch algorithm).",
                        "task_type": "coding",
                        "estimated_minutes": 45,
                        "external_resources": [
                            {"title": "Optimal Probabilistic Cache Stampede Prevention (Vattani et al.)", "url": "https://en.wikipedia.org/wiki/Cache_stampede", "type": "paper"}
                        ]
                    },
                    {
                        "day_number": 3,
                        "title": "Quantitative Performance Metrics (p50, p95, p99)",
                        "description": "Learn why averages deceive and practice calculating percentile distributions on synthetic latency logs.",
                        "task_type": "practice",
                        "estimated_minutes": 35,
                        "external_resources": [
                            {"title": "Everything You Know About Latency Is Wrong (Gil Tene)", "url": "https://www.youtube.com/watch?v=lJ8ydIuPFeU", "type": "video"}
                        ]
                    },
                    {
                        "day_number": 4,
                        "title": "Asynchronous Concurrency & Event Loop Starvation",
                        "description": "Write a benchmark demonstrating how `time.sleep()` freezes an asyncio server vs `asyncio.sleep()`.",
                        "task_type": "coding",
                        "estimated_minutes": 45,
                        "external_resources": [
                            {"title": "Python asyncio Internals & Coroutine Scheduling", "url": "https://docs.python.org/3/library/asyncio.html", "type": "documentation"}
                        ]
                    },
                    {
                        "day_number": 5,
                        "title": "Distributed Transactions & Idempotency",
                        "description": "Design an idempotent payment webhook receiver using PostgreSQL unique constraints and idempotency keys.",
                        "task_type": "practice",
                        "estimated_minutes": 45,
                        "external_resources": [
                            {"title": "Stripe Guide to Designing Robust and Idempotent APIs", "url": "https://stripe.com/blog/idempotency", "type": "guide"}
                        ]
                    },
                    {
                        "day_number": 6,
                        "title": "Mock Technical Interview Dry Run",
                        "description": "Perform an adaptive 15-minute mock interview focusing specifically on caching and database bottlenecks.",
                        "task_type": "practice",
                        "estimated_minutes": 30,
                        "external_resources": []
                    },
                    {
                        "day_number": 7,
                        "title": "Comparable Reassessment Session",
                        "description": "Complete a full reassessment interview to measure your score delta against your baseline rubric.",
                        "task_type": "reassessment",
                        "estimated_minutes": 30,
                        "external_resources": []
                    }
                ]
            }

        # Default fallback JSON
        else:
            parsed = {
                "status": "success",
                "message": "Processed successfully by Skill Issue Mock Provider",
                "model": self.model_id
            }

        json_str = json.dumps(parsed, indent=2)
        in_tokens = max(50, len(prompt.split()) * 2)
        out_tokens = max(100, len(json_str.split()) * 2)

        return ProviderResponse(
            text=json_str,
            parsed_json=parsed,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            estimated_cost_usd=0.0,
            model_id=self.model_id
        )
