"""Shared generation, evaluation, parsing, and display helpers."""

import json
from typing import Callable, Optional

from call_llm import call_model
from config import (
    CLASSIFIER_MAX_RESPONSE_TOKENS,
    CLASSIFIER_TEMPERATURE,
    JUDGE_MAX_RESPONSE_TOKENS,
    JUDGE_TEMPERATURE,
    MAX_JUDGE_VALIDATION_RETRIES,
    MAX_REVISIONS,
)
from prompts import (
    CLASSIFIER_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    STORYTELLER_SYSTEM_PROMPT,
    build_classification_prompt,
    build_feedback_judge_evaluation_prompt,
    build_judge_evaluation_prompt,
    build_judge_retry_prompt,
    build_story_generation_prompt,
    build_story_revision_prompt,
    build_user_feedback_revision_prompt,
    get_category_strategy,
)
from ResponseModel import (
    ClassificationResult,
    EvaluatedDraft,
    JudgeResult,
    RequestCheck,
    StoryCategory,
    StoryResult,
)


JUDGE_CRITERIA = {
    "age_appropriateness",
    "bedtime_suitability",
    "request_adherence",
    "story_structure",
    "creativity",
    "clarity",
    "safety",
}


def parse_classification_result(raw_result: str) -> ClassificationResult:
    """Parse and validate the Request Classifier's JSON response."""
    try:
        payload = json.loads(raw_result)
    except json.JSONDecodeError as exc:
        raise ValueError("Request Classifier returned invalid JSON.") from exc

    if not isinstance(payload, dict) or set(payload) != {"category", "reason"}:
        raise ValueError("Classification response must contain category and reason.")

    try:
        category = StoryCategory(payload["category"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Request Classifier returned an unsupported category.") from exc

    reason = payload["reason"]
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Classification reason must be a non-empty string.")

    return ClassificationResult(category=category, reason=reason.strip())


def classify_story_request(user_request: str) -> ClassificationResult:
    """Classify a story request into one supported primary category."""
    raw_result = call_model(
        system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        user_prompt=build_classification_prompt(user_request),
        max_tokens=CLASSIFIER_MAX_RESPONSE_TOKENS,
        temperature=CLASSIFIER_TEMPERATURE,
    )
    return parse_classification_result(raw_result)


def generate_story(user_request: str, category: StoryCategory) -> str:
    """Generate an age-appropriate bedtime story for a user request."""
    category_strategy = get_category_strategy(category)
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_generation_prompt(
            user_request=user_request,
            category=category,
            category_strategy=category_strategy,
        ),
    )


def revise_story(
    user_request: str,
    story: str,
    judge_result: JudgeResult,
    category: StoryCategory,
    user_feedback: str = "",
) -> str:
    """Ask the Storyteller to revise one story using Judge feedback."""
    failed_requirements = [
        f"{check.requirement} Evidence: {check.evidence}"
        for check in judge_result.request_checks
        if not check.satisfied
    ]
    category_strategy = get_category_strategy(category)
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_revision_prompt(
            user_request=user_request,
            story=story,
            strengths=judge_result.strengths,
            issues=judge_result.issues,
            revision_instructions=judge_result.revision_instructions,
            failed_requirements=failed_requirements,
            category=category,
            category_strategy=category_strategy,
            user_feedback=user_feedback,
        ),
    )


def revise_story_from_user_feedback(
    user_request: str,
    story: str,
    user_feedback: str,
    category: StoryCategory,
) -> str:
    """Revise a selected story once using the user's explicit feedback."""
    category_strategy = get_category_strategy(category)
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_user_feedback_revision_prompt(
            user_request=user_request,
            story=story,
            user_feedback=user_feedback,
            category=category,
            category_strategy=category_strategy,
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


def _improve_story_drafts(
    user_request: str,
    story: str,
    category: StoryCategory,
    user_feedback: str = "",
    on_revision: Optional[Callable[[int, int], None]] = None,
) -> StoryResult:
    """Evaluate and improve one starting draft within the configured limit."""
    judge_result = evaluate_story(user_request, story, user_feedback)
    revision_count = 0
    evaluated_drafts = [
        EvaluatedDraft(
            story=story,
            judge_result=judge_result,
            revision_number=revision_count,
        )
    ]

    while not judge_result.approved and revision_count < MAX_REVISIONS:
        if on_revision is not None:
            on_revision(revision_count + 1, MAX_REVISIONS)
        story = revise_story(
            user_request,
            story,
            judge_result,
            category,
            user_feedback=user_feedback,
        )
        revision_count += 1
        judge_result = evaluate_story(user_request, story, user_feedback)
        evaluated_drafts.append(
            EvaluatedDraft(
                story=story,
                judge_result=judge_result,
                revision_number=revision_count,
            )
        )

    best_draft = max(
        evaluated_drafts,
        key=lambda draft: draft.judge_result.quality_rank,
    )

    return StoryResult(
        selected_draft=best_draft,
        revisions_performed=revision_count,
    )


def generate_improved_story(
    user_request: str,
    category: StoryCategory,
    on_revision: Optional[Callable[[int, int], None]] = None,
) -> StoryResult:
    """Generate, evaluate, and revise a new story within the configured limit."""
    story = generate_story(user_request, category)
    return _improve_story_drafts(
        user_request=user_request,
        story=story,
        category=category,
        on_revision=on_revision,
    )


def improve_feedback_story(
    user_request: str,
    story: str,
    user_feedback: str,
    category: StoryCategory,
    on_revision: Optional[Callable[[int, int], None]] = None,
) -> StoryResult:
    """Evaluate and improve a story updated from explicit user feedback."""
    return _improve_story_drafts(
        user_request=user_request,
        story=story,
        category=category,
        user_feedback=user_feedback,
        on_revision=on_revision,
    )


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


def collect_user_feedback() -> Optional[str]:
    """Ask whether the user wants changes and return validated feedback."""
    while True:
        choice = input(
            "\nWould you like to keep this story or request a change? "
            "[keep/change]: "
        ).strip().lower()

        if choice in {"keep", "k"}:
            return None
        if choice in {"change", "c"}:
            break

        print("Please enter 'keep' or 'change'.")

    while True:
        feedback = input("What would you like to change? ").strip()
        if feedback:
            return feedback
        print("Please describe the change you would like.")


def format_feedback_history(feedback_history: list[str]) -> str:
    """Format chronological feedback while preserving round precedence."""
    return "\n".join(
        f"Feedback round {index}: {feedback}"
        for index, feedback in enumerate(feedback_history, start=1)
    )
