"""
Code comprehension bank: realistic infrastructure code with planted, production-style bugs.

Lines ending in `# @bug` mark the answer-key bug locations. The marker is stripped before code is
served and line numbers are computed from it, so the key and the code can't drift apart. Every
`trace` expectation is verified by executing the harness in backend/tests/test_comprehension.py.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

BUG_MARKER = "# @bug"


@dataclass
class Question:
    id: str
    type: str  # explain | trace | bug | review | numeric
    prompt: str
    key_points: List[str] = field(default_factory=list)
    harness: Optional[str] = None          # trace: code appended to the item's main file
    expected_output: Optional[str] = None  # trace
    accept_patterns: List[str] = field(default_factory=list)  # numeric / complexity regexes


@dataclass
class Item:
    id: str
    title: str
    difficulty: str  # medium | hard
    tags: List[str]
    context: str
    files: Dict[str, str]
    questions: List[Question]
    estimated_minutes: int = 15
    language: str = "python"

    def clean_files(self) -> Dict[str, str]:
        return {name: "\n".join(_strip_marker(l) for l in src.strip("\n").splitlines()) + "\n"
                for name, src in self.files.items()}

    def bug_lines(self) -> List[Tuple[str, int]]:
        out = []
        for name, src in self.files.items():
            for i, line in enumerate(src.strip("\n").splitlines(), 1):
                if line.rstrip().endswith(BUG_MARKER):
                    out.append((name, i))
        return out


def _strip_marker(line: str) -> str:
    s = line.rstrip()
    return s[: -len(BUG_MARKER)].rstrip() if s.endswith(BUG_MARKER) else line.rstrip()


ITEMS: List[Item] = [
    Item(
        id="ttl-lru-cache", title="TTL + LRU cache", difficulty="medium", tags=["caching", "data structures"],
        context="A small in-process cache used in front of a slow profile service.",
        files={"cache.py": '''
import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, capacity, ttl_seconds, clock=time.monotonic):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.clock = clock
        self._data = OrderedDict()  # key -> (value, expires_at)

    def get(self, key, default=None):
        if key not in self._data:
            return default
        value, expires_at = self._data[key]
        self._data.move_to_end(key)  # @bug
        if self.clock() >= expires_at:
            return default
        return value

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (value, self.clock() + self.ttl)
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
'''},
        questions=[
            Question("q1", "explain", "In two or three sentences: what does this class do, and what does it promise callers?",
                     ["bounded by capacity with least-recently-used eviction", "each entry expires after ttl_seconds",
                      "get returns the default for missing or expired keys", "reading a key refreshes its recency"]),
            Question("q2", "trace", "What does this print? Give the exact output.",
                     harness='''
t = [0]
c = TTLCache(2, 10, clock=lambda: t[0])
c.put("a", 1)
t[0] = 5
c.put("b", 2)
t[0] = 11
print(c.get("a"))
c.put("c", 3)
print(c.get("b"), c.get("c"))
''', expected_output="None\nNone 3"),
            Question("q3", "bug", "Under load this cache evicts entries that are still valid. Which line causes it, and why?",
                     ["get() moves an expired entry to the most-recent end before checking expiry",
                      "expired entries are never deleted, so they keep occupying capacity",
                      "live entries (like 'b') get evicted instead of the dead one"]),
            Question("q4", "review", "Write the review comment you'd leave: the minimal fix and one more improvement.",
                     ["check expiry before move_to_end", "delete the expired entry inside get",
                      "optionally purge expired entries before evicting on put"]),
        ]),
    Item(
        id="token-bucket", title="Token-bucket rate limiter", difficulty="hard", tags=["rate limiting", "time"],
        context="Per-client limiter on an API gateway. Clients report being throttled below their plan's rate.",
        files={"limiter.py": '''
import time


class TokenBucket:
    """Allows `rate` requests per second with bursts up to `capacity`."""

    def __init__(self, rate, capacity, clock=time.monotonic):
        self.rate = rate
        self.capacity = capacity
        self.clock = clock
        self.tokens = capacity
        self.updated = clock()

    def allow(self, cost=1):
        now = self.clock()
        elapsed = now - self.updated
        refill = int(elapsed * self.rate)
        if refill > 0:
            self.tokens = min(self.capacity, self.tokens + refill)
            self.updated = now  # @bug
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
'''},
        questions=[
            Question("q1", "explain", "Explain the algorithm in your own words, including how bursts work.",
                     ["tokens refill continuously at `rate` per second", "bucket holds at most `capacity` tokens (burst size)",
                      "each request spends `cost` tokens and is rejected if not enough"]),
            Question("q2", "trace", "What does this print?",
                     harness='''
t = [0.0]
b = TokenBucket(rate=1, capacity=5, clock=lambda: t[0])
results = [b.allow() for _ in range(5)]
for now in (1.5, 3.0, 3.4):
    t[0] = now
    results.append(b.allow())
print(results)
''', expected_output="[True, True, True, True, True, True, True, False]"),
            Question("q3", "bug", "Why do clients get fewer requests than `rate` allows? Point at the line.",
                     ["refill is truncated to whole tokens with int()",
                      "setting `updated = now` throws away the fractional remainder of elapsed time",
                      "irregular request spacing loses up to almost one token per refill, so the effective rate drops"]),
            Question("q4", "review", "How would you fix it, and what changes if this limiter must work across 20 gateway replicas?",
                     ["keep tokens as a float and add elapsed * rate without truncation, or advance updated by refill / rate",
                      "per-process buckets multiply the limit by the replica count",
                      "use a shared store with atomic updates (e.g. Redis Lua script) or sticky routing"]),
        ]),
    Item(
        id="quota-race", title="Per-user quota tracker", difficulty="hard", tags=["concurrency", "threads"],
        context="Used by a multi-threaded worker pool to cap free-tier usage.",
        files={"quota.py": '''
import threading


class QuotaTracker:
    def __init__(self, limit):
        self.limit = limit
        self.used = {}
        self.lock = threading.Lock()

    def try_consume(self, user, amount=1):
        current = self.used.get(user, 0)  # @bug
        if current + amount > self.limit:
            return False
        with self.lock:
            self.used[user] = current + amount
        return True

    def remaining(self, user):
        with self.lock:
            return self.limit - self.used.get(user, 0)
'''},
        questions=[
            Question("q1", "trace", "Single-threaded: what does this print?",
                     harness='''
q = QuotaTracker(3)
print([q.try_consume("u", 2), q.try_consume("u", 2), q.remaining("u")])
''', expected_output="[True, False, 1]"),
            Question("q2", "bug", "Free-tier users sometimes exceed their limit under load. Which line, and what exactly happens?",
                     ["the read and the limit check happen outside the lock (check-then-act race)",
                      "two threads read the same `current`, both pass the check, and both write current + amount",
                      "the second write overwrites the first (lost update) so usage is under-counted and the limit is exceeded"]),
            Question("q3", "review", "Show the fix in words, and say what goes wrong if you only move the write under the lock.",
                     ["take the lock before reading `used` and keep it through the check and the write",
                      "the read/check/write must be one atomic critical section",
                      "locking only the write still lets two threads act on a stale read"]),
            Question("q4", "review", "Now there are 3 worker hosts, each with its own QuotaTracker. What breaks and what do you use instead?",
                     ["each process has its own dict, so the effective limit is multiplied by the number of hosts",
                      "state must live in a shared store", "use an atomic increment with a check (Redis INCR/Lua, or a DB row lock / conditional update)"]),
        ]),
    Item(
        id="retry-helper", title="Retry with exponential backoff", difficulty="medium", tags=["reliability", "error handling"],
        context="Shared helper wrapped around outbound HTTP calls in several services.",
        files={"retry.py": '''
import random
import time


def retry(fn, attempts=5, base=0.1, cap=5.0, sleep=time.sleep, retry_on=(Exception,)):
    delay = base
    for attempt in range(attempts):
        try:
            return fn()
        except retry_on:
            if attempt == attempts:  # @bug
                raise
            jitter = random.uniform(0, delay)
            sleep(min(cap, delay + jitter))
            delay *= 2
'''},
        questions=[
            Question("q1", "trace", "What does this print?",
                     harness='''
calls, slept = [], []
def flaky():
    calls.append(1)
    raise ValueError("boom")
print(retry(flaky, attempts=3, sleep=slept.append), len(calls), len(slept))
''', expected_output="None 3 3"),
            Question("q2", "bug", "A downstream outage made a caller treat failures as success. Which line, and why?",
                     ["`attempt == attempts` is never true because range stops at attempts - 1",
                      "after the last failure the loop just ends and the function returns None instead of raising",
                      "it also sleeps one extra time after the final attempt"]),
            Question("q3", "review", "Besides that bug, name the two most important production risks in this helper.",
                     ["retrying non-idempotent calls (e.g. POST payments) can duplicate side effects",
                      "catching broad Exception retries programming errors and validation failures",
                      "no overall deadline/budget, so worst-case latency is unbounded by callers' timeouts",
                      "retry storms without a circuit breaker during outages"]),
            Question("q4", "numeric", "Ignoring jitter, what's the total sleep time for attempts=5, base=0.1, cap=5.0 if every call fails (with the bug fixed so it doesn't sleep after the last attempt)?",
                     accept_patterns=[r"(?<![\d.])1\.5\s*(s|sec|seconds)?\b", r"(?<![\d.])1500\s*ms\b"]),
        ]),
    Item(
        id="keyset-pagination", title="Cursor pagination", difficulty="hard", tags=["APIs", "databases"],
        context="Backs the /orders?cursor= endpoint. Support tickets mention 'missing orders' when paging.",
        files={"paging.py": '''
def page(rows, limit, cursor=None):
    """rows: dicts with a unique 'id' and a 'created_at'. Returns (items, next_cursor)."""
    ordered = sorted(rows, key=lambda r: r["created_at"])
    if cursor is not None:
        ordered = [r for r in ordered if r["created_at"] > cursor]  # @bug
    items = ordered[:limit]
    next_cursor = items[-1]["created_at"] if len(items) == limit else None
    return items, next_cursor
'''},
        questions=[
            Question("q1", "trace", "What does this print?",
                     harness='''
rows = [{"id": i, "created_at": t} for i, t in enumerate([1, 2, 2, 2, 3])]
seen, cur = [], None
while True:
    items, cur = page(rows, 2, cur)
    seen += [r["id"] for r in items]
    if cur is None:
        break
print(seen)
''', expected_output="[0, 1, 4]"),
            Question("q2", "bug", "Explain the 'missing orders' bug and point at the line.",
                     ["the cursor uses created_at, which is not unique",
                      "rows sharing the boundary timestamp are filtered out by `> cursor`",
                      "so ids 2 and 3 are skipped"]),
            Question("q3", "review", "Propose the fix, including what the cursor should contain and what index the database needs.",
                     ["use a compound cursor (created_at, id) compared as a tuple",
                      "order by (created_at, id) so the order is total/deterministic",
                      "composite index on (created_at, id)", "encode the cursor opaquely (e.g. base64) for clients"]),
            Question("q4", "review", "Why is this approach better than OFFSET/LIMIT when new orders arrive while a client pages?",
                     ["offset shifts when rows are inserted, causing duplicates or skips",
                      "keyset cursors are stable across inserts", "offset scans get slower for deep pages; keyset uses the index"]),
        ]),
    Item(
        id="consistent-hash", title="Consistent hashing ring", difficulty="hard", tags=["distributed systems", "hashing"],
        context="Routes cache keys to memcached nodes. On-call saw intermittent 500s with an IndexError.",
        files={"ring.py": '''
import bisect
import hashlib


def _h(key):
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % 1000


class Ring:
    def __init__(self, nodes, replicas=3):
        self.ring = []
        self.owner = {}
        for node in nodes:
            for r in range(replicas):
                point = _h(f"{node}#{r}")
                self.ring.append(point)
                self.owner[point] = node
        self.ring.sort()

    def node_for(self, key):
        idx = bisect.bisect_right(self.ring, _h(key))
        return self.owner[self.ring[idx]]  # @bug
'''},
        questions=[
            Question("q1", "explain", "What problem does this structure solve compared with `hash(key) % len(nodes)`?",
                     ["adding or removing a node only remaps a small fraction of keys",
                      "keys go to the first ring point clockwise from their hash",
                      "virtual nodes (replicas) spread load more evenly"]),
            Question("q2", "trace", "What does this print?",
                     harness='''
r = Ring(["a", "b"], replicas=1)
for k in ["user-1", "user-2", "user-3", "user-4", "user-5"]:
    try:
        print(k, r.node_for(k))
    except IndexError:
        print(k, "IndexError")
''', expected_output="user-1 a\nuser-2 a\nuser-3 IndexError\nuser-4 a\nuser-5 b"),
            Question("q3", "bug", "Where does the IndexError come from, and what's the one-line fix?",
                     ["bisect_right returns len(ring) when the key hashes past the last point",
                      "the ring must wrap around to index 0", "fix: idx % len(self.ring) (or idx = 0 when idx == len)"]),
            Question("q4", "review", "Name a second, quieter correctness problem in __init__.",
                     ["two virtual nodes can hash to the same point; the later one silently overwrites owner",
                      "the tiny 0-999 hash space makes collisions likely", "use a larger hash space and handle collisions"]),
        ]),
    Item(
        id="async-fanout", title="Async fan-out with a semaphore", difficulty="medium", tags=["async", "performance"],
        context="Loads user profiles for a dashboard. p99 latency is terrible and CPU is idle.",
        files={"fanout.py": '''
import asyncio
import time


async def fetch(user_id):
    time.sleep(0.1)  # @bug
    return {"id": user_id}


async def fetch_all(user_ids, limit=10):
    sem = asyncio.Semaphore(limit)

    async def one(uid):
        async with sem:
            return await fetch(uid)

    return await asyncio.gather(*(one(u) for u in user_ids))
'''},
        questions=[
            Question("q1", "numeric", "Roughly how long does `asyncio.run(fetch_all(range(20)))` take? Give a number.",
                     accept_patterns=[r"(?<![\d.])2(\.0+)?\s*(s|sec|secs|seconds)\b", r"\btwo seconds\b", r"(?<![\d.])2000\s*ms\b", r"~\s*2(?![\d.])"]),
            Question("q2", "bug", "Why that long, and which line is responsible?",
                     ["time.sleep is a blocking call that freezes the event loop",
                      "so the 20 fetches run one after another instead of concurrently",
                      "the semaphore limit of 10 never matters"]),
            Question("q3", "review", "Fix it, and say how long it would take after the fix with limit=10.",
                     ["use await asyncio.sleep (or an async HTTP client) instead of time.sleep",
                      "with limit 10 the 20 calls run in two waves", "about 0.2 seconds"]),
        ]),
    Item(
        id="closures-defaults", title="Event handler registry", difficulty="medium", tags=["python semantics"],
        context="Plugin system that registers handlers per event name.",
        files={"handlers.py": '''
def make_handlers(events):
    handlers = []
    for name in events:
        handlers.append(lambda payload: f"{name}:{payload}")  # @bug
    return handlers


def register(registry={}, *, key, fn):  # @bug
    registry.setdefault(key, []).append(fn)
    return registry
'''},
        questions=[
            Question("q1", "trace", "What does this print?",
                     harness='''
hs = make_handlers(["created", "deleted"])
print(hs[0]("x"), hs[1]("y"))
a = register(key="k", fn=1)
b = register(key="k", fn=2)
print(a is b, a["k"])
''', expected_output="deleted:x deleted:y\nTrue [1, 2]"),
            Question("q2", "bug", "There are two bugs. Name both lines and explain each.",
                     ["the lambda captures the variable `name`, not its value (late binding), so all handlers see the last event",
                      "the mutable default `registry={}` is created once and shared across calls",
                      "registrations leak between unrelated callers"]),
            Question("q3", "review", "Give the idiomatic fix for each.",
                     ["bind the value: lambda payload, name=name: ... or functools.partial",
                      "use registry=None and create a new dict inside the function"]),
        ]),
    Item(
        id="build-order", title="Build dependency order", difficulty="hard", tags=["graphs", "topological sort"],
        context="CI computes which targets to build first. Some builds silently skip targets.",
        files={"build.py": '''
from collections import defaultdict, deque


def build_order(deps):
    """deps: {target: [prerequisites]}. Returns an order where prerequisites come first."""
    indegree = defaultdict(int)
    children = defaultdict(list)
    for target, prereqs in deps.items():
        indegree.setdefault(target, 0)
        for p in prereqs:  # @bug
            children[p].append(target)
            indegree[target] += 1
    queue = deque(sorted(n for n, d in indegree.items() if d == 0))
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    return order  # @bug
'''},
        questions=[
            Question("q1", "trace", "What does this print?",
                     harness='''
print(build_order({"app": ["lib", "utils"], "lib": ["utils"]}))
print(build_order({"a": ["b"], "b": ["a"], "c": []}))
''', expected_output="[]\n['c']"),
            Question("q2", "bug", "Explain both reasons targets get silently dropped, with lines.",
                     ["prerequisites that aren't keys (like 'utils') never get an indegree entry, so they never enter the queue",
                      "so everything depending on them is dropped too",
                      "cycles are silently ignored: the function never checks that every node was emitted"]),
            Question("q3", "numeric", "What's the time complexity of a correct version in terms of V targets and E edges?",
                     accept_patterns=[r"o\s*\(\s*v\s*\+\s*e\s*\)", r"o\s*\(\s*e\s*\+\s*v\s*\)", r"linear in (the )?(number of )?(nodes|vertices) (and|plus) edges"]),
            Question("q4", "review", "How should the function behave on a cycle, and how do you report it usefully?",
                     ["raise an error instead of returning a partial order",
                      "detect it when len(order) != number of nodes",
                      "report the nodes involved in the cycle so the user can fix the dependency"]),
        ]),
]

ITEMS_BY_ID: Dict[str, Item] = {i.id: i for i in ITEMS}
