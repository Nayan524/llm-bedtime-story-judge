"""Tests for top-level CLI coordination with all external work mocked."""

from types import SimpleNamespace
from typing import Any

import main
from ResponseModel import StoryCategory


def story_result(story: str) -> SimpleNamespace:
    return SimpleNamespace(
        story=story,
        revisions_performed=0,
        selected_revision=0,
        judge_result=object(),
    )


def test_empty_request_exits_before_classification(
    monkeypatch: Any, capsys: Any
) -> None:
    classifier_calls = []
    monkeypatch.setattr("builtins.input", lambda prompt: "  ")
    monkeypatch.setattr(
        main,
        "classify_story_request",
        lambda request: classifier_calls.append(request),
    )

    main.main()

    assert classifier_calls == []
    assert "Please provide a short description" in capsys.readouterr().out


def test_keep_exits_without_feedback_revision(monkeypatch: Any) -> None:
    revision_calls = []
    monkeypatch.setattr("builtins.input", lambda prompt: "A rabbit story")
    monkeypatch.setattr(
        main,
        "classify_story_request",
        lambda request: SimpleNamespace(
            category=StoryCategory.COMFORT,
            reason="The request centers on reassurance.",
        ),
    )
    monkeypatch.setattr(
        main,
        "generate_improved_story",
        lambda *args, **kwargs: story_result("Initial story"),
    )
    monkeypatch.setattr(main, "print_judge_report", lambda result: None)
    monkeypatch.setattr(main, "collect_user_feedback", lambda: None)
    monkeypatch.setattr(
        main,
        "revise_story_from_user_feedback",
        lambda **kwargs: revision_calls.append(kwargs),
    )

    main.main()

    assert revision_calls == []


def test_two_feedback_rounds_accumulate_and_use_latest_story(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setattr(main, "MAX_USER_FEEDBACK_ROUNDS", 2)
    monkeypatch.setattr("builtins.input", lambda prompt: "A rabbit story")
    monkeypatch.setattr(
        main,
        "classify_story_request",
        lambda request: SimpleNamespace(
            category=StoryCategory.COMFORT,
            reason="Comfort",
        ),
    )
    monkeypatch.setattr(
        main,
        "generate_improved_story",
        lambda *args, **kwargs: story_result("Initial story"),
    )
    feedback = iter(["Add Grandma", "Make the ending shorter"])
    monkeypatch.setattr(main, "collect_user_feedback", lambda: next(feedback))
    revision_inputs = []

    def fake_feedback_revision(**kwargs: object) -> str:
        revision_inputs.append((kwargs["story"], kwargs["user_feedback"]))
        return "Feedback draft"

    monkeypatch.setattr(
        main, "revise_story_from_user_feedback", fake_feedback_revision
    )
    improved_results = iter(
        [story_result("Round 1 story"), story_result("Round 2 story")]
    )
    monkeypatch.setattr(
        main,
        "improve_feedback_story",
        lambda **kwargs: next(improved_results),
    )
    monkeypatch.setattr(main, "print_judge_report", lambda result: None)

    main.main()

    assert revision_inputs[0] == (
        "Initial story",
        "Feedback round 1: Add Grandma",
    )
    assert revision_inputs[1] == (
        "Round 1 story",
        "Feedback round 1: Add Grandma\n"
        "Feedback round 2: Make the ending shorter",
    )
    assert "Maximum feedback rounds reached" in capsys.readouterr().out


def test_classification_validation_error_is_user_facing(
    monkeypatch: Any, capsys: Any
) -> None:
    generation_calls = []
    monkeypatch.setattr("builtins.input", lambda prompt: "A rabbit story")

    def fail_classification(request: str) -> object:
        raise ValueError("invalid classifier response")

    monkeypatch.setattr(main, "classify_story_request", fail_classification)
    monkeypatch.setattr(
        main,
        "generate_improved_story",
        lambda *args, **kwargs: generation_calls.append((args, kwargs)),
    )

    main.main()

    assert generation_calls == []
    assert "Unable to classify the story request" in capsys.readouterr().out
