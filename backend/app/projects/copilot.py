import os
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.projects.schemas import ProjectCopilotRequest, ProjectCopilotResponse
from backend.app.projects.repository import get_project
from backend.app.providers.factory import ModelFactory
from backend.app.providers.service import ProviderConfigService
from backend.app.core.logging import logger

COPILOT_SYSTEM_PROMPT = """You are a Principal Systems Engineer and Pair-Programming Mentor on Skill Issue.
You are pair-programming with a candidate on a Work Simulation challenge.

STRICT READ-ONLY GUARDRAIL INVARIANTS:
1. You have READ-ONLY access to the repository files and candidate's editor buffer.
2. You CANNOT write, mutate, edit, or create files directly in the workspace.
3. If the candidate submits an amateurish or lazy prompt like "fix it", "write the code", "it doesn't work":
   - Remind them dryly that you cannot write to their editor.
   - Point them directly to the specific file and function where the issue lies.
   - Give a concise architectural hint or targeted snippet (10-20 lines) and explain where to place it.
4. BRAND PERSONA:
   - Direct, dry, intelligent, observant, respectful of the learner.
   - Zero patronizing cheerleading ("Great job!", "Fascinating question!").
5. ACCURACY:
   - Use the candidate's active file, current code, and recent test failure tracebacks to answer accurately.
   - Always mention the file path (e.g. `src/limiter.py`) and line numbers.
"""

def generate_heuristic_copilot_response(
    project_id: str,
    message: str,
    files: Dict[str, str],
    active_file: Optional[str],
    last_test_results: Optional[Dict[str, Any]],
) -> str:
    msg_lower = message.lower().strip()

    # Check for amateurish prompts
    is_amateur = any(p in msg_lower for p in [
        "fix it", "fix my code", "give me code", "give me the code", "code it for me",
        "doesn't work", "doesnt work", "why is it broken", "help", "do it"
    ]) and len(msg_lower.split()) <= 6

    if project_id == "distributed-rate-limiter":
        current_limiter = files.get("src/limiter.py", "")
        has_sliding_window = "zremrangebyscore" in current_limiter and "zcard" in current_limiter

        if is_amateur:
            return (
                "I have read-only access to your repository and cannot modify files on your behalf. "
                "Looking at `src/limiter.py`, your rate limiter currently permits all requests without tracking timestamps.\n\n"
                "To pass the tests, you need to implement the sliding window counter in `is_rate_limited`:\n"
                "1. Clean expired requests: `self.storage.zremrangebyscore(key, 0.0, now - self.window_seconds)`\n"
                "2. Check active count: `current_count = self.storage.zcard(key)`\n"
                "3. If under `self.max_requests`, add the current timestamp with `self.storage.zadd(key, {str(uuid.uuid4()): now})`.\n\n"
                "Where in `is_rate_limited` are you currently calculating the `reset_after_seconds`?"
            )

        if "explain" in msg_lower or "architecture" in msg_lower or "how" in msg_lower:
            return (
                "### Architecture Overview: Distributed Rate Limiter\n\n"
                "- **`src/storage.py`**: A thread-safe Redis mock providing Sorted Set operations (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`).\n"
                "- **`src/limiter.py`**: Where your logic belongs. Uses client-specific keys like `ratelimit:{client_id}`.\n"
                "- **`src/server.py`**: The HTTP middleware extracting `X-RateLimit-*` headers and translating rejections into HTTP 429.\n\n"
                "The core mechanism is a **Sliding Window Log**: each request records a timestamp into Redis. "
                "Any timestamp older than `now - window_seconds` is purged before counting."
            )

        if "fail" in msg_lower or "test" in msg_lower or "error" in msg_lower:
            return (
                "Inspect `tests/test_rate_limiter.py`:\n"
                "- `test_blocks_requests_exceeding_limit`: Expects the 6th request within the window to return `is_allowed=False`.\n"
                "- `test_rate_limit_headers_calculation`: Needs `remaining` to accurately decrement (`max_requests - current_count - 1`).\n\n"
                "In `src/limiter.py`, ensure you call `self.storage.zremrangebyscore(key, 0.0, now - self.window_seconds)` *before* checking `self.storage.zcard(key)`."
            )

        return (
            "In `src/limiter.py`, make sure you use `self.storage.zadd(key, {str(uuid.uuid4()): now})` "
            "and `self.storage.expire(key, self.window_seconds)` when permitting a request. "
            "For denied requests, calculate `reset_after_seconds` using the oldest entry in `self.storage.zrangebyscore`."
        )

    elif project_id == "async-job-queue":
        if is_amateur:
            return (
                "I cannot edit `src/dispatcher.py` directly because my permissions are strictly read-only.\n\n"
                "Your dispatcher is currently popping tasks strictly via FIFO without checking `task.priority`.\n"
                "To fix `test_priority_scheduling`:\n"
                "```python\n"
                "def get_next_task(self) -> Optional[Task]:\n"
                "    if not self.queue:\n"
                "        return None\n"
                "    # Priority HIGH (1) before NORMAL (2) before LOW (3), then sequence_id\n"
                "    self.queue.sort(key=lambda t: (t.priority.value, t.sequence_id))\n"
                "    return self.queue.pop(0)\n"
                "```\n"
                "Try placing that in `src/dispatcher.py` and run your CI/CD tests."
            )

        if "backoff" in msg_lower:
            return (
                "For exponential backoff in `calculate_backoff(self, task: Task)`:\n"
                "The mathematical formula is `base_delay * (2 ** retry_count)`.\n"
                "```python\n"
                "return float(task.base_delay * (2 ** task.retry_count))\n"
                "```\n"
                "Make sure you cast to float to match the test assertion."
            )

        if "dead letter" in msg_lower or "dlq" in msg_lower or "hook" in msg_lower:
            return (
                "In `handle_failure(self, task: Task, error: Exception)`:\n"
                "1. Increment `task.retry_count += 1`\n"
                "2. If `task.retry_count < task.max_retries`: set `task.status = TaskStatus.RETRYING` and re-enqueue.\n"
                "3. Else: set `task.status = TaskStatus.DEAD_LETTER`, append to `self.dead_letter_queue`, and invoke "
                "`self.dead_letter_hook.on_task_dead_letter(task, error)` if present."
            )

        return (
            "Focus on `src/dispatcher.py`. You need to implement:\n"
            "1. Priority ordering in `get_next_task()`\n"
            "2. Backoff formula `base_delay * (2 ** retry_count)` in `calculate_backoff()`\n"
            "3. State machine transitions to `RETRYING` vs `DEAD_LETTER` in `handle_failure()`."
        )

    return "I am reviewing your project files in read-only mode. What specific component or test failure would you like to examine?"

