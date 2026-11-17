"""Insurer contract reads and reversible request status updates over MCP."""

import json
import os
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from stayline.backend.db import connect
from stayline.backend.faults import with_fault
from stayline.backend.rules import authority_is_valid, is_operation_permitted, match_contracts
from stayline.config import Settings
from stayline.servers.results import tool_error


INSURER_ID = Settings().insurer_id
READ = ToolAnnotations(
    readOnlyHint=True, idempotentHint=True, destructiveHint=False, openWorldHint=False
)
WRITE = ToolAnnotations(
    readOnlyHint=False, idempotentHint=True, destructiveHint=False, openWorldHint=False
)
DANGEROUS_WRITE = ToolAnnotations(
    readOnlyHint=False, idempotentHint=True, destructiveHint=True, openWorldHint=False
)
NoticeId = Annotated[str, Field(pattern=r"^N-\d{4}-\d{4}$")]
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
@with_fault("get_contract")
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


def _stored_result(db: sqlite3.Connection, key: str | None) -> dict | None:
    """Return a prior keyed result inside the current transaction."""
    if key is None:
        return None
    row = db.execute(
        "SELECT result_json FROM idempotency_keys WHERE key = ?", (key,)
    ).fetchone()
    return json.loads(row["result_json"]) if row is not None else None


def _save_result(db: sqlite3.Connection, key: str | None, tool: str, result: dict) -> None:
    """Persist a keyed result with its effect."""
    if key is not None:
        db.execute(
            "INSERT INTO idempotency_keys (key, tool, result_json) VALUES (?, ?, ?)",
            (key, tool, json.dumps(result)),
        )


