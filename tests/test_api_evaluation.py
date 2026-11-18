"""Read-only evaluation summary and comparison routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stayline.api.app import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]


def client_for(eval_dir: Path) -> TestClient:
    return TestClient(create_app(eval_dir=eval_dir, ui_dist=REPO_ROOT / "missing-ui"))


def test_main_summary():
    with client_for(REPO_ROOT / "eval") as client:
        response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert (data["runs"], data["scenarios"], data["overall"]["passed"]) == (90, 30, 88)
    assert [row["kind"] for row in data["by_kind"]] == [
        "normal", "ambiguous", "impossible", "adversarial",
    ]
    assert len(data["failed"]) == 2
    assert {row["id"] for row in data["failed"]} == {"s14"}
    assert data["domain"]["under_blocking"] == 0
    assert len(data["scenario_rows"]) == 30
    assert data["scenario_rows"][13]["stop_reasons"] == ["done", "done", "error"]


def test_other_summary_and_comparison():
    with client_for(REPO_ROOT / "eval") as client:
        other = client.get("/api/summary", params={"name": "mistral/results.jsonl"})
        comparison = client.get("/api/comparison", params={
            "a": "results.jsonl", "b": "mistral/results.jsonl",
        })
    assert other.status_code == 200
    assert other.json()["overall"]["passed"] == 60
    assert comparison.status_code == 200
    data = comparison.json()
    assert data["shared"] == 30
    assert data["only_a"] == 11
    assert data["sign_test_p"] < 0.002
    assert data["a_extra"]["model"] == "deepseek/deepseek-v4.1-flash"
    assert data["b_extra"]["model"] == "mistralai/mistral-small-2603"


@pytest.mark.parametrize("name", ["../x.jsonl", "a/b/c.jsonl", "results.json"])
def test_bad_names(name: str):
    with client_for(REPO_ROOT / "eval") as client:
        assert client.get("/api/summary", params={"name": name}).status_code == 400
        assert client.get("/api/comparison", params={"a": name, "b": "results.jsonl"}).status_code == 400


def test_missing_and_empty(tmp_path: Path):
    (tmp_path / "results.jsonl").write_text("", encoding="utf-8")
    with client_for(tmp_path) as client:
        assert client.get("/api/summary", params={"name": "missing.jsonl"}).status_code == 404
        assert client.get("/api/comparison", params={
            "a": "results.jsonl", "b": "missing.jsonl",
        }).status_code == 404
        data = client.get("/api/summary").json()
    assert data["runs"] == 0
    assert data["overall"]["passed"] == 0
    assert data["scenario_rows"] == []
    assert data["domain"] is None


def test_symlink_outside_eval_dir(tmp_path: Path):
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    outside = tmp_path / "outside.jsonl"
    outside.write_text("", encoding="utf-8")
    (eval_dir / "outside.jsonl").symlink_to(outside)
    with client_for(eval_dir) as client:
        assert client.get("/api/summary", params={"name": "outside.jsonl"}).status_code == 400
