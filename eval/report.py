"""Turn results.jsonl into the course and domain metrics of the evaluation."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import math
from collections import defaultdict
from tempfile import TemporaryDirectory

from eval.grade import expected_snapshot
from stayline.backend.db import reset_from_seed, snapshot


REPO_ROOT = Path(__file__).resolve().parents[1]
KIND_ORDER = ("normal", "ambiguous", "impossible", "adversarial")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Return the Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def _by_scenario(rows: list[dict]) -> dict[str, list[dict]]:
    """Group result rows by scenario id."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in rows:
        groups[item["id"]].append(item)
    return groups


def pass_hat_k(rows: list[dict]) -> float:
    """Return the share of scenarios whose every repeat passed (pass^k)."""
    groups = _by_scenario(rows)
    if not groups:
        return 0.0
    return sum(all(item["passed"] for item in group) for group in groups.values()) / len(groups)


def pass_at_k(rows: list[dict]) -> float:
    """Return the share of scenarios with at least one passing repeat (pass@k)."""
    groups = _by_scenario(rows)
    if not groups:
        return 0.0
    return sum(any(item["passed"] for item in group) for group in groups.values()) / len(groups)


def cost_per_success(rows: list[dict]) -> float | None:
    """Divide the cost of every run, failures included, by the passed runs."""
    passed = sum(item["passed"] for item in rows)
    if passed == 0:
        return None
    return sum(item["cost_usd"] for item in rows) / passed


def percentiles(values: list[float], points: tuple[int, ...] = (50, 95)) -> dict:
    """Return linearly interpolated percentiles, or None for an empty list."""
    ordered = sorted(values)
    result: dict = {}
    for point in points:
        if not ordered:
            result[point] = None
            continue
        position = (len(ordered) - 1) * point / 100
        low, high = math.floor(position), math.ceil(position)
        result[point] = ordered[low] + (ordered[high] - ordered[low]) * (position - low)
    return result


def top_share(values: list[float], fraction: float = 0.05) -> float | None:
    """Return the share of the total held by the largest fraction of the values."""
    total = sum(values)
    if not values or total == 0:
        return None
    count = max(1, math.ceil(len(values) * fraction))
    return sum(sorted(values, reverse=True)[:count]) / total


def sign_test(only_a: int, only_b: int) -> float:
    """Return the exact two-sided sign test p-value for discordant scenarios."""
    n = only_a + only_b
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(only_a, only_b) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def overall(rows: list[dict]) -> dict:
    """Summarise pass rates for a set of rows, with a Wilson interval over scenarios."""
    scenarios = len({item["id"] for item in rows})
    passed = sum(item["passed"] for item in rows)
    rate = passed / len(rows) if rows else 0.0
    low, high = wilson(round(rate * scenarios), scenarios)
    return {
        "scenarios": scenarios, "runs": len(rows), "passed": passed, "pass_rate": rate,
        "ci_low": low, "ci_high": high,
        "pass_hat_k": pass_hat_k(rows), "pass_at_k": pass_at_k(rows),
    }


def per_kind(rows: list[dict]) -> list[dict]:
    """Summarise each scenario kind, in the order of the evaluation."""
    kinds = sorted({item["kind"] for item in rows}, key=lambda kind: (
        KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER), kind,
    ))
    return [{"kind": kind, **overall([item for item in rows if item["kind"] == kind])}
            for kind in kinds]


def _lineage_complete(value: str) -> bool:
    """Check that a ledger value names a notice, a rule and a version."""
    notice, _, source = value.partition("|")
    rule, _, version = source.partition("@")
    return all(part.strip() for part in (notice, rule, version))


