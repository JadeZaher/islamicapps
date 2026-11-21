"""Validate a deterministic Neo4j bulk-import graph bundle."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterator, Sequence

try:
    from .contract import (
        BUNDLE_SCHEMA_VERSION,
        CANDIDATE_PATH_MARKERS,
        CANONICAL_TRADITIONS,
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
        UNIFIED_COLUMNS,
        deterministic_json_bytes,
        graph_content_hash,
        sha256_file,
        sha256_text,
    )
except ImportError:  # pragma: no cover - direct script execution
    from contract import (  # type: ignore
        BUNDLE_SCHEMA_VERSION,
        CANDIDATE_PATH_MARKERS,
        CANONICAL_TRADITIONS,
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
        UNIFIED_COLUMNS,
        deterministic_json_bytes,
        graph_content_hash,
        sha256_file,
        sha256_text,
    )

_csv_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit(_csv_limit)
        break
    except OverflowError:
        _csv_limit //= 10

EXPORT_DIR = Path(__file__).resolve().parent
HADITH_DATA_DIR = EXPORT_DIR.parent
PROJECT_ROOT = HADITH_DATA_DIR.parent.parent

MAX_REPORTED_ERRORS = 200
PUBLISHABLE_REVIEW_STATES = {"human_verified", "source_verified"}
PUBLISHABLE_RELEASE_STATES = {"canonical_release", "publication_ready"}
MODEL_PROVENANCE_RE = re.compile(
    r"ai|automated|generated|gpt|llm|machine|model|openai|anthropic|claude|gemma|pipeline",
    re.IGNORECASE,
)

EXPECTED_ID_PREFIXES = {
    "Hadith-ID": "hadith:",
    "Narrator-ID": "narrator:rawi:",
    "Source-ID": "source:",
    "Collection-ID": "collection:",
    "Book-ID": "book:",
    "Chapter-ID": "chapter:",
    "Tradition-ID": "tradition:",
    "Chain-ID": "chain:",
    "NameMention-ID": "mention:",
    "Translation-ID": "translation:",
    "Alias-ID": "alias:",
    "Evidence-ID": "evidence:",
    "Citation-ID": "citation:",
    "Biography-ID": "biography:",
    "Place-ID": "place:",
    "Event-ID": "event:",
}

REQUIRED_LABELS = {
    "Hadith": {"Hadith", "Report"},
    "Narrator": {"Narrator", "Person"},
    "Source": {"Source"},
    "Collection": {"Collection"},
    "Book": {"Book"},
    "Chapter": {"Chapter"},
    "Tradition": {"Tradition", "ReligiousTradition"},
    "Chain": {"Chain"},
    "NameMention": {"NameMention"},
    "Translation": {"Translation"},
    "Alias": {"Alias"},
    "Evidence": {"Evidence"},
    "Citation": {"Citation"},
    "Biography": {"Biography", "Profile", "SourceProfile"},
    "Place": {"Place", "Location"},
    "Event": {"Event", "HistoricalEvent"},
}


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path.name}")
    return value


def _iter_dict_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def _open_csv(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("rt", encoding="utf-8-sig", newline="")


def _rawi_profile_hash(row: dict[str, str]) -> str:
    payload = json.dumps(
        [str(row.get(column) or "") for column in RAWI_PROFILE_COLUMNS],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256_text(payload)


def _indexed_narrators(value: str) -> tuple[set[int], int, int]:
    text = str(value or "").strip()
    if not text or text == "NA":
        return set(), 0, 0
    values: set[int] = set()
    tokens = text.split(",")
    for token in tokens:
        normalized = token.strip()
        if not normalized.isdigit() or int(normalized) <= 0:
            raise ValueError(f"invalid indexed narrator token: {normalized!r}")
        values.add(int(normalized))
    return values, len(tokens), len(tokens) - len(values)


def _dict_row_shape_errors(
    row: dict[str | None, str | list[str] | None],
    fieldnames: Sequence[str],
) -> tuple[list[str] | None, list[str]]:
    extra = row.get(None)
    missing = [column for column in fieldnames if row.get(column) is None]
    return extra if isinstance(extra, list) else None, missing


def _csv_metadata(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        count = sum(1 for _ in reader)
    return header, count


def _as_int(value: str, label: str, add_error) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        add_error(f"{label} is not an integer: {value!r}")
        return None


def _as_bool(value: str, label: str, add_error) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    add_error(f"{label} is not canonical boolean text: {value!r}")
    return None


def _labels(value: str) -> set[str]:
    return {label for label in value.split(";") if label}


def _relationship_id_columns(spec: dict) -> tuple[str, str]:
    return spec["header"][0], spec["header"][1]


def _validate_compare_bundle(
    manifest: dict, compare_bundle: Path, add_error
) -> dict:
    other_path = compare_bundle / "manifest.json"
    if not other_path.is_file():
        add_error("compare bundle has no manifest.json")
        return {"requested": True, "equal": False}
    try:
        other = _load_json(other_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        add_error(f"compare bundle manifest is invalid: {error}")
        return {"requested": True, "equal": False}
    other_report = validate_bundle(
        compare_bundle, compare_bundle=None, write_report=False
    )
    if not other_report["import_ready"]:
        add_error("compare bundle failed independent integrity validation")
    keys = (
        "bundle_schema_version",
        "bundle_version",
        "content_sha256",
        "files",
        "support_files",
        "inputs",
        "curation_snapshot",
        "coverage",
        "generation",
    )
    equal = other_report["import_ready"] and all(
        manifest.get(key) == other.get(key) for key in keys
    )
    if not equal:
        add_error("compare bundle is not deterministically identical")
    return {
        "requested": True,
        "equal": equal,
        "content_sha256": other.get("content_sha256", ""),
    }


def validate_bundle(
    bundle_dir: Path | str,
    compare_bundle: Path | str | None = None,
    *,
    write_report: bool = True,
) -> dict:
    """Validate bundle integrity and separately report publication readiness."""
    bundle_dir = Path(bundle_dir)
    errors: list[str] = []
    warnings: list[str] = []
    publication_blockers: list[str] = []
    total_error_count = 0

    def add_error(message: str) -> None:
        nonlocal total_error_count
        total_error_count += 1
        if len(errors) < MAX_REPORTED_ERRORS:
            errors.append(message)

    manifest_path = bundle_dir / "manifest.json"
    try:
        manifest = _load_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        report = {
            "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
            "import_ready": False,
            "publication_ready": False,
            "errors": [f"manifest.json is invalid: {error}"],
            "error_count": 1,
            "warnings": [],
            "publication_blockers": ["bundle integrity failed"],
            "gates": {"manifest_integrity": {"passed": False}},
        }
        if write_report and bundle_dir.is_dir():
            (bundle_dir / "validation_report.json").write_bytes(
                deterministic_json_bytes(report)
            )
        return report

    if manifest.get("bundle_schema_version") != BUNDLE_SCHEMA_VERSION:
        add_error("unsupported bundle_schema_version")
    if manifest.get("input_schema_version") != 2:
        add_error("input_schema_version must be 2")
    if not str(manifest.get("source_release_state") or "").strip():
        add_error("source_release_state is blank")
    coverage = manifest.get("coverage")
    coverage_scope = (
        str(coverage.get("scope") or "")
        if isinstance(coverage, dict)
        else ""
    )
    if coverage_scope not in {"complete", "fixture_partial"}:
        add_error("coverage.scope must be complete or fixture_partial")

    manifest_file_items = [
        item for item in manifest.get("files", []) if isinstance(item, dict)
    ]
    manifest_files = {
        item.get("path"): item
        for item in manifest_file_items
    }
    expected_paths = set(NODE_FILES) | set(RELATIONSHIP_FILES)
    if len(manifest_file_items) != len(manifest_files):
        add_error("manifest graph file paths must be listed exactly once")
    if set(manifest_files) != expected_paths:
        missing = sorted(expected_paths - set(manifest_files))
        extra = sorted(set(manifest_files) - expected_paths)
        add_error(f"manifest graph file set mismatch; missing={missing}, extra={extra}")

    actual_graph_metadata: list[dict] = []
    file_headers_valid: dict[str, bool] = {}
    actual_node_rows = 0
    actual_relationship_rows = 0
    for relative_path, spec in sorted({**NODE_FILES, **RELATIONSHIP_FILES}.items()):
        path = bundle_dir / relative_path
        item = manifest_files.get(relative_path, {})
        if not path.is_file():
            add_error(f"missing graph file: {relative_path}")
            file_headers_valid[relative_path] = False
            continue
        try:
            header, row_count = _csv_metadata(path)
        except (OSError, UnicodeError, csv.Error) as error:
            add_error(f"cannot parse {relative_path}: {error}")
            file_headers_valid[relative_path] = False
            continue
        header_valid = header == spec["header"]
        file_headers_valid[relative_path] = header_valid
        if not header_valid:
            add_error(f"header mismatch: {relative_path}")
        actual = {
            "path": relative_path,
            "header": header,
            "row_count": row_count,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "kind": "node" if relative_path in NODE_FILES else "relationship",
        }
        if relative_path in NODE_FILES:
            actual["entity"] = spec["entity"]
            actual["namespace"] = spec["namespace"]
            actual_node_rows += row_count
        else:
            actual["type"] = spec["type"]
            actual["start_namespace"] = spec["start_namespace"]
            actual["end_namespace"] = spec["end_namespace"]
            actual_relationship_rows += row_count
        actual_graph_metadata.append(actual)
        for key in ("header", "row_count", "bytes", "sha256"):
            if item.get(key) != actual[key]:
                add_error(f"manifest {key} mismatch: {relative_path}")
        metadata_keys = (
            ("kind", "entity", "namespace")
            if relative_path in NODE_FILES
            else (
                "kind",
                "type",
                "start_namespace",
                "end_namespace",
            )
        )
        for key in metadata_keys:
            if item.get(key) != actual[key]:
                add_error(f"manifest {key} mismatch: {relative_path}")

    manifest_support_items = [
        item
        for item in manifest.get("support_files", [])
        if isinstance(item, dict)
    ]
    manifest_support = {
        item.get("path"): item
        for item in manifest_support_items
    }
    expected_support_paths = {
        "source_work_registry.json",
        "neo4j-admin-import.ps1",
        "post_import_schema.cypher",
    }
    if len(manifest_support_items) != len(manifest_support):
        add_error("manifest support file paths must be listed exactly once")
    if set(manifest_support) != expected_support_paths:
        add_error("manifest support file set mismatch")
    allowed_bundle_paths = (
        expected_paths
        | expected_support_paths
        | {"manifest.json", "validation_report.json"}
    )
    actual_bundle_paths = {
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if path.is_file()
    }
    unlisted_paths = sorted(actual_bundle_paths - allowed_bundle_paths)
    if unlisted_paths:
        add_error(f"unlisted bundle files: {unlisted_paths}")
    actual_support_metadata: list[dict] = []
    for relative_path in sorted(expected_support_paths):
        path = bundle_dir / relative_path
        item = manifest_support.get(relative_path, {})
        if not path.is_file():
            add_error(f"missing support file: {relative_path}")
            continue
        actual = {
            "path": relative_path,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "kind": "support",
        }
        actual_support_metadata.append(actual)
        for key in ("bytes", "sha256"):
            if item.get(key) != actual[key]:
                add_error(f"manifest {key} mismatch: {relative_path}")
    try:
        loader_text = (bundle_dir / "neo4j-admin-import.ps1").read_text(
            encoding="utf-8"
        )
        for relative_path in sorted(expected_paths):
            windows_relative = relative_path.replace("/", "\\")
            argument_kind = (
                "--nodes=" if relative_path in NODE_FILES else "--relationships="
            )
            expected_argument = (
                f'"{argument_kind}$bundleDir\\{windows_relative}"'
            )
            if loader_text.count(expected_argument) != 1:
                add_error(
                    "loader must reference graph file exactly once as an "
                    f"import argument: {relative_path}"
                )
        for required_loader_token in (
            "--id-type=string",
            "--input-encoding=UTF-8",
            "--bad-tolerance=0",
            "--skip-duplicate-nodes=false",
            "--skip-bad-relationships=false",
            "--overwrite-destination=false",
            "--multiline-fields-format=v2",
            "--dry-run=true",
            "Neo4j 2026.02 or newer is required",
        ):
            if required_loader_token not in loader_text:
                add_error(
                    f"loader missing strict token: {required_loader_token}"
                )
        if "--overwrite-destination=true" in loader_text:
            add_error("loader must not overwrite an existing database")
        schema_text = (
            bundle_dir / "post_import_schema.cypher"
        ).read_text(encoding="utf-8")
        for spec in NODE_FILES.values():
            label = spec["entity"]
            expected_constraint = (
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
            )
            if schema_text.count(expected_constraint) != 1:
                add_error(
                    f"post-import schema lacks one id constraint for {label}"
                )
    except (OSError, UnicodeError) as error:
        add_error(f"cannot validate import support files: {error}")
    actual_content_hash = graph_content_hash(
        actual_graph_metadata, actual_support_metadata
    )
    if manifest.get("content_sha256") != actual_content_hash:
        add_error("manifest content_sha256 mismatch")

    registry: dict = {}
    source_by_slug: dict[str, dict] = {}
    work_by_id: dict[str, dict] = {}
    work_by_pair: dict[tuple[str, str], dict] = {}
    try:
        registry = _load_json(bundle_dir / "source_work_registry.json")
        works = registry.get("source_works", [])
        sources = registry.get("sources", [])
        if len(works) != 34:
            add_error("bundle source-work registry must contain 34 works")
        for work in works:
            work_id = work["source_work_id"]
            pair = (work["tradition"], work["canonical_source"])
            if work_id in work_by_id or pair in work_by_pair:
                add_error(f"duplicate source-work registry entry: {work_id}")
            work_by_id[work_id] = work
            work_by_pair[pair] = work
        for source in sources:
            slug = source["slug"]
            if slug in source_by_slug:
                add_error(f"duplicate source registry slug: {slug}")
            source_by_slug[slug] = source
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        add_error(f"source-work registry is invalid: {error}")

    generation = manifest.get("generation")
    if not isinstance(generation, dict) or not str(
        generation.get("command") or ""
    ).startswith(
        "python datasets/hadith-data/neo4j_export/export_bundle.py "
    ):
        add_error("manifest deterministic generation command is missing")

    candidate_input_error_count = 0
    input_roles: Counter[str] = Counter()
    bound_dataset_path: Path | None = None
    bound_rawis_path: Path | None = None
    rawi_input_hash_valid = False
    bound_curation_manifest: dict | None = None
    curation_input_item: dict | None = None
    for item in manifest.get("inputs", []):
        normalized = str(item.get("path") or "").lower()
        for marker in CANDIDATE_PATH_MARKERS:
            if marker in normalized:
                candidate_input_error_count += 1
                add_error(f"candidate input leaked into manifest: {marker}")
        role = item.get("role")
        input_roles[str(role)] += 1
        if role == "curation_manifest":
            curation_input_item = item
        if role in {
            "schema_v2_dataset",
            "rawi_registry",
            "curation_manifest",
            "source_work_registry",
            "isnad_extractor",
            "graph_exporter",
            "graph_contract",
            "graph_validator",
        }:
            declared_path = Path(str(item.get("path") or ""))
            input_path = (
                declared_path
                if declared_path.is_absolute()
                else PROJECT_ROOT / declared_path
            )
            if input_path.is_file():
                input_hash_valid = not (
                    input_path.stat().st_size != item.get("bytes")
                    or sha256_file(input_path) != item.get("sha256")
                )
                if not input_hash_valid:
                    add_error(f"manifest input hash mismatch: {role}")
                if role == "schema_v2_dataset":
                    bound_dataset_path = input_path
                elif role == "rawi_registry":
                    bound_rawis_path = input_path
                    rawi_input_hash_valid = input_hash_valid
                elif role == "curation_manifest":
                    try:
                        bound_curation_manifest = _load_json(input_path)
                    except (OSError, ValueError, json.JSONDecodeError) as error:
                        add_error(f"bound curation manifest is invalid: {error}")
            else:
                warnings.append(f"input_binding_unavailable={role}")
    for required_role in (
        "schema_v2_dataset",
        "rawi_registry",
        "source_work_registry",
        "isnad_extractor",
        "graph_exporter",
        "graph_contract",
        "graph_validator",
    ):
        if input_roles[required_role] != 1:
            add_error(f"manifest input role must occur once: {required_role}")
    curation_snapshot = manifest.get("curation_snapshot")
    if curation_snapshot is not None and input_roles["curation_manifest"] != 1:
        add_error("curation_snapshot requires exactly one curation_manifest input")
    if (
        manifest.get("source_release_state") == "development_nonrelease"
        and curation_snapshot is None
    ):
        add_error("development_nonrelease bundle lacks curation_snapshot")
    declared_candidate_exclusions = manifest.get("candidate_inputs_excluded")
    if declared_candidate_exclusions != list(CANDIDATE_PATH_MARKERS):
        candidate_input_error_count += 1
        add_error("candidate_inputs_excluded contract mismatch")

    with tempfile.TemporaryDirectory(prefix="hadith-graph-validation-") as temp:
        database_path = Path(temp) / "validation.sqlite3"
        connection = sqlite3.connect(database_path)
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE node_ids (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                file_path TEXT NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE hadiths (
                id TEXT PRIMARY KEY,
                record_id TEXT UNIQUE,
                source_record_id TEXT,
                tradition TEXT,
                source TEXT,
                source_id TEXT,
                source_work_id TEXT,
                status TEXT,
                translation_disposition TEXT,
                provenance TEXT,
                excluded INTEGER,
                arabic_hash TEXT
            ) WITHOUT ROWID;
            CREATE TABLE narrators (
                id TEXT PRIMARY KEY,
                scholar_indx INTEGER UNIQUE,
                name TEXT
            ) WITHOUT ROWID;
            CREATE TABLE biographies (
                id TEXT PRIMARY KEY,
                subject_id TEXT UNIQUE,
                scholar_indx INTEGER UNIQUE,
                profile_kind TEXT,
                source_id TEXT,
                source_locator TEXT,
                citation_id TEXT,
                review_state TEXT,
                provenance TEXT,
                profile_hash TEXT,
                profile_payload TEXT
            ) WITHOUT ROWID;
            CREATE TABLE sources (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE,
                release_state TEXT
            ) WITHOUT ROWID;
            CREATE TABLE collections (
                id TEXT PRIMARY KEY,
                source_work_id TEXT UNIQUE,
                name TEXT,
                tradition TEXT,
                source_id TEXT
            ) WITHOUT ROWID;
            CREATE TABLE books (
                id TEXT PRIMARY KEY,
                collection_id TEXT
            ) WITHOUT ROWID;
            CREATE TABLE chapters (
                id TEXT PRIMARY KEY,
                collection_id TEXT,
                book_id TEXT
            ) WITHOUT ROWID;
            CREATE TABLE traditions (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE
            ) WITHOUT ROWID;
            CREATE TABLE chains (
                id TEXT PRIMARY KEY,
                hadith_id TEXT,
                source_record_id TEXT,
                branch INTEGER,
                length INTEGER,
                resolved INTEGER,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            ) WITHOUT ROWID;
            CREATE TABLE mentions (
                id TEXT PRIMARY KEY,
                hadith_id TEXT,
                source_record_id TEXT,
                chain_id TEXT,
                branch INTEGER,
                position INTEGER,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            ) WITHOUT ROWID;
            CREATE TABLE translations (
                id TEXT PRIMARY KEY,
                text_value TEXT,
                text_hash TEXT,
                status TEXT,
                source TEXT,
                model TEXT,
                review_state TEXT,
                source_record_id TEXT,
                arabic_hash TEXT,
                provenance TEXT,
                candidate_only INTEGER
            ) WITHOUT ROWID;
            CREATE TABLE evidence (
                id TEXT PRIMARY KEY,
                evidence_kind TEXT,
                provenance TEXT,
                expected_source_id TEXT,
                quality_excluded INTEGER
            ) WITHOUT ROWID;
            CREATE TABLE aliases (
                id TEXT PRIMARY KEY,
                alias_kind TEXT,
                provenance TEXT
            ) WITHOUT ROWID;
            CREATE TABLE has_chain (
                hadith_id TEXT,
                chain_id TEXT,
                branch INTEGER,
                source_record_id TEXT,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            );
            CREATE TABLE includes_mention (
                chain_id TEXT,
                mention_id TEXT,
                position INTEGER,
                branch INTEGER,
                source_record_id TEXT,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            );
            CREATE TABLE next_edges (
                start_id TEXT,
                end_id TEXT,
                chain_id TEXT,
                hadith_id TEXT,
                from_position INTEGER,
                to_position INTEGER,
                source_record_id TEXT,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            );
            CREATE TABLE resolutions (
                mention_id TEXT,
                narrator_id TEXT,
                chain_id TEXT,
                hadith_id TEXT,
                position INTEGER,
                source_record_id TEXT,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            );
            CREATE TABLE includes_narrator (
                chain_id TEXT,
                narrator_id TEXT,
                position INTEGER,
                branch INTEGER,
                source_record_id TEXT,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            );
            CREATE TABLE narrated_edges (
                start_id TEXT,
                end_id TEXT,
                chain_id TEXT,
                hadith_id TEXT,
                from_position INTEGER,
                to_position INTEGER,
                source_record_id TEXT,
                extraction_method TEXT,
                sanad_confidence TEXT,
                provenance TEXT
            );
            CREATE TABLE translation_of (
                translation_id TEXT,
                hadith_id TEXT
            );
            CREATE TABLE translation_supported_by (
                translation_id TEXT,
                evidence_id TEXT
            );
            CREATE TABLE biography_of (
                biography_id TEXT,
                narrator_id TEXT,
                review_state TEXT,
                provenance TEXT
            );
            CREATE TABLE biography_from_source (
                biography_id TEXT,
                source_id TEXT,
                review_state TEXT,
                provenance TEXT
            );
            CREATE TABLE student_of (
                student_id TEXT,
                teacher_id TEXT,
                evidence_fields TEXT,
                evidence_count INTEGER,
                reciprocal INTEGER,
                review_state TEXT,
                provenance TEXT,
                UNIQUE(student_id, teacher_id)
            );
            CREATE TABLE relationship_rows (
                file_path TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (file_path, payload)
            ) WITHOUT ROWID;
            CREATE TABLE memberships (
                edge_type TEXT NOT NULL,
                start_id TEXT NOT NULL,
                end_id TEXT NOT NULL,
                provenance TEXT
            );
            CREATE TABLE source_arabic (
                record_id TEXT PRIMARY KEY,
                source_record_id TEXT NOT NULL,
                arabic_hash TEXT NOT NULL,
                translation_text_hash TEXT NOT NULL,
                translation_status TEXT NOT NULL,
                translation_source TEXT NOT NULL,
                translation_model TEXT NOT NULL,
                translation_review_state TEXT NOT NULL,
                provenance TEXT NOT NULL,
                translation_disposition TEXT NOT NULL
            ) WITHOUT ROWID;
            """
        )

        by_tradition: Counter[str] = Counter()
        by_collection: Counter[str] = Counter()
        by_provenance_source: Counter[str] = Counter()
        input_translation_status: Counter[str] = Counter()
        exported_translation_status: Counter[str] = Counter()
        translation_dispositions: Counter[str] = Counter()
        blank_translation_text = 0
        blank_translation_source = 0
        blank_translation_review = 0
        missing_required_model = 0
        non_publishable_review = 0
        arabic_hash_errors = 0

        for relative_path, spec in sorted(NODE_FILES.items()):
            if not file_headers_valid.get(relative_path):
                continue
            path = bundle_dir / relative_path
            namespace = spec["namespace"]
            id_header = spec["header"][0]
            label_header = spec["header"][-1]
            prefix = EXPECTED_ID_PREFIXES[namespace]
            for row_no, row in enumerate(_iter_dict_rows(path), start=2):
                node_id = row[id_header]
                if row.get("id:string") != node_id:
                    add_error(
                        f"{relative_path}:{row_no} persisted id does not match "
                        "the import ID"
                    )
                if not node_id.startswith(prefix):
                    add_error(
                        f"{relative_path}:{row_no} ID lacks {prefix!r} prefix"
                    )
                try:
                    connection.execute(
                        "INSERT INTO node_ids(id, namespace, file_path) "
                        "VALUES (?, ?, ?)",
                        (node_id, namespace, relative_path),
                    )
                except sqlite3.IntegrityError:
                    add_error(f"duplicate/colliding node ID: {node_id}")
                required_labels = REQUIRED_LABELS[spec["entity"]]
                if not required_labels.issubset(_labels(row[label_header])):
                    add_error(
                        f"{relative_path}:{row_no} missing labels "
                        f"{sorted(required_labels)}"
                    )

                try:
                    if spec["entity"] == "Hadith":
                        expected_hash = sha256_text(row["text_ar:string"])
                        if row["arabic_sha256:string"] != expected_hash:
                            arabic_hash_errors += 1
                            add_error(
                                f"{relative_path}:{row_no} Arabic SHA-256 mismatch"
                            )
                        excluded = _as_bool(
                            row["quality_excluded:boolean"],
                            f"{relative_path}:{row_no} quality_excluded",
                            add_error,
                        )
                        record_id = row["record_id:string"]
                        expected_reason = SOURCE_QUALITY_EXCLUSIONS.get(record_id)
                        if expected_reason:
                            if not excluded or (
                                row["quality_exclusion_reason:string"]
                                != expected_reason
                            ):
                                add_error(
                                    f"{record_id} source-quality exclusion is "
                                    "not exactly flagged"
                                )
                        elif excluded:
                            add_error(
                                f"unsupported source-quality exclusion: {record_id}"
                            )
                        connection.execute(
                            "INSERT INTO hadiths VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                node_id,
                                record_id,
                                row["source_record_id:string"],
                                row["tradition:string"],
                                row["source:string"],
                                row["source_id:string"],
                                row["source_work_id:string"],
                                row["translation_status:string"],
                                row["translation_disposition:string"],
                                row["provenance:string"],
                                int(bool(excluded)),
                                row["arabic_sha256:string"],
                            ),
                        )
                        by_tradition[row["tradition:string"]] += 1
                        by_collection[row["source:string"]] += 1
                        source_slug = row["source_id:string"].removeprefix("source:")
                        by_provenance_source[source_slug] += 1
                        status = row["translation_status:string"] or "<blank>"
                        input_translation_status[status] += 1
                        disposition = row["translation_disposition:string"]
                        if disposition not in {
                            "exported_source_surface",
                            "omitted_machine_candidate",
                            "omitted_missing_provenance",
                            "omitted_missing_text",
                            "omitted_source_quality_exclusion",
                        }:
                            add_error(
                                f"{relative_path}:{row_no} invalid translation "
                                f"disposition: {disposition!r}"
                            )
                        if bool(excluded) != (
                            disposition == "omitted_source_quality_exclusion"
                        ):
                            add_error(
                                f"{relative_path}:{row_no} translation "
                                "disposition/exclusion mismatch"
                            )
                        translation_dispositions[disposition] += 1
                    elif spec["entity"] == "Narrator":
                        scholar = _as_int(
                            row["scholar_indx:int"],
                            f"{relative_path}:{row_no} scholar_indx",
                            add_error,
                        )
                        if scholar is not None:
                            connection.execute(
                                "INSERT INTO narrators VALUES (?, ?, ?)",
                                (node_id, scholar, row["name:string"]),
                            )
                    elif spec["entity"] == "Source":
                        connection.execute(
                            "INSERT INTO sources VALUES (?, ?, ?)",
                            (
                                node_id,
                                row["slug:string"],
                                row["release_state:string"],
                            ),
                        )
                    elif spec["entity"] == "Collection":
                        connection.execute(
                            "INSERT INTO collections VALUES (?, ?, ?, ?, ?)",
                            (
                                node_id,
                                row["source_work_id:string"],
                                row["name:string"],
                                row["tradition:string"],
                                row["source_id:string"],
                            ),
                        )
                    elif spec["entity"] == "Book":
                        connection.execute(
                            "INSERT INTO books VALUES (?, ?)",
                            (node_id, row["collection_id:string"]),
                        )
                    elif spec["entity"] == "Chapter":
                        connection.execute(
                            "INSERT INTO chapters VALUES (?, ?, ?)",
                            (
                                node_id,
                                row["collection_id:string"],
                                row["book_id:string"],
                            ),
                        )
                    elif spec["entity"] == "Tradition":
                        connection.execute(
                            "INSERT INTO traditions VALUES (?, ?)",
                            (node_id, row["name:string"]),
                        )
                    elif spec["entity"] == "Chain":
                        values = [
                            _as_int(
                                row["branch:int"],
                                f"{relative_path}:{row_no} branch",
                                add_error,
                            ),
                            _as_int(
                                row["length:int"],
                                f"{relative_path}:{row_no} length",
                                add_error,
                            ),
                        ]
                        resolved = _as_bool(
                            row["resolved:boolean"],
                            f"{relative_path}:{row_no} resolved",
                            add_error,
                        )
                        if None not in values and resolved is not None:
                            connection.execute(
                                "INSERT INTO chains VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    node_id,
                                    row["hadith_id:string"],
                                    row["source_record_id:string"],
                                    values[0],
                                    values[1],
                                    int(resolved),
                                    row["extraction_method:string"],
                                    row["sanad_confidence:string"],
                                    row["provenance:string"],
                                ),
                            )
                    elif spec["entity"] == "NameMention":
                        branch = _as_int(
                            row["branch:int"],
                            f"{relative_path}:{row_no} branch",
                            add_error,
                        )
                        position = _as_int(
                            row["position:int"],
                            f"{relative_path}:{row_no} position",
                            add_error,
                        )
                        if branch is not None and position is not None:
                            connection.execute(
                                "INSERT INTO mentions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    node_id,
                                    row["hadith_id:string"],
                                    row["source_record_id:string"],
                                    row["chain_id:string"],
                                    branch,
                                    position,
                                    row["extraction_method:string"],
                                    row["sanad_confidence:string"],
                                    row["provenance:string"],
                                ),
                            )
                    elif spec["entity"] == "Translation":
                        candidate = _as_bool(
                            row["candidate_only:boolean"],
                            f"{relative_path}:{row_no} candidate_only",
                            add_error,
                        )
                        if candidate:
                            candidate_input_error_count += 1
                            add_error(
                                f"{relative_path}:{row_no} candidate translation "
                                "was promoted"
                            )
                        connection.execute(
                            "INSERT INTO translations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                node_id,
                                row["text:string"],
                                sha256_text(row["text:string"]),
                                row["status:string"],
                                row["source:string"],
                                row["model:string"],
                                row["review_state:string"],
                                row["source_record_id:string"],
                                row["arabic_sha256:string"],
                                row["provenance_source:string"],
                                int(bool(candidate)),
                            ),
                        )
                        status = row["status:string"] or "<blank>"
                        exported_translation_status[status] += 1
                        blank_translation_text += int(not row["text:string"].strip())
                        blank_translation_source += int(
                            not row["source:string"].strip()
                        )
                        blank_translation_review += int(
                            not row["review_state:string"].strip()
                        )
                        non_publishable_review += int(
                            row["review_state:string"]
                            not in PUBLISHABLE_REVIEW_STATES
                        )
                        if (
                            MODEL_PROVENANCE_RE.search(
                                row["source:string"]
                                + " "
                                + row["review_state:string"]
                            )
                            and not row["model:string"].strip()
                        ):
                            missing_required_model += 1
                    elif spec["entity"] == "Evidence":
                        excluded = _as_bool(
                            row["quality_excluded:boolean"],
                            f"{relative_path}:{row_no} quality_excluded",
                            add_error,
                        )
                        evidence_provenance = row["provenance_source:string"]
                        evidence_source_matches = [
                            source["slug"]
                            for source in registry.get("sources", [])
                            if any(
                                evidence_provenance == prefix
                                or evidence_provenance.startswith(prefix + ":")
                                or evidence_provenance.startswith(prefix + "/")
                                for prefix in source.get(
                                    "provenance_prefixes", []
                                )
                            )
                        ]
                        if len(evidence_source_matches) != 1:
                            add_error(
                                f"{relative_path}:{row_no} evidence provenance "
                                "does not resolve exactly once"
                            )
                        expected_evidence_source = (
                            f"source:{evidence_source_matches[0]}"
                            if len(evidence_source_matches) == 1
                            else ""
                        )
                        connection.execute(
                            "INSERT INTO evidence VALUES (?, ?, ?, ?, ?)",
                            (
                                node_id,
                                row["evidence_kind:string"],
                                evidence_provenance,
                                expected_evidence_source,
                                int(bool(excluded)),
                            ),
                        )
                    elif spec["entity"] == "Alias":
                        connection.execute(
                            "INSERT INTO aliases VALUES (?, ?, ?)",
                            (
                                node_id,
                                row["alias_kind:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["entity"] == "Biography":
                        scholar = _as_int(
                            row["scholar_indx:int"],
                            f"{relative_path}:{row_no} scholar_indx",
                            add_error,
                        )
                        profile_payload = json.dumps(
                            [
                                row[f"{column}:string"]
                                for column in RAWI_PROFILE_COLUMNS
                            ],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        expected_profile_hash = sha256_text(profile_payload)
                        if row["raw_profile_sha256:string"] != expected_profile_hash:
                            add_error(
                                f"{relative_path}:{row_no} raw profile SHA-256 "
                                "mismatch"
                            )
                        if scholar is not None:
                            expected_subject = f"narrator:rawi:{scholar}"
                            expected_id = (
                                f"biography:narrator-lexicon:{scholar}"
                            )
                            if (
                                node_id != expected_id
                                or row["subject_id:string"] != expected_subject
                                or row["profile_kind:string"]
                                != "rawi_lexicon_profile"
                                or row["source_id:string"]
                                != "source:narrator-lexicon"
                                or row["source_locator:string"]
                                != f"all_rawis.csv#scholar_indx={scholar}"
                                or row["citation_id:string"]
                                or row["review_state:string"]
                                != RAWI_PROFILE_REVIEW_STATE
                                or row["provenance:string"]
                                != RAWI_PROFILE_PROVENANCE
                            ):
                                add_error(
                                    f"{relative_path}:{row_no} narrator profile "
                                    "contract mismatch"
                                )
                            connection.execute(
                                "INSERT INTO biographies VALUES "
                                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    node_id,
                                    row["subject_id:string"],
                                    scholar,
                                    row["profile_kind:string"],
                                    row["source_id:string"],
                                    row["source_locator:string"],
                                    row["citation_id:string"],
                                    row["review_state:string"],
                                    row["provenance:string"],
                                    row["raw_profile_sha256:string"],
                                    profile_payload,
                                ),
                            )
                except sqlite3.IntegrityError:
                    add_error(
                        f"duplicate {spec['entity']} identity/property at "
                        f"{relative_path}:{row_no}"
                    )
                except KeyError as error:
                    add_error(f"{relative_path}:{row_no} missing field {error}")
        connection.commit()

        arabic_source_binding_errors = 0
        if bound_dataset_path is not None:
            try:
                with _open_csv(bound_dataset_path) as handle:
                    reader = csv.DictReader(handle)
                    if reader.fieldnames != UNIFIED_COLUMNS:
                        add_error("bound dataset schema does not match schema-v2")
                    else:
                        for source_row_no, source_row in enumerate(
                            reader, start=2
                        ):
                            source_record_id = source_row[
                                "source_record_id"
                            ].strip()
                            review_state = source_row[
                                "translation_review_status"
                            ].strip()
                            translation_source = source_row[
                                "translation_source"
                            ].strip()
                            record_id = source_row["record_id"].strip()
                            if record_id in SOURCE_QUALITY_EXCLUSIONS:
                                expected_disposition = (
                                    "omitted_source_quality_exclusion"
                                )
                            elif not source_row["text_en"].strip():
                                expected_disposition = "omitted_missing_text"
                            elif not translation_source or not review_state:
                                expected_disposition = (
                                    "omitted_missing_provenance"
                                )
                            elif review_state == "machine_unreviewed":
                                expected_disposition = (
                                    "omitted_machine_candidate"
                                )
                            else:
                                expected_disposition = (
                                    "exported_source_surface"
                                )
                            try:
                                connection.execute(
                                    "INSERT INTO source_arabic VALUES "
                                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (
                                        record_id,
                                        source_record_id,
                                        sha256_text(source_row["text_ar"]),
                                        sha256_text(source_row["text_en"]),
                                        source_row["translation_status"].strip(),
                                        translation_source,
                                        source_row["translation_model"].strip(),
                                        review_state,
                                        source_row["provenance_source"].strip(),
                                        expected_disposition,
                                    ),
                                )
                            except sqlite3.IntegrityError:
                                arabic_source_binding_errors += 1
                                add_error(
                                    "bound dataset has duplicate record_id at "
                                    f"line {source_row_no}"
                                )
                connection.commit()
                source_binding_mismatches = connection.execute(
                    """
                    SELECT COUNT(*) FROM source_arabic s
                    LEFT JOIN hadiths h ON h.record_id = s.record_id
                    WHERE h.id IS NULL
                       OR h.source_record_id != s.source_record_id
                       OR h.arabic_hash != s.arabic_hash
                       OR h.status != s.translation_status
                       OR h.provenance != s.provenance
                       OR h.translation_disposition != s.translation_disposition
                    """
                ).fetchone()[0]
                exported_binding_mismatches = connection.execute(
                    """
                    SELECT COUNT(*) FROM hadiths h
                    LEFT JOIN source_arabic s ON s.record_id = h.record_id
                    WHERE s.record_id IS NULL
                       OR h.source_record_id != s.source_record_id
                       OR h.arabic_hash != s.arabic_hash
                       OR h.status != s.translation_status
                       OR h.provenance != s.provenance
                       OR h.translation_disposition != s.translation_disposition
                    """
                ).fetchone()[0]
                arabic_source_binding_errors += (
                    source_binding_mismatches + exported_binding_mismatches
                )
                if source_binding_mismatches or exported_binding_mismatches:
                    add_error(
                        "Arabic source binding mismatch: "
                        f"source={source_binding_mismatches}, "
                        f"export={exported_binding_mismatches}"
                    )
            except (OSError, UnicodeError, csv.Error) as error:
                arabic_source_binding_errors += 1
                add_error(f"cannot verify bound dataset Arabic: {error}")
        else:
            warnings.append("arabic_source_binding_unavailable")

        rawi_source_binding_errors = 0
        rawi_profile_binding_available = bound_rawis_path is not None
        rawi_profile_binding_performed = False
        if rawi_profile_binding_available and not rawi_input_hash_valid:
            rawi_source_binding_errors += 1
        expected_student_edges: dict[tuple[int, int], set[str]] = {}
        expected_profile_stats: dict[str, int] = {}
        if bound_rawis_path is not None:
            rawi_profile_binding_performed = True
            try:
                with _open_csv(bound_rawis_path) as handle:
                    reader = csv.DictReader(handle)
                    if tuple(reader.fieldnames or ()) != RAWI_COLUMNS:
                        rawi_source_binding_errors += 1
                        add_error(
                            "bound rawi registry schema does not match the "
                            "lossless profile contract"
                        )
                        rawi_rows: list[dict[str, str]] = []
                    else:
                        rawi_rows = []
                        for source_row_no, source_row in enumerate(
                            reader, start=2
                        ):
                            extra, missing = _dict_row_shape_errors(
                                source_row, RAWI_COLUMNS
                            )
                            if extra is not None or missing:
                                rawi_source_binding_errors += 1
                                add_error(
                                    "bound rawi registry has a non-exact row "
                                    f"shape at line {source_row_no}: "
                                    f"extra={extra!r}, missing={missing}"
                                )
                                continue
                            rawi_rows.append(source_row)
                source_scholars: set[int] = set()
                for source_row_no, source_row in enumerate(rawi_rows, start=2):
                    token = str(source_row["scholar_indx"] or "").strip()
                    if not token.isdigit() or int(token) <= 0:
                        rawi_source_binding_errors += 1
                        add_error(
                            "bound rawi registry has invalid scholar_indx at "
                            f"line {source_row_no}"
                        )
                        continue
                    scholar = int(token)
                    if scholar in source_scholars:
                        rawi_source_binding_errors += 1
                        add_error(
                            "bound rawi registry has duplicate scholar_indx at "
                            f"line {source_row_no}: {scholar}"
                        )
                        continue
                    source_scholars.add(scholar)
                    narrator = connection.execute(
                        "SELECT name FROM narrators WHERE scholar_indx = ?",
                        (scholar,),
                    ).fetchone()
                    profile = connection.execute(
                        "SELECT subject_id, profile_hash, profile_payload "
                        "FROM biographies WHERE scholar_indx = ?",
                        (scholar,),
                    ).fetchone()
                    expected_payload = json.dumps(
                        [
                            str(source_row.get(column) or "")
                            for column in RAWI_PROFILE_COLUMNS
                        ],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    expected_hash = sha256_text(expected_payload)
                    if (
                        narrator is None
                        or narrator[0] != str(source_row["name"] or "")
                        or profile is None
                        or profile[0] != f"narrator:rawi:{scholar}"
                        or profile[1] != expected_hash
                        or profile[2] != expected_payload
                    ):
                        rawi_source_binding_errors += 1
                        add_error(
                            "rawi profile source binding mismatch at "
                            f"scholar_indx={scholar}"
                        )

                indexed_assertion_tokens = 0
                indexed_duplicate_fields = 0
                indexed_duplicate_occurrences = 0
                all_indexed_pairs: dict[tuple[int, int], set[str]] = {}
                for source_row in rawi_rows:
                    scholar = int(source_row["scholar_indx"])
                    teachers, teacher_tokens, teacher_duplicates = (
                        _indexed_narrators(
                            source_row["teachers_inds"]
                        )
                    )
                    students, student_tokens, student_duplicates = (
                        _indexed_narrators(
                            source_row["students_inds"]
                        )
                    )
                    indexed_assertion_tokens += teacher_tokens + student_tokens
                    indexed_duplicate_fields += int(
                        teacher_duplicates > 0
                    ) + int(student_duplicates > 0)
                    indexed_duplicate_occurrences += (
                        teacher_duplicates + student_duplicates
                    )
                    for teacher in teachers:
                        all_indexed_pairs.setdefault(
                            (scholar, teacher), set()
                        ).add("teachers_inds")
                    for student in students:
                        all_indexed_pairs.setdefault(
                            (student, scholar), set()
                        ).add("students_inds")

                missing_pairs = 0
                self_pairs = 0
                for pair, fields in all_indexed_pairs.items():
                    student, teacher = pair
                    if (
                        student not in source_scholars
                        or teacher not in source_scholars
                    ):
                        missing_pairs += 1
                    elif student == teacher:
                        self_pairs += 1
                    else:
                        expected_student_edges[pair] = fields
                expected_profile_stats = {
                    "profile_nodes": len(source_scholars),
                    "indexed_learning_assertion_tokens": (
                        indexed_assertion_tokens
                    ),
                    "indexed_learning_duplicate_fields": (
                        indexed_duplicate_fields
                    ),
                    "indexed_learning_duplicate_occurrences": (
                        indexed_duplicate_occurrences
                    ),
                    "unique_indexed_pairs": len(all_indexed_pairs),
                    "exported_student_of_pairs": len(expected_student_edges),
                    "corroborated_pairs": sum(
                        len(fields) == 2
                        for fields in expected_student_edges.values()
                    ),
                    "omitted_missing_endpoint_pairs": missing_pairs,
                    "omitted_self_pairs": self_pairs,
                }
                narrator_count = connection.execute(
                    "SELECT COUNT(*) FROM narrators"
                ).fetchone()[0]
                biography_count = connection.execute(
                    "SELECT COUNT(*) FROM biographies"
                ).fetchone()[0]
                if (
                    narrator_count != len(source_scholars)
                    or biography_count != len(source_scholars)
                ):
                    rawi_source_binding_errors += 1
                    add_error(
                        "rawi narrator/profile cardinality does not match "
                        "the bound registry"
                    )
            except (
                OSError,
                UnicodeError,
                csv.Error,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                rawi_source_binding_errors += 1
                add_error(f"cannot verify bound rawi profiles: {error}")
        else:
            warnings.append("rawi_profile_source_binding_unavailable")
            if coverage_scope == "complete":
                rawi_source_binding_errors += 1
                add_error(
                    "complete bundle validation requires the bound rawi "
                    "profile source to be available"
                )

        source_release_state = str(manifest.get("source_release_state") or "")
        for source_id, slug, release_state in connection.execute(
            "SELECT id, slug, release_state FROM sources"
        ):
            if source_id != f"source:{slug}":
                add_error(f"source ID/slug mismatch: {source_id}")
            if slug not in source_by_slug:
                add_error(f"unregistered source slug: {slug}")
            if release_state != source_release_state:
                add_error(f"source release-state mismatch: {source_id}")
        for tradition_node_id, name in connection.execute(
            "SELECT id, name FROM traditions"
        ):
            if name not in CANONICAL_TRADITIONS:
                add_error(f"unsupported tradition node: {name}")
            if tradition_node_id != f"tradition:{name.lower()}":
                add_error(f"tradition ID/name mismatch: {tradition_node_id}")
        for collection_id, work_id, name, tradition, source_id in connection.execute(
            "SELECT id, source_work_id, name, tradition, source_id FROM collections"
        ):
            work = work_by_id.get(work_id)
            if not work:
                add_error(f"unregistered collection source_work_id: {work_id}")
                continue
            if collection_id != f"collection:{work_id}":
                add_error(f"collection ID/source_work_id mismatch: {collection_id}")
            if (
                name != work["canonical_source"]
                or tradition != work["tradition"]
                or source_id != f"source:{work['source_slug']}"
            ):
                add_error(f"collection registry mismatch: {collection_id}")
        for (
            hadith_id,
            record_id,
            _source_record_id,
            tradition,
            source_name,
            source_id,
            work_id,
            _status,
            _translation_disposition,
            _provenance,
            _excluded,
            _arabic_hash,
        ) in connection.execute("SELECT * FROM hadiths"):
            if hadith_id != f"hadith:{record_id}":
                add_error(f"Hadith ID/record_id mismatch: {hadith_id}")
            work = work_by_pair.get((tradition, source_name))
            if not work:
                add_error(
                    f"unregistered Hadith tradition/source: "
                    f"{tradition}/{source_name}"
                )
            elif (
                work_id != work["source_work_id"]
                or source_id != f"source:{work['source_slug']}"
            ):
                add_error(f"Hadith source normalization mismatch: {hadith_id}")
            provenance_matches = [
                source["slug"]
                for source in registry.get("sources", [])
                if any(
                    _provenance == prefix
                    or _provenance.startswith(prefix + ":")
                    or _provenance.startswith(prefix + "/")
                    for prefix in source.get("provenance_prefixes", [])
                )
            ]
            if provenance_matches != [source_id.removeprefix("source:")]:
                add_error(f"Hadith provenance/source mismatch: {hadith_id}")

        actual_traditions = set(by_tradition)
        actual_work_ids = {
            row[0]
            for row in connection.execute(
                "SELECT source_work_id FROM collections"
            )
        }
        if isinstance(coverage, dict):
            if coverage.get("traditions") != sorted(actual_traditions):
                add_error("coverage tradition set mismatch")
            if coverage.get("source_work_ids") != sorted(actual_work_ids):
                add_error("coverage source-work set mismatch")
        if coverage_scope == "complete":
            if actual_traditions != set(CANONICAL_TRADITIONS):
                add_error("complete bundle lacks one or more traditions")
            if actual_work_ids != set(work_by_id):
                add_error("complete bundle lacks one or more source works")

        relationship_type_errors = 0
        orphan_edges = 0
        duplicate_relationship_occurrences = 0
        for relative_path, spec in sorted(RELATIONSHIP_FILES.items()):
            if not file_headers_valid.get(relative_path):
                continue
            path = bundle_dir / relative_path
            start_header, end_header = _relationship_id_columns(spec)
            type_header = spec["header"][-1]
            for row_no, row in enumerate(_iter_dict_rows(path), start=2):
                start_id = row[start_header]
                end_id = row[end_header]
                payload = json.dumps(
                    [row[column] for column in spec["header"]],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                try:
                    connection.execute(
                        "INSERT INTO relationship_rows VALUES (?, ?)",
                        (relative_path, payload),
                    )
                except sqlite3.IntegrityError:
                    duplicate_relationship_occurrences += 1
                    add_error(
                        f"{relative_path}:{row_no} duplicate relationship occurrence"
                    )
                if row[type_header] != spec["type"]:
                    relationship_type_errors += 1
                    add_error(
                        f"{relative_path}:{row_no} relationship type mismatch"
                    )
                start_exists = connection.execute(
                    "SELECT 1 FROM node_ids WHERE id = ? AND namespace = ?",
                    (start_id, spec["start_namespace"]),
                ).fetchone()
                end_exists = connection.execute(
                    "SELECT 1 FROM node_ids WHERE id = ? AND namespace = ?",
                    (end_id, spec["end_namespace"]),
                ).fetchone()
                if not start_exists or not end_exists:
                    orphan_edges += 1
                    add_error(
                        f"{relative_path}:{row_no} orphan endpoint "
                        f"{start_id!r}->{end_id!r}"
                    )
                try:
                    if spec["type"] in {
                        "HADITH_IN_COLLECTION",
                        "HADITH_IN_TRADITION",
                        "HADITH_FROM_SOURCE",
                        "REPORT_SUPPORTED_BY",
                        "COLLECTION_IN_TRADITION",
                        "COLLECTION_FROM_SOURCE",
                        "HADITH_IN_BOOK",
                        "HADITH_IN_CHAPTER",
                        "CHAPTER_IN_BOOK",
                        "BOOK_IN_COLLECTION",
                        "NARRATOR_FROM_SOURCE",
                        "EVIDENCE_FROM_SOURCE",
                        "BIOGRAPHY_OF",
                        "BIOGRAPHY_FROM_SOURCE",
                        "ATTRIBUTED_TO",
                        "ALIAS_OF",
                    }:
                        connection.execute(
                            "INSERT INTO memberships VALUES (?, ?, ?, ?)",
                            (
                                spec["type"],
                                start_id,
                                end_id,
                                row["provenance:string"],
                            ),
                        )
                    if spec["type"] == "HAS_CHAIN":
                        connection.execute(
                            "INSERT INTO has_chain VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                int(row["branch:int"]),
                                row["source_record_id:string"],
                                row["extraction_method:string"],
                                row["sanad_confidence:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "INCLUDES_MENTION":
                        connection.execute(
                            "INSERT INTO includes_mention VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                int(row["position:int"]),
                                int(row["branch:int"]),
                                row["source_record_id:string"],
                                row["extraction_method:string"],
                                row["sanad_confidence:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "NEXT_IN_CHAIN":
                        connection.execute(
                            "INSERT INTO next_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                row["chain_id:string"],
                                row["hadith_id:string"],
                                int(row["from_position:int"]),
                                int(row["to_position:int"]),
                                row["source_record_id:string"],
                                row["extraction_method:string"],
                                row["sanad_confidence:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "RESOLVES_TO":
                        connection.execute(
                            "INSERT INTO resolutions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                row["chain_id:string"],
                                row["hadith_id:string"],
                                int(row["position:int"]),
                                row["source_record_id:string"],
                                row["extraction_method:string"],
                                row["sanad_confidence:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "INCLUDES":
                        connection.execute(
                            "INSERT INTO includes_narrator VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                int(row["position:int"]),
                                int(row["branch:int"]),
                                row["source_record_id:string"],
                                row["extraction_method:string"],
                                row["sanad_confidence:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "NARRATED_FROM":
                        connection.execute(
                            "INSERT INTO narrated_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                row["chain_id:string"],
                                row["hadith_id:string"],
                                int(row["from_position:int"]),
                                int(row["to_position:int"]),
                                row["source_record_id:string"],
                                row["extraction_method:string"],
                                row["sanad_confidence:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "TRANSLATION_OF":
                        connection.execute(
                            "INSERT INTO translation_of VALUES (?, ?)",
                            (start_id, end_id),
                        )
                    elif spec["type"] == "TRANSLATION_SUPPORTED_BY":
                        connection.execute(
                            "INSERT INTO translation_supported_by VALUES (?, ?)",
                            (start_id, end_id),
                        )
                    elif spec["type"] == "BIOGRAPHY_OF":
                        connection.execute(
                            "INSERT INTO biography_of VALUES (?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                row["review_state:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "BIOGRAPHY_FROM_SOURCE":
                        connection.execute(
                            "INSERT INTO biography_from_source VALUES (?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                row["review_state:string"],
                                row["provenance:string"],
                            ),
                        )
                    elif spec["type"] == "STUDENT_OF":
                        evidence_fields = row["evidence_fields:string"].split("|")
                        if (
                            not evidence_fields
                            or set(evidence_fields)
                            - {"students_inds", "teachers_inds"}
                            or evidence_fields != sorted(set(evidence_fields))
                        ):
                            raise ValueError(
                                "invalid or non-canonical evidence_fields"
                            )
                        evidence_count = int(row["evidence_count:int"])
                        reciprocal = _as_bool(
                            row["reciprocal:boolean"],
                            f"{relative_path}:{row_no} reciprocal",
                            add_error,
                        )
                        if reciprocal is None:
                            raise ValueError("invalid reciprocal boolean")
                        if (
                            evidence_count != len(evidence_fields)
                            or reciprocal != (len(evidence_fields) == 2)
                            or row["review_state:string"]
                            != RAWI_PROFILE_REVIEW_STATE
                            or row["provenance:string"]
                            != RAWI_PROFILE_PROVENANCE
                        ):
                            raise ValueError(
                                "indexed learning evidence contract mismatch"
                            )
                        connection.execute(
                            "INSERT INTO student_of VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (
                                start_id,
                                end_id,
                                row["evidence_fields:string"],
                                evidence_count,
                                int(reciprocal),
                                row["review_state:string"],
                                row["provenance:string"],
                            ),
                        )
                except (KeyError, TypeError, ValueError, sqlite3.IntegrityError) as error:
                    add_error(f"{relative_path}:{row_no} invalid properties: {error}")
        connection.commit()

        connection.executescript(
            """
            CREATE INDEX memberships_type_start
              ON memberships(edge_type, start_id);
            CREATE INDEX memberships_type_end
              ON memberships(edge_type, end_id);
            CREATE INDEX translation_of_translation
              ON translation_of(translation_id);
            CREATE INDEX translation_of_hadith
              ON translation_of(hadith_id);
            CREATE INDEX translation_evidence_translation
              ON translation_supported_by(translation_id);
            """
        )
        connection.commit()

        membership_checks = {
            "HADITH_IN_COLLECTION": """
                SELECT COUNT(*) FROM (
                    SELECT h.id
                    FROM hadiths h
                    LEFT JOIN memberships m
                      ON m.edge_type = 'HADITH_IN_COLLECTION'
                     AND m.start_id = h.id
                    GROUP BY h.id, h.source_work_id, h.provenance
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != 'collection:' || h.source_work_id
                       OR MIN(m.provenance) != h.provenance
                )
            """,
            "HADITH_IN_TRADITION": """
                SELECT COUNT(*) FROM (
                    SELECT h.id
                    FROM hadiths h
                    LEFT JOIN memberships m
                      ON m.edge_type = 'HADITH_IN_TRADITION'
                     AND m.start_id = h.id
                    GROUP BY h.id, h.tradition, h.provenance
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != 'tradition:' || LOWER(h.tradition)
                       OR MIN(m.provenance) != h.provenance
                )
            """,
            "HADITH_FROM_SOURCE": """
                SELECT COUNT(*) FROM (
                    SELECT h.id
                    FROM hadiths h
                    LEFT JOIN memberships m
                      ON m.edge_type = 'HADITH_FROM_SOURCE'
                     AND m.start_id = h.id
                    GROUP BY h.id, h.source_id, h.provenance
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != h.source_id
                       OR MIN(m.provenance) != h.provenance
                )
            """,
            "REPORT_SUPPORTED_BY": """
                SELECT COUNT(*) FROM (
                    SELECT h.id
                    FROM hadiths h
                    LEFT JOIN memberships m
                      ON m.edge_type = 'REPORT_SUPPORTED_BY'
                     AND m.start_id = h.id
                    GROUP BY h.id, h.record_id, h.provenance
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != 'evidence:report:' || h.record_id
                       OR MIN(m.provenance) != h.provenance
                )
            """,
            "COLLECTION_IN_TRADITION": """
                SELECT COUNT(*) FROM (
                    SELECT c.id
                    FROM collections c
                    LEFT JOIN memberships m
                      ON m.edge_type = 'COLLECTION_IN_TRADITION'
                     AND m.start_id = c.id
                    GROUP BY c.id, c.tradition
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != 'tradition:' || LOWER(c.tradition)
                )
            """,
            "COLLECTION_FROM_SOURCE": """
                SELECT COUNT(*) FROM (
                    SELECT c.id
                    FROM collections c
                    LEFT JOIN memberships m
                      ON m.edge_type = 'COLLECTION_FROM_SOURCE'
                     AND m.start_id = c.id
                    GROUP BY c.id, c.source_id
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != c.source_id
                )
            """,
            "BOOK_IN_COLLECTION": """
                SELECT COUNT(*) FROM (
                    SELECT b.id
                    FROM books b
                    LEFT JOIN memberships m
                      ON m.edge_type = 'BOOK_IN_COLLECTION'
                     AND m.start_id = b.id
                    GROUP BY b.id, b.collection_id
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != b.collection_id
                )
            """,
            "CHAPTER_IN_BOOK": """
                SELECT COUNT(*) FROM (
                    SELECT c.id
                    FROM chapters c
                    LEFT JOIN memberships m
                      ON m.edge_type = 'CHAPTER_IN_BOOK'
                     AND m.start_id = c.id
                    GROUP BY c.id, c.book_id
                    HAVING (
                        c.book_id != '' AND (
                            COUNT(m.end_id) != 1
                            OR MIN(m.end_id) != c.book_id
                        )
                    ) OR (
                        c.book_id = '' AND COUNT(m.end_id) != 0
                    )
                )
            """,
            "NARRATOR_FROM_SOURCE": """
                SELECT COUNT(*) FROM (
                    SELECT n.id
                    FROM narrators n
                    LEFT JOIN memberships m
                      ON m.edge_type = 'NARRATOR_FROM_SOURCE'
                     AND m.start_id = n.id
                    GROUP BY n.id
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != 'source:narrator-lexicon'
                )
            """,
            "BIOGRAPHY_OF": """
                SELECT COUNT(*) FROM (
                    SELECT b.id
                    FROM biographies b
                    LEFT JOIN memberships m
                      ON m.edge_type = 'BIOGRAPHY_OF'
                     AND m.start_id = b.id
                    GROUP BY b.id, b.subject_id, b.review_state, b.provenance
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != b.subject_id
                       OR MIN(m.provenance) != b.provenance
                )
            """,
            "BIOGRAPHY_FROM_SOURCE": """
                SELECT COUNT(*) FROM (
                    SELECT b.id
                    FROM biographies b
                    LEFT JOIN memberships m
                      ON m.edge_type = 'BIOGRAPHY_FROM_SOURCE'
                     AND m.start_id = b.id
                    GROUP BY b.id, b.source_id, b.review_state, b.provenance
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != b.source_id
                       OR MIN(m.provenance) != b.provenance
                )
            """,
            "EVIDENCE_FROM_SOURCE": """
                SELECT COUNT(*) FROM (
                    SELECT e.id
                    FROM evidence e
                    LEFT JOIN memberships m
                      ON m.edge_type = 'EVIDENCE_FROM_SOURCE'
                     AND m.start_id = e.id
                    GROUP BY e.id, e.expected_source_id
                    HAVING COUNT(m.end_id) != 1
                       OR MIN(m.end_id) != e.expected_source_id
                )
            """,
            "ALIAS_OF": """
                SELECT COUNT(*) FROM (
                    SELECT a.id
                    FROM aliases a
                    LEFT JOIN memberships m
                      ON m.edge_type = 'ALIAS_OF'
                     AND m.start_id = a.id
                    GROUP BY a.id, a.alias_kind
                    HAVING (
                        a.alias_kind = 'canonical_name'
                        AND COUNT(m.end_id) != 1
                    ) OR (
                        a.alias_kind != 'canonical_name'
                        AND COUNT(m.end_id) != 0
                    )
                )
            """,
        }
        membership_integrity_errors = 0
        for edge_type, query in membership_checks.items():
            mismatch_count = connection.execute(query).fetchone()[0]
            if mismatch_count:
                membership_integrity_errors += mismatch_count
                add_error(
                    f"{edge_type} semantic/cardinality failures: "
                    f"{mismatch_count}"
                )
        profile_link_failures = connection.execute(
            """
            SELECT COUNT(*) FROM biographies b
            LEFT JOIN narrators n ON n.id = b.subject_id
            LEFT JOIN biography_of bo ON bo.biography_id = b.id
            LEFT JOIN biography_from_source bs ON bs.biography_id = b.id
            LEFT JOIN sources s ON s.id = b.source_id
            WHERE n.id IS NULL OR n.scholar_indx != b.scholar_indx
               OR bo.biography_id IS NULL
               OR bo.narrator_id != b.subject_id
               OR bo.review_state != b.review_state
               OR bo.provenance != b.provenance
               OR bs.biography_id IS NULL
               OR bs.source_id != b.source_id
               OR bs.review_state != b.review_state
               OR bs.provenance != b.provenance
               OR s.id IS NULL
            """
        ).fetchone()[0]
        if profile_link_failures:
            membership_integrity_errors += profile_link_failures
            add_error(
                "narrator Biography/Profile linkage failures: "
                f"{profile_link_failures}"
            )

        self_student_edges = connection.execute(
            "SELECT COUNT(*) FROM student_of WHERE student_id = teacher_id"
        ).fetchone()[0]
        if self_student_edges:
            membership_integrity_errors += self_student_edges
            add_error(
                f"STUDENT_OF self-link failures: {self_student_edges}"
            )
        actual_student_edges = {
            (student_scholar, teacher_scholar): {
                "fields": set(evidence_fields.split("|")),
                "evidence_count": evidence_count,
                "reciprocal": bool(reciprocal),
            }
            for (
                student_scholar,
                teacher_scholar,
                evidence_fields,
                evidence_count,
                reciprocal,
            ) in connection.execute(
                """
                SELECT student.scholar_indx, teacher.scholar_indx,
                       edge.evidence_fields, edge.evidence_count,
                       edge.reciprocal
                FROM student_of edge
                JOIN narrators student ON student.id = edge.student_id
                JOIN narrators teacher ON teacher.id = edge.teacher_id
                """
            )
        }
        if bound_rawis_path is not None:
            learning_edge_failures = 0
            if set(actual_student_edges) != set(expected_student_edges):
                learning_edge_failures += len(
                    set(actual_student_edges) ^ set(expected_student_edges)
                )
            for pair in set(actual_student_edges) & set(expected_student_edges):
                actual = actual_student_edges[pair]
                expected_fields = expected_student_edges[pair]
                if (
                    actual["fields"] != expected_fields
                    or actual["evidence_count"] != len(expected_fields)
                    or actual["reciprocal"] != (len(expected_fields) == 2)
                ):
                    learning_edge_failures += 1
            if learning_edge_failures:
                membership_integrity_errors += learning_edge_failures
                rawi_source_binding_errors += learning_edge_failures
                add_error(
                    "STUDENT_OF source binding/direction failures: "
                    f"{learning_edge_failures}"
                )

        declared_profile_contract = manifest.get("narrator_profiles")
        static_profile_contract = {
            "raw_profile_fields": list(RAWI_PROFILE_COLUMNS),
            "profile_review_state": RAWI_PROFILE_REVIEW_STATE,
            "profile_provenance": RAWI_PROFILE_PROVENANCE,
            "direction": "student_to_teacher",
            "evidence_policy": (
                "teachers_inds on the student row and students_inds on the "
                "teacher row are aggregated without claiming citation review"
            ),
        }
        if not isinstance(declared_profile_contract, dict):
            add_error("narrator_profiles manifest contract is missing")
        else:
            for key, value in static_profile_contract.items():
                if declared_profile_contract.get(key) != value:
                    add_error(
                        f"narrator_profiles manifest mismatch: {key}"
                    )
            if expected_profile_stats:
                for key, value in expected_profile_stats.items():
                    if declared_profile_contract.get(key) != value:
                        add_error(
                            f"narrator_profiles manifest mismatch: {key}"
                        )
            elif (
                declared_profile_contract.get("profile_nodes")
                != connection.execute(
                    "SELECT COUNT(*) FROM biographies"
                ).fetchone()[0]
                or declared_profile_contract.get(
                    "exported_student_of_pairs"
                )
                != len(actual_student_edges)
            ):
                add_error(
                    "narrator_profiles manifest internal count mismatch"
                )
        invalid_attributions = connection.execute(
            """
            SELECT COUNT(*) FROM memberships m
            LEFT JOIN hadiths h ON h.id = m.start_id
            LEFT JOIN aliases a ON a.id = m.end_id
            WHERE m.edge_type = 'ATTRIBUTED_TO'
              AND (
                  h.id IS NULL OR h.excluded != 0
                  OR a.id IS NULL OR a.alias_kind != 'attribution_surface'
                  OR a.provenance != 'surface_normalization_v1'
                  OR m.provenance != h.provenance
              )
            """
        ).fetchone()[0]
        duplicate_attributions = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT start_id FROM memberships
                WHERE edge_type = 'ATTRIBUTED_TO'
                GROUP BY start_id HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        if invalid_attributions or duplicate_attributions:
            membership_integrity_errors += (
                invalid_attributions + duplicate_attributions
            )
            add_error(
                "ATTRIBUTED_TO semantic/cardinality failures: "
                f"invalid={invalid_attributions}, "
                f"duplicate={duplicate_attributions}"
            )
        structure_membership_failures = connection.execute(
            """
            SELECT
              (
                SELECT COUNT(*) FROM (
                    SELECT h.id
                    FROM hadiths h
                    LEFT JOIN memberships m
                      ON m.edge_type = 'HADITH_IN_BOOK'
                     AND m.start_id = h.id
                    LEFT JOIN books b ON b.id = m.end_id
                    GROUP BY h.id, h.source_work_id
                    HAVING COUNT(m.end_id) > 1
                       OR (
                         COUNT(m.end_id) = 1
                         AND MIN(b.collection_id) !=
                             'collection:' || h.source_work_id
                       )
                )
              )
              +
              (
                SELECT COUNT(*) FROM (
                    SELECT h.id
                    FROM hadiths h
                    LEFT JOIN memberships m
                      ON m.edge_type = 'HADITH_IN_CHAPTER'
                     AND m.start_id = h.id
                    LEFT JOIN chapters c ON c.id = m.end_id
                    GROUP BY h.id, h.source_work_id
                    HAVING COUNT(m.end_id) > 1
                       OR (
                         COUNT(m.end_id) = 1
                         AND MIN(c.collection_id) !=
                             'collection:' || h.source_work_id
                       )
                )
              )
              +
              (
                SELECT COUNT(*) FROM books b
                WHERE NOT EXISTS (
                    SELECT 1 FROM memberships m
                    WHERE m.edge_type = 'HADITH_IN_BOOK'
                      AND m.end_id = b.id
                )
              )
              +
              (
                SELECT COUNT(*) FROM chapters c
                WHERE NOT EXISTS (
                    SELECT 1 FROM memberships m
                    WHERE m.edge_type = 'HADITH_IN_CHAPTER'
                      AND m.end_id = c.id
                )
              )
            """
        ).fetchone()[0]
        if structure_membership_failures:
            membership_integrity_errors += structure_membership_failures
            add_error(
                "Book/Chapter membership failures: "
                f"{structure_membership_failures}"
            )

        connection.executescript(
            """
            CREATE INDEX includes_mention_chain ON includes_mention(chain_id);
            CREATE INDEX next_edges_chain ON next_edges(chain_id);
            CREATE INDEX resolutions_chain ON resolutions(chain_id);
            CREATE INDEX includes_narrator_chain ON includes_narrator(chain_id);
            CREATE INDEX narrated_edges_chain ON narrated_edges(chain_id);
            """
        )
        connection.commit()

        chain_integrity_errors = 0

        def chain_error(message: str) -> None:
            nonlocal chain_integrity_errors
            chain_integrity_errors += 1
            add_error(message)

        mention_stats = {
            chain_id: (count, minimum, maximum, distinct_count)
            for chain_id, count, minimum, maximum, distinct_count in connection.execute(
                "SELECT chain_id, COUNT(*), MIN(position), MAX(position), "
                "COUNT(DISTINCT position) FROM mentions GROUP BY chain_id"
            )
        }
        next_counts = dict(
            connection.execute(
                "SELECT chain_id, COUNT(*) FROM next_edges GROUP BY chain_id"
            )
        )
        resolution_counts = dict(
            connection.execute(
                "SELECT chain_id, COUNT(*) FROM resolutions GROUP BY chain_id"
            )
        )
        include_counts = dict(
            connection.execute(
                "SELECT chain_id, COUNT(*) FROM includes_narrator GROUP BY chain_id"
            )
        )
        narrated_counts = dict(
            connection.execute(
                "SELECT chain_id, COUNT(*) FROM narrated_edges GROUP BY chain_id"
            )
        )
        has_chain_counts = dict(
            connection.execute(
                "SELECT chain_id, COUNT(*) FROM has_chain GROUP BY chain_id"
            )
        )
        for (
            chain_id,
            hadith_id,
            source_record_id,
            branch,
            length,
            resolved,
            extraction_method,
            sanad_confidence,
            provenance,
        ) in connection.execute(
            "SELECT * FROM chains ORDER BY id"
        ):
            stats = mention_stats.get(chain_id, (0, None, None, 0))
            if not (
                stats[0] == length
                and stats[3] == length
                and (length == 0 or (stats[1] == 0 and stats[2] == length - 1))
            ):
                chain_error(f"non-contiguous NameMention positions: {chain_id}")
            if next_counts.get(chain_id, 0) != max(length - 1, 0):
                chain_error(f"NEXT_IN_CHAIN count mismatch: {chain_id}")
            if has_chain_counts.get(chain_id, 0) != 1:
                chain_error(f"HAS_CHAIN count mismatch: {chain_id}")
            if resolved:
                if resolution_counts.get(chain_id, 0) != length:
                    chain_error(f"RESOLVES_TO count mismatch: {chain_id}")
                if include_counts.get(chain_id, 0) != length:
                    chain_error(f"INCLUDES count mismatch: {chain_id}")
                if narrated_counts.get(chain_id, 0) != max(length - 1, 0):
                    chain_error(f"NARRATED_FROM count mismatch: {chain_id}")
            elif (
                resolution_counts.get(chain_id, 0)
                or include_counts.get(chain_id, 0)
                or narrated_counts.get(chain_id, 0)
            ):
                chain_error(f"partial resolution leaked onto unresolved chain: {chain_id}")

        branch_group_failures = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT c.hadith_id
                FROM chains c
                GROUP BY c.hadith_id
                HAVING MIN(c.branch) != 0
                   OR MAX(c.branch) != COUNT(DISTINCT c.branch) - 1
                   OR COUNT(*) != COUNT(DISTINCT c.branch)
            )
            """
        ).fetchone()[0]
        if branch_group_failures:
            chain_error(
                "non-contiguous or duplicate branch indexes for "
                f"{branch_group_failures} Hadiths"
            )
        invalid_chain_identity_count = connection.execute(
            """
            SELECT COUNT(*) FROM chains c
            LEFT JOIN hadiths h ON h.id = c.hadith_id
            WHERE h.id IS NULL
               OR c.source_record_id != h.source_record_id
               OR c.id != 'chain:' || h.record_id || ':' ||
                  printf('%04d', c.branch)
               OR c.length <= 0
            """
        ).fetchone()[0]
        if invalid_chain_identity_count:
            chain_error(
                f"invalid Chain identity/length rows: {invalid_chain_identity_count}"
            )

        chain_sql_checks = {
            "HAS_CHAIN binding": """
                SELECT COUNT(*) FROM has_chain h
                LEFT JOIN chains c ON c.id = h.chain_id
                LEFT JOIN hadiths report ON report.id = c.hadith_id
                WHERE c.id IS NULL OR h.hadith_id != c.hadith_id
                   OR h.branch != c.branch OR h.provenance != c.provenance
                   OR report.id IS NULL
                   OR c.source_record_id != report.source_record_id
                   OR h.source_record_id != c.source_record_id
                   OR h.extraction_method != c.extraction_method
                   OR h.sanad_confidence != c.sanad_confidence
            """,
            "INCLUDES_MENTION binding": """
                SELECT COUNT(*) FROM includes_mention i
                LEFT JOIN mentions m ON m.id = i.mention_id
                LEFT JOIN chains c ON c.id = i.chain_id
                WHERE m.id IS NULL OR c.id IS NULL OR m.chain_id != i.chain_id
                   OR m.position != i.position OR m.branch != i.branch
                   OR m.source_record_id != c.source_record_id
                   OR i.source_record_id != c.source_record_id
                   OR m.provenance != i.provenance
                   OR m.extraction_method != i.extraction_method
                   OR m.sanad_confidence != i.sanad_confidence
                   OR c.extraction_method != i.extraction_method
                   OR c.sanad_confidence != i.sanad_confidence
            """,
            "NEXT_IN_CHAIN adjacency": """
                SELECT COUNT(*) FROM next_edges n
                LEFT JOIN mentions a ON a.id = n.start_id
                LEFT JOIN mentions b ON b.id = n.end_id
                LEFT JOIN chains c ON c.id = n.chain_id
                WHERE a.id IS NULL OR b.id IS NULL OR c.id IS NULL
                   OR n.to_position != n.from_position + 1
                   OR a.chain_id != n.chain_id OR b.chain_id != n.chain_id
                   OR a.position != n.from_position OR b.position != n.to_position
                   OR n.hadith_id != c.hadith_id
                   OR n.source_record_id != c.source_record_id
                   OR n.provenance != c.provenance
                   OR n.extraction_method != c.extraction_method
                   OR n.sanad_confidence != c.sanad_confidence
            """,
            "RESOLVES_TO binding": """
                SELECT COUNT(*) FROM resolutions r
                LEFT JOIN mentions m ON m.id = r.mention_id
                LEFT JOIN chains c ON c.id = r.chain_id
                WHERE m.id IS NULL OR c.id IS NULL OR c.resolved != 1
                   OR m.chain_id != r.chain_id OR m.position != r.position
                   OR m.source_record_id != c.source_record_id
                   OR r.source_record_id != c.source_record_id
                   OR r.hadith_id != c.hadith_id OR r.provenance != c.provenance
                   OR r.extraction_method != c.extraction_method
                   OR r.sanad_confidence != c.sanad_confidence
            """,
            "INCLUDES/RESOLVES_TO equivalence": """
                SELECT COUNT(*) FROM includes_narrator i
                LEFT JOIN chains c ON c.id = i.chain_id
                LEFT JOIN resolutions r
                  ON r.chain_id = i.chain_id AND r.position = i.position
                 AND r.narrator_id = i.narrator_id
                WHERE c.id IS NULL OR r.mention_id IS NULL
                   OR i.branch != c.branch OR i.provenance != c.provenance
                   OR i.source_record_id != c.source_record_id
                   OR i.extraction_method != c.extraction_method
                   OR i.sanad_confidence != c.sanad_confidence
            """,
            "NARRATED_FROM binding": """
                SELECT COUNT(*) FROM narrated_edges n
                LEFT JOIN chains c ON c.id = n.chain_id
                LEFT JOIN resolutions a
                  ON a.chain_id = n.chain_id AND a.position = n.from_position
                 AND a.narrator_id = n.start_id
                LEFT JOIN resolutions b
                  ON b.chain_id = n.chain_id AND b.position = n.to_position
                 AND b.narrator_id = n.end_id
                WHERE c.id IS NULL OR a.mention_id IS NULL OR b.mention_id IS NULL
                   OR n.to_position != n.from_position + 1
                   OR n.hadith_id != c.hadith_id
                   OR n.source_record_id != c.source_record_id
                   OR n.provenance != c.provenance
                   OR n.extraction_method != c.extraction_method
                   OR n.sanad_confidence != c.sanad_confidence
            """,
        }
        for label, query in chain_sql_checks.items():
            mismatch_count = connection.execute(query).fetchone()[0]
            if mismatch_count:
                chain_error(f"{label} failures: {mismatch_count}")

        translation_count = connection.execute(
            "SELECT COUNT(*) FROM translations"
        ).fetchone()[0]
        hadith_count = connection.execute(
            "SELECT COUNT(*) FROM hadiths"
        ).fetchone()[0]
        expected_translation_count = connection.execute(
            "SELECT COUNT(*) FROM hadiths "
            "WHERE translation_disposition = 'exported_source_surface'"
        ).fetchone()[0]
        if translation_count != expected_translation_count:
            add_error(
                "translation count must equal export-eligible Hadith count: "
                f"{translation_count} != {expected_translation_count}"
            )
        invalid_translation_links = connection.execute(
            """
            SELECT COUNT(*) FROM translations t
            LEFT JOIN translation_of x ON x.translation_id = t.id
            LEFT JOIN hadiths h ON h.id = x.hadith_id
            LEFT JOIN source_arabic s ON s.record_id = h.record_id
            WHERE x.translation_id IS NULL OR h.id IS NULL
               OR s.record_id IS NULL
               OR h.translation_disposition != 'exported_source_surface'
               OR t.id != 'translation:' || h.record_id || ':en'
               OR t.text_hash != s.translation_text_hash
               OR t.status != s.translation_status
               OR t.source != s.translation_source
               OR t.model != s.translation_model
               OR t.review_state != s.translation_review_state
               OR t.source_record_id != h.source_record_id
               OR t.arabic_hash != h.arabic_hash
               OR t.provenance != h.provenance
               OR t.candidate_only != 0
            """
        ).fetchone()[0]
        duplicate_translation_links = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT translation_id FROM translation_of
                GROUP BY translation_id HAVING COUNT(*) != 1
            )
            """
        ).fetchone()[0]
        hadith_translation_target_failures = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT h.id
                FROM hadiths h
                LEFT JOIN translation_of x ON x.hadith_id = h.id
                GROUP BY h.id, h.translation_disposition
                HAVING (
                    h.translation_disposition = 'exported_source_surface'
                    AND COUNT(x.translation_id) != 1
                ) OR (
                    h.translation_disposition != 'exported_source_surface'
                    AND COUNT(x.translation_id) != 0
                )
            )
            """
        ).fetchone()[0]
        unsupported_translation_evidence = connection.execute(
            """
            SELECT COUNT(*) FROM translations t
            LEFT JOIN translation_supported_by x ON x.translation_id = t.id
            LEFT JOIN evidence e ON e.id = x.evidence_id
            WHERE x.translation_id IS NULL OR e.id IS NULL
            """
        ).fetchone()[0]
        if (
            invalid_translation_links
            or duplicate_translation_links
            or hadith_translation_target_failures
        ):
            add_error(
                "TRANSLATION_OF integrity failures: "
                f"invalid={invalid_translation_links}, "
                f"duplicate={duplicate_translation_links}, "
                f"target={hadith_translation_target_failures}"
            )
        if unsupported_translation_evidence:
            add_error(
                "TRANSLATION_SUPPORTED_BY integrity failures: "
                f"{unsupported_translation_evidence}"
            )

        expected_gated_files = {
            "nodes/citations.csv",
            "nodes/events.csv",
            "nodes/places.csv",
            "relationships/cites.csv",
            "relationships/supported_by.csv",
        }
        nonempty_gated = [
            item["path"]
            for item in actual_graph_metadata
            if item["path"] in expected_gated_files and item["row_count"] != 0
        ]
        if nonempty_gated:
            add_error(f"non-ready evidence entities were populated: {nonempty_gated}")
        declared_gates = {
            item.get("entity"): item.get("reason")
            for item in manifest.get("empty_gated_entities", [])
            if isinstance(item, dict)
        }
        if declared_gates != EMPTY_GATED_ENTITIES:
            add_error("empty_gated_entities manifest contract mismatch")

        counts = manifest.get("counts", {})
        derived_counts = {
            "by_tradition": dict(sorted(by_tradition.items())),
            "by_collection": dict(sorted(by_collection.items())),
            "by_provenance_source": dict(sorted(by_provenance_source.items())),
            "input_translation_status": dict(
                sorted(input_translation_status.items())
            ),
            "exported_translation_status": dict(
                sorted(exported_translation_status.items())
            ),
            "translation_disposition": dict(
                sorted(translation_dispositions.items())
            ),
        }
        for key, value in derived_counts.items():
            if counts.get(key) != value:
                add_error(f"manifest cross-count mismatch: {key}")
        totals = manifest.get("totals", {})
        expected_totals = {
            "nodes": actual_node_rows,
            "relationships": actual_relationship_rows,
            "hadith_records": hadith_count,
            "rawi_records": connection.execute(
                "SELECT COUNT(*) FROM narrators"
            ).fetchone()[0],
        }
        for key, value in expected_totals.items():
            if totals.get(key) != value:
                add_error(f"manifest total mismatch: {key}")

        curation_binding_errors = 0
        if curation_snapshot is not None:
            if not isinstance(curation_snapshot, dict):
                curation_binding_errors += 1
                add_error("curation_snapshot must be an object or null")
            else:
                if curation_snapshot.get("record_count") != hadith_count:
                    curation_binding_errors += 1
                    add_error("curation_snapshot record_count mismatch")
                if curation_snapshot.get("source_counts") != derived_counts[
                    "by_collection"
                ]:
                    curation_binding_errors += 1
                    add_error("curation_snapshot source_counts mismatch")
                if curation_snapshot.get("tradition_counts") != derived_counts[
                    "by_tradition"
                ]:
                    curation_binding_errors += 1
                    add_error("curation_snapshot tradition_counts mismatch")
                if bound_curation_manifest is not None:
                    expected_snapshot = {
                        "path": (
                            curation_input_item.get("path")
                            if curation_input_item
                            else None
                        ),
                        "sha256": (
                            curation_input_item.get("sha256")
                            if curation_input_item
                            else None
                        ),
                        "schema_version": bound_curation_manifest.get(
                            "schema_version"
                        ),
                        "record_count": bound_curation_manifest.get(
                            "record_count"
                        ),
                        "candidate_content_sha256": bound_curation_manifest.get(
                            "candidate_content_sha256", ""
                        ),
                        "ready_for_full_load": bound_curation_manifest.get(
                            "ready_for_full_load"
                        ),
                        "full_load_gates": bound_curation_manifest.get(
                            "full_load_gates", {}
                        ),
                        "release_blockers": bound_curation_manifest.get(
                            "release_blockers", {}
                        ),
                        "source_counts": bound_curation_manifest.get(
                            "source_counts", {}
                        ),
                        "tradition_counts": bound_curation_manifest.get(
                            "tradition_counts", {}
                        ),
                    }
                    if curation_snapshot != expected_snapshot:
                        curation_binding_errors += 1
                        add_error(
                            "curation_snapshot does not match its bound manifest"
                        )

        declared_exclusions = {
            item.get("record_id"): item
            for item in manifest.get("exclusions", [])
            if isinstance(item, dict)
        }
        if set(declared_exclusions) != set(SOURCE_QUALITY_EXCLUSIONS):
            add_error("manifest exclusion identity set mismatch")
        for record_id, reason in SOURCE_QUALITY_EXCLUSIONS.items():
            item = declared_exclusions.get(record_id, {})
            present = bool(
                connection.execute(
                    "SELECT 1 FROM hadiths WHERE record_id = ?", (record_id,)
                ).fetchone()
            )
            if item.get("reason") != reason or item.get("present") is not present:
                add_error(f"manifest exclusion binding mismatch: {record_id}")
            if coverage_scope == "complete" and not present:
                add_error(
                    f"complete bundle lacks source-quality exclusion: {record_id}"
                )

        compare_result = {"requested": False}
        if compare_bundle is not None:
            compare_result = _validate_compare_bundle(
                manifest, Path(compare_bundle), add_error
            )

        if source_release_state not in PUBLISHABLE_RELEASE_STATES:
            publication_blockers.append(
                f"source_release_state={source_release_state!r} is not publication-ready"
            )
        if coverage_scope != "complete":
            publication_blockers.append(
                f"coverage_scope={coverage_scope!r} is not a complete corpus"
            )
        if isinstance(curation_snapshot, dict):
            if not curation_snapshot.get("ready_for_full_load", False):
                publication_blockers.append(
                    "bound curation snapshot is not ready_for_full_load"
                )
            failed_curation_gates = sorted(
                name
                for name, gate in curation_snapshot.get(
                    "full_load_gates", {}
                ).items()
                if isinstance(gate, dict) and not gate.get("passed", False)
            )
            if failed_curation_gates:
                publication_blockers.append(
                    "bound curation gates failed: "
                    + ", ".join(failed_curation_gates)
                )
        if EMPTY_GATED_ENTITIES:
            publication_blockers.append(
                "citation-bound Citation/Place/Event curation is non-ready"
            )
        if RAWI_PROFILE_REVIEW_STATE not in PUBLISHABLE_REVIEW_STATES:
            publication_blockers.append(
                "narrator profiles are not publication-reviewed: "
                f"{RAWI_PROFILE_REVIEW_STATE}"
            )
        if blank_translation_text:
            publication_blockers.append(
                f"{blank_translation_text} translations have blank text"
            )
        if blank_translation_source:
            publication_blockers.append(
                f"{blank_translation_source} translations lack provenance source"
            )
        if blank_translation_review:
            publication_blockers.append(
                f"{blank_translation_review} translations lack review state"
            )
        if missing_required_model:
            publication_blockers.append(
                f"{missing_required_model} model-provenance translations lack model ID"
            )
        if non_publishable_review:
            publication_blockers.append(
                f"{non_publishable_review} translations are not source/human verified"
            )
        for disposition in (
            "omitted_machine_candidate",
            "omitted_missing_provenance",
            "omitted_missing_text",
        ):
            disposition_count = translation_dispositions.get(disposition, 0)
            if disposition_count:
                publication_blockers.append(
                    f"{disposition_count} reports have {disposition}"
                )
        unresolved_chain_count = connection.execute(
            "SELECT COUNT(*) FROM chains WHERE resolved = 0"
        ).fetchone()[0]
        if unresolved_chain_count:
            publication_blockers.append(
                f"{unresolved_chain_count} extracted chains remain unresolved"
            )
        extraction_contract = manifest.get("extraction", {})
        if extraction_contract.get(
            "default_branch_limit"
        ) != DEFAULT_ISNAD_BRANCH_LIMIT or extraction_contract.get(
            "export_branch_limit"
        ) != EXPORT_ISNAD_BRANCH_LIMIT:
            add_error("isnad branch-limit contract mismatch")
        if not str(
            extraction_contract.get("empty_branch_policy") or ""
        ).strip():
            add_error("empty-branch policy is missing")
        extraction_limit_failures = extraction_contract.get("limit_failures")
        if extraction_limit_failures:
            add_error("isnad extraction limit failures prevent import readiness")
            publication_blockers.append("isnad extraction limit failures are recorded")

        integrity_gate_counts = {
            "orphan_edges": orphan_edges,
            "duplicate_relationship_occurrences": (
                duplicate_relationship_occurrences
            ),
            "membership_integrity_errors": membership_integrity_errors,
            "relationship_type_errors": relationship_type_errors,
            "arabic_hash_errors": arabic_hash_errors,
            "arabic_source_binding_errors": arabic_source_binding_errors,
            "rawi_profile_source_binding_errors": rawi_source_binding_errors,
            "chain_integrity_errors": chain_integrity_errors,
            "candidate_separation_errors": candidate_input_error_count,
        }
        warnings.extend(
            [
                f"translation_blank_text={blank_translation_text}",
                f"translation_blank_source={blank_translation_source}",
                f"translation_blank_review_state={blank_translation_review}",
                f"translation_missing_required_model={missing_required_model}",
                f"unresolved_chains={unresolved_chain_count}",
            ]
        )
        connection.close()

    import_ready = total_error_count == 0
    if not import_ready:
        publication_blockers.append("bundle integrity failed")
    publication_ready = import_ready and not publication_blockers
    gates = {
        "manifest_integrity": {
            "passed": not any(
                "manifest" in error or "missing graph file" in error
                for error in errors
            )
        },
        "unique_ids": {
            "passed": not any(
                "duplicate/colliding node ID" in error
                or "duplicate rawi" in error
                for error in errors
            )
        },
        "referential_integrity": {
            "passed": (
                integrity_gate_counts["orphan_edges"] == 0
                and integrity_gate_counts[
                    "duplicate_relationship_occurrences"
                ] == 0
                and integrity_gate_counts["membership_integrity_errors"] == 0
            ),
            "orphan_edges": integrity_gate_counts["orphan_edges"],
            "duplicate_relationship_occurrences": integrity_gate_counts[
                "duplicate_relationship_occurrences"
            ],
            "semantic_cardinality_errors": integrity_gate_counts[
                "membership_integrity_errors"
            ],
        },
        "tradition_source_normalization": {
            "passed": not any(
                "normalization mismatch" in error
                or "unregistered source" in error
                or "unsupported tradition" in error
                for error in errors
            )
        },
        "chain_integrity": {
            "passed": integrity_gate_counts["chain_integrity_errors"] == 0,
            "errors": integrity_gate_counts["chain_integrity_errors"],
        },
        "arabic_round_trip": {
            "passed": (
                integrity_gate_counts["arabic_hash_errors"] == 0
                and integrity_gate_counts["arabic_source_binding_errors"] == 0
            ),
            "errors": integrity_gate_counts["arabic_hash_errors"],
            "source_binding_errors": integrity_gate_counts[
                "arabic_source_binding_errors"
            ],
        },
        "narrator_profile_binding": {
            "passed": (
                rawi_profile_binding_available
                and rawi_profile_binding_performed
                and rawi_input_hash_valid
                and integrity_gate_counts[
                    "rawi_profile_source_binding_errors"
                ] == 0
                and integrity_gate_counts["membership_integrity_errors"] == 0
            ),
            "available": rawi_profile_binding_available,
            "performed": rawi_profile_binding_performed,
            "input_hash_valid": rawi_input_hash_valid,
            "source_binding_errors": integrity_gate_counts[
                "rawi_profile_source_binding_errors"
            ],
            "profile_nodes": (
                expected_profile_stats.get("profile_nodes")
                if expected_profile_stats
                else None
            ),
            "student_of_edges": (
                expected_profile_stats.get("exported_student_of_pairs")
                if expected_profile_stats
                else None
            ),
            "review_state": RAWI_PROFILE_REVIEW_STATE,
            "passed_for_publication": (
                RAWI_PROFILE_REVIEW_STATE in PUBLISHABLE_REVIEW_STATES
            ),
        },
        "translation_provenance": {
            "passed_for_import": candidate_input_error_count == 0,
            "passed_for_publication": not any(
                value
                for value in (
                    blank_translation_text,
                    blank_translation_source,
                    blank_translation_review,
                    missing_required_model,
                    non_publishable_review,
                )
            ),
            "blank_text": blank_translation_text,
            "blank_source": blank_translation_source,
            "blank_review_state": blank_translation_review,
            "missing_required_model": missing_required_model,
            "non_publishable_review_state": non_publishable_review,
        },
        "candidate_separation": {
            "passed": candidate_input_error_count == 0,
            "errors": candidate_input_error_count,
        },
        "manifest_cross_counts": {
            "passed": not any(
                "cross-count mismatch" in error
                or "manifest total mismatch" in error
                or "narrator_profiles manifest mismatch" in error
                for error in errors
            )
        },
        "source_curation_binding": {
            "passed": curation_binding_errors == 0,
            "errors": curation_binding_errors,
            "ready_for_full_load": (
                curation_snapshot.get("ready_for_full_load")
                if isinstance(curation_snapshot, dict)
                else None
            ),
        },
        "deterministic_compare": compare_result,
    }
    report = {
        "bundle_schema_version": manifest.get("bundle_schema_version"),
        "bundle_version": manifest.get("bundle_version"),
        "content_sha256": actual_content_hash,
        "source_release_state": manifest.get("source_release_state"),
        "import_ready": import_ready,
        "publication_ready": publication_ready,
        "error_count": total_error_count,
        "errors": errors,
        "warnings": warnings,
        "publication_blockers": sorted(set(publication_blockers)),
        "gates": gates,
    }
    if write_report:
        (bundle_dir / "validation_report.json").write_bytes(
            deterministic_json_bytes(report)
        )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--compare-bundle", type=Path)
    parser.add_argument("--require-publication-ready", action="store_true")
    parser.add_argument("--no-write-report", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = validate_bundle(
        args.bundle,
        args.compare_bundle,
        write_report=not args.no_write_report,
    )
    print(
        json.dumps(
            {
                "import_ready": report["import_ready"],
                "publication_ready": report["publication_ready"],
                "error_count": report["error_count"],
                "content_sha256": report.get("content_sha256", ""),
            },
            sort_keys=True,
        )
    )
    if not report["import_ready"]:
        return 2
    if args.require_publication_ready and not report["publication_ready"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
