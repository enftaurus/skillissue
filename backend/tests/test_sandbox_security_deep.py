import asyncio
import json
import os
import signal
import time
import httpx
import pytest
from fastapi.testclient import TestClient

from sandbox.executor.main import app, EXECUTOR_SECRET
from sandbox.executor.schemas import ExecuteRequest, TestCase, CheckerType
from sandbox.executor.persistent_manager import PersistentSandboxManager

@pytest.fixture
def api_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")

@pytest.fixture
def auth_headers():
    return {"X-Executor-Secret": EXECUTOR_SECRET}

# -------------------------------------------------------------
# 1. Multi-Language Execution Through Service
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_python_service_execution(api_client, auth_headers):
    """Test Python execution through /execute and /execute/stream."""
    req = ExecuteRequest(
        job_id="test_py_service",
        language="python",
        code="import sys\nline = sys.stdin.read().strip()\nprint(f'Echo: {line}')",
        test_cases=[
            TestCase(stdin="SkillIssue", expected_stdout="Echo: SkillIssue", is_hidden=False),
            TestCase(stdin="HiddenData", expected_stdout="Echo: HiddenData", is_hidden=True),
        ],
        time_limit_seconds=3.0,
        memory_limit_mb=256,
    )

    # 1. Regular endpoint
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert data["tests_passed"] == 2
    assert len(data["test_results"]) == 2
    # Verify hidden test masking
    assert data["test_results"][1]["is_hidden"] is True
    assert data["test_results"][1]["stdout"] == ""

    # 2. SSE streaming endpoint
    stream_res = await api_client.post("/execute/stream", headers=auth_headers, json=req.model_dump())
    assert stream_res.status_code == 200
    lines = stream_res.text.strip().split("\n\n")
    events = [json.loads(line.replace("data: ", "")) for line in lines if line.startswith("data: ")]
    event_names = [e.get("event") for e in events]
    assert "queued" in event_names
    assert "compiling" in event_names
    assert "test_result" in event_names
    assert "done" in event_names

@pytest.mark.asyncio
async def test_cpp_service_execution(api_client, auth_headers):
    """Test C++ compilation and execution through /execute."""
    code = """#include <iostream>
#include <string>
using namespace std;
int main() {
    string s;
    if (cin >> s) {
        cout << "CPP: " << s << endl;
    }
    return 0;
}
"""
    req = ExecuteRequest(
        job_id="test_cpp_service",
        language="cpp",
        code=code,
        test_cases=[
            TestCase(stdin="Speed", expected_stdout="CPP: Speed\n", is_hidden=False),
        ],
        time_limit_seconds=3.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert data["tests_passed"] == 1

@pytest.mark.asyncio
async def test_java_service_execution(api_client, auth_headers):
    """Test Java compilation and execution through /execute."""
    code = """import java.util.Scanner;
public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        if (sc.hasNext()) {
            System.out.println("Java: " + sc.next());
        }
    }
}
"""
    req = ExecuteRequest(
        job_id="test_java_service",
        language="java",
        code=code,
        test_cases=[
            TestCase(stdin="JVM", expected_stdout="Java: JVM\n", is_hidden=False),
        ],
        time_limit_seconds=3.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert data["tests_passed"] == 1

# -------------------------------------------------------------
# 2. Adversarial Security & Resource Exhaustion Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_infinite_loop_timeout(api_client, auth_headers):
    """Test that infinite loops are killed within the time limit without hanging the executor."""
    code = "while True:\n    pass\n"
    req = ExecuteRequest(
        job_id="test_infinite_loop",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="", is_hidden=False)],
        time_limit_seconds=1.0,
        memory_limit_mb=256,
    )
    start = time.time()
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    elapsed = time.time() - start

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "time_limit_exceeded"
    assert elapsed < 3.0, "Timeout must be enforced promptly"

@pytest.mark.asyncio
async def test_fork_bomb_mitigation(api_client, auth_headers):
    """Test that fork bombs are safely terminated by process-group termination and limits."""
    code = """import os, sys
try:
    while True:
        os.fork()
except Exception:
    pass
"""
    req = ExecuteRequest(
        job_id="test_fork_bomb",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="", is_hidden=False)],
        time_limit_seconds=1.0,
        memory_limit_mb=256,
    )
    start = time.time()
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    elapsed = time.time() - start

    assert res.status_code == 200
    assert elapsed < 3.5, "Fork bomb must not hang the executor host"

