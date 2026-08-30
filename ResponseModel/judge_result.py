"""Structured response returned by the LLM Judge."""

from dataclasses import dataclass

from ResponseModel.request_check import RequestCheck


@dataclass(frozen=True)
class JudgeResult:
    """Validated scores and feedback returned by the LLM Judge."""

    request_checks: list[RequestCheck]
    scores: dict[str, int]
    strengths: list[str]
    issues: list[str]
    revision_instructions: list[str]

    @property
    def average_score(self) -> float:
        return sum(self.scores.values()) / len(self.scores)

    @property
    def failed_requirement_count(self) -> int:
        return sum(not check.satisfied for check in self.request_checks)

    @property
    def hard_requirements_pass(self) -> bool:
        return all(
            self.scores[criterion] >= 4
            for criterion in (
                "age_appropriateness",
                "bedtime_suitability",
                "request_adherence",
                "safety",
            )
        )

    @property
    def minimum_score(self) -> int:
        return min(self.scores.values())

    @property
    def approved(self) -> bool:
        explicit_requirements_pass = self.failed_requirement_count == 0
        remaining_criteria_pass = all(
            score >= 3 for score in self.scores.values()
        )
        return (
            explicit_requirements_pass
            and self.hard_requirements_pass
            and remaining_criteria_pass
            and self.average_score >= 4.0
        )

    @property
    def quality_rank(self) -> tuple[bool, bool, int, int, float]:
        """Return a safety-first tuple used to compare evaluated drafts."""
        return (
            self.approved,
            self.hard_requirements_pass,
            -self.failed_requirement_count,
            self.minimum_score,
            self.average_score,
        )
