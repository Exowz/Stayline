"""Local trace and redaction behavior for scripted agent runs."""

import json
import logging
import re
from pathlib import Path

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from stayline.agent.run import always_yes, run_task
from stayline.backend.db import connect, reset_from_seed
from stayline.config import Settings
from stayline.tracing.redact import Redactor
from stayline.tracing.spans import start_tracing
from tests.fakes import ScriptedLLM
from tests.helpers import TEST_MODULES


ROOT = Path(__file__).resolve().parents[1]
NOTICE_TEXT = "La saisie concerne le contrat indiqué dans le présent avis."


def read_spans(path: Path) -> list[dict]:
    """Read one local trace file."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


async def traced_run(tmp_path, steps, endpoint=None, seed="seeds/base.json"):
    """Run a scripted model against a fresh seed."""
    db_path = tmp_path / "backend.sqlite"
    reset_from_seed(str(ROOT / seed), str(db_path))
    tracer = start_tracing("s01#0-ab12cd34", tmp_path / "traces", endpoint,
                           Redactor.from_db(db_path))
    model = ScriptedLLM(steps)
    try:
        record = await run_task(
            "Apply the notice.", operator_id="operator", run_id="s01#0-ab12cd34",
            settings=Settings(db_path=str(db_path)), max_steps=30,
            approver=always_yes, llm=model, modules=TEST_MODULES, tracer=tracer,
        )
    finally:
        path = tracer.close()
    return record, path


async def test_scripted_run_has_parented_spans_and_matching_totals(tmp_path):
    record, path = await traced_run(tmp_path, [
        {"tool": "get_notice", "args": {"notice_id": "N-2026-0417"}},
        {"tool": "get_contract", "args": {"contract_id": "C-0001"}},
        {"tool": "apply_seizure", "args": {
            "notice_id": "N-2026-0417", "contract_id": "C-0001",
        }},
        {"tool": "finish", "args": {"summary": "Applied."}},
    ])
    spans = read_spans(path)
    roots = [span for span in spans if span["kind"] == "AGENT"]
    llms = [span for span in spans if span["kind"] == "LLM"]
    tools = [span for span in spans if span["kind"] == "TOOL"]
    assert record["stop_reason"] == "done"
    assert len(roots) == 1 and roots[0]["name"] == "s01#0"
    assert len(llms) == record["model_calls"] == 4
    assert len(tools) == len(record["tool_calls"])
    assert [(span["kind"], span["name"]) for span in spans].count(("CHAIN", "approval")) == 1
    assert len({span["trace_id"] for span in spans}) == 1
    ids = {span["span_id"] for span in spans}
    assert all(span["parent_id"] in ids for span in spans if span["kind"] != "AGENT")
    assert roots[0]["parent_id"] is None
    assert roots[0]["attributes"]["stop_reason"] == "done"
    assert sum(span["attributes"]["llm.token_count.prompt"] for span in llms) == sum(
        item["tokens_in"] for item in record["usage"])
    assert sum(span["attributes"]["llm.token_count.completion"] for span in llms) == sum(
        item["tokens_out"] for item in record["usage"])
    assert sum(span["attributes"]["llm.cost_usd"] for span in llms) == sum(
        item["cost_usd"] for item in record["usage"])
    raw = path.read_text(encoding="utf-8")
    assert "Benaïssa" not in raw
    assert re.search("benaissa", raw, re.IGNORECASE) is None
    assert "1978-03-14" not in raw
    assert NOTICE_TEXT not in raw


async def test_failed_tool_span_records_error_code(tmp_path):
    record, path = await traced_run(tmp_path, [
        {"tool": "unknown_tool", "args": {}},
        {"tool": "finish", "args": {"summary": "Stopped."}},
    ])
    failed = [span for span in read_spans(path) if span["kind"] == "TOOL"]
    assert record["stop_reason"] == "done"
    assert len(failed) == 1
    assert failed[0]["status"] == "error"
    assert failed[0]["attributes"]["error.code"] == "invalid_argument"


async def test_unreachable_phoenix_keeps_complete_local_trace(tmp_path):
    record, path = await traced_run(tmp_path, [
        {"tool": "finish", "args": {"summary": "Done."}},
    ], endpoint="http://127.0.0.1:9")
    spans = read_spans(path)
    assert record["stop_reason"] == "done"
    assert [span["kind"] for span in spans].count("AGENT") == 1
    assert [span["kind"] for span in spans].count("LLM") == 1


def test_redactor_stable_folded_nested_and_longest_first():
    redactor = Redactor(persons=["Jean", "Jean Pierre", "Benaïssa"],
                        dates=["1978-03-14"], places=["75112"])
    value = {"people": ["JEAN PIERRE", "benaissa, BENAÏSSA"],
             "birth": {"date": "1978-03-14", "place": "75112"}}
    first = redactor.redact(value)
    assert first["people"][0].startswith("<PERSON_")
    assert "Pierre" not in first["people"][0]
    assert first["people"][1].split(", ")[0] == first["people"][1].split(", ")[1]
    assert first["birth"]["date"] == "<DATE_1>"
    assert first["birth"]["place"] == "<PLACE_1>"
    assert redactor.redact(value) == first


def test_redactor_masks_untrusted_and_notice_text():
    redactor = Redactor(notices=[NOTICE_TEXT])
    assert redactor.redact({"untrusted": "secret", "nested": [
        f"Before {NOTICE_TEXT} after",
    ]}) == {"untrusted": "<UNTRUSTED 6 chars>",
           "nested": [f"Before <UNTRUSTED {len(NOTICE_TEXT)} chars> after"]}


def test_redactor_from_reset_seed_covers_subscriber_and_notice(tmp_path):
    db_path = tmp_path / "backend.sqlite"
    reset_from_seed(str(ROOT / "seeds/base.json"), str(db_path))
    redactor = Redactor.from_db(db_path)
    with connect(str(db_path)) as db:
        notice = db.execute("SELECT free_text FROM notices LIMIT 1").fetchone()[0]
    redacted = redactor.redact(f"Benaïssa BENAISSA 1978-03-14 75112 {notice}")
    assert "Bena" not in redacted
    assert "1978-03-14" not in redacted
    assert "75112" not in redacted
    assert notice not in redacted


def test_phoenix_export_keeps_parentage_and_redacted_attributes(tmp_path, monkeypatch):
    exported = []

    class CollectingExporter(SpanExporter):
        def __init__(self, endpoint, timeout):
            assert endpoint == "http://phoenix/v1/traces"

        def export(self, spans):
            exported.extend(spans)
            return SpanExportResult.SUCCESS

        def shutdown(self):
            pass

    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        CollectingExporter,
    )
    tracer = start_tracing("s01#0-ab12cd34", tmp_path, "http://phoenix",
                           Redactor(persons=["Benaïssa"]))
    with tracer.span("get_contract", "TOOL", **{"output.value": "Benaïssa"}):
        pass
    path = tracer.close()
    local = read_spans(path)
    root = next(span for span in exported if span.name == "s01#0")
    child = next(span for span in exported if span.name == "get_contract")
    assert child.context.trace_id == root.context.trace_id
    assert child.parent.span_id == root.context.span_id
    assert child.attributes["output.value"] == "<PERSON_1>"
    assert local[0]["attributes"]["output.value"] == "<PERSON_1>"


def test_phoenix_export_failure_warns_once(tmp_path, monkeypatch, caplog):
    class FailingExporter(SpanExporter):
        def __init__(self, endpoint, timeout):
            pass

        def export(self, spans):
            return SpanExportResult.FAILURE

        def shutdown(self):
            pass

    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        FailingExporter,
    )
    with caplog.at_level(logging.WARNING):
        tracer = start_tracing("s01#0-ab12cd34", tmp_path, "http://phoenix")
        with tracer.span("first", "LLM"):
            pass
        with tracer.span("second", "LLM"):
            pass
        path = tracer.close()
    assert len(read_spans(path)) == 3
    assert sum("Phoenix trace export failed" in item.message for item in caplog.records) == 1


def test_phoenix_flush_failure_still_closes_local_trace(tmp_path, caplog):
    class BrokenProvider:
        def force_flush(self, timeout_millis):
            raise RuntimeError("flush failed")

        def shutdown(self):
            raise RuntimeError("shutdown failed")

    tracer = start_tracing("s01#0-ab12cd34", tmp_path, None)
    tracer.provider = BrokenProvider()
    with caplog.at_level(logging.WARNING):
        path = tracer.close()
    assert len(read_spans(path)) == 1
    assert tracer.file.closed
    assert sum("Phoenix trace export failed" in item.message for item in caplog.records) == 1


async def test_untrusted_tool_text_never_reaches_the_trace(tmp_path):
    record, path = await traced_run(tmp_path, [
        {"tool": "get_contract", "args": {"contract_id": "C-0001"}},
        {"tool": "finish", "args": {"summary": "Read."}},
    ], seed="seeds/adv_contract_comment.json")
    raw = path.read_text(encoding="utf-8")
    assert "seizure lifted by court order" not in raw
    assert "<UNTRUSTED" in raw
