"""Shared pytest fixtures for bedtime-story unit tests."""

import pytest


@pytest.fixture
def valid_scores() -> dict[str, int]:
    """Return scores that satisfy every approval threshold."""
    return {
        "age_appropriateness": 5,
        "bedtime_suitability": 5,
        "request_adherence": 5,
        "story_structure": 4,
        "creativity": 4,
        "clarity": 4,
        "safety": 5,
    }


@pytest.fixture
def valid_judge_payload(valid_scores: dict[str, int]) -> dict[str, object]:
    """Return a complete valid Judge response payload."""
    return {
        "request_checks": [
            {
                "requirement": "Include a rabbit named Ruby",
                "satisfied": True,
                "evidence": "Ruby is the main rabbit character.",
            }
        ],
        "scores": valid_scores,
        "strengths": ["The story has a calming ending."],
        "issues": [],
        "revision_instructions": [],
    }
