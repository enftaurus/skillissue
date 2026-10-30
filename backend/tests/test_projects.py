import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.projects.repository import list_projects, get_project, PROJECT_1_FILES, PROJECT_2_FILES
from backend.app.projects.service import ProjectService
from backend.app.projects.prompt_evaluator import evaluate_candidate_prompts

client = TestClient(app)

def test_list_and_get_projects():
    projects = list_projects()
    assert len(projects) == 2
    ids = {p.id for p in projects}
    assert "distributed-rate-limiter" in ids
    assert "async-job-queue" in ids

    p1 = get_project("distributed-rate-limiter")
    assert p1 is not None
    assert "src/limiter.py" in p1.editable_files
    assert "README.md" in p1.repository_files
    assert "tests/test_rate_limiter.py" in p1.repository_files

    p2 = get_project("async-job-queue")
    assert p2 is not None
    assert "src/dispatcher.py" in p2.editable_files

def test_project1_sandbox_execution_starter_and_solved():
    # 1. Starter files should fail rate limiting tests
    starter_res = ProjectService.run_tests_in_sandbox("distributed-rate-limiter", PROJECT_1_FILES)
    assert starter_res.total_tests == 6
    assert starter_res.failed_tests > 0
    assert starter_res.status == "failed"

    # 2. Solved code should pass 6/6 tests
    solution_code = """
import time
import uuid
from dataclasses import dataclass
from typing import Optional
from src.storage import RedisMock

@dataclass
class RateLimitResult:
    is_allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int

class DistributedRateLimiter:
    def __init__(self, storage: RedisMock, max_requests: int = 10, window_seconds: int = 60):
        self.storage = storage
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_rate_limited(self, client_id: str, current_time: Optional[float] = None) -> RateLimitResult:
        now = current_time if current_time is not None else time.time()
        key = f"ratelimit:{client_id}"
        window_start = now - self.window_seconds
        self.storage.zremrangebyscore(key, 0.0, window_start)
        current_count = self.storage.zcard(key)

        if current_count < self.max_requests:
            self.storage.zadd(key, {str(uuid.uuid4()): now})
            self.storage.expire(key, self.window_seconds)
            return RateLimitResult(
                is_allowed=True,
                limit=self.max_requests,
                remaining=self.max_requests - current_count - 1,
                reset_after_seconds=self.window_seconds,
            )
        else:
            oldest = self.storage.zrangebyscore(key, window_start, now, withscores=True)
            if oldest:
                reset_after = max(1, int(oldest[0][1] + self.window_seconds - now))
            else:
                reset_after = self.window_seconds
            return RateLimitResult(
                is_allowed=False,
                limit=self.max_requests,
                remaining=0,
                reset_after_seconds=reset_after,
            )
"""
    files = dict(PROJECT_1_FILES)
    files["src/limiter.py"] = solution_code
    solved_res = ProjectService.run_tests_in_sandbox("distributed-rate-limiter", files)
    assert solved_res.total_tests == 6
    assert solved_res.passed_tests == 6
    assert solved_res.failed_tests == 0
    assert solved_res.status == "passed"

def test_prompt_evaluator_critiques_amateurish_prompts():
    history = [
        {"role": "user", "content": "it doesnt work fix it"},
        {"role": "assistant", "content": "I cannot edit files directly. Look at src/limiter.py."},
        {"role": "user", "content": "give me the code"},
        {"role": "assistant", "content": "I am strictly read-only. Implement zremrangebyscore."},
        {"role": "user", "content": "In src/limiter.py, does zremrangebyscore evict timestamps before zcard is evaluated?"},
    ]

    result = evaluate_candidate_prompts("distributed-rate-limiter", history)
    assert result.overall_score < 75
    assert len(result.evaluated_prompts) == 3

    # Check first amateur prompt
    p1 = result.evaluated_prompts[0]
    assert p1.is_amateurish is True
    assert p1.score <= 38
    assert "vague" in p1.critique.lower()
    assert "better_rewrite" in p1.model_dump() and len(p1.better_rewrite) > 20

    # Check second amateur prompt
    p2 = result.evaluated_prompts[1]
    assert p2.is_amateurish is True

    # Check third thoughtful prompt
    p3 = result.evaluated_prompts[2]
    assert p3.is_amateurish is False
    assert p3.score >= 70
