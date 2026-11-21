"""Shared I/O for biography verification: OpenITI entry reader, canonical name key, lexicon loader, paths.

Reads files as text only (downloads are untrusted data). See README.md in this directory.
"""

import csv
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import diagnostic_common as common  # noqa: E402

JOB = "biography-verification"
EXTERNAL = common.DATASETS_DIR / "sources" / "external"
LEXICON = common.REGISTRY_PATH
LEXICON_CANDIDATES = common.DIAGNOSTICS_DIR / "biography-recovery" / "biographical_assertion_candidates.jsonl"
LEXICON_ASSESSMENTS = common.DIAGNOSTICS_DIR / "biography-recovery" / "narrator_assessment_candidates.jsonl"
HADITH_KG = EXTERNAL / "hadith-kg" / "hadith-kg.db"
RIWAYAT = EXTERNAL / "riwayat-corpus" / "hadith_master.db"

WORKS = {
    "ibn_hajar_taqrib": {
        "path": EXTERNAL / "openiti-0852IbnHajar.TaqribTahdhib" / "0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed",
        "tradition": "sunni", "critic": "Ibn Hajar al-Asqalani (d. 852)", "title": "Taqrib al-Tahdhib",
        "openiti_uri": "0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1",
        "entry_markers": ("### $ ", "### $$ "),
    },
    "mizzi_tahdhib_kamal": {
        "path": EXTERNAL / "openiti-0742Mizzi.TahdhibKamal" / "0742Mizzi.TahdhibKamal.Shamela0003722-ara1.mARkdown",
        "tradition": "sunni", "critic": "al-Mizzi (d. 742), reporting earlier critics", "title": "Tahdhib al-Kamal",
        "openiti_uri": "0742Mizzi.TahdhibKamal.Shamela0003722-ara1", "entry_markers": ("### $ ",),
    },
    "najashi_rijal": {
        "path": EXTERNAL / "openiti-0450Najashi.Rijal" / "0450Najashi.Rijal.Shia002931-ara1.mARkdown",
        "tradition": "imami", "critic": "al-Najashi (d. 450)", "title": "Rijal al-Najashi",
        "openiti_uri": "0450Najashi.Rijal.Shia002931-ara1", "entry_markers": ("### $ ",),
    },
    "tusi_rijal": {
        "path": EXTERNAL / "openiti-0460ShaykhTusi.Rijal" / "0460ShaykhTusi.Rijal.Shia002935-ara1.mARkdown",
        "tradition": "imami", "critic": "al-Tusi (d. 460)", "title": "Rijal al-Tusi",
        "openiti_uri": "0460ShaykhTusi.Rijal.Shia002935-ara1", "entry_markers": ("### $ ",),
    },
    "tusi_fihrist": {
        "path": EXTERNAL / "openiti-0460ShaykhTusi.Fihrist" / "0460ShaykhTusi.Fihrist.Shia002934-ara1.mARkdown",
        "tradition": "imami", "critic": "al-Tusi (d. 460)", "title": "al-Fihrist",
        "openiti_uri": "0460ShaykhTusi.Fihrist.Shia002934-ara1", "entry_markers": ("### $ ",),
    },
}

_PAGE = re.compile(r"PageV(\d+)P(\d+)")
_MILESTONE = re.compile(r"\bms\d+\b")
_META = re.compile(r"^#META#\s*([0-9]+\.\w+)\s*::\s*(.*)$")


def openiti_header(path: Path) -> dict:
    """`#META#` header fields (edition, editor, publisher) as recorded by OpenITI."""
    header = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("#META#Header#End"):
                break
            match = _META.match(line.strip())
            if match and match.group(2).strip() != "NODATA":
                header[match.group(1)] = match.group(2).strip()
    return header


def display_text(raw: str) -> str:
    """Markup removed (line joins, page and milestone markers, pipes); characters otherwise as in the file."""
    text = re.sub(r"\n(?:~~|# )", " ", raw)
    text = _PAGE.sub(" ", _MILESTONE.sub(" ", text))
    text = text.replace("|", " ")
    return " ".join(text.split())


