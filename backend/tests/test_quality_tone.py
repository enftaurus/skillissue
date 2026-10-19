import pytest
from backend.app.providers.mock_provider import MockProvider
from backend.app.interviews.prompts import build_interviewer_system_prompt

BAD_SYCOPHANTIC_PHRASES = [
    "great answer",
    "that is fascinating",
    "awesome explanation",
    "profound journey",
    "as an ai interviewer",
    "tell me everything about your skills"
]

@pytest.mark.asyncio
async def test_interview_tone_and_anti_sycophancy():
    provider = MockProvider()

    # 1. Test initial question naturalness and length
    sys_prompt = build_interviewer_system_prompt(
        category="technical",
        target_role="Backend Engineer",
        difficulty="intermediate",
        domain_skills=["Python", "FastAPI", "PostgreSQL", "Redis"]
    )

    r1 = await provider.generate_text(
        prompt="Candidate is ready. Ask first question.",
        system_prompt=sys_prompt
    )

    r1_lower = r1.text.lower()
    for phrase in BAD_SYCOPHANTIC_PHRASES:
        assert phrase not in r1_lower, f"Found sycophantic AI phrase: '{phrase}'"

    # Should ask a concise question (under 4 sentences)
    sentences = [s.strip() for s in r1.text.split(".") if s.strip()]
    assert len(sentences) <= 4, "Interviewer question is too long or compound"

    # 2. Test adaptive skepticism to unverified 10x faster claim
    r2 = await provider.generate_text(
        prompt="Respond to candidate",
        system_prompt=sys_prompt,
        conversation_history=[
            {"role": "assistant", "content": "How did you design your session cache?"},
            {"role": "user", "content": "We added Redis and it made everything 10x faster."}
        ]
    )

    r2_lower = r2.text.lower()
    # Must challenge or probe the measurement/latency
    assert any(term in r2_lower for term in ["measure", "latency", "redis", "how did you"]), (
        f"Interviewer failed to challenge unverified claim: {r2.text}"
    )
    for phrase in BAD_SYCOPHANTIC_PHRASES:
        assert phrase not in r2_lower
