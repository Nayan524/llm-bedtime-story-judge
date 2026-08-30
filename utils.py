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
)
from ResponseModel import JudgeResult


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


def _validate_feedback_list(value: object, field_name: str) -> list[str]:
    """Validate one list of textual feedback from the Judge."""
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"Judge field '{field_name}' must be a list of strings.")
    return [item.strip() for item in value]


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

    return JudgeResult(
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
