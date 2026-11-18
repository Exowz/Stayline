"""Operator alias memory: store behavior with no model."""

from stayline.memory.aliases import (
    forget_operator, load_aliases, namespace, open_store, recall_aliases, remember_alias,
)


MESSAGE = "Orion is instruction 2026/00417 at TJ Paris"
ORION = {"alias": "Orion", "case_reference": "2026/00417", "court": "TJ Paris"}


def test_namespace_is_per_operator():
    assert namespace("op-1") == ("operators", "op-1", "aliases")


def test_alias_survives_closing_and_reopening_the_file(tmp_path):
    path = str(tmp_path / "memory.sqlite")
    with open_store(path) as store:
        assert remember_alias(store, "op-1", **ORION, operator_message=MESSAGE) is True
    with open_store(path) as store:
        assert recall_aliases(store, "op-1") == {
            "orion": {"case_reference": "2026/00417", "court": "TJ Paris", "history": []},
        }


def test_correction_keeps_history(tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        remember_alias(store, "op-1", **ORION, operator_message=MESSAGE)
        newer = "Orion is now instruction 2026/00500 at TJ Lyon"
        assert remember_alias(
            store, "op-1", "Orion", "2026/00500", "TJ Lyon", operator_message=newer
        ) is True
        value = recall_aliases(store, "op-1")["orion"]
    assert value["case_reference"] == "2026/00500" and value["court"] == "TJ Lyon"
    assert value["history"] == [{"case_reference": "2026/00417", "court": "TJ Paris"}]


def test_repeating_the_same_value_adds_no_history(tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        remember_alias(store, "op-1", **ORION, operator_message=MESSAGE)
        remember_alias(store, "op-1", **ORION, operator_message=MESSAGE)
        assert recall_aliases(store, "op-1")["orion"]["history"] == []


def test_another_operator_sees_nothing(tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        remember_alias(store, "op-1", **ORION, operator_message=MESSAGE)
        assert recall_aliases(store, "op-2") == {}


def test_alias_only_in_a_tool_result_is_not_stored(tmp_path):
    operator_message = "A CGP request came in, please process it."
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        stored = remember_alias(store, "op-1", **ORION, operator_message=operator_message)
        assert stored is False
        assert recall_aliases(store, "op-1") == {}


def test_guard_needs_alias_case_and_court_in_the_message(tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        for message in (
            "Orion is instruction 2026/00417",
            "Orion is at TJ Paris",
            "It is instruction 2026/00417 at TJ Paris",
        ):
            assert remember_alias(store, "op-1", **ORION, operator_message=message) is False
        assert recall_aliases(store, "op-1") == {}


def test_guard_ignores_case_and_court_punctuation(tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        stored = remember_alias(
            store, "op-1", "orion", "2026/00417", "TJ-PARIS", operator_message=MESSAGE.upper()
        )
        assert stored is True


def test_forget_operator_empties_the_namespace(tmp_path):
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        remember_alias(store, "op-1", **ORION, operator_message=MESSAGE)
        remember_alias(
            store, "op-1", "Atlas", "2026/00500", "TJ Lyon",
            operator_message="Atlas is instruction 2026/00500 at TJ Lyon",
        )
        remember_alias(store, "op-2", **ORION, operator_message=MESSAGE)
        assert forget_operator(store, "op-1") == 2
        assert recall_aliases(store, "op-1") == {}
        assert "orion" in recall_aliases(store, "op-2")


def test_load_aliases_preloads_each_operator(tmp_path):
    memory = {"op-1": {"Orion": {"case_reference": "2026/00417", "court": "TJ Paris"}}}
    with open_store(str(tmp_path / "memory.sqlite")) as store:
        load_aliases(store, memory)
        assert recall_aliases(store, "op-1")["orion"]["case_reference"] == "2026/00417"
        assert recall_aliases(store, "op-2") == {}
