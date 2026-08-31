"""Tests for feedback collection, history, and improvement orchestration."""

from types import SimpleNamespace
from typing import Any

import pytest

import src.feedback as feedback
import src.improvement as improvement
from src.ResponseModel import StoryCategory


@pytest.mark.parametrize("choice", ["keep", "k", "KEEP", " K "])
def test_keep_choice_returns_no_feedback(
    monkeypatch: Any, choice: str
) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: choice)

    assert feedback.collect_user_feedback() is None


@pytest.mark.parametrize("choice", ["change", "c", "CHANGE", " C "])
def test_change_choice_returns_feedback(monkeypatch: Any, choice: str) -> None:
    answers = iter([choice, "Make the ending funnier"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert feedback.collect_user_feedback() == "Make the ending funnier"


def test_invalid_choice_reprompts(monkeypatch: Any, capsys: Any) -> None:
    answers = iter(["maybe", "keep"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert feedback.collect_user_feedback() is None
    assert "Please enter 'keep' or 'change'." in capsys.readouterr().out


def test_empty_feedback_reprompts(monkeypatch: Any, capsys: Any) -> None:
    answers = iter(["change", "  ", "Make it shorter"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert feedback.collect_user_feedback() == "Make it shorter"
    assert "Please describe the change" in capsys.readouterr().out


def test_feedback_history_is_numbered_in_order() -> None:
    result = feedback.format_feedback_history(
        ["Add Grandma", "Make the ending shorter"]
    )

    assert result == (
        "Feedback round 1: Add Grandma\n"
        "Feedback round 2: Make the ending shorter"
    )


def test_approved_feedback_draft_needs_no_automatic_revision(
    monkeypatch: Any,
) -> None:
    approved = SimpleNamespace(
        approved=True,
        quality_rank=(True, True, 0, 4, 4.5),
    )
    revisions = []
    evaluations = []

    def fake_evaluation(
        request: str, story: str, user_feedback: str = ""
    ) -> object:
        evaluations.append((story, user_feedback))
        return approved

    monkeypatch.setattr(improvement, "evaluate_story", fake_evaluation)
    monkeypatch.setattr(
        improvement,
        "revise_story",
        lambda *args, **kwargs: revisions.append((args, kwargs)),
    )

    result = improvement.improve_feedback_story(
        user_request="A rabbit story",
        story="Feedback draft",
        user_feedback="Add Grandma",
        category=StoryCategory.COMFORT,
    )

    assert result.story == "Feedback draft"
    assert result.revisions_performed == 0
    assert evaluations == [("Feedback draft", "Add Grandma")]
    assert revisions == []


def test_feedback_reaches_every_evaluation_and_revision(
    monkeypatch: Any,
) -> None:
    rejected = SimpleNamespace(
        approved=False,
        quality_rank=(False, True, 0, 3, 3.5),
    )
    approved = SimpleNamespace(
        approved=True,
        quality_rank=(True, True, 0, 4, 4.4),
    )
    judgments = iter([rejected, approved])
    evaluations = []
    revisions = []

    def fake_evaluation(
        request: str, story: str, user_feedback: str = ""
    ) -> object:
        evaluations.append(user_feedback)
        return next(judgments)

    def fake_revision(
        request: str,
        story: str,
        judge_result: object,
        category: StoryCategory,
        user_feedback: str = "",
    ) -> str:
        revisions.append(user_feedback)
        return "Automatic revision"

    monkeypatch.setattr(improvement, "evaluate_story", fake_evaluation)
    monkeypatch.setattr(improvement, "revise_story", fake_revision)

    result = improvement.improve_feedback_story(
        user_request="A rabbit story",
        story="Feedback draft",
        user_feedback="Feedback round 1: Add Grandma",
        category=StoryCategory.COMFORT,
    )

    assert result.story == "Automatic revision"
    assert evaluations == [
        "Feedback round 1: Add Grandma",
        "Feedback round 1: Add Grandma",
    ]
    assert revisions == ["Feedback round 1: Add Grandma"]
