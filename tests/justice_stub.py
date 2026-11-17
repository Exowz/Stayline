"""Stand-in justice server used until the real server is merged."""

import json
import os
from contextlib import closing
from datetime import date

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from stayline.backend.db import connect
from stayline.servers.results import tool_error


mcp = MCPServer("justice-reference")
READ = ToolAnnotations(
    readOnlyHint=True, idempotentHint=True, destructiveHint=False, openWorldHint=False
)


@mcp.tool(annotations=READ)
def get_notice(notice_id: str) -> dict:
    """Read a court notice by its identifier."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        row = db.execute("SELECT * FROM notices WHERE notice_id = ?", (notice_id,)).fetchone()
    if row is None:
        raise tool_error("not_found", f"Notice {notice_id} was not found")
    return {
        "notice_id": row["notice_id"], "court_id": row["court_id"],
        "judge_role": row["judge_role"], "procedure_type": row["procedure_type"],
        "case_reference": row["case_reference"],
        "target": {
            "policy_number": row["target_policy_number"],
            "last_name": row["target_last_name"],
            "first_names": row["target_first_names"],
            "birth_date": row["target_birth_date"],
            "birth_place_code": row["target_birth_place_code"],
        },
        "untrusted": {"free_text": row["free_text"]},
    }


@mcp.tool(annotations=READ)
def find_notices(case_reference: str, court_id: str | None = None) -> list[dict]:
    """Find notices by case reference and optional court."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        rows = db.execute(
            "SELECT notice_id, court_id, case_reference, judge_role, procedure_type "
            "FROM notices WHERE case_reference = ? AND (? IS NULL OR court_id = ?) "
            "ORDER BY notice_id", (case_reference, court_id, court_id),
        ).fetchall()
    return [dict(row) for row in rows]


@mcp.tool(annotations=READ)
def resolve_issuing_authority(
    court_id: str, judge_role: str, procedure_type: str
) -> dict:
    """Check an issuing authority against the reference table."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        court = db.execute(
            "SELECT 1 FROM judicial_reference WHERE court_id = ? LIMIT 1", (court_id,)
        ).fetchone()
        row = db.execute(
            "SELECT valid, note FROM judicial_reference WHERE court_id = ? "
            "AND judge_role = ? AND procedure_type = ?",
            (court_id, judge_role, procedure_type),
        ).fetchone()
    if court is None:
        raise tool_error("not_found", f"Court {court_id} was not found")
    result = {
        "court_id": court_id, "judge_role": judge_role,
        "procedure_type": procedure_type, "valid": bool(row["valid"]) if row else False,
        "basis": "CPP 706-153",
    }
    if row and row["note"]:
        result["untrusted"] = {"note": row["note"]}
    return result


@mcp.tool(annotations=READ)
def get_rule(rule_id: str, as_of_date: date) -> dict:
    """Read the latest rule version valid on the given date."""
    with closing(connect(os.environ["STAYLINE_DB"])) as db:
        row = db.execute(
            "SELECT rule_id, version, valid_from, restrictions FROM rules "
            "WHERE rule_id = ? AND valid_from <= ? "
            "ORDER BY valid_from DESC, version DESC LIMIT 1",
            (rule_id, as_of_date.isoformat()),
        ).fetchone()
    if row is None:
        raise tool_error("not_found", f"Rule {rule_id} was not found")
    return {
        "rule_id": row["rule_id"], "version": row["version"],
        "valid_from": row["valid_from"],
        "restrictions": json.loads(row["restrictions"]),
    }


if __name__ == "__main__":
    mcp.run()
