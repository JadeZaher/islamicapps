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
for _path in (HADITH_DATA_DIR, DATASETS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from neo4j_export.contract import (  # noqa: E402
    deterministic_json_bytes,
    graph_content_hash,
    sha256_file,
    typed_column_name,
)

PROJECTION_VERSION = "2026.11.21.1"
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
# Mention-exact and legacy-index identities that disagree: stored unresolved, counted, never guessed.
WITHHELD_CONFLICT = (None, "unresolved", None, None, "withheld_conflicting_automatic_identities")
MAX_SAFE_INTEGER = 2**53 - 1
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


def parse_chain_indx(value: str) -> list[list[int]]:
    """Same grammar as export_bundle._parse_chain_indx: branches split by '|', ids by ','."""
    text = str(value or "").strip()
    if not text or text in {"[]", "nan"}:
        return []
    if text.startswith("[") and text.endswith("]") and "|" not in text:
        text = text[1:-1].strip()
    if not text:
        return []
    branches: list[list[int]] = []
    for branch_text in text.split("|"):
        tokens = [token.strip() for token in branch_text.split(",")]
        if not tokens or any(not token for token in tokens):
            raise ValueError(f"empty chain_indx token in {value!r}")
        branch = []
        for token in tokens:
            if not token.isdigit() or int(token) <= 0:
                raise ValueError(f"invalid chain_indx token {token!r}")
            branch.append(int(token))
        branches.append(branch)
    return branches


def provider_ids_agree(legacy_id: str, provider_hadith_id: str | None, hadith_no: str | None) -> bool:
    """Corroborating id check on a unique Arabic join. Some works were re-keyed in the 37-column file
    (`pc_9`, `rabi_0825`) while the legacy `hadith_id` is the hadith number, so equal-to-`hadith_no` also agrees."""
    legacy_id = (legacy_id or "").strip()
    if not legacy_id or not provider_hadith_id:
        return True
    return legacy_id == provider_hadith_id.strip() or legacy_id == (hadith_no or "").strip()


def shapes_match(index_branches: Sequence[Sequence[int]], chain_lengths: Sequence[int]) -> bool:
    """Legacy links load only when branch count and every branch length equal the extracted chains."""
    return (
        len(index_branches) > 0
        and len(index_branches) == len(chain_lengths)
        and all(len(branch) == length for branch, length in zip(index_branches, chain_lengths))
    )


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
    arabic_mismatches = 0
    provenance_mismatches = 0
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
        hadith_info[hadith_id] = {
            "record_id": row["record_id"], "tradition_id": tradition_id, "source": row["source"],
            "source_work_id": collection["source_work_id"], "arabic_sha256": row["arabic_sha256"],
            "provider_hadith_id": blank_to_none(source_row["hadith_id"]), "hadith_no": hadith_no,
        }
        hadiths.append([
            hadith_id, row["record_id"], blank_to_none(row["source_record_id"]),
            blank_to_none(source_row["hadith_id"]), collection_id, collection["sort_key"],
            blank_to_none(source_row["source_display_label"]), tradition_id, hadith_book.get(hadith_id),
            hadith_chapter.get(hadith_id), blank_to_none(source_row["volume"]), blank_to_none(source_row["chapter_no"]),
            chapter_title, chapter_title.lower() if chapter_title else None, category,
            category.lower() if category else None, hadith_no, text_ar if text_ar != "" else None,
            arabic_norm(text_ar) if text_ar.strip() else None, row["arabic_sha256"], blank_to_none(row["sanad"]),
            blank_to_none(source_row["sanad_confidence"]), blank_to_none(row["matn_ar"]),
            alias_surface[attributed] if attributed else None, narration_level,
            blank_to_none(source_row["chain_type"]), blank_to_none(source_row["school"]), blank_to_none(row["url"]),
            blank_to_none(row["page_ref"]), blank_to_none(row["provenance"]),
            blank_to_none(row["translation_disposition"]), row["quality_excluded"] == "true",
            blank_to_none(row["quality_exclusion_reason"]),
        ])
    if arabic_mismatches:
        raise ProjectionError(f"{arabic_mismatches} hadiths fail the Arabic SHA-256 binding")
    canonical.write("hadiths", [
        "id", "record_id", "source_record_id", "provider_hadith_id", "collection_id", "collection_sort_key",
        "source_display_label", "tradition_id", "book_id", "chapter_id", "volume", "chapter_no", "chapter_title",
        "chapter_title_folded", "category", "category_folded", "hadith_no", "text_ar", "text_ar_normalized",
        "arabic_sha256", "sanad", "sanad_confidence", "matn_ar", "attributed_to", "narration_level", "chain_type",
        "school", "url", "page_ref", "provenance_source", "translation_disposition", "quality_excluded",
        "quality_exclusion_reason",
    ], hadiths)
    counts["arabic_sha256_binding_errors"] = arabic_mismatches
    counts["hadith_provenance_differs_from_unified"] = provenance_mismatches
    record_to_hadith = {info["record_id"]: hadith_id for hadith_id, info in hadith_info.items()}

    # translations (canonical) and translation_candidates (candidate stream)
    translation_target = bundle.one_to_one("relationships/translation_of.csv")
    translations = []
    state_counts: Counter = Counter()
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
        translations.append([
            row["id"], hadith_id, row["language"], text,
            blank_to_none(unified[info["record_id"]]["matn_en"]), state, row["status"],
            blank_to_none(row["review_state"]), blank_to_none(row["source"]), blank_to_none(row["model"]), None,
            blank_to_none(row["provenance_source"]), blank_to_none(row["source_record_id"]), row["arabic_sha256"],
        ])
    canonical.write("translations", [
        "id", "hadith_id", "language", "text", "matn_text", "state", "quality_status", "review_state_raw", "source",
        "model", "translator", "provenance_source", "source_record_id", "arabic_sha256",
    ], translations)
    counts["translation_states"] = dict(sorted(state_counts.items()))

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

    # narrators, lexicon profiles, aliases, teachers
    narrators = []
    narrator_ids: set[str] = set()
    for row in bundle.rows("nodes/narrators.csv"):
        name = row["name"]
        name_ar = blank_to_none(resolver_module._extract_arabic_name_raw(name))
        narrator_ids.add(row["id"])
        narrators.append([row["id"], "rawi", row["scholar_indx"], int(row["scholar_indx"]), name, name_ar,
                          english_name(name), arabic_norm(name_ar) if name_ar else None])
    canonical.write("narrators", ["id", "authority", "authority_key", "scholar_indx", "name", "name_ar", "name_en",
                                  "name_ar_normalized"], narrators)
    biography_subject = bundle.one_to_one("relationships/biography_of.csv")
    profiles = []
    for row in bundle.rows("nodes/biographies.csv"):
        if biography_subject[row["id"]] != row["subject_id"]:
            raise ProjectionError(f"{row['id']} subject disagrees")
        profiles.append([
            row["subject_id"], row["id"], row["raw_profile_sha256"], blank_to_none(row["grade"]), None, None, None,
            int4_or_none(parse_hijri_year(row["birth_date_hijri"], row["birth_date"], row["birth_date_place"])),
            int4_or_none(parse_exact_safe_integer(row["birth_date_gregorian"])),
            blank_to_none(row["birth_date_hijri"].strip()), blank_to_none(row["birth_date_gregorian"].strip()),
            blank_to_none(row["birth_date"].strip()), blank_to_none(row["birth_place"]),
            int4_or_none(parse_hijri_year(row["death_date_hijri"], None, row["death_date_place"])),
            int4_or_none(parse_exact_safe_integer(row["death_date_gregorian"])),
            blank_to_none(row["death_date_hijri"].strip()), blank_to_none(row["death_date_gregorian"].strip()),
            None, blank_to_none(row["death_place"]), blank_to_none(row["death_reason"]),
            "lexicon_unverified", row["review_state"], blank_to_none(row["source_locator"]),
        ])
    canonical.write("narrator_lexicon_profiles", [
        "narrator_id", "bundle_id", "raw_profile_sha256", "lexicon_grade_label", "bio", "tabaqah_raw",
        "geographic_region", "birth_year_hijri", "birth_year_gregorian", "birth_year_hijri_raw",
        "birth_year_gregorian_raw", "birth_source_text", "birth_place", "death_year_hijri", "death_year_gregorian",
        "death_year_hijri_raw", "death_year_gregorian_raw", "death_source_text", "death_place", "death_reason",
        "review_state", "source_status", "source_locator",
    ], profiles)
    aliases = []
    for alias_id, narrator_id in bundle.one_to_one("relationships/alias_of.csv").items():
        row = alias_rows[alias_id]
        aliases.append([alias_id, narrator_id, row["surface"], row["normalized_surface"], row["alias_kind"]])
    canonical.write("narrator_aliases", ["id", "narrator_id", "surface", "normalized_surface", "alias_kind"], aliases)
    teachers = []
    for row in bundle.rows("relationships/student_of.csv"):
        teachers.append([row["start"], row["end"], pg_array(row["evidence_fields"].split("|")),
                         int(row["evidence_count"]), row["reciprocal"] == "true", row["review_state"]])
    canonical.write("narrator_teachers", ["student_id", "teacher_id", "evidence_fields", "evidence_count",
                                          "reciprocal", "review_state"], teachers, key_width=2)

    # chains
    chain_owner = {row["end"]: row["start"] for row in bundle.rows("relationships/has_chain.csv")}
    chains = []
    chain_rows: dict[str, dict] = {}
    chains_by_hadith: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for row in bundle.rows("nodes/chains.csv"):
        if chain_owner.get(row["id"]) != row["hadith_id"]:
            raise ProjectionError(f"{row['id']}: has_chain disagrees with the chain's hadith_id")
        chain_rows[row["id"]] = row
        chains_by_hadith[row["hadith_id"]].append((int(row["branch"]), int(row["length"]), row["id"]))
        chains.append([row["id"], row["hadith_id"], int(row["branch"]), int(row["length"]), row["resolved"] == "true",
                       row["extraction_method"], None, blank_to_none(row["sanad_confidence"])])
    canonical.write("chains", ["id", "hadith_id", "branch", "length", "resolved", "extraction_method", "confidence",
                               "sanad_confidence"], chains)
    for branches in chains_by_hadith.values():
        branches.sort()

    # chain mentions: bundle (report_atomic) -> per-mention exact (mention_exact) -> legacy index (source_index)
    resolves_to = bundle.one_to_one("relationships/resolves_to.csv")
    mentions_by_chain: dict[str, list[dict]] = defaultdict(list)
    for row in bundle.rows("nodes/name_mentions.csv"):
        mentions_by_chain[row["chain_id"]].append(row)
    exact_index, blocked_index = resolver_module.build_narrator_index(str(args.rawis))
    surface_cache: dict[str, tuple[str | None, str | None]] = {}

    def resolve_surface(surface: str) -> tuple[str | None, str | None]:
        if surface not in surface_cache:
            scholar = resolver_module.resolve_narrator(surface, exact_index, blocked_index)
            tier = None
            if scholar:
                if exact_index.get(resolver_module.narrator_normalize(surface)):
                    tier = "tier0"
                elif exact_index.folded.get(resolver_module.narrator_fold_normalize(surface)):
                    tier = "tier1"
                else:
                    tier = "tier2"
            surface_cache[surface] = (scholar, tier)
        return surface_cache[surface]

    resolution: dict[str, tuple] = {}  # mention id -> (narrator_id, resolution, basis, confidence, method)
    for chain_id, rows in mentions_by_chain.items():
        for row in rows:
            narrator_id = resolves_to.get(row["id"])
            if narrator_id is not None:
                resolution[row["id"]] = (narrator_id, "exact_registry", "report_atomic", 1.0, "bundle_chain_indx")
                continue
            scholar, tier = resolve_surface(row["surface"])
            candidate = f"narrator:rawi:{scholar}" if scholar else None
            if candidate in narrator_ids:
                resolution[row["id"]] = (candidate, "exact_registry", "mention_exact", 1.0, f"name_invariant_{tier}")

    legacy_counts: Counter = Counter()
    if args.legacy_source_index:
        legacy_counts = apply_legacy_source_index(
            args.legacy_master, hadith_info, tradition_names, chains_by_hadith, mentions_by_chain, narrator_ids,
            resolution,
        )
    resolution_counts: Counter = Counter()

    mentions = []
    empty_normalized = 0
    for chain_id in sorted(mentions_by_chain):
        rows = sorted(mentions_by_chain[chain_id], key=lambda item: int(item["position"]))
        positions = [int(row["position"]) for row in rows]
        if positions != list(range(len(rows))) or len(rows) != int(chain_rows[chain_id]["length"]):
            raise ProjectionError(f"{chain_id}: mention positions are not contiguous 0..length-1")
        owner = hadith_info[chain_rows[chain_id]["hadith_id"]]
        work = owner["source_work_id"]
        tradition = tradition_names[owner["tradition_id"]]
        for index, row in enumerate(rows):
            # A surface such as a bare conjunction 'و' normalizes to '': keep '' (known empty), never NULL (unknown).
            surface = Verbatim(row["normalized_surface"])
            teacher = Verbatim(rows[index + 1]["normalized_surface"]) if index + 1 < len(rows) else None
            student = Verbatim(rows[index - 1]["normalized_surface"]) if index > 0 else None
            if surface == "":
                empty_normalized += 1
            coarse, fine = review_unit_ids(surface, teacher, student, work)
            narrator_id, resolved_as, basis, confidence, method = resolution.get(row["id"], UNRESOLVED)
            resolution_counts[f"{tradition}:{resolved_as}:{method or 'none'}"] += 1
            mentions.append([
                row["id"], chain_id, row["hadith_id"], int(row["position"]), row["surface"], surface, teacher,
                student, coarse, fine, "person" if narrator_id else "unclassified", resolved_as, basis, narrator_id,
                confidence, method,
            ])
    canonical.write("chain_mentions", [
        "id", "chain_id", "hadith_id", "position", "surface_ar", "surface_normalized", "teacher_context_normalized",
        "student_context_normalized", "review_unit_id", "review_unit_fine_id", "link_kind", "resolution",
        "resolution_basis", "narrator_id", "confidence", "extraction_method",
    ], mentions)
    counts["mention_resolution"] = dict(sorted(resolution_counts.items()))
    counts["mentions_with_empty_normalized_surface"] = empty_normalized
    counts["legacy_source_index"] = dict(sorted(legacy_counts.items()))

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
            assessments.append(assessment_row(info, code, tradition, "gradings_full", ordinal, "cited_ruling",
                                              entry["scholar"], entry["grade"], entry["citation"]))
            assessment_counts["gradings_full:cited_ruling"] += 1
    canonical.write("hadith_assessments", [
        "id", "hadith_id", "tradition_id", "grade_scheme", "ordinal", "kind", "grader", "grade_raw", "grade_canonical",
        "grade_detail", "citation_raw", "cited_work", "cited_volume", "cited_page", "citation_id", "source_field",
        "review_state",
    ], assessments)
    counts["hadith_assessments"] = dict(sorted(assessment_counts.items()))

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
        },
        "release": {
            "release_class": "release" if source_release_state == "release" else "non_release",
            "non_release_reason": None if source_release_state == "release"
            else f"source_release_state={source_release_state}; bundle publication_ready=false",
            "attribution_disclaimer": ATTRIBUTION_DISCLAIMER,
        },
        "options": {"legacy_source_index": bool(args.legacy_source_index)},
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


