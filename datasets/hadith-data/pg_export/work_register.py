"""Persons a work itself credits: the compiler heading every chain, and a transmitter the work names in full.

Data: `work_register.json` (owner-reviewable). Rules and rationale: AGENTS.md §Compiler as first transmitter.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

HERE = Path(__file__).resolve().parent
REGISTER_PATH = HERE / "work_register.json"
# The reader tool's work profiles and alias rule (chain-reader/v3), reused so the projection and the reader agree on when
# the text already writes the compiler (owner 2026-11-22; pilot cases cr-0183, cr-0197: a longer spelling of his name).
READER_V3_DIR = HERE.parent / "chain-reader" / "v3"
PROFILES_V3_PATH = READER_V3_DIR / "work_profiles_v3.json"
EXPAND_V3_PATH = READER_V3_DIR / "expand_v3.py"


def _reader_expand():
    import importlib.util
    import sys
    for extra in (str(READER_V3_DIR), str(READER_V3_DIR.parent)):
        if extra not in sys.path:
            sys.path.append(extra)
    spec = importlib.util.spec_from_file_location("chain_reader_expand_v3", EXPAND_V3_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
LICENCE = ("Shura wa Istehsan register (work_register.json); the name as the work writes it or as the owner's ruling credits it to "
           "the work, OpenITI and provider texts under their own licences")

MARKS = re.compile(r"[ً-ٰٟـ]")
LEADING_NUMBERING = re.compile(r"^[\s\d٠-٩\-–—/\\.,:؛،()\[\]«»\"']+")
CONTINUATION_PREFIX = re.compile(r"^تابع\s*/\s*")
# A chain the compiler heard: the opening hearing verb of his own words (Sunni works, Musnad Zayd), optionally waw/fa-led.
HEARING = r"(?:حدثنا|حدثني|حدثناه|حدثنيه|أخبرنا|أخبرني|أخبرناه|أخبرنيه|خبرنا|أنبأنا|أنبأني|نبأنا|سمعت|ثنا|قرأت على|قرئ على)"
DIRECT_VERB = re.compile(r"^[وف]?" + HEARING + r"(?:\s|$|:)")
# «قال: أخبرني …» opening a report is the work's transmitter quoting the compiler's own hearing (al-Amali of al-Mufid).
QUOTED_COMPILER = re.compile(r"^و?قال\s*:?\s*\]?\s*(?=[وف]?" + HEARING + r")")
# Works whose chains open with the shaykh's name and no verb (al-Kafi, al-Saduq): these openings say he did not hear it.
INDIRECT_OPENING = re.compile(
    r"^(?:و\s*)?(?:قال|قالت|روى|روي|يروى|وروي|عن|عنه|ذكر|بلغني|بلغنا|في|بهذا|بإسناده|باسناده|ومنهم|منهم|أما|وأما|قلنا|فإن|"
    r"قد|وقد|هذا|سئل|كان|وكان)(?:\s|$|:)")


def fold(text: str) -> str:
    """Comparison form of a name: marks, tatweel, alef and Persian letters folded, single spaces."""
    text = MARKS.sub("", text or "")
    text = re.sub("[أإآٱ]", "ا", text).replace("ى", "ي").replace("ی", "ي").replace("ک", "ك").replace("ة", "ه")
    return " ".join(text.split())


def opening_words(text: str) -> str:
    """The start of a report's chain text with numbering, brackets and a «تابع/» continuation marker removed."""
    text = MARKS.sub("", text or "").replace("ی", "ي").replace("ک", "ك")
    text = LEADING_NUMBERING.sub("", text.strip())
    text = CONTINUATION_PREFIX.sub("", text).strip()
    return QUOTED_COMPILER.sub("", text)


@dataclass(frozen=True)
class Compiler:
    work: str
    narrator_id: str
    opening: str                    # verb | name | fixed
    written: frozenset[str]          # folded forms that mean the text already writes him as a link
    direct_first: frozenset[str]     # fixed-shape works: the only first links he heard directly


@dataclass(frozen=True)
class NamedInFull:
    narrator_id: str
    work: str
    surfaces: frozenset[str]
    detail: str