@pytest.mark.asyncio
async def test_oversized_output_capped(api_client, auth_headers):
    """Test that spamming large volumes of stdout is capped and flagged."""
    code = "import sys\nprint('A' * 2_000_000)\n"
    req = ExecuteRequest(
        job_id="test_oversized_output",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="small", is_hidden=False)],
        time_limit_seconds=2.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "output_limit_exceeded"
    # Verify stdout was truncated to <= 1MB
    assert len(data["test_results"][0]["stdout"]) <= 1_048_576

@pytest.mark.asyncio
async def test_memory_pressure_limit(api_client, auth_headers):
    """Test that excessive memory allocation is capped by RLIMIT_AS."""
    code = "a = bytearray(500 * 1024 * 1024)\nprint(len(a))\n"
    req = ExecuteRequest(
        job_id="test_memory_pressure",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="524288000", is_hidden=False)],
        time_limit_seconds=2.0,
        memory_limit_mb=128,  # 128 MB limit vs 500 MB allocation
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("memory_limit_exceeded", "runtime_error")

@pytest.mark.asyncio
async def test_network_isolation_probe(api_client, auth_headers):
    """Test that network access is completely unreachable from the sandbox."""
    code = """import socket, sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    s.connect(('8.8.8.8', 53))
    print("NETWORK_CONNECTED")
except Exception as e:
    print(f"BLOCKED: {e}")
"""
    req = ExecuteRequest(
        job_id="test_net_probe",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="", is_hidden=False)],
        time_limit_seconds=2.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    stdout = data["test_results"][0]["stdout"]
    assert "NETWORK_CONNECTED" not in stdout
    assert "BLOCKED" in stdout

@pytest.mark.asyncio
async def test_environment_variable_isolation(api_client, auth_headers):
    """Test that host application secrets and AWS keys are not accessible in sandbox env."""
    code = """import os
leak = [k for k in os.environ if 'SECRET' in k or 'AWS' in k or 'DATABASE' in k or 'POSTGRES' in k]
print(f"LEAK_KEYS: {leak}")
"""
    req = ExecuteRequest(
        job_id="test_env_isolation",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="LEAK_KEYS: []\n", is_hidden=False)],
        time_limit_seconds=2.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert "LEAK_KEYS: []" in data["test_results"][0]["stdout"]

@pytest.mark.asyncio
async def test_filesystem_traversal_and_write_protection(api_client, auth_headers):
    """Test that root filesystem is read-only and host shadow/env files cannot be modified or read by untrusted code."""
    code = """import os
results = []
# Try writing to /etc
try:
    with open('/etc/malicious', 'w') as f:
        f.write('hacked')
    results.append('WROTE_ETC')
except Exception:
    results.append('ETC_RO')

# Try reading /etc/shadow
try:
    with open('/etc/shadow', 'r') as f:
        f.read()
    results.append('READ_SHADOW')
except Exception:
    results.append('SHADOW_DENIED')

print(';'.join(results))
"""
    req = ExecuteRequest(
        job_id="test_fs_protection",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="ETC_RO;SHADOW_DENIED\n", is_hidden=False)],
        time_limit_seconds=2.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert "ETC_RO;SHADOW_DENIED" in data["test_results"][0]["stdout"]

@pytest.mark.asyncio
async def test_temporary_file_creation_in_tmpfs(api_client, auth_headers):
    """Test that temporary files in /tmp can be created and are isolated in tmpfs."""
    code = """import tempfile, os
with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tf:
    tf.write('hello_sandbox_tmp')
    tf_path = tf.name

with open(tf_path, 'r') as f:
    print(f.read())
"""
    req = ExecuteRequest(
        job_id="test_tmpfs_files",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="hello_sandbox_tmp\n", is_hidden=False)],
        time_limit_seconds=2.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "accepted"
    assert "hello_sandbox_tmp" in data["test_results"][0]["stdout"]

# -------------------------------------------------------------
# 3. Admission Control & Backpressure
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_admission_control_backpressure(api_client, auth_headers):
    """Test that exceeding MAX_CONCURRENT_WORKERS returns HTTP 429 backpressure."""
    from sandbox.executor.main import admission

    # Occupy all worker slots artificially
    original_active = admission._active
    admission._active = admission.max_concurrent

    try:
        req = ExecuteRequest(
            job_id="test_queue_full",
            language="python",
            code="print(1)",
            test_cases=[TestCase(stdin="", expected_stdout="1\n", is_hidden=False)],
            time_limit_seconds=1.0,
            memory_limit_mb=256,
        )

        # 1. /execute endpoint backpressure
        res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
        assert res.status_code == 429
        assert res.headers.get("retry-after") == "2"

        # 2. /execute/stream endpoint backpressure
        res_stream = await api_client.post("/execute/stream", headers=auth_headers, json=req.model_dump())
        assert res_stream.status_code == 429
        assert res_stream.headers.get("retry-after") == "2"

    finally:
        admission._active = original_active

