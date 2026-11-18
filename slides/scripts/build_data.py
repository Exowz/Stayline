"""Build measured deck data from committed evaluation results and traces."""

from datetime import datetime
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval import report  # noqa: E402


DEST = ROOT / "slides/generated/deck.json"


def compact_runs(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (int(row["id"][1:]), row["repeat"]))
    keys = ("id", "kind", "repeat", "passed", "stop_reason", "steps")
    return [{key: row[key] for key in keys} for row in ordered]


def summary(rows: list[dict], scenarios: list[dict], seeds: dict[str, dict]) -> dict:
    overall = report.overall(rows)
    return {
        "passed": overall["passed"], "runs": overall["runs"],
        "pass_rate": overall["pass_rate"], "by_kind": report.per_kind(rows),
        "overall": {key: overall[key] for key in ("pass_hat_k", "ci_low", "ci_high")},
        "cost_per_success": report.cost_per_success(rows),
        "latency_s": report.percentiles([row["latency_s"] for row in rows]),
        "domain": report.domain_metrics(rows, scenarios, seeds),
    }


def trace(path: Path) -> dict:
    rows = report.load_rows(path)
    root = next(row for row in rows if row["kind"] == "AGENT")
    spans = [row for row in rows if row["kind"] != "AGENT"]
    first = min(datetime.fromisoformat(row["start"]) for row in spans)
    result = []
    for row in spans:
        attrs = row.get("attributes", {})
        result.append({
            "name": row["name"], "kind": row["kind"], "ms": row["ms"],
            "status": row["status"],
            "tokens_in": attrs.get("llm.token_count.prompt", 0),
            "tokens_out": attrs.get("llm.token_count.completion", 0),
            "cost_usd": attrs.get("llm.cost_usd", 0),
            "t0_ms": (datetime.fromisoformat(row["start"]) - first).total_seconds() * 1000,
        })
    return {
        "spans": result, "total_ms": root["ms"],
        "total_tokens_in": sum(row["tokens_in"] for row in result),
        "total_tokens_out": sum(row["tokens_out"] for row in result),
        "total_cost_usd": sum(row["cost_usd"] for row in result),
        "model_calls": sum(row["kind"] == "LLM" for row in result),
        "tool_calls": sum(row["kind"] == "TOOL" for row in result),
    }


def main() -> None:
    rows = report.load_rows(ROOT / "eval/results.jsonl")
    mistral = report.load_rows(ROOT / "eval/mistral/results.jsonl")
    baseline = report.load_rows(ROOT / "eval/runs/2026-11-18-baseline-1/results.jsonl")
    scenarios = report.load_rows(ROOT / "eval/scenarios.jsonl")
    seeds = report.seed_snapshots(scenarios, {row["id"] for row in rows + mistral + baseline})
    failing = next(row for row in rows if row["id"] == "s14" and row["repeat"] == 2)
    deck = {
        "runs": compact_runs(rows), "mistral_runs": compact_runs(mistral),
        "baseline1_runs": compact_runs(baseline),
        "summary": summary(rows, scenarios, seeds),
        "mistral_summary": summary(mistral, scenarios, seeds),
        "baseline1_summary": summary(baseline, scenarios, seeds),
        "comparison": report.compare(rows, mistral),
        "traces": {
            "s01": trace(ROOT / "docs/defence/traces/s01-0.jsonl"),
            "s14": trace(ROOT / "docs/defence/traces/s14-2.jsonl"),
        },
        "s14": {"reason": failing["reason"], "stop_reason": failing["stop_reason"]},
    }
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {DEST}")


if __name__ == "__main__":
    main()
