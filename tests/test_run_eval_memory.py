"""The evaluation runner handles operator, memory and prior_tasks scenario fields."""

import json
from pathlib import Path

import pytest

from eval.run_eval import load_scenarios, run_scenario
from stayline.config import Settings
from tests.fakes import ConditionalLLM, ScriptedLLM
from tests.helpers import TEST_MODULES


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {item["id"]: item for item in load_scenarios(ROOT / "eval/scenarios.jsonl")}
ASK = {"tool": "ask_operator", "args": {"question": "Which contract is Orion?"}}
DONE = {"tool": "finish", "args": {"summary": "Done."}}
REFUSE_R5 = {"tool": "set_request_status", "args": {
    "request_id": "R-0005", "status": "unavailable_manual_review",
}}


async def test_corrected_alias_is_used_by_the_later_run(tmp_path):
    llm = ScriptedLLM([
        {"tool": "remember_alias", "args": {
            "alias": "Orion", "case_reference": "2026/00500", "court": "TJ Lyon",
        }},
        DONE,
        {"tool": "find_notices", "args": {"case_reference": "2026/00500", "court_id": "TJ-LYON"}},
        REFUSE_R5,
        DONE,
    ])
    result = await run_scenario(
        SCENARIOS["s14"], 0, Settings(), tmp_path, llm=llm, modules=TEST_MODULES,
    )
    assert result["passed"] is True, result["reason"]
    assert result["prior_tools"] == [[]]
    final_hint = next(
        item["content"] for item in llm.seen[2] if "Known aliases" in str(item.get("content"))
    )
    assert "2026/00500" in final_hint and "2026/00417" not in final_hint


async def test_unknown_alias_with_memory_off_asks_and_changes_nothing(tmp_path):
    llm = ConditionalLLM(with_memory=[REFUSE_R5, DONE], without_memory=[ASK])
    result = await run_scenario(
        SCENARIOS["s18"], 0, Settings(), tmp_path, llm=llm, modules=TEST_MODULES,
    )
    assert result["passed"] is True, result["reason"]
    assert result["stop_reason"] == "asked_operator" and "prior_tools" not in result


async def test_alias_of_another_operator_is_not_shown(tmp_path):
    llm = ConditionalLLM(with_memory=[REFUSE_R5, DONE], without_memory=[ASK])
    result = await run_scenario(
        SCENARIOS["s19"], 0, Settings(), tmp_path, llm=llm, modules=TEST_MODULES,
    )
    assert result["passed"] is True, result["reason"]
    assert not any("Known aliases" in str(item.get("content")) for item in llm.seen[0])


async def test_the_alias_hint_reaches_the_right_operator(tmp_path):
    scenario = {**SCENARIOS["s19"], "operator": "op-alice"}
    llm = ConditionalLLM(with_memory=[REFUSE_R5, DONE], without_memory=[ASK])
    result = await run_scenario(scenario, 0, Settings(), tmp_path, llm=llm, modules=TEST_MODULES)
    assert any("Known aliases" in str(item.get("content")) for item in llm.seen[0])
    assert result["passed"] is False and result["tools"] == ["set_request_status"]


@pytest.mark.parametrize("field,value", [
    ("operator", 5), ("memory", []), ("prior_tasks", {}),
])
def test_optional_fields_are_type_checked(tmp_path, field, value):
    line = {**SCENARIOS["s18"], field: value}
    path = tmp_path / "scenarios.jsonl"
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=f"invalid {field}"):
        load_scenarios(path)
