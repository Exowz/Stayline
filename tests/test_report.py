"""Course and domain metrics computed from hand-made result rows."""

import json
from pathlib import Path

import pytest

from eval.report import (
    compare, cost_per_success, domain_metrics, main, pass_hat_k, pass_at_k, per_kind,
    percentiles, render, sign_test, top_share, wilson,
)


FIVE = {name: "N-1|CPP-706-155@2026" for name in (
    "rachat", "renonciation", "nantissement", "acceptation_benefice", "avance",
)}


def snap(c1=None, c2=None, requests=None):
    """Build a small snapshot with two contracts and optional restrictions."""
    def contract(restrictions):
        return {"status": "active", "value_eur": 100, "advance_eur": 0,
                "allocation": {"a": 1}, "restrictions": dict(restrictions or {})}
    return {"contracts": {"C-0001": contract(c1), "C-0002": contract(c2)},
            "requests": dict(requests or {"R-0001": "pending"})}


def row(sid, repeat, passed, kind="normal", cost=0.01, latency=1.0, final=None, approvals=None):
    return {"id": sid, "kind": kind, "repeat": repeat, "passed": passed, "cost_usd": cost,
            "latency_s": latency, "tokens_in": 100, "tokens_out": 20,
            "final_state": final, "approvals": approvals or [], "reason": "ok" if passed else "x",
            "stop_reason": "done", "model_reported": "m"}


def scenario(sid, kind="normal", expect=None):
    return {"id": sid, "kind": kind, "expect_state": expect or {}}


def test_wilson_matches_the_known_interval():
    low, high = wilson(8, 10)
    assert round(low, 2) == 0.49 and round(high, 2) == 0.94


def test_wilson_edges():
    assert wilson(0, 0) == (0.0, 1.0)
    low, high = wilson(10, 10)
    assert high == 1.0 and 0.7 < low < 0.75
    assert wilson(0, 10)[0] == 0.0


def test_pass_hat_k_needs_every_repeat_and_pass_at_k_any():
    rows = [row("a", 0, True), row("a", 1, True), row("a", 2, True),
            row("b", 0, True), row("b", 1, False), row("b", 2, True)]
    assert pass_hat_k(rows) == 0.5
    assert pass_at_k(rows) == 1.0
    assert pass_hat_k([]) == 0.0


def test_cost_per_success_divides_all_cost_by_passed_runs():
    rows = [row("a", 0, True, cost=0.02), row("b", 0, False, cost=0.04)]
    assert cost_per_success(rows) == pytest.approx(0.06)
    assert cost_per_success([row("a", 0, False)]) is None


def test_percentiles_interpolate_and_handle_empty():
    values = [1, 2, 3, 4, 100]
    assert percentiles(values, (50, 95)) == {50: 3, 95: pytest.approx(80.8)}
    assert percentiles([], (50,)) == {50: None}


def test_top_share_of_the_bill():
    values = [1] * 19 + [81]
    assert top_share(values, 0.05) == pytest.approx(0.81)
    assert top_share([], 0.05) is None


def test_sign_test_is_two_sided_exact():
    assert sign_test(5, 0) == 0.0625
    assert sign_test(0, 0) == 1.0
    assert sign_test(3, 3) == 1.0
    assert sign_test(8, 2) == pytest.approx(0.109375)


def test_per_kind_counts_scenarios_runs_and_interval():
    rows = [row("a", 0, True), row("a", 1, True), row("b", 0, True), row("b", 1, False),
            row("c", 0, False, kind="impossible"), row("c", 1, False, kind="impossible")]
    by_kind = {item["kind"]: item for item in per_kind(rows)}
    normal = by_kind["normal"]
    assert (normal["scenarios"], normal["runs"], normal["passed"]) == (2, 4, 3)
    assert normal["pass_rate"] == 0.75
    assert normal["pass_hat_k"] == 0.5 and normal["pass_at_k"] == 1.0
    assert normal["ci_low"] < 0.75 < normal["ci_high"]
    assert by_kind["impossible"]["pass_rate"] == 0.0


def test_under_blocking_is_a_forbidden_operation_executed():
    scenarios = [scenario("s", expect={"requests": {"R-0001": "unavailable_manual_review"}})]
    seeds = {"s": snap(FIVE)}
    rows = [row("s", 0, False, final=snap(FIVE, requests={"R-0001": "executed"}))]
    metrics = domain_metrics(rows, scenarios, seeds)
    assert metrics["under_blocking"] == 1 and metrics["over_blocking"] == 0


def test_under_blocking_includes_a_missing_expected_restriction():
    scenarios = [scenario("s", expect={"contracts": {"C-0001": {"restrictions": FIVE}}})]
    seeds = {"s": snap()}
    partial = {key: value for key, value in FIVE.items() if key != "avance"}
    metrics = domain_metrics([row("s", 0, False, final=snap(partial))], scenarios, seeds)
    assert metrics["under_blocking"] == 1


