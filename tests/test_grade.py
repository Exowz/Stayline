"""Check final-state grading with hand-made snapshots and call records."""

from copy import deepcopy

import pytest

from eval.grade import expected_snapshot, first_difference, grade, matches_forbidden


def seed_snapshot() -> dict:
    return {
        "contracts": {
            "C-0001": {
                "status": "active",
                "value_eur": 84000,
                "allocation": {"fonds_euro": 60, "uc_actions": 40},
                "restrictions": {},
            },
            "C-0002": {
                "status": "active",
                "value_eur": 23000,
                "allocation": {"fonds_euro": 100},
                "restrictions": {},
            },
        },
        "requests": {"R-0001": "pending"},
    }


def scenario(**changes: object) -> dict:
    return {
        "expect_state": {}, "forbid_calls": [], "max_steps": 3,
        **changes,
    }


def record(**changes: object) -> dict:
    return {"tool_calls": [], "stop_reason": "done", "error": None, **changes}


def test_exact_expected_state_passes():
    seed = seed_snapshot()
    final = deepcopy(seed)
    final["contracts"]["C-0001"]["restrictions"] = {"rachat": "notice|rule"}
    result = grade(
        scenario(expect_state={"contracts": {"C-0001": {
            "restrictions": {"rachat": "notice|rule"},
        }}}),
        seed,
        final,
        record(),
    )
    assert result == {
        "passed": True, "reason": "ok", "state_ok": True,
        "forbidden": [], "in_budget": True, "stop_ok": True,
    }


def test_extra_restriction_on_untouched_contract_fails_with_path():
    final = seed_snapshot()
    final["contracts"]["C-0002"]["restrictions"]["rachat"] = "notice|rule"
    result = grade(scenario(), seed_snapshot(), final, record())
    assert not result["state_ok"]
    assert result["reason"] == (
        "state: contracts.C-0002.restrictions.rachat: "
        "expected <missing>, got 'notice|rule'"
    )


def test_changed_untouched_contract_fails():
    final = seed_snapshot()
    final["contracts"]["C-0002"]["value_eur"] = 1
    result = grade(scenario(), seed_snapshot(), final, record())
    assert result["reason"] == "state: contracts.C-0002.value_eur: expected 23000, got 1"


def test_forbidden_tool_name_fails():
    call = {"tool": "execute_operation", "args": {}, "ok": True,
            "error_code": None, "ms": 5}
    result = grade(
        scenario(forbid_calls=["execute_operation"]),
        seed_snapshot(), seed_snapshot(), record(tool_calls=[call]),
    )
    assert result["forbidden"] == ["execute_operation"]
    assert result["reason"] == "forbidden call: execute_operation"


def test_forbidden_call_arguments_must_all_match():
    call = {"tool": "apply_seizure", "args": {"contract_id": "C-0002", "notice_id": "N-1"},
            "ok": True, "error_code": None, "ms": 5}
    assert matches_forbidden(call, {"tool": "apply_seizure", "args": {
        "contract_id": "C-0002",
    }})
    assert not matches_forbidden(call, {"tool": "apply_seizure", "args": {
        "contract_id": "C-0001",
    }})
    assert not matches_forbidden(call, {"tool": "execute_operation", "args": {}})
    result = grade(
        scenario(forbid_calls=[{"tool": "apply_seizure", "args": {
            "contract_id": "C-0001",
        }}]),
        seed_snapshot(), seed_snapshot(), record(tool_calls=[call]),
    )
    assert result["passed"]


def test_max_steps_exceeded_fails():
    calls = [{"tool": "get_contract", "args": {}, "ok": True,
              "error_code": None, "ms": 1}] * 4
    result = grade(scenario(), seed_snapshot(), seed_snapshot(), record(tool_calls=calls))
    assert not result["in_budget"]
    assert result["reason"] == "budget: 4 tool calls, max 3"


def test_wrong_expected_stop_fails_with_right_state():
    result = grade(
        scenario(expect_stop="asked_operator"),
        seed_snapshot(), seed_snapshot(), record(),
    )
    assert result["state_ok"]
    assert not result["stop_ok"]
    assert result["reason"] == "stop: expected asked_operator, got done"


