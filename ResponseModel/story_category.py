"""Supported bedtime-story request categories."""

from enum import Enum


class StoryCategory(str, Enum):
    """Primary category selected for a user's story request."""

    ADVENTURE = "adventure"
    COMFORT = "comfort"
    EDUCATIONAL = "educational"
    FANTASY = "fantasy"
    HUMOROUS = "humorous"
    VALUES = "values"
    EVERYDAY = "everyday"
