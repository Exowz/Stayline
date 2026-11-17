"""A stored alias changes a later run, in a new thread with a new store handle."""

from stayline.agent.run import always_yes, run_task
from stayline.backend.db import snapshot
from stayline.config import load_settings
from stayline.memory.aliases import open_store, recall_aliases
from tests.fakes import ConditionalLLM, ScriptedLLM
from tests.helpers import TEST_MODULES


REMEMBER = {"tool": "remember_alias", "args": {
    "alias": "Orion", "case_reference": "2026/00417", "court": "TJ Paris",
}}
FIRST_TASK = "Orion is instruction 2026/00417 at TJ Paris"
SECOND_TASK = "A CGP request came in on the Orion contract, process it"
REFUSE = {"tool": "set_request_status", "args": {
    "request_id": "R-0001", "status": "unavailable_manual_review",
}}


async def run(task, seeded_db, store, llm, operator="op-1", run_id="run"):
    return await run_task(
        task, operator_id=operator, run_id=run_id, settings=load_settings(db_path=seeded_db),
        max_steps=20, approver=always_yes, llm=llm, store=store, modules=TEST_MODULES,
    )


def second_run_model() -> ConditionalLLM:
    return ConditionalLLM(
        with_memory=[
            {"tool": "find_notices", "args": {"case_reference": "2026/00417", "court_id": "TJ-PARIS"}},
            REFUSE,
            {"tool": "finish", "args": {"summary": "Request R-0001 is unavailable."}},
        ],
        without_memory=[{"tool": "ask_operator", "args": {"question": "Which contract is Orion?"}}],
    )


async def test_alias_given_in_run_one_changes_run_two(seeded_db, tmp_path):
    memory = str(tmp_path / "memory.sqlite")
    seed = snapshot(seeded_db)
    with open_store(memory) as store:
        first = await run(FIRST_TASK, seeded_db, store, ScriptedLLM([
            REMEMBER, {"tool": "finish", "args": {"summary": "Noted."}},
        ]), run_id="thread-1")
    assert first["stop_reason"] == "done" and snapshot(seeded_db) == seed
    with open_store(memory) as store:
        assert "orion" in recall_aliases(store, "op-1")
        model = second_run_model()
        second = await run(SECOND_TASK, seeded_db, store, model, run_id="thread-2")
    assert any("Known aliases" in str(item.get("content")) for item in model.seen[0])
    assert second["stop_reason"] == "done"
    assert snapshot(seeded_db)["requests"]["R-0001"] == "unavailable_manual_review"


async def test_same_second_run_on_an_empty_store_asks_and_changes_nothing(seeded_db, tmp_path):
    seed = snapshot(seeded_db)
    with open_store(str(tmp_path / "empty.sqlite")) as store:
        model = second_run_model()
        record = await run(SECOND_TASK, seeded_db, store, model, run_id="thread-2")
    assert not any("Known aliases" in str(item.get("content")) for item in model.seen[0])
    assert record["stop_reason"] == "asked_operator"
    assert snapshot(seeded_db) == seed


async def test_another_operator_does_not_get_the_alias(seeded_db, tmp_path):
    memory = str(tmp_path / "memory.sqlite")
    seed = snapshot(seeded_db)
    with open_store(memory) as store:
        await run(FIRST_TASK, seeded_db, store, ScriptedLLM([
            REMEMBER, {"tool": "finish", "args": {"summary": "Noted."}},
        ]), operator="op-1", run_id="thread-1")
        model = second_run_model()
        record = await run(SECOND_TASK, seeded_db, store, model, operator="op-2", run_id="thread-2")
    assert record["stop_reason"] == "asked_operator"
    assert snapshot(seeded_db) == seed


async def test_remember_guard_rejects_a_value_the_operator_never_said(seeded_db, tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        record = await run("Process the request.", seeded_db, store, ScriptedLLM([
            REMEMBER, {"tool": "finish", "args": {"summary": "Done."}},
        ]))
        assert recall_aliases(store, "op-1") == {}
    assert record["stop_reason"] == "done"


async def test_remember_without_a_store_is_a_typed_error_not_a_crash(seeded_db):
    record = await run(FIRST_TASK, seeded_db, None, ScriptedLLM([
        REMEMBER, {"tool": "finish", "args": {"summary": "Done."}},
    ]))
    assert record["stop_reason"] == "done"
