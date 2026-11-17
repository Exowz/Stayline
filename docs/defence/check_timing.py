"""Check that each beat of the defence script fits its time budget.

Spoken words per beat are counted at 140 words per minute. Cues, stage
directions, "If asked:" lines, headings and HTML comments are not spoken.
A [RESULT: ...] placeholder counts as two spoken words.
"""

import re
import sys
from pathlib import Path

WORDS_PER_MINUTE = 140
SPEAKER_TARGET_S = 300
SPEAKER_TOLERANCE_S = 15
HEADER = re.compile(r"^\*\*(KHADIDJA|EWAN) · about (\d+) seconds\*\*$")
BEAT = re.compile(r"^## Beat (\d+): (.+)$")


def spoken_words(text: str) -> int:
    """Count spoken words in one beat block."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\[RESULT:[^\]]*\]", " placeholder placeholder ", text)
    text = text.replace("[click]", " ")
    lines = [
        line for line in text.splitlines()
        if not line.startswith((">", "If asked:", "#", "**"))
    ]
    return len(re.findall(r"[\w'’]+", " ".join(lines)))


def read_beats(path: Path) -> list[dict]:
    """Split the script into beats with speaker, budget and spoken words."""
    beats: list[dict] = []
    current: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        beat = BEAT.match(line)
        if beat:
            current = {"number": int(beat.group(1)), "title": beat.group(2),
                       "speaker": None, "seconds": 0, "lines": []}
            beats.append(current)
            continue
        if current is None:
            continue
        header = HEADER.match(line)
        if header:
            current["speaker"], current["seconds"] = header.group(1), int(header.group(2))
        else:
            current["lines"].append(line)
    for beat in beats:
        beat["words"] = spoken_words("\n".join(beat["lines"]))
        beat["budget"] = beat["seconds"] * WORDS_PER_MINUTE // 60
    return beats


def check(beats: list[dict]) -> list[str]:
    """Return every timing problem found."""
    problems: list[str] = []
    totals: dict[str, float] = {}
    for beat in beats:
        if beat["speaker"] is None:
            problems.append(f"beat {beat['number']} has no speaker header")
            continue
        if beat["words"] > beat["budget"]:
            problems.append(
                f"beat {beat['number']} ({beat['speaker']}): {beat['words']} words, "
                f"budget {beat['budget']}")
        seconds = beat["words"] * 60 / WORDS_PER_MINUTE
        totals[beat["speaker"]] = totals.get(beat["speaker"], 0) + seconds
    for speaker, seconds in totals.items():
        if abs(seconds - SPEAKER_TARGET_S) > SPEAKER_TOLERANCE_S:
            problems.append(
                f"{speaker}: {seconds:.0f}s spoken, needs {SPEAKER_TARGET_S} "
                f"plus or minus {SPEAKER_TOLERANCE_S}")
    return problems


def main(argv: list[str]) -> int:
    """Print the per-beat table and return 1 when a check fails."""
    path = Path(argv[1]) if len(argv) > 1 else Path(__file__).with_name("script.md")
    beats = read_beats(path)
    for beat in beats:
        print(f"beat {beat['number']:>2} {str(beat['speaker']):<9} "
              f"{beat['words']:>4} / {beat['budget']:>4} words  {beat['title']}")
    problems = check(beats)
    for problem in problems:
        print("FAIL:", problem)
    if not problems:
        print("timing ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
