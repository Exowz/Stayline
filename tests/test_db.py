"""Tests for the seeded SQLite backend and observable snapshot."""

import shutil
from contextlib import closing
from pathlib import Path

import pytest

from stayline.backend.db import connect, reset_from_seed, snapshot


BASE_SEED = Path(__file__).resolve().parents[1] / "seeds" / "base.json"


def test_reset_gives_seed_state(tmp_path: Path) -> None:
    db = str(tmp_path / "s.sqlite")
    reset_from_seed(str(BASE_SEED), db)
    snap = snapshot(db)
    assert snap["contracts"]["C-0001"] == {
        "status": "active",
        "value_eur": 84000,
        "advance_eur": 0,
        "allocation": {"fonds_euro": 60, "uc_actions": 40},
        "restrictions": {},
    }
    assert snap["requests"]["R-0001"] == "pending"
    assert snap["contracts"]["C-0006"]["status"] == "surrendered"


def test_reset_is_repeatable(tmp_path: Path) -> None:
    db = str(tmp_path / "s.sqlite")
    reset_from_seed(str(BASE_SEED), db)
    first = snapshot(db)
    with closing(connect(db)) as connection:
        with connection:
            connection.execute("UPDATE contracts SET value_eur = 1")
    reset_from_seed(str(BASE_SEED), db)
    assert snapshot(db) == first


def test_extends_overrides_by_key(tmp_path: Path) -> None:
    db = str(tmp_path / "s.sqlite")
    shutil.copyfile(BASE_SEED, tmp_path / "base.json")
    child = tmp_path / "child.json"
    child.write_text(
        '{"extends": "base.json", "contracts": '
        '[{"contract_id": "C-0001", "status": "surrendered"}]}',
        encoding="utf-8",
    )
    reset_from_seed(str(child), db)
    contract = snapshot(db)["contracts"]["C-0001"]
    assert contract["status"] == "surrendered"
    assert contract["value_eur"] == 84000
    assert contract["allocation"] == {"fonds_euro": 60, "uc_actions": 40}


def test_extends_requires_full_new_rows(tmp_path: Path) -> None:
    shutil.copyfile(BASE_SEED, tmp_path / "base.json")
    child = tmp_path / "child.json"
    child.write_text(
        '{"extends": "base.json", "contracts": [{"contract_id": "C-0008"}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="full row"):
        reset_from_seed(str(child), str(tmp_path / "s.sqlite"))


def test_snapshot_shows_lineage(tmp_path: Path) -> None:
    db = str(tmp_path / "s.sqlite")
    reset_from_seed(str(BASE_SEED), db)
    with closing(connect(db)) as connection:
        with connection:
            connection.execute(
                "INSERT INTO restriction_ledger "
                "(contract_id, restriction, notice_id, rule_id, rule_version, applied_at, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "C-0001", "rachat", "N-2026-0417", "CPP-706-155",
                    "2026", "2026-11-17", "",
                ),
            )
    assert snapshot(db)["contracts"]["C-0001"]["restrictions"] == {
        "rachat": "N-2026-0417|CPP-706-155@2026"
    }


def test_base_cast_ids_and_other_insurer_exist(tmp_path: Path) -> None:
    db = str(tmp_path / "s.sqlite")
    reset_from_seed(str(BASE_SEED), db)
    with closing(connect(db)) as connection:
        ids_by_table = {
            "subscribers": {row[0] for row in connection.execute("SELECT subscriber_id FROM subscribers")},
            "contracts": {row[0] for row in connection.execute("SELECT contract_id FROM contracts")},
            "notices": {row[0] for row in connection.execute("SELECT notice_id FROM notices")},
            "operation_requests": {
                row[0] for row in connection.execute("SELECT request_id FROM operation_requests")
            },
        }
        insurer = connection.execute(
            "SELECT insurer FROM contracts WHERE contract_id = ?", ("C-0007",)
        ).fetchone()[0]
    assert ids_by_table["subscribers"] == {f"S-{number:04d}" for number in range(1, 7)}
    assert ids_by_table["contracts"] == {f"C-{number:04d}" for number in range(1, 8)}
    assert ids_by_table["notices"] == {"N-2026-0417"}
    assert ids_by_table["operation_requests"] == {
        f"R-{number:04d}" for number in range(1, 6)
    }
    assert insurer == "OTHER-VIE"
    assert "C-0007" in snapshot(db)["contracts"]
