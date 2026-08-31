"""Tests for bounded correction of invalid Judge responses."""

import json
from typing import Any

import openai
import pytest

import src.judging as judging


def test_valid_judge_response_needs_one_call(
    monkeypatch: Any, valid_judge_payload: dict[str, object]
) -> None:
    calls = []

    def fake_call_model(**kwargs: object) -> str:
        calls.append(kwargs)
        return json.dumps(valid_judge_payload)

    monkeypatch.setattr(judging, "call_model", fake_call_model)

    result = judging.evaluate_story("A rabbit story", "A valid story")

    assert result.approved
    assert len(calls) == 1


def test_invalid_then_valid_response_retries_once(
    monkeypatch: Any, valid_judge_payload: dict[str, object]
) -> None:
    invalid_payload = dict(valid_judge_payload)
    invalid_payload["request_checks"] = []
    responses = iter([json.dumps(invalid_payload), json.dumps(valid_judge_payload)])
    prompts = []

    def fake_call_model(**kwargs: object) -> str:
        prompts.append(kwargs["user_prompt"])
        return next(responses)

    monkeypatch.setattr(judging, "call_model", fake_call_model)

    result = judging.evaluate_story("A rabbit story", "A valid story")

    assert result.approved
    assert len(prompts) == 2
    assert "Judge must return at least one request check" in prompts[1]


def test_two_invalid_responses_raise_value_error(
    monkeypatch: Any, valid_judge_payload: dict[str, object]
) -> None:
    invalid_payload = dict(valid_judge_payload)
    invalid_payload["request_checks"] = []
    calls = []

    def fake_call_model(**kwargs: object) -> str:
        calls.append(kwargs)
        return json.dumps(invalid_payload)

    monkeypatch.setattr(judging, "call_model", fake_call_model)

    with pytest.raises(ValueError, match="at least one request check"):
        judging.evaluate_story("A rabbit story", "A story")

    assert len(calls) == 2


def test_feedback_is_preserved_in_retry_prompt(
    monkeypatch: Any, valid_judge_payload: dict[str, object]
) -> None:
    invalid_payload = dict(valid_judge_payload)
    invalid_payload["request_checks"] = []
    responses = iter([json.dumps(invalid_payload), json.dumps(valid_judge_payload)])
    prompts = []

    def fake_call_model(**kwargs: object) -> str:
        prompts.append(kwargs["user_prompt"])
        return next(responses)

    monkeypatch.setattr(judging, "call_model", fake_call_model)

    judging.evaluate_story(
        "A rabbit story",
        "An updated story",
        user_feedback="Make Grandma part of the solution.",
    )

    assert len(prompts) == 2
    assert "Make Grandma part of the solution." in prompts[0]
    assert "Make Grandma part of the solution." in prompts[1]


def test_api_error_is_not_retried(monkeypatch: Any) -> None:
    calls = []

    def failing_call_model(**kwargs: object) -> str:
        calls.append(kwargs)
        raise openai.error.OpenAIError("API unavailable")

    monkeypatch.setattr(judging, "call_model", failing_call_model)

    with pytest.raises(openai.error.OpenAIError, match="API unavailable"):
        judging.evaluate_story("A rabbit story", "A story")

    assert len(calls) == 1
