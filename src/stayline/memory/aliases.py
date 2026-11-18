"""Operator-confirmed case aliases in a durable, per-operator store.

An alias is a lookup hint, never evidence: current records decide the target.
"""

import re
from contextlib import contextmanager
from typing import Iterator

from langgraph.store.sqlite import SqliteStore


def namespace(operator_id: str) -> tuple[str, str, str]:
    """Return the store namespace that holds one operator's aliases."""
    return ("operators", operator_id, "aliases")


@contextmanager
def open_store(path: str) -> Iterator[SqliteStore]:
    """Open the SQLite-backed store at a file path, creating its tables."""
    with SqliteStore.from_conn_string(path) as store:
        store.setup()
        yield store


def _normal(text: str) -> str:
    """Fold case and collapse spaces, dashes and underscores for comparison."""
    return re.sub(r"[\s_-]+", " ", text.casefold()).strip()


def _said(operator_message: str, *values: str) -> bool:
    """Check that every value appears in the operator's own message."""
    message = _normal(operator_message)
    return all(_normal(value) and _normal(value) in message for value in values)


def remember_alias(
    store, operator_id: str, alias: str, case_reference: str, court: str,
    operator_message: str,
) -> bool:
    """Store an alias only when the operator's own message contains all three values."""
    if not _said(operator_message, alias, case_reference, court):
        return False
    key = alias.casefold().strip()
    current = store.get(namespace(operator_id), key)
    history = list(current.value.get("history", [])) if current else []
    if current and (current.value["case_reference"], current.value["court"]) != (
        case_reference, court
    ):
        history.append({
            "case_reference": current.value["case_reference"],
            "court": current.value["court"],
        })
    store.put(namespace(operator_id), key, {
        "case_reference": case_reference, "court": court, "history": history,
    })
    return True


def recall_aliases(store, operator_id: str) -> dict[str, dict]:
    """Return one operator's aliases by key; another operator's are never included."""
    items = store.search(namespace(operator_id), limit=1000)
    return {item.key: item.value for item in items}


def forget_operator(store, operator_id: str) -> int:
    """Delete one operator's aliases from this store and count them."""
    keys = list(recall_aliases(store, operator_id))
    for key in keys:
        store.delete(namespace(operator_id), key)
    return len(keys)


def load_aliases(store, memory: dict[str, dict[str, dict]]) -> None:
    """Preload aliases for evaluation: operator id, then alias, then value."""
    for operator_id, aliases in memory.items():
        for alias, value in aliases.items():
            store.put(namespace(operator_id), alias.casefold().strip(), {
                "case_reference": value["case_reference"], "court": value["court"],
                "history": list(value.get("history", [])),
            })
