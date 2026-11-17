"""Serve local runs, approvals, backend state, and UI assets."""

import asyncio
import json
import os
import re
import secrets
from contextlib import asynccontextmanager, closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from stayline.agent.llm import LLM, OpenRouterLLM
from stayline.agent.run import run_task
from stayline.backend.db import connect, reset_from_seed, snapshot
from stayline.config import Settings, load_settings


REPO_ROOT = Path(__file__).resolve().parents[3]


class ResetBody(BaseModel):
    """Name a seed within the configured seed directory."""

    seed: str


class RunBody(BaseModel):
    """Describe a local agent run."""

    task: str
    operator_id: str = "op-default"
    max_steps: int = 14


class DecisionBody(BaseModel):
    """Approve or reject a pending guarded write."""

    approve: bool
    reason: str = ""


@dataclass
class RunState:
    """Hold one run's stream and approval wait point."""

    events: list[dict] = field(default_factory=list)
    queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)
    pending: asyncio.Future[dict] | None = None
    task: asyncio.Task | None = None

    def emit(self, event: dict) -> None:
        """Record an event and wake connected streams."""
        self.events.append(event)
        self.queue.put_nowait(event)


def _public_event(event: dict) -> dict:
    """Map runner events to the UI's public fields."""
    kind = event["type"]
    if kind == "model":
        return {key: event.get(key) for key in (
            "type", "model", "tokens_in", "tokens_out", "cost_usd", "ms",
        )}
    if kind == "tool":
        return {key: event.get(key) for key in (
            "type", "tool", "args", "ok", "error_code", "ms",
        )}
    if kind == "approval_needed":
        return {"type": kind, "preview": event["preview"]}
    if kind == "approval_decided":
        decision = event["decision"]
        return {"type": kind, "approve": bool(decision.get("approve")),
                "reason": decision.get("reason", "")}
    record = event["record"]
    usage = record.get("usage", [])
    return {
        "type": "finished", "stop_reason": record["stop_reason"],
        "steps": len(record.get("tool_calls", [])),
        "model_calls": record.get("model_calls", 0),
        "tokens_in": sum(item.get("tokens_in", 0) for item in usage),
        "tokens_out": sum(item.get("tokens_out", 0) for item in usage),
        "cost_usd": sum(item.get("cost_usd", 0.0) for item in usage),
        "latency_s": record.get("latency_s", 0.0),
        "answer": record.get("answer"),
    }


