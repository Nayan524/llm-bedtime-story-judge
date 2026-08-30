"""OpenAI model-call boundary for the bedtime-story application."""

import openai

from config import (
    MAX_RESPONSE_TOKENS,
    MODEL_NAME,
    STORY_TEMPERATURE,
    get_openai_api_key,
)


def call_model(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = MAX_RESPONSE_TOKENS,
    temperature: float = STORY_TEMPERATURE,
) -> str:
    """Call the assignment's required OpenAI model with explicit chat roles."""
    openai.api_key = get_openai_api_key()
    resp = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"].strip()  # type: ignore
