"""The Imams' conventional kunyas in Imami chains (pure). Rule and data: imam_kunya_conventions.json; see
pg_export/AGENTS.md §Imam kunyas."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from transliteration import table_key

CONVENTIONS_PATH = Path(__file__).resolve().parent / "imam_kunya_conventions.json"
KUNYA_HEADS = {"ابو", "ابي", "ابا"}


@dataclass(frozen=True)
class ImamKunyaMatch:
    basis: str              # imam_kunya_convention (one Imam) or imam_kunya_candidate (a shared kunya, unqualified)
    imam_ids: tuple[str, ...]
    detail: str


class ImamKunyaRegister:
    def __init__(self, data: dict):
        self.data = data
        self.imams = {imam["ordinal"]: imam for imam in data["imams"]}
        self.kunyas: list[tuple[tuple[str, ...], dict]] = []
        for entry in data["kunyas"]:
            words = tuple(table_key(word) for word in entry["kunya"].split())
            qualifiers = {tuple(table_key(word) for word in phrase.split()): ordinal
                          for phrase, ordinal in entry["qualifiers"].items()}
            self.kunyas.append((words[1:], {**entry, "qualifier_keys": qualifiers}))
        self.kunyas.sort(key=lambda item: -len(item[0]))   # longest kunya name first (عبد الله before a one-word one)

    @classmethod
    def load(cls, path: Path = CONVENTIONS_PATH) -> "ImamKunyaRegister":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def imam_id(self, ordinal: int) -> str:
        return self.imams[ordinal]["id"]

    def match(self, surface: str, tradition: str, marker_follows: bool) -> ImamKunyaMatch | None:
        """The Imam(s) a kunya surface names under the convention, or None (not Imami, no marker, not a listed kunya,
        or other words after the kunya)."""
        if tradition != "Imami":
            return None
        words = [table_key(word) for word in (surface or "").split()]
        marker_in_surface = bool(words) and words[-1] in ("ع", "(ع)")
        if marker_in_surface:
            words = words[:-1]
        if not (marker_in_surface or marker_follows) or len(words) < 2 or words[0] not in KUNYA_HEADS:
            return None
        for name, entry in self.kunyas:
            if tuple(words[1:1 + len(name)]) != name:
                continue
            rest = tuple(words[1 + len(name):])
            kunya = entry["kunya"]
            if rest:
                ordinal = entry["qualifier_keys"].get(rest)
                if ordinal is None:
                    return None
                return ImamKunyaMatch("imam_kunya_convention", (self.imam_id(ordinal),),
                                      f"{kunya} + {' '.join(rest)}: qualifier names one Imam")
            if entry["unqualified"] is not None:
                return ImamKunyaMatch("imam_kunya_convention", (self.imam_id(entry["unqualified"]),),
                                      f"{kunya}: conventional kunya with the marker")
            return ImamKunyaMatch("imam_kunya_candidate", tuple(self.imam_id(o) for o in entry["shared_by"]),
                                  f"{kunya}: shared by several Imams, no qualifier")
        return None


def detail_ascii(detail: str) -> str:
    """Single-line detail text (no control characters) for the CSV."""
    return re.sub(r"\s+", " ", detail).strip()
