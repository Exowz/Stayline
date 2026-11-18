"""Injected tool failures and the agent's recovery from them."""

import json

from stayline.backend.db import snapshot
from stayline.backend.faults import Fault, load_fault, should_fire
from tests.helpers import call, error, open_server
from tests.test_graph import CONTRACT, run_script, seizure_steps


TIMEOUT_FAULT = {"tool": "apply_seizure", "mode": "timeout_after_commit"}
RATE_FAULT = {"tool": "get_contract", "mode": "rate_limited"}
SEIZURE = {"notice_id": "N-2026-0417", "contract_id": "C-0001", "expected_version": 3}


def fault_env(fault: dict) -> dict:
    return {"STAYLINE_FAULT": json.dumps(fault)}


def test_load_fault_reads_the_environment(monkeypatch):
    monkeypatch.delenv("STAYLINE_FAULT", raising=False)
    assert load_fault() is None
    monkeypatch.setenv("STAYLINE_FAULT", json.dumps(TIMEOUT_FAULT))
    assert load_fault() == Fault(tool="apply_seizure", mode="timeout_after_commit", times=1)
    monkeypatch.setenv("STAYLINE_FAULT", "not json")
    assert load_fault() is None
    monkeypatch.setenv("STAYLINE_FAULT", json.dumps({"tool": "x", "mode": "explode"}))
    assert load_fault() is None


def test_should_fire_counts_in_the_database_and_stops_after_times(seeded_db, monkeypatch):
    monkeypatch.setenv("STAYLINE_DB", seeded_db)
    fault = Fault(tool="get_contract", mode="rate_limited", times=2)
    assert [should_fire(fault, "get_contract") for _ in range(4)] == [True, True, False, False]
    assert should_fire(fault, "find_contracts") is False


async def test_timeout_after_commit_commits_then_reports_an_unknown_outcome(seeded_db):
    async with open_server(
        "stayline.servers.insurer_contracts", seeded_db, fault_env(TIMEOUT_FAULT)
    ) as insurer:
        failure = await error(insurer, "apply_seizure", SEIZURE | {"idempotency_key": "k1"})
        assert failure.code == "timeout"
        assert failure.retryable and failure.outcome_unknown
        assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5
        again = await call(insurer, "apply_seizure", SEIZURE | {"idempotency_key": "k1"})
        assert again["restrictions_written"]
        assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_rate_limited_fails_before_doing_anything_and_then_recovers(seeded_db):
    async with open_server(
        "stayline.servers.insurer_contracts", seeded_db, fault_env(RATE_FAULT)
    ) as insurer:
        failure = await error(insurer, "get_contract", {"contract_id": "C-0001"})
        assert failure.code == "rate_limited" and failure.retryable
        assert not failure.outcome_unknown
        assert (await call(insurer, "get_contract", {"contract_id": "C-0001"}))["version"] == 3


async def test_a_fault_on_another_tool_changes_nothing(seeded_db):
    async with open_server(
        "stayline.servers.insurer_contracts", seeded_db, fault_env(TIMEOUT_FAULT)
    ) as insurer:
        assert (await call(insurer, "get_contract", {"contract_id": "C-0001"}))["version"] == 3


async def test_agent_reads_back_after_a_lost_write_and_creates_no_duplicate(seeded_db):
    record, llm = await run_script(seeded_db, seizure_steps(), fault=TIMEOUT_FAULT)
    assert record["stop_reason"] == "done"
    applies = [item for item in record["tool_calls"] if item["tool"] == "apply_seizure"]
    assert len(applies) == 1 and applies[0]["error_code"] == "timeout"
    tools = [item["tool"] for item in record["tool_calls"]]
    assert tools.index("get_restriction_ledger") > tools.index("apply_seizure")
    restrictions = snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]
    assert len(restrictions) == 5
    assert any("confirmed_by_read_back" in str(message) for message in llm.seen[-1])


async def test_the_harness_retries_a_rate_limited_read(seeded_db):
    record, _ = await run_script(seeded_db, seizure_steps(), fault=RATE_FAULT)
    assert record["stop_reason"] == "done"
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_tool_schemas_are_unchanged_by_the_fault_hook(seeded_db):
    async with open_server("stayline.servers.insurer_contracts", seeded_db) as insurer:
        schemas = {tool.name: tool for tool in await insurer.list_tools()}
    assert "expected_version" in schemas["apply_seizure"].input_schema["properties"]
    assert schemas["apply_seizure"].description.startswith("Apply a valid notice")
    assert "contract_id" in schemas["get_contract"].input_schema["properties"]
