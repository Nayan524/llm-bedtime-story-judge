"""Judge response parsing, validation, and story evaluation."""

import json
from typing import Optional

from .call_llm import call_model
from .config import (
    JUDGE_MAX_RESPONSE_TOKENS,
    JUDGE_TEMPERATURE,
    MAX_JUDGE_VALIDATION_RETRIES,
)
from .prompts import (
    JUDGE_SYSTEM_PROMPT,
    build_feedback_judge_evaluation_prompt,
    build_judge_evaluation_prompt,
    build_judge_retry_prompt,
)
from .ResponseModel import JudgeResult, RequestCheck


JUDGE_CRITERIA = {
    "age_appropriateness",
    "bedtime_suitability",
    "request_adherence",
    "story_structure",
    "creativity",
    "clarity",
    "safety",
}


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


def evaluate_story(
    user_request: str, story: str, user_feedback: str = ""
) -> JudgeResult:
    """Ask the LLM Judge to score a story and validate its response."""
    user_prompt = (
        build_feedback_judge_evaluation_prompt(
            user_request=user_request,
            user_feedback=user_feedback,
            story=story,
        )
        if user_feedback
        else build_judge_evaluation_prompt(user_request, story)
    )
    last_error: Optional[ValueError] = None

    for attempt in range(MAX_JUDGE_VALIDATION_RETRIES + 1):
        raw_result = call_model(
            system_prompt=JUDGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=JUDGE_MAX_RESPONSE_TOKENS,
            temperature=JUDGE_TEMPERATURE,
        )
        try:
            return parse_judge_result(raw_result)
        except ValueError as exc:
            last_error = exc
            if attempt == MAX_JUDGE_VALIDATION_RETRIES:
                raise
            user_prompt = build_judge_retry_prompt(
                user_request=user_request,
                story=story,
                validation_error=str(exc),
                user_feedback=user_feedback,
            )

    raise last_error or ValueError("Judge evaluation failed validation.")
