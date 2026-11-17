"""Insurer contract reads and reversible request status updates over MCP."""

import json
import os
import sqlite3
from contextlib import closing
from datetime import date
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from stayline.backend.db import connect
from stayline.backend.rules import match_contracts
from stayline.config import Settings
from stayline.servers.results import tool_error


INSURER_ID = Settings().insurer_id
READ = ToolAnnotations(
    readOnlyHint=True, idempotentHint=True, destructiveHint=False, openWorldHint=False
)
WRITE = ToolAnnotations(
    readOnlyHint=False, idempotentHint=True, destructiveHint=False, openWorldHint=False
)
ContractId = Annotated[str, Field(pattern=r"^C-\d{4}$")]
RequestId = Annotated[str, Field(pattern=r"^R-\d{4}$")]
RequestStatus = Literal["pending", "executed", "unavailable_manual_review"]


class SubscriberIdentity(BaseModel):
    """Identity fields used to find a subscriber's contracts."""

    last_name: str | None = None
    first_names: str | None = None
    birth_date: date | None = None
    birth_place_code: str | None = None


mcp = MCPServer("insurer-contracts")


def _request_fields(row: sqlite3.Row) -> dict:
    """Decode the trusted fields shared by request reads."""
    return {
        "request_id": row["request_id"],
        "type": row["type"],
        "contract_id": row["contract_id"],
        "origin": row["origin"],
        "amount_eur": row["amount_eur"],
        "target_allocation": json.loads(row["target_allocation"])
        if row["target_allocation"] is not None else None,
        "status": row["status"],
        "created_at": row["created_at"],
    }


def _own_contract(db: sqlite3.Connection, contract_id: str) -> bool:
    """Check that a contract exists and belongs to this insurer."""
    row = db.execute(
        "SELECT 1 FROM contracts WHERE contract_id = ? AND insurer = ?",
        (contract_id, INSURER_ID),
    ).fetchone()
    return row is not None


@mcp.tool(annotations=READ)
def find_contracts(
    subscriber_identity: SubscriberIdentity, contract_reference: str | None = None
) -> dict:
    """Find contract candidates by identity and policy number; use for contract lookup.
    Returns an outcome with evidence; example: subscriber_identity={"birth_date":"1970-01-31","birth_place_code":"13055"}, contract_reference="AV-2000-123456"."""
    target = subscriber_identity.model_dump(mode="json")
    target["policy_number"] = contract_reference
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        rows = [dict(row) for row in db.execute(
            "SELECT c.contract_id, c.policy_number, c.insurer, s.last_name, "
            "s.first_names, s.birth_date, s.birth_place_code "
            "FROM contracts AS c JOIN subscribers AS s ON s.subscriber_id = c.subscriber_id"
        )]
    return match_contracts(target, rows, INSURER_ID).model_dump()


@mcp.tool(annotations=READ)
def get_contract(contract_id: ContractId) -> dict:
    """Read a contract and subscriber; use after identifying a contract.
    Returns status, version and untrusted comment; example: contract_id="C-1234"."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        row = db.execute(
            "SELECT c.*, s.last_name, s.first_names, s.birth_date, "
            "s.birth_place_code, s.deceased FROM contracts AS c "
            "JOIN subscribers AS s ON s.subscriber_id = c.subscriber_id "
            "WHERE c.contract_id = ? AND c.insurer = ?",
            (contract_id, INSURER_ID),
        ).fetchone()
    if row is None:
        raise tool_error("contract_not_found", f"Contract {contract_id} was not found")
    return {
        "contract_id": row["contract_id"],
        "policy_number": row["policy_number"],
        "status": row["status"],
        "version": row["version"],
        "value_eur": row["value_eur"],
        "advance_eur": row["advance_eur"],
        "allocation": json.loads(row["allocation"]),
        "subscriber": {
            "subscriber_id": row["subscriber_id"],
            "last_name": row["last_name"],
            "first_names": row["first_names"],
            "birth_date": row["birth_date"],
            "birth_place_code": row["birth_place_code"],
            "deceased": bool(row["deceased"]),
        },
        "untrusted": {"comment": row["comment"]},
    }


@mcp.tool(annotations=READ)
def get_operation_request(request_id: RequestId) -> dict:
    """Read one adviser request; use when its request id is known.
    Returns request fields and untrusted text; example: request_id="R-5678"."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        row = db.execute(
            "SELECT r.* FROM operation_requests AS r "
            "JOIN contracts AS c ON c.contract_id = r.contract_id "
            "WHERE r.request_id = ? AND c.insurer = ?",
            (request_id, INSURER_ID),
        ).fetchone()
    if row is None:
        raise tool_error("not_found", f"Request {request_id} was not found")
    return _request_fields(row) | {
        "untrusted": {
            "note": row["note"],
            "attachments": json.loads(row["attachments"]),
        }
    }


