"""Pure routing decisions for the agent graph."""

from stayline.agent.state import CONTROL, DANGEROUS, AgentState


def router(state: AgentState) -> str:
    """Select the next graph node from the latest action and budgets."""
    action = state["action"]
    assert action is not None

    if action["type"] == "final":
        return "__end__"
    if state["model_calls"] >= state["max_model_calls"]:
        return "give_up"
    if action["type"] == "none":
        return "give_up" if state["reminded"] else "remind"
    if action["tool"] == "remember_alias":
        return "remember"
    if len(state["tool_calls"]) >= state["max_steps"]:
        return "give_up"
    if action["tool"] in DANGEROUS:
        return "prepare"
    return "read_tool"


def give_up_reason(state: AgentState) -> str:
    """Name the budget that stopped routing."""
    if state["model_calls"] >= state["max_model_calls"]:
        return "max_model_calls"
    if state["action"] is not None and state["action"]["type"] == "none" and state["reminded"]:
        return "error"
    return "max_steps"
