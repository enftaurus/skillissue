"""
Hardened runner for multi-file project test suites.

Threat model: the candidate controls the contents of the editable files, and that code
runs inside the same Python process as pytest. So:

* The process must not see host secrets: no host filesystem except the interpreter and
  system libraries, a cleared environment, no network, and an unprivileged uid.
* Pass/fail must not come from stdout, which the candidate can forge. Results come from
  a JUnit XML report and are cross-checked against the test names parsed server-side
  from the authoritative test files, plus the pytest exit code.
* Obvious tampering primitives (hard exits, raw fd writes, interpreter/pytest
  introspection) in candidate files are rejected before execution.

Residual risk: a determined attacker running in-process can still forge a result file.
Moving project runs into the Docker executor with an out-of-process harness is the
durable fix (see docs/decisions/0023).
"""
import ast
import io
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from backend.app.core.errors import AppException
from backend.app.core.logging import logger

BASE_SANDBOX_DIR = os.path.join(tempfile.gettempdir(), "skillissue_projects")
SANDBOX_WORKDIR = "/work"
_FSTRING_TOKENS = {getattr(tokenize, n) for n in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END") if hasattr(tokenize, n)}
TIMEOUT_SECONDS = 12.0
MAX_OUTPUT_CHARS = 20_000

# Primitives that only exist in candidate code to tamper with the harness or exfiltrate data.
FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    (r"\bos\s*\.\s*_exit\b", "hard process exit (os._exit)"),
    (r"\bos\s*\.\s*(write|dup2?|fdopen|kill|fork|exec\w*|spawn\w*|system|popen)\b", "raw OS process/fd access"),
    (r"\bsys\s*\.\s*(modules|settrace|setprofile|exit|_getframe|stdout|stderr|__stdout__|__stderr__)\b", "interpreter tampering"),
    (r"\b(_pytest|pytest|junit|conftest)\b", "test harness tampering"),
    (r"\b(ctypes|subprocess|socket|importlib|builtins|inspect|gc|signal|atexit|multiprocessing|threading\s*\.\s*_)\b", "restricted module"),
    (r"__import__|__builtins__|__subclasses__|__globals__|__code__|__loader__", "dynamic import / introspection"),
    (r"\bos\s*\.\s*environ\b|\bgetenv\b", "environment access"),
    (r"\b(open|exec|eval|compile|getattr|globals|vars)\s*\(", "file access or dynamic code execution"),
]


@dataclass
class SandboxRunResult:
    status: str  # passed | failed | error
    passed: List[str] = field(default_factory=list)
    failed: Dict[str, Tuple[str, str]] = field(default_factory=dict)  # name -> (message, traceback)
    raw_output: str = ""
    duration_ms: int = 0
    integrity_flags: List[str] = field(default_factory=list)


def expected_test_names(repository_files: Dict[str, str]) -> Set[str]:
    """Collect test function names from the authoritative (server-side) test files."""
    names: Set[str] = set()
    for path, content in repository_files.items():
        if not (path.startswith("tests/") and path.endswith(".py")):
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                names.add(node.name)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith("test"):
                        names.add(sub.name)
    return names


HOST_PATH_PATTERN = (r"/proc/|/etc/|/home/|/root/|\.env\b|\.aws\b", "host filesystem path")


