"""Assemble read-only evaluation data from the report's metrics."""

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval.report import (  # noqa: E402
    compare, cost_per_success, domain_metrics, load_rows, overall, per_kind,
    percentiles, seed_snapshots,
)


def result_path(eval_dir: Path, name: str) -> Path | None:
    """Validate a result name and return its contained path, or None."""
    segment = r"[A-Za-z0-9_.-]+"
    if ".." in name or re.fullmatch(rf"(?:{segment}/)?{segment}\.jsonl", name) is None:
        return None
    root = eval_dir.resolve()
    path = (root / name).resolve()
    return path if path.is_relative_to(root) else None


def domain_for(rows: list[dict], eval_dir: Path) -> dict | None:
    """Rebuild the report's seed snapshots when scenarios are available."""
    scenarios_path = eval_dir / "scenarios.jsonl"
    if not scenarios_path.is_file():
        return None
    scenarios = load_rows(scenarios_path)
    seeds = seed_snapshots(scenarios, {item["id"] for item in rows})
    return domain_metrics(rows, scenarios, seeds)


def extra(name: str, rows: list[dict], domain: dict | None) -> dict:
    """Describe the cost, latency and model of one result set."""
    latency = percentiles([item["latency_s"] for item in rows])
    return {
        "name": name,
        "model": rows[0].get("model_reported") if rows else None,
        "cost_per_success": cost_per_success(rows),
        "latency_s": {"p50": latency[50], "p95": latency[95]},
        "total_cost_usd": sum(item["cost_usd"] for item in rows),
        "domain": domain,
    }


def summary(name: str, rows: list[dict], domain: dict | None) -> dict:
    """Group report metrics and individual scenario outcomes."""
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for item in rows:
        by_scenario[item["id"]].append(item)
    scenario_rows = []
    for sid, group in sorted(by_scenario.items(), key=lambda pair: (
        int(match.group(1)) if (match := re.search(r"(\d+)$", pair[0])) else -1,
        pair[0],
    )):
        group.sort(key=lambda item: item["repeat"])
        scenario_rows.append({
            "id": sid, "kind": group[0]["kind"],
            "passed": sum(bool(item["passed"]) for item in group),
            "runs": len(group),
            "stop_reasons": [item.get("stop_reason") for item in group],
        })
    failures = [{key: item.get(key) for key in (
        "id", "repeat", "kind", "stop_reason", "reason",
    )} for item in rows if not item["passed"]]
    costs = percentiles([item["cost_usd"] for item in rows])
    common = extra(name, rows, domain)
    return {
        **common, "runs": len(rows), "scenarios": len(by_scenario),
        "overall": overall(rows), "by_kind": per_kind(rows),
        "cost_usd": {"p50": costs[50], "p95": costs[95]},
        "scenario_rows": scenario_rows, "failed": failures,
    }


def comparison(a_name: str, a_rows: list[dict], a_domain: dict | None,
               b_name: str, b_rows: list[dict], b_domain: dict | None) -> dict:
    """Add display data to the report's paired comparison."""
    return {
        **compare(a_rows, b_rows),
        "a_extra": extra(a_name, a_rows, a_domain),
        "b_extra": extra(b_name, b_rows, b_domain),
    }
