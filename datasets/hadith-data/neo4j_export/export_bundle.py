"""Build a deterministic, import-ready Neo4j graph bundle."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import shutil
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterator, Sequence

try:
    from .contract import (
        BUNDLE_SCHEMA_VERSION,
        BUNDLE_VERSION,
        CANDIDATE_PATH_MARKERS,
        CANONICAL_TRADITIONS,
        DEFAULT_SOURCE_RELEASE_STATE,
        DEFAULT_ISNAD_BRANCH_LIMIT,
        EMPTY_GATED_ENTITIES,
        EXPORT_ISNAD_BRANCH_LIMIT,
        NODE_FILES,
        RAWI_COLUMNS,
        RAWI_PROFILE_COLUMNS,
        RAWI_PROFILE_PROVENANCE,
        RAWI_PROFILE_REVIEW_STATE,
        RELATIONSHIP_FILES,
        SOURCE_QUALITY_EXCLUSIONS,
        TEXT_MULTILINE_FILES,
        UNIFIED_COLUMNS,
        deterministic_json_bytes,
        graph_content_hash,
        sha256_file,
        sha256_text,
        stable_hash,
        tradition_id,
    )
except ImportError:  # pragma: no cover - direct script execution
    from contract import (  # type: ignore
        BUNDLE_SCHEMA_VERSION,
        BUNDLE_VERSION,
        CANDIDATE_PATH_MARKERS,
        CANONICAL_TRADITIONS,
        DEFAULT_SOURCE_RELEASE_STATE,
        DEFAULT_ISNAD_BRANCH_LIMIT,
        EMPTY_GATED_ENTITIES,
        EXPORT_ISNAD_BRANCH_LIMIT,
        NODE_FILES,
        RAWI_COLUMNS,
        RAWI_PROFILE_COLUMNS,
        RAWI_PROFILE_PROVENANCE,
        RAWI_PROFILE_REVIEW_STATE,
        RELATIONSHIP_FILES,
        SOURCE_QUALITY_EXCLUSIONS,
        TEXT_MULTILINE_FILES,
        UNIFIED_COLUMNS,
        deterministic_json_bytes,
        graph_content_hash,
        sha256_file,
        sha256_text,
        stable_hash,
        tradition_id,
    )

EXPORT_DIR = Path(__file__).resolve().parent
HADITH_DATA_DIR = EXPORT_DIR.parent
PROJECT_ROOT = HADITH_DATA_DIR.parent.parent
SOURCE_WORK_REGISTRY = EXPORT_DIR / "source_work_registry.json"
EXTRACTOR_PATH = HADITH_DATA_DIR / "extract_isnad_unified.py"
EXPORTER_PATH = Path(__file__).resolve()
CONTRACT_PATH = EXPORT_DIR / "contract.py"
VALIDATOR_PATH = EXPORT_DIR / "validate_bundle.py"
THAQALAYN_URL_RE = re.compile(
    r"^https?://(?:www[.])?thaqalayn[.]net/hadith/"
    r"([^/]+)/([^/]+)/([^/]+)/([^/?#]+)(?:[?#].*)?$"
)

if str(HADITH_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(HADITH_DATA_DIR))

import extract_isnad_unified as isnad_extractor_module  # noqa: E402
from extract_isnad_unified import (  # noqa: E402
    IsnadExtractionLimitError,
    extract_isnad_branches,
    name_normalize,
)

_csv_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit(_csv_limit)
        break
    except OverflowError:
        _csv_limit //= 10


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _assert_allowed_input(path: Path, role: str) -> None:
    normalized = path.as_posix().lower()
    marker = next(
        (value for value in CANDIDATE_PATH_MARKERS if value in normalized),
        None,
    )
    if marker:
        raise ValueError(f"{role} input is a prohibited candidate asset: {marker}")
    if not path.is_file():
        raise ValueError(f"{role} input does not exist: {path}")


def _open_csv(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("rt", encoding="utf-8-sig", newline="")


def _row_labels(*labels: str) -> str:
    return ";".join(labels)


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _parse_chain_indx(value: str) -> list[list[int]]:
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
        branch: list[int] = []
        for token in tokens:
            if not token.isdigit() or int(token) <= 0:
                raise ValueError(f"invalid chain_indx token {token!r}")
            branch.append(int(token))
        branches.append(branch)
    return branches


def _parse_indexed_narrators(
    value: str,
    *,
    field: str,
    line_no: int,
) -> tuple[set[int], int, int]:
    text = str(value or "").strip()
    if not text or text == "NA":
        return set(), 0, 0
    parsed: set[int] = set()
    tokens = text.split(",")
    for token in tokens:
        normalized = token.strip()
        if not normalized.isdigit() or int(normalized) <= 0:
            raise ValueError(
                f"invalid {field} narrator index at line {line_no}: "
                f"{normalized!r}"
            )
        parsed.add(int(normalized))
    return parsed, len(tokens), len(tokens) - len(parsed)


def _rawi_profile_hash(row: dict[str, str]) -> str:
    payload = json.dumps(
        [str(row.get(column) or "") for column in RAWI_PROFILE_COLUMNS],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256_text(payload)


def _assert_exact_dict_row(
    row: dict[str | None, str | list[str] | None],
    fieldnames: Sequence[str],
    *,
    role: str,
    line_no: int,
) -> None:
    extra = row.get(None)
    missing = [column for column in fieldnames if row.get(column) is None]
    if extra is not None or missing:
        raise ValueError(
            f"{role} CSV has a non-exact row shape at line {line_no}: "
            f"extra={extra!r}, missing={missing}"
        )


class _Stage:
    """Disk-backed deterministic row set."""

    def __init__(self, path: Path):
        self.path = path
        self.connection = sqlite3.connect(path)
        # The staging DB is disposable and rebuilt from immutable inputs.
        self.connection.execute("PRAGMA journal_mode=OFF")
        self.connection.execute("PRAGMA synchronous=OFF")
        self.connection.execute(
            """
            CREATE TABLE staged_rows (
                file_path TEXT NOT NULL,
                sort_key TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (file_path, sort_key)
            ) WITHOUT ROWID
            """
        )
        self.pending = 0

    def put(self, file_path: str, sort_key: str, row: Sequence[str]) -> None:
        expected = (
            NODE_FILES.get(file_path) or RELATIONSHIP_FILES.get(file_path)
        )["header"]
        values = list(row)
        if file_path in NODE_FILES and len(values) == len(expected) - 1:
            # neo4j-admin import IDs are lookup tokens, not stored properties.
            # Persist the same namespaced value as `id` for post-import access.
            values.insert(1, values[0])
        if len(values) != len(expected):
            raise ValueError(
                f"{file_path} row has {len(values)} fields; expected {len(expected)}"
            )
        payload = json.dumps(
            ["" if value is None else str(value) for value in values],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            self.connection.execute(
                "INSERT INTO staged_rows(file_path, sort_key, payload) "
                "VALUES (?, ?, ?)",
                (file_path, sort_key, payload),
            )
        except sqlite3.IntegrityError:
            existing = self.connection.execute(
                "SELECT payload FROM staged_rows "
                "WHERE file_path = ? AND sort_key = ?",
                (file_path, sort_key),
            ).fetchone()
            if not existing or existing[0] != payload:
                raise ValueError(
                    f"stable-key collision in {file_path}: {sort_key}"
                ) from None
        self.pending += 1
        if self.pending >= 100_000:
            self.connection.commit()
            self.pending = 0

    def write_files(self, output_dir: Path) -> list[dict]:
        self.connection.commit()
        metadata: list[dict] = []
        all_specs = {**NODE_FILES, **RELATIONSHIP_FILES}
        for file_path, spec in sorted(all_specs.items()):
            target = output_dir / file_path
            target.parent.mkdir(parents=True, exist_ok=True)
            row_count = 0
            with target.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(
                    handle,
                    dialect="excel",
                    lineterminator="\n",
                    quoting=csv.QUOTE_MINIMAL,
                )
                writer.writerow(spec["header"])
                cursor = self.connection.execute(
                    "SELECT payload FROM staged_rows "
                    "WHERE file_path = ? ORDER BY sort_key",
                    (file_path,),
                )
                for (payload,) in cursor:
                    writer.writerow(json.loads(payload))
                    row_count += 1
            item = {
                "path": file_path,
                "header": spec["header"],
                "row_count": row_count,
                "bytes": target.stat().st_size,
                "sha256": sha256_file(target),
                "kind": "node" if file_path in NODE_FILES else "relationship",
            }
            if file_path in NODE_FILES:
                item["entity"] = spec["entity"]
                item["namespace"] = spec["namespace"]
            else:
                item["type"] = spec["type"]
                item["start_namespace"] = spec["start_namespace"]
                item["end_namespace"] = spec["end_namespace"]
            metadata.append(item)
        return metadata

    def close(self) -> None:
        self.connection.close()


def _load_registry() -> dict:
    registry = json.loads(SOURCE_WORK_REGISTRY.read_text(encoding="utf-8"))
    works = registry.get("source_works")
    sources = registry.get("sources")
    if not isinstance(works, list) or len(works) != 34:
        raise ValueError("source_work_registry.json must contain exactly 34 works")
    if not isinstance(sources, list):
        raise ValueError("source_work_registry.json sources must be a list")

    by_pair: dict[tuple[str, str], dict] = {}
    by_id: dict[str, dict] = {}
    for work in works:
        pair = (work["tradition"], work["canonical_source"])
        work_id = work["source_work_id"]
        if pair in by_pair or work_id in by_id:
            raise ValueError(f"duplicate source-work registry identity: {work_id}")
        if work["tradition"] not in CANONICAL_TRADITIONS:
            raise ValueError(f"unsupported registry tradition: {work['tradition']}")
        by_pair[pair] = work
        by_id[work_id] = work

    source_by_slug: dict[str, dict] = {}
    for source in sources:
        slug = source["slug"]
        if slug in source_by_slug:
            raise ValueError(f"duplicate source slug: {slug}")
        source_by_slug[slug] = source

    registry["_by_pair"] = by_pair
    registry["_by_id"] = by_id
    registry["_source_by_slug"] = source_by_slug
    return registry


def _source_for_provenance(registry: dict, provenance: str) -> dict:
    matches = []
    for source in registry["sources"]:
        if any(
            provenance == prefix
            or provenance.startswith(prefix + ":")
            or provenance.startswith(prefix + "/")
            for prefix in source["provenance_prefixes"]
        ):
            matches.append(source)
    if len(matches) != 1:
        raise ValueError(
            f"provenance_source must resolve exactly once: {provenance!r}"
        )
    return matches[0]


def _resolve_work(registry: dict, row: dict) -> tuple[dict, dict]:
    tradition = row["tradition"].strip()
    source_name = row["source"].strip()
    work = registry["_by_pair"].get((tradition, source_name))
    if not work:
        raise ValueError(
            f"unregistered source/tradition pair: {(tradition, source_name)!r}"
        )
    supplied_id = row["source_work_id"].strip()
    if tradition == "Imami" and not supplied_id:
        raise ValueError(
            f"Imami row {row['record_id']!r} lacks required source_work_id"
        )
    if supplied_id and supplied_id != work["source_work_id"]:
        raise ValueError(
            f"source_work_id mismatch for {row['record_id']!r}: "
            f"{supplied_id!r} != {work['source_work_id']!r}"
        )
    upstream = _source_for_provenance(
        registry, row["provenance_source"].strip()
    )
    if upstream["slug"] != work["source_slug"]:
        raise ValueError(
            f"source/provenance mismatch for {row['record_id']!r}: "
            f"{work['source_slug']!r} != {upstream['slug']!r}"
        )
    return work, upstream


def _structure_nodes(row: dict, work: dict, source_slug: str) -> tuple[dict | None, dict | None]:
    collection_id = f"collection:{work['source_work_id']}"
    provenance = row["provenance_source"].strip()
    volume = row["volume"].strip()
    chapter_no = row["chapter_no"].strip()
    chapter_name = row["chapter"].strip()
    provider_file_id = row["provider_file_id"].strip()
    provider_book_id = row["provider_book_id"].strip()
    book: dict | None = None
    chapter: dict | None = None

    if source_slug == "sunnah-com" and chapter_no:
        book_id = f"book:{stable_hash(collection_id, 'k6-book', chapter_no)}"
        book = {
            "id": book_id,
            "number": chapter_no,
            "name": chapter_name,
            "volume": "",
            "provider_file_id": "",
            "provider_book_id": "",
        }
    elif source_slug == "thaqalayn-api":
        provider_key = provider_file_id or provider_book_id
        if provider_key:
            book_id = f"book:{stable_hash(collection_id, 'thaqalayn', provider_key, volume)}"
            book = {
                "id": book_id,
                "number": provider_file_id,
                "name": row["source_display_label"].strip() or volume,
                "volume": volume,
                "provider_file_id": provider_file_id,
                "provider_book_id": provider_book_id,
            }
        if chapter_no:
            match = THAQALAYN_URL_RE.fullmatch(row["url"].strip())
            if not match:
                raise ValueError(
                    f"Thaqalayn row {row['record_id']!r} lacks a parseable "
                    "provider chapter URL"
                )
            (
                provider_url_book,
                provider_category_number,
                provider_chapter_number,
                _provider_hadith_number,
            ) = match.groups()
            if provider_category_number != chapter_no:
                raise ValueError(
                    f"Thaqalayn row {row['record_id']!r} category/URL mismatch"
                )
            parent_key = book["id"] if book else collection_id
            provider_chapter_locator = (
                f"{provider_url_book}/{provider_category_number}/"
                f"{provider_chapter_number}"
            )
            chapter = {
                "id": (
                    "chapter:"
                    + stable_hash(
                        parent_key,
                        "thaqalayn",
                        provider_category_number,
                        provider_chapter_number,
                    )
                ),
                "number": provider_chapter_number,
                "category_number": provider_category_number,
                "provider_chapter_locator": provider_chapter_locator,
                "name": chapter_name,
            }
    elif source_slug in {
        "jami-sahih-rabi-openiti",
        "musnad-zayd-openiti",
        "musnad-rida-openiti",
    }:
        if volume:
            book_id = f"book:{stable_hash(collection_id, 'openiti-volume', volume)}"
            book = {
                "id": book_id,
                "number": volume,
                "name": f"Volume {volume}",
                "volume": volume,
                "provider_file_id": "",
                "provider_book_id": "",
            }
        if chapter_no:
            parent_key = book["id"] if book else collection_id
            normalized_heading = unicodedata.normalize("NFC", chapter_name)
            chapter = {
                "id": (
                    "chapter:"
                    + stable_hash(
                        parent_key,
                        "openiti-heading",
                        chapter_no,
                        normalized_heading,
                    )
                ),
                "number": chapter_no,
                "category_number": "",
                "provider_chapter_locator": (
                    f"openiti-local:{chapter_no}:"
                    f"{sha256_text(normalized_heading)}"
                ),
                "name": chapter_name,
            }
    elif source_slug == "sheikahmad-pure-canon" and any(
        (volume, chapter_no, chapter_name, provider_file_id, provider_book_id)
    ):
        raise ValueError(
            f"Pure Canon row {row['record_id']!r} contains unsupported "
            "structure fields; add an evidence-backed mapping before export"
        )

    if book:
        book["collection_id"] = collection_id
        book["provenance"] = provenance
    if chapter:
        chapter["collection_id"] = collection_id
        chapter["book_id"] = book["id"] if book else ""
        chapter["provenance"] = provenance
    return book, chapter


def _support_files(output_dir: Path, graph_files: list[dict]) -> list[dict]:
    registry_target = output_dir / "source_work_registry.json"
    shutil.copyfile(SOURCE_WORK_REGISTRY, registry_target)

    node_paths = [
        item["path"] for item in graph_files if item["kind"] == "node"
    ]
    relationship_paths = [
        item["path"] for item in graph_files if item["kind"] == "relationship"
    ]
    def windows_path(value: str) -> str:
        return value.replace("/", chr(92))

    multiline = ",".join(
        f'"$bundleDir\\{windows_path(path)}"' for path in TEXT_MULTILINE_FILES
    )
    node_args = ",\n".join(
        f'    "--nodes=$bundleDir\\{windows_path(path)}"'
        for path in node_paths
    )
    relationship_args = ",\n".join(
        f'    "--relationships=$bundleDir\\{windows_path(path)}"'
        for path in relationship_paths
    )
    loader = f"""param(
    [Parameter(Mandatory = $true)][string]$Database,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$bundleDir = $PSScriptRoot
$versionText = (& neo4j-admin --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {{ throw "neo4j-admin is unavailable" }}
if ($versionText -notmatch '(?<year>20[0-9]{{2}})[.](?<month>[0-9]{{2}})') {{
    throw "Neo4j calendar version 2026.02 or newer is required: $versionText"
}}
$neo4jVersion = [version]("$($Matches.year).$([int]$Matches.month)")
if ($neo4jVersion -lt [version]"2026.2") {{
    throw "Neo4j 2026.02 or newer is required: $versionText"
}}
$multilineFiles = @({multiline}) -join ","
$commonArgs = @(
    "database", "import", "full",
    "--id-type=string",
    "--input-encoding=UTF-8",
    "--bad-tolerance=0",
    "--skip-duplicate-nodes=false",
    "--skip-bad-relationships=false",
    "--overwrite-destination=false",
    "--multiline-fields=$multilineFiles",
    "--multiline-fields-format=v2",
{node_args},
{relationship_args}
)

& neo4j-admin @commonArgs "--dry-run=true" $Database
if ($LASTEXITCODE -ne 0) {{ throw "neo4j-admin dry run failed" }}
if (-not $Execute) {{
    Write-Host "Dry run passed. Re-run with -Execute to perform the import."
    exit 0
}}
& neo4j-admin @commonArgs "--dry-run=false" $Database
if ($LASTEXITCODE -ne 0) {{ throw "neo4j-admin import failed" }}
Write-Host "Import complete. Apply post_import_schema.cypher separately."
"""
    loader_path = output_dir / "neo4j-admin-import.ps1"
    loader_path.write_bytes(loader.replace("\r\n", "\n").encode("utf-8"))

    constraints = [
        ("Hadith", "hadith_id"),
        ("Narrator", "narrator_id"),
        ("Source", "source_id"),
        ("Collection", "collection_id"),
        ("Book", "book_id"),
        ("Chapter", "chapter_id"),
        ("Tradition", "tradition_id"),
        ("Chain", "chain_id"),
        ("NameMention", "name_mention_id"),
        ("Translation", "translation_id"),
        ("Alias", "alias_id"),
        ("Evidence", "evidence_id"),
        ("Citation", "citation_id"),
        ("Biography", "biography_id"),
        ("Place", "place_id"),
        ("Event", "event_id"),
    ]
    cypher_lines = [
        (
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
        )
        for label, name in constraints
    ]
    cypher_lines.extend(
        [
            "CREATE INDEX narrator_scholar_indx IF NOT EXISTS "
            "FOR (n:Narrator) ON (n.scholar_indx);",
            "CREATE INDEX collection_source_work_id IF NOT EXISTS "
            "FOR (n:Collection) ON (n.source_work_id);",
            "CREATE INDEX hadith_record_id IF NOT EXISTS "
            "FOR (n:Hadith) ON (n.record_id);",
        ]
    )
    cypher_path = output_dir / "post_import_schema.cypher"
    cypher_path.write_bytes(("\n".join(cypher_lines) + "\n").encode("utf-8"))

    support: list[dict] = []
    for path in (
        registry_target,
        loader_path,
        cypher_path,
    ):
        support.append(
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "kind": "support",
            }
        )
    return sorted(support, key=lambda item: item["path"])


def export_bundle(
    input_path: Path | str,
    rawis_path: Path | str,
    output_dir: Path | str,
    source_release_state: str = DEFAULT_SOURCE_RELEASE_STATE,
    *,
    curation_manifest_path: Path | str | None = None,
    coverage_scope: str = "complete",
    validate: bool = True,
) -> dict:
    """Export one immutable graph bundle from schema-v2 and rawi inputs."""
    input_path = Path(input_path)
    rawis_path = Path(rawis_path)
    output_dir = Path(output_dir)
    _assert_allowed_input(input_path, "dataset")
    _assert_allowed_input(rawis_path, "rawis")
    curation_manifest: dict | None = None
    if curation_manifest_path is not None:
        curation_manifest_path = Path(curation_manifest_path)
        _assert_allowed_input(curation_manifest_path, "curation manifest")
        curation_manifest = json.loads(
            curation_manifest_path.read_text(encoding="utf-8")
        )
        if curation_manifest.get("schema_version") != 2:
            raise ValueError("curation manifest schema_version must be 2")
        if curation_manifest.get("dataset_schema") != UNIFIED_COLUMNS:
            raise ValueError("curation manifest dataset_schema does not match input")
        if not isinstance(curation_manifest.get("ready_for_full_load"), bool):
            raise ValueError(
                "curation manifest ready_for_full_load must be boolean"
            )
    elif source_release_state == "development_nonrelease":
        raise ValueError(
            "development_nonrelease exports require --curation-manifest"
        )
    if not source_release_state.strip():
        raise ValueError("source_release_state must be explicit and nonblank")
    if coverage_scope not in {"complete", "fixture_partial"}:
        raise ValueError("coverage_scope must be complete or fixture_partial")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be absent or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = _load_registry()
    staging_path = output_dir / ".graph_export_staging.sqlite3"
    stage = _Stage(staging_path)
    narrator_ids: set[int] = set()
    seen_records: set[str] = set()
    source_counts: Counter[str] = Counter()
    source_slug_counts: Counter[str] = Counter()
    tradition_counts: Counter[str] = Counter()
    input_translation_status_counts: Counter[str] = Counter()
    exported_translation_status_counts: Counter[str] = Counter()
    translation_disposition_counts: Counter[str] = Counter()
    extraction_counts: Counter[str] = Counter()
    extraction_failures: list[dict] = []
    present_exclusions: set[str] = set()
    represented_work_ids: set[str] = set()
    indexed_learning_evidence: dict[tuple[int, int], set[str]] = {}
    indexed_learning_assertion_tokens = 0
    indexed_learning_duplicate_fields = 0
    indexed_learning_duplicate_occurrences = 0
    indexed_learning_missing_pairs = 0
    indexed_learning_self_pairs = 0
    indexed_learning_corroborated_pairs = 0

    try:
        narrator_source_id = "source:narrator-lexicon"
        narrator_source = registry["_source_by_slug"]["narrator-lexicon"]
        stage.put(
            "nodes/sources.csv",
            narrator_source_id,
            [
                narrator_source_id,
                narrator_source["slug"],
                narrator_source["name"],
                source_release_state,
                "Source",
            ],
        )
        with _open_csv(rawis_path) as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != RAWI_COLUMNS:
                raise ValueError(
                    "rawis CSV must use the exact lossless profile schema; "
                    f"received {reader.fieldnames!r}"
                )
            for line_no, row in enumerate(reader, start=2):
                _assert_exact_dict_row(
                    row,
                    RAWI_COLUMNS,
                    role="rawis",
                    line_no=line_no,
                )
                token = str(row.get("scholar_indx") or "").strip()
                if not token.isdigit() or int(token) <= 0:
                    raise ValueError(
                        f"invalid rawi scholar_indx at line {line_no}: {token!r}"
                    )
                scholar_indx = int(token)
                if scholar_indx in narrator_ids:
                    raise ValueError(
                        f"duplicate rawi scholar_indx at line {line_no}: "
                        f"{scholar_indx}"
                    )
                narrator_ids.add(scholar_indx)
                narrator_id = f"narrator:rawi:{scholar_indx}"
                name = str(row.get("name") or "")
                stage.put(
                    "nodes/narrators.csv",
                    narrator_id,
                    [
                        narrator_id,
                        str(scholar_indx),
                        name,
                        narrator_source_id,
                        _row_labels("Narrator", "Person"),
                    ],
                )
                alias_id = f"alias:narrator:rawi:{scholar_indx}:canonical"
                stage.put(
                    "nodes/aliases.csv",
                    alias_id,
                    [
                        alias_id,
                        name,
                        name_normalize(name),
                        "canonical_name",
                        "narrator-lexicon",
                        "Alias",
                    ],
                )
                stage.put(
                    "relationships/alias_of.csv",
                    f"{alias_id}\x1f{narrator_id}",
                    [alias_id, narrator_id, "narrator-lexicon", "ALIAS_OF"],
                )
                stage.put(
                    "relationships/narrator_from_source.csv",
                    narrator_id,
                    [
                        narrator_id,
                        narrator_source_id,
                        "narrator-lexicon",
                        "NARRATOR_FROM_SOURCE",
                    ],
                )
                biography_id = f"biography:narrator-lexicon:{scholar_indx}"
                stage.put(
                    "nodes/biographies.csv",
                    biography_id,
                    [
                        biography_id,
                        narrator_id,
                        str(scholar_indx),
                        "rawi_lexicon_profile",
                        narrator_source_id,
                        f"all_rawis.csv#scholar_indx={scholar_indx}",
                        "",
                        RAWI_PROFILE_REVIEW_STATE,
                        RAWI_PROFILE_PROVENANCE,
                        _rawi_profile_hash(row),
                        *[
                            str(row.get(column) or "")
                            for column in RAWI_PROFILE_COLUMNS
                        ],
                        _row_labels("Biography", "Profile", "SourceProfile"),
                    ],
                )
                stage.put(
                    "relationships/biography_of.csv",
                    f"{biography_id}\x1f{narrator_id}",
                    [
                        biography_id,
                        narrator_id,
                        RAWI_PROFILE_REVIEW_STATE,
                        RAWI_PROFILE_PROVENANCE,
                        "BIOGRAPHY_OF",
                    ],
                )
                stage.put(
                    "relationships/biography_from_source.csv",
                    f"{biography_id}\x1f{narrator_source_id}",
                    [
                        biography_id,
                        narrator_source_id,
                        RAWI_PROFILE_REVIEW_STATE,
                        RAWI_PROFILE_PROVENANCE,
                        "BIOGRAPHY_FROM_SOURCE",
                    ],
                )
                teachers, teacher_tokens, teacher_duplicates = (
                    _parse_indexed_narrators(
                        row["teachers_inds"],
                        field="teachers_inds",
                        line_no=line_no,
                    )
                )
                indexed_learning_assertion_tokens += teacher_tokens
                indexed_learning_duplicate_fields += int(
                    teacher_duplicates > 0
                )
                indexed_learning_duplicate_occurrences += teacher_duplicates
                for teacher_indx in teachers:
                    indexed_learning_evidence.setdefault(
                        (scholar_indx, teacher_indx), set()
                    ).add("teachers_inds")
                students, student_tokens, student_duplicates = (
                    _parse_indexed_narrators(
                        row["students_inds"],
                        field="students_inds",
                        line_no=line_no,
                    )
                )
                indexed_learning_assertion_tokens += student_tokens
                indexed_learning_duplicate_fields += int(
                    student_duplicates > 0
                )
                indexed_learning_duplicate_occurrences += student_duplicates
                for student_indx in students:
                    indexed_learning_evidence.setdefault(
                        (student_indx, scholar_indx), set()
                    ).add("students_inds")

        for (student_indx, teacher_indx), evidence_fields in sorted(
            indexed_learning_evidence.items()
        ):
            if (
                student_indx not in narrator_ids
                or teacher_indx not in narrator_ids
            ):
                indexed_learning_missing_pairs += 1
                continue
            if student_indx == teacher_indx:
                indexed_learning_self_pairs += 1
                continue
            student_id = f"narrator:rawi:{student_indx}"
            teacher_id = f"narrator:rawi:{teacher_indx}"
            corroborated = len(evidence_fields) == 2
            indexed_learning_corroborated_pairs += int(corroborated)
            stage.put(
                "relationships/student_of.csv",
                f"{student_id}\x1f{teacher_id}",
                [
                    student_id,
                    teacher_id,
                    "|".join(sorted(evidence_fields)),
                    str(len(evidence_fields)),
                    _bool(corroborated),
                    RAWI_PROFILE_REVIEW_STATE,
                    RAWI_PROFILE_PROVENANCE,
                    "STUDENT_OF",
                ],
            )

        with _open_csv(input_path) as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != UNIFIED_COLUMNS:
                raise ValueError(
                    "dataset must use exact schema-v2 37-column header; "
                    f"received {reader.fieldnames!r}"
                )
            for line_no, row in enumerate(reader, start=2):
                _assert_exact_dict_row(
                    row,
                    UNIFIED_COLUMNS,
                    role="dataset",
                    line_no=line_no,
                )
                record_id = row["record_id"].strip()
                source_record_id = row["source_record_id"].strip()
                provenance = row["provenance_source"].strip()
                if not record_id or not source_record_id or not provenance:
                    raise ValueError(
                        f"row {line_no} lacks record/source/provenance identity"
                    )
                if record_id in seen_records:
                    raise ValueError(f"duplicate record_id: {record_id}")
                seen_records.add(record_id)

                work, upstream_source = _resolve_work(registry, row)
                tradition = row["tradition"].strip()
                source_name = row["source"].strip()
                source_slug = upstream_source["slug"]
                source_id = f"source:{source_slug}"
                collection_id = f"collection:{work['source_work_id']}"
                represented_work_ids.add(work["source_work_id"])
                hadith_id = f"hadith:{record_id}"
                tradition_node_id = tradition_id(tradition)
                exclusion_reason = SOURCE_QUALITY_EXCLUSIONS.get(record_id, "")
                excluded = bool(exclusion_reason)
                if excluded:
                    present_exclusions.add(record_id)

                source_counts[source_name] += 1
                source_slug_counts[source_slug] += 1
                tradition_counts[tradition] += 1
                status = row["translation_status"].strip()
                input_translation_status_counts[status or "<blank>"] += 1
                translation_review_state = row[
                    "translation_review_status"
                ].strip()
                translation_source = row["translation_source"].strip()
                if excluded:
                    translation_disposition = "omitted_source_quality_exclusion"
                elif not row["text_en"].strip():
                    translation_disposition = "omitted_missing_text"
                elif not translation_source or not translation_review_state:
                    translation_disposition = "omitted_missing_provenance"
                elif translation_review_state == "machine_unreviewed":
                    translation_disposition = "omitted_machine_candidate"
                else:
                    translation_disposition = "exported_source_surface"
                translation_disposition_counts[translation_disposition] += 1

                stage.put(
                    "nodes/sources.csv",
                    source_id,
                    [
                        source_id,
                        source_slug,
                        upstream_source["name"],
                        source_release_state,
                        "Source",
                    ],
                )
                stage.put(
                    "nodes/traditions.csv",
                    tradition_node_id,
                    [
                        tradition_node_id,
                        tradition,
                        tradition.lower(),
                        _row_labels("Tradition", "ReligiousTradition"),
                    ],
                )
                stage.put(
                    "nodes/collections.csv",
                    collection_id,
                    [
                        collection_id,
                        work["source_work_id"],
                        work["slug"],
                        source_name,
                        tradition,
                        source_id,
                        "Collection",
                    ],
                )
                stage.put(
                    "relationships/collection_in_tradition.csv",
                    collection_id,
                    [
                        collection_id,
                        tradition_node_id,
                        provenance,
                        "COLLECTION_IN_TRADITION",
                    ],
                )
                stage.put(
                    "relationships/collection_from_source.csv",
                    collection_id,
                    [
                        collection_id,
                        source_id,
                        provenance,
                        "COLLECTION_FROM_SOURCE",
                    ],
                )

                text_ar = row["text_ar"]
                arabic_hash = sha256_text(text_ar)
                stage.put(
                    "nodes/hadiths.csv",
                    hadith_id,
                    [
                        hadith_id,
                        record_id,
                        source_record_id,
                        source_name,
                        work["source_work_id"],
                        source_id,
                        tradition,
                        tradition_node_id,
                        row["hadith_no"],
                        text_ar,
                        arabic_hash,
                        row["sanad"],
                        row["matn_ar"],
                        row["url"],
                        row["page_ref"],
                        status,
                        provenance,
                        translation_disposition,
                        _bool(excluded),
                        exclusion_reason,
                        _row_labels("Hadith", "Report"),
                    ],
                )
                for path, end_id, edge_type in (
                    (
                        "relationships/hadith_in_collection.csv",
                        collection_id,
                        "HADITH_IN_COLLECTION",
                    ),
                    (
                        "relationships/hadith_in_tradition.csv",
                        tradition_node_id,
                        "HADITH_IN_TRADITION",
                    ),
                    (
                        "relationships/hadith_from_source.csv",
                        source_id,
                        "HADITH_FROM_SOURCE",
                    ),
                ):
                    stage.put(
                        path,
                        hadith_id,
                        [hadith_id, end_id, provenance, edge_type],
                    )

                report_evidence_id = f"evidence:report:{record_id}"
                stage.put(
                    "nodes/evidence.csv",
                    report_evidence_id,
                    [
                        report_evidence_id,
                        "source_record",
                        source_record_id,
                        provenance,
                        "",
                        "",
                        row["url"],
                        row["page_ref"],
                        arabic_hash,
                        "source_locator_unreviewed",
                        _bool(excluded),
                        exclusion_reason,
                        "Evidence",
                    ],
                )
                stage.put(
                    "relationships/report_supported_by.csv",
                    hadith_id,
                    [
                        hadith_id,
                        report_evidence_id,
                        provenance,
                        "REPORT_SUPPORTED_BY",
                    ],
                )
                stage.put(
                    "relationships/evidence_from_source.csv",
                    report_evidence_id,
                    [
                        report_evidence_id,
                        source_id,
                        provenance,
                        "EVIDENCE_FROM_SOURCE",
                    ],
                )

                book, chapter = _structure_nodes(row, work, source_slug)
                if book:
                    stage.put(
                        "nodes/books.csv",
                        book["id"],
                        [
                            book["id"],
                            collection_id,
                            book["number"],
                            book["name"],
                            book["volume"],
                            book["provider_file_id"],
                            book["provider_book_id"],
                            provenance,
                            "Book",
                        ],
                    )
                    stage.put(
                        "relationships/book_in_collection.csv",
                        book["id"],
                        [
                            book["id"],
                            collection_id,
                            provenance,
                            "BOOK_IN_COLLECTION",
                        ],
                    )
                    stage.put(
                        "relationships/hadith_in_book.csv",
                        hadith_id,
                        [hadith_id, book["id"], provenance, "HADITH_IN_BOOK"],
                    )
                if chapter:
                    stage.put(
                        "nodes/chapters.csv",
                        chapter["id"],
                        [
                            chapter["id"],
                            collection_id,
                            chapter["book_id"],
                            chapter["number"],
                            chapter["category_number"],
                            chapter["provider_chapter_locator"],
                            chapter["name"],
                            provenance,
                            "Chapter",
                        ],
                    )
                    stage.put(
                        "relationships/hadith_in_chapter.csv",
                        hadith_id,
                        [
                            hadith_id,
                            chapter["id"],
                            provenance,
                            "HADITH_IN_CHAPTER",
                        ],
                    )
                    if book:
                        stage.put(
                            "relationships/chapter_in_book.csv",
                            chapter["id"],
                            [
                                chapter["id"],
                                book["id"],
                                provenance,
                                "CHAPTER_IN_BOOK",
                            ],
                        )

                if excluded:
                    extraction_counts["quality_excluded"] += 1
                    if record_id == "thaqalayn:06840b21d9e61e1ab351aec4":
                        extraction_counts["paratext_chain_omitted"] += 1
                        continue

                if translation_disposition == "exported_source_surface":
                    translation_id = f"translation:{record_id}:en"
                    exported_translation_status_counts[status or "<blank>"] += 1
                    stage.put(
                        "nodes/translations.csv",
                        translation_id,
                        [
                            translation_id,
                            "en",
                            row["text_en"],
                            status,
                            translation_source,
                            row["translation_model"],
                            translation_review_state,
                            source_record_id,
                            arabic_hash,
                            provenance,
                            "false",
                            "Translation",
                        ],
                    )
                    stage.put(
                        "relationships/translation_of.csv",
                        translation_id,
                        [
                            translation_id,
                            hadith_id,
                            provenance,
                            "TRANSLATION_OF",
                        ],
                    )
                    translation_evidence_id = (
                        f"evidence:translation:{record_id}"
                    )
                    stage.put(
                        "nodes/evidence.csv",
                        translation_evidence_id,
                        [
                            translation_evidence_id,
                            "translation_provenance",
                            source_record_id,
                            provenance,
                            translation_source,
                            row["translation_model"],
                            row["url"],
                            row["page_ref"],
                            arabic_hash,
                            translation_review_state,
                            "false",
                            "",
                            "Evidence",
                        ],
                    )
                    stage.put(
                        "relationships/translation_supported_by.csv",
                        translation_id,
                        [
                            translation_id,
                            translation_evidence_id,
                            provenance,
                            "TRANSLATION_SUPPORTED_BY",
                        ],
                    )
                    stage.put(
                        "relationships/evidence_from_source.csv",
                        translation_evidence_id,
                        [
                            translation_evidence_id,
                            source_id,
                            provenance,
                            "EVIDENCE_FROM_SOURCE",
                        ],
                    )

                attribution = row["attributed_to"].strip()
                if attribution and not excluded:
                    alias_id = (
                        "alias:attribution:"
                        + stable_hash(tradition, unicodedata.normalize("NFC", attribution))
                    )
                    stage.put(
                        "nodes/aliases.csv",
                        alias_id,
                        [
                            alias_id,
                            attribution,
                            name_normalize(attribution),
                            "attribution_surface",
                            "surface_normalization_v1",
                            "Alias",
                        ],
                    )
                    stage.put(
                        "relationships/attributed_to.csv",
                        f"{hadith_id}\x1f{alias_id}",
                        [hadith_id, alias_id, provenance, "ATTRIBUTED_TO"],
                    )

                try:
                    surface_branches = extract_isnad_branches(text_ar)
                except IsnadExtractionLimitError as error:
                    if error.projected <= EXPORT_ISNAD_BRANCH_LIMIT:
                        original_limit = (
                            isnad_extractor_module.MAX_ISNAD_BRANCHES
                        )
                        try:
                            isnad_extractor_module.MAX_ISNAD_BRANCHES = (
                                EXPORT_ISNAD_BRANCH_LIMIT
                            )
                            surface_branches = extract_isnad_branches(text_ar)
                        except IsnadExtractionLimitError as retry_error:
                            extraction_counts["limit_failures"] += 1
                            extraction_failures.append(
                                {
                                    "record_id": record_id,
                                    "reason": str(retry_error),
                                }
                            )
                            continue
                        finally:
                            isnad_extractor_module.MAX_ISNAD_BRANCHES = (
                                original_limit
                            )
                        extraction_counts["expanded_limit_reports"] += 1
                    else:
                        extraction_counts["limit_failures"] += 1
                        extraction_failures.append(
                            {"record_id": record_id, "reason": str(error)}
                        )
                        continue
                empty_branch_count = sum(
                    1 for branch in surface_branches if not branch
                )
                if empty_branch_count:
                    extraction_counts["empty_branches_omitted"] += (
                        empty_branch_count
                    )
                    surface_branches = [
                        branch for branch in surface_branches if branch
                    ]
                if not surface_branches:
                    extraction_counts["not_extractable"] += 1
                    continue
                extraction_counts["reports_with_chains"] += 1
                extraction_counts["chains"] += len(surface_branches)
                resolved_branches = _parse_chain_indx(row["chain_indx"])
                fully_resolved = bool(resolved_branches) and (
                    len(resolved_branches) == len(surface_branches)
                    and all(
                        len(resolved) == len(surface)
                        for resolved, surface in zip(
                            resolved_branches, surface_branches
                        )
                    )
                    and all(
                        narrator in narrator_ids
                        for branch in resolved_branches
                        for narrator in branch
                    )
                )
                if resolved_branches and not fully_resolved:
                    extraction_counts["resolution_shape_mismatch"] += 1
                elif fully_resolved:
                    extraction_counts["fully_resolved_reports"] += 1

                extraction_method = "extract_isnad_unified"
                sanad_confidence = row["sanad_confidence"].strip()
                for branch_index, surfaces in enumerate(surface_branches):
                    chain_id = f"chain:{record_id}:{branch_index:04d}"
                    branch_resolved = (
                        resolved_branches[branch_index]
                        if fully_resolved
                        else []
                    )
                    stage.put(
                        "nodes/chains.csv",
                        chain_id,
                        [
                            chain_id,
                            hadith_id,
                            source_record_id,
                            str(branch_index),
                            str(len(surfaces)),
                            _bool(fully_resolved),
                            extraction_method,
                            sanad_confidence,
                            provenance,
                            "Chain",
                        ],
                    )
                    stage.put(
                        "relationships/has_chain.csv",
                        chain_id,
                        [
                            hadith_id,
                            chain_id,
                            str(branch_index),
                            source_record_id,
                            extraction_method,
                            sanad_confidence,
                            provenance,
                            "HAS_CHAIN",
                        ],
                    )
                    mention_ids: list[str] = []
                    for position, surface in enumerate(surfaces):
                        mention_id = (
                            f"mention:{record_id}:{branch_index:04d}:{position:04d}"
                        )
                        mention_ids.append(mention_id)
                        stage.put(
                            "nodes/name_mentions.csv",
                            mention_id,
                            [
                                mention_id,
                                hadith_id,
                                source_record_id,
                                chain_id,
                                str(branch_index),
                                str(position),
                                surface,
                                name_normalize(surface),
                                extraction_method,
                                sanad_confidence,
                                provenance,
                                "NameMention",
                            ],
                        )
                        stage.put(
                            "relationships/includes_mention.csv",
                            mention_id,
                            [
                                chain_id,
                                mention_id,
                                str(position),
                                str(branch_index),
                                source_record_id,
                                extraction_method,
                                sanad_confidence,
                                provenance,
                                "INCLUDES_MENTION",
                            ],
                        )
                        if fully_resolved:
                            narrator_id = (
                                f"narrator:rawi:{branch_resolved[position]}"
                            )
                            stage.put(
                                "relationships/resolves_to.csv",
                                mention_id,
                                [
                                    mention_id,
                                    narrator_id,
                                    chain_id,
                                    hadith_id,
                                    str(position),
                                    source_record_id,
                                    extraction_method,
                                    sanad_confidence,
                                    provenance,
                                    "RESOLVES_TO",
                                ],
                            )
                            stage.put(
                                "relationships/includes.csv",
                                mention_id,
                                [
                                    chain_id,
                                    narrator_id,
                                    str(position),
                                    str(branch_index),
                                    source_record_id,
                                    extraction_method,
                                    sanad_confidence,
                                    provenance,
                                    "INCLUDES",
                                ],
                            )
                    for position in range(len(mention_ids) - 1):
                        edge_key = (
                            f"{chain_id}\x1f{position:08d}\x1f{position + 1:08d}"
                        )
                        stage.put(
                            "relationships/next_in_chain.csv",
                            edge_key,
                            [
                                mention_ids[position],
                                mention_ids[position + 1],
                                chain_id,
                                hadith_id,
                                str(position),
                                str(position + 1),
                                source_record_id,
                                extraction_method,
                                sanad_confidence,
                                provenance,
                                "NEXT_IN_CHAIN",
                            ],
                        )
                        if fully_resolved:
                            student_id = (
                                f"narrator:rawi:{branch_resolved[position]}"
                            )
                            teacher_id = (
                                f"narrator:rawi:{branch_resolved[position + 1]}"
                            )
                            stage.put(
                                "relationships/narrated_from.csv",
                                edge_key,
                                [
                                    student_id,
                                    teacher_id,
                                    chain_id,
                                    hadith_id,
                                    str(position),
                                    str(position + 1),
                                    source_record_id,
                                    extraction_method,
                                    sanad_confidence,
                                    provenance,
                                    "NARRATED_FROM",
                                ],
                            )

        if curation_manifest is not None:
            expected_record_count = curation_manifest.get("record_count")
            if expected_record_count != len(seen_records):
                raise ValueError(
                    "curation manifest record_count mismatch: "
                    f"{expected_record_count!r} != {len(seen_records)}"
                )
            expected_sources = curation_manifest.get("source_counts")
            if expected_sources != dict(sorted(source_counts.items())):
                raise ValueError("curation manifest source_counts mismatch")
            expected_traditions = curation_manifest.get("tradition_counts")
            if expected_traditions != dict(sorted(tradition_counts.items())):
                raise ValueError("curation manifest tradition_counts mismatch")
        if coverage_scope == "complete":
            expected_work_ids = set(registry["_by_id"])
            if represented_work_ids != expected_work_ids:
                raise ValueError(
                    "complete coverage requires every registered source work; "
                    f"missing={sorted(expected_work_ids - represented_work_ids)}, "
                    f"extra={sorted(represented_work_ids - expected_work_ids)}"
                )
            if set(tradition_counts) != set(CANONICAL_TRADITIONS):
                raise ValueError(
                    "complete coverage requires every canonical tradition"
                )
            if present_exclusions != set(SOURCE_QUALITY_EXCLUSIONS):
                raise ValueError(
                    "complete coverage requires both source-quality exclusions"
                )
        graph_files = stage.write_files(output_dir)
    finally:
        stage.close()
        if staging_path.exists():
            staging_path.unlink()

    support_files = _support_files(output_dir, graph_files)
    total_nodes = sum(
        item["row_count"] for item in graph_files if item["kind"] == "node"
    )
    total_relationships = sum(
        item["row_count"]
        for item in graph_files
        if item["kind"] == "relationship"
    )
    exclusions = [
        {
            "record_id": record_id,
            "reason": reason,
            "present": record_id in present_exclusions,
            "handling": (
                "flagged Hadith/Evidence only; translation, attribution, and "
                "chain assertions omitted"
                if record_id == "thaqalayn:06840b21d9e61e1ab351aec4"
                else (
                    "flagged Hadith/Evidence; translation and attribution "
                    "omitted; source-surface chain retained when extractable"
                )
            ),
        }
        for record_id, reason in sorted(SOURCE_QUALITY_EXCLUSIONS.items())
    ]
    inputs = [
        {
            "role": "schema_v2_dataset",
            "path": _display_path(input_path),
            "bytes": input_path.stat().st_size,
            "sha256": sha256_file(input_path),
        },
        {
            "role": "rawi_registry",
            "path": _display_path(rawis_path),
            "bytes": rawis_path.stat().st_size,
            "sha256": sha256_file(rawis_path),
        },
        {
            "role": "source_work_registry",
            "path": _display_path(SOURCE_WORK_REGISTRY),
            "bytes": SOURCE_WORK_REGISTRY.stat().st_size,
            "sha256": sha256_file(SOURCE_WORK_REGISTRY),
        },
        {
            "role": "isnad_extractor",
            "path": _display_path(EXTRACTOR_PATH),
            "bytes": EXTRACTOR_PATH.stat().st_size,
            "sha256": sha256_file(EXTRACTOR_PATH),
        },
        {
            "role": "graph_exporter",
            "path": _display_path(EXPORTER_PATH),
            "bytes": EXPORTER_PATH.stat().st_size,
            "sha256": sha256_file(EXPORTER_PATH),
        },
        {
            "role": "graph_contract",
            "path": _display_path(CONTRACT_PATH),
            "bytes": CONTRACT_PATH.stat().st_size,
            "sha256": sha256_file(CONTRACT_PATH),
        },
        {
            "role": "graph_validator",
            "path": _display_path(VALIDATOR_PATH),
            "bytes": VALIDATOR_PATH.stat().st_size,
            "sha256": sha256_file(VALIDATOR_PATH),
        },
    ]
    curation_snapshot = None
    if curation_manifest is not None:
        assert curation_manifest_path is not None
        inputs.append(
            {
                "role": "curation_manifest",
                "path": _display_path(curation_manifest_path),
                "bytes": curation_manifest_path.stat().st_size,
                "sha256": sha256_file(curation_manifest_path),
            }
        )
        curation_snapshot = {
            "path": _display_path(curation_manifest_path),
            "sha256": sha256_file(curation_manifest_path),
            "schema_version": curation_manifest["schema_version"],
            "record_count": curation_manifest["record_count"],
            "candidate_content_sha256": curation_manifest.get(
                "candidate_content_sha256", ""
            ),
            "ready_for_full_load": curation_manifest["ready_for_full_load"],
            "full_load_gates": curation_manifest.get("full_load_gates", {}),
            "release_blockers": curation_manifest.get("release_blockers", {}),
            "source_counts": curation_manifest.get("source_counts", {}),
            "tradition_counts": curation_manifest.get("tradition_counts", {}),
        }
    manifest = {
        "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_version": BUNDLE_VERSION,
        "input_schema_version": 2,
        "input_schema": UNIFIED_COLUMNS,
        "source_release_state": source_release_state,
        "coverage": {
            "scope": coverage_scope,
            "traditions": sorted(tradition_counts),
            "source_work_ids": sorted(represented_work_ids),
        },
        "inputs": inputs,
        "curation_snapshot": curation_snapshot,
        "generation": {
            "command": (
                "python datasets/hadith-data/neo4j_export/export_bundle.py "
                f"--input {_display_path(input_path)} "
                f"--rawis {_display_path(rawis_path)} "
                "--output <new-empty-bundle-directory> "
                f"--source-release-state {source_release_state}"
                + (
                    " --curation-manifest "
                    + _display_path(curation_manifest_path)
                    if curation_manifest_path is not None
                    else ""
                )
                + (
                    " --coverage-scope fixture_partial"
                    if coverage_scope == "fixture_partial"
                    else ""
                )
            ),
            "deterministic_sort": "UTF-8 stable namespaced row key",
            "staging": "SQLite primary-key collision audit",
        },
        "content_sha256": graph_content_hash(graph_files, support_files),
        "files": sorted(graph_files, key=lambda item: item["path"]),
        "support_files": support_files,
        "totals": {
            "nodes": total_nodes,
            "relationships": total_relationships,
            "hadith_records": len(seen_records),
            "rawi_records": len(narrator_ids),
        },
        "counts": {
            "by_tradition": dict(sorted(tradition_counts.items())),
            "by_collection": dict(sorted(source_counts.items())),
            "by_provenance_source": dict(sorted(source_slug_counts.items())),
            "input_translation_status": dict(
                sorted(input_translation_status_counts.items())
            ),
            "exported_translation_status": dict(
                sorted(exported_translation_status_counts.items())
            ),
            "translation_disposition": dict(
                sorted(translation_disposition_counts.items())
            ),
        },
        "narrator_profiles": {
            "profile_nodes": len(narrator_ids),
            "raw_profile_fields": list(RAWI_PROFILE_COLUMNS),
            "profile_review_state": RAWI_PROFILE_REVIEW_STATE,
            "profile_provenance": RAWI_PROFILE_PROVENANCE,
            "indexed_learning_assertion_tokens": (
                indexed_learning_assertion_tokens
            ),
            "indexed_learning_duplicate_fields": (
                indexed_learning_duplicate_fields
            ),
            "indexed_learning_duplicate_occurrences": (
                indexed_learning_duplicate_occurrences
            ),
            "unique_indexed_pairs": len(indexed_learning_evidence),
            "exported_student_of_pairs": (
                len(indexed_learning_evidence)
                - indexed_learning_missing_pairs
                - indexed_learning_self_pairs
            ),
            "corroborated_pairs": indexed_learning_corroborated_pairs,
            "omitted_missing_endpoint_pairs": indexed_learning_missing_pairs,
            "omitted_self_pairs": indexed_learning_self_pairs,
            "direction": "student_to_teacher",
            "evidence_policy": (
                "teachers_inds on the student row and students_inds on the "
                "teacher row are aggregated without claiming citation review"
            ),
        },
        "exclusions": exclusions,
        "empty_gated_entities": [
            {"entity": entity, "reason": reason}
            for entity, reason in sorted(EMPTY_GATED_ENTITIES.items())
        ],
        "candidate_inputs_excluded": list(CANDIDATE_PATH_MARKERS),
        "extraction": {
            "counts": dict(sorted(extraction_counts.items())),
            "limit_failures": sorted(
                extraction_failures, key=lambda item: item["record_id"]
            ),
            "resolution_policy": (
                "all branches and lengths must match chain_indx and every "
                "rawi endpoint must exist; no partial resolution"
            ),
            "default_branch_limit": DEFAULT_ISNAD_BRANCH_LIMIT,
            "export_branch_limit": EXPORT_ISNAD_BRANCH_LIMIT,
            "empty_branch_policy": (
                "zero-occurrence branches carry no transmission evidence "
                "and are omitted before contiguous branch numbering"
            ),
        },
        "registry": {
            "path": "source_work_registry.json",
            "version": registry["registry_version"],
            "work_count": len(registry["source_works"]),
        },
        "import": {
            "command": (
                "powershell -File .\\neo4j-admin-import.ps1 "
                "-Database <database> [-Execute]"
            ),
            "dry_run_first": True,
            "id_type": "string",
            "bad_tolerance": 0,
            "skip_duplicate_nodes": False,
            "skip_bad_relationships": False,
            "overwrite_destination": False,
            "multiline_fields_format": "v2",
            "multiline_files": list(TEXT_MULTILINE_FILES),
            "minimum_neo4j_admin_version": "2026.02",
            "documentation_target": "2026.06",
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(deterministic_json_bytes(manifest))

    if validate:
        try:
            from .validate_bundle import validate_bundle
        except ImportError:  # pragma: no cover - direct script execution
            from validate_bundle import validate_bundle  # type: ignore
        report = validate_bundle(output_dir)
        if not report["import_ready"]:
            raise ValueError(
                "generated bundle failed validation: "
                + "; ".join(report["errors"][:10])
            )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--rawis", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--curation-manifest",
        type=Path,
        help=(
            "Schema-v2 curation manifest to hash-bind and preserve release "
            "gates; required for development_nonrelease exports."
        ),
    )
    parser.add_argument(
        "--coverage-scope",
        choices=("complete", "fixture_partial"),
        default="complete",
        help="Require full registered coverage (default) or allow test fixtures.",
    )
    parser.add_argument(
        "--source-release-state",
        default=DEFAULT_SOURCE_RELEASE_STATE,
        help=(
            "Explicit snapshot release state recorded on Source nodes and in "
            "the manifest (default: unreviewed_local_snapshot)."
        ),
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help=(
            "Write the bundle without the immediate audit; intended only "
            "when validate_bundle.py will audit paired regenerations next."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        manifest = export_bundle(
            args.input,
            args.rawis,
            args.output,
            args.source_release_state,
            curation_manifest_path=args.curation_manifest,
            coverage_scope=args.coverage_scope,
            validate=not args.no_validate,
        )
    except (OSError, ValueError, csv.Error, sqlite3.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "output": str(args.output),
                "content_sha256": manifest["content_sha256"],
                "nodes": manifest["totals"]["nodes"],
                "relationships": manifest["totals"]["relationships"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
