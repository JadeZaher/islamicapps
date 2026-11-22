"""Project a validated Neo4j-format bundle into Postgres COPY-ready CSVs (design section 4.4).

Standard library only. Deterministic: rows sorted by primary key, no timestamps, hash-bound manifests.
Rationale and rules: see datasets/hadith-data/pg_export/AGENTS.md.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Sequence

HERE = Path(__file__).resolve().parent
HADITH_DATA_DIR = HERE.parent
DATASETS_DIR = HADITH_DATA_DIR.parent
PROJECT_ROOT = DATASETS_DIR.parent
DIAGNOSTICS_DIR = HADITH_DATA_DIR / "diagnostics"
CORRESPONDENCE_JOB_DIR = DIAGNOSTICS_DIR / "report-correspondence"
GRADING_RECOVERY_DIR = DIAGNOSTICS_DIR / "grading-recovery"
# Reused, never copied: matn_isolation (the matn-column rule) and grading-recovery's non-ruling classification.
for _path in (HADITH_DATA_DIR, DATASETS_DIR, CORRESPONDENCE_JOB_DIR, GRADING_RECOVERY_DIR, DIAGNOSTICS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import external_identity as xid  # noqa: E402
import machine_english  # noqa: E402
from chain_chronology import DEATH_GAP_YEARS as CHRONOLOGY_DEATH_GAP_YEARS  # noqa: E402
from chain_chronology import IRSAL_YEARS as CHRONOLOGY_IRSAL_YEARS  # noqa: E402
from chain_chronology import Lifespan, contest_chain  # noqa: E402
from imam_kunya import ImamKunyaRegister, CONVENTIONS_PATH  # noqa: E402
import chain_builder  # noqa: E402
import chain_structure  # noqa: E402
import chain_fix_projection  # noqa: E402
from work_register import WorkRegister  # noqa: E402
import work_register as work_register_module  # noqa: E402
from mention_text import PlainText, locate_mentions  # noqa: E402
from provider_english import ProviderEnglish  # noqa: E402
from transliteration import latin_name  # noqa: E402
from neo4j_export.contract import (  # noqa: E402
    deterministic_json_bytes,
    graph_content_hash,
    sha256_file,
    typed_column_name,
)

PROJECTION_VERSION = "2026.11.22.14"
CORRESPONDENCE_CLASSES = frozenset({"same_wording", "same_report_variant_wording", "partial_overlap"})
CORRESPONDENCE_SCOPES = frozenset({"same_work", "cross_work_same_tradition", "cross_tradition"})
ATTRIBUTION_DISCLAIMER = (
    "kathrat al-riwaya describes transmission volume only; it is not a judgment "
    "of narrator reliability or hadith authenticity."
)
TRADITION_GRADE_SCHEMES = {
    "Sunni": "sunni_7tier",
    "Imami": "imami_4tier",
    "Zaydi": "zaydi_3tier",
    "Ibadi": "ibadi_2tier",
}
NARRATION_LEVELS = {"marfu", "imam", "mawquf", "maqtu", "unknown"}
# Bundle translation review_state -> translations.state (section 5.3); the raw value is kept in review_state_raw.
TRANSLATION_STATE_MAP = {
    "human_verified": "human_verified",
    "source_verified": "source_verified",
    "source_provided": "source_provided",
    "source_status_unknown": "source_provided",
}
PURE_CANON_INCLUSION_LABEL = "ثابت"
PLACEHOLDER_GRADES = {"", "no_extant_evaluation"}
ARABIC_LETTER = re.compile(r"[؀-ۿ]")
ENGLISH_BEFORE_ARABIC = re.compile(r"^(.*?)\s*\(\s*[؀-ۿ]")
# JS `\b` is ASCII-only; Python's is Unicode. Explicit ASCII lookarounds keep parity with io.ts parseHijriYear.
BEFORE_HIJRA = re.compile(r"(?<![A-Za-z0-9_])BH(?![A-Za-z0-9_])", re.IGNORECASE)
CITATION_VOLUME_PAGE = re.compile(r"^(.*\S)\s*\(\s*([^()/]+?)\s*/\s*([^()/]+?)\s*\)$")
ARRAY_ELEMENT = re.compile(r"^[a-z_]+$")
UNRESOLVED = (None, "unresolved", None, None, None)
# The only automatic identity that stands (machine-reviewed, never "verified"): an uncontested
# source_index_confirmed_by_text candidate (AGENTS.md).
VERIFIED_RESOLUTION = ("source_index", "source_index", 1.0, "source_index_confirmed_by_text")
VERIFIED_BASES = frozenset({"source_index_confirmed_by_text"})
# A kunya-only match is shown as a label beside other candidates and never contests a standing identity (owner 2026-11-21).
NON_CONTESTING_BASES = frozenset({"name_kunya_only"})
SOURCE_BASES = frozenset({"source_index", "source_index_confirmed_by_text"})
NAME_BASIS_BY_TIER = {"tier0": "name_exact", "tier1": "name_spelling_fold", "tier2": "name_spelling_fold"}
# Owner decision (c): automatic name matches against the (Sunni-centred) lexicon only on Sunni reports.
NAME_MATCH_TRADITIONS = frozenset({"Sunni"})
K6_CONFIRMED_BASIS = "source_index_corroborated_by_text"   # the K6 sidecar's report-level basis label
IMAMI_ENGLISH_LEXICON = DIAGNOSTICS_DIR / "chain-reconciliation" / "output" / "imami_surface_lexicon.jsonl.gz"
# Honorific symbols an English translation writes as one character (ﷺ, ﷻ, ﷽ and the small marks ؐ-ؓ): not Arabic text.
HONORIFIC_SYMBOLS = re.compile(r"[\ufdfa\ufdfb\ufdfd\u0610-\u0613]")
ARABIC_SCRIPT = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]")
MODULE_FILES = ("transliteration.py", "mention_text.py", "imam_kunya.py", "external_identity.py", "provider_english.py",
                "chain_chronology.py", "chain_builder.py", "opening_isnad_rules.json", "edition_identifications.json",
                "chain_structure.py", "machine_english.py", "work_register.py", "work_register.json",
                "chain_fix_projection.py")
RECONCILED_SIDECARS = ("k6_source_index.jsonl.gz", "pure_canon_chain.jsonl.gz", "no_chain_in_source.jsonl.gz")
MAX_SAFE_INTEGER = 2**53 - 1
OPENING_ISNAD_LICENCE = ("Shura wa Istehsan register (opening_isnad_rules.json); the name as the work's opening isnad writes "
                         "it, OpenITI text (CC BY-NC-SA 4.0)")
# The lexicon's descriptive fields kept verbatim in narrator_lexicon_profiles.source_fields (never a reliability label).
LEXICON_SOURCE_FIELDS = ("places_of_stay", "parents", "spouse", "siblings", "children", "tags", "area_of_interest")
LEXICON_BRACKETED = re.compile(r"\s*\[[^\]]*\]")
INT4_MAX = 2**31 - 1

_csv_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit(_csv_limit)
        break
    except OverflowError:
        _csv_limit //= 10


class ProjectionError(ValueError):
    """Raised when an input fails a refusal condition; nothing is written as complete."""


# ─── Pure projection rules (table-tested in test_export_postgres.py) ──────────────────────────────


def blank_to_none(value: str | None) -> str | None:
    """Unknown is NULL: blank and whitespace-only cells load as NULL; other text is kept as written."""
    if value is None or value.strip() == "":
        return None
    return value


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_exact_safe_integer(value: str | None) -> int | None:
    """Port of io.ts parseExactSafeIntegerOrNull: only an exact ASCII integer token."""
    token = (value or "").strip()
    if not re.fullmatch(r"[+-]?\d+", token, re.ASCII):
        return None
    number = int(token)
    return number if abs(number) <= MAX_SAFE_INTEGER else None


def parse_hijri_year(raw_year: str | None, *context: str | None) -> int | None:
    """Port of io.ts parseHijriYear: a 'BH' token anywhere in the date context makes the year negative."""
    year = parse_exact_safe_integer(raw_year)
    if year is None:
        return None
    before_hijra = any(BEFORE_HIJRA.search(value or "") for value in (raw_year, *context))
    return -abs(year) if before_hijra else year


def int4_or_none(value: int | None) -> int | None:
    return value if value is not None and -INT4_MAX - 1 <= value <= INT4_MAX else None


def english_name(lexicon_name: str) -> str | None:
    """The lexicon `name` reads 'English ( Arabic ( honorific'; the English part is what precedes the Arabic block."""
    match = ENGLISH_BEFORE_ARABIC.match(lexicon_name)
    if match:
        return blank_to_none(match.group(1).strip())
    return None if ARABIC_LETTER.search(lexicon_name) else blank_to_none(lexicon_name.strip())


def lexicon_source_fields(row: dict[str, str]) -> str | None:
    """The lexicon's descriptive fields as compact JSON; tags and interests lose their brackets (slugs, a [Grade:] label)."""
    fields = {}
    for name in LEXICON_SOURCE_FIELDS:
        value = (row.get(name) or "").strip()
        if name in ("tags", "area_of_interest"):
            value = ", ".join(part.strip() for part in LEXICON_BRACKETED.sub("", value).split(",") if part.strip())
        if value and value != "NA":
            fields[name] = value
    return json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")) if fields else None


def _normalise_grade_text(value: str) -> str:
    """Port of grade-taxonomy.ts normaliseArabic."""
    value = re.sub(r"\s+", " ", value).strip()
    value = value.replace("ی", "ي").replace("ک", "ك")
    value = re.sub(r"ة\s", "ة ", value)
    return value.replace("‌", "").replace("‍", "")


GRADE_EXACT = {
    "": "ungraded", "null": "ungraded",
    "thabit": "sahih", "sahih": "sahih", "daif": "da_if", "hasan": "hasan",
    "صحيح": "sahih", "حسن": "hasan", "موثق": "muwaththaq", "ضعيف": "da_if", "مجهول": "majhul",
    "مرسل": "mursal", "معتبر": "mu_tabar", "مختلف فيه": "mukhtalaf", "مرفوع": "mursal", "مضمر": "mursal",
    "حسن كالصحيح": "sahih", "موثق كالصحيح": "sahih", "مجهول كالصحيح": "sahih", "صحيح على الظاهر": "sahih",
    "حسن على الظاهر": "hasan", "مرسل كالموثق": "muwaththaq", "حسن او موثق": "hasan", "حسن أو موثق": "hasan",
    "ضعيف على المشهور": "da_if", "ضعيف على الشهور": "da_if", "ضعيف على المشهور معتبر عند ي": "mu_tabar",
    "سكت عنه": "ungraded", "لم يخرجه": "ungraded",
}
GRADE_CONTAINS = [
    ("ساقط", "mawdu"), ("موضوع", "mawdu"), ("كالصحيح", "sahih"), ("معتبر", "mu_tabar"), ("مختلف", "mukhtalaf"),
    ("صحيح", "sahih"), ("حسن", "hasan"), ("موثق", "muwaththaq"), ("مجهول", "majhul"), ("مرسل", "mursal"),
    ("مرفوع", "mursal"), ("مضمر", "mursal"), ("ضعيف", "da_if"),
    ("sahih", "sahih"), ("hasan", "hasan"), ("daif", "da_if"), ("thabit", "sahih"),
]


def map_to_canonical(display_grade: str | None) -> str:
    """Port of grade-taxonomy.ts mapToCanonical: exact map, then first contains rule, else 'ungraded'."""
    if display_grade is None:
        return "ungraded"
    normalised = _normalise_grade_text(display_grade)
    lower = normalised.lower()
    if normalised in GRADE_EXACT:
        return GRADE_EXACT[normalised]
    if lower in GRADE_EXACT:
        return GRADE_EXACT[lower]
    for pattern, canonical in GRADE_CONTAINS:
        if pattern in normalised or pattern.lower() in lower:
            return canonical
    return "ungraded"