def create_app(
    settings: Settings | None = None,
    llm_factory: Callable[[], LLM] | None = None,
    modules: tuple[str, ...] | None = None,
    seeds_dir: Path = REPO_ROOT / "seeds",
    ui_dist: Path = REPO_ROOT / "ui" / "dist",
    eval_dir: Path = REPO_ROOT / "eval",
) -> FastAPI:
    """Build an isolated UI service with one active backend run."""
    settings = settings or load_settings()
    if not settings.db_path:
        settings = settings.model_copy(update={
            "db_path": str(REPO_ROOT / "stayline-demo.sqlite"),
        })
    if llm_factory is None:
        llm_factory = lambda: OpenRouterLLM(settings)
    runs: dict[str, RunState] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """Cancel a running task when the server stops."""
        try:
            yield
        finally:
            for state in runs.values():
                if state.task is not None and not state.task.done():
                    state.task.cancel()
                    await asyncio.gather(state.task, return_exceptions=True)

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    def active() -> bool:
        """Report whether the backend is owned by a live run."""
        return any(state.task is not None and not state.task.done()
                   for state in runs.values())

    def seed_names() -> list[str]:
        """List usable JSON seed files in name order."""
        return sorted(path.name for path in seeds_dir.glob("*.json") if path.is_file())

    def get_run(run_id: str) -> RunState:
        """Find an existing run or return a route error."""
        state = runs.get(run_id)
        if state is None:
            raise HTTPException(404, "Unknown run")
        return state

    @app.get("/api/seeds")
    def list_seeds() -> list[str]:
        """List the available seed names."""
        return seed_names()

    @app.post("/api/reset")
    def reset(body: ResetBody) -> dict:
        """Restore one selected seed when no run owns the backend."""
        if active():
            raise HTTPException(409, "A run is active")
        if body.seed not in seed_names():
            raise HTTPException(404, "Unknown seed")
        reset_from_seed(str(seeds_dir / body.seed), settings.db_path)
        return snapshot(settings.db_path)

    @app.post("/api/runs")
    async def start_run(body: RunBody) -> dict[str, str]:
        """Start an agent run and return its short public id."""
        if active():
            raise HTTPException(409, "A run is active")
        run_id = f"run-{secrets.token_hex(4)}"
        state = RunState()
        runs[run_id] = state

        async def approver(preview: dict) -> dict:
            """Wait for one operator decision at this approval pause."""
            state.pending = asyncio.get_running_loop().create_future()
            try:
                return await state.pending
            finally:
                state.pending = None

        async def execute() -> None:
            """Own the checkpointer and finish the public stream."""
            try:
                async with AsyncSqliteSaver.from_conn_string(
                    settings.checkpoint_db_path
                ) as saver:
                    await run_task(
                        body.task, operator_id=body.operator_id, run_id=run_id,
                        settings=settings, max_steps=body.max_steps,
                        approver=approver, llm=llm_factory(),
                        modules=modules, checkpointer=saver,
                        on_event=lambda event: state.emit(_public_event(event)),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                state.emit({
                    "type": "finished", "stop_reason": "error", "steps": 0,
                    "model_calls": 0, "tokens_in": 0, "tokens_out": 0,
                    "cost_usd": 0.0, "latency_s": 0.0, "answer": None,
                })
            finally:
                if not state.events or state.events[-1]["type"] != "finished":
                    state.emit({
                        "type": "finished", "stop_reason": "error", "steps": 0,
                        "model_calls": 0, "tokens_in": 0, "tokens_out": 0,
                        "cost_usd": 0.0, "latency_s": 0.0, "answer": None,
                    })

        state.task = asyncio.create_task(execute())
        return {"run_id": run_id}

    @app.get("/api/runs/{run_id}/events")
    async def stream_events(run_id: str) -> StreamingResponse:
        """Replay and stream one run's events through completion."""
        state = get_run(run_id)

        async def stream():
            """Yield each event once, including the final event."""
            index = 0
            while True:
                while index < len(state.events):
                    event = state.events[index]
                    index += 1
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if event["type"] == "finished":
                        return
                await state.queue.get()

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/runs/{run_id}/decision")
    async def decide(run_id: str, body: DecisionBody) -> dict:
        """Resolve the current approval exactly once."""
        state = get_run(run_id)
        if state.pending is None or state.pending.done():
            raise HTTPException(409, "No approval is pending")
        state.pending.set_result(body.model_dump())
        return {"ok": True}

    @app.get("/api/ledger")
    def ledger() -> dict:
        """Return restriction lineage and request status counts."""
        with closing(connect(settings.db_path)) as db:
            rows = [dict(row) for row in db.execute(
                "SELECT contract_id, restriction, notice_id, rule_id, "
                "rule_version, applied_at FROM restriction_ledger "
                "ORDER BY contract_id, restriction"
            )]
            statuses = {row["status"]: row["count"] for row in db.execute(
                "SELECT status, COUNT(*) AS count FROM operation_requests GROUP BY status"
            )}
        return {
            "restricted_contracts": sorted({row["contract_id"] for row in rows}),
            "operations": {
                "blocked": statuses.get("unavailable_manual_review", 0),
                "permitted": statuses.get("executed", 0),
                "pending": statuses.get("pending", 0),
            },
            "rows": rows,
        }

    @app.get("/api/results")
    def results(name: str = "results.jsonl") -> list[dict]:
        """Read evaluation records from a named JSONL file."""
        if re.fullmatch(r"[A-Za-z0-9_.-]+\.jsonl", name) is None:
            raise HTTPException(400, "Invalid results name")
        path = eval_dir / name
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    if ui_dist.is_dir():
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")
    return app


_justice_module = os.getenv("STAYLINE_JUSTICE_MODULE")
app = create_app(modules=(
    _justice_module, "stayline.servers.insurer_contracts",
) if _justice_module else None)
