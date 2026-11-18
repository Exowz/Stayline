"""Graph and runner behavior against the seeded MCP servers."""

import json
from contextlib import closing
from pathlib import Path

import pytest
from langgraph.types import Command

from stayline.agent.graph import build_graph
from stayline.agent.prompts import SYSTEM_PROMPT
from stayline.agent.run import always_yes, run_task
from stayline.agent.state import initial_state
from stayline.backend.db import connect, reset_from_seed, snapshot
from stayline.config import load_settings
from tests.fakes import FlakyHarness, ScriptedLLM
from tests.helpers import TEST_MODULES


NOTICE = "N-2026-0417"
CONTRACT = "C-0001"
SEIZURE = {"notice_id": NOTICE, "contract_id": CONTRACT}


def seizure_steps(expected_version: int | None = None) -> list[dict]:
    """Return the normal notice lookup and guarded write script."""
    args = dict(SEIZURE)
    if expected_version is not None:
        args["expected_version"] = expected_version
    return [
        {"tool": "get_notice", "args": {"notice_id": NOTICE}},
        {"tool": "resolve_issuing_authority", "args": {
            "court_id": "TJ-PARIS", "judge_role": "juge_instruction",
            "procedure_type": "information_judiciaire",
        }},
        {"tool": "find_contracts", "args": {
            "subscriber_identity": {
                "last_name": "Benaissa", "first_names": "Karim",
                "birth_date": "1978-03-14", "birth_place_code": "75112",
            }, "contract_reference": "av-2019 004.512",
        }},
        {"tool": "apply_seizure", "args": args},
        {"tool": "finish", "args": {"summary": "Applied."}},
    ]


async def run_script(seeded_db: str, steps: list[dict], **options) -> tuple[dict, ScriptedLLM]:
    """Run a scripted task with the test justice server."""
    llm = ScriptedLLM(steps)
    record = await run_task(
        "Process the request.", operator_id="operator", run_id="graph-test",
        settings=load_settings(db_path=seeded_db), max_steps=options.pop("max_steps", 30),
        approver=options.pop("approver", always_yes), llm=llm,
        modules=TEST_MODULES, **options,
    )
    return record, llm


async def test_seizure_happy_path(seeded_db):
    record, _ = await run_script(seeded_db, seizure_steps())
    assert record["stop_reason"] == "done"
    assert len(record["approvals"]) == 1
    preview = record["approvals"][0]["preview"]
    assert preview["contract"]["contract_id"] == CONTRACT
    assert preview["match"]["outcome"] == "match"
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_rejection_writes_nothing(seeded_db):
    before = snapshot(seeded_db)

    async def reject(preview):
        return {"approve": False, "reason": "needs review"}

    record, llm = await run_script(seeded_db, seizure_steps(), approver=reject)
    assert len(record["approvals"]) == 1
    assert any("rejected by the human: needs review" in str(m)
               for m in llm.seen[-1])
    assert snapshot(seeded_db) == before