def _split_code_and_strings(content: str) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
    """Return (code_lines, string_literals) with line numbers, dropping comments and docstrings."""
    code: Dict[int, List[str]] = {}
    strings: List[Tuple[int, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(content).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING or tok.type in _FSTRING_TOKENS:
                strings.append((tok.start[0], tok.string))
                continue
            code.setdefault(tok.start[0], []).append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Unparseable source: fall back to scanning everything (pytest will report the syntax error).
        return list(enumerate(content.splitlines(), 1)), []
    return [(ln, " ".join(parts)) for ln, parts in sorted(code.items())], strings


def scan_candidate_files(files: Dict[str, str]) -> List[str]:
    flags: List[str] = []
    for path, content in files.items():
        code_lines, strings = _split_code_and_strings(content)
        for pattern, label in FORBIDDEN_PATTERNS:
            for ln, text in code_lines:
                m = re.search(pattern, text)
                if m:
                    flags.append(f"{path}:{ln}: {label} (`{m.group(0).strip()}`) is not allowed in this challenge")
                    break
        for ln, text in strings:
            m = re.search(HOST_PATH_PATTERN[0], text)
            if m:
                flags.append(f"{path}:{ln}: {HOST_PATH_PATTERN[1]} (`{m.group(0)}`) is not allowed in this challenge")
                break
    return flags


def _bwrap_command(bwrap_bin: str, job_dir: str, report_rel: str) -> List[str]:
    python = sys.executable
    cmd = [
        bwrap_bin,
        "--unshare-all", "--die-with-parent", "--new-session",
        "--ro-bind", "/usr", "/usr",
    ]
    for p in ("/bin", "/lib", "/lib64", "/sbin", "/etc/alternatives", "/etc/ld.so.cache", "/etc/localtime"):
        cmd += ["--ro-bind-try", p, p]
    # Interpreter / virtualenv (read-only). Only the venv dir is exposed, never the repo root.
    for prefix in {os.path.realpath(sys.prefix), os.path.realpath(sys.base_prefix)}:
        if not prefix.startswith("/usr"):
            cmd += ["--ro-bind", prefix, prefix]
    if sys.prefix != os.path.realpath(sys.prefix) and not sys.prefix.startswith("/usr"):
        cmd += ["--ro-bind", sys.prefix, sys.prefix]
    cmd += [
        # Empty /proc instead of a fresh procfs: works inside Docker without systempaths=unconfined and hides
        # every /proc/<pid> entry from candidate code (ADR 0026).
        "--tmpfs", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--bind", job_dir, SANDBOX_WORKDIR, "--chdir", SANDBOX_WORKDIR,
        "--clearenv",
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "HOME", "/tmp",
        "--setenv", "PYTHONPATH", SANDBOX_WORKDIR,
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        "--uid", "65534", "--gid", "65534",
        python, "-I", "-m", "pytest", "-p", "no:cacheprovider", "-o", "pythonpath=.",
        "-q", "--tb=short", f"--junitxml={report_rel}", "tests/",
    ]
    return cmd


def _parse_junit(report_path: str) -> Tuple[List[str], Dict[str, Tuple[str, str]], List[str]]:
    passed: List[str] = []
    failed: Dict[str, Tuple[str, str]] = {}
    seen: List[str] = []
    root = ET.parse(report_path).getroot()
    for case in root.iter("testcase"):
        name = case.get("name", "")
        seen.append(name)
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is not None:
            failed[name] = ((problem.get("message") or "Test failed")[:500], (problem.text or "")[:4000])
        elif case.find("skipped") is not None:
            failed[name] = ("Test skipped", "")
        else:
            passed.append(name)
    return passed, failed, seen


def _env_flags() -> Tuple[str, bool]:
    """(environment, allow_unsandboxed). The executor container has no app settings/secrets, so fall back to env."""
    try:
        from backend.app.core.config import settings
        return settings.ENVIRONMENT.lower(), bool(settings.ALLOW_UNSANDBOXED_PROJECT_TESTS)
    except Exception:
        return (os.environ.get("ENVIRONMENT", "development").lower(),
                os.environ.get("ALLOW_UNSANDBOXED_PROJECT_TESTS", "").lower() == "true")


def _run_via_executor(url: str, repository_files: Dict[str, str], editable_files: List[str],
                      overlay: Dict[str, str], t_start: float) -> SandboxRunResult:
    import httpx
    secret = os.environ.get("EXECUTOR_SECRET", "dev-executor-secret-token-32chars-min!")
    try:
        r = httpx.post(f"{url.rstrip('/')}/execute-project", headers={"X-Executor-Secret": secret}, timeout=TIMEOUT_SECONDS + 15,
                       json={"repository_files": repository_files, "editable_files": editable_files, "candidate_files": overlay})
        r.raise_for_status()
        d = r.json()
    except Exception as e:
        logger.warning(f"Project executor unavailable: {type(e).__name__}")
        raise AppException("Project test sandbox is unavailable right now. Try again shortly.",
                           code="SANDBOX_UNAVAILABLE", status_code=503)
    return SandboxRunResult(status=d.get("status", "error"), passed=list(d.get("passed", [])),
                            failed={k: tuple(v) for k, v in (d.get("failed") or {}).items()},
                            raw_output=str(d.get("raw_output", ""))[-MAX_OUTPUT_CHARS:],
                            duration_ms=int(d.get("duration_ms") or (time.time() - t_start) * 1000),
                            integrity_flags=list(d.get("integrity_flags", [])))


def run_project_tests(repository_files: Dict[str, str], editable_files: List[str], candidate_files: Dict[str, str]) -> SandboxRunResult:
    t_start = time.time()
    # Only editable files may be overridden. Tests, fixtures and infrastructure stay authoritative.
    overlay = {p: c for p, c in candidate_files.items() if p in editable_files}
    flags = scan_candidate_files(overlay)
    if flags:
        return SandboxRunResult(
            status="error",
            raw_output="Integrity check failed. Tests were not executed.\n" + "\n".join(flags),
            duration_ms=int((time.time() - t_start) * 1000),
            integrity_flags=flags,
        )

    bwrap_bin = shutil.which("bwrap")
    executor_url = os.environ.get("EXECUTOR_URL")
    if not bwrap_bin and executor_url:
        # Production: the API container has no bubblewrap and holds the secrets, so project tests run in the
        # separate executor container (no app secrets) under the same hardened runner.
        return _run_via_executor(executor_url, repository_files, editable_files, overlay, t_start)
    environment, allow_unsandboxed = _env_flags()
    if not bwrap_bin and (environment == "production" or not allow_unsandboxed):
        raise AppException(
            "Project test sandbox is unavailable on this server, so candidate code was not executed.",
            code="SANDBOX_UNAVAILABLE",
            status_code=503,
        )

    expected = expected_test_names(repository_files)
    os.makedirs(BASE_SANDBOX_DIR, exist_ok=True)
    job_dir = tempfile.mkdtemp(prefix="job_", dir=BASE_SANDBOX_DIR)
    report_rel = f".r_{secrets.token_hex(16)}.xml"
    returncode: Optional[int] = None
    try:
        merged = dict(repository_files)
        merged.update(overlay)
        for rel_path, content in merged.items():
            dest = os.path.normpath(os.path.join(job_dir, rel_path))
            if not dest.startswith(job_dir + os.sep):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)

        if bwrap_bin:
            cmd = _bwrap_command(bwrap_bin, job_dir, report_rel)
            env = {"PATH": "/usr/bin:/bin"}
        else:
            logger.warning("Running project tests WITHOUT bubblewrap (ALLOW_UNSANDBOXED_PROJECT_TESTS=true). Dev only.")
            cmd = [sys.executable, "-I", "-m", "pytest", "-p", "no:cacheprovider", "-o", "pythonpath=.", "-q", "--tb=short", f"--junitxml={report_rel}", "tests/"]
            env = {"PATH": "/usr/bin:/bin", "HOME": job_dir, "PYTHONPATH": job_dir}

        try:
            proc = subprocess.run(cmd, cwd=job_dir, env=env, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
            returncode = proc.returncode
            raw_output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        except subprocess.TimeoutExpired:
            raw_output = f"Execution timed out after {TIMEOUT_SECONDS:.0f}s."

        raw_output = raw_output.replace(job_dir, SANDBOX_WORKDIR)[-MAX_OUTPUT_CHARS:]
        report_path = os.path.join(job_dir, report_rel)
        duration_ms = int((time.time() - t_start) * 1000)

        if returncode is None or not os.path.exists(report_path):
            return SandboxRunResult(status="error", raw_output=raw_output, duration_ms=duration_ms)
        try:
            passed, failed, seen = _parse_junit(report_path)
        except ET.ParseError:
            return SandboxRunResult(status="error", raw_output=raw_output, duration_ms=duration_ms,
                                    integrity_flags=["Test report was malformed."])
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)

    # Cross-check the report against the authoritative test list and the exit code.
    integrity: List[str] = []
    # Parametrized tests report as name[param-id]; compare base names, but full ids must be unique.
    seen_base = {n.split("[", 1)[0] for n in seen}
    if expected and (len(seen) != len(set(seen)) or seen_base != expected):
        integrity.append("Reported tests do not match the challenge's test suite.")
    if returncode == 0 and failed:
        integrity.append("Exit code reports success but tests failed.")
    if returncode not in (0, 1):
        # 2 = interrupted / collection error, 3 = internal error, 4 = usage error, 5 = no tests
        status = "error"
    elif integrity:
        status = "error"
    else:
        status = "passed" if (passed and not failed and returncode == 0) else "failed"

    if integrity:
        logger.warning(f"Project test integrity mismatch: {integrity}")
        raw_output = "Integrity check failed: " + " ".join(integrity) + "\n\n" + raw_output
        passed, failed = [], {}

    return SandboxRunResult(status=status, passed=passed, failed=failed, raw_output=raw_output,
                            duration_ms=duration_ms, integrity_flags=integrity)
