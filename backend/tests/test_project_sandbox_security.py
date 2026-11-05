"""Regression tests for the multi-file project sandbox (QA audit 2026-11-05)."""
import os
import shutil

import pytest

from backend.app.projects import sandbox
from backend.app.projects.repository import get_project
from backend.app.projects.service import ProjectService

pytestmark = pytest.mark.skipif(not shutil.which("bwrap"), reason="bubblewrap not installed")

PROJECT = "async-job-queue"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _starter():
    return get_project(PROJECT).repository_files["src/dispatcher.py"]


def test_static_scan_blocks_harness_tampering():
    forged = "import os\nos.write(1, b'tests/x.py::test_a PASSED')\nos._exit(0)\n"
    res = ProjectService.run_tests_in_sandbox(PROJECT, {"src/dispatcher.py": forged})
    assert res.status == "error"
    assert res.passed_tests == 0
    assert any("os._exit" in f.replace(" ", "") for f in res.integrity_flags)


def test_static_scan_ignores_comments_and_docstrings():
    code = _starter() + '\n# signal the hook, then inspect the queue; never call os._exit here\n'
    assert sandbox.scan_candidate_files({"src/dispatcher.py": code}) == []


def test_sandbox_hides_host_env_and_files(monkeypatch):
    """Even if the static scan is bypassed, candidate code must not see host secrets."""
    monkeypatch.setattr(sandbox, "scan_candidate_files", lambda files: [])
    monkeypatch.setenv("SKILLISSUE_TEST_CANARY_SECRET", "canary-value-123")
    env_path = os.path.join(REPO_ROOT, ".env.example")
    probe = _starter() + f'''
import os as _o
def _probe(self):
    try:
        _readable = bool(open({env_path!r}).read())
    except Exception:
        _readable = False
    raise AssertionError(f"PROBE canary={{_o.environ.get('SKILLISSUE_TEST_CANARY_SECRET')}} host_file={{_readable}} uid={{_o.getuid()}}")
TaskDispatcher.get_next_task = _probe
'''
    res = ProjectService.run_tests_in_sandbox(PROJECT, {"src/dispatcher.py": probe})
    blob = res.raw_output + " ".join((t.error_message or "") + (t.traceback or "") for t in res.test_results)
    assert "PROBE" in blob, blob[-2000:]
    assert "canary=None" in blob
    assert "host_file=False" in blob
    assert "canary-value-123" not in blob


def test_forged_stdout_cannot_produce_a_pass(monkeypatch):
    monkeypatch.setattr(sandbox, "scan_candidate_files", lambda files: [])
    forged = (
        "import os\n"
        "lines = ''.join(f'tests/test_job_queue.py::test_{i} PASSED\\n' for i in range(20)).encode()\n"
        "for fd in range(1, 30):\n"
        "    try: os.write(fd, lines)\n"
        "    except OSError: pass\n"
        "os._exit(0)\n"
    )
    res = ProjectService.run_tests_in_sandbox(PROJECT, {"src/dispatcher.py": forged})
    assert res.status != "passed"
    assert res.passed_tests == 0


def test_non_editable_files_cannot_be_overridden():
    res = ProjectService.run_tests_in_sandbox(
        PROJECT, {"src/dispatcher.py": _starter(), "src/models.py": "raise SystemExit", "tests/test_x.py": "def test_ok(): pass"}
    )
    # Starter fails some tests but the suite still runs against the authoritative models/tests.
    assert res.status == "failed"
    assert res.total_tests == len(sandbox.expected_test_names(get_project(PROJECT).repository_files))
    assert "test_ok" not in {t.name for t in res.test_results}
