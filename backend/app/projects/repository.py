from typing import Dict, List, Optional
from backend.app.projects.schemas import ProjectSummary, ProjectDetail

PROJECT_1_FILES: Dict[str, str] = {
    "README.md": """# Distributed Rate Limiter Middleware

## Objective
Design and implement a multi-tenant **Distributed Rate Limiter** middleware in Python.
Your rate limiter protects microservice APIs from denial of service and resource starvation by enforcing per-client quotas against an in-memory Redis datastore.

## Core Requirements

### 1. Multi-Tenant Tracking
- Each client is uniquely identified by `client_id` (e.g. an API Key or client IP).
- Quotas must be isolated per client: Client A consuming their quota must NEVER block Client B.

### 2. Sliding Window Counter / Log Algorithm
- Implement the sliding window algorithm using Redis Sorted Sets (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`):
  1. The Redis key for each client is `ratelimit:{client_id}`.
  2. On each incoming request at Unix timestamp `now`:
     - Remove all recorded timestamps older than `now - window_seconds` via `zremrangebyscore`.
     - Count the number of active requests in the current sliding window using `zcard`.
     - If active requests `< max_requests`:
       - Record the new request timestamp using `zadd(key, {request_id: now})`.
       - Refresh key expiration with `expire(key, window_seconds)`.
       - Allow request with `is_allowed = True`.
     - Else:
       - Deny request with `is_allowed = False`.
  3. Calculate:
     - `remaining`: `max(0, max_requests - current_count)`
     - `reset_after_seconds`: time in seconds until the oldest request in the window expires.

### 3. File Layout
- `src/storage.py`: Thread-safe mock implementation of Redis with Sorted Set operations. **[Read-Only]**
- `src/limiter.py`: The `DistributedRateLimiter` class. **[EDIT THIS FILE]**
- `src/server.py`: API middleware layer calculating `X-RateLimit-*` headers. **[Read-Only]**
- `tests/test_rate_limiter.py`: Automated CI/CD test suite. **[Read-Only]**

## Verification
Run tests using the CI/CD test runner button or:
```bash
pytest -v --tb=short tests/
```
""",
    "src/storage.py": '''"""
Thread-safe in-memory Redis simulation supporting Sorted Set operations.
"""
import time
import threading
from typing import Dict, List, Optional, Any, Tuple

class RedisMock:
    def __init__(self):
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._sorted_sets: Dict[str, Dict[str, float]] = {}  # key -> {member: score}
        self._expirations: Dict[str, float] = {}

    def _purge_if_expired(self, key: str) -> None:
        if key in self._expirations:
            if time.time() > self._expirations[key]:
                self._data.pop(key, None)
                self._sorted_sets.pop(key, None)
                self._expirations.pop(key, None)

    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add members with scores to a sorted set."""
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._sorted_sets:
                self._sorted_sets[key] = {}
            added = 0
            for member, score in mapping.items():
                if member not in self._sorted_sets[key]:
                    added += 1
                self._sorted_sets[key][member] = float(score)
            return added

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """Remove members in sorted set whose score is between min_score and max_score inclusive."""
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._sorted_sets:
                return 0
            zset = self._sorted_sets[key]
            to_remove = [
                m for m, s in zset.items() if min_score <= s <= max_score
            ]
            for m in to_remove:
                del zset[m]
            return len(to_remove)

    def zcard(self, key: str) -> int:
        """Return the number of members in the sorted set."""
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._sorted_sets:
                return 0
            return len(self._sorted_sets[key])

    def zrangebyscore(self, key: str, min_score: float, max_score: float, withscores: bool = False) -> List[Any]:
        """Return members with scores between min_score and max_score."""
        with self._lock:
            self._purge_if_expired(key)
            if key not in self._sorted_sets:
                return []
            items = sorted(self._sorted_sets[key].items(), key=lambda x: x[1])
            filtered = [(m, s) for m, s in items if min_score <= s <= max_score]
            if withscores:
                return filtered
            return [m for m, _ in filtered]

    def expire(self, key: str, seconds: int) -> bool:
        """Set a timeout on key in seconds."""
        with self._lock:
            if key in self._data or key in self._sorted_sets:
                self._expirations[key] = time.time() + seconds
                return True
            return False

    def ttl(self, key: str) -> int:
        """Get remaining time to live in seconds."""
        with self._lock:
            if key not in self._expirations:
                return -1
            rem = int(self._expirations[key] - time.time())
            return max(0, rem)

    def flushall(self) -> None:
        """Clear all keys in datastore."""
        with self._lock:
            self._data.clear()
            self._sorted_sets.clear()
            self._expirations.clear()
''',
    "src/limiter.py": '''"""
Distributed Rate Limiter implementation.
Candidates: Complete the implementation of `is_rate_limited` using sliding window logic.
"""
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
    """
    Multi-tenant Sliding Window Distributed Rate Limiter backed by Redis.
    """
    def __init__(self, storage: RedisMock, max_requests: int = 10, window_seconds: int = 60):
        self.storage = storage
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_rate_limited(self, client_id: str, current_time: Optional[float] = None) -> RateLimitResult:
        """
        Evaluate whether a request from client_id is permitted under the sliding window quota.

        Args:
            client_id: Unique identifier for the client (e.g. IP or API key)
            current_time: Optional timestamp override for deterministic testing

        Returns:
            RateLimitResult containing:
            - is_allowed: True if request is under limit, False if limit exceeded
            - limit: Total allowed requests per window
            - remaining: Number of remaining allowed requests in current window
            - reset_after_seconds: Seconds until window frees up capacity
        """
        now = current_time if current_time is not None else time.time()
        key = f"ratelimit:{client_id}"

        # TODO: Implement the Sliding Window Counter algorithm:
        # 1. Calculate window start: window_start = now - self.window_seconds
        # 2. Prune old records from sorted set: self.storage.zremrangebyscore(key, 0.0, window_start)
        # 3. Query current active requests: current_count = self.storage.zcard(key)
        # 4. If current_count < self.max_requests:
        #      - Add current request timestamp: self.storage.zadd(key, {str(uuid.uuid4()): now})
        #      - Refresh key expiration: self.storage.expire(key, self.window_seconds)
        #      - Return RateLimitResult with is_allowed=True, remaining=(self.max_requests - current_count - 1)
        # 5. Else:
        #      - Find the oldest request timestamp in the window to compute reset_after_seconds
        #      - Return RateLimitResult with is_allowed=False, remaining=0

        # Starter stub (Permits all requests - fails rate limiting tests!)
        return RateLimitResult(
            is_allowed=True,
            limit=self.max_requests,
            remaining=self.max_requests,
            reset_after_seconds=self.window_seconds,
        )
''',
    "src/server.py": '''"""
FastAPI / ASGI HTTP middleware integration for DistributedRateLimiter.
"""
from typing import Dict, Any, Tuple
from src.limiter import DistributedRateLimiter, RateLimitResult

class RateLimitMiddleware:
    def __init__(self, limiter: DistributedRateLimiter):
        self.limiter = limiter

    def handle_request(self, client_id: str) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
        """
        Simulates handling an HTTP request and generating rate limit headers.
        Returns: (http_status_code, headers_dict, json_body)
        """
        res: RateLimitResult = self.limiter.is_rate_limited(client_id)
        headers = {
            "X-RateLimit-Limit": str(res.limit),
            "X-RateLimit-Remaining": str(res.remaining),
            "X-RateLimit-Reset": str(res.reset_after_seconds),
        }

        if not res.is_allowed:
            headers["Retry-After"] = str(res.reset_after_seconds)
            return (
                429,
                headers,
                {"error": "Too Many Requests", "retry_after": res.reset_after_seconds}
            )

        return (200, headers, {"status": "ok", "message": "Request processed"})
''',
    "tests/test_rate_limiter.py": '''"""
Automated CI/CD Test Suite for Distributed Rate Limiter.
"""
import time
import pytest
from src.storage import RedisMock
from src.limiter import DistributedRateLimiter
from src.server import RateLimitMiddleware

@pytest.fixture
def storage():
    return RedisMock()

@pytest.fixture
def limiter(storage):
    # 5 requests per 10 seconds window
    return DistributedRateLimiter(storage=storage, max_requests=5, window_seconds=10)

def test_allows_requests_under_limit(limiter):
    """Verify that requests below capacity are allowed and remaining count decrements."""
    t0 = 1000.0
    for i in range(5):
        result = limiter.is_rate_limited("client_alpha", current_time=t0 + i * 0.1)
        assert result.is_allowed is True, f"Request {i+1} should be allowed"
        assert result.limit == 5
        assert result.remaining == 5 - (i + 1)

def test_blocks_requests_exceeding_limit(limiter):
    """Verify that 6th request within window is rejected with is_allowed=False and remaining=0."""
    t0 = 2000.0
    for i in range(5):
        res = limiter.is_rate_limited("client_beta", current_time=t0 + i * 0.1)
        assert res.is_allowed is True

    # 6th request must breach limit
    excess = limiter.is_rate_limited("client_beta", current_time=t0 + 1.0)
    assert excess.is_allowed is False
    assert excess.remaining == 0
    assert excess.reset_after_seconds > 0

def test_multi_tenant_isolation(limiter):
    """Ensure clients do not interfere with each other's rate limits."""
    t0 = 3000.0
    # Client 1 exhausts their limit
    for _ in range(5):
        limiter.is_rate_limited("tenant_1", current_time=t0)
    
    assert limiter.is_rate_limited("tenant_1", current_time=t0).is_allowed is False

    # Client 2 should still have full quota
    res_tenant_2 = limiter.is_rate_limited("tenant_2", current_time=t0)
    assert res_tenant_2.is_allowed is True
    assert res_tenant_2.remaining == 4

def test_rate_limit_headers_calculation(limiter):
    """Verify HTTP middleware returns accurate X-RateLimit-* and Retry-After headers."""
    middleware = RateLimitMiddleware(limiter)
    
    # 1st request -> 200 OK
    code, headers, body = middleware.handle_request("web_client")
    assert code == 200
    assert headers["X-RateLimit-Limit"] == "5"
    assert headers["X-RateLimit-Remaining"] == "4"

    # Exhaust remaining 4
    for _ in range(4):
        middleware.handle_request("web_client")

    # Next request -> 429 Too Many Requests
    code_429, headers_429, body_429 = middleware.handle_request("web_client")
    assert code_429 == 429
    assert headers_429["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in headers_429
    assert body_429["error"] == "Too Many Requests"

def test_sliding_window_expiration(limiter):
    """Verify that after the window elapses, the client's quota is replenished."""
    t0 = 4000.0
    # Exhaust 5 requests at t0
    for _ in range(5):
        limiter.is_rate_limited("user_gamma", current_time=t0)

    assert limiter.is_rate_limited("user_gamma", current_time=t0 + 1.0).is_allowed is False

    # Advance time past window (10 seconds)
    t_after = t0 + 11.0
    replenished = limiter.is_rate_limited("user_gamma", current_time=t_after)
    assert replenished.is_allowed is True
    assert replenished.remaining == 4

def test_burst_traffic_concurrency(limiter):
    """Verify rapid burst of requests within same millisecond are capped at limit."""
    t_burst = 5000.123
    results = [limiter.is_rate_limited("burst_client", current_time=t_burst) for _ in range(10)]
    
    allowed = sum(1 for r in results if r.is_allowed)
    denied = sum(1 for r in results if not r.is_allowed)
    assert allowed == 5
    assert denied == 5
'''
}

