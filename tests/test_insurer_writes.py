"""Exercise versioned insurer writes against the observable backend state."""

from pathlib import Path

from stayline.backend.db import connect, reset_from_seed, snapshot
from tests.helpers import call, error, open_server


SEEDS = Path(__file__).resolve().parents[1] / "seeds"
RESTRICTIONS = ("rachat", "renonciation", "nantissement", "acceptation_benefice", "avance")
APPLY = {"notice_id": "N-2026-0417", "contract_id": "C-0001", "expected_version": 3}


def variant_db(tmp_path: Path, seed: str) -> str:
    """Build a separate database from one seed variant."""
    db_path = str(tmp_path / f"{seed}.sqlite")
    reset_from_seed(str(SEEDS / seed), db_path)
    return db_path


async def test_apply_writes_five_restrictions_with_lineage(insurer, seeded_db):
    result = await call(insurer, "apply_seizure", APPLY)
    state = snapshot(seeded_db)
    assert state["contracts"]["C-0001"]["restrictions"] == {
        name: "N-2026-0417|CPP-706-155@2026" for name in RESTRICTIONS
    }
    assert set(result["restrictions_written"]) == set(RESTRICTIONS)


async def test_apply_bumps_version_and_touches_no_other_contract(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await call(insurer, "apply_seizure", APPLY)
    state = snapshot(seeded_db)
    assert result["contract_id"] == "C-0001"
    assert result["version"] == 4
    assert state["contracts"]["C-0001"] | {"restrictions": {}} == before["contracts"]["C-0001"]
    assert {key: value for key, value in state["contracts"].items() if key != "C-0001"} == {
        key: value for key, value in before["contracts"].items() if key != "C-0001"
    }
    assert state["requests"] == before["requests"]


async def test_apply_wrong_contract_is_refused(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await error(insurer, "apply_seizure", APPLY | {"contract_id": "C-0002", "expected_version": 1})
    assert result.code == "contract_not_found"
    assert "does not target" in result.message
    assert snapshot(seeded_db) == before


async def test_apply_stale_version(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await error(insurer, "apply_seizure", APPLY | {"expected_version": 2})
    assert result.code == "stale_version"
    assert result.retryable
    assert "3" in result.message
    assert snapshot(seeded_db) == before


async def test_apply_twice_same_notice(insurer, seeded_db):
    await call(insurer, "apply_seizure", APPLY)
    before = snapshot(seeded_db)
    result = await error(insurer, "apply_seizure", APPLY)
    assert result.code == "duplicate_notice"
    assert len(snapshot(seeded_db)["contracts"]["C-0001"]["restrictions"]) == 5
    assert snapshot(seeded_db) == before


async def test_apply_same_key_replays(insurer, seeded_db):
    args = APPLY | {"idempotency_key": "apply-once"}
    first = await call(insurer, "apply_seizure", args)
    before = snapshot(seeded_db)
    second = await call(insurer, "apply_seizure", args)
    assert second == first
    assert len(snapshot(seeded_db)["contracts"]["C-0001"]["restrictions"]) == 5
    assert snapshot(seeded_db) == before


async def test_apply_authority_mismatch(tmp_path):
    seeded_db = variant_db(tmp_path, "authority_mismatch.json")
    before = snapshot(seeded_db)
    async with open_server("stayline.servers.insurer_contracts", seeded_db) as insurer:
        result = await error(insurer, "apply_seizure", APPLY)
    assert result.code == "authority_mismatch"
    assert snapshot(seeded_db) == before


async def test_apply_deceased_and_surrendered(tmp_path):
    for seed, contract_id, reason in (
        ("deceased_target.json", "C-0005", "CPP 706-155 paragraph 1"),
        ("surrendered_target.json", "C-0006", "surrendered"),
    ):
        seeded_db = variant_db(tmp_path, seed)
        before = snapshot(seeded_db)
        async with open_server("stayline.servers.insurer_contracts", seeded_db) as insurer:
            result = await error(insurer, "apply_seizure", {
                "notice_id": "N-2026-0417", "contract_id": contract_id, "expected_version": 1,
            })
        assert result.code == "operation_not_permitted"
        assert reason in result.message
        assert snapshot(seeded_db) == before


async def test_execute_rachat_on_seized_is_refused(insurer, seeded_db):
    await call(insurer, "apply_seizure", APPLY)
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-0001", "contract_id": "C-0001", "expected_version": 3,
    })
    assert result.code == "operation_not_permitted"
    assert "N-2026" not in result.message
    assert "2026/00417" not in result.message
    assert snapshot(seeded_db) == before


async def test_execute_avance_on_seized_is_refused(insurer, seeded_db):
    await call(insurer, "apply_seizure", APPLY)
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-0004", "contract_id": "C-0001", "expected_version": 4,
    })
    assert result.code == "operation_not_permitted"
    assert snapshot(seeded_db) == before


async def test_execute_arbitrage_on_seized_is_allowed(insurer, seeded_db):
    await call(insurer, "apply_seizure", APPLY)
    before = snapshot(seeded_db)
    result = await call(insurer, "execute_operation", {
        "request_id": "R-0002", "contract_id": "C-0001", "expected_version": 4,
    })
    state = snapshot(seeded_db)
    assert result == {"request_id": "R-0002", "status": "executed", "contract_id": "C-0001", "version": 5}
    assert state["contracts"]["C-0001"]["allocation"] == {"fonds_euro": 80, "uc_actions": 20}
    assert state["contracts"]["C-0001"]["restrictions"] == before["contracts"]["C-0001"]["restrictions"]
    assert state["requests"]["R-0002"] == "executed"


