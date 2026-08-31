"""Tests for Judge approval and best-draft ranking rules."""

import pytest

from src.ResponseModel import JudgeResult, RequestCheck


def make_result(
    scores: dict[str, int], *, requirement_satisfied: bool = True
) -> JudgeResult:
    return JudgeResult(
        request_checks=[
            RequestCheck(
                requirement="Include Ruby",
                satisfied=requirement_satisfied,
                evidence="Ruby is present." if requirement_satisfied else "Ruby is absent.",
            )
        ],
        scores=scores,
        strengths=[],
        issues=[],
        revision_instructions=[],
    )


@pytest.mark.parametrize(
    "criterion",
    [
        "age_appropriateness",
        "bedtime_suitability",
        "request_adherence",
        "safety",
    ],
)
def test_hard_requirement_below_four_prevents_approval(
    valid_scores: dict[str, int], criterion: str
) -> None:
    valid_scores[criterion] = 3

    result = make_result(valid_scores)

    assert not result.hard_requirements_pass
    assert not result.approved


def test_failed_explicit_requirement_prevents_approval(
    valid_scores: dict[str, int],
) -> None:
    result = make_result(valid_scores, requirement_satisfied=False)

    assert result.failed_requirement_count == 1
    assert not result.approved


def test_low_average_prevents_approval(valid_scores: dict[str, int]) -> None:
    valid_scores.update(
        {
            "story_structure": 3,
            "creativity": 3,
            "clarity": 3,
            "age_appropriateness": 4,
            "bedtime_suitability": 4,
            "request_adherence": 4,
            "safety": 4,
        }
    )

    result = make_result(valid_scores)

    assert result.average_score < 4.0
    assert not result.approved


def test_quality_rank_prioritizes_hard_requirements(
    valid_scores: dict[str, int],
) -> None:
    safe_scores = {criterion: 4 for criterion in valid_scores}
    unsafe_scores = {criterion: 5 for criterion in valid_scores}
    unsafe_scores["safety"] = 3

    safe_result = make_result(safe_scores)
    unsafe_result = make_result(unsafe_scores)

    assert safe_result.quality_rank > unsafe_result.quality_rank


def test_quality_rank_prefers_fewer_failed_requirements(
    valid_scores: dict[str, int],
) -> None:
    passing_checks = make_result(valid_scores)
    failed_check = make_result(valid_scores, requirement_satisfied=False)

    assert passing_checks.quality_rank > failed_check.quality_rank