async def test_preview_uses_backend_version_not_model_version(seeded_db):
    record, _ = await run_script(seeded_db, seizure_steps(99))
    assert record["approvals"][0]["preview"]["args"]["expected_version"] == 3
    assert record["stop_reason"] == "done"
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_stale_version_returns_to_preview(seeded_db):
    approvals = 0

    async def bump_once(preview):
        nonlocal approvals
        approvals += 1
        if approvals == 1:
            with closing(connect(seeded_db)) as db, db:
                db.execute("UPDATE contracts SET version = version + 1 WHERE contract_id = ?", (CONTRACT,))
        return {"approve": True, "reason": "ok"}

    record, _ = await run_script(seeded_db, seizure_steps(), approver=bump_once)
    assert record["stop_reason"] == "done"
    assert len(record["approvals"]) == 2
    assert [entry["preview"]["args"]["expected_version"] for entry in record["approvals"]] == [3, 4]
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_resume_does_not_double_write(harness, seeded_db):
    llm = ScriptedLLM(seizure_steps())
    graph = build_graph(harness, llm)
    config = {"configurable": {"thread_id": "same-run"}}
    out = await graph.ainvoke(initial_state("Apply notice", "operator", "same-run", 30, 12), config)
    preview = out["__interrupt__"][0].value
    out = await graph.ainvoke(Command(resume={"approve": True, "reason": "ok"}), config)
    assert out["stop_reason"] == "done"
    again = await harness.call("apply_seizure", preview["args"], "same-run")
    assert again.ok
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_outcome_unknown_reads_back_no_duplicate(harness, seeded_db):
    llm = ScriptedLLM(seizure_steps())
    graph = build_graph(FlakyHarness(harness, "apply_seizure"), llm)
    config = {"configurable": {"thread_id": "unknown-run"}}
    out = await graph.ainvoke(initial_state("Apply notice", "operator", "unknown-run", 30, 12), config)
    out = await graph.ainvoke(Command(resume={"approve": True, "reason": "ok"}), config)
    assert out["stop_reason"] == "done"
    assert any("confirmed_by_read_back" in str(message) for message in llm.seen[-1])
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_outcome_unknown_retries_once_when_read_back_is_empty(harness, seeded_db):
    class LostBeforeWrite(FlakyHarness):
        async def call(self, tool, args, run_id):
            if tool == self.tool and self.times > 0:
                self.times -= 1
                from stayline.servers.results import ToolError, ToolResult
                return ToolResult(ok=False, error=ToolError(
                    code="timeout", message="lost", retryable=True, outcome_unknown=True,
                ))
            return await self.inner.call(tool, args, run_id)

    llm = ScriptedLLM(seizure_steps())
    graph = build_graph(LostBeforeWrite(harness, "apply_seizure"), llm)
    config = {"configurable": {"thread_id": "retry-run"}}
    out = await graph.ainvoke(initial_state("Apply notice", "operator", "retry-run", 30, 12), config)
    out = await graph.ainvoke(Command(resume={"approve": True, "reason": "ok"}), config)
    assert out["stop_reason"] == "done"
    assert sum(item["tool"] == "apply_seizure" for item in out["tool_calls"]) == 2
    assert len(snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"]) == 5


async def test_execute_operation_uses_trusted_request_data(seeded_db):
    steps = [
        {"tool": "execute_operation", "args": {
            "request_id": "R-0005", "contract_id": "C-0003", "expected_version": 99,
        }},
        {"tool": "finish", "args": {"summary": "Executed."}},
    ]
    record, _ = await run_script(seeded_db, steps)
    preview = record["approvals"][0]["preview"]
    assert preview["args"]["expected_version"] == 1
    assert preview["effect"] == {"type": "avance", "amount_eur": 2000}
    assert preview["active_restrictions"] == []
    assert record["stop_reason"] == "done"
    assert snapshot(seeded_db)["requests"]["R-0005"] == "executed"
    assert snapshot(seeded_db)["contracts"]["C-0003"]["advance_eur"] == 2000


async def test_refusal_path_sets_status_without_approval(seeded_db):
    steps = [
        {"tool": "set_request_status", "args": {
            "request_id": "R-0001", "status": "unavailable_manual_review",
        }},
        {"tool": "finish", "args": {"summary": "Unavailable for manual review."}},
    ]
    record, _ = await run_script(seeded_db, steps)
    assert record["stop_reason"] == "done"
    assert record["approvals"] == []
    assert snapshot(seeded_db)["requests"]["R-0001"] == "unavailable_manual_review"


@pytest.mark.parametrize("tool,args,reason", [
    ("ask_operator", {"question": "Which contract?"}, "asked_operator"),
    ("refuse", {"reason": "Invalid action."}, "refused"),
])
async def test_ask_and_refuse_stop_reasons(seeded_db, tool, args, reason):
    before = snapshot(seeded_db)
    record, _ = await run_script(seeded_db, [{"tool": tool, "args": args}])
    assert record["stop_reason"] == reason
    assert record["approvals"] == []
    assert snapshot(seeded_db) == before


async def test_step_budget_stop(seeded_db):
    steps = [{"tool": "get_contract", "args": {"contract_id": CONTRACT}}] * 3
    record, _ = await run_script(seeded_db, steps, max_steps=2)
    assert record["stop_reason"] == "max_steps"
    assert len(record["tool_calls"]) == 2
    assert snapshot(seeded_db)["contracts"][CONTRACT]["restrictions"] == {}


async def test_plain_text_twice_is_error_and_never_writes(seeded_db):
    before = snapshot(seeded_db)
    record, llm = await run_script(seeded_db, [{"text": "First."}, {"text": "Second."}])
    assert record["stop_reason"] == "error"
    assert sum("End the run by calling finish" in str(message)
               for messages in llm.seen for message in messages) == 1
    assert snapshot(seeded_db) == before


@pytest.mark.parametrize("seed,contract_id,target,reason", [
    ("deceased_target.json", "C-0005", {
        "last_name": "Lefevre", "first_names": "Paul",
        "birth_date": "1968-02-09", "birth_place_code": "59350",
    }, "deceased"),
    ("surrendered_target.json", "C-0006", {
        "last_name": "Dubois", "first_names": "Anne",
        "birth_date": "1975-08-16", "birth_place_code": "44109",
    }, "surrendered"),
])
async def test_invalid_seizure_target_refused_before_approval(
    tmp_path, seed, contract_id, target, reason,
):
    seed_path = Path(__file__).resolve().parents[1] / "seeds" / seed
    db_path = str(tmp_path / "variant.sqlite")
    reset_from_seed(str(seed_path), db_path)
    before = snapshot(db_path)
    events = []
    steps = [
        {"tool": "get_notice", "args": {"notice_id": NOTICE}},
        {"tool": "find_contracts", "args": {
            "subscriber_identity": target, "contract_reference": None,
        }},
        {"tool": "get_contract", "args": {"contract_id": contract_id}},
        {"tool": "apply_seizure", "args": {
            "notice_id": NOTICE, "contract_id": contract_id,
        }},
        {"tool": "refuse", "args": {"reason": "Target cannot be seized."}},
    ]

    record, llm = await run_script(db_path, steps, on_event=events.append)

    assert record["stop_reason"] == "refused"
    assert record["approvals"] == []
    assert not any(event["type"] == "approval_needed" for event in events)
    assert "apply_seizure" not in [entry["tool"] for entry in record["tool_calls"]]
    assert "operation_not_permitted" in str(llm.seen[-1])
    assert reason in str(llm.seen[-1])
    assert snapshot(db_path) == before


async def test_bad_json_arguments_do_not_crash(seeded_db):
    before = snapshot(seeded_db)
    record, llm = await run_script(seeded_db, [
        {"tool": "get_contract", "raw_arguments": "{not json"},
        {"tool": "finish", "args": {"summary": "Done."}},
    ])
    assert record["stop_reason"] == "done"
    assert "not valid JSON" in str(llm.seen[-1])
    assert snapshot(seeded_db) == before


async def test_prepare_unknown_contract_returns_error_observation(seeded_db):
    before = snapshot(seeded_db)
    record, llm = await run_script(seeded_db, [
        {"tool": "apply_seizure", "args": {"notice_id": NOTICE, "contract_id": "C-9999"}},
        {"tool": "finish", "args": {"summary": "Could not apply."}},
    ])
    assert record["approvals"] == []
    assert "contract_not_found" in str(llm.seen[-1])
    assert snapshot(seeded_db) == before


async def test_runner_error_returns_record(seeded_db):
    class RaisingLLM:
        async def complete(self, messages, tools):
            raise RuntimeError("model failed")

    before = snapshot(seeded_db)
    record = await run_task(
        "Task", operator_id="operator", run_id="error-run",
        settings=load_settings(db_path=seeded_db), max_steps=5,
        approver=always_yes, llm=RaisingLLM(), modules=TEST_MODULES,
    )
    assert record["stop_reason"] == "error"
    assert "RuntimeError: model failed" in record["error"]
    assert snapshot(seeded_db) == before


async def test_finished_event_error_returns_record(seeded_db):
    def on_event(event):
        if event["type"] == "finished":
            raise RuntimeError("event failed")

    before = snapshot(seeded_db)
    record, _ = await run_script(
        seeded_db, [{"tool": "finish", "args": {"summary": "Done."}}],
        on_event=on_event,
    )
    assert record["stop_reason"] == "error"
    assert "RuntimeError: event failed" in record["error"]
    assert snapshot(seeded_db) == before


def test_prompt_has_no_scenario_text():
    for fragment in ("N-2026", "C-00", "R-00", "Orion", "Benaissa"):
        assert fragment not in SYSTEM_PROMPT
    scenarios = Path(__file__).resolve().parents[1] / "eval" / "scenarios.jsonl"
    if not scenarios.exists():
        pytest.skip("Scenario file is absent")
    for line in scenarios.read_text().splitlines():
        assert json.loads(line)["task"] not in SYSTEM_PROMPT


def test_prompt_directs_refusal_for_missing_contract_and_forbidden_task():
    assert ("If searching for the target by identity and by policy number both return "
            "contract_not_found, the contract is not held by this insurer: stop searching "
            "and call refuse.") in SYSTEM_PROMPT
    assert ("If the task itself asks you to bypass, ignore or lift a restriction, or to do "
            "something the rules never allow, call refuse and change nothing. Setting a "
            "request status is only for adviser requests you are processing normally.") in SYSTEM_PROMPT