def apply_legacy_source_index(legacy_master: Path, hadith_info: dict, tradition_names: dict,
                              chains_by_hadith: dict, mentions_by_chain: dict, narrator_ids: set,
                              resolution: dict) -> Counter:
    """Owner Q1: load the legacy chain_indx as source_index links, only on a unique join and an exact shape match."""
    counts: Counter = Counter()
    bundle_keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    for hadith_id, info in hadith_info.items():
        bundle_keys[(info["source"], info["arabic_sha256"])].append(hadith_id)
    legacy_keys: Counter = Counter()
    indexed_rows: list[tuple[tuple[str, str], str, str]] = []
    with open_text(legacy_master) as handle:
        for row in csv.DictReader(handle):
            key = (row["source"].strip(), sha256_text(row["text_ar"]))
            legacy_keys[key] += 1
            if row["chain_indx"].strip() not in {"", "[]", "nan"}:
                indexed_rows.append((key, row["hadith_id"].strip(), row["chain_indx"]))
    counts["legacy_rows_with_chain_indx"] = len(indexed_rows)
    for key, legacy_provider_id, chain_indx in indexed_rows:
        targets = bundle_keys.get(key, [])
        if not targets:
            counts["rejected_no_unique_match:none"] += 1
            continue
        if len(targets) > 1:
            counts["rejected_no_unique_match:ambiguous_bundle"] += 1
            continue
        if legacy_keys[key] > 1:
            counts["rejected_no_unique_match:duplicate_legacy"] += 1
            continue
        hadith_id = targets[0]
        info = hadith_info[hadith_id]
        if not provider_ids_agree(legacy_provider_id, info["provider_hadith_id"], info["hadith_no"]):
            counts["rejected_provider_id_conflict"] += 1
            continue
        tradition = tradition_names[info["tradition_id"]]
        if tradition == "Imami":
            counts["rejected_imami"] += 1
            continue
        try:
            branches = parse_chain_indx(chain_indx)
        except ValueError:
            counts["rejected_parse_error"] += 1
            continue
        if any(f"narrator:rawi:{scholar}" not in narrator_ids for branch in branches for scholar in branch):
            counts["rejected_unknown_rawi"] += 1
            continue
        chain_list = chains_by_hadith.get(hadith_id, [])
        if not shapes_match(branches, [length for _, length, _ in chain_list]):
            counts["rejected_shape_mismatch" if chain_list else "rejected_no_extracted_chain"] += 1
            continue
        counts[f"accepted_reports:{tradition}"] += 1
        for (_, _, chain_id), branch in zip(chain_list, branches):
            mentions = sorted(mentions_by_chain[chain_id], key=lambda item: int(item["position"]))
            for mention, scholar in zip(mentions, branch):
                narrator_id = f"narrator:rawi:{scholar}"
                existing = resolution.get(mention["id"])
                if existing is not None:
                    verdict = "agree" if existing[0] == narrator_id else "disagree"
                    counts[f"mentions_existing:{verdict}:{existing[4]}"] += 1
                    if verdict == "disagree" and existing[2] == "mention_exact":
                        # Two automated sources name different people: withhold both, never pick one.
                        resolution[mention["id"]] = WITHHELD_CONFLICT
                    continue
                resolution[mention["id"]] = (narrator_id, "source_index", "source_index", 1.0, "legacy_chain_indx")
                counts["mentions_linked"] += 1
    return counts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", required=True, type=Path, help="validated Neo4j-format bundle directory")
    parser.add_argument("--input", required=True, type=Path, help="the 37-column unified CSV the bundle was built from")
    parser.add_argument("--rawis", required=True, type=Path, help="all_rawis.csv the bundle was built from")
    parser.add_argument("--legacy-master", required=True, type=Path, help="the committed 26-column master")
    parser.add_argument("--catalog", required=True, type=Path,
                        help="live catalog JSON from `tsx src/db/load/dump-catalog.ts` (headers must match)")
    parser.add_argument("--output", required=True, type=Path, help="new, empty output directory")
    parser.add_argument("--legacy-source-index", action="store_true",
                        help="load legacy chain_indx links as resolution source_index (owner question 1)")
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
