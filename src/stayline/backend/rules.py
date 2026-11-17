"""Pure rules for contract matching and permitted operations."""

import unicodedata
from typing import Literal

from pydantic import BaseModel


Evidence = Literal["policy_number", "birth_date", "birth_place", "name"]
Outcome = Literal["match", "ambiguous_match", "contract_not_found"]

RESTRICTIONS_706_155 = (
    "rachat",
    "renonciation",
    "nantissement",
    "acceptation_benefice",
    "avance",
)

_VALID_AUTHORITIES = {
    ("jld", "enquete_preliminaire"),
    ("jld", "enquete_flagrance"),
    ("juge_instruction", "information_judiciaire"),
}


class Candidate(BaseModel):
    """A contract with the fields that support its candidacy."""

    contract_id: str
    policy_number: str
    evidence: list[Evidence]


class MatchOutcome(BaseModel):
    """The contract decision and its sorted candidates."""

    outcome: Outcome
    candidates: list[Candidate]


def normalise_policy_number(raw: str | None) -> str | None:
    """Remove policy separators and uppercase the remaining text."""

    if raw is None:
        return None
    number = "".join(char for char in raw if not char.isspace() and char not in "-./")
    return number.upper() or None


def fold_name(name: str) -> str:
    """Fold accents and case, then collapse whitespace."""

    plain = "".join(
        char for char in unicodedata.normalize("NFKD", name)
        if not unicodedata.combining(char)
    )
    return " ".join(plain.casefold().split())


def _name_matches(target: dict, row: dict) -> bool:
    last_name = target.get("last_name")
    first_names = target.get("first_names")
    return bool(
        last_name and first_names
        and row.get("last_name") and row.get("first_names")
        and fold_name(last_name) == fold_name(row["last_name"])
        and fold_name(first_names) == fold_name(row["first_names"])
    )


def _identity_matches(target: dict, row: dict) -> bool:
    return (
        str(target["birth_date"]) == str(row["birth_date"])
        and target["birth_place_code"] == row["birth_place_code"]
    )


def _candidate(row: dict, evidence: list[Evidence]) -> Candidate:
    return Candidate(
        contract_id=row["contract_id"],
        policy_number=row["policy_number"],
        evidence=evidence,
    )


def _identity_candidates(target: dict, rows: list[dict]) -> list[Candidate]:
    candidates = []
    for row in rows:
        if _identity_matches(target, row):
            evidence: list[Evidence] = ["birth_date", "birth_place"]
            if _name_matches(target, row):
                evidence.append("name")
            candidates.append(_candidate(row, evidence))
    return candidates


def _name_candidates(target: dict, rows: list[dict]) -> list[Candidate]:
    candidates = []
    for row in rows:
        if _name_matches(target, row):
            evidence: list[Evidence] = ["name"]
            if target.get("birth_date") and str(target["birth_date"]) == str(row["birth_date"]):
                evidence.append("birth_date")
            if target.get("birth_place_code") and target["birth_place_code"] == row["birth_place_code"]:
                evidence.append("birth_place")
            candidates.append(_candidate(row, evidence))
    return candidates


def _outcome(outcome: Outcome, candidates: list[Candidate]) -> MatchOutcome:
    return MatchOutcome(
        outcome=outcome,
        candidates=sorted(candidates, key=lambda candidate: candidate.contract_id),
    )


def match_contracts(target: dict, rows: list[dict], insurer_id: str) -> MatchOutcome:
    """Match a target against this insurer's contract rows."""

    own_rows = [row for row in rows if row["insurer"] == insurer_id]
    number = normalise_policy_number(target.get("policy_number"))
    identity_complete = bool(target.get("birth_date") and target.get("birth_place_code"))

    if number is not None:
        numbered = [
            row for row in own_rows
            if normalise_policy_number(row["policy_number"]) == number
        ]
        if len(numbered) == 1:
            row = numbered[0]
            if identity_complete and _identity_matches(target, row):
                evidence: list[Evidence] = ["policy_number", "birth_date", "birth_place"]
                if _name_matches(target, row):
                    evidence.append("name")
                return _outcome("match", [_candidate(row, evidence)])
            return _outcome("ambiguous_match", [_candidate(row, ["policy_number"])])
        if numbered:
            return _outcome(
                "ambiguous_match",
                [_candidate(row, ["policy_number"]) for row in numbered],
            )
        if identity_complete:
            candidates = _identity_candidates(target, own_rows)
            return _outcome("ambiguous_match" if candidates else "contract_not_found", candidates)

    if identity_complete:
        candidates = _identity_candidates(target, own_rows)
        outcome: Outcome = "match" if len(candidates) == 1 else "ambiguous_match"
    else:
        candidates = _name_candidates(target, own_rows)
        outcome = "ambiguous_match"
    return _outcome(outcome if candidates else "contract_not_found", candidates)


def authority_is_valid(judge_role: str, procedure_type: str) -> bool:
    """Check whether the judge may issue this type of procedure."""

    return (judge_role, procedure_type) in _VALID_AUTHORITIES


def is_operation_permitted(request_type: str, active_restrictions: set[str]) -> bool:
    """Permit an operation when its type has no active restriction."""

    return request_type not in active_restrictions
