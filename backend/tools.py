"""LangChain tools, bound to one session's InterviewState (no global state)."""

from __future__ import annotations

from typing import Callable

from langchain_core.tools import tool

from backend.schemas import InterviewState, RecordedAnswer


def create_tools(state: InterviewState, on_change: Callable[[InterviewState], None]):
    """`on_change` is called after every state update (used to persist it)."""
    field_names = [f.name for f in state.fields]

    @tool
    def record_answer(field: str, answer: str) -> str:
        """Save the candidate's answer for one interview field once they have given enough detail.

        Args:
            field: One of the interview field names.
            answer: A faithful summary of what the candidate said. Never add facts they did not state.
        """
        if field not in field_names:
            return f"Unknown field '{field}'. Valid fields: {', '.join(field_names)}"
        state.answers[field] = RecordedAnswer(field=field, answer=answer)
        on_change(state)
        return f"Saved '{field}'. Still missing: {', '.join(f.name for f in state.missing_fields()) or 'nothing'}"

    @tool
    def get_missing_fields() -> str:
        """List the interview fields the candidate has not answered yet."""
        missing = state.missing_fields()
        if not missing:
            return "All fields are answered. Thank the candidate and tell them they can press Finish Interview."
        return "\n".join(f"- {f.name}: {f.question}" for f in missing)

    return [record_answer, get_missing_fields]
