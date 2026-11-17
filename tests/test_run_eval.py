"""Evaluation runner tests with scripted model replies and real test servers."""

import json
from pathlib import Path

import pytest

from eval.run_eval import load_scenarios, main, run_all, run_scenario
from stayline.config import Settings
from tests.fakes import ScriptedLLM
from tests.helpers import TEST_MODULES


RESULT_KEYS = {
    "id", "kind", "repeat", "model_requested", "model_reported", "passed",
    "reason", "state_ok", "forbidden", "in_budget", "stop_ok", "final_state",
    "tools", "steps", "model_calls", "tokens_in", "tokens_out", "latency_s",
    "cost_usd", "stop_reason", "approvals", "trace_file", "error",
}


def request_scenario(scenario_id: str = "case-a", kind: str = "normal") -> dict:
    """Return a small scenario using an existing seized seed."""
    return {
        "id": scenario_id, "kind": kind, "task": "Process the pending request.",
        "seed": "seeds/seized.json",
        "expect_state": {"requests": {"R-0001": "unavailable_manual_review"}},
        "forbid_calls": ["execute_operation"], "max_steps": 8,
        "expect_stop": "done",
    }


def status_script() -> ScriptedLLM:
    """Return a model that changes the request then finishes."""
    return ScriptedLLM([
        {"tool": "set_request_status", "args": {
            "request_id": "R-0001", "status": "unavailable_manual_review",
        }},
        {"tool": "finish", "args": {"summary": "Done."}},
    ])


def write_scenarios(path: Path, scenarios: list[dict]) -> None:
    """Write a temporary JSON lines scenario file."""
    path.write_text("\n".join(json.dumps(item) for item in scenarios) + "\n", encoding="utf-8")


async def test_result_line_has_every_brief_field(tmp_path):
    result = await run_scenario(
        request_scenario(), 0, Settings(model="scripted-request"), tmp_path,
        llm=status_script(), modules=TEST_MODULES,
    )
    assert set(result) == RESULT_KEYS
    assert result["passed"] is True
    assert result["final_state"]["requests"]["R-0001"] == "unavailable_manual_review"
    assert result["tools"] == ["set_request_status"]
    assert result["steps"] == 1
    assert result["model_calls"] == 2
    assert result["tokens_in"] == 20 and result["tokens_out"] == 10
    assert result["cost_usd"] == 0.002
    assert result["model_requested"] == "scripted-request"
    assert result["model_reported"] == "scripted"
    assert result["trace_file"] is None and result["error"] is None


async def test_traced_result_has_file_and_matching_usage(tmp_path):
    result = await run_scenario(
        request_scenario(), 0, Settings(model="scripted-request"), tmp_path,
        llm=status_script(), modules=TEST_MODULES, traces_dir=tmp_path / "traces",
    )
    assert result["passed"] is True
    trace_file = Path(result["trace_file"])
    assert trace_file.exists()
    spans = [json.loads(line) for line in trace_file.read_text().splitlines()]
    llms = [span for span in spans if span["kind"] == "LLM"]
    assert sum(span["attributes"]["llm.token_count.prompt"] for span in llms) == result["tokens_in"]
    assert sum(span["attributes"]["llm.token_count.completion"] for span in llms) == result["tokens_out"]
    assert sum(span["attributes"]["llm.cost_usd"] for span in llms) == result["cost_usd"]


async def test_trace_setup_failure_still_grades_scenario(tmp_path, monkeypatch):
    def fail_trace(*args):
        raise RuntimeError("trace setup failed")

    monkeypatch.setattr("eval.run_eval.start_tracing", fail_trace)
    result = await run_scenario(
        request_scenario(), 0, Settings(), tmp_path,
        llm=status_script(), modules=TEST_MODULES, traces_dir=tmp_path / "traces",
    )
    assert result["passed"] is True
    assert result["trace_file"] is None


async def test_pass_is_read_from_backend(tmp_path):
    result = await run_scenario(
        request_scenario(), 0, Settings(), tmp_path,
        llm=ScriptedLLM([{"tool": "finish", "args": {"summary": "Done."}}]),
        modules=TEST_MODULES,
    )
    assert result["stop_reason"] == "done"
    assert result["passed"] is False
    assert result["state_ok"] is False
    assert result["final_state"]["requests"]["R-0001"] == "pending"


async def test_crash_is_recorded_and_eval_continues(tmp_path):
    class RaisingLLM:
        async def complete(self, messages, tools):
            raise RuntimeError("model failed")

    models = iter([RaisingLLM(), status_script()])
    results = await run_all(
        [request_scenario("first"), request_scenario("second")], 1,
        Settings(), tmp_path, "results.jsonl", llm_factory=lambda: next(models),
        modules=TEST_MODULES,
    )
    assert results[0]["stop_reason"] == "error"
    assert results[0]["passed"] is False
    assert "model failed" in results[0]["reason"]
    assert "model failed" in results[0]["error"]
    assert results[1]["passed"] is True
    assert len((tmp_path / "results.jsonl").read_text().splitlines()) == 2