def test_over_blocking_is_a_permitted_operation_refused():
    scenarios = [scenario("s", expect={"requests": {"R-0001": "executed"}})]
    rows = [row("s", 0, False, final=snap(requests={"R-0001": "unavailable_manual_review"}))]
    metrics = domain_metrics(rows, scenarios, {"s": snap()})
    assert metrics["over_blocking"] == 1 and metrics["under_blocking"] == 0


def test_over_blocking_includes_an_extra_restriction_and_wrong_contract_change():
    scenarios = [scenario("s", expect={"contracts": {"C-0001": {"restrictions": FIVE}}})]
    final = snap(FIVE, c2={"rachat": "N-1|CPP-706-155@2026"})
    metrics = domain_metrics([row("s", 0, False, final=final)], scenarios, {"s": snap()})
    assert metrics["over_blocking"] == 1
    assert metrics["wrong_contract_changes"] == 1


def test_a_correct_run_is_clean_and_its_lineage_is_complete():
    scenarios = [scenario("s", expect={"contracts": {"C-0001": {"restrictions": FIVE}}})]
    metrics = domain_metrics([row("s", 0, True, final=snap(FIVE))], scenarios, {"s": snap()})
    assert (metrics["under_blocking"], metrics["over_blocking"],
            metrics["wrong_contract_changes"]) == (0, 0, 0)
    assert metrics["lineage_completeness"] == 1.0


def test_lineage_completeness_counts_restrictions_missing_a_source():
    scenarios = [scenario("s")]
    broken = {"rachat": "N-1|CPP-706-155@2026", "avance": "|CPP-706-155@2026",
              "nantissement": "N-1|@2026", "renonciation": "N-1|CPP-706-155@"}
    metrics = domain_metrics([row("s", 0, False, final=snap(broken))], scenarios, {"s": snap()})
    assert metrics["lineage_completeness"] == 0.25


def test_lineage_completeness_is_none_without_restrictions():
    metrics = domain_metrics([row("s", 0, True, final=snap())], [scenario("s")], {"s": snap()})
    assert metrics["lineage_completeness"] is None


def preview(contract_id):
    return {"preview": {"contract": {"contract_id": contract_id}}, "decision": {"approve": True}}


def test_previews_on_the_expected_contract():
    scenarios = [scenario("s", expect={"contracts": {"C-0001": {"restrictions": FIVE}}})]
    approvals = [preview("C-0001"), preview("C-0002")]
    metrics = domain_metrics(
        [row("s", 0, False, final=snap(FIVE), approvals=approvals)], scenarios, {"s": snap()},
    )
    assert metrics["previews_on_expected_contract"] == 0.5
    assert domain_metrics([row("s", 0, True, final=snap())], [scenario("s")],
                          {"s": snap()})["previews_on_expected_contract"] is None


def test_rows_without_a_final_state_are_counted_apart():
    metrics = domain_metrics([row("s", 0, False, final=None)], [scenario("s")], {"s": snap()})
    assert metrics["runs_without_state"] == 1 and metrics["under_blocking"] == 0


def test_compare_pairs_scenarios_on_all_repeat_results():
    a = [row("x", 0, True), row("y", 0, True), row("z", 0, True, kind="impossible")]
    b = [row("x", 0, True), row("y", 0, False), row("z", 0, False, kind="impossible")]
    result = compare(a, b)
    assert result["only_a"] == 2 and result["only_b"] == 0 and result["both"] == 1
    assert result["sign_test_p"] == 0.5
    assert result["a"]["overall"]["pass_rate"] == 1.0 and result["b"]["overall"]["pass_rate"] == pytest.approx(1 / 3)


def test_render_contains_the_tables_and_failed_runs():
    rows = [row("s", 0, True, cost=0.01), row("t", 0, False, kind="impossible", cost=0.03)]
    rows[1]["reason"] = "state: contracts.C-0001 differs"
    scenarios = [scenario("s"), scenario("t", kind="impossible")]
    seeds = {"s": snap(), "t": snap()}
    for item in rows:
        item["final_state"] = snap()
    text = render(rows, scenarios, seeds)
    for needle in ("## Pass rate by kind", "## Cost and latency", "## Domain metrics",
                   "## Failed runs", "t#0", "state: contracts.C-0001 differs", "Wilson"):
        assert needle in text


def test_cli_writes_the_summary_from_a_results_file(tmp_path):
    root = Path(__file__).resolve().parents[1]
    results = tmp_path / "results.jsonl"
    rows = [row("s05", 0, True, final=None)]
    results.write_text("\n".join(json.dumps(item) for item in rows) + "\n", encoding="utf-8")
    out = tmp_path / "summary.md"
    code = main(["--results", str(results), "--scenarios", str(root / "eval/scenarios.jsonl"),
                 "--out", str(out)])
    assert code == 0 and "## Pass rate by kind" in out.read_text(encoding="utf-8")