def clean_grade_detail(display_grade: str | None) -> str:
    """Port of grade-taxonomy.ts cleanGradeDetail."""
    if not display_grade:
        return ""
    cleaned = _normalise_grade_text(display_grade)
    for broken, fixed in (("الظاه\\s+ر", "الظاهر"), ("المشهو\\s+ر", "المشهور"), ("الصحي\\s+ح", "الصحيح"),
                          ("المعتب\\s+ر", "المعتبر"), ("الموث\\s+ق", "الموثق")):
        cleaned = re.sub(broken, fixed, cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_gradings_full(value: str) -> tuple[list[dict], int]:
    """Port of assessment.ts parseGradingsFull. Returns (entries, skipped malformed segments)."""
    if not value or not value.strip():
        return [], 0
    entries: list[dict] = []
    skipped = 0
    for segment in value.split(" | "):
        colon = segment.find(":")
        if colon == -1:
            skipped += 1
            continue
        scholar = segment[:colon].strip()
        rest = segment[colon + 1:].strip()
        grade, citation = rest, ""
        last_close = rest.rfind(")")
        if last_close != -1:
            depth, open_index = 0, -1
            for index in range(last_close, -1, -1):
                if rest[index] == ")":
                    depth += 1
                elif rest[index] == "(":
                    depth -= 1
                    if depth == 0:
                        open_index = index
                        break
            if open_index != -1:
                grade = rest[:open_index].strip()
                citation = rest[open_index + 1:last_close].strip()
        if not scholar or not grade:
            skipped += 1
            continue
        entries.append({"scholar": scholar, "grade": grade, "citation": citation})
    return entries, skipped


def split_citation(citation: str | None) -> tuple[str | None, str | None, str | None]:
    """'Mir'at al-'Uqul (1/25)' -> (work, volume, page); a bare title -> (title, None, None)."""
    citation = blank_to_none(citation)
    if citation is None:
        return None, None, None
    match = CITATION_VOLUME_PAGE.match(citation)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return citation, None, None


def review_unit_ids(surface: str, teacher: str | None, student: str | None, source_work_id: str) -> tuple[str, str]:
    """Coarse and fine review-unit keys (section 4.2): SHA-256 over \\x1f-joined parts, NULL context as ''."""
    coarse = sha256_text("\x1f".join((surface, teacher or "", source_work_id)))
    fine = sha256_text("\x1f".join((surface, teacher or "", student or "", source_work_id)))
    return coarse, fine


def align_source_index(row: dict, branches: Sequence[Sequence[str]]) -> dict[tuple[int, int], tuple[int, bool]] | None:
    """(branch, position) -> (source position, shared_trunk) for every position the K6 sidecar corroborated.

    None when the sidecar's text branches are not exactly the extracted branches (then no position is mapped).
    In a multi-branch report an uncorroborated position inherits the source position of a corroborated twin whose
    branch opens with the identical surfaces up to and including it: the same tahwil trunk written once in the
    Arabic. Convergence (shared endings) is not inherited: a relational surface such as أبيه there may name
    different people.
    """
    if [list(branch) for branch in (row.get("text_branches") or [])] != [list(branch) for branch in branches]:
        return None
    aligned: dict[tuple[int, int], tuple[int, bool]] = {}
    for item in row.get("aligned_positions") or []:
        key = (int(item["branch"]), int(item["branch_position"]))
        if key in aligned:
            raise ProjectionError(f"{row['record_id']}: aligned position {key} listed twice")
        aligned[key] = (int(item["source_position"]), False)
    inherited: dict[tuple[int, int], tuple[int, bool]] = {}
    for branch_index, surfaces in enumerate(branches):
        for position in range(len(surfaces)):
            if (branch_index, position) in aligned:
                continue
            for (twin_branch, twin_position), (source_position, _) in sorted(aligned.items()):
                if (twin_branch != branch_index and twin_position == position
                        and list(branches[twin_branch][:position + 1]) == list(surfaces[:position + 1])):
                    inherited[(branch_index, position)] = (source_position, True)
                    break
    aligned.update(inherited)
    return aligned


def verified_narrator(candidates: Sequence[tuple[str, str]]) -> str | None:
    """The machine-reviewed identity a mention's (narrator_id, basis) candidates give it (`narrator_id`), or None.

    Stands only when a source_index_confirmed_by_text candidate exists and no other candidate names a different
    narrator: a contested identity is shown with both candidates and is never presented as settled. A kunya-only
    candidate is a label, never a contest (owner decision 2026-11-21).
    """
    confirmed = {narrator for narrator, basis in candidates if basis in VERIFIED_BASES}
    if len(confirmed) != 1:
        return None
    contesting = {narrator for narrator, basis in candidates if basis not in NON_CONTESTING_BASES}
    return next(iter(confirmed)) if contesting == confirmed else None


MACHINE_ENGLISH_OVERLAY = HADITH_DATA_DIR / "machine_translation_candidates" / "machine_english_overlay.jsonl.gz"
TRANSLATION_PIN = HADITH_DATA_DIR / "translation_model.json"


def machine_english_input(args: argparse.Namespace) -> dict | None:
    """The overlay file as the manifest binds it (None when there is none)."""
    path = args.machine_english
    if path is None or not path.is_file():
        return None
    return {"path": display_path(path), "sha256": sha256_file(path), "pinned_model": json.loads(TRANSLATION_PIN.read_text(encoding="utf-8"))["model_id"]}


def machine_english_rows(args: argparse.Namespace, translations: list[list], hadith_info: dict, hadith_text: dict,
                         record_to_hadith: dict) -> tuple[list[list], dict]:
    """Machine English for reports with no usable source English (state machine_unreviewed; source-provided wins)."""
    bound = machine_english_input(args)
    if bound is None:
        return translations, {"overlay": None}
    candidates = machine_english.read_overlay(args.machine_english)
    rows, report = machine_english.overlay_translations(translations, hadith_info, hadith_text, record_to_hadith, candidates,
                                                       bound["pinned_model"])
    return rows, {"overlay": bound["path"], **report}


def english_quality(status: str, text: str) -> str:
    """The bundle's quality status, except that an English text whose only Arabic-script characters are honorific
    symbols (ﷺ) is complete: the symbol is the translator's typography, not Arabic left in the English."""
    if status == "arabic_leakage" and not ARABIC_SCRIPT.search(HONORIFIC_SYMBOLS.sub("", text)):
        return "complete"
    return status


def candidate_agreement(narrator_ids: Iterable[str]) -> str:
    """How a mention's candidates relate: 'none', 'one' (one narrator, any number of bases) or 'differ'."""
    distinct = set(narrator_ids)
    return "none" if not distinct else "one" if len(distinct) == 1 else "differ"


def candidate_id(mention_id: str, basis: str, narrator_id: str) -> str:
    return f"candidate:{mention_id.removeprefix('mention:')}:{basis}:{narrator_id.removeprefix('narrator:')}"


def pg_array(values: Iterable[str]) -> str:
    items = list(values)
    for item in items:
        if not ARRAY_ELEMENT.match(item):
            raise ProjectionError(f"array element needs quoting: {item!r}")
    return "{" + ",".join(items) + "}"


class Verbatim(str):
    """Text written as is, even when empty: a computed value that is genuinely '' (not unknown)."""


def cell(value: object) -> str | None:
    """CSV cell for COPY (format csv): None stays unquoted-empty (NULL); everything else is quoted text."""
    if value is None:
        return None
    if isinstance(value, Verbatim):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    text = str(value)
    return None if text == "" else text


# ─── IO helpers ───────────────────────────────────────────────────────────────────────────────────


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("rt", encoding="utf-8-sig", newline="")


class Bundle:
    """A validated Neo4j-format bundle; every file is hash-checked against its manifest before use."""

    def __init__(self, directory: Path):
        self.directory = directory
        manifest_path = directory / "manifest.json"
        report_path = directory / "validation_report.json"
        if not manifest_path.is_file() or not report_path.is_file():
            raise ProjectionError("bundle lacks manifest.json or validation_report.json")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("import_ready") is not True:
            raise ProjectionError("bundle validation report does not say import_ready: true")
        if report.get("content_sha256") != self.manifest.get("content_sha256"):
            raise ProjectionError("validation report and manifest name different content_sha256")
        self.files = {item["path"]: item for item in self.manifest["files"]}
        for item in [*self.manifest["files"], *self.manifest.get("support_files", [])]:
            path = directory / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
                raise ProjectionError(f"bundle file does not match its manifest: {item['path']}")
        recomputed = graph_content_hash(self.manifest["files"], self.manifest.get("support_files", []))
        if recomputed != self.manifest["content_sha256"]:
            raise ProjectionError("bundle content_sha256 does not match its files")

    def input_sha256(self, role: str) -> str | None:
        for item in self.manifest.get("inputs", []):
            if item.get("role") == role:
                return item["sha256"]
        return None

    def rows(self, relative_path: str) -> Iterator[dict[str, str]]:
        """Rows keyed by property name; relationship endpoints as 'start'/'end'; :LABEL/:TYPE dropped."""
        spec = self.files[relative_path]
        count = 0
        with (self.directory / relative_path).open("rt", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            if header != spec["header"]:
                raise ProjectionError(f"{relative_path}: header differs from manifest")
            names = []
            for column in header:
                if column.startswith(":START_ID"):
                    names.append("start")
                elif column.startswith(":END_ID"):
                    names.append("end")
                elif column.startswith(":"):
                    names.append(None)
                else:
                    names.append(typed_column_name(column))
            for values in reader:
                count += 1
                yield {name: value for name, value in zip(names, values) if name is not None}
        if count != spec["row_count"]:
            raise ProjectionError(f"{relative_path}: {count} rows, manifest says {spec['row_count']}")

    def one_to_one(self, relative_path: str) -> dict[str, str]:
        """A relationship file with exactly one row per start node, as start -> end."""
        mapping: dict[str, str] = {}
        for row in self.rows(relative_path):
            if row["start"] in mapping:
                raise ProjectionError(f"{relative_path}: {row['start']} has more than one row")
            mapping[row["start"]] = row["end"]
        return mapping


class TableWriter:
    """Writes one sorted COPY CSV per table and records its manifest entry."""

    def __init__(self, output_dir: Path, stream: str, catalog: dict | None):
        self.output_dir = output_dir / stream
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.stream = stream
        self.catalog = catalog
        self.files: list[dict] = []

    def write(self, table: str, header: list[str], rows: list[list[object]], key_width: int = 1) -> None:
        if self.catalog is not None:
            check_header(self.catalog, table, header)
        rows.sort(key=lambda row: tuple(str(value) for value in row[:key_width]))
        not_null = [index for index, name in enumerate(header) if name in not_null_columns(self.catalog, table)]
        keys = set()
        for row in rows:
            if len(row) != len(header):
                raise ProjectionError(f"{table}: row width {len(row)} != header {len(header)}")
            for index in not_null:
                if cell(row[index]) is None:
                    raise ProjectionError(
                        f"schema/data mismatch: {table}.{header[index]} is NOT NULL but row {row[0]!r} has no value")
            key = tuple(row[:key_width])
            if key in keys:
                raise ProjectionError(f"{table}: duplicate key {key}")
            keys.add(key)
        path = self.output_dir / f"{table}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, dialect="excel", lineterminator="\n", quoting=csv.QUOTE_NOTNULL)
            writer.writerow(header)
            for row in rows:
                writer.writerow([cell(value) for value in row])
        self.files.append({
            "path": f"{self.stream}/{table}.csv",
            "table": table,
            "header": header,
            "row_count": len(rows),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })


def not_null_columns(catalog: dict | None, table: str) -> set[str]:
    if catalog is None:
        return set()
    return {column["name"] for column in catalog.get(table, []) if column.get("nullable") is False}


def check_header(catalog: dict, table: str, header: list[str]) -> None:
    """The CSV header must equal, as a set, the live columns the catalog marks `csv` (information_schema)."""
    if table not in catalog:
        raise ProjectionError(f"catalog has no table {table}")
    expected = {column["name"] for column in catalog[table] if column["role"] == "csv"}
    actual = set(header)
    if actual != expected or len(actual) != len(header):
        raise ProjectionError(
            f"{table}: header mismatch with live catalog; extra={sorted(actual - expected)} "
            f"missing={sorted(expected - actual)}"
        )


# ─── Projection ───────────────────────────────────────────────────────────────────────────────────


def load_unified(path: Path) -> dict[str, dict[str, str]]:
    columns = (
        "record_id", "hadith_id", "source_display_label", "volume", "chapter_no", "chapter", "category", "school",
        "chain_type", "narration_level", "sanad_confidence", "provenance_source", "tradition", "grade_tradition",
        "grade_source", "grade_value", "gradings_full", "text_en", "matn_en", "translation_source",
        "translation_model", "translation_review_status", "translation_status",
    )
    rows: dict[str, dict[str, str]] = {}
    with open_text(path) as handle:
        for row in csv.DictReader(handle):
            record_id = row["record_id"].strip()
            if not record_id or record_id in rows:
                raise ProjectionError(f"unified CSV record_id blank or duplicated: {record_id!r}")
            rows[record_id] = {column: row[column] for column in columns}
    return rows


def load_openiti_extraction(directory: Path) -> tuple[dict[str, dict], str]:
    """Report structure of the OpenITI works by record_id, hash-checked against its build manifest."""
    manifest = json.loads((directory / "openiti_extraction.manifest.json").read_text(encoding="utf-8"))
    path = directory / "openiti_extraction.jsonl.gz"
    digest = sha256_file(path)
    if digest != manifest["outputs"][0]["sha256"]:
        raise ProjectionError("reconciled/openiti_extraction.jsonl.gz: SHA-256 differs from its build manifest")
    rows: dict[str, dict] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["record_id"] in rows:
                raise ProjectionError(f"reconciled/openiti_extraction.jsonl.gz: {row['record_id']} listed twice")
            rows[row["record_id"]] = row
    return rows, digest


def load_reconciled_sidecars(directory: Path) -> tuple[dict[str, dict[str, dict]], dict[str, str], str | None]:
    """The three reconciled sidecars keyed by record_id, each file hash-checked against its build manifest.

    Returns (rows by file, file SHA-256 by file, the resolver SHA-256 the K6 corroboration was computed with).
    """
    k6_manifest = json.loads((directory / "k6_source_index.manifest.json").read_text(encoding="utf-8"))
    canon_manifest = json.loads((directory / "pure_canon_chain.manifest.json").read_text(encoding="utf-8"))
    expected = {k6_manifest["output"]["file"]: k6_manifest["output"]["sha256"]}
    expected.update({item["file"]: item["sha256"] for item in canon_manifest["outputs"]})
    loaded: dict[str, dict[str, dict]] = {}
    hashes: dict[str, str] = {}
    for name in RECONCILED_SIDECARS:
        path = directory / name
        if not path.is_file():
            raise ProjectionError(f"reconciled/{name} is missing; rebuild it with its script (reconciled/README.md)")
        digest = sha256_file(path)
        if digest != expected.get(name):
            raise ProjectionError(f"reconciled/{name}: SHA-256 differs from its build manifest")
        rows: dict[str, dict] = {}
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if row["record_id"] in rows:
                    raise ProjectionError(f"reconciled/{name}: {row['record_id']} listed twice")
                rows[row["record_id"]] = row
        loaded[name], hashes[name] = rows, digest
    return loaded, hashes, k6_manifest["code_sha256"].get("datasets/hadith-data/regen_unified_csvs.py")


def apply_chain_sidecars(branches_by_hadith: dict[str, list[dict]], no_chain: dict[str, dict],
                         pure_canon: dict[str, dict], hadith_info: dict[str, dict],
                         record_to_hadith: dict[str, str], normalize) -> Counter:
    """Drop chains the source does not have, and replace Pure Canon chains extracted from matn-only `text_ar` with
    the extraction of the source's own chain field. Both sidecars must be bound to the hadith's exact Arabic."""
    counts: Counter = Counter()
    for record_id, row in sorted(no_chain.items()):
        hadith_id = record_to_hadith.get(record_id)
        if hadith_id is None:
            counts["no_chain_in_source:record_not_in_bundle"] += 1
            continue
        if row["text_ar_sha256"] != hadith_info[hadith_id]["arabic_sha256"]:
            raise ProjectionError(f"{record_id}: no_chain_in_source sidecar is bound to different Arabic")
        if row.get("suppress_extracted_chain") is not True:
            counts[f"no_chain_in_source:{row['reason']}:kept"] += 1
            continue
        removed = branches_by_hadith.pop(hadith_id, [])
        counts[f"no_chain_in_source:{row['reason']}:reports"] += 1
        counts[f"no_chain_in_source:{row['reason']}:invented_chains_dropped"] += len(removed)
    for record_id, row in sorted(pure_canon.items()):
        hadith_id = record_to_hadith.get(record_id)
        if hadith_id is None:
            counts["pure_canon_chain:record_not_in_bundle"] += 1
            continue
        if record_id in no_chain:
            raise ProjectionError(f"{record_id}: both a source chain and no_chain_in_source")
        if row["text_ar_sha256"] != hadith_info[hadith_id]["arabic_sha256"]:
            raise ProjectionError(f"{record_id}: pure_canon_chain sidecar is bound to different Arabic")
        counts["pure_canon_chain:text_ar_chains_replaced"] += len(branches_by_hadith.pop(hadith_id, []))
        branches = [branch for branch in (row.get("branches") or []) if branch]
        for index, surfaces in enumerate(branches):
            branches_by_hadith.setdefault(hadith_id, []).append({
                "id": f"chain:{record_id}:{index:04d}", "branch": index, "resolved": False,
                "extraction_method": "source_chain_field", "sanad_confidence": None,
                "mentions": [(f"mention:{record_id}:{index:04d}:{position:04d}", surface, normalize(surface))
                             for position, surface in enumerate(surfaces)],
            })
        counts["pure_canon_chain:reports_with_source_chain" if branches
               else "pure_canon_chain:reports_without_extracted_narrator"] += 1
        counts["pure_canon_chain:chains"] += len(branches)
    return counts


def matn_isolator():
    """report-correspondence's MatnIsolator with no sidecars, so `isolate` applies only its matn-column rule."""
    import extract_isnad_unified
    import matn_isolation
    return matn_isolation.MatnIsolator(extract_isnad_unified, {}, {})


def accepted_matn(isolator, record_id: str, text_ar: str, matn_ar: str | None) -> tuple[str | None, str | None]:
    """(matn to store, rejection reason). The column is stored only when matn_isolation accepts it as this report's
    own matn: its letters occur inside the report's own text and it does not start where the text starts with a chain."""
    if matn_ar is None or not matn_ar.strip():
        return None, None
    import matn_isolation
    _, method, _, note = isolator.isolate({"record_id": record_id, "text_ar": text_ar, "matn_ar": matn_ar})
    if method == matn_isolation.METHOD_MATN_COLUMN:
        return matn_ar, None
    return None, note or "matn_column_rejected"


def non_ruling_reason(grade: str) -> str | None:
    """grading-recovery's classification of a gradings_full term that is not a ruling (`لم يخرجه`, `سكت عنه`, ...)."""
    from build_hadith_assessment_rows import NON_RULING_CLASSES, fold
    return NON_RULING_CLASSES.get(fold(grade))


def correspondence_pair_id(hadith_id_a: str, hadith_id_b: str) -> str:
    return "report-pair:" + hashlib.sha256(f"{hadith_id_a}\x1f{hadith_id_b}".encode("utf-8")).hexdigest()[:20]


def project_correspondences(directory: Path, hadith_info: dict[str, dict], input_sha: str
                            ) -> tuple[list[list[object]], list[list[object]], dict, dict]:
    """Candidate pairs and cluster members from the report-correspondence output, bound to each side's Arabic.

    A pair whose report is gone or whose Arabic hash differs from the loaded text is dropped and counted, never loaded.
    Returns (candidate rows, member rows, counts, input hashes)."""
    pairs_path = directory / "report_correspondence_pairs.csv"
    members_path = directory / "report_correspondence_cluster_members.csv"
    summary_path = directory / "summary.json"
    for path in (pairs_path, members_path, summary_path):
        if not path.is_file():
            raise ProjectionError(f"{display_path(path)} is missing; rebuild it with "
                                  "diagnostics/report-correspondence/build_report_correspondence.py")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    built_on = [digest for name, digest in summary["inputs_sha256"].items() if name.endswith(".incomplete.csv.gz")]
    if built_on != [input_sha]:
        raise ProjectionError("report-correspondence output was built from another unified CSV than --input")
    method = summary["parameters"]["method_version"]
    counts: Counter = Counter()
    candidates: list[list[object]] = []
    with pairs_path.open("rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            a, b = row["hadith_id_a"], row["hadith_id_b"]
            if not a < b or row["pair_id"] != correspondence_pair_id(a, b) or row["method_version"] != method:
                raise ProjectionError(f"{row['pair_id']}: pair id, order or method version is inconsistent")
            if (row["class"] not in CORRESPONDENCE_CLASSES or row["scope"] not in CORRESPONDENCE_SCOPES
                    or row["basis"] != "textual_overlap"):
                raise ProjectionError(f"{row['pair_id']}: class, scope or basis outside the enums")
            if a not in hadith_info or b not in hadith_info:
                counts["pairs_dropped:report_not_loaded"] += 1
                continue
            if (row["arabic_sha256_a"] != hadith_info[a]["arabic_sha256"]
                    or row["arabic_sha256_b"] != hadith_info[b]["arabic_sha256"]):
                counts["pairs_dropped:arabic_hash_changed"] += 1
                continue
            counts[f"pairs:{row['class']}"] += 1
            counts[f"scope:{row['scope']}"] += 1
            candidates.append([
                row["pair_id"], a, b, row["arabic_sha256_a"], row["arabic_sha256_b"], row["class"],
                float(row["jaccard"]), float(row["containment"]), float(row["global_containment"]),
                float(row["length_ratio"]), int(row["shared_shingles"]), int(row["shingles_a"]),
                int(row["shingles_b"]), int(row["words_a"]), int(row["words_b"]), row["score_band"], row["scope"],
                row["matn_split_a"], row["matn_split_b"], row["cluster_id"], row["basis"], method,
            ])
    members: list[list[object]] = []
    with members_path.open("rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["method_version"] != method:
                raise ProjectionError(f"{row['hadith_id']}: cluster member of another method version")
            if row["hadith_id"] not in hadith_info or row["star_centre"] not in hadith_info:
                counts["members_dropped:report_not_loaded"] += 1
                continue
            members.append([method, row["hadith_id"], row["cluster_id"], row["star_centre"],
                            row["is_star_centre"] == "True"])
    counts["pairs_loaded"] = len(candidates)
    counts["cluster_members_loaded"] = len(members)
    counts["clusters"] = len({row[2] for row in members})
    hashes = {"pairs_sha256": sha256_file(pairs_path), "cluster_members_sha256": sha256_file(members_path),
              "summary_sha256": sha256_file(summary_path), "method_version": method}
    return candidates, members, dict(sorted(counts.items())), hashes


def project(args: argparse.Namespace) -> dict:
    import regen_unified_csvs as resolver_module  # the canonical exact resolver (name invariant, tiers 0-2)
    from classify_attribution import _norm as arabic_norm

    output_dir: Path = args.output
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ProjectionError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))

    bundle = Bundle(args.bundle)
    input_sha = sha256_file(args.input)
    if input_sha != bundle.input_sha256("schema_v2_dataset"):
        raise ProjectionError("unified CSV SHA-256 differs from the bundle manifest's input dataset hash")
    rawis_sha = sha256_file(args.rawis)
    if rawis_sha != bundle.input_sha256("rawi_registry"):
        raise ProjectionError("rawi CSV SHA-256 differs from the bundle manifest")
    if not args.legacy_master.is_file():
        raise ProjectionError("legacy master is required (its hash is recorded on dataset_versions)")
    legacy_sha = sha256_file(args.legacy_master)
    registry = json.loads((args.bundle / "source_work_registry.json").read_text(encoding="utf-8"))

    counts: dict = {}
    canonical = TableWriter(output_dir, "canonical", catalog)
    candidates = TableWriter(output_dir, "candidates", None)
    unified = load_unified(args.input)

    # traditions, sources
    traditions = []
    tradition_names: dict[str, str] = {}
    for row in bundle.rows("nodes/traditions.csv"):
        if row["name"] not in TRADITION_GRADE_SCHEMES:
            raise ProjectionError(f"unknown tradition {row['name']!r}")
        tradition_names[row["id"]] = row["name"]
        traditions.append([row["id"], row["name"], None, row["normalized_name"], TRADITION_GRADE_SCHEMES[row["name"]]])
    canonical.write("traditions", ["id", "code", "name_arabic", "normalized_name", "grade_scheme"], traditions)
    sources = [[r["id"], r["slug"], r["name"], r["release_state"]] for r in bundle.rows("nodes/sources.csv")]
    canonical.write("sources", ["id", "slug", "name", "release_state"], sources)

    # collections
    sort_keys = {work["source_work_id"]: index + 1 for index, work in enumerate(registry["source_works"])}
    collection_tradition = bundle.one_to_one("relationships/collection_in_tradition.csv")
    collection_source = bundle.one_to_one("relationships/collection_from_source.csv")
    collections = []
    collection_by_id: dict[str, dict] = {}
    for row in bundle.rows("nodes/collections.csv"):
        tradition_id = collection_tradition[row["id"]]
        if tradition_names[tradition_id] != row["tradition"] or collection_source[row["id"]] != row["source_id"]:
            raise ProjectionError(f"collection {row['id']} node and relationships disagree")
        collection_by_id[row["id"]] = {"tradition_id": tradition_id, "sort_key": sort_keys[row["source_work_id"]],
                                       "source_work_id": row["source_work_id"]}
        collections.append([row["id"], row["source_work_id"], row["slug"], row["name"], None,
                            sort_keys[row["source_work_id"]], tradition_id, row["source_id"], None, None,
                            registry["registry_version"]])
    canonical.write("collections", ["id", "source_work_id", "slug", "name", "name_arabic", "sort_key", "tradition_id",
                                    "source_id", "compiler_name", "bibliographic_work_id", "registry_version"],
                    collections)

    # books, chapters
    book_collection = bundle.one_to_one("relationships/book_in_collection.csv")
    books = []
    for row in bundle.rows("nodes/books.csv"):
        if book_collection[row["id"]] != row["collection_id"]:
            raise ProjectionError(f"book {row['id']} collection disagrees")
        books.append([row["id"], row["collection_id"], blank_to_none(row["number"]), blank_to_none(row["name"]),
                      blank_to_none(row["volume"]), blank_to_none(row["provider_file_id"]),
                      blank_to_none(row["provider_book_id"])])
    canonical.write("books", ["id", "collection_id", "number", "name", "volume", "provider_file_id",
                              "provider_book_id"], books)
    chapter_book = bundle.one_to_one("relationships/chapter_in_book.csv")
    chapters = []
    for row in bundle.rows("nodes/chapters.csv"):
        book_id = blank_to_none(row["book_id"])
        if chapter_book.get(row["id"]) != book_id:
            raise ProjectionError(f"chapter {row['id']} book disagrees")
        name = blank_to_none(row["name"])
        chapters.append([row["id"], row["collection_id"], book_id, blank_to_none(row["number"]),
                         blank_to_none(row["category_number"]), name, name.lower() if name else None,
                         blank_to_none(row["provider_chapter_locator"])])
    canonical.write("chapters", ["id", "collection_id", "book_id", "number", "category_number", "name", "name_folded",
                                 "provider_chapter_locator"], chapters)

    # hadiths
    hadith_collection = bundle.one_to_one("relationships/hadith_in_collection.csv")
    hadith_tradition = bundle.one_to_one("relationships/hadith_in_tradition.csv")
    hadith_book = bundle.one_to_one("relationships/hadith_in_book.csv")
    hadith_chapter = bundle.one_to_one("relationships/hadith_in_chapter.csv")
    attribution_target = bundle.one_to_one("relationships/attributed_to.csv")
    alias_surface: dict[str, str] = {}
    alias_rows: dict[str, dict] = {}
    for row in bundle.rows("nodes/aliases.csv"):
        alias_surface[row["id"]] = row["surface"]
        alias_rows[row["id"]] = row
    hadiths = []
    hadith_info: dict[str, dict] = {}
    hadith_text: dict[str, str] = {}
    openiti_extraction, openiti_extraction_sha = load_openiti_extraction(args.reconciled)
    extraction_unused = set(openiti_extraction)
    extraction_counts: Counter = Counter()
    arabic_mismatches = 0
    provenance_mismatches = 0
    isolator = matn_isolator()
    matn_counts: Counter = Counter()
    for row in bundle.rows("nodes/hadiths.csv"):
        hadith_id = row["id"]
        source_row = unified.get(row["record_id"])
        if source_row is None:
            raise ProjectionError(f"{hadith_id}: record_id absent from the unified CSV")
        collection_id = hadith_collection[hadith_id]
        tradition_id = hadith_tradition[hadith_id]
        collection = collection_by_id[collection_id]
        if tradition_id != row["tradition_id"] or tradition_id != collection["tradition_id"]:
            raise ProjectionError(f"{hadith_id}: tradition disagrees with node or collection")
        text_ar = row["text_ar"]
        if sha256_text(text_ar) != row["arabic_sha256"]:
            arabic_mismatches += 1
        if blank_to_none(source_row["provenance_source"]) != blank_to_none(row["provenance"]):
            provenance_mismatches += 1
        narration_level = blank_to_none(source_row["narration_level"])
        if narration_level is not None and narration_level not in NARRATION_LEVELS:
            raise ProjectionError(f"{hadith_id}: narration_level {narration_level!r} outside the enum")
        chapter_title = blank_to_none(source_row["chapter"])
        category = blank_to_none(source_row["category"])
        hadith_no = blank_to_none(row["hadith_no"].strip())
        attributed = attribution_target.get(hadith_id)
        # A matn is stored only when it is this report's own (1,597 K6 rows carry a neighbour's; ~13k carry the chain).
        extraction = openiti_extraction.get(row["record_id"])
        # OpenITI: the parser's own matn (the sidecar), the same parse the unified CSV copied, read fresh.
        source_matn = extraction.get("matn_ar") if extraction is not None else blank_to_none(row["matn_ar"])
        matn_ar, matn_rejection = accepted_matn(isolator, row["record_id"], text_ar, source_matn)
        if matn_rejection:
            matn_counts[f"rejected:{matn_rejection}"] += 1
            matn_counts[f"rejected_by_work:{collection['source_work_id']}"] += 1
        elif matn_ar is not None:
            matn_counts["stored"] += 1
        if row["record_id"].startswith("openiti:") and extraction is None:
            raise ProjectionError(f"{hadith_id}: OpenITI report without a row in reconciled/openiti_extraction.jsonl.gz")
        if extraction is not None:
            extraction_unused.discard(row["record_id"])
            if extraction["text_ar_sha256"] != row["arabic_sha256"]:
                raise ProjectionError(f"{hadith_id}: openiti_extraction is bound to different Arabic")
            inherits = extraction["sanad_inherits_from_record_id"]
            extraction_counts[f"split_confidence:{extraction['split_confidence']}"] += 1
            extraction_counts["sanad_inherits_from"] += inherits is not None
            extraction_counts["source_notes"] += len(extraction["source_notes"])
        hadith_text[hadith_id] = text_ar
        hadith_info[hadith_id] = {
            "record_id": row["record_id"], "tradition_id": tradition_id, "source": row["source"],
            "source_work_id": collection["source_work_id"], "arabic_sha256": row["arabic_sha256"],
            "provider_hadith_id": blank_to_none(source_row["hadith_id"]), "hadith_no": hadith_no,
            "source_record_id": blank_to_none(row["source_record_id"]),
        }
        hadiths.append([
            hadith_id, row["record_id"], blank_to_none(row["source_record_id"]),
            blank_to_none(source_row["hadith_id"]), collection_id, collection["sort_key"],
            blank_to_none(source_row["source_display_label"]), tradition_id, hadith_book.get(hadith_id),
            hadith_chapter.get(hadith_id), blank_to_none(source_row["volume"]), blank_to_none(source_row["chapter_no"]),
            chapter_title, chapter_title.lower() if chapter_title else None, category,
            category.lower() if category else None, hadith_no, text_ar if text_ar != "" else None,
            arabic_norm(text_ar) if text_ar.strip() else None, row["arabic_sha256"], blank_to_none(row["sanad"]),
            blank_to_none(source_row["sanad_confidence"]), matn_ar,
            extraction["sanad_ar"] if extraction else None,
            f"hadith:{extraction['sanad_inherits_from_record_id']}"
            if extraction and extraction["sanad_inherits_from_record_id"] else None,
            extraction["split_confidence"] if extraction else None,
            json.dumps(extraction["source_notes"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if extraction and extraction["source_notes"] else None,
            alias_surface[attributed] if attributed else None, narration_level,
            blank_to_none(source_row["chain_type"]), blank_to_none(source_row["school"]), blank_to_none(row["url"]),
            blank_to_none(row["page_ref"]), blank_to_none(row["provenance"]),
            blank_to_none(row["translation_disposition"]), row["quality_excluded"] == "true",
            blank_to_none(row["quality_exclusion_reason"]),
        ])
    hadith_columns = [
        "id", "record_id", "source_record_id", "provider_hadith_id", "collection_id", "collection_sort_key",
        "source_display_label", "tradition_id", "book_id", "chapter_id", "volume", "chapter_no", "chapter_title",
        "chapter_title_folded", "category", "category_folded", "hadith_no", "text_ar", "text_ar_normalized",
        "arabic_sha256", "sanad", "sanad_confidence", "matn_ar", "sanad_ar", "sanad_inherits_from", "split_confidence",
        "source_notes", "attributed_to", "narration_level", "chain_type", "school", "url", "page_ref", "provenance_source", "translation_disposition", "quality_excluded",
        "quality_exclusion_reason",
    ]
    if arabic_mismatches:
        raise ProjectionError(f"{arabic_mismatches} hadiths fail the Arabic SHA-256 binding")
    if extraction_unused:
        raise ProjectionError(f"{len(extraction_unused)} openiti_extraction rows name no loaded report")
    known_hadith_ids = {item[0] for item in hadiths}
    inherits_at = hadith_columns.index("sanad_inherits_from")
    dangling = [item[0] for item in hadiths if item[inherits_at] is not None and item[inherits_at] not in known_hadith_ids]
    if dangling:
        raise ProjectionError(f"{len(dangling)} reports inherit a chain from a report that is not loaded")
    counts["openiti_extraction"] = dict(sorted(extraction_counts.items()))
    canonical.write("hadiths", hadith_columns, hadiths)
    counts["arabic_sha256_binding_errors"] = arabic_mismatches
    counts["hadith_provenance_differs_from_unified"] = provenance_mismatches
    counts["matn_ar"] = dict(sorted(matn_counts.items()))
    record_to_hadith = {info["record_id"]: hadith_id for hadith_id, info in hadith_info.items()}

    # translations (canonical) and translation_candidates (candidate stream)
    translation_target = bundle.one_to_one("relationships/translation_of.csv")
    translations = []
    state_counts: Counter = Counter()
    quality_counts: Counter = Counter()
    for row in bundle.rows("nodes/translations.csv"):
        hadith_id = translation_target[row["id"]]
        info = hadith_info[hadith_id]
        if row["arabic_sha256"] != info["arabic_sha256"]:
            raise ProjectionError(f"{row['id']}: translation Arabic hash differs from its hadith")
        if row["candidate_only"] != "false":
            raise ProjectionError(f"{row['id']}: candidate row in the canonical bundle surface")
        state = TRANSLATION_STATE_MAP.get(row["review_state"])
        if state is None:
            raise ProjectionError(f"{row['id']}: review_state {row['review_state']!r} has no translation_state")
        state_counts[f"{row['review_state']}->{state}"] += 1
        text = row["text"].lstrip()
        quality = english_quality(row["status"], text)
        if quality != row["status"]:
            quality_counts[f"{row['status']}->{quality}:{tradition_names[info['tradition_id']]}"] += 1
        translations.append([
            row["id"], hadith_id, row["language"], text,
            blank_to_none(unified[info["record_id"]]["matn_en"]), state, quality,
            blank_to_none(row["review_state"]), blank_to_none(row["source"]), blank_to_none(row["model"]), None,
            blank_to_none(row["provenance_source"]), blank_to_none(row["source_record_id"]), row["arabic_sha256"],
        ])
    machine_rows, machine_report = machine_english_rows(args, translations, hadith_info, hadith_text, record_to_hadith)
    counts["machine_english"] = machine_report
    translations = machine_rows
    canonical.write("translations", [
        "id", "hadith_id", "language", "text", "matn_text", "state", "quality_status", "review_state_raw", "source",
        "model", "translator", "provenance_source", "source_record_id", "arabic_sha256",
    ], translations)
    counts["translation_states"] = dict(sorted(state_counts.items()))
    counts["translation_quality_reclassified"] = dict(sorted(quality_counts.items()))

    candidate_rows = []
    for record_id, source_row in unified.items():
        if source_row["translation_review_status"] != "machine_unreviewed" or not source_row["text_en"].strip():
            continue
        hadith_id = record_to_hadith[record_id]
        model = blank_to_none(source_row["translation_model"])
        candidate_source = source_row["translation_source"].strip() or "unspecified"
        candidate_rows.append([
            f"translation-candidate:{record_id}:en:{candidate_source}", hadith_id, "en", candidate_source,
            source_row["text_en"].lstrip(), "machine_unreviewed" if model else "unknown_provenance", model,
            blank_to_none(source_row["translation_status"]) or "unknown", hadith_info[hadith_id]["arabic_sha256"],
        ])
    candidates.write("translation_candidates", ["id", "hadith_id", "language", "candidate_source", "text", "state",
                                                "model", "quality_status", "arabic_sha256"], candidate_rows)

    # narrators, lexicon profiles, aliases, teachers. The resolver's index also names the placeholder rows.
    exact_index, blocked_index = resolver_module.build_narrator_index(str(args.rawis))
    placeholders: dict[str, str] = exact_index.placeholders
    narrators = []
    narrator_ids: set[str] = set()
    narrator_english: dict[str, str] = {}
    for row in bundle.rows("nodes/narrators.csv"):
        name = row["name"]
        name_ar = blank_to_none(resolver_module._extract_arabic_name_raw(name))
        narrator_ids.add(row["id"])
        name_en = english_name(name)
        # The lexicon's own Latin rendering: its English field, else the Latin run before the Arabic (as the page shows
        # it, `splitLatinArabic`). Used only as a chain name's Latin form, credited to the lexicon.
        lexicon_latin = name_en or blank_to_none(re.split(r"[\u0600-\u06ff]", name, maxsplit=1)[0].strip(" (-,"))
        if lexicon_latin and re.search(r"[A-Za-z]", lexicon_latin):
            narrator_english[row["id"]] = lexicon_latin
        narrators.append([row["id"], "rawi", row["scholar_indx"], int(row["scholar_indx"]), name, name_ar,
                          name_en, arabic_norm(name_ar) if name_ar else None,
                          placeholders.get(row["scholar_indx"]), None, None])
    lexicon_ids = set(narrator_ids)
    # The Imam register (imam_kunya_conventions.json) and the external narrators some claim or link names.
    imam_register = ImamKunyaRegister.load()
    imam_profiles = []
    for imam in imam_register.data["imams"]:
        narrator_ids.add(imam["id"])
        narrator_english[imam["id"]] = imam["name_latin"]
        narrators.append([imam["id"], "imam_register", str(imam["ordinal"]), None, imam["name_ar"], imam["name_ar"],
                          imam["name_latin"], arabic_norm(imam["name_ar"]), None, imam["name_latin"], "identity_name"])
        imam_profiles.append([imam["id"], "imam_register", json.dumps(
            {"ordinal": imam["ordinal"], "known_as": imam["known_as"],
             "kunyas": [entry["kunya"] for entry in imam_register.data["kunyas"] if imam["ordinal"] in entry["shared_by"]]},
            ensure_ascii=False, sort_keys=True), xid.LICENCE["imam_register"], None,
            "Shura wa Istehsan register, for the owner to review", "source_unverified"])
    # Persons a work's own opening isnad names and the register lacks (opening_isnad_rules.json), credited to the work.
    for person in chain_builder.load_zayd_rule()[1]:
        narrator_ids.add(person["id"])
        narrator_english[person["id"]] = person["name_latin"]
        narrators.append([person["id"], "imam_register", person["id"].rsplit(":", 1)[1], None, person["name_ar"],
                          person["name_ar"], person["name_latin"], arabic_norm(person["name_ar"]), None,
                          person["name_latin"], "identity_name"])
        imam_profiles.append([person["id"], "imam_register", json.dumps(
            {"known_as": person["known_as"], "tradition": person["tradition"], "named_by": person["asserted_by"]},
            ensure_ascii=False, sort_keys=True), OPENING_ISNAD_LICENCE, None, person["asserted_by"],
            "source_unverified"])
    # Persons a work credits (work_register.json): compilers heading its chains, a transmitter it names in full.
    work_register = WorkRegister()
    for row in work_register.narrator_rows(arabic_norm):
        narrator_ids.add(row[0])
        narrator_english[row[0]] = row[9]
        narrators.append(row)
    imam_profiles.extend(work_register.profile_rows())
    external = xid.ExternalSources(args.reconciled)
    for row in external.narrator_rows(arabic_norm):
        narrator_ids.add(row[0])
        narrators.append(row)
    missing_compilers = sorted({c.narrator_id for c in work_register.compilers.values()} - narrator_ids)
    if missing_compilers:
        raise ProjectionError(f"work_register.json names compilers the projection does not load: {missing_compilers}")
    canonical.write("narrators", ["id", "authority", "authority_key", "scholar_indx", "name", "name_ar", "name_en",
                                  "name_ar_normalized", "placeholder_reason", "name_latin", "name_latin_basis"], narrators)
    external_profiles = external.profile_rows()
    canonical.write("narrator_source_profiles", ["narrator_id", "source", "assertions", "licence", "label_reason",
                                                 "asserted_by", "review_state"], imam_profiles + external_profiles)
    canonical.write("narrator_external_ids", ["id", "narrator_id", "namespace", "external_id", "asserted_by"],
                    external.external_id_rows())
    link_rows, link_dropped = external.link_rows(lexicon_ids, placeholders)
    canonical.write("narrator_link_candidates", ["id", "external_narrator_id", "rawi_narrator_id", "basis", "evidence",
                                                 "review_state"], link_rows)
    person_keys = external.person_keys(lexicon_ids, placeholders)
    narrator_placeholder = {row[0]: row[8] for row in narrators if row[8]}
    counts["narrators_by_authority"] = dict(sorted(Counter(row[1] for row in narrators).items()))
    counts["external_label_like"] = dict(sorted(Counter(
        f"{row[1]}:{row[4].split(':')[0]}" for row in external_profiles if row[4]).items()))
    counts["narrator_link_candidates_dropped"] = dict(sorted(link_dropped.items()))
    counts["narrator_placeholders"] = dict(sorted(Counter(placeholders.values()).items()))
    biography_subject = bundle.one_to_one("relationships/biography_of.csv")
    profiles = []
    lifespans: dict[str, Lifespan] = {}   # lexicon years for the chain chronology guard; a recorded 0 is not a year
    for row in bundle.rows("nodes/biographies.csv"):
        if biography_subject[row["id"]] != row["subject_id"]:
            raise ProjectionError(f"{row['id']} subject disagrees")
        birth = int4_or_none(parse_hijri_year(row["birth_date_hijri"], row["birth_date"], row["birth_date_place"]))
        death = int4_or_none(parse_hijri_year(row["death_date_hijri"], None, row["death_date_place"]))
        lifespans[row["subject_id"]] = Lifespan(birth or None, death or None)
        # The lexicon's `grade` column is its generation class ("Comp.(RA) [1st Generation]"), so it is also tabaqah_raw.
        profiles.append([
            row["subject_id"], row["id"], row["raw_profile_sha256"], blank_to_none(row["grade"]), None,
            blank_to_none(row["grade"].strip()), None, birth,
            int4_or_none(parse_exact_safe_integer(row["birth_date_gregorian"])),
            blank_to_none(row["birth_date_hijri"].strip()), blank_to_none(row["birth_date_gregorian"].strip()),
            blank_to_none(row["birth_date"].strip()), blank_to_none(row["birth_place"]), death,
            int4_or_none(parse_exact_safe_integer(row["death_date_gregorian"])),
            blank_to_none(row["death_date_hijri"].strip()), blank_to_none(row["death_date_gregorian"].strip()),
            None, blank_to_none(row["death_place"]), blank_to_none(row["death_reason"]),
            "lexicon_unverified", row["review_state"], blank_to_none(row["source_locator"]), lexicon_source_fields(row),
        ])
    canonical.write("narrator_lexicon_profiles", [
        "narrator_id", "bundle_id", "raw_profile_sha256", "lexicon_grade_label", "bio", "tabaqah_raw",
        "geographic_region", "birth_year_hijri", "birth_year_gregorian", "birth_year_hijri_raw",
        "birth_year_gregorian_raw", "birth_source_text", "birth_place", "death_year_hijri", "death_year_gregorian",
        "death_year_hijri_raw", "death_year_gregorian_raw", "death_source_text", "death_place", "death_reason",
        "review_state", "source_status", "source_locator", "source_fields",
    ], profiles)
    aliases = []
    for alias_id, narrator_id in bundle.one_to_one("relationships/alias_of.csv").items():
        row = alias_rows[alias_id]
        aliases.append([alias_id, narrator_id, row["surface"], row["normalized_surface"], row["alias_kind"]])
    canonical.write("narrator_aliases", ["id", "narrator_id", "surface", "normalized_surface", "alias_kind"], aliases)
    teachers = []
    lexicon_pairs: set[tuple[str, str]] = set()   # (student, teacher) the lexicon's own teacher lists name
    for row in bundle.rows("relationships/student_of.csv"):
        lexicon_pairs.add((row["start"], row["end"]))
        teachers.append([row["start"], row["end"], pg_array(row["evidence_fields"].split("|")),
                         int(row["evidence_count"]), row["reciprocal"] == "true", row["review_state"]])
    canonical.write("narrator_teachers", ["student_id", "teacher_id", "evidence_fields", "evidence_count",
                                          "reciprocal", "review_state"], teachers, key_width=2)

    # chains and mentions: the bundle's text extraction, then the reconciled sidecars (AGENTS.md "Chains")
    from extract_isnad_unified import name_normalize
    chain_owner = {row["end"]: row["start"] for row in bundle.rows("relationships/has_chain.csv")}
    mentions_by_chain: dict[str, list[dict]] = defaultdict(list)
    for row in bundle.rows("nodes/name_mentions.csv"):
        mentions_by_chain[row["chain_id"]].append(row)
    branches_by_hadith: dict[str, list[dict]] = defaultdict(list)
    for row in bundle.rows("nodes/chains.csv"):
        if chain_owner.get(row["id"]) != row["hadith_id"]:
            raise ProjectionError(f"{row['id']}: has_chain disagrees with the chain's hadith_id")
        rows = sorted(mentions_by_chain.pop(row["id"], []), key=lambda item: int(item["position"]))
        if [int(item["position"]) for item in rows] != list(range(len(rows))) or len(rows) != int(row["length"]):
            raise ProjectionError(f"{row['id']}: mention positions are not contiguous 0..length-1")
        if any(item["hadith_id"] != row["hadith_id"] for item in rows):
            raise ProjectionError(f"{row['id']}: a mention names another hadith than its chain")
        branches_by_hadith[row["hadith_id"]].append({
            "id": row["id"], "branch": int(row["branch"]), "resolved": row["resolved"] == "true",
            "extraction_method": row["extraction_method"], "sanad_confidence": blank_to_none(row["sanad_confidence"]),
            "mentions": [(item["id"], item["surface"], item["normalized_surface"]) for item in rows],
        })
    if mentions_by_chain:
        raise ProjectionError(f"{len(mentions_by_chain)} mention chains have no chain row")

    sidecars, sidecar_hashes, k6_resolver_sha = load_reconciled_sidecars(args.reconciled)
    counts["chain_sidecars"] = dict(sorted(apply_chain_sidecars(
        branches_by_hadith, sidecars["no_chain_in_source.jsonl.gz"], sidecars["pure_canon_chain.jsonl.gz"],
        hadith_info, record_to_hadith, name_normalize).items()))

    # OpenITI works: the chain is cut from the parser's sanad_ar, continuations inherit (chain_builder.py).
    zayd_rule, register_additions = chain_builder.load_zayd_rule()
    openiti_reports = []
    for hadith_id, info in hadith_info.items():
        extraction = openiti_extraction.get(info["record_id"])
        if extraction is None:
            continue
        if info["source_work_id"] not in chain_builder.OPENITI_WORKS:
            raise ProjectionError(f"{hadith_id}: OpenITI extraction row outside the three parsed works")
        openiti_reports.append(chain_builder.OpenitiReport(
            info["record_id"], chain_builder.work_of(info["record_id"]), hadith_text[hadith_id], extraction["sanad_ar"],
            extraction.get("matn_ar"), extraction["split_confidence"], extraction["sanad_inherits_from_record_id"]))
    built = chain_builder.build_openiti_chains(openiti_reports, zayd_rule)
    # A continuation copies the candidates of the written mentions it repeats, so those reports are projected first.
    build_order = {record_to_hadith[record_id]: index for index, record_id in enumerate(built.branches)}
    openiti_counts: Counter = Counter(built.counts)
    inheriting_hadiths: set[str] = set()
    for record_id, branches in built.branches.items():
        hadith_id = record_to_hadith[record_id]
        openiti_counts["bundle_chains_replaced"] += len(branches_by_hadith.pop(hadith_id, []))
        for index, branch in enumerate(branches):
            inherited = any(mention.inherited_from for mention in branch)
            inheriting_hadiths.update([hadith_id] if inherited else [])
            branches_by_hadith[hadith_id].append({
                "id": f"chain:{record_id}:{index:04d}", "branch": index, "resolved": False,
                "extraction_method": "openiti_inherited_chain" if inherited else "openiti_sanad_span",
                "sanad_confidence": None,
                "mentions": [(f"mention:{record_id}:{index:04d}:{position:04d}", mention.surface,
                              name_normalize(mention.surface)) for position, mention in enumerate(branch)],
                "built": branch,
            })
            openiti_counts["chains"] += 1
            openiti_counts["mentions"] += len(branch)
            openiti_counts["mentions_inherited"] += sum(1 for mention in branch if mention.inherited_from)
    counts["openiti_chain_builder"] = dict(sorted(openiti_counts.items()))

    # Thaqalayn (Imami) chains: «جميعا» groups, non-narrators, suspended chains, anonymous gaps (chain_builder.py).
    imami_counts: Counter = Counter()
    imami_built: dict[str, list[chain_builder.ImamiChain]] = {}
    for hadith_id in sorted(branches_by_hadith):
        info = hadith_info[hadith_id]
        if not hadith_id.startswith("hadith:thaqalayn:") or tradition_names[info["tradition_id"]] != "Imami":
            continue
        surfaces = [[surface for _, surface, _ in branch["mentions"]]
                    for branch in sorted(branches_by_hadith[hadith_id], key=lambda item: item["branch"])]
        work = info["source_work_id"].split(":", 1)[1]
        imami_built[hadith_id] = chain_builder.build_imami_chains(hadith_text[hadith_id], surfaces, work, imami_counts)
        if not imami_built[hadith_id]:
            imami_counts["reports_left_without_chain"] += 1
    imami_suspension = chain_builder.mark_mid_chain_starts(
        {h: (hadith_info[h]["source_work_id"], hadith_text[h]) for h in imami_built}, imami_built, imami_counts)
    # «وبهذا الإسناد» directly after a report of the same chapter: the only antecedent filled in this round.
    chapter_order: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for hadith_id in imami_built:
        provider = hadith_info[hadith_id]["provider_hadith_id"]
        if hadith_chapter.get(hadith_id) and provider and provider.isdigit():
            chapter_order[hadith_chapter[hadith_id]].append((int(provider), hadith_id))
    previous_report: dict[str, str] = {}
    for reports in chapter_order.values():
        reports.sort()
        for (_, earlier), (_, later) in zip(reports, reports[1:]):
            previous_report[later] = earlier
    imami_resolved = chain_builder.resolve_same_isnad(imami_built, previous_report,
                                                      {h: hadith_info[h]["record_id"] for h in imami_built}, imami_counts)
    imami_depth = {hadith_id: depth for hadith_id, depth in imami_resolved.items()}
    for hadith_id, chains_built in imami_built.items():
        record_id = hadith_info[hadith_id]["record_id"]
        branches_by_hadith[hadith_id] = []
        for index, chain in enumerate(chains_built):
            inherited = any(mention.inherited_from for mention in chain.mentions)
            if inherited:
                inheriting_hadiths.add(hadith_id)
            branches_by_hadith[hadith_id].append({
                "id": f"chain:{record_id}:{index:04d}", "branch": index, "resolved": False,
                "extraction_method": "thaqalayn_inherited_chain" if inherited else "extract_isnad_unified",
                "sanad_confidence": None, "suspension": imami_suspension.get((hadith_id, index), chain.suspension),
                "mentions": [(f"mention:{record_id}:{index:04d}:{position:04d}", mention.surface,
                              name_normalize(mention.surface)) for position, mention in enumerate(chain.mentions)],
                "built": chain.mentions,
            })
            imami_counts["chains"] += 1
            imami_counts["mentions"] += len(chain.mentions)
            imami_counts[f"suspension:{branches_by_hadith[hadith_id][-1]['suspension']}"] += 1
        if not branches_by_hadith[hadith_id]:
            del branches_by_hadith[hadith_id]
    for hadith_id, depth in imami_depth.items():
        build_order[hadith_id] = 1_000_000 + depth
    counts["imami_chain_builder"] = dict(sorted(imami_counts.items()))

    # K6 source index: mapped onto the extracted branches only where the sidecar's text branches are exactly them.
    source_counts: Counter = Counter()
    source_alignment: dict[str, tuple[dict, dict]] = {}
    for record_id, row in sorted(sidecars["k6_source_index.jsonl.gz"].items()):
        hadith_id = record_to_hadith.get(record_id)
        if hadith_id is None:
            source_counts["reports_not_in_bundle"] += 1
            continue
        if row["arabic_sha256"] != hadith_info[hadith_id]["arabic_sha256"]:
            raise ProjectionError(f"{record_id}: K6 sidecar is bound to different Arabic")
        if not row.get("source_ids"):
            source_counts["reports_without_source_index"] += 1
            continue
        branches = sorted(branches_by_hadith.get(hadith_id, []), key=lambda branch: branch["branch"])
        alignment = align_source_index(row, [[surface for _, surface, _ in branch["mentions"]] for branch in branches])
        if alignment is None:
            source_counts["reports_whose_text_branches_differ_from_the_extraction"] += 1
            continue
        source_alignment[hadith_id] = (row, alignment)
        source_counts[f"reports_mapped:{row['basis']}"] += 1

    # Sunni chains (chain_builder.py, audit chain-audit/sunni/): flattened tahwil split at its seam, formula words cut out
    # of names, «A و B» neighbours on one level. Runs after the K6 alignment, so each moved mention keeps its source-index
    # claim through its origin (bundle branch, position).
    sunni_counts: Counter = Counter()
    for hadith_id in sorted(branches_by_hadith):
        info = hadith_info[hadith_id]
        if tradition_names[info["tradition_id"]] != "Sunni":
            continue
        old = sorted(branches_by_hadith[hadith_id], key=lambda item: item["branch"])
        if any(branch.get("built") for branch in old):
            continue
        surfaces = [[surface for _, surface, _ in branch["mentions"]] for branch in old]
        rebuilt = chain_builder.build_sunni_chains(hadith_text[hadith_id], surfaces, sunni_counts)
        if [[mention.surface for mention in chain.mentions] for chain in rebuilt] == surfaces:
            continue
        record_id = info["record_id"]
        method = old[0]["extraction_method"]
        sunni_counts["reports_changed"] += 1
        branches_by_hadith[hadith_id] = [{
            "id": f"chain:{record_id}:{index:04d}", "branch": index, "resolved": False,
            "extraction_method": method, "sanad_confidence": old[0]["sanad_confidence"],
            "mentions": [(f"mention:{record_id}:{index:04d}:{position:04d}", mention.surface,
                          name_normalize(mention.surface)) for position, mention in enumerate(chain.mentions)],
            "origins": [mention.origin for mention in chain.mentions],
        } for index, chain in enumerate(rebuilt)]
        if not rebuilt:
            del branches_by_hadith[hadith_id]
    counts["sunni_chain_builder"] = dict(sorted(sunni_counts.items()))

    # Accepted chain fixes (chain_fix_projection.py, AGENTS.md §Chain fixes): after every builder, before the gate.
    # An absent or empty overrides file is a no-op.
    chain_fix_counts: Counter = Counter()
    chain_fix_overrides = chain_fix_projection.replay.load_overrides(args.chain_fixes)
    chain_field = {record_to_hadith[record_id]: row["chain"] for record_id, row in sidecars["pure_canon_chain.jsonl.gz"].items()
                   if record_id in record_to_hadith and row.get("chain")}
    # replace_routes reports keep their rule-built branches until the mention loop is done (chain_fix_projection.py).
    chain_fix_replacing = chain_fix_projection.apply_overrides(chain_fix_overrides, branches_by_hadith, hadith_info,
                                                               hadith_text, chain_field, chain_fix_counts)

    # Chain structure gate (chain_structure.py, AGENTS.md §Chain structure gate): prose and rijal works and chapter
    # headings store no chain at all; the loader retires their earlier rows.
    structure_counts: Counter = Counter()
    retired_by_gate: set[str] = set()       # mention id prefixes of reports whose chains the gate retires
    pure_canon_rows = sidecars["pure_canon_chain.jsonl.gz"]
    for hadith_id in sorted(branches_by_hadith):
        info = hadith_info[hadith_id]
        from_text = info["record_id"] not in pure_canon_rows
        reason = chain_structure.retire_reason(info["source_work_id"], tradition_names[info["tradition_id"]],
                                               hadith_text[hadith_id], from_text)
        if reason:
            structure_counts[f"retired_chains:{reason}"] += len(branches_by_hadith.pop(hadith_id))
            structure_counts[f"retired_reports:{reason}"] += 1
            retired_by_gate.add(f"mention:{info['record_id']}:")
    edition_ids = chain_builder.load_edition_identifications()
    death_year = {narrator: span.death for narrator, span in lifespans.items()}

    name_cache: dict[str, tuple[str, str, str] | None] = {}

    def name_match(surface: str) -> tuple[str, str, str] | None:
        """(scholar_indx, basis, detail) from the canonical resolver tiers, else a labelled kunya-only candidate."""
        if surface not in name_cache:
            match = None
            scholar = resolver_module.resolve_narrator(surface, exact_index, blocked_index)
            if scholar:
                if exact_index.get(resolver_module.narrator_normalize(surface)):
                    tier = "tier0"
                elif exact_index.folded.get(resolver_module.narrator_fold_normalize(surface)):
                    tier = "tier1"
                else:
                    tier = "tier2"
                match = (scholar, NAME_BASIS_BY_TIER[tier], tier)
            else:
                kunya = resolver_module.kunya_only_candidate(surface, exact_index)
                if kunya:
                    match = (kunya, "name_kunya_only", "kunya_only_registry_entry")
            name_cache[surface] = match
        return name_cache[surface]

    def source_claims(hadith_id: str, branch: dict, position: int, mention_id: str, surface_ar: str, owner: dict,
                      dropped: Counter, external_tally: Counter) -> list[xid.Candidate]:
        """The sources' own claims at one written mention: the K6 source index through the mention's origin, then hadith-kg
        and Riwayat claims bound to its surface and the report's Arabic."""
        found: list[xid.Candidate] = []
        source = source_alignment.get(hadith_id)
        if source is not None:
            row, alignment = source
            origin = branch["origins"][position] if branch.get("origins") else (branch["branch"], position)
            hit = alignment.get(origin) if origin else None
            if hit is not None:
                source_position, shared_trunk = hit
                scholar = row["source_ids"][source_position]
                basis = "source_index_confirmed_by_text" if row["basis"] == K6_CONFIRMED_BASIS else "source_index"
                if f"narrator:rawi:{scholar}" not in narrator_ids:
                    dropped[f"{basis}:narrator_not_in_bundle"] += 1
                elif placeholders.get(scholar):
                    # Owner decision (d): a placeholder row is never a match target, whoever names it.
                    dropped[f"{basis}:placeholder:{placeholders[scholar]}"] += 1
                else:
                    detail = row["agreement_class"] + (":shared_trunk" if shared_trunk else "")
                    found.append(xid.Candidate(f"narrator:rawi:{scholar}", basis, detail, source_position))
        found.extend(external.candidates_for(mention_id, hadith_id, surface_ar, owner["arabic_sha256"], external_tally))
        return found

    # Bare kunya rule (AGENTS.md §Bare kunya rule): in a work with no curated per-report narrator index (xid.KUNYA_RULE_WORKS) a
    # surface that is only a kunya stands only when exactly one person in that work's own source carries it. Carriers are counted
    # per work, kunya and source over every written bare-kunya mention before any identity is decided.
    kunya_carriers: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for hadith_id, report_branches in branches_by_hadith.items():
        owner = hadith_info[hadith_id]
        if owner["source_work_id"] not in xid.KUNYA_RULE_WORKS:
            continue
        for branch in report_branches:
            built_mentions = branch.get("built")
            for position, (mention_id, surface_ar, _) in enumerate(branch["mentions"]):
                if built_mentions and built_mentions[position].inherited_from:
                    continue
                key = xid.bare_kunya_key(surface_ar)
                if key is None:
                    continue
                for claim in source_claims(hadith_id, branch, position, mention_id, surface_ar, owner, Counter(), Counter()):
                    if not claim.placeholder and not claim.label_like:
                        kunya_carriers[(owner["source_work_id"], key, xid.authority_of(claim.narrator_id))].add(claim.narrator_id)
    compiler_counts: Counter = Counter()

    provider_english = ProviderEnglish(args.imami_english_lexicon)
    chains = []
    mentions = []
    identity_rows = []
    identity: dict[str, Counter] = defaultdict(Counter)
    latin_counts: Counter = Counter()
    external_counts: Counter = Counter()
    chronology: Counter = Counter()
    empty_normalized = 0
    written_candidates: dict[str, list[xid.Candidate]] = {}   # candidates of every written OpenITI mention
    for hadith_id in sorted(branches_by_hadith,
                            key=lambda item: (item in inheriting_hadiths, build_order.get(item, 0), item)):
        branches = sorted(branches_by_hadith[hadith_id], key=lambda branch: branch["branch"])
        if [branch["branch"] for branch in branches] != list(range(len(branches))):
            raise ProjectionError(f"{hadith_id}: chain branches are not contiguous 0..n-1")
        owner = hadith_info[hadith_id]
        work = owner["source_work_id"]
        tradition = tradition_names[owner["tradition_id"]]
        report_text = PlainText(hadith_text[hadith_id])
        pure_canon_row = pure_canon_rows.get(owner["record_id"])
        extraction = openiti_extraction.get(owner["record_id"])
        detection_text = (pure_canon_row["chain"] if pure_canon_row else None) or (
            extraction.get("sanad_ar") if extraction else None) or hadith_text[hadith_id]
        structure = chain_structure.assess(chain_structure.ReportChains(
            detection_text, [[surface for _, surface, _ in branch["mentions"]] for branch in branches], tradition,
            [bool(branch.get("built")) and any(mention.inherited_from for mention in branch["built"]) for branch in branches],
            hadith_id.startswith("hadith:thaqalayn:"), work, pure_canon_row is None))
        # Thaqalayn's English sanad lexicon covers its own Imami works only.
        provider_text = tradition == "Imami" and hadith_id.startswith("hadith:thaqalayn:")
        for branch, reasons in zip(branches, structure):
            rows = branch["mentions"]
            built_mentions = branch.get("built")
            status = chain_structure.UNCERTAIN if reasons else chain_structure.CHECKED
            fix = branch.get("chain_fix")
            if fix and fix["structure_status"]:
                # A fix's reading is not re-gated: its status is the fix's (read_by_model, verified_by_reviewer).
                status, reasons = fix["structure_status"], []
            structure_counts[f"{tradition}:{status}"] += 1
            structure_counts.update(f"reason:{tradition}:{reason}" for reason in reasons)
            chains.append([branch["id"], hadith_id, branch["branch"], len(rows), branch["resolved"],
                           branch["extraction_method"], None, branch["sanad_confidence"], branch.get("suspension"), None,
                           status, pg_array(reasons) if reasons else None, fix["fix_id"] if fix else None, None, None])
            if built_mentions and any(mention.inherited_from for mention in built_mentions):
                # An inherited name is not written in this report: only the written ones are located in its text.
                written_at = [position for position, mention in enumerate(built_mentions) if not mention.inherited_from]
                located = locate_mentions(report_text, [rows[position][1] for position in written_at])
                spans = [None] * len(rows)
                for position, span in zip(written_at, located):
                    spans[position] = span
            else:
                spans = locate_mentions(report_text, [surface_ar for _, surface_ar, _ in rows])
            resolved = []   # per position: (found, standing), before the chronology contest
            for position, (mention_id, surface_ar, normalized) in enumerate(rows):
                # A surface such as a bare conjunction 'و' normalizes to '': keep '' (known empty), never NULL.
                if normalized == "":
                    empty_normalized += 1

                found: list[xid.Candidate] = []
                built_mention = built_mentions[position] if built_mentions else None
                if built_mention is not None and built_mention.inherited_from:
                    # A continuation repeats a written mention: the same candidates, from the same sources.
                    root_id = "mention:{}:{:04d}:{:04d}".format(*built_mention.inherited_from)
                    found = list(written_candidates[root_id])
                    identity["inherited_mentions"][tradition] += 1
                else:
                    if tradition in NAME_MATCH_TRADITIONS:
                        match = name_match(surface_ar)
                        if match:
                            scholar, basis, detail = match
                            if f"narrator:rawi:{scholar}" not in narrator_ids:
                                identity["dropped"][f"{basis}:narrator_not_in_bundle"] += 1
                            elif placeholders.get(scholar) and basis != "name_kunya_only":
                                raise ProjectionError(f"{mention_id}: {basis} targets placeholder rawi {scholar}")
                            else:
                                found.append(xid.Candidate(f"narrator:rawi:{scholar}", basis, detail,
                                                           placeholder=placeholders.get(scholar)))
                    claims = source_claims(hadith_id, branch, position, mention_id, surface_ar, owner, identity["dropped"],
                                           external_counts)
                    named = work_register.named_person(work, surface_ar)
                    if named is not None:
                        # The work names this transmitter in full (work_register.json): its own record stands; a source's
                        # confirmed claim stays beside it as an unconfirmed candidate (owner 2026-11-22, Abu Ubayda).
                        lowered = [xid.demote_kunya_only(claim, surface_ar) for claim in claims]
                        identity["named_in_full_claims_unconfirmed"][tradition] += sum(
                            1 for before, after in zip(claims, lowered) if before.basis != after.basis)
                        claims = lowered
                        found.append(xid.Candidate(named.narrator_id, xid.OPENING_ISNAD_BASIS, named.detail))
                        identity["named_in_full"][f"{tradition}:{named.narrator_id}"] += 1
                    found.extend(claims)
                    if built_mention is not None and built_mention.rule_identity:
                        narrator_id, detail = built_mention.rule_identity
                        found.append(xid.Candidate(narrator_id, xid.OPENING_ISNAD_BASIS, detail))
                    origin = branch["origins"][position] if branch.get("origins") else (branch["branch"], position)
                    edition = edition_ids.get((hadith_id, origin)) if origin else None
                    if edition and edition["surface"] == surface_ar:
                        identity["edition_identifications"][tradition] += 1
                        found.append(xid.Candidate(edition["narrator_id"], xid.EDITION_BASIS, edition["detail"]))
                    # The Imams' conventional kunyas, with the honorific marker after the name in the text.
                    span = spans[position]
                    marker = report_text.honorific_after(*span) if span else False
                    imam = imam_register.match(surface_ar, tradition, marker)
                    if imam:
                        identity["imam_kunya"][f"{imam.basis}:{imam.detail}"] += 1
                        for imam_id in imam.imam_ids:
                            found.append(xid.Candidate(imam_id, imam.basis, imam.detail))

                for candidate in found:
                    identity_rows.append([candidate_id(mention_id, candidate.basis, candidate.narrator_id), mention_id,
                                          hadith_id, candidate.narrator_id, candidate.basis, candidate.detail,
                                          candidate.source_position, candidate.source_ref, candidate.origin])
                    identity["candidates_by_basis"][f"{tradition}:{candidate.basis}"] += 1
                if built_mentions:
                    written_candidates[mention_id] = found
                agreement = candidate_agreement(candidate.narrator_id for candidate in found)
                identity["mentions_by_agreement"][f"{tradition}:{agreement}"] += 1
                standing = xid.standing_identity(found, person_keys)
                kunya_reason = None
                kunya = xid.bare_kunya_key(surface_ar) if standing and work in xid.KUNYA_RULE_WORKS                     and standing[1] in xid.KUNYA_RULE_AUTHORITIES else None
                if kunya:
                    carriers = max(len(kunya_carriers[(work, kunya, authority)])
                                   for authority in xid.KUNYA_RULE_AUTHORITIES[standing[1]])
                    if xid.bare_kunya_withheld(work, carriers):
                        kunya_reason = (f"kunya only: {carriers} people carry «{surface_ar}» in this work's source, so the "
                                        "name alone cannot say which")
                        identity["standing_withheld_by_kunya_rule"][f"{tradition}:{standing[1]}"] += 1
                        standing = None
                    else:
                        identity["standing_bare_kunya_one_carrier"][f"{tradition}:{standing[1]}"] += 1
                if built_mention is not None and built_mention.link_kind in ("not_a_narrator", "anonymous"):
                    # A back-reference or an unnamed transmitter is a label: its candidates stay, no identity stands.
                    if standing:
                        identity["standing_blocked_on_label_position"][f"{tradition}:{built_mention.link_kind}"] += 1
                    standing = None
                    kunya_reason = None
                if standing is None and any(c.basis in xid.CONFIRMED_SOURCE_BASES for c in found):
                    identity["confirmed_but_contested_or_not_counted"][tradition] += 1
                resolved.append((found, standing, kunya_reason))

            # Chain chronology guard (chain_chronology.py, AGENTS.md §Chain chronology): a standing identity may not
            # make an adjacent pair impossible on the lexicon's years; seams of a repeated narrator are only counted.
            contest = contest_chain([standing[0] if standing else None for _, standing, _ in resolved], lifespans,
                                    lexicon_pairs)
            chronology["pairs_decided_against_one_name"] += contest.decided
            chronology["pairs_undecided_both_withheld"] += contest.undecided
            chronology["pairs_left_standing_possible_irsal"] += contest.irsal
            chronology["pairs_left_to_the_view_repeated_narrator"] += contest.repeated_left
            chronology["seam_pairs_never_a_transmission"] += contest.seam_pairs
            chronology["seam_chains"] += 1 if contest.seam_pairs else 0
            if tradition == "Sunni":
                gap = chain_builder.missing_link_after([standing[0] if standing else None for _, standing, _ in resolved],
                                                       death_year, [surface for _, surface, _ in rows])
                if gap is not None:
                    chains[-1][9] = gap
                    identity["chains_with_missing_link"][tradition] += 1
            final_ids: list[str | None] = []
            for position, (mention_id, surface_ar, normalized) in enumerate(rows):
                found, standing, kunya_reason = resolved[position]
                surface = Verbatim(normalized)
                teacher = Verbatim(rows[position + 1][2]) if position + 1 < len(rows) else None
                student = Verbatim(rows[position - 1][2]) if position > 0 else None
                coarse, fine = review_unit_ids(surface, teacher, student, work)
                withheld = contest.withheld.get(position) or kunya_reason
                if withheld and not kunya_reason:
                    kind = "undecided" if "cannot tell" in withheld else "decided"
                    chronology[f"mentions_withheld:{tradition}:{kind}"] += 1
                    identity["standing_withheld_by_chronology"][f"{tradition}:{standing[1]}"] += 1
                if standing and not withheld:
                    narrator_id, method = standing
                    resolved_as, resolution_basis, confidence = "source_index", "source_index", 1.0
                    identity["standing_by_method"][f"{tradition}:{method}"] += 1
                else:
                    narrator_id, resolved_as, resolution_basis, confidence, method = UNRESOLVED
                identity["mentions"][tradition] += 1
                span = spans[position]

                # The name in Latin letters (AGENTS.md §Latin names): the provider's English, then an identity's
                # English name, then a transliteration of the name as written; else none (Arabic alone).
                latin: tuple[str, str, str | None] | None = None
                if provider_text:
                    hit = provider_english.lookup(resolver_module.narrator_fold_normalize(surface_ar))
                    if hit:
                        latin = (hit[0], "provider_english", None)
                if latin is None:
                    named = narrator_id
                    if named is None and not withheld:   # a withheld identity never names the mention
                        people = {c.narrator_id for c in found
                                  if c.basis not in xid.NON_CONTESTING_BASES and not c.placeholder}
                        named = next(iter(people)) if len(people) == 1 else None
                    if named and named in narrator_english:
                        latin = (narrator_english[named], "identity_name", named)
                if latin is None:
                    written = report_text.original_span(*span) if span else surface_ar
                    reading = latin_name(written)
                    if reading:
                        latin = (reading[0], reading[1], None)
                latin_counts[f"{tradition}:{latin[1] if latin else 'none'}"] += 1
                built_mention = built_mentions[position] if built_mentions else None
                link_kind = (built_mention.link_kind if built_mention is not None else None) or (
                    "person" if narrator_id else "unclassified")
                inherited_from = ("mention:{}:{:04d}:{:04d}".format(*built_mention.inherited_from)
                                  if built_mention is not None and built_mention.inherited_from else None)
                mentions.append([
                    mention_id, branch["id"], hadith_id, position, surface_ar, surface, teacher, student, coarse, fine,
                    link_kind, resolved_as, resolution_basis, narrator_id,
                    confidence, method, latin[0] if latin else None, latin[1] if latin else None,
                    latin[2] if latin else None, withheld, inherited_from,
                ])
                final_ids.append(narrator_id)
            # The work's compiler heads the chain as its first transmitter, derived, never a mention (owner 2026-11-22;
            # work_register.py): not when the text already writes him; 'direct' only when he heard position 0.
            head = work_register.head(work, [surface for _, surface, _ in rows], final_ids, branch.get("suspension"),
                                      detection_text)
            if head is not None:
                chains[-1][13], chains[-1][14] = head
                compiler_counts[f"{tradition}:{work}:{head[1]}"] += 1
            elif work in work_register.compilers:
                compiler_counts[f"{tradition}:{work}:written_in_text"] += 1
    # Accepted fixes that replace routes: the rule-built rows of those reports become the fix's rows, by the apply's rule.
    # External claims were consumed by the rule-built mentions, so the unused-claims check below reads their ids.
    mention_ids_built = {row[0] for row in mentions}
    chains, mentions, identity_rows = chain_fix_projection.rewrite_rows(chain_fix_replacing, chains, mentions, identity_rows,
                                                                        Verbatim, chain_fix_counts)
    counts["chain_fixes"] = {"overrides": len(chain_fix_overrides), **dict(sorted(chain_fix_counts.items()))}
    counts["chain_structure"] = dict(sorted(structure_counts.items()))
    counts["compiler_heads"] = dict(sorted(compiler_counts.items()))
    canonical.write("chains", ["id", "hadith_id", "branch", "length", "resolved", "extraction_method", "confidence",
                               "sanad_confidence", "suspension", "missing_link_after", "structure_status",
                               "structure_reasons", "chain_fix_id", "compiler_narrator_id", "compiler_link"], chains)
    canonical.write("chain_mentions", [
        "id", "chain_id", "hadith_id", "position", "surface_ar", "surface_normalized", "teacher_context_normalized",
        "student_context_normalized", "review_unit_id", "review_unit_fine_id", "link_kind", "resolution",
        "resolution_basis", "narrator_id", "confidence", "extraction_method", "name_latin", "name_latin_basis",
        "name_latin_narrator_id", "identity_withheld_reason", "inherited_from_mention_id",
    ], mentions)
    canonical.write("chain_mention_candidates", ["id", "mention_id", "hadith_id", "narrator_id", "basis", "detail",
                                                 "source_position", "source_ref", "source_assertion_origin"],
                    identity_rows)
    unused_claims = set(external.claims_by_mention) - mention_ids_built
    # A claim on a chain the gate retires (prose work, chapter heading) goes with it, counted; any other is a refusal.
    gate_dropped = {claim for claim in unused_claims if claim.startswith(tuple(retired_by_gate))} if retired_by_gate else set()
    counts["chain_structure"]["external_claims_dropped_with_retired_chains"] = len(gate_dropped)
    unused_claims -= gate_dropped
    if unused_claims:
        print(f"unused external claim, e.g. {min(unused_claims)}", file=sys.stderr)
        raise ProjectionError(f"{len(unused_claims)} external claims name a mention the projection does not have")
    counts["latin_names"] = dict(sorted(latin_counts.items()))
    counts["external_claims"] = dict(sorted(external_counts.items()))
    counts["mentions_with_empty_normalized_surface"] = empty_normalized
    counts["k6_source_index"] = dict(sorted(source_counts.items()))
    counts["identity_candidates"] = {key: dict(sorted(value.items())) for key, value in sorted(identity.items())}
    counts["chain_chronology"] = {"death_gap_years": CHRONOLOGY_DEATH_GAP_YEARS, "irsal_years": CHRONOLOGY_IRSAL_YEARS,
                                  **dict(sorted(chronology.items()))}
    counts["k6_sidecar_built_with_current_resolver"] = k6_resolver_sha == sha256_file(Path(resolver_module.__file__))

    # hadith assessments
    assessments = []
    assessment_counts: Counter = Counter()
    for hadith_id, info in hadith_info.items():
        source_row = unified[info["record_id"]]
        tradition = tradition_names[info["tradition_id"]]
        code = tradition.lower()
        grade_value = source_row["grade_value"].strip()
        if grade_value not in PLACEHOLDER_GRADES:
            grade_tradition = source_row["grade_tradition"].strip() or tradition
            if grade_tradition != tradition:
                raise ProjectionError(f"{hadith_id}: grade_tradition {grade_tradition} != hadith tradition")
            if grade_value != PURE_CANON_INCLUSION_LABEL:
                raise ProjectionError(f"{hadith_id}: unclassified grade_value {grade_value!r}")
            assessments.append(assessment_row(info, code, tradition, "grade_value", 0, "collection_label", None,
                                              grade_value, None))
            assessment_counts["grade_value:collection_label"] += 1
        entries, skipped = parse_gradings_full(source_row["gradings_full"])
        assessment_counts["gradings_full:malformed_segments_skipped"] += skipped
        for ordinal, entry in enumerate(entries):
            if entry["grade"].strip() in PLACEHOLDER_GRADES:
                continue
            reason = non_ruling_reason(entry["grade"])
            if reason:   # "he did not include it", "silent on it", a back-reference: not a ruling, never a grade
                assessment_counts[f"gradings_full:non_ruling_excluded:{reason}"] += 1
                continue
            assessments.append(assessment_row(info, code, tradition, "gradings_full", ordinal, "cited_ruling",
                                              entry["scholar"], entry["grade"], entry["citation"]))
            assessment_counts["gradings_full:cited_ruling"] += 1
    canonical.write("hadith_assessments", [
        "id", "hadith_id", "tradition_id", "grade_scheme", "ordinal", "kind", "grader", "grade_raw", "grade_canonical",
        "grade_detail", "citation_raw", "cited_work", "cited_volume", "cited_page", "citation_id", "source_field",
        "review_state",
    ], assessments)
    counts["hadith_assessments"] = dict(sorted(assessment_counts.items()))

    # report correspondences (pipeline candidates; reviewer decisions live in the curation table)
    correspondence_rows, member_rows, correspondence_counts, correspondence_inputs = project_correspondences(
        args.correspondence, hadith_info, input_sha)
    canonical.write("report_correspondence_candidates", [
        "id", "hadith_id_a", "hadith_id_b", "arabic_sha256_a", "arabic_sha256_b", "relation_class", "jaccard",
        "containment", "global_containment", "length_ratio", "shared_shingles", "shingles_a", "shingles_b", "words_a",
        "words_b", "score_band", "scope", "matn_split_a", "matn_split_b", "cluster_id", "basis", "method_version",
    ], correspondence_rows)
    canonical.write("report_correspondence_cluster_members", [
        "method_version", "hadith_id", "cluster_id", "star_centre_hadith_id", "is_star_centre",
    ], member_rows, key_width=2)
    counts["report_correspondences"] = correspondence_counts

    # evidence tables: created empty at launch (section 5.8); the bundle's Citation surface is header-only
    if bundle.files["nodes/citations.csv"]["row_count"] != 0:
        raise ProjectionError("bundle has citations; the projection does not map them yet")
    canonical.write("bibliographic_works", ["id", "title", "title_ar", "author", "author_narrator_id", "tradition_id",
                                            "author_death_year_hijri", "openiti_uri"], [])
    canonical.write("editions", ["id", "work_id", "editor", "publisher", "place", "year", "locator_scheme", "url",
                                 "rights_status"], [])
    canonical.write("citations", ["id", "work_id", "edition_id", "volume", "page", "locator", "url", "quote_ar",
                                  "quote_en", "retrieved_at", "review_state"], [])

    counts["by_tradition"] = dict(sorted(Counter(tradition_names[i["tradition_id"]] for i in hadith_info.values()).items()))
    source_release_state = bundle.manifest["source_release_state"]
    base = {
        "projection_version": PROJECTION_VERSION,
        "target": "postgres",
        "source_bundle": {
            "path": display_path(args.bundle),
            "content_sha256": bundle.manifest["content_sha256"],
            "bundle_version": bundle.manifest["bundle_version"],
            "bundle_schema_version": bundle.manifest["bundle_schema_version"],
            "source_release_state": source_release_state,
            "import_ready": True,
            "expected_record_count": bundle.manifest["totals"]["hadith_records"],
        },
        "inputs": {
            "input_dataset_sha256": input_sha,
            "rawis_sha256": rawis_sha,
            "legacy_master": {"path": display_path(args.legacy_master), "sha256": legacy_sha},
            "curation_manifest_sha256": bundle.input_sha256("curation_manifest"),
            "extractor": {
                "version": f"extract_isnad_unified@bundle-{bundle.manifest['bundle_version']}",
                "sha256": bundle.input_sha256("isnad_extractor"),
            },
            "resolver_sha256": sha256_file(Path(resolver_module.__file__)),
            "arabic_norm_sha256": sha256_file(DATASETS_DIR / "classify_attribution.py"),
            "projection_sha256": sha256_file(Path(__file__)),
            "reconciled_sidecars": {f"reconciled/{name}": digest for name, digest in sorted(sidecar_hashes.items())},
            "openiti_extraction_sha256": openiti_extraction_sha,
            "k6_sidecar_resolver_sha256": k6_resolver_sha,
            "matn_isolation_sha256": sha256_file(CORRESPONDENCE_JOB_DIR / "matn_isolation.py"),
            "extractor_sha256": sha256_file(HADITH_DATA_DIR / "extract_isnad_unified.py"),
            "non_ruling_rule_sha256": sha256_file(GRADING_RECOVERY_DIR / "build_hadith_assessment_rows.py"),
            "report_correspondence": {"path": display_path(args.correspondence), **correspondence_inputs},
            "external_identity_sidecars": {f"reconciled/{name}": digest for name, digest in sorted(external.hashes.items())},
            "imam_kunya_conventions_sha256": sha256_file(CONVENTIONS_PATH),
            "machine_english": machine_english_input(args),
            "reader_v3_work_profiles": {"work_profiles_v3.json": sha256_file(work_register_module.PROFILES_V3_PATH),
                                        "expand_v3.py": sha256_file(work_register_module.EXPAND_V3_PATH)},
            "chain_fixes": ({"path": display_path(args.chain_fixes), "sha256": sha256_file(args.chain_fixes),
                             "replay_sha256": sha256_file(chain_fix_projection.REPLAY_PATH)}
                            if args.chain_fixes.is_file() else None),
            "imami_english_lexicon": {"path": display_path(args.imami_english_lexicon),
                                      "sha256": sha256_file(args.imami_english_lexicon)},
            "name_modules_sha256": {name: sha256_file(HERE / name) for name in MODULE_FILES},
        },
        "release": {
            "release_class": "release" if source_release_state == "release" else "non_release",
            "non_release_reason": None if source_release_state == "release"
            else f"source_release_state={source_release_state}; bundle publication_ready=false",
            "attribution_disclaimer": ATTRIBUTION_DISCLAIMER,
        },
        "options": {"source_index": "k6_sidecar", "name_match_traditions": sorted(NAME_MATCH_TRADITIONS)},
    }
    manifests = {}
    for writer in (canonical, candidates):
        manifest = {**base, "stream": writer.stream, "files": writer.files,
                    "counts": counts if writer is canonical else {},
                    "content_sha256": graph_content_hash(writer.files, [])}
        (output_dir / writer.stream / "manifest.json").write_bytes(deterministic_json_bytes(manifest))
        manifests[writer.stream] = manifest
    return manifests


def assessment_row(info: dict, code: str, tradition: str, source_field: str, ordinal: int, kind: str,
                   grader: str | None, grade_raw: str, citation_raw: str | None) -> list[object]:
    work, volume, page = split_citation(citation_raw)
    return [
        f"assessment:{info['record_id']}:{code}:{source_field}:{ordinal:02d}", record_hadith_id(info),
        f"tradition:{code}", TRADITION_GRADE_SCHEMES[tradition], ordinal, kind, blank_to_none(grader), grade_raw,
        map_to_canonical(grade_raw), blank_to_none(clean_grade_detail(grade_raw)), blank_to_none(citation_raw), work,
        volume, page, None, source_field, "source_provided",
    ]


def record_hadith_id(info: dict) -> str:
    return f"hadith:{info['record_id']}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", required=True, type=Path, help="validated Neo4j-format bundle directory")
    parser.add_argument("--input", required=True, type=Path, help="the 37-column unified CSV the bundle was built from")
    parser.add_argument("--rawis", required=True, type=Path, help="all_rawis.csv the bundle was built from")
    parser.add_argument("--legacy-master", required=True, type=Path, help="the committed 26-column master")
    parser.add_argument("--catalog", required=True, type=Path,
                        help="live catalog JSON from `tsx src/db/load/dump-catalog.ts` (headers must match)")
    parser.add_argument("--output", required=True, type=Path, help="new, empty output directory")
    parser.add_argument("--reconciled", type=Path, default=HADITH_DATA_DIR / "reconciled",
                        help="reconciled sidecar directory (K6 source index, Pure Canon chains, no-chain flags)")
    parser.add_argument("--correspondence", type=Path, default=CORRESPONDENCE_JOB_DIR / "output",
                        help="report-correspondence output (pairs, cluster members, summary.json)")
    parser.add_argument("--machine-english", type=Path, default=MACHINE_ENGLISH_OVERLAY,
                        help="gated machine English (translate_gap_fill.py finalize); a missing file means none")
    parser.add_argument("--imami-english-lexicon", type=Path, default=IMAMI_ENGLISH_LEXICON,
                        help="Thaqalayn English-sanad surface lexicon (diagnostics/chain-reconciliation)")
    parser.add_argument("--chain-fixes", type=Path, default=chain_fix_projection.OVERRIDES_PATH,
                        help="accepted chain-fix overrides (chain-fixes/accepted_overrides.jsonl.gz); absent means none")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        manifests = project(args)
    except (OSError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    summary = {stream: {"content_sha256": manifest["content_sha256"],
                        "rows": {item["table"]: item["row_count"] for item in manifest["files"]}}
               for stream, manifest in manifests.items()}
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
