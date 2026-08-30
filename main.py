import openai

from config import MAX_USER_FEEDBACK_ROUNDS
from utils import (
    classify_story_request,
    collect_user_feedback,
    format_feedback_history,
    generate_improved_story,
    improve_feedback_story,
    print_judge_report,
    revise_story_from_user_feedback,
)


"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

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

    print(f"\nStory category: {classification.category.value.title()}")
    print(f"Reason: {classification.reason}")

    try:
        result = generate_improved_story(
            user_input,
            classification.category,
            on_revision=lambda current, maximum: print(
                f"\nDraft needs improvement. Revising ({current}/{maximum})..."
            ),
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

    print(f"\n--- Final story ---\n\n{result.story}")
    print(f"\nRevisions performed: {result.revisions_performed}")
    selected_version = (
        "Initial draft"
        if result.selected_revision == 0
        else f"Revision {result.selected_revision}"
    )
    print(f"Selected version: {selected_version}")
    print_judge_report(result.judge_result)

    current_story = result.story
    feedback_history = []

    for feedback_round in range(1, MAX_USER_FEEDBACK_ROUNDS + 1):
        feedback = collect_user_feedback()
        if feedback is None:
            print("Story accepted. Goodnight!")
            return

        feedback_history.append(feedback)
        accumulated_feedback = format_feedback_history(feedback_history)
        print(
            f"\nApplying feedback round {feedback_round} "
            f"of {MAX_USER_FEEDBACK_ROUNDS}..."
        )
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
                on_revision=lambda current, maximum: print(
                    "\nFeedback-updated draft needs improvement. "
                    f"Revising ({current}/{maximum})..."
                ),
            )
        except openai.error.OpenAIError as exc:
            print(f"Unable to evaluate or improve the updated story: {exc}")
            return
        except ValueError as exc:
            print(f"Unable to evaluate the updated story: {exc}")
            return

        print(f"\n--- Updated story ---\n\n{feedback_result.story}")
        print(
            "\nAutomatic revisions performed: "
            f"{feedback_result.revisions_performed}"
        )
        selected_feedback_version = (
            "User-feedback draft"
            if feedback_result.selected_revision == 0
            else f"Automatic revision {feedback_result.selected_revision}"
        )
        print(f"Selected version: {selected_feedback_version}")
        print_judge_report(feedback_result.judge_result)
        current_story = feedback_result.story

    print("\nMaximum feedback rounds reached. Goodnight!")


if __name__ == "__main__":
    main()
