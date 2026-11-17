"""State shared by the agent graph and router."""

import operator
from typing import Annotated, TypedDict


DANGEROUS = frozenset({"apply_seizure", "execute_operation"})
CONTROL = frozenset({"finish", "ask_operator", "refuse", "remember_alias"})
STOP_REASONS = (
    "done",
    "asked_operator",
    "refused",
    "max_steps",
    "max_model_calls",
    "error",
)


class AgentState(TypedDict):
    """Checkpointed state for one agent run."""

    task: str
    operator_id: str
    run_id: str
    max_steps: int
    max_model_calls: int
    model_calls: int
    reminded: bool
    messages: Annotated[list[dict], operator.add]
    action: dict | None
    preview: dict | None
    tool_calls: Annotated[list[dict], operator.add]
    usage: Annotated[list[dict], operator.add]
    approvals: Annotated[list[dict], operator.add]
    stop_reason: str | None
    answer: str | None


def initial_state(
    task: str, operator_id: str, run_id: str, max_steps: int, max_model_calls: int
) -> AgentState:
    """Return a fresh, fully populated state for a run."""
    return {
        "task": task,
        "operator_id": operator_id,
        "run_id": run_id,
        "max_steps": max_steps,
        "max_model_calls": max_model_calls,
        "model_calls": 0,
        "reminded": False,
        "messages": [],
        "action": None,
        "preview": None,
        "tool_calls": [],
        "usage": [],
        "approvals": [],
        "stop_reason": None,
        "answer": None,
    }
