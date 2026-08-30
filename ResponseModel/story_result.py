"""Final result produced by the bounded story-improvement workflow."""

from dataclasses import dataclass

from ResponseModel.judge_result import JudgeResult


@dataclass(frozen=True)
class StoryResult:
    """Store the final story, evaluation, and number of revisions performed."""

    story: str
    judge_result: JudgeResult
    revision_count: int
