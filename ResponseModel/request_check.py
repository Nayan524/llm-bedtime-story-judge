"""Evidence for one explicit requirement from the user's request."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestCheck:
    """Record whether a story satisfies one explicit user requirement."""

    requirement: str
    satisfied: bool
    evidence: str
