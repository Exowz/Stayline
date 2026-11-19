"""The defence deck stays reproducible from its committed sources."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
SLIDES = ROOT / "slides"
SCRIPT = ROOT / "docs/defence/script.md"


def run_script(name: str) -> None:
    subprocess.run([str(PYTHON), str(SLIDES / "scripts" / name)], cwd=ROOT, check=True)


def beats() -> list[tuple[str, str]]:
    source = re.sub(r"<!--.*?-->", "", SCRIPT.read_text(), flags=re.S)
    sections = re.split(r"(?=^## Beat \d+:)", source, flags=re.M)[1:]
    result = []
    for section in sections:
        spoken = re.search(r"\*\*[^\n]+\*\*\n\n(.*?)\n\nIf asked:", section, re.S)
        assert spoken
        clean = "\n".join(line for line in spoken.group(1).splitlines() if not line.startswith(">"))
        result.append((section, clean.strip()))
    return result


def test_notes_are_deterministic_and_match_script() -> None:
    run_script("build_slides.py")
    first = (SLIDES / "slides.md").read_bytes()
    run_script("build_slides.py")
    assert (SLIDES / "slides.md").read_bytes() == first
    content = first.decode()
    sections = re.split(r"^---\s*$", content, flags=re.M)[2:]
    notes = re.findall(r"<!--\n(.*?)\n-->", content, flags=re.S)
    source_beats = beats()
    assert len(source_beats) == len(notes) == 10
    assert len(re.findall(r"<B\d\d\w+ />", content)) == 10
    assert "\u2014" not in content and "\u2013" not in content
    for (source, spoken), note in zip(source_beats, notes):
        assert spoken in note
        assert "-->" not in note
    slide_chunks = re.findall(r"<B\d\d\w+ />.*?(?=\n---\n|\Z)", content, flags=re.S)
    assert len(slide_chunks) == 10
    for (source, _), slide in zip(source_beats, slide_chunks):
        assert slide.count('class="click-register"') == source.count("[click]")


def test_data_is_deterministic_and_computed() -> None:
    run_script("build_data.py")
    first = (SLIDES / "generated/deck.json").read_bytes()
    run_script("build_data.py")
    assert (SLIDES / "generated/deck.json").read_bytes() == first
    deck = json.loads(first)
    assert deck["summary"]["passed"] == 88
    assert deck["summary"]["runs"] == 90
    assert deck["mistral_summary"]["passed"] == 60
    assert deck["baseline1_summary"]["passed"] == 75
    assert deck["comparison"]["only_a"] == 11
    assert len(deck["runs"]) == len(deck["mistral_runs"]) == len(deck["baseline1_runs"]) == 90
    assert sum(s["kind"] == "LLM" and s["tokens_out"] == 4000 for s in deck["traces"]["s14"]["spans"]) == 2
    assert deck["traces"]["s01"]["model_calls"] == 6
