"""UI service routes and Studio entry point."""

import json
import re
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stayline.agent.state import initial_state
from stayline.backend.db import reset_from_seed
from stayline.config import load_settings
from tests.fakes import ScriptedLLM
from tests.helpers import TEST_MODULES


ROOT = Path(__file__).resolve().parents[1]


def seizure_steps() -> list[dict]:
    """Request a guarded seizure through the normal read path."""
    return [
        {"tool": "get_notice", "args": {"notice_id": "N-2026-0417"}},
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
        {"tool": "apply_seizure", "args": {
            "notice_id": "N-2026-0417", "contract_id": "C-0001",
        }},
        {"tool": "finish", "args": {"summary": "Applied."}},
    ]


def client_for(tmp_path: Path, steps: list[dict] | None = None) -> TestClient:
    """Create an isolated app with scripted model and seed data."""
    from stayline.api.app import create_app

    db_path = tmp_path / "state.sqlite"
    reset_from_seed(str(ROOT / "seeds" / "base.json"), str(db_path))
    settings = load_settings(
        db_path=str(db_path), checkpoint_db_path=str(tmp_path / "checkpoints.sqlite"),
    )
    return TestClient(create_app(
        settings=settings, llm_factory=lambda: ScriptedLLM(steps or []),
        modules=TEST_MODULES, eval_dir=tmp_path / "eval",
        ui_dist=tmp_path / "missing-ui",
    ))


def events(client: TestClient, run_id: str) -> list[dict]:
    """Read the completed SSE replay as JSON messages."""
    response = client.get(f"/api/runs/{run_id}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return [json.loads(line.removeprefix("data: ")) for line in response.text.splitlines()
            if line.startswith("data: ")]


def decide_when_pending(client: TestClient, run_id: str, approve: bool) -> None:
    """Wait for the scripted run to reach its approval pause."""
    for _ in range(200):
        response = client.post(f"/api/runs/{run_id}/decision", json={
            "approve": approve, "reason": "reviewed",
        })
        if response.status_code == 200:
            return
        assert response.status_code == 409
        time.sleep(0.02)
    pytest.fail("Run did not reach approval")


def test_approval_stream_and_ledger(tmp_path: Path):
    with client_for(tmp_path, seizure_steps()) as client:
        response = client.post("/api/runs", json={"task": "Apply notice"})
        assert response.status_code == 200
        run_id = response.json()["run_id"]
        assert re.fullmatch(r"run-[0-9a-f]{8}", run_id)
        decide_when_pending(client, run_id, True)
        stream = events(client, run_id)
        kinds = [item["type"] for item in stream]
        assert "model" in kinds
        assert "tool" in kinds
        assert kinds.index("tool") < kinds.index("approval_needed")
        preview = next(item["preview"] for item in stream
                       if item["type"] == "approval_needed")
        assert preview["tool"] == "apply_seizure"
        assert preview["contract"]["contract_id"] == "C-0001"
        assert next(item for item in stream if item["type"] == "approval_decided")["approve"]
        assert stream[-1]["type"] == "finished"
        assert stream[-1]["stop_reason"] == "done"
        assert stream[-1]["steps"] >= 4
        assert stream[-1]["tokens_in"] > 0
        assert any(item["type"] == "tool" and item["tool"] == "get_notice"
                   and item["ok"] and "args" in item for item in stream)
        ledger = client.get("/api/ledger").json()
        assert ledger["restricted_contracts"] == ["C-0001"]
        assert len(ledger["rows"]) == 5
        assert {row["notice_id"] for row in ledger["rows"]} == {"N-2026-0417"}
        assert set(ledger["operations"]) == {"blocked", "permitted", "pending"}


def test_rejection_leaves_ledger_empty(tmp_path: Path):
    with client_for(tmp_path, seizure_steps()) as client:
        run_id = client.post("/api/runs", json={"task": "Apply notice"}).json()["run_id"]
        decide_when_pending(client, run_id, False)
        assert events(client, run_id)[-1]["type"] == "finished"
        assert client.get("/api/ledger").json()["rows"] == []


def test_reset_seed_and_reject_bad_names(tmp_path: Path):
    with client_for(tmp_path) as client:
        assert "base.json" in client.get("/api/seeds").json()
        response = client.post("/api/reset", json={"seed": "seized.json"})
        assert response.status_code == 200
        assert len(response.json()["contracts"]["C-0001"]["restrictions"]) == 5
        assert len(client.get("/api/ledger").json()["rows"]) == 5
        for seed in ("missing.json", "../x.json"):
            assert client.post("/api/reset", json={"seed": seed}).status_code == 404


def test_active_run_conflicts_and_unknown_run(tmp_path: Path):
    with client_for(tmp_path, seizure_steps()) as client:
        assert client.post("/api/runs/absent/decision", json={"approve": True}).status_code == 404
        assert client.get("/api/runs/absent/events").status_code == 404
        run_id = client.post("/api/runs", json={"task": "Apply notice"}).json()["run_id"]
        assert client.post("/api/runs", json={"task": "Another"}).status_code == 409
        assert client.post("/api/reset", json={"seed": "base.json"}).status_code == 409
        decide_when_pending(client, run_id, True)
        assert client.post(f"/api/runs/{run_id}/decision", json={"approve": True}).status_code == 409
        assert events(client, run_id)[-1]["type"] == "finished"


def test_results_file_and_name_validation(tmp_path: Path):
    with client_for(tmp_path) as client:
        assert client.get("/api/results").json() == []
        result_dir = tmp_path / "eval"
        result_dir.mkdir()
        (result_dir / "results.jsonl").write_text('{"id": "one"}\n{"id": "two"}\n')
        (result_dir / "other.jsonl").write_text('{"id": "other"}\n')
        assert client.get("/api/results").json() == [{"id": "one"}, {"id": "two"}]
        assert client.get("/api/results?name=other.jsonl").json() == [{"id": "other"}]
        assert client.get("/api/results?name=../other.jsonl").status_code == 400


@pytest.mark.asyncio
async def test_studio_helper_runs_finish(seeded_db: str):
    from stayline.agent.studio import build_studio_graph

    llm = ScriptedLLM([{"tool": "finish", "args": {"summary": "Done."}}])
    async with build_studio_graph(load_settings(db_path=seeded_db), llm, TEST_MODULES) as graph:
        out = await graph.ainvoke(
            initial_state("Done", "operator", "studio-test", 4, 12),
            {"configurable": {"thread_id": "studio-test"}},
        )
    assert out["stop_reason"] == "done"


def test_finished_after_model_error(tmp_path: Path):
    class RaisingLLM(ScriptedLLM):
        async def complete(self, messages, tools):
            raise RuntimeError("model failed")

    with client_for(tmp_path) as client:
        from stayline.api.app import create_app

        settings = load_settings(
            db_path=str(tmp_path / "state.sqlite"),
            checkpoint_db_path=str(tmp_path / "checkpoints.sqlite"),
        )
        with TestClient(create_app(
            settings=settings, llm_factory=lambda: RaisingLLM([]), modules=TEST_MODULES,
            ui_dist=tmp_path / "missing-ui",
        )) as error_client:
            run_id = error_client.post("/api/runs", json={"task": "Fail"}).json()["run_id"]
            stream = events(error_client, run_id)
            assert stream[-1]["type"] == "finished"
            assert stream[-1]["stop_reason"] == "error"