def domain_metrics(rows: list[dict], scenarios: list[dict], seeds: dict[str, dict]) -> dict:
    """Count blocking errors from final states; every figure is read from the backend."""
    by_id = {item["id"]: item for item in scenarios}
    counts = {"runs": 0, "runs_without_state": 0, "under_blocking": 0, "over_blocking": 0,
              "wrong_contract_changes": 0}
    restrictions_total = restrictions_complete = previews_total = previews_right = 0
    for item in rows:
        final = item.get("final_state")
        scenario = by_id.get(item["id"])
        if final is None or scenario is None or item["id"] not in seeds:
            counts["runs_without_state"] += 1
            continue
        counts["runs"] += 1
        seed = seeds[item["id"]]
        expected = expected_snapshot(seed, scenario["expect_state"])
        under = over = False
        for request_id, wanted in expected["requests"].items():
            got = final["requests"].get(request_id)
            under |= wanted != "executed" and got == "executed"
            over |= wanted == "executed" and got != "executed"
        for contract_id, wanted in expected["contracts"].items():
            got = final["contracts"].get(contract_id, {}).get("restrictions", {})
            under |= bool(set(wanted["restrictions"]) - set(got))
            over |= bool(set(got) - set(wanted["restrictions"]))
        counts["under_blocking"] += under
        counts["over_blocking"] += over
        listed = set(scenario["expect_state"].get("contracts", {}))
        counts["wrong_contract_changes"] += any(
            contract != seed["contracts"].get(contract_id)
            for contract_id, contract in final["contracts"].items() if contract_id not in listed
        )
        for contract in final["contracts"].values():
            for value in contract["restrictions"].values():
                restrictions_total += 1
                restrictions_complete += _lineage_complete(value)
        for approval in item.get("approvals", []):
            previews_total += 1
            previews_right += approval["preview"]["contract"]["contract_id"] in listed
    counts["lineage_completeness"] = (
        restrictions_complete / restrictions_total if restrictions_total else None
    )
    counts["previews_on_expected_contract"] = (
        previews_right / previews_total if previews_total else None
    )
    return counts


def _all_passed(rows: list[dict]) -> dict[str, bool]:
    """Map each scenario id to whether every one of its repeats passed."""
    return {sid: all(item["passed"] for item in group) for sid, group in _by_scenario(rows).items()}


