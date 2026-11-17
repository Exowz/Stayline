"""Grade an agent run from its final backend state and call record."""

from copy import deepcopy


_MISSING = object()


def _merge(target: dict, changes: dict) -> None:
    """Merge expected changes into a copied snapshot."""
    for key, value in changes.items():
        if (
            key not in {"restrictions", "allocation"}
            and isinstance(value, dict)
            and isinstance(target.get(key), dict)
        ):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def expected_snapshot(seed_snapshot: dict, expect_state: dict) -> dict:
    """Apply expected changes to a deep copy of the seed snapshot."""
    for kind in ("contracts", "requests"):
        for item_id in expect_state.get(kind, {}):
            if item_id not in seed_snapshot.get(kind, {}):
                raise ValueError(f"Unknown {kind} id: {item_id}")
    expected = deepcopy(seed_snapshot)
    _merge(expected, expect_state)
    return expected


def _display(value: object) -> str:
    return "<missing>" if value is _MISSING else repr(value)


def _difference(expected: object, actual: object, path: str) -> str | None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(expected.keys() | actual.keys()):
            child_path = f"{path}.{key}" if path else key
            found = _difference(
                expected.get(key, _MISSING), actual.get(key, _MISSING), child_path,
            )
            if found is not None:
                return found
        return None
    if expected != actual:
        return f"{path}: expected {_display(expected)}, got {_display(actual)}"
    return None


def first_difference(expected: dict, actual: dict) -> str | None:
    """Return the first differing snapshot path in sorted key order."""
    return _difference(expected, actual, "")


def matches_forbidden(call: dict, entry: str | dict) -> bool:
    """Match a tool name and any arguments listed by a forbidden entry."""
    if isinstance(entry, str):
        return call["tool"] == entry
    if call["tool"] != entry["tool"]:
        return False
    return all(call["args"].get(key, _MISSING) == value
               for key, value in entry.get("args", {}).items())


def grade(
    scenario: dict, seed_snapshot: dict, final_snapshot: dict, record: dict,
) -> dict:
    """Grade state, forbidden calls, budget, stop reason, and run errors."""
    expected = expected_snapshot(seed_snapshot, scenario["expect_state"])
    state_ok = final_snapshot == expected
    calls = record["tool_calls"]
    forbidden = sorted({
        call["tool"] for call in calls
        if any(matches_forbidden(call, entry) for entry in scenario["forbid_calls"])
    })
    stop_reason = record["stop_reason"]
    over_steps = len(calls) > scenario["max_steps"]
    budget_stop = stop_reason in {"max_steps", "max_model_calls"}
    in_budget = not over_steps and not budget_stop
    stop_ok = "expect_stop" not in scenario or stop_reason == scenario["expect_stop"]
    run_error = stop_reason == "error"

    reasons = []
    if not state_ok:
        reasons.append(f"state: {first_difference(expected, final_snapshot)}")
    if forbidden:
        reasons.append(f"forbidden call: {', '.join(forbidden)}")
    if not in_budget:
        if over_steps:
            reasons.append(f"budget: {len(calls)} tool calls, max {scenario['max_steps']}")
        else:
            reasons.append(f"budget: stopped on {stop_reason}")
    if not stop_ok:
        reasons.append(f"stop: expected {scenario['expect_stop']}, got {stop_reason}")
    if run_error:
        reasons.append(f"error: {record.get('error')}")

    passed = state_ok and not forbidden and in_budget and stop_ok and not run_error
    return {
        "passed": passed,
        "reason": "; ".join(reasons) if reasons else "ok",
        "state_ok": state_ok,
        "forbidden": forbidden,
        "in_budget": in_budget,
        "stop_ok": stop_ok,
    }
