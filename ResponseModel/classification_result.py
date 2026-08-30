"""Structured response returned by the Request Classifier."""

from dataclasses import dataclass

from ResponseModel.story_category import StoryCategory


@dataclass(frozen=True)
class ClassificationResult:
    """Store the selected story category and supporting reason."""

    category: StoryCategory
    reason: str
