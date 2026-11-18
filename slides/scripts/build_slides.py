"""Build Slidev pages and presenter notes from the defence script."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/defence/script.md"
DEST = ROOT / "slides/slides.md"
COMPONENTS = (
    "Freeze", "TwoButtons", "Backend", "Graph", "DemoSuccess",
    "DemoFailure", "Memory", "Results", "ErrorAnalysis", "Close",
)
FRONTMATTER = """---
theme: default
title: Stayline
canvasWidth: 1920
aspectRatio: 16/9
fonts:
  provider: none
transition: stay-fade
mcp: false
colorSchema: light
---
"""


def parse(source: str) -> list[tuple[str, str, str, int]]:
    source = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    sections = re.split(r"(?=^## Beat \d+:)", source, flags=re.M)[1:]
    beats = []
    for number, section in enumerate(sections, 1):
        head = re.match(r"## Beat (\d+): ([^\n]+)", section)
        if not head or int(head.group(1)) != number:
            raise ValueError(f"Expected beat {number}")
        speaker = re.search(r"^\*\*[^\n]+\*\*$", section, flags=re.M)
        asked = re.search(r"^If asked:.*$", section, flags=re.M)
        if not speaker or not asked:
            raise ValueError(f"Missing speaker or If asked in beat {number}")
        spoken = section[speaker.end():asked.start()]
        spoken = "\n".join(line for line in spoken.splitlines() if not line.startswith(">"))
        spoken = spoken.strip()
        if "-->" in spoken or "-->" in asked.group():
            raise ValueError(f"Unsafe note delimiter in beat {number}")
        beats.append((speaker.group(), spoken, asked.group(), spoken.count("[click]")))
    if len(beats) != len(COMPONENTS):
        raise ValueError(f"Expected {len(COMPONENTS)} beats, found {len(beats)}")
    return beats


def render(beats: list[tuple[str, str, str, int]]) -> str:
    pages = []
    for number, (speaker, spoken, asked, clicks) in enumerate(beats, 1):
        lines = [f"<B{number:02d}{COMPONENTS[number - 1]} />"]
        lines += ['<span v-click class="click-register" />'] * clicks
        lines += ["", "<!--", speaker, "", spoken, "", asked, "-->"]
        pages.append("\n".join(lines))
    result = FRONTMATTER + "\n" + "\n\n---\n\n".join(pages) + "\n"
    if any(char in result for char in ("\u2014", "\u2013")):
        raise ValueError("Long dash found in slides")
    return result


def main() -> None:
    DEST.write_text(render(parse(SOURCE.read_text(encoding="utf-8"))), encoding="utf-8")
    print(f"wrote {DEST}")


if __name__ == "__main__":
    main()