class WorkRegister:
    def __init__(self, path: Path = REGISTER_PATH):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self.persons = {person["id"]: person for person in self.data["persons"]}
        self.compilers = {
            work: Compiler(work, entry["narrator_id"], entry["opening"], frozenset(fold(f) for f in entry.get("written_forms", [])),
                           frozenset(fold(f) for f in entry.get("direct_first_forms", [])))
            for work, entry in self.data["compilers"].items()}
        self.named_in_full = [NamedInFull(entry["narrator_id"], entry["work"], frozenset(fold(s) for s in entry["surfaces"]),
                                          entry["detail"]) for entry in self.data["named_in_full"]]
        for compiler in self.compilers.values():
            if compiler.opening not in ("verb", "name", "fixed"):
                raise ValueError(f"{compiler.work}: unknown opening rule {compiler.opening!r}")
            if compiler.opening == "fixed" and not compiler.direct_first:
                raise ValueError(f"{compiler.work}: a fixed opening needs direct_first_forms")
        self.reader = _reader_expand()
        self.profiles = {key: value for key, value in json.loads(PROFILES_V3_PATH.read_text(encoding="utf-8")).items()
                         if not key.startswith("_")}
        for work in self.compilers:
            if not self.profiles.get(work, {}).get("compiler_head"):
                raise ValueError(f"{work}: work_register.json heads it with a compiler, work_profiles_v3.json does not")
        overlap = set(self.compilers) & set(self.data["works_without_compiler"])
        if overlap:
            raise ValueError(f"works both with and without a compiler: {sorted(overlap)}")

    def register_ids(self) -> set[str]:
        return {person_id for person_id in self.persons if person_id.startswith("narrator:work:")}

    def narrator_rows(self, arabic_norm) -> list[list]:
        """narrators rows (id, authority, authority_key, scholar_indx, name, name_ar, name_en, name_ar_normalized,
        placeholder_reason, name_latin, name_latin_basis) for the work_register persons."""
        return [[person["id"], "work_register", person["id"].removeprefix("narrator:work:"), None, person["name_ar"],
                 person["name_ar"], person["name_latin"], arabic_norm(person["name_ar"]), None, person["name_latin"],
                 "identity_name"] for person in self.persons.values() if person["id"].startswith("narrator:work:")]

    def profile_rows(self) -> list[list]:
        """narrator_source_profiles rows (narrator_id, source, assertions, licence, label_reason, asserted_by, review_state)."""
        rows = []
        for person in self.persons.values():
            if not person["id"].startswith("narrator:work:"):
                continue
            works = sorted(work for work, entry in self.data["compilers"].items() if entry["narrator_id"] == person["id"])
            works += sorted(entry["work"] for entry in self.data["named_in_full"] if entry["narrator_id"] == person["id"])
            assertions = {"role": person["role"], "tradition": person["tradition"], "works": works,
                          "credited_by": person["credited_by"]}
            if person.get("candidate_records"):
                assertions["candidate_records_not_merged"] = person["candidate_records"]
            if person.get("same_name_rows_not_reused"):
                assertions["same_name_rows_not_reused"] = person["same_name_rows_not_reused"]
            rows.append([person["id"], "work_register", json.dumps(assertions, ensure_ascii=False, sort_keys=True), LICENCE,
                         None, person["credited_by"], "source_unverified"])
        return rows

    def named_person(self, work: str, surface_ar: str) -> NamedInFull | None:
        key = fold(surface_ar)
        for entry in self.named_in_full:
            if entry.work == work and key in entry.surfaces:
                return entry
        return None

    def head(self, work: str, surfaces: Sequence[str], narrator_ids: Iterable[str | None], suspension: str | None,
             opening_text: str) -> tuple[str, str] | None:
        """(compiler narrator id, 'direct' | 'indirect') heading one chain, or None (no compiler, or the text writes him).

        'direct' means the compiler heard position 0: a pair forms. A suspended chain, an opening that says he gives the
        report without his route («وقال», «وروى», «عن»), or a fixed-shape work whose first link is not the fixed one, is
        'indirect': the head is shown, no pair.
        """
        compiler = self.compilers.get(work)
        if compiler is None or not surfaces:
            return None
        # Written already: the reader tool's alias rule (first written link, or any for the Muwatta), the register's own
        # forms, or a standing identity on the compiler's record.
        links = [{"surface": surface, "start": 0, "end": 0, "kind": "narrator"} for surface in surfaces]
        if (self.reader.compiler_written(links, self.profiles[work]) or fold(surfaces[0]) in compiler.written
                or compiler.narrator_id in set(narrator_ids)):
            return None
        if suspension:
            return compiler.narrator_id, "indirect"
        opening = opening_words(opening_text)
        if compiler.opening == "verb":
            direct = bool(DIRECT_VERB.match(opening))
        elif compiler.opening == "name":
            direct = not INDIRECT_OPENING.match(opening)
        else:
            direct = fold(surfaces[0]) in compiler.direct_first
        return compiler.narrator_id, "direct" if direct else "indirect"

    def route_links(self, work: str, reader_text: str, planned_chains: Sequence[dict]) -> list[str | None]:
        """Per planned chain, the compiler's 'direct' | 'indirect' mark from that route's OWN opening words; None for the first
        chain (it keeps the report-opening mark `head` gave it), for a route whose opening cannot be read (no written link) and
        for a co-transmitter joined by «و» before the first alike (None means "as the first chain"; later joined routes repeat
        the mark of the route before them).

        A fix's other routes used to copy the first chain's mark: «وقال الليث» in al-Bukhari then read as heard directly.
        The route's opening is the word(s) between the nearest earlier written link and its first written name (the hearing
        verb or «وقال»), read by the same per-work rule as `head` (verb: the last word must be a hearing verb, alone or after
        «قال»; fixed: its own first link; a name-opening work keeps the report's mark: no verb to read per route)."""
        compiler = self.compilers.get(work)
        spans = [tuple(m["span"]) for chain in planned_chains for m in chain["mentions"] if m.get("span")]
        marks: list[str | None] = []
        previous: str | None = None
        for index, chain in enumerate(planned_chains):
            written = [m for m in chain["mentions"] if m.get("span")]
            if index == 0 or compiler is None or not written or chain["mentions"][0] is not written[0] or compiler.opening == "name":
                marks.append(None)           # a name-opening work (al-Kafi, al-Saduq) has no hearing verb to read per route: the report's mark stands
                continue
            if chain.get("suspension"):
                previous = "indirect"
                marks.append(previous)
                continue
            first_start = written[0]["span"][0]
            boundary = max((end for _, end in spans if end <= first_start), default=0)
            words = opening_words(reader_text[boundary:first_start]).split()
            last = words[-1].strip(":،,.؛-") if words else ""
            surface = written[0]["surface_ar"]
            if compiler.opening == "fixed":
                previous = "direct" if fold(surface) in compiler.direct_first else "indirect"
            elif last in ("", "و", "ف"):
                pass                    # a co-transmitter joined by «و»: shares the opening verb of the route before it
            else:
                candidates = [last, " ".join(words[-2:]).replace(":", " ")]
                previous = "direct" if any(DIRECT_VERB.match(opening_words(candidate)) for candidate in candidates) else "indirect"
            marks.append(previous)
        return marks
