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
    def approved(self) -> bool:
        explicit_requirements_pass = all(
            check.satisfied for check in self.request_checks
        )
        hard_requirements_pass = all(
            self.scores[criterion] >= 4
            for criterion in (
                "age_appropriateness",
                "bedtime_suitability",
                "safety",
            )
        )
        remaining_criteria_pass = all(score >= 3 for score in self.scores.values())
        return (
            explicit_requirements_pass
            and hard_requirements_pass
            and remaining_criteria_pass
            and self.average_score >= 4.0
        )
