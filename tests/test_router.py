"""Tests for the agent state and pure router."""

import subprocess
import sys


def make_state(**updates):
    from stayline.agent.state import initial_state

    state = initial_state("Review notice", "operator-1", "run-1", 8, 12)
    state.update(updates)
    return state


def route(state):
    from stayline.agent.router import router

    return router(state)


def test_initial_state_has_all_starting_values():
    state = make_state()

    assert state == {
        "task": "Review notice",
        "operator_id": "operator-1",
        "run_id": "run-1",
        "max_steps": 8,
        "max_model_calls": 12,
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


def test_final_action_ends():
    state = make_state(action={"type": "final", "stop": "done", "text": "Done"})

    assert route(state) == "__end__"


def test_final_wins_when_both_budgets_are_exhausted():
    state = make_state(
        action={"type": "final", "stop": "done", "text": "Done"},
        model_calls=12,
        tool_calls=[{} for _ in range(8)],
    )

    assert route(state) == "__end__"


def test_model_call_budget_gives_up_before_tool_routing():
    state = make_state(
        action={"type": "call", "tool": "remember_alias", "args": {}, "call_id": "c1"},
        model_calls=12,
    )

    assert route(state) == "give_up"


def test_plain_text_reminds_once():
    state = make_state(action={"type": "none"})

    assert route(state) == "remind"


def test_plain_text_ends_after_reminder():
    state = make_state(action={"type": "none"}, reminded=True)

    assert route(state) == "__end__"


def test_remember_alias_does_not_consume_step_budget():
    state = make_state(
        action={"type": "call", "tool": "remember_alias", "args": {}, "call_id": "c1"},
        tool_calls=[{} for _ in range(8)],
    )

    assert route(state) == "remember"


def test_ninth_tool_call_gives_up_at_eight_steps():
    state = make_state(
        action={"type": "call", "tool": "apply_seizure", "args": {}, "call_id": "c1"},
        tool_calls=[{} for _ in range(8)],
    )

    assert route(state) == "give_up"


def test_dangerous_tool_goes_to_prepare():
    state = make_state(
        action={"type": "call", "tool": "execute_operation", "args": {}, "call_id": "c1"}
    )

    assert route(state) == "prepare"


def test_set_request_status_goes_to_read_tool():
    state = make_state(
        action={"type": "call", "tool": "set_request_status", "args": {}, "call_id": "c1"}
    )

    assert route(state) == "read_tool"


def test_read_tool_goes_to_read_tool():
    state = make_state(
        action={"type": "call", "tool": "get_contract", "args": {}, "call_id": "c1"}
    )

    assert route(state) == "read_tool"


def test_unknown_tool_goes_to_read_tool():
    state = make_state(
        action={"type": "call", "tool": "unknown_tool", "args": {}, "call_id": "c1"}
    )

    assert route(state) == "read_tool"


def test_give_up_reason_is_model_calls_when_both_budgets_are_exhausted():
    from stayline.agent.router import give_up_reason

    state = make_state(model_calls=12, tool_calls=[{} for _ in range(8)])

    assert give_up_reason(state) == "max_model_calls"


def test_give_up_reason_is_max_steps_when_model_budget_remains():
    from stayline.agent.router import give_up_reason

    state = make_state(tool_calls=[{} for _ in range(8)])

    assert give_up_reason(state) == "max_steps"


def test_router_import_does_not_load_external_agent_packages():
    code = (
        "import stayline.agent.router, sys; "
        "print(','.join(name for name in "
        "('openai', 'agents', 'mcp', 'langgraph') if name in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == ""
