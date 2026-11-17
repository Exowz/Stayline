"""Tests for the pure contract and authority rules."""

from stayline.backend.rules import (
    RESTRICTIONS_706_155,
    authority_is_valid,
    fold_name,
    is_operation_permitted,
    match_contracts,
    normalise_policy_number,
)


ROWS = [
    {
        "contract_id": "C-0001",
        "policy_number": "AV-2019-004512",
        "insurer": "STAYLINE-VIE",
        "last_name": "Benaïssa",
        "first_names": "Karim",
        "birth_date": "1978-03-14",
        "birth_place_code": "75112",
    },
    {
        "contract_id": "C-0002",
        "policy_number": "AV-2021-000873",
        "insurer": "STAYLINE-VIE",
        "last_name": "Benaïssa",
        "first_names": "Karim",
        "birth_date": "1978-03-14",
        "birth_place_code": "75112",
    },
    {
        "contract_id": "C-0003",
        "policy_number": "AV-2018-001200",
        "insurer": "STAYLINE-VIE",
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": "1985-11-02",
        "birth_place_code": "69123",
    },
    {
        "contract_id": "C-0004",
        "policy_number": "AV-2020-007781",
        "insurer": "STAYLINE-VIE",
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": "1990-06-21",
        "birth_place_code": "33063",
    },
    {
        "contract_id": "C-0005",
        "policy_number": "AV-2015-000310",
        "insurer": "STAYLINE-VIE",
        "last_name": "Lefèvre",
        "first_names": "Paul",
        "birth_date": None,
        "birth_place_code": None,
    },
    {
        "contract_id": "C-0006",
        "policy_number": "AV-2012-000045",
        "insurer": "STAYLINE-VIE",
        "last_name": "Dubois",
        "first_names": "Anne",
        "birth_date": None,
        "birth_place_code": None,
    },
    {
        "contract_id": "C-0007",
        "policy_number": "XV-2017-009000",
        "insurer": "OTHER-VIE",
        "last_name": "Nguyen",
        "first_names": "Linh",
        "birth_date": None,
        "birth_place_code": None,
    },
]


def test_normalise():
    assert normalise_policy_number("av-2019 004.512") == "AV2019004512"
    assert normalise_policy_number(" av/2019-004512 ") == "AV2019004512"
    assert normalise_policy_number(" .-/ ") is None
    assert normalise_policy_number(None) is None


def test_number_and_identity_match_despite_spelling():
    target = {
        "policy_number": "av-2019 004.512",
        "last_name": "Benaissa",
        "first_names": "Karim",
        "birth_date": "1978-03-14",
        "birth_place_code": "75112",
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0001"]
    assert out.candidates[0].policy_number == "AV-2019-004512"
    assert set(out.candidates[0].evidence) == {
        "policy_number", "birth_date", "birth_place", "name"
    }


def test_no_number_single_contract_matches():
    target = {
        "policy_number": None,
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": "1985-11-02",
        "birth_place_code": "69123",
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0003"]
    assert set(out.candidates[0].evidence) == {"birth_date", "birth_place", "name"}


def test_no_number_two_contracts_is_ambiguous():
    target = {
        "policy_number": None,
        "last_name": "Benaissa",
        "first_names": "Karim",
        "birth_date": "1978-03-14",
        "birth_place_code": "75112",
    }
    out = match_contracts(target, list(reversed(ROWS)), "STAYLINE-VIE")
    assert out.outcome == "ambiguous_match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0001", "C-0002"]
    assert all(set(candidate.evidence) == {"birth_date", "birth_place", "name"}
               for candidate in out.candidates)


def test_namesake_without_birth_data_is_ambiguous():
    target = {
        "policy_number": None,
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": None,
        "birth_place_code": None,
    }
    out = match_contracts(target, list(reversed(ROWS)), "STAYLINE-VIE")
    assert out.outcome == "ambiguous_match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0003", "C-0004"]
    assert [candidate.evidence for candidate in out.candidates] == [["name"], ["name"]]


def test_number_with_conflicting_identity_is_ambiguous():
    target = {
        "policy_number": "AV-2019-004512",
        "last_name": "Benaïssa",
        "first_names": "Karim",
        "birth_date": "1985-11-02",
        "birth_place_code": "69123",
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "ambiguous_match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0001"]
    assert out.candidates[0].evidence == ["policy_number"]


def test_number_without_birth_data_is_ambiguous():
    target = {
        "policy_number": "AV-2019-004512",
        "last_name": None,
        "first_names": None,
        "birth_date": None,
        "birth_place_code": None,
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "ambiguous_match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0001"]
    assert out.candidates[0].evidence == ["policy_number"]


def test_wrong_digit_with_unique_identity_is_ambiguous():
    target = {
        "policy_number": "AV-2018-001201",
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": "1985-11-02",
        "birth_place_code": "69123",
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "ambiguous_match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0003"]
    assert set(out.candidates[0].evidence) == {"birth_date", "birth_place", "name"}


def test_other_insurer_is_not_found():
    target = {
        "policy_number": "XV-2017-009000",
        "last_name": "Nguyen",
        "first_names": "Linh",
        "birth_date": None,
        "birth_place_code": None,
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "contract_not_found"
    assert out.candidates == []


def test_nothing_matches_is_not_found():
    target = {
        "policy_number": "AV-2099-999999",
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": "2000-01-01",
        "birth_place_code": "75001",
    }
    out = match_contracts(target, ROWS, "STAYLINE-VIE")
    assert out.outcome == "contract_not_found"
    assert out.candidates == []


def test_authority_pairs():
    assert authority_is_valid("jld", "enquete_preliminaire")
    assert authority_is_valid("jld", "enquete_flagrance")
    assert authority_is_valid("juge_instruction", "information_judiciaire")
    assert not authority_is_valid("jld", "information_judiciaire")
    assert not authority_is_valid("juge_instruction", "enquete_preliminaire")
    assert not authority_is_valid("other", "enquete_flagrance")


def test_permissions():
    seized = {"rachat", "renonciation", "nantissement", "acceptation_benefice", "avance"}
    assert RESTRICTIONS_706_155 == (
        "rachat", "renonciation", "nantissement", "acceptation_benefice", "avance"
    )
    assert not is_operation_permitted("rachat", seized)
    assert not is_operation_permitted("avance", seized)
    assert is_operation_permitted("arbitrage", seized)
    assert is_operation_permitted("rachat", set())


def test_wrong_number_with_incomplete_identity_uses_name():
    target = {
        "policy_number": "AV-2018-001201",
        "last_name": "Martin",
        "first_names": "Claire",
        "birth_date": "1985-11-02",
        "birth_place_code": None,
    }
    out = match_contracts(target, list(reversed(ROWS)), "STAYLINE-VIE")
    assert out.outcome == "ambiguous_match"
    assert [candidate.contract_id for candidate in out.candidates] == ["C-0003", "C-0004"]
    assert [set(candidate.evidence) for candidate in out.candidates] == [
        {"name", "birth_date"}, {"name"}
    ]


def test_fold_name_removes_accents_and_outer_space():
    assert fold_name("  BENAÏSSA ") == "benaissa"
    assert fold_name("  Claire   Marie  ") == "claire marie"
