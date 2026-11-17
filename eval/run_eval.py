"""Run seeded evaluation scenarios and write one result per run."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import asyncio
import json
from tempfile import TemporaryDirectory
from typing import Callable
from uuid import uuid4

from eval.grade import grade
from stayline.agent.llm import LLM
from stayline.agent.run import always_yes, run_task
from stayline.backend.db import reset_from_seed, snapshot
from stayline.config import Settings, load_settings


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {
    "id", "kind", "task", "seed", "expect_state", "forbid_calls", "max_steps",
}
KINDS = {"normal", "ambiguous", "impossible", "adversarial"}
FIELD_TYPES = {
    "id": str, "task": str, "seed": str, "expect_state": dict,
    "forbid_calls": list, "max_steps": int,
}


def load_scenarios(path: str | Path) -> list[dict]:
    """Read JSON lines and validate the required scenario fields."""
    scenarios = []
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                scenario = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"line {line_number}: invalid JSON: {error.msg}") from error
            if not isinstance(scenario, dict):
                raise ValueError(f"line {line_number}: expected a JSON object")
            missing = REQUIRED_FIELDS - scenario.keys()
            if missing:
                raise ValueError(
                    f"line {line_number}: missing required fields: {', '.join(sorted(missing))}"
                )
            for field, expected_type in FIELD_TYPES.items():
                if type(scenario[field]) is not expected_type:
                    raise ValueError(f"line {line_number}: invalid {field}")
            if not isinstance(scenario["kind"], str) or scenario["kind"] not in KINDS:
                raise ValueError(f"line {line_number}: invalid kind: {scenario['kind']}")
            scenarios.append(scenario)
    return scenarios


async def run_scenario(
    scenario: dict, repeat: int, settings: Settings, out_dir: Path,
    llm: LLM | None = None, modules: tuple[str, ...] | None = None,
) -> dict:
    """Run a scenario on an isolated database and grade its final state."""
    result = {
        "id": scenario["id"], "kind": scenario["kind"], "repeat": repeat,
        "model_requested": settings.model, "model_reported": None,
        "passed": False, "reason": "", "state_ok": False, "forbidden": [],
        "in_budget": False, "stop_ok": False, "final_state": None,
        "tools": [], "steps": 0, "model_calls": 0,
        "tokens_in": 0, "tokens_out": 0, "latency_s": 0.0, "cost_usd": 0.0,
        "stop_reason": "error", "approvals": [], "trace_file": None, "error": None,
    }
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="stayline-eval-", dir=out_dir) as temp_dir:
            db_path = Path(temp_dir) / "backend.sqlite"
            memory_path = Path(temp_dir) / "memory.sqlite"
            seed_path = REPO_ROOT / scenario["seed"]
            reset_from_seed(str(seed_path), str(db_path))
            seed_snapshot = snapshot(str(db_path))
            run_id = f"{scenario['id']}#{repeat}-{uuid4().hex[:8]}"
            run_settings = settings.model_copy(update={
                "db_path": str(db_path), "memory_db_path": str(memory_path),
                # The model-call cap follows the scenario's step budget: one call per
                # tool step, plus room for the final action and one reminder.
                "max_model_calls": max(settings.max_model_calls, scenario["max_steps"] + 4),
            })
            record = await run_task(
                scenario["task"], operator_id=scenario.get("operator", "op-default"),
                run_id=run_id, settings=run_settings, max_steps=scenario["max_steps"],
                approver=always_yes, llm=llm, fault=scenario.get("fault"),
                modules=modules,
            )
            calls = record["tool_calls"]
            usage = record["usage"]
            result.update({
                "model_reported": record["model_reported"],
                "tools": [call["tool"] for call in calls],
                "steps": len(calls), "model_calls": record["model_calls"],
                "tokens_in": sum(item.get("tokens_in", 0) for item in usage),
                "tokens_out": sum(item.get("tokens_out", 0) for item in usage),
                "latency_s": record["latency_s"],
                "cost_usd": sum(item.get("cost_usd", 0.0) for item in usage),
                "stop_reason": record["stop_reason"],
                "approvals": record["approvals"], "error": record.get("error"),
            })
            final_state = snapshot(str(db_path))
            result["final_state"] = final_state
            result.update(grade(scenario, seed_snapshot, final_state, record))
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        result.update({
            "passed": False, "reason": f"error: {message}",
            "stop_reason": "error", "error": message,
        })
    return result


async def run_all(
    scenarios: list[dict], repeats: int, settings: Settings, out_dir: Path,
    results_name: str, llm_factory: Callable[[], LLM] | None = None,
    modules: tuple[str, ...] | None = None,
) -> list[dict]:
    """Run scenarios sequentially and flush each JSON result to disk."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with (out_dir / results_name).open("w", encoding="utf-8") as target:
        for scenario in scenarios:
            for repeat in range(repeats):
                llm = llm_factory() if llm_factory is not None else None
                result = await run_scenario(
                    scenario, repeat, settings, out_dir, llm=llm, modules=modules,
                )
                target.write(json.dumps(result, ensure_ascii=False) + "\n")
                target.flush()
                results.append(result)
                status = "PASS" if result["passed"] else "FAIL"
                progress = (
                    f"{result['id']}#{repeat} {status} {result['stop_reason']} "
                    f"{result['steps']} steps {result['latency_s']:.1f}s "
                    f"${result['cost_usd']:.4f}"
                )
                if not result["passed"]:
                    progress += f" {result['reason']}"
                print(progress, file=sys.stderr)
    return results


def main(argv: list[str] | None = None, llm_factory: Callable[[], LLM] | None = None) -> int:
    """Parse CLI flags, run selected scenarios, and print a summary."""
    parser = argparse.ArgumentParser(description="Run Stayline evaluation scenarios.")
    parser.add_argument("--scenarios", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--ids")
    parser.add_argument("--kind", choices=sorted(KINDS))
    parser.add_argument("--results-name", default="results.jsonl")
    parser.add_argument("--justice-module", default="stayline.servers.justice_reference")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        print("--repeats must be at least 1", file=sys.stderr)
        return 2
    overrides = {"model": args.model} if args.model is not None else {}
    settings = load_settings(**overrides)
    if llm_factory is None and not settings.api_key.get_secret_value():
        print("OPENROUTER_API_KEY is required for live evaluation", file=sys.stderr)
        return 2
    try:
        scenarios = load_scenarios(args.scenarios)
    except (OSError, ValueError) as error:
        print(f"Could not load scenarios: {error}", file=sys.stderr)
        return 2
    if args.ids:
        selected_ids = {item.strip() for item in args.ids.split(",")}
        scenarios = [scenario for scenario in scenarios if scenario["id"] in selected_ids]
    if args.kind:
        scenarios = [scenario for scenario in scenarios if scenario["kind"] == args.kind]
    modules = (args.justice_module, "stayline.servers.insurer_contracts")
    results = asyncio.run(run_all(
        scenarios, args.repeats, settings, Path(args.out), args.results_name,
        llm_factory=llm_factory, modules=modules,
    ))
    print(f"passed {sum(result['passed'] for result in results)}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
