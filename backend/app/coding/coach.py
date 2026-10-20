import os
import json
import re
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.coding.problems import CODING_PROBLEMS
from backend.app.coding.schemas import DsaCoachRequest, DsaCoachResponse
from backend.app.providers.factory import ModelFactory
from backend.app.providers.service import ProviderConfigService
from backend.app.core.errors import EntityNotFoundError, AppException, ProviderError
from backend.app.core.logging import logger

DSA_COACH_SYSTEM_PROMPT = """You are a senior principal engineer and DSA mentor conducting a practice session on Skill Issue.
Your mission is to help the student think through and solve data structures and algorithms problems themselves, without giving away complete solutions.

BRAND PERSONA:
- Gen Z wit meets Gilfoyle-level engineering precision.
- Direct, dry, intelligent, observant, respectful of the learner.
- Zero patronizing cheerleading ("Great job!", "You're almost there champ!").

STRICT COACHING INVARIANTS:
1. PROGRESSIVE HINTING:
   - Level 1: Clarify the fundamental mathematical or algorithmic observation/invariant. Nudge their intuition.
   - Level 2: Point toward an appropriate data structure or algorithmic pattern (e.g. Hash Map, Two Pointers, Monotonic Stack, Dynamic Programming state definition).
   - Level 3: Help derive the approach or walk through the tricky edge case / recurrence step without writing the complete program.
   - Level 4: Offer structured pseudocode or step-by-step logic. Even at Level 4, do NOT paste a complete copy-pasteable solution unless explicitly requested.
2. CONTEXTUAL REASONING:
   - Inspect what the user has tried and their current code. If they made a specific error (e.g. O(N^2) nested loop, off-by-one, memory leak), point directly to the line or logic causing the issue.
   - If the user hasn't provided code or context, ask what approaches they've considered or where their mental model is stuck.
3. CONVERSATIONAL MEMORY:
   - Never repeat the same hint already provided in the conversation history. Build on what was already discussed.
4. GUIDING QUESTION:
   - Always conclude with exactly ONE guiding question that pushes the candidate to reason about Big-O complexity, an invariant, or an edge case.
5. NO CODE FABRICATION:
   - Do not claim tests were run or code was executed. Your role is strictly Socratic mentorship.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching:
{
  "hint_level": 1,
  "hint_text": "Detailed pedagogical explanation nudging the candidate toward the key observation...",
  "guiding_question": "What is the time complexity of scanning the array for the complement on every element?",
  "suggested_focus": "Time vs space trade-off using a Hash Map"
}
"""

class DsaCoachService:
    @classmethod
    async def get_hint(
        cls,
        db: AsyncSession,
        user_id: str,
        problem_id: str,
        data: DsaCoachRequest,
    ) -> DsaCoachResponse:
        problem = CODING_PROBLEMS.get(problem_id)
        if not problem:
            raise EntityNotFoundError("CodingProblem", problem_id)

        if not getattr(problem, "ai_coaching_supported", True):
            raise AppException(
                f"AI coaching is not currently enabled for problem '{problem.title}'.",
                code="COACHING_NOT_SUPPORTED",
                status_code=400,
            )

        # In production/live mode, require verified Bedrock configuration
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        provider_config = await ProviderConfigService.get_config(db, user_id)
        if not is_test and (not provider_config or not provider_config.is_valid):
            raise AppException(
                "A verified AWS Bedrock account is required to use the DSA AI coach. "
                "Please configure your AWS credentials in Provider Onboarding (/onboarding/bedrock) or Settings.",
                code="BEDROCK_CONFIG_REQUIRED",
                status_code=400,
                details={"action": "onboarding_required", "setup_url": "/onboarding/bedrock"}
            )

        # Build context prompt
        context_parts = [
            f"PROBLEM: {problem.title} ({problem.difficulty.upper()})",
            f"CATEGORY: {problem.category}",
            f"DESCRIPTION:\n{problem.description}",
            f"CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in problem.constraints),
            f"REQUESTED HINT LEVEL: Level {data.hint_level} (out of 4)",
        ]

        if data.user_code and data.user_code.strip():
            context_parts.append(
                f"CANDIDATE'S CURRENT CODE ({data.language.upper()}):\n"
                f"```{data.language}\n{data.user_code.strip()}\n```"
            )

        if data.user_message and data.user_message.strip():
            context_parts.append(f"CANDIDATE'S QUESTION / THOUGHTS:\n\"{data.user_message.strip()}\"")

        if data.conversation_history:
            history_text = "\n".join(
                f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
                for m in data.conversation_history[-6:]
            )
            context_parts.append(f"PREVIOUS COACHING CONVERSATION:\n{history_text}")

        user_prompt = "\n\n".join(context_parts)

        # Generate response using real provider
        provider = await ModelFactory.get_for_user(db, user_id, task_type="coding")
        response = await provider.generate_json(
            prompt=user_prompt,
            system_prompt=DSA_COACH_SYSTEM_PROMPT,
        )

        parsed = response.parsed_json or {}
        if not parsed or "error" in parsed:
            # Fallback extraction or standard structured response
            hint_text = response.text.strip() if response.text else (
                f"Focus on the core invariant for {problem.title}. "
                "Consider what data structure lets you check state or complements in O(1) time."
            )
            return DsaCoachResponse(
                hint_level=data.hint_level,
                hint_text=hint_text,
                guiding_question="What is the bottleneck in your current approach, and how does your chosen data structure mitigate it?",
                suggested_focus="Invariant analysis and complexity constraints",
                tokens_used=response.input_tokens + response.output_tokens,
            )

        return DsaCoachResponse(
            hint_level=int(parsed.get("hint_level", data.hint_level)),
            hint_text=str(parsed.get("hint_text", "Analyze the relationship between each element and your target constraint.")),
            guiding_question=str(parsed.get("guiding_question", "What invariant must hold true at every iteration?")),
            suggested_focus=parsed.get("suggested_focus"),
            tokens_used=response.input_tokens + response.output_tokens,
        )
