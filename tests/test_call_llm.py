"""Tests for the isolated OpenAI model-call boundary."""

from types import SimpleNamespace
from typing import Any

import openai
import pytest

import src.call_llm as call_llm
from src.config import MODEL_NAME


def test_call_model_sends_roles_and_generation_settings(monkeypatch: Any) -> None:
    captured = {}

    monkeypatch.setattr(call_llm, "get_openai_api_key", lambda: "test-key")

    def fake_create(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message={"content": "  Story text  "})]
        )

    monkeypatch.setattr(call_llm.openai.ChatCompletion, "create", fake_create)

    result = call_llm.call_model(
        system_prompt="System instructions",
        user_prompt="User request",
        max_tokens=321,
        temperature=0.6,
    )

    assert result == "Story text"
    assert call_llm.openai.api_key == "test-key"
    assert captured == {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "User request"},
        ],
        "stream": False,
        "max_tokens": 321,
        "temperature": 0.6,
    }


def test_call_model_propagates_api_errors(monkeypatch: Any) -> None:
    calls = []
    monkeypatch.setattr(call_llm, "get_openai_api_key", lambda: "test-key")

    def failing_create(**kwargs: object) -> object:
        calls.append(kwargs)
        raise openai.error.OpenAIError("API unavailable")

    monkeypatch.setattr(call_llm.openai.ChatCompletion, "create", failing_create)

    with pytest.raises(openai.error.OpenAIError, match="API unavailable"):
        call_llm.call_model("system", "user")

    assert len(calls) == 1
