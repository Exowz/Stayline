"""Write local JSONL spans and optionally forward them to Phoenix."""

import json
import logging
import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator
from uuid import uuid4

from stayline.agent.llm import LLM, LLMReply
from stayline.servers.results import ToolResult
from stayline.tracing.redact import Redactor


_current: ContextVar["_Span | None"] = ContextVar("stayline_span", default=None)
_logger = logging.getLogger(__name__)


class _WarningExporter:
    """Report a failed batch once without affecting local spans."""

    def __init__(self, inner: Any, warn: Any) -> None:
        self.inner = inner
        self.warn = warn

    def export(self, spans: Any) -> Any:
        """Forward a batch and report export failure."""
        from opentelemetry.sdk.trace.export import SpanExportResult
        try:
            result = self.inner.export(spans)
            if result != SpanExportResult.SUCCESS:
                self.warn("batch export failed")
            return result
        except Exception as error:
            self.warn(error)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        """Close the wrapped exporter."""
        self.inner.shutdown()


class _Span:
    """Hold one span until its context exits."""

    def __init__(self, tracer: "RunTracer", name: str, kind: str, attrs: dict) -> None:
        self.tracer = tracer
        self.name = name
        self.kind = kind
        self.attrs = attrs
        self.span_id = uuid4().hex[:16]
        self.parent_id = _current.get().span_id if _current.get() else None
        self.start = datetime.now(timezone.utc)
        self.tick = perf_counter()
        self.status = "ok"

    def set(self, **attrs: Any) -> None:
        """Add attributes before the span closes."""
        self.attrs.update(attrs)

    def fail(self, message: str) -> None:
        """Mark the span as failed and record the reason."""
        self.status = "error"
        self.attrs["error.message"] = message


class RunTracer:
    """Own one trace file and its optional telemetry exporter."""

    def __init__(self, run_id: str, out_dir: Path, phoenix_endpoint: str | None,
                 redactor: Redactor | None) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_.#-]", "_", run_id)
        self.path = out_dir / f"{safe_id}.jsonl"
        self.file = self.path.open("w", encoding="utf-8")
        self.trace_id = uuid4().hex
        self.redactor = redactor or Redactor()
        self.provider = None
        self.otel = None
        self._warned = False
        self.closed = False
        if phoenix_endpoint:
            try:
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                self.provider = TracerProvider()
                exporter = OTLPSpanExporter(
                    endpoint=f"{phoenix_endpoint.rstrip('/')}/v1/traces", timeout=1,
                )
                self.provider.add_span_processor(BatchSpanProcessor(
                    _WarningExporter(exporter, self._warn)))
                self.otel = self.provider.get_tracer("stayline")
            except Exception as error:
                self._warn(error)
        root_name = re.sub(r"-[0-9a-fA-F]{8}$", "", run_id)
        self._root_context = self.span(root_name, "AGENT")
        self.root = self._root_context.__enter__()

    def _warn(self, error: Exception | str) -> None:
        if not self._warned:
            _logger.warning("Phoenix trace export failed: %s", error)
            self._warned = True

    def _write(self, span: _Span, attributes: dict) -> None:
        end = datetime.now(timezone.utc)
        line = {
            "trace_id": self.trace_id, "span_id": span.span_id,
            "parent_id": span.parent_id, "name": span.name, "kind": span.kind,
            "start": span.start.isoformat(), "end": end.isoformat(),
            "ms": round((perf_counter() - span.tick) * 1000, 3),
            "status": span.status, "attributes": attributes,
        }
        self.file.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
        self.file.flush()

    @contextmanager
    def span(self, name: str, kind: str, **attrs: Any) -> Iterator[_Span]:
        """Open a span nested under the current span."""
        span = _Span(self, name, kind, attrs)
        token = _current.set(span)
        remote_context = None
        remote = None
        if self.otel:
            try:
                remote_context = self.otel.start_as_current_span(name)
                remote = remote_context.__enter__()
                remote.set_attribute("openinference.span.kind", kind)
            except Exception as error:
                self._warn(error)
        try:
            yield span
        except Exception as error:
            span.fail(f"{type(error).__name__}: {error}")
            raise
        finally:
            try:
                attributes = self.redactor.redact(span.attrs)
                self._write(span, attributes)
                if remote is not None:
                    try:
                        for key, value in attributes.items():
                            remote.set_attribute(key, value if isinstance(value, (str, bool, int, float))
                                                 else json.dumps(value, ensure_ascii=False, default=str))
                        if span.status == "error":
                            from opentelemetry.trace import Status, StatusCode
                            remote.set_status(Status(StatusCode.ERROR))
                    except Exception as error:
                        self._warn(error)
            finally:
                if remote_context is not None and remote is not None:
                    try:
                        remote_context.__exit__(None, None, None)
                    except Exception as error:
                        self._warn(error)
                _current.reset(token)

    def close(self) -> Path:
        """Close the root, flush optional export, and return the file path."""
        if not self.closed:
            self.closed = True
            try:
                self._root_context.__exit__(None, None, None)
                if self.provider and not self.provider.force_flush(timeout_millis=1500):
                    self._warn("flush timed out")
            except Exception as error:
                self._warn(error)
            finally:
                if self.provider:
                    try:
                        self.provider.shutdown()
                    except Exception as error:
                        self._warn(error)
                self.file.close()
        return self.path


def start_tracing(run_id: str, out_dir: Path, phoenix_endpoint: str | None,
                  redactor: Redactor | None = None) -> RunTracer:
    """Start a local trace for one run."""
    return RunTracer(run_id, out_dir, phoenix_endpoint, redactor)


class TracedLLM:
    """Record model usage without changing the model reply."""

    def __init__(self, inner: LLM, tracer: RunTracer) -> None:
        self.inner = inner
        self.tracer = tracer

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        """Trace one model completion."""
        with self.tracer.span("complete", "LLM") as span:
            reply = await self.inner.complete(messages, tools)
            usage = reply.usage
            span.set(**{
                "llm.model_name": usage.get("model", ""),
                "llm.token_count.prompt": usage.get("tokens_in", 0),
                "llm.token_count.completion": usage.get("tokens_out", 0),
                "llm.cost_usd": usage.get("cost_usd", 0.0),
            })
            return reply


class TracedHarness:
    """Trace every tool call while forwarding tool metadata."""

    def __init__(self, inner: Any, tracer: RunTracer) -> None:
        self.inner = inner
        self.tracer = tracer

    def tool_specs(self) -> list[dict]:
        """Forward the model-visible tool definitions."""
        return self.inner.tool_specs()

    async def call(self, tool: str, args: dict, run_id: str) -> ToolResult:
        """Record the input, output and failed result code."""
        # Keep values structured so the redactor can see "untrusted" keys.
        with self.tracer.span(tool, "TOOL", **{"input.value": {"tool": tool, "args": args}}) as span:
            result = await self.inner.call(tool, args, run_id)
            span.set(**{"output.value": result.model_dump(mode="json")})
            if not result.ok:
                span.fail(result.error.message if result.error else "Tool call failed")
                if result.error:
                    span.set(**{"error.code": result.error.code})
            return result
