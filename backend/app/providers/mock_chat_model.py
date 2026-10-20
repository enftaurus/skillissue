from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field
import json
import asyncio
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.runnables import Runnable, RunnableLambda
from backend.app.providers.mock_provider import MockProvider

class MockChatModel(BaseChatModel):
    """
    LangChain BaseChatModel implementation of the Skill Issue Mock Engine.
    Provides deterministic, offline, zero-cost conversational responses
    and structured JSON outputs for development, testing, and CI.
    """
    model_id: str = "mock-qwen3-32b"
    temperature: float = 0.7
    max_tokens: int = 1000
    mock_provider: MockProvider = Field(default_factory=lambda: MockProvider("mock-qwen3-32b"))

    model_config = {
        "arbitrary_types_allowed": True
    }

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

    def _extract_messages(self, messages: List[BaseMessage]):
        system_prompt = None
        history: List[Dict[str, str]] = []
        last_prompt = ""

        for m in messages:
            if isinstance(m, SystemMessage):
                system_prompt = m.content
            elif isinstance(m, HumanMessage):
                history.append({"role": "user", "content": m.content})
                last_prompt = m.content
            elif isinstance(m, AIMessage):
                history.append({"role": "assistant", "content": m.content})

        return system_prompt, history, last_prompt

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        system_prompt, history, last_prompt = self._extract_messages(messages)
        # Run sync wrapper for mock provider
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = pool.submit(
                    asyncio.run,
                    self.mock_provider.generate_text(
                        prompt=last_prompt or "Continue interview",
                        system_prompt=system_prompt,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        conversation_history=history,
                    )
                ).result()
        else:
            res = asyncio.run(
                self.mock_provider.generate_text(
                    prompt=last_prompt or "Continue interview",
                    system_prompt=system_prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    conversation_history=history,
                )
            )

        gen = ChatGeneration(message=AIMessage(content=res.text))
        return ChatResult(generations=[gen])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        system_prompt, history, last_prompt = self._extract_messages(messages)
        res = await self.mock_provider.generate_text(
            prompt=last_prompt or "Continue interview",
            system_prompt=system_prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            conversation_history=history,
        )
        gen = ChatGeneration(message=AIMessage(content=res.text))
        return ChatResult(generations=[gen])

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        **kwargs: Any,
    ) -> Runnable[List[BaseMessage], Any]:
        """
        Returns a runnable that produces schema-validated structured output
        using the deterministic mock provider.
        """
        async def _run(messages: Union[List[BaseMessage], str, Dict[str, Any]]) -> Any:
            if isinstance(messages, str):
                messages = [HumanMessage(content=messages)]
            elif isinstance(messages, dict):
                # Prompt dictionary
                messages = [HumanMessage(content=str(messages))]

            system_prompt, history, last_prompt = self._extract_messages(messages)

            # Check if this is an adaptive decision schema
            schema_is_pydantic = isinstance(schema, type) and issubclass(schema, BaseModel)
            schema_fields = getattr(schema, "model_fields", {}) if schema_is_pydantic else {}

            if "decision" in schema_fields or "action" in schema_fields:
                prompt_lower = (last_prompt or "").lower()
                # Deterministic adaptive decision rules
                action = "next_topic"
                difficulty_delta = 0
                reason = "Candidate demonstrated clear understanding of architectural trade-offs."

                if "redis" in prompt_lower or "faster" in prompt_lower or "10x" in prompt_lower or "vague" in prompt_lower:
                    action = "ask_follow_up"
                    reason = "Candidate made an unverified latency claim; follow up on measurement methodology."
                elif "fail" in prompt_lower or "struggle" in prompt_lower or "error" in prompt_lower or "idk" in prompt_lower:
                    action = "decrease_difficulty"
                    difficulty_delta = -1
                    reason = "Candidate encountered difficulty with low-level concurrency mechanisms."
                elif "distributed" in prompt_lower or "raft" in prompt_lower or "paxos" in prompt_lower or "saga" in prompt_lower:
                    action = "increase_difficulty"
                    difficulty_delta = 1
                    reason = "Candidate articulated distributed consensus clearly; test edge-case partitioned networks."

                data = {
                    "action": action,
                    "reason": reason,
                    "difficulty_delta": difficulty_delta,
                    "suggested_topic": "system_design" if action == "next_topic" else None,
                    "confidence": 0.9,
                }
                if schema_is_pydantic:
                    return schema.model_validate(data)
                return data

            # General structured JSON output (e.g. evaluation, plans)
            res = await self.mock_provider.generate_json(
                prompt=last_prompt,
                system_prompt=system_prompt,
                schema=schema if isinstance(schema, dict) else schema.model_json_schema(),
                conversation_history=history,
            )

            parsed = res.parsed_json or {}
            if schema_is_pydantic:
                try:
                    return schema.model_validate(parsed)
                except Exception as e:
                    # In case of partial schema mismatch, fill defaults
                    return schema.model_validate(parsed, strict=False)
            return parsed

        return RunnableLambda(_run)
