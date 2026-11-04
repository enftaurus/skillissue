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
        sys_lower = (system_prompt or "").lower()
        last_user_message = ""
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "").lower()
                    break

        # Socratic Hint Generation
        if "hint level 1" in prompt_lower or "tier 1" in prompt_lower or ("hint" in prompt_lower and "level 1" in prompt_lower):
            text = "Consider what data structure enables constant-time O(1) lookups for previously seen elements instead of scanning the array repeatedly."
        elif "hint level 2" in prompt_lower or "tier 2" in prompt_lower or ("hint" in prompt_lower and "level 2" in prompt_lower):
            text = "Use a Hash Map or Two-Pointer approach. For each element, check if the required complement or state is already present in your map before inserting."
        elif "hint level 3" in prompt_lower or "tier 3" in prompt_lower or ("hint" in prompt_lower and "level 3" in prompt_lower):
            text = "Iterate through elements with index: check if target minus current value exists in seen dictionary. If found, return indices. Otherwise store value with current index."
        elif "hint" in prompt_lower:
            text = "Focus on the invariant: what information do you need at each step, and what data structure lets you check or update that in O(1) time?"
        # DSA Intro / Problem Presentation Turn
        elif "here is your question" in prompt_lower or "candidate just introduced themselves" in prompt_lower or ("dsa" in sys_lower and "introduce" in prompt_lower):
            ack = "Nice to meet you. "
            if "raja" in last_user_message or "raja babu" in last_user_message or "raja" in prompt_lower:
                ack = "Nice to meet you, Raja Babu. "
            if "dp" in last_user_message or "dynamic programming" in last_user_message or "overlapping" in last_user_message:
                ack += "Dynamic programming with overlapping subproblems and memoization gives a great dopamine hit when state transitions align cleanly—until space constraints bite. "
            elif "competitive" in last_user_message or "cp" in last_user_message:
                ack += "Competitive programming builds sharp time-complexity intuition under time pressure. "
            elif "graph" in last_user_message or "tree" in last_user_message:
                ack += "Graph theory and topological sorting are great—straightforward until you hit cyclic dependencies. "
            else:
                ack += "Appreciate the background introduction. "

            if "### " in prompt:
                prob_part = prompt.split("### ")[1]
                for stop_word in ["Before you start", "4. Ask them", "\n4. "]:
                    if stop_word in prob_part:
                        prob_part = prob_part.split(stop_word)[0].strip()
                problem_block = f"### {prob_part}".strip().rstrip("'\"")
            else:
                problem_block = (
                    "### Two Sum — Target Pair Index\n\n"
                    "Given an array of integers `nums` and an integer `target`, return the 0-indexed positions of the two numbers such that they add up to `target`.\n\n"
                    "Assume each input has exactly one solution, and you may not use the same element twice.\n\n"
                    "**Input Format:**\nFirst line: integer N. Second line: N space-separated integers. Third line: integer target.\n\n"
                    "**Output Format:**\nPrint two space-separated indices: i j\n\n"
                    "**Constraints:**\n- 2 <= N <= 10^4\n- -10^9 <= nums[i] <= 10^9\n- -10^9 <= target <= 10^9\n\n"
                    "**Sample Input:**\n```\n4\n2 7 11 15\n9\n```\n**Sample Output:**\n```\n0 1\n```"
                )

            text = (
                f"{ack}Now let's start today's session. Here is your question:\n\n"
                f"{problem_block}\n\n"
                "Before you start writing code, please walk me through your initial thoughts and the algorithmic approach you plan to follow, your target time and space complexity, and any edge cases you're considering."
            )
        # Adaptive follow-up simulation
        elif "redis" in last_user_message or "redis" in prompt_lower:

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

        # Explanation Check: Question Generation
        if "<candidate_code>" in prompt and ("write follow-up questions" in sys_lower or "one rationale" in prompt_lower or "one mutation" in prompt_lower):
            code_match = re.search(r"<candidate_code>(.*?)</candidate_code>", prompt, re.DOTALL)
            code_text = code_match.group(1) if code_match else ""
            tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", code_text)
            tokens = [t for t in tokens if t not in {"def", "class", "return", "import", "from", "for", "while", "if", "else", "elif", "in", "and", "or", "not"}]
            ref1 = tokens[0] if tokens else "solve"
            ref2 = tokens[1] if len(tokens) > 1 else ref1
            ref3 = tokens[2] if len(tokens) > 2 else ref2

            is_single = bool(re.search(r"write\s+1\s+question", prompt_lower))
            if is_single:
                questions = [
                    {
                        "type": "rationale",
                        "text": f"Why did you choose this implementation pattern around '{ref1}' instead of an alternative iterative approach?",
                        "code_reference": ref1
                    }
                ]
            else:
                questions = [
                    {
                        "type": "rationale",
                        "text": f"Why did you choose your specific approach and data structure around '{ref1}' rather than a named alternative?",
                        "code_reference": ref1
                    },
                    {
                        "type": "mutation",
                        "text": f"If the problem constraints were modified to allow duplicates or streaming input, what exact lines around '{ref2}' would change?",
                        "code_reference": ref2
                    },
                    {
                        "type": "behaviour",
                        "text": f"What is the time complexity and result of your logic around '{ref3}' on an empty or single-element input?",
                        "code_reference": ref3
                    }
                ]
            parsed = {"questions": questions}

        # Explanation Check: Judge Answers
        elif "question_evaluations" in prompt_lower or "evaluating candidate spoken or written answers against their submitted code" in sys_lower:
            is_mismatched = any(bad in prompt_lower for bad in [
                "i don't know", "dont know", "stole this", "copied this", "copied from", "magic", "no idea",
                "chatgpt", "fabricated", "hallucination", "someone else"
            ])
            # Find all Question N occurrences
            q_matches = re.findall(r"Question\s+(\d+)", prompt)
            unique_indices = sorted(list(set(int(x) for x in q_matches))) if q_matches else [0, 1, 2]
            q_evals = []
            for idx in unique_indices:
                if is_mismatched:
                    q_evals.append({
                        "question_index": idx,
                        "accuracy": 1,
                        "consistency": 1,
                        "depth": 1,
                        "evidence_quote": "Mismatched candidate explanation",
                        "code_reference": "solution",
                        "critique": "Candidate verbal explanation contradicted the algorithm implemented in code."
                    })
                else:
                    q_evals.append({
                        "question_index": idx,
                        "accuracy": 4,
                        "consistency": 4,
                        "depth": 3,
                        "evidence_quote": "Valid technical response explaining implementation mechanics",
                        "code_reference": "solve",
                        "critique": "Solid explanation matching implementation logic."
                    })

            parsed = {
                "question_evaluations": q_evals,
                "coaching_what_went_well": ["Demonstrated clear grasp of data structures and cycle detection"],
                "coaching_what_to_revisit": ["Review space complexity on deep recursion trees"]
            }

        # 1. Post-Interview Evaluation
        elif "<untrusted_candidate_transcript>" in prompt or "rubric" in sys_lower or "evaluat" in sys_lower:
            # Extract candidate lines from prompt if present
            candidate_lines = []
            for line in prompt.split("\n"):
                clean = line.strip()
                if clean.startswith("Candidate:"):
                    candidate_lines.append(clean.split("Candidate:", 1)[1].strip())


            first_cand_quote = candidate_lines[0] if candidate_lines else "We used Redis for caching to speed up user session lookups."
            first_sentence = first_cand_quote.split(".")[0] + "." if "." in first_cand_quote else first_cand_quote
            second_cand_quote = candidate_lines[1] if len(candidate_lines) > 1 else first_cand_quote
            second_sentence = second_cand_quote.split(".")[0] + "." if "." in second_cand_quote else second_cand_quote

            # Calibrate score and dimensions based on transcript signals
            is_flawed = any(k in prompt_lower for k in [
                "acid relational",
                "replace postgresql",
                "time.sleep",
                "computers are fast",
                "double for loop",
                "linear time because",
                "without a base case",
                "unindexed n+1",
                "dropped production table",
                "shout at",
                "shouted at",
                "blame the intern",
                "blamed the intern",
            ])
            is_exceptional = any(k in prompt_lower for k in [
                "xfetch",
                "saga",
                "idempotency keys",
                "isolation levels",
                "ssi",
                "sentinel nodes",
                "chaos engineering",
                "active-active",
                "error budgets",
                "blameless postmortem",
                "prometheus",
                "sliding window"
            ])


            if is_flawed:
                overall_score = 38.0
                dim_score = 1
                explanation_prefix = "Significant architectural misconception or flawed complexity analysis. "
                strengths = ["Communicates with confidence, though technical premises were incorrect."]
                weaknesses = [
                    "Fundamental misunderstanding of core principles or complexity guarantees.",
                    "Unable to correctly analyze failure scenarios or trade-offs."
                ]
            elif is_exceptional:
                overall_score = 88.5
                dim_score = 5
                explanation_prefix = "High-caliber engineering depth. Rigorous reasoning with explicit trade-offs and quantitative telemetry metrics. "
                strengths = [
                    "Staff-level mastery of failure modes, resilience patterns, and telemetry.",
                    "Precise explanation of distributed consistency and algorithmic trade-offs."
                ]
                weaknesses = [
                    "Could further articulate operational failure thresholds under regional network partitions."
                ]
            else:
                overall_score = 76.5
                dim_score = 4
                explanation_prefix = "Solid baseline engineering competency with minor gaps in operational edge cases. "
                strengths = [
                    "Direct and concise technical explanations without buzzword padding.",
                    "Demonstrated practical familiarity with primary frameworks and database tools."
                ]
                weaknesses = [
                    "Relies on unverified assertions of speed or reliability without citing quantitative latency distributions (p95/p99)."
                ]

            parsed = {
                "overall_score": overall_score,
                "dimension_scores": {
                    "technical_depth": {
                        "score": dim_score,
                        "max_score": 5,
                        "explanation": f"{explanation_prefix}Candidate addressed the system mechanisms.",
                        "evidence_quote": first_sentence
                    },
                    "system_design_tradeoffs": {
                        "score": max(1, dim_score - 1 if is_flawed else (dim_score if not is_exceptional else 4)),
                        "max_score": 5,
                        "explanation": f"{explanation_prefix}Evaluated boundary conditions and failure behavior.",
                        "evidence_quote": second_sentence
                    },
                    "communication_clarity": {
                        "score": 4 if not is_flawed else 3,
                        "max_score": 5,
                        "explanation": "Structured explanation without excessive conversational filler.",
                        "evidence_quote": first_sentence
                    },
                    "problem_solving_rigor": {
                        "score": dim_score,
                        "max_score": 5,
                        "explanation": f"{explanation_prefix}Methodical walk-through of the problem statement.",
                        "evidence_quote": second_sentence
                    }
                },
                "strengths": strengths,
                "weaknesses": weaknesses,
                "missing_concepts": [
                    "Distributed locks and mutex semantics in concurrent workers",
                    "Telemetry telemetry metrics (p95 latency, saturations, error budgets)"
                ],
                "evidence_excerpts": [
                    {"quote": first_sentence, "critique": "Key assertion from candidate's response."},
                    {"quote": second_sentence, "critique": "Follow-up explanation provided during the interview."}
                ],
                "question_feedback": [
                    {
                        "question_index": 1,
                        "interviewer_question": "Can you walk me through your technical approach and key decisions?",
                        "candidate_answer": first_cand_quote,
                        "verbatim_quote": first_sentence,
                        "critique": "Critique on technical depth and architectural assumptions." if not is_flawed else "Severe technical misconception cited directly in transcript.",
                        "strong_answer_guide": "Senior answers establish baseline metrics, trade-offs, and failure boundaries clearly.",
                        "targeted_resource": "Architecture & Engineering System Design Principles"
                    },
                    {
                        "question_index": 2,
                        "interviewer_question": "How do you handle system degradation or scale bottlenecks?",
                        "candidate_answer": second_cand_quote,
                        "verbatim_quote": second_sentence,
                        "critique": "Proactively address edge cases, backpressure, and graceful degradation.",
                        "strong_answer_guide": "Explain circuit breaker patterns, request coalescing, or exponential backoff with jitter.",
                        "targeted_resource": "Resilient Distributed Systems Engineering"
                    }
                ],
                "weakness_analysis": [
                    {
                        "topic": "PostgreSQL Partitioning",
                        "subtopic": "DDL Lock Mitigation",
                        "evidence": first_sentence,
                        "gap_explanation": "Understood declarative table partitioning syntax but omitted catalog locking behavior during partition attachment.",
                        "learning_objective": "Master PostgreSQL concurrent partition maintenance and query planner pruning invariants.",
                        "suggested_exercise": "Benchmark concurrent partition attachment under heavy write load using pgbench.",
                        "confidence": "high"
                    },
                    {
                        "topic": "Distributed System Observability",
                        "subtopic": "Latency Distributions",
                        "evidence": second_sentence,
                        "gap_explanation": "Relies on vague assertions of performance gains without citing quantitative percentiles (p95, p99) or instrumentation.",
                        "learning_objective": "Learn to instrument services with Prometheus histograms and interpret tail latency metrics under saturation.",
                        "suggested_exercise": "Configure a local service with OpenTelemetry and measure p99 latency during artificial lock contention.",
                        "confidence": "medium"
                    }
                ],
                "suggested_corrections": [
                    "Whenever claiming a performance win in an interview, state the metric: 'Reduced median latency from 140ms to 18ms under 2,000 req/sec'.",
                    "Proactively address failure modes: mention circuit breakers, timeouts, and fallback policies."
                ],
                "uncertainty_notes": [
                    "DSA algorithmic complexity was evaluated based on the provided transcript turn."
                ]
            }


        # 4. Planly Multi-Day Improvement Plan
        elif "<untrusted_evaluation_data>" in prompt_lower or "planly" in sys_lower or "daily practice routines" in sys_lower or "roadmap" in prompt_lower or "plan" in prompt_lower:
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

        # 3. Job Description Parsing
        elif "<raw_job_description>" in prompt or "job description" in prompt_lower or "extract skills" in prompt_lower:
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

        # 4. Resume Parsing
        elif "<raw_resume_text>" in prompt or "resume" in prompt_lower or "extract resume" in prompt_lower:
            parsed = {
                "detected_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Git", "Redis", "SQLAlchemy", "Linux"],
                "project_contexts": [
                    {"name": "Skill Issue Core API", "tech": "Python, FastAPI, Postgres", "summary": "Engineered modular interview prep engine with AES-256 credential encryption and sandbox isolation."}
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
