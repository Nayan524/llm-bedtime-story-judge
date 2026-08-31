"""Tests for category strategies and prompt data propagation."""

from ResponseModel import StoryCategory
from prompts import (
    CATEGORY_STRATEGIES,
    build_feedback_judge_evaluation_prompt,
    build_judge_retry_prompt,
    build_story_generation_prompt,
    build_story_revision_prompt,
    build_user_feedback_revision_prompt,
    get_category_strategy,
)


def test_every_category_has_a_non_empty_strategy() -> None:
    assert set(CATEGORY_STRATEGIES) == set(StoryCategory)
    assert all(strategy.strip() for strategy in CATEGORY_STRATEGIES.values())


def test_generation_prompt_contains_category_and_strategy() -> None:
    strategy = get_category_strategy(StoryCategory.EDUCATIONAL)

    prompt = build_story_generation_prompt(
        user_request="Teach me about the Moon",
        category=StoryCategory.EDUCATIONAL,
        category_strategy=strategy,
    )

    assert "<story_category>\neducational\n</story_category>" in prompt
    assert strategy in prompt
    assert "Teach me about the Moon" in prompt


def test_judge_revision_prompt_contains_all_revision_inputs() -> None:
    strategy = get_category_strategy(StoryCategory.ADVENTURE)

    prompt = build_story_revision_prompt(
        user_request="A forest quest",
        story="Current draft",
        strengths=["Memorable characters"],
        issues=["The ending is rushed"],
        revision_instructions=["Add a calm final scene"],
        failed_requirements=["Include a silver key"],
        category=StoryCategory.ADVENTURE,
        category_strategy=strategy,
        user_feedback="Feedback round 1: Make it shorter",
    )

    for expected in (
        "A forest quest",
        "Current draft",
        "Memorable characters",
        "The ending is rushed",
        "Add a calm final scene",
        "Include a silver key",
        "Feedback round 1: Make it shorter",
        strategy,
    ):
        assert expected in prompt


def test_user_feedback_prompt_gives_later_round_precedence() -> None:
    strategy = get_category_strategy(StoryCategory.COMFORT)
    feedback = (
        "Feedback round 1: End with sentence A.\n"
        "Feedback round 2: Replace the ending with sentence B."
    )

    prompt = build_user_feedback_revision_prompt(
        user_request="A rabbit faces a storm",
        story="Current story",
        user_feedback=feedback,
        category=StoryCategory.COMFORT,
        category_strategy=strategy,
    )

    assert feedback in prompt
    assert "later\nround override an earlier round" in prompt
    assert "explicit user\nfeedback takes priority" in prompt


def test_feedback_judge_prompt_treats_feedback_as_requirements() -> None:
    prompt = build_feedback_judge_evaluation_prompt(
        user_request="A rabbit story",
        user_feedback="Add Grandma to the solution",
        story="Updated story",
    )

    assert "Add Grandma to the solution" in prompt
    assert "additional request requirement" in prompt
    assert "Updated story" in prompt


def test_judge_retry_prompt_preserves_error_and_feedback() -> None:
    prompt = build_judge_retry_prompt(
        user_request="A rabbit story",
        story="Updated story",
        validation_error="request_checks cannot be empty",
        user_feedback="Feedback round 1: Add Grandma",
    )

    assert "request_checks cannot be empty" in prompt
    assert "Feedback round 1: Add Grandma" in prompt
    assert "later round overrides" in prompt
