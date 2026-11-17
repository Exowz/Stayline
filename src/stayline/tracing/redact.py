"""Remove seeded personal and untrusted text from trace attributes."""

import json
import unicodedata
from contextlib import closing
from pathlib import Path
from typing import Any

from stayline.backend.db import connect


def _fold(value: str) -> str:
    """Fold accents and case for stable matching."""
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(char))


class Redactor:
    """Replace known seed values with stable placeholders."""

    def __init__(
        self, persons: list[str] | None = None, dates: list[str] | None = None,
        places: list[str] | None = None, notices: list[str] | None = None,
    ) -> None:
        self.replacements: dict[str, str] = {}
        for values, label in ((persons or [], "PERSON"), (dates or [], "DATE"),
                              (places or [], "PLACE")):
            count = 0
            for value in values:
                key = _fold(value)
                if key and key not in self.replacements:
                    count += 1
                    self.replacements[key] = f"<{label}_{count}>"
        for value in notices or []:
            key = _fold(value)
            if key:
                self.replacements[key] = f"<UNTRUSTED {len(value)} chars>"

    @classmethod
    def from_db(cls, db_path: Path) -> "Redactor":
        """Learn names, birth details and notice text from a run database."""
        persons: list[str] = []
        dates: list[str] = []
        places: list[str] = []
        notices: list[str] = []
        with closing(connect(str(db_path))) as db:
            for table, prefix in (("subscribers", ""), ("notices", "target_")):
                columns = [f"{prefix}{name}" for name in
                           ("last_name", "first_names", "birth_date", "birth_place_code")]
                for row in db.execute(f"SELECT {', '.join(columns)} FROM {table}"):
                    for target, value in zip((persons, persons, dates, places), row):
                        if value:
                            target.append(str(value))
            for row in db.execute("SELECT free_text FROM notices"):
                if row[0]:
                    notices.append(str(row[0]))
        return cls(persons, dates, places, notices)

    def _redact_text(self, value: str) -> str:
        """Choose longest non-overlapping matches in the original text."""
        folded = ""
        positions: list[int] = []
        for index, char in enumerate(value):
            part = _fold(char)
            folded += part
            positions.extend([index] * len(part))
        matches: list[tuple[int, int, str]] = []
        for key in sorted(self.replacements, key=len, reverse=True):
            start = 0
            while (found := folded.find(key, start)) >= 0:
                first, last = positions[found], positions[found + len(key) - 1] + 1
                if not any(first < end and last > begin for begin, end, _ in matches):
                    matches.append((first, last, self.replacements[key]))
                start = found + 1
        for first, last, replacement in sorted(matches, reverse=True):
            value = value[:first] + replacement + value[last:]
        return value

    def redact(self, value: Any) -> Any:
        """Recursively redact strings and untrusted dictionary values."""
        if isinstance(value, dict):
            return {key: (f"<UNTRUSTED {len(item if isinstance(item, str) else json.dumps(item, ensure_ascii=False))} chars>"
                          if key == "untrusted" else self.redact(item))
                    for key, item in value.items()}
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, str):
            return self._redact_text(value)
        return value
