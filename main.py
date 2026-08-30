import openai

from config import (
    MAX_RESPONSE_TOKENS,
    MODEL_NAME,
    STORY_TEMPERATURE,
    get_openai_api_key,
)
from prompts import STORYTELLER_SYSTEM_PROMPT, build_story_generation_prompt


"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

"""


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


def generate_story(user_request: str) -> str:
    """Generate an age-appropriate bedtime story for a user request."""
    return call_model(
        system_prompt=STORYTELLER_SYSTEM_PROMPT,
        user_prompt=build_story_generation_prompt(user_request),
    )


def main() -> None:
    """Run the bedtime-story command-line experience."""
    user_input = input("What kind of story do you want to hear? ").strip()
    if not user_input:
        print("Please provide a short description of the story you would like.")
        return

    try:
        story = generate_story(user_input)
    except RuntimeError as exc:
        print(f"Configuration error: {exc}")
        return
    except openai.error.OpenAIError as exc:
        print(f"Unable to generate a story: {exc}")
        return

    print(f"\n{story}")


if __name__ == "__main__":
    main()