PROJECT_2_FILES: Dict[str, str] = {
    "README.md": """# Async Job Queue with Priority & Dead-Letter Retries

## Objective
Extend an existing asynchronous task queue engine (`TaskDispatcher`).
The starter codebase contains basic FIFO queue processing. Your mission is to add production-grade reliability features:

## Core Requirements

### 1. Priority Scheduling
- Tasks have three priority tiers defined in `src/models.py`:
  - `TaskPriority.HIGH` (value 1)
  - `TaskPriority.NORMAL` (value 2)
  - `TaskPriority.LOW` (value 3)
- When `get_next_task()` is called, higher-priority tasks MUST always be dispatched before lower-priority tasks.
- If multiple tasks share the same priority, maintain FIFO order (earliest enqueued first).

### 2. Exponential Backoff Calculation
- When a task fails, calculate the retry delay using exponential backoff:
  ```
  delay = task.base_delay * (2 ** task.retry_count)
  ```
- Example: with `base_delay = 2.0`:
  - 1st retry (retry_count = 0 before increment): `2.0 * (2 ** 0) = 2.0s`
  - 2nd retry (retry_count = 1): `2.0 * (2 ** 1) = 4.0s`
  - 3rd retry (retry_count = 2): `2.0 * (2 ** 2) = 8.0s`

### 3. Maximum Retries & Dead-Letter Queue (DLQ)
- Each task has `max_retries` (default 3).
- In `handle_failure(task, error)`:
  - If `task.retry_count < task.max_retries`:
    - Increment `task.retry_count += 1`
    - Update `task.status = TaskStatus.RETRYING`
    - Re-enqueue the task for subsequent execution
  - If `task.retry_count >= task.max_retries`:
    - Set `task.status = TaskStatus.DEAD_LETTER`
    - Append to `dispatcher.dead_letter_queue`
    - Invoke the registered `dead_letter_hook` callback

## File Layout
- `src/models.py`: Task dataclass, TaskStatus, and TaskPriority enums. **[Read-Only]**
- `src/hooks.py`: DeadLetterHook interface and audit logger. **[Read-Only]**
- `src/dispatcher.py`: The `TaskDispatcher` class. **[EDIT THIS FILE]**
- `tests/test_dispatcher.py`: Automated CI/CD test suite. **[Read-Only]**

## Verification
Run tests using the CI/CD test runner button or:
```bash
pytest -v --tb=short tests/
```
""",
    "src/models.py": '''"""
Task data models and status enums.
"""
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Dict

class TaskPriority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"

@dataclass
class Task:
    id: str
    name: str
    fn: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    max_retries: int = 3
    retry_count: int = 0
    base_delay: float = 1.0
    last_error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    sequence_id: int = 0
''',
    "src/hooks.py": '''"""
Failure hooks and Dead-Letter Queue audit observers.
"""
from typing import Protocol, List, Tuple
from src.models import Task

class DeadLetterHook(Protocol):
    def on_task_dead_letter(self, task: Task, error: Exception) -> None:
        ...

class InMemoryAuditHook:
    """Records dead-lettered tasks for alerting and forensic auditing."""
    def __init__(self):
        self.dead_letters: List[Tuple[Task, str]] = []

    def on_task_dead_letter(self, task: Task, error: Exception) -> None:
        self.dead_letters.append((task, str(error)))
''',
    "src/dispatcher.py": '''"""
Task Queue Dispatcher implementation.
Candidates: Implement priority scheduling, exponential backoff, and DLQ handling.
"""
import time
from typing import List, Optional, Callable
from src.models import Task, TaskStatus, TaskPriority
from src.hooks import DeadLetterHook

class TaskDispatcher:
    """
    Background Task Dispatcher with Priority Queuing, Exponential Backoff, and Dead-Letter routing.
    """
    def __init__(self, dead_letter_hook: Optional[DeadLetterHook] = None):
        self.dead_letter_hook = dead_letter_hook
        self.queue: List[Task] = []
        self.dead_letter_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self._seq = 0

    def enqueue(self, task: Task) -> None:
        """Enqueue a new or retrying task."""
        self._seq += 1
        task.sequence_id = self._seq
        self.queue.append(task)

    def get_next_task(self) -> Optional[Task]:
        """
        Retrieve and remove the highest priority task ready to execute.
        - Higher priority (HIGH < NORMAL < LOW) executes first.
        - Same priority follows FIFO sequence_id ordering.
        """
        if not self.queue:
            return None

        # TODO: Implement priority ordering!
        # Sort queue so that:
        # 1. task.priority.value is lowest (HIGH=1 comes before LOW=3)
        # 2. task.sequence_id is lowest (FIFO tie-breaker)
        # Currently just pops FIFO from the front:
        return self.queue.pop(0)

    def calculate_backoff(self, task: Task) -> float:
        """
        Calculate backoff delay in seconds: base_delay * (2 ** retry_count).
        """
        # TODO: Implement exponential backoff calculation
        return 0.0

    def handle_failure(self, task: Task, error: Exception) -> None:
        """
        Handle task execution error.
        - If retry_count < max_retries:
            - Increment retry_count
            - Set status to TaskStatus.RETRYING
            - Record last_error string
            - Re-enqueue task
        - If retries exhausted (retry_count >= max_retries):
            - Set status to TaskStatus.DEAD_LETTER
            - Record last_error string
            - Add to dead_letter_queue
            - Call dead_letter_hook.on_task_dead_letter(task, error) if hook provided
        """
        # TODO: Implement retry vs dead-letter logic
        pass

    def run_next_task(self) -> Optional[Task]:
        """Runs the next eligible task synchronously, handling success and failure."""
        task = self.get_next_task()
        if not task:
            return None

        task.status = TaskStatus.RUNNING
        try:
            task.fn(*task.args, **task.kwargs)
            task.status = TaskStatus.COMPLETED
            self.completed_tasks.append(task)
        except Exception as e:
            self.handle_failure(task, e)

        return task
''',
    "tests/test_dispatcher.py": '''"""
Automated CI/CD Test Suite for Async Job Queue.
"""
import pytest
from src.models import Task, TaskStatus, TaskPriority
from src.hooks import InMemoryAuditHook
from src.dispatcher import TaskDispatcher

def dummy_success():
    return "ok"

def dummy_fail():
    raise RuntimeError("Permanent connection failure")

def test_fifo_order_for_same_priority():
    """Tasks with identical priority should execute in FIFO order."""
    dispatcher = TaskDispatcher()
    t1 = Task(id="t1", name="job1", fn=dummy_success, priority=TaskPriority.NORMAL)
    t2 = Task(id="t2", name="job2", fn=dummy_success, priority=TaskPriority.NORMAL)
    t3 = Task(id="t3", name="job3", fn=dummy_success, priority=TaskPriority.NORMAL)

    dispatcher.enqueue(t1)
    dispatcher.enqueue(t2)
    dispatcher.enqueue(t3)

    assert dispatcher.get_next_task().id == "t1"
    assert dispatcher.get_next_task().id == "t2"
    assert dispatcher.get_next_task().id == "t3"

def test_priority_scheduling():
    """HIGH priority tasks must execute before NORMAL and LOW regardless of submission order."""
    dispatcher = TaskDispatcher()
    low_task = Task(id="low", name="low_job", fn=dummy_success, priority=TaskPriority.LOW)
    normal_task = Task(id="norm", name="norm_job", fn=dummy_success, priority=TaskPriority.NORMAL)
    high_task = Task(id="high", name="high_job", fn=dummy_success, priority=TaskPriority.HIGH)

    dispatcher.enqueue(low_task)
    dispatcher.enqueue(normal_task)
    dispatcher.enqueue(high_task)

    first = dispatcher.get_next_task()
    second = dispatcher.get_next_task()
    third = dispatcher.get_next_task()

    assert first.id == "high", f"Expected high priority first, got {first.id}"
    assert second.id == "norm", f"Expected normal priority second, got {second.id}"
    assert third.id == "low", f"Expected low priority third, got {third.id}"

def test_exponential_backoff_calculation():
    """Verify exponential backoff progression formula: base_delay * (2 ** retry_count)."""
    dispatcher = TaskDispatcher()
    task = Task(id="backoff_task", name="retry_calc", fn=dummy_fail, base_delay=2.0)
    
    task.retry_count = 0
    assert dispatcher.calculate_backoff(task) == 2.0  # 2.0 * 2^0 = 2.0
    task.retry_count = 1
    assert dispatcher.calculate_backoff(task) == 4.0  # 2.0 * 2^1 = 4.0
    task.retry_count = 2
    assert dispatcher.calculate_backoff(task) == 8.0  # 2.0 * 2^2 = 8.0

def test_task_retry_success():
    """Task that fails twice and succeeds on third run should transition to COMPLETED."""
    dispatcher = TaskDispatcher()
    execution_attempts = 0

    def flaky_operation():
        nonlocal execution_attempts
        execution_attempts += 1
        if execution_attempts < 3:
            raise ValueError(f"Temporary flake attempt {execution_attempts}")
        return "success"

    flaky_task = Task(id="flaky", name="flaky_task", fn=flaky_operation, max_retries=3)
    dispatcher.enqueue(flaky_task)

    # 1st attempt: fails -> retrying (retry_count = 1)
    dispatcher.run_next_task()
    assert flaky_task.status == TaskStatus.RETRYING
    assert flaky_task.retry_count == 1
    assert len(dispatcher.queue) == 1

    # 2nd attempt: fails -> retrying (retry_count = 2)
    dispatcher.run_next_task()
    assert flaky_task.status == TaskStatus.RETRYING
    assert flaky_task.retry_count == 2

    # 3rd attempt: succeeds -> completed
    dispatcher.run_next_task()
    assert flaky_task.status == TaskStatus.COMPLETED
    assert flaky_task in dispatcher.completed_tasks

def test_dead_letter_queue_exhaustion():
    """Task exceeding max_retries must transition to DEAD_LETTER and land in DLQ."""
    dispatcher = TaskDispatcher()
    failing_task = Task(id="failing", name="fail_task", fn=dummy_fail, max_retries=2)
    dispatcher.enqueue(failing_task)

    # 1st attempt
    dispatcher.run_next_task()
    assert failing_task.status == TaskStatus.RETRYING
    assert failing_task.retry_count == 1

    # 2nd attempt (reaches max_retries = 2)
    dispatcher.run_next_task()
    assert failing_task.status == TaskStatus.DEAD_LETTER
    assert failing_task.retry_count == 2
    assert failing_task in dispatcher.dead_letter_queue
    assert "Permanent connection failure" in failing_task.last_error

def test_dead_letter_hook_invoked():
    """Registered dead_letter_hook callback must receive the task and exception."""
    hook = InMemoryAuditHook()
    dispatcher = TaskDispatcher(dead_letter_hook=hook)
    task = Task(id="hook_task", name="hook_job", fn=dummy_fail, max_retries=1)
    dispatcher.enqueue(task)

    dispatcher.run_next_task()  # attempt 1 -> max retries exhausted
    assert len(hook.dead_letters) == 1
    recorded_task, recorded_err = hook.dead_letters[0]
    assert recorded_task.id == "hook_task"
    assert "Permanent connection failure" in recorded_err
'''
}

