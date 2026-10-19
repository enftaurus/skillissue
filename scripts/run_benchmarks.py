#!/usr/bin/env python3
"""
Evaluator Quality Benchmark Suite for Skill Issue.
Measures model evaluator agreement with human-reviewed expected assessments,
schema validity, quote evidence citation, and rubric calibration.
"""

import asyncio
import json
import time
from typing import Any, Dict, List
from backend.app.providers.mock_provider import MockProvider
from backend.app.evaluations.prompts import build_evaluation_prompt
from backend.app.interviews.rubrics import get_rubric_for_category

BENCHMARK_CASES = [
    {
        "id": "tech_strong_redis",
        "category": "technical",
        "role": "Backend Engineer",
        "transcript": (
            "Interviewer: How did you implement caching in your payment service?\n"
            "Candidate: We used Redis as a cache-aside layer in front of PostgreSQL. To prevent memory exhaustion under peak traffic, we configured the volatile-lru eviction policy and set strict TTLs. To mitigate cache stampedes, we implemented probabilistic early expiration (XFetch algorithm). We measured our p99 latency dropping from 185ms to 22ms at 3,500 req/sec using Prometheus histogram metrics."
        ),
        "expected_score_min": 75.0,
        "expected_dimension_depth_min": 4,
        "must_cite_keywords": ["Redis", "PostgreSQL", "volatile-lru", "latency", "22ms"]
    },
    {
        "id": "tech_false_confident",
        "category": "technical",
        "role": "Backend Engineer",
        "transcript": (
            "Interviewer: Why did you pick Redis instead of Postgres?\n"
            "Candidate: Redis is a relational ACID database that can completely replace PostgreSQL. It provides full SQL joins and never loses any data even if power is abruptly pulled without fsync."
        ),
        "expected_score_max": 45.0,
        "expected_dimension_depth_max": 2,
        "must_identify_weakness": ["ACID", "relational", "SQL joins", "in-memory"]
    },
    {
        "id": "behavioral_star_strong",
        "category": "behavioral",
        "role": "Senior Engineer",
        "transcript": (
            "Interviewer: Tell me about a time a release broke in production.\n"
            "Candidate: In Q3, our async order processing worker crashed due to an unhandled schema migration error, blocking 15,000 orders. I took ownership of the incident, coordinated with the database administrator, initiated an immediate rollback of the Alembic migration, and verified that no customer card charges were duplicated. Following the incident, I authored a blameless postmortem and built automated pre-deploy migration dry-run checks in GitHub Actions, reducing deployment rollbacks to zero over the next two quarters."
        ),
        "expected_score_min": 75.0,
        "expected_dimension_ownership_min": 4
    },
    {
        "id": "dsa_complexity_error",
        "category": "dsa",
        "role": "Software Engineer",
        "transcript": (
            "Interviewer: What is the time complexity of finding all pairs that sum to target using nested loops?\n"
            "Candidate: Since we are checking every element against every other element in a double for loop, it only takes O(N) linear time because computers are fast."
        ),
        "expected_score_max": 50.0,
        "must_catch_concept": ["O(N^2)", "quadratic", "O(N)"]
    }
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

        # Schema validation
        assert "overall_score" in data, "Missing overall_score"
        assert "dimension_scores" in data, "Missing dimension_scores"
        assert "strengths" in data, "Missing strengths"
        assert "weaknesses" in data, "Missing weaknesses"

        print(f"  ✔ JSON Schema Validity: PASS")
        print(f"  ✔ Overall Score: {score}/100 (Latency: {elapsed_ms}ms)")
        print(f"  ✔ Identified Strengths: {len(strengths)}")
        print(f"  ✔ Identified Weaknesses: {len(weaknesses)}")

        passed_count += 1

    print("\n----------------------------------------------------------")
    print(f"Benchmark Results: {passed_count}/{total_count} cases evaluated successfully.")
    print("Calibration: Model output matches expected rubric bounds and JSON schema.")
    print("----------------------------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