@mcp.tool(annotations=READ)
def find_operation_requests(
    contract_id: ContractId, status: RequestStatus | None = None
) -> list[dict]:
    """List a contract's requests, optionally by status; use to locate a request.
    Returns ordered request fields; example: contract_id="C-1234", status="pending"."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        if not _own_contract(db, contract_id):
            raise tool_error("contract_not_found", f"Contract {contract_id} was not found")
        rows = db.execute(
            "SELECT * FROM operation_requests WHERE contract_id = ? "
            "AND (? IS NULL OR status = ?) ORDER BY created_at, request_id",
            (contract_id, status, status),
        ).fetchall()
    return [_request_fields(row) for row in rows]


@mcp.tool(annotations=READ)
def get_restriction_ledger(contract_id: ContractId) -> list[dict]:
    """Read active contract restrictions; use to check a seizure's lineage.
    Returns ordered ledger rows and any untrusted note; example: contract_id="C-1234"."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        if not _own_contract(db, contract_id):
            raise tool_error("contract_not_found", f"Contract {contract_id} was not found")
        rows = db.execute(
            "SELECT restriction, notice_id, rule_id, rule_version, applied_at, note "
            "FROM restriction_ledger WHERE contract_id = ? ORDER BY restriction",
            (contract_id,),
        ).fetchall()
    result = []
    for row in rows:
        item = {key: row[key] for key in (
            "restriction", "notice_id", "rule_id", "rule_version", "applied_at"
        )}
        if row["note"]:
            item["untrusted"] = {"note": row["note"]}
        result.append(item)
    return result


@mcp.tool(annotations=WRITE)
def set_request_status(
    request_id: RequestId,
    status: Literal["unavailable_manual_review"],
    idempotency_key: Annotated[
        str | None, Field(description="Set by the harness for safe retries")
    ] = None,
) -> dict:
    """Move a pending request to manual review; use when an adviser request is blocked.
    Returns the new status and fixed adviser message; example: request_id="R-5678", status="unavailable_manual_review"."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        with db:
            db.execute("BEGIN IMMEDIATE")
            if idempotency_key is not None:
                stored = db.execute(
                    "SELECT result_json FROM idempotency_keys WHERE key = ?",
                    (idempotency_key,),
                ).fetchone()
                if stored is not None:
                    return json.loads(stored["result_json"])
            row = db.execute(
                "SELECT r.status FROM operation_requests AS r "
                "JOIN contracts AS c ON c.contract_id = r.contract_id "
                "WHERE r.request_id = ? AND c.insurer = ?",
                (request_id, INSURER_ID),
            ).fetchone()
            if row is None:
                raise tool_error("not_found", f"Request {request_id} was not found")
            if row["status"] != "pending":
                raise tool_error("conflict", f"Request {request_id} is not pending")
            result = {
                "request_id": request_id,
                "status": status,
                "adviser_message": "Unavailable. The request has been sent to manual review.",
            }
            db.execute(
                "UPDATE operation_requests SET status = ? WHERE request_id = ?",
                (status, request_id),
            )
            if idempotency_key is not None:
                db.execute(
                    "INSERT INTO idempotency_keys (key, tool, result_json) VALUES (?, ?, ?)",
                    (idempotency_key, "set_request_status", json.dumps(result)),
                )
    return result


if __name__ == "__main__":
    mcp.run()