PROJECTS_CATALOG: Dict[str, Dict] = {
    "distributed-rate-limiter": {
        "id": "distributed-rate-limiter",
        "title": "Design a Distributed Rate Limiter Middleware",
        "slug": "distributed-rate-limiter",
        "difficulty": "senior",
        "estimated_minutes": 25,
        "description": "Implement a high-throughput, multi-tenant sliding window distributed rate limiter backed by an in-memory Redis Sorted Set datastore with RFC-compliant headers and 429 response handling.",
        "tags": ["Distributed Systems", "Redis", "Concurrency", "FastAPI / ASGI"],
        "icon": "shield-alert",
        "domain": "Distributed Systems & Reliability",
        "repository_files": PROJECT_1_FILES,
        "editable_files": ["src/limiter.py"],
        "active_file": "src/limiter.py",
        "instructions": "Open src/limiter.py and implement the sliding window counter algorithm using the provided RedisMock sorted set methods. Then click Run CI/CD Tests.",
    },
    "async-job-queue": {
        "id": "async-job-queue",
        "title": "Async Task Queue with Priority & Dead-Letter Retries",
        "slug": "async-job-queue",
        "difficulty": "mid",
        "estimated_minutes": 25,
        "description": "Extend an existing asynchronous task queue engine to support strict priority ordering (HIGH, NORMAL, LOW), exponential backoff retries, and dead-letter queue routing upon retry exhaustion.",
        "tags": ["Async Systems", "Queues", "Reliability", "State Machine"],
        "icon": "layers",
        "domain": "Systems & Reliability Engineering",
        "repository_files": PROJECT_2_FILES,
        "editable_files": ["src/dispatcher.py"],
        "active_file": "src/dispatcher.py",
        "instructions": "Open src/dispatcher.py and add priority scheduling, exponential backoff calculation, and dead-letter handling to satisfy all test assertions.",
    }
}

def list_projects() -> List[ProjectSummary]:
    return [
        ProjectSummary(
            id=p["id"],
            title=p["title"],
            slug=p["slug"],
            difficulty=p["difficulty"],
            estimated_minutes=p["estimated_minutes"],
            description=p["description"],
            tags=p["tags"],
            icon=p["icon"],
            domain=p["domain"],
        )
        for p in PROJECTS_CATALOG.values()
    ]

def get_project(project_id: str) -> Optional[ProjectDetail]:
    p = PROJECTS_CATALOG.get(project_id)
    if not p:
        return None
    return ProjectDetail(
        id=p["id"],
        title=p["title"],
        slug=p["slug"],
        difficulty=p["difficulty"],
        estimated_minutes=p["estimated_minutes"],
        description_markdown=p["repository_files"].get("README.md", ""),
        repository_files=p["repository_files"],
        editable_files=p["editable_files"],
        active_file=p["active_file"],
        instructions=p["instructions"],
        domain=p["domain"],
    )
