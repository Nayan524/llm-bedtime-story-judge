"""User-feedback collection and history formatting."""

from typing import Optional


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
