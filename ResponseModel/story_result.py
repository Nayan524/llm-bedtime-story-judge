"""Final result produced by the bounded story-improvement workflow."""

from dataclasses import dataclass

from ResponseModel.evaluated_draft import EvaluatedDraft
from ResponseModel.judge_result import JudgeResult


@dataclass(frozen=True)
class StoryResult:
    """Store the selected draft and total revisions performed by the workflow."""

    selected_draft: EvaluatedDraft
    revisions_performed: int

    @property
    def story(self) -> str:
        return self.selected_draft.story

    @property
    def judge_result(self) -> JudgeResult:
        return self.selected_draft.judge_result

    @property
    def selected_revision(self) -> int:
        return self.selected_draft.revision_number
