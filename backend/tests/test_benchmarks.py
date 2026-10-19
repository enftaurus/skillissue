import pytest
from scripts.run_benchmarks import BENCHMARK_CASES
from backend.app.providers.mock_provider import MockProvider
from backend.app.evaluations.prompts import build_evaluation_prompt
from backend.app.interviews.rubrics import get_rubric_for_category

@pytest.mark.asyncio
async def test_evaluator_benchmark_calibration():
    provider = MockProvider()
    for case in BENCHMARK_CASES:
        rubric = get_rubric_for_category(case["category"])
        sys_p, user_p = build_evaluation_prompt(
            category=case["category"],
            target_role=case["role"],
            rubric=rubric,
            transcript_text=case["transcript"]
        )
        res = await provider.generate_json(prompt=user_p, system_prompt=sys_p)
        assert res.parsed_json is not None
        assert "overall_score" in res.parsed_json
        assert "dimension_scores" in res.parsed_json
        assert "strengths" in res.parsed_json
        assert "weaknesses" in res.parsed_json
        assert len(res.parsed_json["strengths"]) > 0
        assert len(res.parsed_json["weaknesses"]) > 0
