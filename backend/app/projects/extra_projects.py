"""
Additional AI-assisted coding projects, built with `make_project` so new ones are cheap to add.

Every project ships a `reference_solution` (server-side only, never sent to clients) that the test
suite runs through the hardened sandbox to prove the challenge is solvable and the starter fails.
"""
from typing import Dict, List


def make_project(*, id: str, title: str, difficulty: str, minutes: int, description: str, tags: List[str],
                 icon: str, domain: str, files: Dict[str, str], editable: List[str], instructions: str,
                 reference_solution: Dict[str, str]) -> Dict:
    assert all(p in files for p in editable), "editable files must exist in the repository"
    assert any(p.startswith("tests/") for p in files), "a project needs a tests/ suite"
    return {
        "id": id, "title": title, "slug": id, "difficulty": difficulty, "estimated_minutes": minutes,
        "description": description, "tags": tags, "icon": icon, "domain": domain,
        "repository_files": files, "editable_files": editable, "active_file": editable[0],
        "instructions": instructions, "reference_solution": reference_solution,
    }


# --------------------------------------------------------------------------- idempotent payments

PAYMENTS_FILES = {
    "README.md": """# Idempotent Payments API

Mobile clients retry `POST /charges` on flaky networks. Today a retry can charge a customer twice.

Implement `PaymentService.charge()` in `src/payments.py`:

1. **Same idempotency key + same request** -> return the *original* `ChargeResult`; never call the ledger again.
2. **Same key + different request** (user or amount differs) -> raise `IdempotencyConflict`.
3. **Concurrent duplicates** (two threads, same key, at the same time) -> exactly one ledger charge.
4. **Expiry**: a key is forgotten `ttl_seconds` after first use (use the injected `clock`); after that it's a new charge.
5. Ledger failures (`LedgerError`) must not be cached: a retry with the same key may succeed later.

Files: `src/ledger.py` (read-only), `src/payments.py` (edit), `tests/test_payments.py` (read-only).
""",
    "src/ledger.py": '''"""Downstream ledger. Read-only."""
import itertools


class LedgerError(Exception):
    pass


class Ledger:
    def __init__(self, fail_next: int = 0):
        self.charges = []
        self._ids = itertools.count(1)
        self.fail_next = fail_next

    def charge(self, user_id: str, amount_cents: int) -> str:
        if self.fail_next > 0:
            self.fail_next -= 1
            raise LedgerError("ledger unavailable")
        charge_id = f"ch_{next(self._ids)}"
        self.charges.append((charge_id, user_id, amount_cents))
        return charge_id
''',
    "src/payments.py": '''"""Payment service. EDIT THIS FILE."""
import threading
import time
from dataclasses import dataclass

from src.ledger import Ledger


class IdempotencyConflict(Exception):
    """Same idempotency key reused with a different request."""


@dataclass(frozen=True)
class ChargeResult:
    charge_id: str
    user_id: str
    amount_cents: int


class PaymentService:
    def __init__(self, ledger: Ledger, ttl_seconds: float = 86400, clock=time.monotonic):
        self.ledger = ledger
        self.ttl_seconds = ttl_seconds
        self.clock = clock

    def charge(self, idempotency_key: str, user_id: str, amount_cents: int) -> ChargeResult:
        # TODO: make this idempotent (see README)
        charge_id = self.ledger.charge(user_id, amount_cents)
        return ChargeResult(charge_id, user_id, amount_cents)
''',
    "tests/test_payments.py": '''import threading
import time

import pytest

from src.ledger import Ledger, LedgerError
from src.payments import ChargeResult, IdempotencyConflict, PaymentService


def test_first_charge_hits_ledger():
    ledger = Ledger()
    r = PaymentService(ledger).charge("k1", "u1", 500)
    assert isinstance(r, ChargeResult) and r.amount_cents == 500
    assert len(ledger.charges) == 1


def test_retry_with_same_key_returns_original():
    ledger = Ledger()
    svc = PaymentService(ledger)
    a = svc.charge("k1", "u1", 500)
    b = svc.charge("k1", "u1", 500)
    assert a == b
    assert len(ledger.charges) == 1


def test_same_key_different_request_conflicts():
    svc = PaymentService(Ledger())
    svc.charge("k1", "u1", 500)
    with pytest.raises(IdempotencyConflict):
        svc.charge("k1", "u1", 999)
    with pytest.raises(IdempotencyConflict):
        svc.charge("k1", "u2", 500)


def test_concurrent_duplicates_charge_once():
    ledger = Ledger()
    original = ledger.charge

    def slow_charge(user_id, amount):
        time.sleep(0.05)
        return original(user_id, amount)

    ledger.charge = slow_charge
    svc = PaymentService(ledger)
    results = []
    threads = [threading.Thread(target=lambda: results.append(svc.charge("k1", "u1", 500))) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ledger.charges) == 1
    assert len(set(results)) == 1


def test_key_expires_after_ttl():
    now = [0.0]
    ledger = Ledger()
    svc = PaymentService(ledger, ttl_seconds=10, clock=lambda: now[0])
    svc.charge("k1", "u1", 500)
    now[0] = 11
    svc.charge("k1", "u1", 500)
    assert len(ledger.charges) == 2


def test_ledger_failure_is_not_cached():
    ledger = Ledger(fail_next=1)
    svc = PaymentService(ledger)
    with pytest.raises(LedgerError):
        svc.charge("k1", "u1", 500)
    r = svc.charge("k1", "u1", 500)
    assert r.charge_id == "ch_1" and len(ledger.charges) == 1
''',
}

