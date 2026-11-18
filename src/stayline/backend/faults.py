"""Injected tool failures for the recovery bonus, read from STAYLINE_FAULT."""

import functools
import json
import os
from contextlib import closing
from datetime import datetime, timezone
from typing import Callable, Literal

from pydantic import BaseModel, ValidationError

from stayline.backend.db import connect
from stayline.servers.results import tool_error


class Fault(BaseModel):
    """One failure to inject: which tool, how, and how many times."""

    tool: str
    mode: Literal["timeout_after_commit", "rate_limited"]
    times: int = 1


def load_fault() -> Fault | None:
    """Read the injected fault from the environment, or None when absent or invalid."""
    raw = os.environ.get("STAYLINE_FAULT")
    if not raw:
        return None
    try:
        return Fault.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        return None


def should_fire(fault: Fault, tool: str) -> bool:
    """Count firings in the database, so the limit holds across calls and restarts."""
    if tool != fault.tool:
        return False
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        db.execute("CREATE TABLE IF NOT EXISTS fault_log (tool TEXT NOT NULL, fired_at TEXT NOT NULL)")
        with db:
            db.execute("BEGIN IMMEDIATE")
            fired = db.execute(
                "SELECT COUNT(*) FROM fault_log WHERE tool = ?", (tool,)
            ).fetchone()[0]
            if fired >= fault.times:
                return False
            db.execute(
                "INSERT INTO fault_log (tool, fired_at) VALUES (?, ?)",
                (tool, datetime.now(timezone.utc).isoformat()),
            )
            return True


def with_fault(tool: str) -> Callable:
    """Wrap a tool so the configured fault fires on it, leaving its signature intact."""

    def decorate(function: Callable) -> Callable:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            fault = load_fault()
            if fault is None or fault.tool != tool:
                return function(*args, **kwargs)
            if fault.mode == "rate_limited":
                if should_fire(fault, tool):
                    raise tool_error("rate_limited", f"Tool '{tool}' is rate limited", retryable=True)
                return function(*args, **kwargs)
            result = function(*args, **kwargs)
            if should_fire(fault, tool):
                raise tool_error(
                    "timeout", f"Tool '{tool}' timed out", retryable=True, outcome_unknown=True,
                )
            return result

        return wrapper

    return decorate
