"""Tests for bounded generation and revision orchestration."""

from types import SimpleNamespace
from typing import Any

import utils
from ResponseModel import StoryCategory


def judgment(
    *, approved: bool, average: float, minimum: int = 3
) -> SimpleNamespace:
    """Create a lightweight Judge stand-in with the ranking interface."""
    return SimpleNamespace(
        approved=approved,
        quality_rank=(approved, True, 0, minimum, average),
    )


def test_approved_initial_story_performs_no_revisions(monkeypatch: Any) -> None:
    approved = judgment(approved=True, average=4.5, minimum=4)
    revise_calls = []

    monkeypatch.setattr(utils, "generate_story", lambda request, category: "draft-0")
    monkeypatch.setattr(
        utils,
        "evaluate_story",
        lambda request, story, user_feedback="": approved,
    )
    monkeypatch.setattr(
        utils,
        "revise_story",
        lambda *args, **kwargs: revise_calls.append((args, kwargs)),
    )

    result = utils.generate_improved_story(
        "A rabbit story", StoryCategory.COMFORT
    )

    assert result.story == "draft-0"
    assert result.revisions_performed == 0
    assert result.selected_revision == 0
    assert revise_calls == []


def test_loop_stops_after_first_approved_revision(monkeypatch: Any) -> None:
    first_judgment = judgment(approved=False, average=3.5)
    second_judgment = judgment(approved=True, average=4.4, minimum=4)
    judgments = iter([first_judgment, second_judgment])
    revision_judgments = []

    monkeypatch.setattr(utils, "generate_story", lambda request, category: "draft-0")
    monkeypatch.setattr(
        utils,
        "evaluate_story",
        lambda request, story, user_feedback="": next(judgments),
    )

    def fake_revision(
        request: str,
        story: str,
        judge_result: object,
        category: StoryCategory,
        user_feedback: str = "",
    ) -> str:
        revision_judgments.append(judge_result)
        return "draft-1"

    monkeypatch.setattr(utils, "revise_story", fake_revision)

    result = utils.generate_improved_story(
        "A rabbit story", StoryCategory.COMFORT
    )

    assert result.story == "draft-1"
    assert result.revisions_performed == 1
    assert result.selected_revision == 1
    assert revision_judgments == [first_judgment]


def test_loop_stops_at_limit_and_reports_progress(monkeypatch: Any) -> None:
    judgments = iter(
        [
            judgment(approved=False, average=3.2),
            judgment(approved=False, average=3.5),
            judgment(approved=False, average=3.4),
        ]
    )
    revision_number = 0
    progress = []

    monkeypatch.setattr(utils, "generate_story", lambda request, category: "draft-0")
    monkeypatch.setattr(
        utils,
        "evaluate_story",
        lambda request, story, user_feedback="": next(judgments),
    )

    def fake_revision(*args: object, **kwargs: object) -> str:
        nonlocal revision_number
        revision_number += 1
        return f"draft-{revision_number}"

    monkeypatch.setattr(utils, "revise_story", fake_revision)

    result = utils.generate_improved_story(
        "A rabbit story",
        StoryCategory.COMFORT,
        on_revision=lambda current, maximum: progress.append((current, maximum)),
    )

    assert result.revisions_performed == utils.MAX_REVISIONS == 2
    assert progress == [(1, 2), (2, 2)]


def test_best_draft_can_be_earlier_than_last_revision(monkeypatch: Any) -> None:
    judgments = iter(
        [
            judgment(approved=False, average=3.5),
            judgment(approved=False, average=4.1),
            judgment(approved=False, average=3.7),
        ]
    )
    revision_number = 0

    monkeypatch.setattr(utils, "generate_story", lambda request, category: "draft-0")
    monkeypatch.setattr(
        utils,
        "evaluate_story",
        lambda request, story, user_feedback="": next(judgments),
    )

    def fake_revision(*args: object, **kwargs: object) -> str:
        nonlocal revision_number
        revision_number += 1
        return f"draft-{revision_number}"

    monkeypatch.setattr(utils, "revise_story", fake_revision)

    result = utils.generate_improved_story(
        "A rabbit story", StoryCategory.COMFORT
    )

    assert result.revisions_performed == 2
    assert result.selected_revision == 1
    assert result.story == "draft-1"


def test_category_and_latest_judgment_reach_each_revision(monkeypatch: Any) -> None:
    first_judgment = judgment(approved=False, average=3.1)
    second_judgment = judgment(approved=False, average=3.4)
    final_judgment = judgment(approved=True, average=4.3, minimum=4)
    judgments = iter([first_judgment, second_judgment, final_judgment])
    generation_categories = []
    revision_inputs = []

    def fake_generation(request: str, category: StoryCategory) -> str:
        generation_categories.append(category)
        return "draft-0"

    monkeypatch.setattr(utils, "generate_story", fake_generation)
    monkeypatch.setattr(
        utils,
        "evaluate_story",
        lambda request, story, user_feedback="": next(judgments),
    )

    def fake_revision(
        request: str,
        story: str,
        judge_result: object,
        category: StoryCategory,
        user_feedback: str = "",
    ) -> str:
        revision_inputs.append((judge_result, category))
        return f"draft-{len(revision_inputs)}"

    monkeypatch.setattr(utils, "revise_story", fake_revision)

    utils.generate_improved_story("A quest", StoryCategory.ADVENTURE)

    assert generation_categories == [StoryCategory.ADVENTURE]
    assert revision_inputs == [
        (first_judgment, StoryCategory.ADVENTURE),
        (second_judgment, StoryCategory.ADVENTURE),
    ]
