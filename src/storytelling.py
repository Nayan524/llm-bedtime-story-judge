"""Story generation and revision operations."""

from .call_llm import call_model
from .prompts import (
    STORYTELLER_SYSTEM_PROMPT,
    build_story_generation_prompt,
    build_story_revision_prompt,
    build_user_feedback_revision_prompt,
    get_category_strategy,
)
from .ResponseModel import JudgeResult, StoryCategory


def generate_story(user_request: str, category: StoryCategory) -> str:
    """Generate an age-appropriate bedtime story for a user request."""
    category_strategy = get_category_strategy(category)
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_generation_prompt(
            user_request=user_request,
            category=category,
            category_strategy=category_strategy,
        ),
    )


def revise_story(
    user_request: str,
    story: str,
    judge_result: JudgeResult,
    category: StoryCategory,
    user_feedback: str = "",
) -> str:
    """Ask the Storyteller to revise one story using Judge feedback."""
    failed_requirements = [
        f"{check.requirement} Evidence: {check.evidence}"
        for check in judge_result.request_checks
        if not check.satisfied
    ]
    category_strategy = get_category_strategy(category)
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_revision_prompt(
            user_request=user_request,
            story=story,
            strengths=judge_result.strengths,
            issues=judge_result.issues,
            revision_instructions=judge_result.revision_instructions,
            failed_requirements=failed_requirements,
            category=category,
            category_strategy=category_strategy,
            user_feedback=user_feedback,
        ),
    )


def revise_story_from_user_feedback(
    user_request: str,
    story: str,
    user_feedback: str,
    category: StoryCategory,
) -> str:
    """Revise a selected story once using the user's explicit feedback."""
    category_strategy = get_category_strategy(category)
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_user_feedback_revision_prompt(
            user_request=user_request,
            story=story,
            user_feedback=user_feedback,
            category=category,
            category_strategy=category_strategy,
        ),
    )
