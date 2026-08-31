"""Tests for Request Classifier response validation."""

import json

import pytest

from src.ResponseModel import StoryCategory
from src.classification import parse_classification_result


def test_parse_valid_classification() -> None:
    raw_result = json.dumps(
        {
            "category": "comfort",
            "reason": "The request centers on overcoming a fear.",
        }
    )

    result = parse_classification_result(raw_result)

    assert result.category is StoryCategory.COMFORT
    assert result.reason == "The request centers on overcoming a fear."


@pytest.mark.parametrize(
    "raw_result, expected_message",
    [
        ("not JSON", "invalid JSON"),
        (
            json.dumps({"category": "mystery", "reason": "A mystery."}),
            "unsupported category",
        ),
        (
            json.dumps({"category": "comfort", "reason": ""}),
            "non-empty string",
        ),
        (
            json.dumps(
                {"category": "comfort", "reason": "Valid", "extra": True}
            ),
            "category and reason",
        ),
    ],
)
def test_reject_invalid_classification(
    raw_result: str, expected_message: str
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        parse_classification_result(raw_result)
