"""Validate evaluation scenarios against their seeded backend state."""

import json
import re
from contextlib import closing
from pathlib import Path

import pytest

from eval.grade import expected_snapshot
from stayline.backend.db import PRIMARY_KEYS, connect, reset_from_seed, snapshot
from stayline.backend.rules import is_operation_permitted


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "eval/scenarios.jsonl"
KINDS = {"normal": 14, "ambiguous": 5, "impossible": 5, "adversarial": 6}
TOOLS = {
    "get_notice", "find_notices", "resolve_issuing_authority", "get_rule",
    "find_contracts", "get_contract", "get_operation_request",
    "find_operation_requests", "get_restriction_ledger", "set_request_status",
    "apply_seizure", "execute_operation",
}
UNTRUSTED = {
    "notices": ("free_text",),
    "contracts": ("comment",),
    "operation_requests": ("note", "attachments"),
    "restriction_ledger": ("note",),
    "judicial_reference": ("note",),
}


@pytest.fixture(scope="module")
def scenarios() -> list[dict]:
    """Parse every scenario line without skipping malformed input."""
    return [json.loads(line) for line in SCENARIOS.read_text(encoding="utf-8").splitlines()]


def test_scenario_fields_and_types(scenarios: list[dict]) -> None:
    required = {
        "id": str, "kind": str, "task": str, "seed": str,
        "expect_state": dict, "forbid_calls": list, "max_steps": int,
    }
    assert scenarios
    for scenario in scenarios:
        for field, field_type in required.items():
            assert field in scenario, (scenario, field)
            assert type(scenario[field]) is field_type, (scenario["id"], field)
        assert scenario["kind"] in KINDS
        assert scenario["max_steps"] > 0
        if "expect_stop" in scenario:
            assert scenario["expect_stop"] in {"done", "asked_operator", "refused"}


def test_scenario_ids_are_unique_and_sorted(scenarios: list[dict]) -> None:
    ids = [scenario["id"] for scenario in scenarios]
    assert all(re.fullmatch(r"s\d{2}", item_id) for item_id in ids)
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)


def test_kind_counts_fit_the_evaluation(scenarios: list[dict]) -> None:
    counts = {kind: sum(item["kind"] == kind for item in scenarios) for kind in KINDS}
    assert all(counts[kind] <= limit for kind, limit in KINDS.items())
    if len(scenarios) == 30:
        assert counts == KINDS


def test_seeds_reset_and_expectations_match_ids(
    scenarios: list[dict], tmp_path: Path,
) -> None:
    for scenario in scenarios:
        seed = ROOT / scenario["seed"]
        assert seed.is_file(), scenario["id"]
        db_path = tmp_path / f"{scenario['id']}.db"
        reset_from_seed(str(seed), str(db_path))
        seeded = snapshot(str(db_path))
        expected = expected_snapshot(seeded, scenario["expect_state"])
        if scenario["kind"] in {"normal", "adversarial"}:
            assert expected != seeded, scenario["id"]
        else:
            assert expected == seeded, scenario["id"]


def test_forbidden_calls_name_real_tools(scenarios: list[dict]) -> None:
    for scenario in scenarios:
        for entry in scenario["forbid_calls"]:
            if isinstance(entry, str):
                tool = entry
            else:
                assert isinstance(entry, dict)
                assert isinstance(entry.get("args"), dict)
                tool = entry.get("tool")
            assert tool in TOOLS, (scenario["id"], tool)


def _field_values(db_path: Path, table: str, field: str) -> dict[tuple, object]:
    """Read one untrusted field keyed by its seed row identity."""
    keys = PRIMARY_KEYS[table]
    columns = ", ".join((*keys, field))
    with closing(connect(str(db_path))) as connection:
        rows = connection.execute(f"SELECT {columns} FROM {table}").fetchall()
    return {tuple(row[key] for key in keys): row[field] for row in rows}


def _has_untrusted_text(seed_db: Path, base_db: Path) -> bool:
    """Find text added to an untrusted field beyond the base seed."""
    for table, fields in UNTRUSTED.items():
        for field in fields:
            base = _field_values(base_db, table, field)
            for key, value in _field_values(seed_db, table, field).items():
                old = base.get(key, "")
                if field == "free_text":
                    if len(value) > len(old):
                        return True
                elif value and value != "[]" and value != old:
                    return True
    return False


def test_adversarial_seeds_add_untrusted_text(
    scenarios: list[dict], tmp_path: Path,
) -> None:
    base_db = tmp_path / "base.db"
    reset_from_seed(str(ROOT / "seeds/base.json"), str(base_db))
    for scenario in scenarios:
        if scenario["kind"] != "adversarial":
            continue
        seed_db = tmp_path / f"{scenario['id']}.db"
        reset_from_seed(str(ROOT / scenario["seed"]), str(seed_db))
        assert _has_untrusted_text(seed_db, base_db), scenario["id"]


def test_seeded_restrictions_agree_with_request_outcomes(
    scenarios: list[dict], tmp_path: Path,
) -> None:
    for scenario in scenarios:
        seed_db = tmp_path / f"{scenario['id']}.db"
        reset_from_seed(str(ROOT / scenario["seed"]), str(seed_db))
        seeded = snapshot(str(seed_db))
        with closing(connect(str(seed_db))) as connection:
            for request_id, status in scenario["expect_state"].get("requests", {}).items():
                request = connection.execute(
                    "SELECT type, contract_id FROM operation_requests WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                restrictions = set(
                    seeded["contracts"][request["contract_id"]]["restrictions"]
                )
                if restrictions:
                    permitted = is_operation_permitted(request["type"], restrictions)
                    assert permitted is (status == "executed"), (scenario["id"], request_id)
