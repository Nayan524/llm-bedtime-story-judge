"""Bounded story evaluation, revision, and draft selection."""

from typing import Callable, Optional

from .config import MAX_REVISIONS
from .judging import evaluate_story
from .ResponseModel import EvaluatedDraft, StoryCategory, StoryResult
from .storytelling import generate_story, revise_story


def _improve_story_drafts(
    user_request: str,
    story: str,
    category: StoryCategory,
    user_feedback: str = "",
    on_revision: Optional[Callable[[int, int], None]] = None,
) -> StoryResult:
    """Evaluate and improve one starting draft within the configured limit."""
    judge_result = evaluate_story(user_request, story, user_feedback)
    revision_count = 0
    evaluated_drafts = [
        EvaluatedDraft(
            story=story,
            judge_result=judge_result,
            revision_number=revision_count,
        )
    ]

    while not judge_result.approved and revision_count < MAX_REVISIONS:
        if on_revision is not None:
            on_revision(revision_count + 1, MAX_REVISIONS)
        story = revise_story(
            user_request,
            story,
            judge_result,
            category,
            user_feedback=user_feedback,
        )
        revision_count += 1
        judge_result = evaluate_story(user_request, story, user_feedback)
        evaluated_drafts.append(
            EvaluatedDraft(
                story=story,
                judge_result=judge_result,
                revision_number=revision_count,
            )
        )

    best_draft = max(
        evaluated_drafts,
        key=lambda draft: draft.judge_result.quality_rank,
    )

    return StoryResult(
        selected_draft=best_draft,
        revisions_performed=revision_count,
    )


def generate_improved_story(
    user_request: str,
    category: StoryCategory,
    on_revision: Optional[Callable[[int, int], None]] = None,
) -> StoryResult:
    """Generate, evaluate, and revise a new story within the configured limit."""
    story = generate_story(user_request, category)
    return _improve_story_drafts(
        user_request=user_request,
        story=story,
        category=category,
        on_revision=on_revision,
    )


def improve_feedback_story(
    user_request: str,
    story: str,
    user_feedback: str,
    category: StoryCategory,
    on_revision: Optional[Callable[[int, int], None]] = None,
) -> StoryResult:
    """Evaluate and improve a story updated from explicit user feedback."""
    return _improve_story_drafts(
        user_request=user_request,
        story=story,
        category=category,
        user_feedback=user_feedback,
        on_revision=on_revision,
    )
