"""Story-request classification and response parsing."""

import json

from .call_llm import call_model
from .config import CLASSIFIER_MAX_RESPONSE_TOKENS, CLASSIFIER_TEMPERATURE
from .prompts import CLASSIFIER_SYSTEM_PROMPT, build_classification_prompt
from .ResponseModel import ClassificationResult, StoryCategory


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
