"""Write slides.public.md: the same deck with no speaker notes and no presenter mode.

Used for the public GitHub Pages build. slides.md stays the source of truth."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "slides.md").read_text(encoding="utf-8")
head, sep, body = src[3:].partition("\n---\n")
body = re.sub(r"<!--.*?-->\s*", "", body, flags=re.S)
out = "---" + head.rstrip() + "\npresenter: false\nrouterMode: hash\nexportFilename: stayline\n---\n" + body
(root / "slides.public.md").write_text(out, encoding="utf-8")
print(f"slides.public.md: {src.count('<!--')} note blocks removed")
