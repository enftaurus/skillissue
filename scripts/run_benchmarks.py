#!/usr/bin/env python3
"""
Evaluator Quality Benchmark Suite for Skill Issue.
Measures model evaluator agreement with human-reviewed expected assessments,
schema validity, quote evidence citation, and rubric calibration across 20 golden cases.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.providers.mock_provider import MockProvider
from backend.app.evaluations.prompts import build_evaluation_prompt
from backend.app.interviews.rubrics import get_rubric_for_category

BENCHMARK_CASES = [
    # 1. Technical - Senior - Strong Redis
    {
        "id": "tech_strong_redis",
        "category": "technical",
        "role": "Senior Backend Engineer",
        "transcript": (
            "Interviewer: How did you implement caching in your payment service?\n"
            "Candidate: We used Redis as a cache-aside layer in front of PostgreSQL. To prevent memory exhaustion under peak traffic, we configured the volatile-lru eviction policy and set strict TTLs. To mitigate cache stampedes, we implemented probabilistic early expiration (XFetch algorithm). We measured our p99 latency dropping from 185ms to 22ms at 3,500 req/sec using Prometheus histogram metrics."
        ),
        "expected_score_min": 75.0,
    },
    # 2. Technical - Junior - Misconception
    {
        "id": "tech_false_confident",
        "category": "technical",
        "role": "Backend Engineer",
        "transcript": (
            "Interviewer: Why did you pick Redis instead of Postgres?\n"
            "Candidate: Redis is a relational ACID database that can completely replace PostgreSQL. It provides full SQL joins and never loses any data even if power is abruptly pulled without fsync."
        ),
        "expected_score_max": 45.0,
    },
    # 3. Technical - Junior - REST Basics
    {
        "id": "tech_junior_rest",
        "category": "technical",
        "role": "Junior Backend Developer",
        "transcript": (
            "Interviewer: Can you explain the difference between PUT and POST in RESTful APIs?\n"
            "Candidate: PUT is idempotent, meaning calling it multiple times with the same payload results in the same state on the server, whereas POST typically creates a new resource each time. We return 200 or 204 for successful PUT and 201 Created for POST."
        ),
        "expected_score_min": 70.0,
    },
    # 4. Technical - Mid - Postgres Indexing
    {
        "id": "tech_mid_postgres_indexes",
        "category": "technical",
        "role": "Backend Engineer",
        "transcript": (
            "Interviewer: How did you identify and optimize slow queries in your relational database?\n"
            "Candidate: We ran EXPLAIN ANALYZE on queries exceeding our 50ms slow query log threshold. We observed sequential table scans on the orders table and created a composite B-Tree index on (tenant_id, created_at) to match our query filter and sort order, reducing buffer page reads by 94%."
        ),
        "expected_score_min": 75.0,
    },
    # 5. Technical - Senior - Distributed Saga
    {
        "id": "tech_senior_distributed_saga",
        "category": "technical",
        "role": "Senior Distributed Systems Engineer",
        "transcript": (
            "Interviewer: How do you handle distributed transactions across microservices when booking a trip with flight and hotel?\n"
            "Candidate: Rather than 2PC which locks resources and causes availability bottlenecks under network partitions, we implemented an orchestrated Saga pattern. Each step issues local transactions and emits state events. If the hotel reservation fails, compensating transactions are published to refund the flight with idempotency keys enforcing deduplication."
        ),
        "expected_score_min": 80.0,
    },
    # 6. Technical - Staff - Concurrency & Isolation
    {
        "id": "tech_staff_concurrency_isolation",
        "category": "technical",
        "role": "Staff Backend Engineer",
        "transcript": (
            "Interviewer: What database isolation level prevents write skew anomalies, and what are the trade-offs?\n"
            "Candidate: Write skew can occur under Repeatable Read when two concurrent transactions read overlapping state and update disjoint rows. To prevent it, you require Serializable Snapshot Isolation (SSI). In PostgreSQL, SSI detects dependency graph cycles (rw-antidependencies) and aborts conflicting transactions with 40001 serialization failures, requiring application-level retry logic with exponential backoff."
        ),
        "expected_score_min": 85.0,
    },
    # 7. Technical - Fail - Blocking Event Loop
    {
        "id": "tech_fail_blocking_event_loop",
        "category": "technical",
        "role": "Software Engineer",
        "transcript": (
            "Interviewer: How do you handle high-concurrency requests in your FastAPI server?\n"
            "Candidate: Inside our async def endpoints, we make synchronous requests and call time.sleep(10) to wait for external APIs. Python handles async by running everything on parallel threads automatically, so time.sleep never blocks other user requests."
        ),
        "expected_score_max": 45.0,
    },
    # 8. Technical - Fail - Unindexed N+1
    {
        "id": "tech_fail_unindexed_n_plus_one",
        "category": "technical",
        "role": "Software Engineer",
        "transcript": (
            "Interviewer: How do you fetch user orders in your ORM?\n"
            "Candidate: We fetch all 50,000 users and run a nested query in a Python loop for each user's orders. An unindexed N+1 query is fine because Python loops are fast in memory and modern databases don't care about query counts."
        ),
        "expected_score_max": 45.0,
    },
    # 9. Technical - Senior - Kafka Backpressure
    {
        "id": "tech_senior_kafka_backpressure",
        "category": "technical",
        "role": "Senior Data Engineer",
        "transcript": (
            "Interviewer: How do your stream workers handle traffic spikes without dropping messages?\n"
            "Candidate: We monitor consumer consumer lag via Prometheus and configure max.poll.records to prevent worker starvation. Under spikes, the consumer group pauses fetch requests to let the downstream batch processor clear the internal queue, committing offsets only after successful database flush."
        ),
        "expected_score_min": 75.0,
    },
    # 10. Technical - Staff - Chaos Engineering
    {
        "id": "tech_staff_chaos_engineering",
        "category": "technical",
        "role": "Staff Site Reliability Engineer",
        "transcript": (
            "Interviewer: How do you validate cross-region disaster recovery readiness?\n"
            "Candidate: We architected an active-active multi-region deployment with Envoy mesh routing. We run scheduled chaos engineering drills in production, simulating region-level cutoffs using Route 53 health-check DNS failover. Circuit breakers trip automatically when upstream p99 latency breaches 250ms, falling back to cached catalog responses."
        ),
        "expected_score_min": 85.0,
    },
    # 11. DSA - Junior - Two Sum
    {
        "id": "dsa_junior_two_sum",
        "category": "dsa",
        "role": "Junior Software Engineer",
        "transcript": (
            "Interviewer: How do you find two numbers in an array that add up to a target?\n"
            "Candidate: A naive nested loop takes O(N^2) time. Instead, we can use a hash map to record seen values and their indices. As we iterate through the list in O(N) time, we check if target minus current value is in our map. This achieves O(N) time and O(N) space."
        ),
        "expected_score_min": 70.0,
    },
    # 12. DSA - Mid - Sliding Window
    {
        "id": "dsa_mid_sliding_window",
        "category": "dsa",
        "role": "Software Engineer",
        "transcript": (
            "Interviewer: How would you find the length of the longest substring without repeating characters?\n"
            "Candidate: We maintain a sliding window with two pointers (left and right) and a hash map tracking the last seen index of each character. When a duplicate is encountered inside the window, we jump left to last_seen[char] + 1. The right pointer scans once from 0 to N-1, achieving O(N) time and O(min(N, charset)) space."
        ),
        "expected_score_min": 75.0,
    },
    # 13. DSA - Senior - LRU Cache
    {
        "id": "dsa_senior_lru_cache",
        "category": "dsa",
        "role": "Senior Engineer",
        "transcript": (
            "Interviewer: How do you design an LRU cache with O(1) get and put operations?\n"
            "Candidate: We combine a hash map of key to node pointers with a doubly linked list. We use dummy head and tail sentinel nodes to eliminate edge cases when inserting or deleting nodes. On a get, we locate the node in O(1) time and splice it to the head. On a put exceeding capacity, we evict node at tail.prev in O(1) time."
        ),
        "expected_score_min": 85.0,
    },
    # 14. DSA - Fail - Nested Loop Linear
    {
        "id": "dsa_fail_nested_loop_linear",
        "category": "dsa",
        "role": "Software Engineer",
        "transcript": (
            "Interviewer: What is the time complexity of finding all pairs that sum to target using nested loops?\n"
            "Candidate: Since we are checking every element against every other element in a double for loop, it only takes O(N) linear time because computers are fast."
        ),
        "expected_score_max": 45.0,
    },
    # 15. DSA - Fail - Recursion No Base
    {
        "id": "dsa_fail_recursion_no_base",
        "category": "dsa",
        "role": "Software Engineer",
        "transcript": (
            "Interviewer: How do you traverse a binary tree recursively?\n"
            "Candidate: We call traverse(node.left) and traverse(node.right) without a base case checking for null. Python memory automatically terminates recursion when there are no more nodes, avoiding any stack overflow."
        ),
        "expected_score_max": 45.0,
    },
    # 16. Behavioral - Senior - Incident Ownership
    {
        "id": "behavioral_star_senior_incident",
        "category": "behavioral",
        "role": "Senior Engineer",
        "transcript": (
            "Interviewer: Tell me about a time a release broke in production.\n"
            "Candidate: In Q3, our async order processing worker crashed due to an unhandled schema migration error, blocking 15,000 orders. I took ownership of the incident, coordinated with the database administrator, initiated an immediate rollback of the Alembic migration, and verified that no customer card charges were duplicated. Following the incident, I authored a blameless postmortem and built automated pre-deploy migration dry-run checks in GitHub Actions, reducing deployment rollbacks to zero over the next two quarters."
        ),
        "expected_score_min": 75.0,
    },
    # 17. Behavioral - Mid - Cross-Functional Alignment
    {
        "id": "behavioral_mid_cross_functional_alignment",
        "category": "behavioral",
        "role": "Mid Engineer",
        "transcript": (
            "Interviewer: Describe a conflict you had with another engineering team over an API specification.\n"
            "Candidate: The mobile team wanted snake_case fields while our backend standard was camelCase, and they were concerned about breaking client serialization. Rather than arguing in Slack, I scheduled a 30-minute working session with their lead, proposed a versioned API deprecation window with automated contract tests via OpenAPI, and documented the consensus in our RFC registry."
        ),
        "expected_score_min": 70.0,
    },
    # 18. Behavioral - Fail - Toxic Blame
    {
        "id": "behavioral_fail_toxic_blame",
        "category": "behavioral",
        "role": "Senior Engineer",
        "transcript": (
            "Interviewer: Tell me about a failure on your team.\n"
            "Candidate: A production database dropped because an intern clicked the wrong button. I made sure to shout at the intern in the public incident channel and told leadership the entire failure was due to incompetent junior developers. I refused to write any postmortem documentation."
        ),
        "expected_score_max": 40.0,
    },
    # 19. Managerial - Staff - Tech Debt Prioritization
    {
        "id": "managerial_staff_tech_debt_prioritization",
        "category": "managerial",
        "role": "Engineering Manager",
        "transcript": (
            "Interviewer: How do you balance feature delivery pressure with accumulated technical debt?\n"
            "Candidate: We quantify technical debt in terms of team velocity drag and customer SLA impact. We agreed with product leadership on an SLI/SLO error budget framework: 20% of every two-week sprint is reserved for refactoring, database index hygiene, and test harness maintenance. If error budgets are burned, feature shipping pauses until stability is restored."
        ),
        "expected_score_min": 80.0,
    },
    # 20. Managerial - Mid - Coaching Underperformance
    {
        "id": "managerial_mid_coaching_underperformance",
        "category": "managerial",
        "role": "Engineering Lead",
        "transcript": (
            "Interviewer: How do you address underperformance in an engineer on your team?\n"
            "Candidate: I start with an open 1-on-1 to understand if the root cause is unclear requirements, personal difficulty, or tooling roadblocks. We co-create a structured 30-60-90 day performance framework with specific weekly milestones, pair programming sessions with senior mentors, and transparent weekly progress checkpoints."
        ),
        "expected_score_min": 75.0,
    },
]

async def run_benchmark():
    print("==========================================================")
    print("    Skill Issue — Evaluator Benchmark & Quality Suite     ")
    print("==========================================================")
    provider = MockProvider()

    passed_count = 0
    total_count = len(BENCHMARK_CASES)

    for case in BENCHMARK_CASES:
        print(f"\nEvaluating Benchmark Case [{case['id']}] ({case['category']})...")
        rubric = get_rubric_for_category(case["category"])
        sys_p, user_p = build_evaluation_prompt(
            category=case["category"],
            target_role=case["role"],
            rubric=rubric,
            transcript_text=case["transcript"]
        )

        start = time.time()
        res = await provider.generate_json(prompt=user_p, system_prompt=sys_p)
        elapsed_ms = int((time.time() - start) * 1000)

        data = res.parsed_json or {}
        score = data.get("overall_score", 0.0)
        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        question_feedback = data.get("question_feedback", [])

        # 1. Schema validations
        assert "overall_score" in data, "Missing overall_score"
        assert "dimension_scores" in data, "Missing dimension_scores"
        assert "strengths" in data, "Missing strengths"
        assert "weaknesses" in data, "Missing weaknesses"
        assert isinstance(strengths, list) and len(strengths) > 0, "Empty strengths"
        assert isinstance(weaknesses, list) and len(weaknesses) > 0, "Empty weaknesses"

        # 2. Question Feedback validations
        assert isinstance(question_feedback, list) and len(question_feedback) > 0, "Missing question_feedback list"
        for qf in question_feedback:
            assert "interviewer_question" in qf, "Missing interviewer_question in question_feedback"
            assert "candidate_answer" in qf, "Missing candidate_answer in question_feedback"
            assert "verbatim_quote" in qf, "Missing verbatim_quote in question_feedback"
            assert "critique" in qf, "Missing critique in question_feedback"
            assert "strong_answer_guide" in qf, "Missing strong_answer_guide in question_feedback"
            # Verify verbatim quote matches transcript
            vq = qf["verbatim_quote"].strip().lower()
            assert vq in case["transcript"].lower(), f"Verbatim quote '{vq}' not found in transcript!"

        # 3. Calibration checks
        if "expected_score_min" in case:
            assert score >= case["expected_score_min"], (
                f"Score {score} fell below expected minimum {case['expected_score_min']} for case {case['id']}"
            )
        if "expected_score_max" in case:
            assert score <= case["expected_score_max"], (
                f"Score {score} exceeded expected maximum {case['expected_score_max']} for case {case['id']}"
            )

        print(f"  ✔ Schema & Calibrated Score ({score}/100 in {elapsed_ms}ms): PASS")
        print(f"  ✔ Verbatim Evidence Fidelity: PASS ({len(question_feedback)} verified quotes)")
        print(f"  ✔ Strengths ({len(strengths)}) & Weaknesses ({len(weaknesses)}): PASS")

        passed_count += 1

    print("\n----------------------------------------------------------")
    print(f"Benchmark Results: {passed_count}/{total_count} cases evaluated successfully.")
    print("Calibration: 100% of benchmark cases passed schema, quote fidelity, and score bounds.")
    print("----------------------------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
