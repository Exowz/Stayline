"""Run one guarded agent task and return a structured record."""

from time import perf_counter
from typing import Awaitable, Callable

from langgraph.types import Command

from stayline.agent.graph import build_graph
from stayline.agent.harness import Harness
from stayline.agent.llm import LLM, OpenRouterLLM
from stayline.agent.state import initial_state
from stayline.config import Settings
from stayline.tracing.spans import RunTracer, TracedHarness, TracedLLM


async def always_yes(preview: dict) -> dict:
    """Approve a guarded write for evaluation runs."""
    return {"approve": True, "reason": "eval"}


async def run_task(
    task: str, *, operator_id: str, run_id: str, settings: Settings,
    max_steps: int, approver: Callable[[dict], Awaitable[dict]],
    llm: LLM | None = None, store=None, fault: dict | None = None,
    on_event: Callable[[dict], None] | None = None, checkpointer=None,
    modules: tuple[str, ...] | None = None,
    tracer: RunTracer | None = None,
) -> dict:
    """Run a task through all approvals and collect its observable record."""
    started = perf_counter()
    record = {
        "run_id": run_id, "stop_reason": "error", "answer": None,
        "tool_calls": [], "model_calls": 0, "usage": [], "approvals": [],
        "latency_s": 0.0, "model_reported": None,
    }
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 4 * (max_steps + settings.max_model_calls) + 10,
    }
    graph = None

    def emit(event: dict) -> None:
        if on_event is not None:
            on_event(event)

    def collect(out: dict) -> None:
        old_tools = len(record["tool_calls"])
        old_usage = len(record["usage"])
        record.update({
            "tool_calls": out.get("tool_calls", record["tool_calls"]),
            "model_calls": out.get("model_calls", record["model_calls"]),
            "usage": out.get("usage", record["usage"]),
            "approvals": out.get("approvals", record["approvals"]),
            "answer": out.get("answer", record["answer"]),
        })
        for entry in record["tool_calls"][old_tools:]:
            emit({"type": "tool", **entry})
        for entry in record["usage"][old_usage:]:
            emit({"type": "model", **entry})

    try:
        harness_args = {"fault": fault}
        if modules is not None:
            harness_args["modules"] = modules
        async with Harness(settings, **harness_args) as harness:
            model = llm or OpenRouterLLM(settings)
            if tracer is not None:
                harness = TracedHarness(harness, tracer)
                model = TracedLLM(model, tracer)
            graph = build_graph(harness, model, store, checkpointer)
            out = await graph.ainvoke(initial_state(
                task, operator_id, run_id, max_steps, settings.max_model_calls
            ), config)
            collect(out)
            while out.get("__interrupt__"):
                preview = out["__interrupt__"][0].value
                emit({"type": "approval_needed", "preview": preview})
                if tracer is None:
                    decision = await approver(preview)
                else:
                    with tracer.span("approval", "CHAIN", tool=preview["tool"]) as span:
                        decision = await approver(preview)
                        span.set(approve=bool(decision.get("approve")))
                emit({"type": "approval_decided", "preview": preview, "decision": decision})
                out = await graph.ainvoke(Command(resume=decision), config)
                collect(out)
            record["stop_reason"] = out.get("stop_reason") or "done"
    except Exception as error:
        if graph is not None:
            try:
                checkpoint = await graph.aget_state(config)
                if checkpoint.values:
                    collect(checkpoint.values)
            except Exception:
                pass
        record["stop_reason"] = "error"
        record["error"] = f"{type(error).__name__}: {error}"
    record["latency_s"] = round(perf_counter() - started, 6)
    record["model_reported"] = (
        record["usage"][-1].get("model") if record["usage"] else None
    )
    try:
        emit({"type": "finished", "record": record})
    except Exception as error:
        record["stop_reason"] = "error"
        record["error"] = f"{type(error).__name__}: {error}"
    if tracer is not None:
        tracer.root.set(
            stop_reason=record["stop_reason"], model_reported=record["model_reported"],
            tokens_in=sum(item.get("tokens_in", 0) for item in record["usage"]),
            tokens_out=sum(item.get("tokens_out", 0) for item in record["usage"]),
            cost_usd=sum(item.get("cost_usd", 0.0) for item in record["usage"]),
            latency_s=record["latency_s"],
        )
    return record