@pytest.mark.asyncio
async def test_hidden_test_cases_not_disclosed(api_client, auth_headers):
    """Requirement 6: Hidden test inputs, expected outputs, and diffs are never leaked in response."""
    req = ExecuteRequest(
        job_id="test_hidden_masking",
        language="python",
        code="print('WrongAnswer')",
        test_cases=[
            TestCase(stdin="VisibleSecret", expected_stdout="VisibleSecret", is_hidden=False),
            TestCase(stdin="HiddenSecretInput", expected_stdout="HiddenSecretExpected", is_hidden=True),
        ],
        time_limit_seconds=2.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()

    hidden_tr = data["test_results"][1]
    assert hidden_tr["is_hidden"] is True
    assert hidden_tr["stdout"] == "", "Hidden test stdout must be empty"
    assert hidden_tr["stderr"] == "", "Hidden test stderr must be empty"
    assert hidden_tr["diff"] is None, "Hidden test diff must be None"

@pytest.mark.asyncio
async def test_process_limit_enforced_against_fork_bomb(api_client, auth_headers):
    """Requirement B.2: Verify kernel process-count enforcement (RLIMIT_NPROC / ulimit -u 64) limits fork bombs."""
    code = """import os
created = 0
for i in range(120):
    try:
        p = os.fork()
        if p == 0:
            import time; time.sleep(0.5); os._exit(0)
        else:
            created += 1
    except BlockingIOError as e:
        print(f"FORK_BLOCKED_AT_{created}")
        break
    except OSError as e:
        if e.errno == 11:
            print(f"FORK_BLOCKED_AT_{created}")
            break
"""
    req = ExecuteRequest(
        job_id="test_fork_proc_limit",
        language="python",
        code=code,
        test_cases=[TestCase(stdin="", expected_stdout="", is_hidden=False)],
        time_limit_seconds=3.0,
        memory_limit_mb=256,
    )
    res = await api_client.post("/execute", headers=auth_headers, json=req.model_dump())
    assert res.status_code == 200
    data = res.json()
    stdout = data["test_results"][0]["stdout"]
    # Kernel process limit should block forks before reaching 120
    assert "FORK_BLOCKED_AT_" in stdout

@pytest.mark.asyncio
async def test_production_fails_closed_without_hardened_profile():
    """Requirement A.3: Production deployment must fail closed if insecure container profile is used."""
    from sandbox.executor.main import lifespan
    from fastapi import FastAPI

    dummy_app = FastAPI()

    # Case 1: Insecure profile in production -> FAILS CLOSED
    old_env = os.environ.get("ENVIRONMENT")
    old_prof = os.environ.get("SANDBOX_SECURITY_PROFILE")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["SANDBOX_SECURITY_PROFILE"] = "local_docker_dev"
        with pytest.raises(RuntimeError) as exc_info:
            async with lifespan(dummy_app):
                pass
        assert "FATAL: Insecure sandbox configuration in production" in str(exc_info.value)

        # Case 2: Hardened microVM profile in production -> Permitted
        os.environ["SANDBOX_SECURITY_PROFILE"] = "hardened_microvm"
        async with lifespan(dummy_app):
            pass

    finally:
        if old_env is not None:
            os.environ["ENVIRONMENT"] = old_env
        else:
            os.environ.pop("ENVIRONMENT", None)
        if old_prof is not None:
            os.environ["SANDBOX_SECURITY_PROFILE"] = old_prof
        else:
            os.environ.pop("SANDBOX_SECURITY_PROFILE", None)

def test_executor_restart_cleans_stale_job_dirs():
    """Requirement B.6: Executor restarts and exceptions do not leave stale writable job directories."""
    stale_dir = "/tmp/skillissue_sandbox/job_stale_orphaned_999"
    os.makedirs(stale_dir, exist_ok=True)
    assert os.path.exists(stale_dir)

    # Re-initializing manager simulates service restart
    new_manager = PersistentSandboxManager()
    assert not os.path.exists(stale_dir), "Stale job directory must be purged on manager restart"