async def test_execute_rachat_on_other_contract(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await call(insurer, "execute_operation", {
        "request_id": "R-0003", "contract_id": "C-0002", "expected_version": 1,
    })
    state = snapshot(seeded_db)
    assert result == {"request_id": "R-0003", "status": "executed", "contract_id": "C-0002", "version": 2}
    assert state["contracts"]["C-0002"]["value_eur"] == 18000
    assert state["requests"]["R-0003"] == "executed"
    assert state["contracts"]["C-0001"] == before["contracts"]["C-0001"]


async def test_execute_request_contract_mismatch(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-0003", "contract_id": "C-0001", "expected_version": 3,
    })
    assert result.code == "invalid_argument"
    assert snapshot(seeded_db) == before


async def test_execute_twice_same_key_pays_once(insurer, seeded_db):
    args = {"request_id": "R-0003", "contract_id": "C-0002", "expected_version": 1,
            "idempotency_key": "execute-once"}
    first = await call(insurer, "execute_operation", args)
    before = snapshot(seeded_db)
    second = await call(insurer, "execute_operation", args)
    assert second == first
    assert snapshot(seeded_db)["contracts"]["C-0002"]["value_eur"] == 18000
    assert snapshot(seeded_db) == before


async def test_apply_second_notice_is_active_seizure(tmp_path):
    seeded_db = variant_db(tmp_path, "second_notice.json")
    async with open_server("stayline.servers.insurer_contracts", seeded_db) as insurer:
        await call(insurer, "apply_seizure", APPLY)
        before = snapshot(seeded_db)
        result = await error(insurer, "apply_seizure", APPLY | {
            "notice_id": "N-2026-0418", "expected_version": 4,
        })
    assert result.code == "active_seizure"
    assert snapshot(seeded_db) == before


async def test_execute_total_rachat_surrenders_contract(insurer, seeded_db):
    with connect(seeded_db) as db:
        db.execute("UPDATE operation_requests SET amount_eur = 23000 WHERE request_id = 'R-0003'")
    result = await call(insurer, "execute_operation", {
        "request_id": "R-0003", "contract_id": "C-0002", "expected_version": 1,
    })
    state = snapshot(seeded_db)
    assert result["version"] == 2
    assert state["contracts"]["C-0002"]["status"] == "surrendered"
    assert state["contracts"]["C-0002"]["value_eur"] == 0
    assert state["requests"]["R-0003"] == "executed"


async def test_execute_rachat_above_value_is_invalid(insurer, seeded_db):
    with connect(seeded_db) as db:
        db.execute("UPDATE operation_requests SET amount_eur = 23001 WHERE request_id = 'R-0003'")
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-0003", "contract_id": "C-0002", "expected_version": 1,
    })
    assert result.code == "invalid_argument"
    assert snapshot(seeded_db) == before


async def test_apply_missing_notice_precedes_missing_contract(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await error(insurer, "apply_seizure", {
        "notice_id": "N-2020-9999", "contract_id": "C-9999", "expected_version": 0,
    })
    assert result.code == "not_found"
    assert snapshot(seeded_db) == before


async def test_execute_missing_request_precedes_missing_contract(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-9999", "contract_id": "C-9999", "expected_version": 0,
    })
    assert result.code == "not_found"
    assert snapshot(seeded_db) == before


async def test_execute_non_pending_precedes_stale_version(insurer, seeded_db):
    with connect(seeded_db) as db:
        db.execute("UPDATE operation_requests SET status = 'executed' WHERE request_id = 'R-0003'")
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-0003", "contract_id": "C-0002", "expected_version": 0,
    })
    assert result.code == "conflict"
    assert snapshot(seeded_db) == before


async def test_execute_stale_version_is_retryable(insurer, seeded_db):
    before = snapshot(seeded_db)
    result = await error(insurer, "execute_operation", {
        "request_id": "R-0003", "contract_id": "C-0002", "expected_version": 0,
    })
    assert result.code == "stale_version"
    assert result.retryable
    assert "1" in result.message
    assert snapshot(seeded_db) == before


async def test_apply_uses_latest_current_rule(insurer, seeded_db):
    with connect(seeded_db) as db:
        db.execute(
            "INSERT INTO rules (rule_id, version, valid_from, restrictions) VALUES (?, ?, ?, ?)",
            ("CPP-706-155", "2026b", "2026-06-01", '["rachat"]'),
        )
        db.execute(
            "INSERT INTO rules (rule_id, version, valid_from, restrictions) VALUES (?, ?, ?, ?)",
            ("CPP-706-155", "2099", "2099-01-01", '["avance"]'),
        )
    result = await call(insurer, "apply_seizure", APPLY)
    state = snapshot(seeded_db)
    assert result["restrictions_written"] == ["rachat"]
    assert state["contracts"]["C-0001"]["restrictions"] == {
        "rachat": "N-2026-0417|CPP-706-155@2026b"
    }