class PageIndex:
    """Page lookup by character offset. OpenITI puts `PageVxxPyyy` at the END of page yyy, so the page holding an
    offset is the first marker at or after it."""

    def __init__(self, document: str):
        self.offsets = []
        self.labels = []
        for match in _PAGE.finditer(document):
            self.offsets.append(match.start())
            self.labels.append(f"v{int(match.group(1))}p{int(match.group(2))}")

    def page_at(self, offset: int):
        import bisect
        position = bisect.bisect_left(self.offsets, offset)
        return self.labels[position] if position < len(self.labels) else None


def read_document(work_key: str) -> str:
    return Path(WORKS[work_key]["path"]).read_text(encoding="utf-8", errors="replace")


def read_entries(work_key: str):
    """Yield entries of one work: marker, printed entry number, line, start page, pages spanned, raw and display text.

    `raw_start` is the character offset of the entry in the document, for statement-level page lookups.
    """
    work = WORKS[work_key]
    document = read_document(work_key)
    pages = PageIndex(document)
    heads = [m for m in re.finditer(r"^### .*$", document, flags=re.M)]
    import bisect
    newlines = [m.start() for m in re.finditer("\n", document)]
    for index, head in enumerate(heads):
        line_text = head.group(0)
        marker = next((m for m in work["entry_markers"] if line_text.startswith(m)), None)
        if marker is None:
            continue
        start = head.start()
        end = heads[index + 1].start() if index + 1 < len(heads) else len(document)
        raw = document[start:end].rstrip("\n")
        body = raw[len(marker):]
        number_match = re.match(r"\s*(\d+)", body)
        first_page = pages.page_at(start)
        last_page = pages.page_at(end - 1)
        spanned = pages.labels[bisect.bisect_left(pages.offsets, start):bisect.bisect_left(pages.offsets, end)]
        if first_page and first_page not in spanned:
            spanned.insert(0, first_page)
        if last_page and last_page not in spanned:
            spanned.append(last_page)
        yield {
            "work": work_key,
            "marker": marker.strip(),
            "entry_number": number_match.group(1) if number_match else None,
            "line": bisect.bisect_left(newlines, start) + 1,
            "raw_start": start,
            "start_page": first_page,
            "pages": spanned,
            "raw": raw,
            "text": display_text(body[number_match.end():] if number_match else body),
        }


_REGEN = None


def regen():
    """The canonical pipeline module (name folds, `_extract_arabic_name`, placeholder rule)."""
    global _REGEN
    if _REGEN is None:
        _REGEN = common.load_regen()
    return _REGEN


def name_key(arabic: str) -> str:
    """Canonical comparison key: narrator_fold_normalize + blessing-formula strip, then the guarded kunya fold."""
    module = regen()
    key = module.strip_blessing_formulas(module.narrator_fold_normalize(arabic or ""))
    return module.fold_kunya_case_forms(key) if module.kunya_fold_allowed(key) else key


def load_lexicon() -> list:
    """Lexicon rows with the canonical Arabic name, its key, placeholder reason and generation marker."""
    module = regen()
    rows = []
    with open(LEXICON, encoding="utf-8", newline="") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), 2):
            name = row["name"]
            arabic = module._extract_arabic_name(name)
            generation = re.search(r"\[(\d+)(?:st|nd|rd|th) [Gg]eneration\]", row["grade"] or "")
            rows.append({
                "scholar_indx": row["scholar_indx"].strip(),
                "csv_line": line_number,
                "name_field": name,
                "arabic_name": arabic,
                "key": name_key(arabic),
                "placeholder_reason": module.registry_placeholder_reason(name),
                "grade_marker": row["grade"],
                "generation_number": int(generation.group(1)) if generation else None,
                "generation_class": _generation_class(row["grade"] or ""),
                "row": row,
            })
    return rows


def _generation_class(marker: str) -> str:
    if marker.startswith("Comp."):
        return "companion"
    if marker.startswith("Follower"):
        return "follower"
    if marker.startswith("Succ."):
        return "successor_of_follower"
    if "Century AH" in marker:
        return "century_marker"
    return "other"


def load_lexicon_candidates() -> dict:
    """biography-recovery part A rows (the lexicon's own dates/places with qualifiers), grouped by scholar_indx."""
    grouped: dict = {}
    with open(LEXICON_CANDIDATES, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            grouped.setdefault(row["scholar_indx"], []).append(row)
    return grouped
