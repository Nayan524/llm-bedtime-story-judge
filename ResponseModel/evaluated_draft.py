"""One story draft paired with its completed Judge evaluation."""

from dataclasses import dataclass

from ResponseModel.judge_result import JudgeResult


@dataclass(frozen=True)
class EvaluatedDraft:
    """Represent one evaluated version in the improvement workflow."""

    story: str
    judge_result: JudgeResult
    revision_number: int
