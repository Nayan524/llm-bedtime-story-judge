import sys
from pathlib import Path

import openai


# Support both `python -m src.main` and direct execution of `src/main.py`.
if __package__ in {None, ""}:
    repository_root = str(Path(__file__).resolve().parent.parent)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "src"


from .config import MAX_USER_FEEDBACK_ROUNDS
from .utils import (
    classify_story_request,
    collect_user_feedback,
    format_feedback_history,
    generate_improved_story,
    improve_feedback_story,
    revise_story_from_user_feedback,
)


"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

I would improve Judge reliability by combining LLM evaluation with deterministic
checks for measurable constraints, such as word count, paragraph count, required
phrases, and dialogue count. I would also evaluate the Judge against a small set of
known valid and invalid stories and consider multiple Judge passes for inconsistent
results.

If the workflow grew, I would introduce a formal agentic architecture in which
classification, generation, evaluation, revision, and user feedback are explicit
tools in a LangGraph-style state graph. This would make branching, persistence,
state transitions, and workflow tracing easier to manage.

For production reliability, I would add structured logging, exponential-backoff
retries, token and cost tracking, and clearer handling of rate limits and temporary
model failures. Finally, I would add a web interface with persistent story sessions
so users could resume stories, compare versions, and continue providing feedback.
"""


def main() -> None:
    """Run the bedtime-story command-line experience."""
    user_input = input("What kind of story do you want to hear? ").strip()
    if not user_input:
        print("Please provide a short description of the story you would like.")
        return

    try:
        classification = classify_story_request(user_input)
    except RuntimeError as exc:
        print(f"Configuration error: {exc}")
        return
    except openai.error.OpenAIError as exc:
        print(f"Unable to classify the story request: {exc}")
        return
    except ValueError as exc:
        print(f"Unable to classify the story request: {exc}")
        return

    try:
        result = generate_improved_story(
            user_input,
            classification.category,
        )
    except RuntimeError as exc:
        print(f"Configuration error: {exc}")
        return
    except openai.error.OpenAIError as exc:
        print(f"Unable to complete story generation: {exc}")
        return
    except ValueError as exc:
        print(f"Unable to evaluate the story: {exc}")
        return

    print(f"\n{result.story}")

    current_story = result.story
    feedback_history = []

    for feedback_round in range(1, MAX_USER_FEEDBACK_ROUNDS + 1):
        feedback = collect_user_feedback()
        if feedback is None:
            print("Story accepted. Goodnight!")
            return

        feedback_history.append(feedback)
        accumulated_feedback = format_feedback_history(feedback_history)
        try:
            updated_story = revise_story_from_user_feedback(
                user_request=user_input,
                story=current_story,
                user_feedback=accumulated_feedback,
                category=classification.category,
            )
        except RuntimeError as exc:
            print(f"Configuration error: {exc}")
            return
        except openai.error.OpenAIError as exc:
            print(f"Unable to apply your feedback: {exc}")
            return

        try:
            feedback_result = improve_feedback_story(
                user_request=user_input,
                story=updated_story,
                user_feedback=accumulated_feedback,
                category=classification.category,
            )
        except openai.error.OpenAIError as exc:
            print(f"Unable to evaluate or improve the updated story: {exc}")
            return
        except ValueError as exc:
            print(f"Unable to evaluate the updated story: {exc}")
            return

        print(f"\n{feedback_result.story}")
        current_story = feedback_result.story

    print("\nMaximum feedback rounds reached. Goodnight!")


if __name__ == "__main__":
    main()