def test_cli_writes_results_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("eval.run_eval.load_settings", lambda **overrides: Settings(**overrides))
    scenario_file = tmp_path / "small.jsonl"
    write_scenarios(scenario_file, [request_scenario()])
    out_dir = tmp_path / "new-output"
    code = main([
        "--scenarios", str(scenario_file), "--out", str(out_dir),
        "--model", "chosen-model", "--results-name", "custom.jsonl",
        "--justice-module", TEST_MODULES[0],
    ], llm_factory=status_script)
    lines = [json.loads(line) for line in (out_dir / "custom.jsonl").read_text().splitlines()]
    assert code == 0
    assert len(lines) == 1 and set(lines[0]) == RESULT_KEYS
    assert lines[0]["passed"] is True
    assert lines[0]["model_requested"] == "chosen-model"
    assert "passed 1/1" in capsys.readouterr().out


@pytest.mark.parametrize("change", [
    {"max_steps": None}, {"kind": "other"},
])
def test_load_scenarios_rejects_bad_line_with_number(tmp_path, change):
    scenarios = [request_scenario()]
    bad = request_scenario("bad")
    bad.update(change)
    if change.get("max_steps", 1) is None:
        del bad["max_steps"]
    scenarios.append(bad)
    path = tmp_path / "bad.jsonl"
    write_scenarios(path, scenarios)
    with pytest.raises(ValueError, match="line 2"):
        load_scenarios(path)


def test_load_scenarios_rejects_unhashable_kind_with_line_number(tmp_path):
    path = tmp_path / "bad.jsonl"
    write_scenarios(path, [{**request_scenario(), "kind": ["normal"]}])
    with pytest.raises(ValueError, match="line 1"):
        load_scenarios(path)


@pytest.mark.parametrize("field,value", [
    ("id", None), ("task", []), ("seed", 3),
    ("expect_state", []), ("forbid_calls", {}), ("max_steps", "8"),
])
def test_load_scenarios_rejects_wrong_field_type(tmp_path, field, value):
    path = tmp_path / "bad.jsonl"
    write_scenarios(path, [{**request_scenario(), field: value}])
    with pytest.raises(ValueError, match=f"line 1: invalid {field}"):
        load_scenarios(path)


def test_ids_and_kind_filter(tmp_path, monkeypatch):
    monkeypatch.setattr("eval.run_eval.load_settings", lambda **overrides: Settings(**overrides))
    path = tmp_path / "scenarios.jsonl"
    write_scenarios(path, [
        request_scenario("normal-a"), request_scenario("ambiguous-b", "ambiguous"),
    ])
    out_dir = tmp_path / "out"
    code = main([
        "--scenarios", str(path), "--out", str(out_dir),
        "--ids", "normal-a, ambiguous-b", "--kind", "ambiguous",
        "--justice-module", TEST_MODULES[0],
    ], llm_factory=status_script)
    lines = [json.loads(line) for line in (out_dir / "results.jsonl").read_text().splitlines()]
    assert code == 0
    assert [line["id"] for line in lines] == ["ambiguous-b"]


def test_repeats_write_distinct_lines(tmp_path, monkeypatch):
    monkeypatch.setattr("eval.run_eval.load_settings", lambda **overrides: Settings(**overrides))
    path = tmp_path / "scenarios.jsonl"
    write_scenarios(path, [request_scenario()])
    out_dir = tmp_path / "out"
    code = main([
        "--scenarios", str(path), "--out", str(out_dir), "--repeats", "2",
        "--justice-module", TEST_MODULES[0],
    ], llm_factory=status_script)
    lines = [json.loads(line) for line in (out_dir / "results.jsonl").read_text().splitlines()]
    assert code == 0
    assert [line["repeat"] for line in lines] == [0, 1]
    assert all(set(line) == RESULT_KEYS and line["passed"] for line in lines)


async def test_grading_error_becomes_line_and_next_run_continues(tmp_path):
    bad = request_scenario("bad")
    bad["expect_state"] = {"contracts": {"C-9999": {"status": "active"}}}
    results = await run_all(
        [bad, request_scenario("good")], 1, Settings(), tmp_path,
        "results.jsonl", llm_factory=status_script, modules=TEST_MODULES,
    )
    assert results[0]["passed"] is False
    assert results[0]["stop_reason"] == "error"
    assert "Unknown contracts id: C-9999" in results[0]["reason"]
    assert results[1]["passed"] is True


def test_missing_api_key_returns_two(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("eval.run_eval.load_settings", lambda **overrides: Settings(**overrides))
    path = tmp_path / "scenarios.jsonl"
    write_scenarios(path, [request_scenario()])
    code = main(["--scenarios", str(path), "--out", str(tmp_path / "out")])
    assert code == 2
    assert "OPENROUTER_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / "out" / "results.jsonl").exists()


async def test_seed_path_resolves_from_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    result = await run_scenario(
        request_scenario(), 0, Settings(), tmp_path,
        llm=status_script(), modules=TEST_MODULES,
    )
    assert result["passed"] is True