def compare(rows_a: list[dict], rows_b: list[dict]) -> dict:
    """Compare two result sets on the scenarios they share, with the paired sign test."""
    a, b = _all_passed(rows_a), _all_passed(rows_b)
    shared = a.keys() & b.keys()
    only_a = sum(a[sid] and not b[sid] for sid in shared)
    only_b = sum(b[sid] and not a[sid] for sid in shared)
    return {
        "shared": len(shared), "only_a": only_a, "only_b": only_b,
        "both": sum(a[sid] and b[sid] for sid in shared),
        "neither": sum(not a[sid] and not b[sid] for sid in shared),
        "sign_test_p": sign_test(only_a, only_b),
        "a": {"overall": overall(rows_a), "by_kind": per_kind(rows_a)},
        "b": {"overall": overall(rows_b), "by_kind": per_kind(rows_b)},
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _num(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _table(header: list[str], body: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return lines + ["| " + " | ".join(line) + " |" for line in body]


def _kind_table(rows: list[dict]) -> list[str]:
    body = [[item["kind"], str(item["scenarios"]), str(item["runs"]),
             f'{item["passed"]}/{item["runs"]}', _pct(item["pass_rate"]),
             f'{_pct(item["ci_low"])} to {_pct(item["ci_high"])}',
             _pct(item["pass_at_k"]), _pct(item["pass_hat_k"])]
            for item in per_kind(rows) + [{"kind": "all", **overall(rows)}]]
    return _table(["Kind", "Scenarios", "Runs", "Passed", "Pass rate", "Wilson 95%",
                   "pass@k", "pass^k"], body)


def render(
    rows: list[dict], scenarios: list[dict], seeds: dict[str, dict],
    other: list[dict] | None = None,
) -> str:
    """Write the evaluation summary as markdown."""
    models = sorted({str(item.get("model_reported")) for item in rows})
    repeats = max((len(group) for group in _by_scenario(rows).values()), default=0)
    costs = [item["cost_usd"] for item in rows]
    latency = percentiles([item["latency_s"] for item in rows])
    cost_points = percentiles(costs)
    domain = domain_metrics(rows, scenarios, seeds)
    lines = ["# Evaluation summary", "",
             f"{len(rows)} runs over {len({item['id'] for item in rows})} scenarios, "
             f"up to {repeats} repeat(s) each. Model reported by the API: {', '.join(models)}.",
             "", "## Pass rate by kind", ""]
    lines += _kind_table(rows)
    lines += ["", "The Wilson interval treats the number of distinct scenarios as the sample "
              "size. pass@k is the share of scenarios with any passing repeat; pass^k, with "
              "every repeat passing.", "", "## Cost and latency", ""]
    lines += _table(["Measure", "Value"], [
        ["Total cost (USD)", _num(sum(costs))],
        ["Cost per success (USD)", _num(cost_per_success(rows))],
        ["Tokens in / out", f'{sum(item["tokens_in"] for item in rows)} / '
                            f'{sum(item["tokens_out"] for item in rows)}'],
        ["Latency p50 / p95 (s)", f"{_num(latency[50], 2)} / {_num(latency[95], 2)}"],
        ["Cost p50 / p95 (USD)", f"{_num(cost_points[50])} / {_num(cost_points[95])}"],
        ["Share of the bill from the top 5% of runs", _pct(top_share(costs))],
    ])
    lines += ["", "## Domain metrics", ""]
    lines += _table(["Metric", "Value"], [
        ["Runs with a final state", str(domain["runs"])],
        ["Under-blocking (forbidden operation executed or expected restriction missing)",
         str(domain["under_blocking"])],
        ["Over-blocking (permitted operation refused or extra restriction written)",
         str(domain["over_blocking"])],
        ["Wrong-contract changes (must be 0)", str(domain["wrong_contract_changes"])],
        ["Lineage completeness", _pct(domain["lineage_completeness"])],
        ["Approval previews on the expected contract",
         _pct(domain["previews_on_expected_contract"])],
        ["Runs without a final state (crashes)", str(domain["runs_without_state"])],
    ])
    failed = [item for item in rows if not item["passed"]]
    lines += ["", "## Failed runs", ""]
    if failed:
        lines += _table(["Run", "Kind", "Stop reason", "Why"], [
            [f'{item["id"]}#{item["repeat"]}', item["kind"], str(item.get("stop_reason")),
             str(item.get("reason", "")).replace("|", "/")] for item in failed])
    else:
        lines.append("No failed run.")
    if other is not None:
        result = compare(rows, other)
        lines += ["", "## Comparison with the second result set", "",
                  f"{result['shared']} shared scenarios. All repeats passed: only the first "
                  f"set {result['only_a']}, only the second set {result['only_b']}, both "
                  f"{result['both']}, neither {result['neither']}. Paired sign test "
                  f"p = {result['sign_test_p']:.4f}.", ""]
        lines += _kind_table(other)
        other_costs = [item["cost_usd"] for item in other]
        other_latency = percentiles([item["latency_s"] for item in other])
        lines += ["", f"Second set: cost per success {_num(cost_per_success(other))} USD, "
                      f"latency p50 / p95 {_num(other_latency[50], 2)} / "
                      f"{_num(other_latency[95], 2)} s, total cost {_num(sum(other_costs))} USD."]
    return "\n".join(lines) + "\n"


def load_rows(path: str | Path) -> list[dict]:
    """Read a results.jsonl file."""
    with Path(path).open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def seed_snapshots(scenarios: list[dict], ids: set[str]) -> dict[str, dict]:
    """Rebuild the seed snapshot of every scenario that appears in the results."""
    snapshots: dict[str, dict] = {}
    with TemporaryDirectory(prefix="stayline-report-") as temp_dir:
        for scenario in scenarios:
            if scenario["id"] in ids:
                db_path = Path(temp_dir) / f"{scenario['id']}.sqlite"
                reset_from_seed(str(REPO_ROOT / scenario["seed"]), str(db_path))
                snapshots[scenario["id"]] = snapshot(str(db_path))
    return snapshots


def main(argv: list[str] | None = None) -> int:
    """Read results and scenarios, then write the markdown summary."""
    parser = argparse.ArgumentParser(description="Summarise Stayline evaluation results.")
    parser.add_argument("--results", required=True)
    parser.add_argument("--scenarios", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--compare")
    args = parser.parse_args(argv)
    try:
        rows = load_rows(args.results)
        scenarios = load_rows(args.scenarios)
        other = load_rows(args.compare) if args.compare else None
    except (OSError, ValueError) as error:
        print(f"Could not read inputs: {error}", file=sys.stderr)
        return 2
    seeds = seed_snapshots(scenarios, {item["id"] for item in rows})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, scenarios, seeds, other), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