PAYMENTS_SOLUTION = {"src/payments.py": '''"""Payment service."""
import threading
import time
from dataclasses import dataclass

from src.ledger import Ledger


class IdempotencyConflict(Exception):
    """Same idempotency key reused with a different request."""


@dataclass(frozen=True)
class ChargeResult:
    charge_id: str
    user_id: str
    amount_cents: int


class PaymentService:
    def __init__(self, ledger: Ledger, ttl_seconds: float = 86400, clock=time.monotonic):
        self.ledger = ledger
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._results = {}
        self._lock = threading.Lock()
        self._key_locks = {}

    def charge(self, idempotency_key: str, user_id: str, amount_cents: int) -> ChargeResult:
        with self._lock:
            key_lock = self._key_locks.setdefault(idempotency_key, threading.Lock())
        with key_lock:
            entry = self._results.get(idempotency_key)
            if entry is not None and self.clock() - entry[0] >= self.ttl_seconds:
                entry = None
                del self._results[idempotency_key]
            if entry is not None:
                result = entry[1]
                if (result.user_id, result.amount_cents) != (user_id, amount_cents):
                    raise IdempotencyConflict(idempotency_key)
                return result
            charge_id = self.ledger.charge(user_id, amount_cents)
            result = ChargeResult(charge_id, user_id, amount_cents)
            self._results[idempotency_key] = (self.clock(), result)
            return result
'''}

# --------------------------------------------------------------------------- webhook signatures