@mcp.tool(annotations=DANGEROUS_WRITE)
@with_fault("apply_seizure")
def apply_seizure(
    notice_id: NoticeId,
    contract_id: ContractId,
    expected_version: int,
    idempotency_key: Annotated[
        str | None, Field(description="Set by the harness for safe retries")
    ] = None,
) -> dict:
    """Apply a valid notice to its matched contract after human approval; return version and restrictions.
    Example: notice_id="N-2020-1234", contract_id="C-1234", expected_version=1. After a timeout the outcome is unknown; read the contract back."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        with db:
            db.execute("BEGIN IMMEDIATE")
            stored = _stored_result(db, idempotency_key)
            if stored is not None:
                return stored

            notice = db.execute(
                "SELECT * FROM notices WHERE notice_id = ?", (notice_id,)
            ).fetchone()
            if notice is None:
                raise tool_error("not_found", f"Notice {notice_id} was not found")
            contract = db.execute(
                "SELECT c.*, s.deceased FROM contracts AS c "
                "JOIN subscribers AS s ON s.subscriber_id = c.subscriber_id "
                "WHERE c.contract_id = ? AND c.insurer = ?",
                (contract_id, INSURER_ID),
            ).fetchone()
            if contract is None:
                raise tool_error("contract_not_found", f"Contract {contract_id} was not found")
            if not authority_is_valid(notice["judge_role"], notice["procedure_type"]):
                raise tool_error("authority_mismatch", "The issuing authority cannot order this procedure")

            target = {
                "policy_number": notice["target_policy_number"],
                "last_name": notice["target_last_name"],
                "first_names": notice["target_first_names"],
                "birth_date": notice["target_birth_date"],
                "birth_place_code": notice["target_birth_place_code"],
            }
            rows = [dict(row) for row in db.execute(
                "SELECT c.contract_id, c.policy_number, c.insurer, s.last_name, "
                "s.first_names, s.birth_date, s.birth_place_code "
                "FROM contracts AS c JOIN subscribers AS s ON s.subscriber_id = c.subscriber_id"
            )]
            match = match_contracts(target, rows, INSURER_ID)
            if match.outcome == "ambiguous_match":
                raise tool_error("ambiguous_match", "The notice target is ambiguous")
            if match.outcome != "match" or len(match.candidates) != 1 or match.candidates[0].contract_id != contract_id:
                raise tool_error("contract_not_found", "The notice does not target this contract")
            if contract["deceased"]:
                raise tool_error(
                    "operation_not_permitted",
                    "The subscriber is deceased; only CPP 706-155 paragraph 1 applies",
                )
            if contract["status"] != "active":
                raise tool_error("operation_not_permitted", f"Contract is {contract['status']}")

            prior = db.execute(
                "SELECT notice_id FROM restriction_ledger WHERE contract_id = ?",
                (contract_id,),
            ).fetchall()
            if any(row["notice_id"] == notice_id for row in prior):
                raise tool_error("duplicate_notice", "This notice is already applied")
            if prior:
                raise tool_error("active_seizure", "Another seizure is already active")
            if expected_version != contract["version"]:
                raise tool_error(
                    "stale_version", f"Current contract version is {contract['version']}",
                    retryable=True,
                )

            rule = db.execute(
                "SELECT rule_id, version, restrictions FROM rules "
                "WHERE rule_id = ? AND valid_from <= ? "
                "ORDER BY valid_from DESC, version DESC LIMIT 1",
                ("CPP-706-155", date.today().isoformat()),
            ).fetchone()
            if rule is None:
                raise tool_error("internal", "No applicable seizure rule was found")
            restrictions = json.loads(rule["restrictions"])
            applied_at = datetime.now(timezone.utc).isoformat()
            for restriction in restrictions:
                db.execute(
                    "INSERT INTO restriction_ledger "
                    "(contract_id, restriction, notice_id, rule_id, rule_version, applied_at, note) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (contract_id, restriction, notice_id, rule["rule_id"], rule["version"], applied_at, ""),
                )
            version = contract["version"] + 1
            db.execute(
                "UPDATE contracts SET version = ? WHERE contract_id = ?", (version, contract_id)
            )
            result = {
                "contract_id": contract_id,
                "version": version,
                "restrictions_written": restrictions,
            }
            _save_result(db, idempotency_key, "apply_seizure", result)
            return result


@mcp.tool(annotations=DANGEROUS_WRITE)
@with_fault("execute_operation")
def execute_operation(
    request_id: RequestId,
    contract_id: ContractId,
    expected_version: int,
    idempotency_key: Annotated[
        str | None, Field(description="Set by the harness for safe retries")
    ] = None,
) -> dict:
    """Execute a permitted pending request after human approval; return its status and version.
    Example: request_id="R-5678", contract_id="C-1234", expected_version=1. After a timeout the outcome is unknown; read the contract back."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        with db:
            db.execute("BEGIN IMMEDIATE")
            stored = _stored_result(db, idempotency_key)
            if stored is not None:
                return stored
            request = db.execute(
                "SELECT * FROM operation_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if request is None:
                raise tool_error("not_found", f"Request {request_id} was not found")
            contract = db.execute(
                "SELECT * FROM contracts WHERE contract_id = ? AND insurer = ?",
                (contract_id, INSURER_ID),
            ).fetchone()
            if contract is None:
                raise tool_error("contract_not_found", f"Contract {contract_id} was not found")
            if request["contract_id"] != contract_id:
                raise tool_error("invalid_argument", "Request belongs to another contract")
            if request["status"] != "pending":
                raise tool_error("conflict", "Request is not pending")
            if contract["status"] != "active":
                raise tool_error("operation_not_permitted", f"Contract is {contract['status']}")
            active = {
                row["restriction"] for row in db.execute(
                    "SELECT restriction FROM restriction_ledger WHERE contract_id = ?",
                    (contract_id,),
                )
            }
            if not is_operation_permitted(request["type"], active):
                raise tool_error("operation_not_permitted", "A restriction is active for this operation")
            if expected_version != contract["version"]:
                raise tool_error(
                    "stale_version", f"Current contract version is {contract['version']}",
                    retryable=True,
                )

            if request["type"] in ("rachat", "avance"):
                amount = request["amount_eur"]
                if amount is None or amount <= 0:
                    raise tool_error("invalid_argument", "Amount must be positive")
                if request["type"] == "rachat":
                    if amount > contract["value_eur"]:
                        raise tool_error("invalid_argument", "Amount exceeds contract value")
                    value = contract["value_eur"] - amount
                    db.execute(
                        "UPDATE contracts SET value_eur = ?, status = ? WHERE contract_id = ?",
                        (value, "surrendered" if value == 0 else "active", contract_id),
                    )
                else:
                    db.execute(
                        "UPDATE contracts SET advance_eur = advance_eur + ? WHERE contract_id = ?",
                        (amount, contract_id),
                    )
            else:
                if request["target_allocation"] is None:
                    raise tool_error("invalid_argument", "Target allocation is required")
                db.execute(
                    "UPDATE contracts SET allocation = ? WHERE contract_id = ?",
                    (request["target_allocation"], contract_id),
                )
            version = contract["version"] + 1
            db.execute(
                "UPDATE contracts SET version = ? WHERE contract_id = ?", (version, contract_id)
            )
            db.execute(
                "UPDATE operation_requests SET status = 'executed' WHERE request_id = ?",
                (request_id,),
            )
            result = {
                "request_id": request_id,
                "status": "executed",
                "contract_id": contract_id,
                "version": version,
            }
            _save_result(db, idempotency_key, "execute_operation", result)
            return result


if __name__ == "__main__":
    mcp.run()