class ProjectCopilotService:
    @classmethod
    async def ask_copilot(
        cls,
        db: AsyncSession,
        user_id: str,
        project_id: str,
        data: ProjectCopilotRequest,
    ) -> ProjectCopilotResponse:
        project = get_project(project_id)
        if not project:
            return ProjectCopilotResponse(
                message=f"Unknown project ID '{project_id}'.",
                tokens_used=0
            )

        # Build context
        files_summary = []
        for path, content in data.files.items():
            files_summary.append(f"--- FILE: {path} ---\n{content[:2000]}\n")
        files_text = "\n".join(files_summary)

        test_context = ""
        if data.last_test_results:
            passed = data.last_test_results.get("passed_tests", 0)
            total = data.last_test_results.get("total_tests", 0)
            test_context = f"\nLATEST TEST RESULTS: {passed}/{total} Passed\nRAW OUTPUT:\n{data.last_test_results.get('raw_output', '')[-800:]}"

        user_prompt = (
            f"PROJECT: {project.title} ({project.domain})\n"
            f"ACTIVE FILE: {data.active_file or 'None'}\n"
            f"{test_context}\n\n"
            f"CURRENT WORKSPACE FILES:\n{files_text}\n\n"
            f"CANDIDATE QUESTION:\n{data.message}"
        )

        # Attempt to use real LLM provider
        try:
            provider = await ModelFactory.get_for_user(db, user_id, task_type="coding")
            response = await provider.generate(
                prompt=user_prompt,
                system_prompt=COPILOT_SYSTEM_PROMPT,
            )
            if response and response.text and response.text.strip():
                return ProjectCopilotResponse(
                    message=response.text.strip(),
                    tokens_used=response.input_tokens + response.output_tokens
                )
        except Exception as e:
            logger.warning(f"Project Copilot LLM provider failed, using heuristic: {e}")

        # Fallback to authentic heuristic response
        heuristic_reply = generate_heuristic_copilot_response(
            project_id=project_id,
            message=data.message,
            files=data.files,
            active_file=data.active_file,
            last_test_results=data.last_test_results,
        )
        return ProjectCopilotResponse(
            message=heuristic_reply,
            tokens_used=120
        )
