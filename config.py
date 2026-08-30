"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv


load_dotenv()

# This model is fixed by the assignment requirements.
MODEL_NAME = "gpt-3.5-turbo"

# Generation and evaluation settings are centralized here so they can be tuned
# without mixing configuration into prompts or orchestration logic.
STORY_TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.1
MAX_RESPONSE_TOKENS = 3_000
MAX_REVISIONS = 2


def get_openai_api_key() -> str:
    """Return the configured OpenAI API key or raise a helpful error."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Copy .env.example to .env "
            "and add your OpenAI API key."
        )
    return api_key
