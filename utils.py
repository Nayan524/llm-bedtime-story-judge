"""Shared generation, evaluation, parsing, and display helpers."""

import json

from call_llm import call_model
from config import (
    JUDGE_MAX_RESPONSE_TOKENS,
    JUDGE_TEMPERATURE,
)
from prompts import (
    JUDGE_SYSTEM_PROMPT,
    STORYTELLER_SYSTEM_PROMPT,
    build_judge_evaluation_prompt,
    build_story_generation_prompt,
    build_story_revision_prompt,
)
from ResponseModel import JudgeResult, RequestCheck


JUDGE_CRITERIA = {
    "age_appropriateness",
    "bedtime_suitability",
    "request_adherence",
    "story_structure",
    "creativity",
    "clarity",
    "safety",
}


def generate_story(user_request: str) -> str:
    """Generate an age-appropriate bedtime story for a user request."""
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_generation_prompt(user_request),
    )


def revise_story(
    user_request: str, story: str, judge_result: JudgeResult
) -> str:
    """Ask the Storyteller to revise one story using Judge feedback."""
    failed_requirements = [
        f"{check.requirement} Evidence: {check.evidence}"
        for check in judge_result.request_checks
        if not check.satisfied
    ]
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_revision_prompt(
            user_request=user_request,
            story=story,
            strengths=judge_result.strengths,
            issues=judge_result.issues,
            revision_instructions=judge_result.revision_instructions,
            failed_requirements=failed_requirements,
        ),
    )


def _validate_feedback_list(value: object, field_name: str) -> list[str]:
    """Validate one list of textual feedback from the Judge."""
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"Judge field '{field_name}' must be a list of strings.")
    return [item.strip() for item in value]


def _parse_request_checks(value: object) -> list[RequestCheck]:
    """Validate the Judge's evidence for every explicit user requirement."""
    if not isinstance(value, list) or not value:
        raise ValueError("Judge must return at least one request check.")

    request_checks = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "requirement",
            "satisfied",
            "evidence",
        }:
            raise ValueError("Each request check must use the required fields.")

        requirement = item["requirement"]
        satisfied = item["satisfied"]
        evidence = item["evidence"]
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError("Each checked requirement must be a non-empty string.")
        if not isinstance(satisfied, bool):
            raise ValueError("Each request check must have a boolean result.")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("Each request check must include evidence.")

        request_checks.append(
            RequestCheck(
                requirement=requirement.strip(),
                satisfied=satisfied,
                evidence=evidence.strip(),
            )
        )

    return request_checks


def parse_judge_result(raw_result: str) -> JudgeResult:
    """Parse and validate the Judge's JSON response."""
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError as exc:
        raise ValueError("Judge returned invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Judge response must be a JSON object.")

    scores = payload.get("scores")
    if not isinstance(scores, dict) or set(scores) != JUDGE_CRITERIA:
        raise ValueError("Judge response contains missing or unexpected score fields.")
    if not all(
        isinstance(score, int) and not isinstance(score, bool) and 1 <= score <= 5
        for score in scores.values()
    ):
        raise ValueError("Every Judge score must be an integer from 1 to 5.")

    request_checks = _parse_request_checks(payload.get("request_checks"))
    failed_check_count = sum(not check.satisfied for check in request_checks)
    scores = dict(scores)
    if failed_check_count == 1:
        scores["request_adherence"] = min(scores["request_adherence"], 3)
    elif failed_check_count >= 2:
        scores["request_adherence"] = min(scores["request_adherence"], 2)

    return JudgeResult(
        request_checks=request_checks,
        scores=scores,
        strengths=_validate_feedback_list(payload.get("strengths"), "strengths"),
        issues=_validate_feedback_list(payload.get("issues"), "issues"),
        revision_instructions=_validate_feedback_list(
            payload.get("revision_instructions"), "revision_instructions"
        ),
    )


def evaluate_story(user_request: str, story: str) -> JudgeResult:
    """Ask the LLM Judge to score a story and validate its response."""
    raw_result = call_model(
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_prompt=build_judge_evaluation_prompt(user_request, story),
        max_tokens=JUDGE_MAX_RESPONSE_TOKENS,
        temperature=JUDGE_TEMPERATURE,
    )
    return parse_judge_result(raw_result)


def print_judge_report(result: JudgeResult) -> None:
    """Display a concise, human-readable summary of a Judge result."""
    decision = "Approved" if result.approved else "Needs improvement"
    print(f"\n--- Judge report ---\nDecision: {decision}")
    print(f"Average score: {result.average_score:.1f}/5")

    print("Scores:")
    for criterion in sorted(result.scores):
        label = criterion.replace("_", " ").title()
        print(f"  {label}: {result.scores[criterion]}/5")

    failed_checks = [
        check for check in result.request_checks if not check.satisfied
    ]
    if failed_checks:
        print("Failed request requirements:")
        for check in failed_checks:
            print(f"  - {check.requirement}")
            print(f"    Evidence: {check.evidence}")

    if result.strengths:
        print("Strengths:")
        for strength in result.strengths:
            print(f"  - {strength}")

    if result.issues:
        print("Issues:")
        for issue in result.issues:
            print(f"  - {issue}")

    if result.revision_instructions:
        print("Suggested improvements:")
        for instruction in result.revision_instructions:
            print(f"  - {instruction}")
