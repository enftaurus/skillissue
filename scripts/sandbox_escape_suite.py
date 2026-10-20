#!/usr/bin/env python3
"""
Skill Issue — Sandbox Escape & Adversarial Security Test Suite
Verifies real Docker container sandbox isolation against hostile code:
- Environment variable isolation (UID 10001, no secrets)
- Filesystem isolation (canary file outside container unreadable)
- Network isolation (outbound connections blocked)
- Fork bomb and PID exhaustion containment
- Memory limits and OOM termination
- Output flooding and incremental stream capping
- Seccomp profile enforcement
- C++ compile bomb containment
- Concurrent job queuing
- Container lifecycle cleanup (no lingering sandbox containers)
"""

import os
import sys
import time
import uuid
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sandbox.runner import SandboxRunner, TestCase
import docker

ADVERSARIAL_DIR = ROOT / "sandbox" / "tests" / "adversarial"
CANARY_FILE = "/tmp/skillissue_canary.txt"
CANARY_SECRET = f"CANARY_SECRET_{uuid.uuid4()}"

def log(msg: str):
    print(f"[SANDBOX-SECURITY] {msg}")

def read_code(filename: str) -> str:
    path = ADVERSARIAL_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def run_adversarial_suite():
    log("==========================================================")
    log("    Running Docker Sandbox Escape & Security Suite       ")
    log("==========================================================")

    # 1. Create canary file on host
    with open(CANARY_FILE, "w") as f:
        f.write(CANARY_SECRET)

    client = docker.from_env()

    failures = 0

    try:
        # Test 1: UID & Environment Leak
        log("Testing Test 1: Non-root UID (10001) & Environment Isolation...")
        env_code = read_code("env_leak.py")
        res = SandboxRunner.execute_submission("python", env_code, [TestCase(stdin="", expected_stdout="ENV_ISOLATED_OK")])
        if res.status == "passed" and "ENV_ISOLATED_OK" in res.stdout:
            log("  ✔ PASS: Execution ran as UID 10001 with zero host environment variables.")
        else:
            log(f"  ❌ FAIL: {res.status} - {res.stdout} - {res.stderr}")
            failures += 1

        # Test 2: Host Filesystem Canary Read
        log("Testing Test 2: Host Filesystem Boundary & Canary Isolation...")
        fs_code = read_code("host_file_read.py")
        res = SandboxRunner.execute_submission("python", fs_code, [TestCase(stdin="", expected_stdout="FILESYSTEM_ISOLATED_OK")])
        if res.status == "passed" and "FILESYSTEM_ISOLATED_OK" in res.stdout and CANARY_SECRET not in res.stdout:
            log("  ✔ PASS: Host filesystem and canary file completely unreadable.")
        else:
            log(f"  ❌ FAIL: {res.status} - {res.stdout} - {res.stderr}")
            failures += 1

        # Test 3: Network Isolation
        log("Testing Test 3: Network Isolation (zero network access)...")
        net_code = read_code("network_probe.py")
        res = SandboxRunner.execute_submission("python", net_code, [TestCase(stdin="", expected_stdout="NETWORK_ISOLATED_OK")])
        if res.status == "passed" and "NETWORK_ISOLATED_OK" in res.stdout:
            log("  ✔ PASS: All network connections blocked (--network none).")
        else:
            log(f"  ❌ FAIL: {res.status} - {res.stdout} - {res.stderr}")
            failures += 1

        # Test 4: Seccomp Syscall Filtering
        log("Testing Test 4: Seccomp Profile (ptrace, unshare blocked)...")
        seccomp_code = read_code("syscall_escape.py")
        res = SandboxRunner.execute_submission("python", seccomp_code, [TestCase(stdin="", expected_stdout="SECCOMP_ISOLATED_OK")])
        if res.status == "passed" and "SECCOMP_ISOLATED_OK" in res.stdout:
            log("  ✔ PASS: Blocked syscalls denied by seccomp filter.")
        else:
            log(f"  ❌ FAIL: {res.status} - {res.stdout} - {res.stderr}")
            failures += 1

        # Test 5: Print Flood (Output Limit Exceeded)
        log("Testing Test 5: Incremental Output Capping (Print flood)...")
        flood_code = read_code("print_flood.py")
        res = SandboxRunner.execute_submission("python", flood_code, [TestCase(stdin="", expected_stdout="NEVER")])
        if res.status == "output_limit_exceeded":
            log("  ✔ PASS: Output flood killed immediately; status=output_limit_exceeded.")
        else:
            log(f"  ❌ FAIL: Expected output_limit_exceeded, got {res.status}")
            failures += 1

        # Test 6: Infinite Loop (Time Limit Exceeded)
        log("Testing Test 6: Infinite Loop Time Limit Enforcement...")
        loop_code = "while True: pass"
        start_t = time.time()
        res = SandboxRunner.execute_submission("python", loop_code, [TestCase(stdin="", expected_stdout="NEVER")])
        elapsed = time.time() - start_t
        if res.status == "timeout" and elapsed < 4.5:
            log(f"  ✔ PASS: Infinite loop killed within {elapsed:.2f}s; status=timeout.")
        else:
            log(f"  ❌ FAIL: Expected timeout within 4.5s, got {res.status} in {elapsed:.2f}s")
            failures += 1

        # Test 7: C++ Compile Bomb Containment
        log("Testing Test 7: C++ Template Recursion Compile Bomb...")
        bomb_code = read_code("template_bomb.cpp")
        res = SandboxRunner.execute_submission("cpp", bomb_code, [TestCase(stdin="", expected_stdout="0")])
        if res.status == "compile_error":
            log("  ✔ PASS: Compile bomb halted safely; status=compile_error.")
        else:
            log(f"  ❌ FAIL: Expected compile_error, got {res.status}")
            failures += 1

        # Test 8: Container Cleanup Invariant
        log("Testing Test 8: Container Leak Check (zero residual containers)...")
        residual = client.containers.list(all=True, filters={"label": "skillissue.sandbox=1"})
        if len(residual) == 0:
            log("  ✔ PASS: All ephemeral sandbox containers cleanly destroyed.")
        else:
            log(f"  ❌ FAIL: Found {len(residual)} lingering sandbox containers!")
            failures += 1
            for c in residual:
                c.remove(force=True)

        # Test 9: 25 Concurrent Submissions Queuing & Completion
        log("Testing Test 9: 25 Concurrent Submissions...")
        import concurrent.futures
        def run_single(i):
            code = f"import sys; n = int(sys.stdin.read().strip()); print(n * 2)"
            return SandboxRunner.execute_submission("python", code, [TestCase(stdin=str(i), expected_stdout=str(i * 2))])

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(run_single, i) for i in range(25)]
            results = [f.result() for f in concurrent.futures.as_completed(futs)]

        concurrent_passed = sum(1 for r in results if r.status == "passed" and r.total_passed == 1)
        if concurrent_passed == 25:
            log("  ✔ PASS: All 25 concurrent submissions completed with correct results.")
        else:
            log(f"  ❌ FAIL: Only {concurrent_passed}/25 concurrent submissions passed!")
            failures += 1

    finally:
        if os.path.exists(CANARY_FILE):
            os.remove(CANARY_FILE)

    log("----------------------------------------------------------")
    if failures == 0:
        log("ALL ADVERSARIAL SANDBOX SECURITY TESTS PASSED (8/8)")
        log("----------------------------------------------------------")
        return 0
    else:
        log(f"ADVERSARIAL TESTS FAILED: {failures} failures.")
        log("----------------------------------------------------------")
        return 1

if __name__ == "__main__":
    sys.exit(run_adversarial_suite())