WEBHOOK_FILES = {
    "README.md": """# Webhook Signature Verifier

Partners send webhooks with a header like `t=1700000000,v1=<hex hmac>`.
The signed payload is `f"{t}.{body}"`, HMAC-SHA256 with a shared secret.

Implement `verify(header, body, now)` in `src/webhooks.py`. It must:

1. Parse the header (order-independent; extra fields allowed; multiple `v1=` values allowed).
2. Accept if **any** `v1` matches **any** active secret (secret rotation).
3. Compare signatures in **constant time**.
4. Reject timestamps older or newer than `tolerance_seconds` (replay protection).
5. Raise `InvalidSignature` with a clear reason for malformed headers, stale timestamps or mismatches.

Files: `src/webhooks.py` (edit), `tests/test_webhooks.py` (read-only).
""",
    "src/webhooks.py": '''"""Webhook verification. EDIT THIS FILE."""
import hashlib
import hmac
from typing import List


class InvalidSignature(Exception):
    pass


def sign(secret: str, timestamp: int, body: str) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


class WebhookVerifier:
    def __init__(self, secrets: List[str], tolerance_seconds: int = 300):
        self.secrets = secrets
        self.tolerance_seconds = tolerance_seconds

    def verify(self, header: str, body: str, now: int) -> bool:
        # TODO: parse the header, check the timestamp window and compare signatures safely.
        t, sig = header.split(",")
        return sig.split("=")[1] == sign(self.secrets[0], int(t.split("=")[1]), body)
''',
    "tests/test_webhooks.py": '''import pytest

from src.webhooks import InvalidSignature, WebhookVerifier, sign

BODY = '{"event":"charge.succeeded","id":"evt_1"}'


def header(secret, t, body=BODY, extra=""):
    return f"t={t},v1={sign(secret, t, body)}" + extra


def test_valid_signature():
    assert WebhookVerifier(["s1"]).verify(header("s1", 1000), BODY, now=1000) is True


def test_field_order_and_extra_fields():
    sig = sign("s1", 1000, BODY)
    assert WebhookVerifier(["s1"]).verify(f"v0=legacy,v1={sig},t=1000", BODY, now=1000)


def test_secret_rotation_and_multiple_signatures():
    t = 1000
    h = f"t={t},v1={sign('old', t, BODY)},v1={sign('new', t, BODY)}"
    assert WebhookVerifier(["new"]).verify(h, BODY, now=t)
    assert WebhookVerifier(["rotated", "old"]).verify(h, BODY, now=t)


def test_tampered_body_rejected():
    with pytest.raises(InvalidSignature):
        WebhookVerifier(["s1"]).verify(header("s1", 1000), BODY + " ", now=1000)


def test_replay_window():
    v = WebhookVerifier(["s1"], tolerance_seconds=300)
    with pytest.raises(InvalidSignature):
        v.verify(header("s1", 1000), BODY, now=1301)
    with pytest.raises(InvalidSignature):
        v.verify(header("s1", 2000), BODY, now=1000)
    assert v.verify(header("s1", 1000), BODY, now=1300)


@pytest.mark.parametrize("bad", ["", "garbage", "t=abc,v1=00", "v1=abcd", "t=1000"])
def test_malformed_headers(bad):
    with pytest.raises(InvalidSignature):
        WebhookVerifier(["s1"]).verify(bad, BODY, now=1000)
''',
}

WEBHOOK_SOLUTION = {"src/webhooks.py": '''"""Webhook verification."""
import hashlib
import hmac
from typing import List


class InvalidSignature(Exception):
    pass


def sign(secret: str, timestamp: int, body: str) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


class WebhookVerifier:
    def __init__(self, secrets: List[str], tolerance_seconds: int = 300):
        self.secrets = secrets
        self.tolerance_seconds = tolerance_seconds

    def verify(self, header: str, body: str, now: int) -> bool:
        timestamp = None
        signatures = []
        for part in (header or "").split(","):
            key, sep, value = part.strip().partition("=")
            if not sep:
                continue
            if key == "t":
                if not value.isdigit():
                    raise InvalidSignature("timestamp is not an integer")
                timestamp = int(value)
            elif key == "v1":
                signatures.append(value)
        if timestamp is None or not signatures:
            raise InvalidSignature("missing timestamp or signature")
        if abs(now - timestamp) > self.tolerance_seconds:
            raise InvalidSignature("timestamp outside tolerance window")
        for secret in self.secrets:
            expected = sign(secret, timestamp, body)
            if any(hmac.compare_digest(expected, s) for s in signatures):
                return True
        raise InvalidSignature("no matching signature")
'''}

EXTRA_PROJECTS = {
    "idempotent-payments": make_project(
        id="idempotent-payments", title="Idempotent Payments API", difficulty="mid", minutes=25,
        description="Stop double charges: implement idempotency keys with conflict detection, concurrency safety, expiry and failure semantics.",
        tags=["Payments", "Concurrency", "Reliability"], icon="credit-card", domain="Fintech Backend Engineering",
        files=PAYMENTS_FILES, editable=["src/payments.py"],
        instructions="Open src/payments.py and make charge() idempotent so retries never double-charge.",
        reference_solution=PAYMENTS_SOLUTION),
    "webhook-signatures": make_project(
        id="webhook-signatures", title="Webhook Signature Verifier", difficulty="mid", minutes=20,
        description="Verify partner webhooks safely: header parsing, secret rotation, constant-time comparison and replay protection.",
        tags=["Security", "APIs", "Cryptography"], icon="shield", domain="Security Engineering",
        files=WEBHOOK_FILES, editable=["src/webhooks.py"],
        instructions="Open src/webhooks.py and implement verify() per the README.",
        reference_solution=WEBHOOK_SOLUTION),
}
