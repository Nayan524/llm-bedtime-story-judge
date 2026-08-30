import openai

from utils import generate_improved_story, print_judge_report


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
        result = generate_improved_story(user_input)
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
    print(f"\nRevisions performed: {result.revision_count}")
    print_judge_report(result.judge_result)


if __name__ == "__main__":
    main()
