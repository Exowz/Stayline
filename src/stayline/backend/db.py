"""Build the SQLite backend from JSON seeds and read its observable state."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE judicial_reference (
    court_id TEXT NOT NULL,
    judge_role TEXT NOT NULL,
    procedure_type TEXT NOT NULL,
    valid INTEGER NOT NULL CHECK (valid IN (0, 1)),
    note TEXT NOT NULL,
    PRIMARY KEY (court_id, judge_role, procedure_type)
);
CREATE TABLE notices (
    notice_id TEXT PRIMARY KEY,
    court_id TEXT NOT NULL,
    judge_role TEXT NOT NULL,
    procedure_type TEXT NOT NULL,
    case_reference TEXT NOT NULL,
    target_policy_number TEXT,
    target_last_name TEXT,
    target_first_names TEXT,
    target_birth_date TEXT,
    target_birth_place_code TEXT,
    free_text TEXT NOT NULL,
    FOREIGN KEY (court_id, judge_role, procedure_type)
        REFERENCES judicial_reference (court_id, judge_role, procedure_type)
);
CREATE TABLE rules (
    rule_id TEXT NOT NULL,
    version TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    restrictions TEXT NOT NULL,
    PRIMARY KEY (rule_id, version)
);
CREATE TABLE subscribers (
    subscriber_id TEXT PRIMARY KEY,
    last_name TEXT NOT NULL,
    first_names TEXT NOT NULL,
    birth_date TEXT NOT NULL,
    birth_place_code TEXT NOT NULL,
    deceased INTEGER NOT NULL CHECK (deceased IN (0, 1))
);
CREATE TABLE contracts (
    contract_id TEXT PRIMARY KEY,
    policy_number TEXT NOT NULL,
    insurer TEXT NOT NULL,
    subscriber_id TEXT NOT NULL REFERENCES subscribers (subscriber_id),
    status TEXT NOT NULL CHECK (status IN ('active', 'surrendered')),
    value_eur INTEGER NOT NULL,
    advance_eur INTEGER NOT NULL,
    allocation TEXT NOT NULL,
    version INTEGER NOT NULL,
    comment TEXT NOT NULL
);
CREATE TABLE operation_requests (
    request_id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('rachat', 'avance', 'arbitrage')),
    contract_id TEXT NOT NULL REFERENCES contracts (contract_id),
    origin TEXT NOT NULL CHECK (origin IN ('cgp', 'operator')),
    amount_eur INTEGER,
    target_allocation TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'executed', 'unavailable_manual_review')),
    created_at TEXT NOT NULL,
    note TEXT NOT NULL,
    attachments TEXT NOT NULL
);
CREATE TABLE restriction_ledger (
    contract_id TEXT NOT NULL REFERENCES contracts (contract_id),
    restriction TEXT NOT NULL,
    notice_id TEXT NOT NULL REFERENCES notices (notice_id),
    rule_id TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    note TEXT NOT NULL,
    PRIMARY KEY (contract_id, restriction, notice_id),
    FOREIGN KEY (rule_id, rule_version) REFERENCES rules (rule_id, version)
);
CREATE TABLE idempotency_keys (
    key TEXT PRIMARY KEY,
    tool TEXT NOT NULL,
    result_json TEXT NOT NULL
);
"""

PRIMARY_KEYS = {
    "judicial_reference": ("court_id", "judge_role", "procedure_type"),
    "notices": ("notice_id",),
    "rules": ("rule_id", "version"),
    "subscribers": ("subscriber_id",),
    "contracts": ("contract_id",),
    "operation_requests": ("request_id",),
    "restriction_ledger": ("contract_id", "restriction", "notice_id"),
    "idempotency_keys": ("key",),
}

JSON_COLUMNS = {
    "rules": {"restrictions"},
    "contracts": {"allocation"},
    "operation_requests": {"target_allocation", "attachments"},
}


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with named rows and foreign keys enabled."""
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _seed_rows(seed_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load a seed and merge its rows over its parent by primary key."""
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    parent = data.pop("extends", None)
    tables = _seed_rows(seed_path.parent / parent) if parent else {}
    for table, child_rows in data.items():
        keys = PRIMARY_KEYS[table]
        merged = {tuple(row[key] for key in keys): row.copy() for row in tables.get(table, [])}
        for row in child_rows:
            key = tuple(row[column] for column in keys)
            merged[key] = {**merged.get(key, {}), **row}
        tables[table] = list(merged.values())
    return tables


def _insert_rows(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    """Insert seed rows, encoding structured fields as JSON text."""
    for row in rows:
        fields = tuple(row)
        values = [
            json.dumps(row[field], ensure_ascii=False) if field in JSON_COLUMNS.get(table, set())
            and row[field] is not None else row[field]
            for field in fields
        ]
        placeholders = ", ".join("?" for _ in fields)
        connection.execute(
            f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})",
            values,
        )


def reset_from_seed(seed_path: str, db_path: str) -> None:
    """Replace a database file with the contents of a merged JSON seed."""
    tables = _seed_rows(Path(seed_path))
    Path(db_path).unlink(missing_ok=True)
    with closing(connect(db_path)) as connection:
        connection.executescript(SCHEMA)
        with connection:
            for table in PRIMARY_KEYS:
                _insert_rows(connection, table, tables.get(table, []))


def snapshot(db_path: str) -> dict[str, Any]:
    """Return contract state, restriction lineage, and request statuses."""
    with closing(connect(db_path)) as connection:
        contracts = {
            row["contract_id"]: {
                "status": row["status"],
                "value_eur": row["value_eur"],
                "advance_eur": row["advance_eur"],
                "allocation": json.loads(row["allocation"]),
                "restrictions": {},
            }
            for row in connection.execute(
                "SELECT contract_id, status, value_eur, advance_eur, allocation "
                "FROM contracts ORDER BY contract_id"
            )
        }
        for row in connection.execute(
            "SELECT contract_id, restriction, notice_id, rule_id, rule_version "
            "FROM restriction_ledger ORDER BY contract_id, restriction, notice_id"
        ):
            contracts[row["contract_id"]]["restrictions"][row["restriction"]] = (
                f'{row["notice_id"]}|{row["rule_id"]}@{row["rule_version"]}'
            )
        requests = {
            row["request_id"]: row["status"]
            for row in connection.execute(
                "SELECT request_id, status FROM operation_requests ORDER BY request_id"
            )
        }
    return {"contracts": contracts, "requests": requests}