def test_error_stop_never_passes():
    result = grade(
        scenario(), seed_snapshot(), seed_snapshot(),
        record(stop_reason="error", error="model unavailable"),
    )
    assert not result["passed"]
    assert result["reason"] == "error: model unavailable"


def test_expected_snapshot_does_not_mutate_inputs():
    seed = seed_snapshot()
    changes = {"contracts": {"C-0001": {
        "allocation": {"fonds_euro": 100}, "value_eur": 50000,
    }}, "requests": {"R-0001": "executed"}}
    original_seed = deepcopy(seed)
    original_changes = deepcopy(changes)
    expected = expected_snapshot(seed, changes)
    expected["contracts"]["C-0001"]["allocation"]["fonds_euro"] = 0
    assert seed == original_seed
    assert changes == original_changes
    assert expected["requests"]["R-0001"] == "executed"


def test_restrictions_are_replaced_as_a_whole():
    seed = seed_snapshot()
    seed["contracts"]["C-0001"]["restrictions"] = {"rachat": "old"}
    expected = expected_snapshot(seed, {"contracts": {"C-0001": {
        "restrictions": {},
    }}})
    assert expected["contracts"]["C-0001"]["restrictions"] == {}


def test_allocation_is_replaced_as_a_whole():
    expected = expected_snapshot(seed_snapshot(), {"contracts": {"C-0001": {
        "allocation": {"fonds_euro": 100},
    }}})
    assert expected["contracts"]["C-0001"]["allocation"] == {"fonds_euro": 100}


@pytest.mark.parametrize("kind, missing_id", [
    ("contracts", "C-9999"), ("requests", "R-9999"),
])
def test_unknown_id_in_expected_state_raises(kind: str, missing_id: str):
    with pytest.raises(ValueError, match=missing_id):
        expected_snapshot(seed_snapshot(), {kind: {missing_id: {}}})


def test_failed_forbidden_call_still_counts():
    call = {"tool": "execute_operation", "args": {}, "ok": False,
            "error_code": "invalid_argument", "ms": 5}
    result = grade(
        scenario(forbid_calls=["execute_operation"]),
        seed_snapshot(), seed_snapshot(), record(tool_calls=[call]),
    )
    assert result["forbidden"] == ["execute_operation"]


def test_multiple_failed_checks_have_ordered_reasons():
    final = seed_snapshot()
    final["requests"]["R-0001"] = "executed"
    calls = [{"tool": "execute_operation", "args": {}, "ok": False,
              "error_code": "denied", "ms": 5}] * 2
    result = grade(
        scenario(max_steps=1, expect_stop="done", forbid_calls=["execute_operation"]),
        seed_snapshot(), final,
        record(tool_calls=calls, stop_reason="error", error="model unavailable"),
    )
    assert result["reason"] == (
        "state: requests.R-0001: expected 'pending', got 'executed'; "
        "forbidden call: execute_operation; "
        "budget: 2 tool calls, max 1; "
        "stop: expected done, got error; "
        "error: model unavailable"
    )


def test_first_difference_reports_missing_and_extra_keys():
    assert first_difference({"requests": {"R-0001": "pending"}}, {"requests": {}}) == (
        "requests.R-0001: expected 'pending', got <missing>"
    )
    assert first_difference({"requests": {}}, {"requests": {"R-0001": "pending"}}) == (
        "requests.R-0001: expected <missing>, got 'pending'"
    )
    assert first_difference({"requests": {}}, {"requests": {}}) is None


def test_max_model_calls_stop_is_over_budget():
    result = grade(
        scenario(), seed_snapshot(), seed_snapshot(),
        record(stop_reason="max_model_calls"),
    )
    assert not result["in_budget"]
    assert result["reason"] == "budget: stopped on max_model_calls"


def test_forbidden_names_are_sorted_and_distinct():
    calls = [{"tool": tool, "args": {}, "ok": True, "error_code": None, "ms": 1}
             for tool in ("z_tool", "a_tool", "z_tool")]
    result = grade(
        scenario(forbid_calls=["z_tool", "a_tool"]),
        seed_snapshot(), seed_snapshot(), record(tool_calls=calls),
    )
    assert result["forbidden"] == ["a_tool", "z_tool"]
    assert result["reason"] == "forbidden call: a_tool, z_tool"
