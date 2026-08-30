"""Tests for structured Judge-response parsing and validation."""

import copy
import json

import pytest

from utils import parse_judge_result


def test_parse_valid_judge_result(valid_judge_payload: dict[str, object]) -> None:
    result = parse_judge_result(json.dumps(valid_judge_payload))

    assert result.approved
    assert result.request_checks[0].satisfied
    assert result.strengths == ["The story has a calming ending."]


def test_reject_empty_request_checks(
    valid_judge_payload: dict[str, object],
) -> None:
    valid_judge_payload["request_checks"] = []

    with pytest.raises(ValueError, match="at least one request check"):
        parse_judge_result(json.dumps(valid_judge_payload))


def test_reject_unexpected_score_field(
    valid_judge_payload: dict[str, object],
) -> None:
    scores = valid_judge_payload["scores"]
    assert isinstance(scores, dict)
    scores["surprise"] = 5

    with pytest.raises(ValueError, match="missing or unexpected score fields"):
        parse_judge_result(json.dumps(valid_judge_payload))


@pytest.mark.parametrize("invalid_score", [0, 6, 3.5, "5", True])
def test_reject_invalid_score(
    valid_judge_payload: dict[str, object], invalid_score: object
) -> None:
    scores = valid_judge_payload["scores"]
    assert isinstance(scores, dict)
    scores["clarity"] = invalid_score

    with pytest.raises(ValueError, match="integer from 1 to 5"):
        parse_judge_result(json.dumps(valid_judge_payload))


def test_one_failed_requirement_caps_adherence_at_three(
    valid_judge_payload: dict[str, object],
) -> None:
    payload = copy.deepcopy(valid_judge_payload)
    checks = payload["request_checks"]
    assert isinstance(checks, list)
    checks[0]["satisfied"] = False

    result = parse_judge_result(json.dumps(payload))

    assert result.scores["request_adherence"] == 3
    assert not result.approved


def test_multiple_failed_requirements_cap_adherence_at_two(
    valid_judge_payload: dict[str, object],
) -> None:
    payload = copy.deepcopy(valid_judge_payload)
    payload["request_checks"] = [
        {
            "requirement": "Use four paragraphs",
            "satisfied": False,
            "evidence": "The story uses three paragraphs.",
        },
        {
            "requirement": "End with an exact sentence",
            "satisfied": False,
            "evidence": "The final sentence is different.",
        },
    ]

    result = parse_judge_result(json.dumps(payload))

    assert result.scores["request_adherence"] == 2
    assert not result.approved
