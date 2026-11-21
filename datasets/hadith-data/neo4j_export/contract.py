"""Shared graph-bundle schema and deterministic helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

BUNDLE_SCHEMA_VERSION = 2
BUNDLE_VERSION = "2026.07.23.2"
DEFAULT_SOURCE_RELEASE_STATE = "unreviewed_local_snapshot"
DEFAULT_ISNAD_BRANCH_LIMIT = 64
EXPORT_ISNAD_BRANCH_LIMIT = 256

UNIFIED_COLUMNS = [
    "id", "hadith_id", "provider_file_id", "provider_book_id",
    "source", "source_work_id", "source_display_label", "tradition", "volume",
    "chapter_no", "hadith_no", "chapter", "category", "chain_indx", "text_ar",
    "text_en", "sanad", "sanad_confidence", "matn_ar", "matn_en", "school",
    "chain_type", "attributed_to", "narration_level", "grade_tradition",
    "grade_source", "grade_value", "gradings_full", "url", "page_ref",
    "record_id", "source_record_id", "provenance_source", "translation_status",
    "translation_source", "translation_model", "translation_review_status",
]

RAWI_PROFILE_COLUMNS = (
    "grade",
    "parents",
    "spouse",
    "siblings",
    "children",
    "birth_date_place",
    "places_of_stay",
    "death_date_place",
    "teachers",
    "students",
    "area_of_interest",
    "tags",
    "books",
    "students_inds",
    "teachers_inds",
    "birth_place",
    "birth_date",
    "birth_date_hijri",
    "birth_date_gregorian",
    "death_date_hijri",
    "death_date_gregorian",
    "death_place",
    "death_reason",
)
RAWI_COLUMNS = ("scholar_indx", "name", *RAWI_PROFILE_COLUMNS)
RAWI_PROFILE_PROVENANCE = "narrator-lexicon:all_rawis.csv"
RAWI_PROFILE_REVIEW_STATE = "source_status_unknown"
CANONICAL_TRADITIONS = ("Ibadi", "Imami", "Sunni", "Zaydi")
CANDIDATE_PATH_MARKERS = (
    "machine_translation_candidates",
    "narrator_alias_candidates",
)

SOURCE_QUALITY_EXCLUSIONS = {
    "thaqalayn:06840b21d9e61e1ab351aec4": (
        "confirmed Kitab al-Ghayba Introduction/paratext; not a hadith report"
    ),
    "thaqalayn:2a1ca7a8bc366eadfcbcb80f": (
        "55,003-character report reserved for separately journaled "
        "multi-request translation"
    ),
}

EMPTY_GATED_ENTITIES = {
    "Citation": "citation-bound evidence curation is empty/non-ready",
    "Event": "citation-bound evidence curation is empty/non-ready",
    "Place": "citation-bound evidence curation is empty/non-ready",
}

NODE_FILES = {
    "nodes/hadiths.csv": {
        "entity": "Hadith",
        "namespace": "Hadith-ID",
        "header": [
            "import_id:ID(Hadith-ID)", "id:string", "record_id:string",
            "source_record_id:string",
            "source:string", "source_work_id:string", "source_id:string",
            "tradition:string", "tradition_id:string", "hadith_no:string",
            "text_ar:string", "arabic_sha256:string", "sanad:string",
            "matn_ar:string", "url:string", "page_ref:string",
            "translation_status:string", "provenance:string",
            "translation_disposition:string",
            "quality_excluded:boolean", "quality_exclusion_reason:string",
            ":LABEL",
        ],
    },
    "nodes/narrators.csv": {
        "entity": "Narrator",
        "namespace": "Narrator-ID",
        "header": [
            "import_id:ID(Narrator-ID)", "id:string", "scholar_indx:int", "name:string",
            "source_id:string", ":LABEL",
        ],
    },
    "nodes/sources.csv": {
        "entity": "Source",
        "namespace": "Source-ID",
        "header": [
            "import_id:ID(Source-ID)", "id:string", "slug:string", "name:string",
            "release_state:string", ":LABEL",
        ],
    },
    "nodes/collections.csv": {
        "entity": "Collection",
        "namespace": "Collection-ID",
        "header": [
            "import_id:ID(Collection-ID)", "id:string", "source_work_id:string",
            "slug:string",
            "name:string", "tradition:string", "source_id:string", ":LABEL",
        ],
    },
    "nodes/books.csv": {
        "entity": "Book",
        "namespace": "Book-ID",
        "header": [
            "import_id:ID(Book-ID)", "id:string", "collection_id:string",
            "number:string",
            "name:string", "volume:string", "provider_file_id:string",
            "provider_book_id:string", "provenance:string", ":LABEL",
        ],
    },
    "nodes/chapters.csv": {
        "entity": "Chapter",
        "namespace": "Chapter-ID",
        "header": [
            "import_id:ID(Chapter-ID)", "id:string", "collection_id:string",
            "book_id:string",
            "number:string", "category_number:string",
            "provider_chapter_locator:string", "name:string",
            "provenance:string", ":LABEL",
        ],
    },
    "nodes/traditions.csv": {
        "entity": "Tradition",
        "namespace": "Tradition-ID",
        "header": [
            "import_id:ID(Tradition-ID)", "id:string", "name:string",
            "normalized_name:string",
            ":LABEL",
        ],
    },
    "nodes/chains.csv": {
        "entity": "Chain",
        "namespace": "Chain-ID",
        "header": [
            "import_id:ID(Chain-ID)", "id:string", "hadith_id:string",
            "source_record_id:string", "branch:int", "length:int",
            "resolved:boolean", "extraction_method:string",
            "sanad_confidence:string", "provenance:string", ":LABEL",
        ],
    },
    "nodes/name_mentions.csv": {
        "entity": "NameMention",
        "namespace": "NameMention-ID",
        "header": [
            "import_id:ID(NameMention-ID)", "id:string", "hadith_id:string",
            "source_record_id:string", "chain_id:string",
            "branch:int", "position:int", "surface:string",
            "normalized_surface:string", "extraction_method:string",
            "sanad_confidence:string", "provenance:string", ":LABEL",
        ],
    },
    "nodes/translations.csv": {
        "entity": "Translation",
        "namespace": "Translation-ID",
        "header": [
            "import_id:ID(Translation-ID)", "id:string", "language:string",
            "text:string",
            "status:string", "source:string", "model:string",
            "review_state:string", "source_record_id:string",
            "arabic_sha256:string", "provenance_source:string",
            "candidate_only:boolean", ":LABEL",
        ],
    },
    "nodes/aliases.csv": {
        "entity": "Alias",
        "namespace": "Alias-ID",
        "header": [
            "import_id:ID(Alias-ID)", "id:string", "surface:string",
            "normalized_surface:string",
            "alias_kind:string", "provenance:string", ":LABEL",
        ],
    },
    "nodes/evidence.csv": {
        "entity": "Evidence",
        "namespace": "Evidence-ID",
        "header": [
            "import_id:ID(Evidence-ID)", "id:string", "evidence_kind:string",
            "source_record_id:string", "provenance_source:string",
            "translation_source:string", "translation_model:string",
            "url:string", "page_ref:string", "arabic_sha256:string",
            "review_state:string", "quality_excluded:boolean",
            "quality_exclusion_reason:string", ":LABEL",
        ],
    },
    "nodes/citations.csv": {
        "entity": "Citation",
        "namespace": "Citation-ID",
        "header": [
            "import_id:ID(Citation-ID)", "id:string", "locator:string",
            "source_id:string", "url:string", "review_state:string",
            "provenance:string",
            ":LABEL",
        ],
    },
    "nodes/biographies.csv": {
        "entity": "Biography",
        "namespace": "Biography-ID",
        "header": [
            "import_id:ID(Biography-ID)", "id:string", "subject_id:string",
            "scholar_indx:int", "profile_kind:string", "source_id:string",
            "source_locator:string", "citation_id:string",
            "review_state:string", "provenance:string",
            "raw_profile_sha256:string",
            *[f"{column}:string" for column in RAWI_PROFILE_COLUMNS],
            ":LABEL",
        ],
    },
    "nodes/places.csv": {
        "entity": "Place",
        "namespace": "Place-ID",
        "header": [
            "import_id:ID(Place-ID)", "id:string", "name:string",
            "source_id:string", "citation_id:string", "review_state:string",
            "provenance:string", ":LABEL",
        ],
    },
    "nodes/events.csv": {
        "entity": "Event",
        "namespace": "Event-ID",
        "header": [
            "import_id:ID(Event-ID)", "id:string", "name:string",
            "source_id:string", "citation_id:string", "review_state:string",
            "provenance:string", ":LABEL",
        ],
    },
}


def _rel(
    edge_type: str,
    start_namespace: str,
    end_namespace: str,
    properties: Iterable[str] = (),
) -> dict:
    return {
        "type": edge_type,
        "start_namespace": start_namespace,
        "end_namespace": end_namespace,
        "header": [
            f":START_ID({start_namespace})",
            f":END_ID({end_namespace})",
            *properties,
            ":TYPE",
        ],
    }


RELATIONSHIP_FILES = {
    "relationships/hadith_in_collection.csv": _rel(
        "HADITH_IN_COLLECTION", "Hadith-ID", "Collection-ID",
        ("provenance:string",),
    ),
    "relationships/hadith_in_chapter.csv": _rel(
        "HADITH_IN_CHAPTER", "Hadith-ID", "Chapter-ID",
        ("provenance:string",),
    ),
    "relationships/hadith_in_book.csv": _rel(
        "HADITH_IN_BOOK", "Hadith-ID", "Book-ID", ("provenance:string",),
    ),
    "relationships/chapter_in_book.csv": _rel(
        "CHAPTER_IN_BOOK", "Chapter-ID", "Book-ID", ("provenance:string",),
    ),
    "relationships/book_in_collection.csv": _rel(
        "BOOK_IN_COLLECTION", "Book-ID", "Collection-ID",
        ("provenance:string",),
    ),
    "relationships/collection_in_tradition.csv": _rel(
        "COLLECTION_IN_TRADITION", "Collection-ID", "Tradition-ID",
        ("provenance:string",),
    ),
    "relationships/collection_from_source.csv": _rel(
        "COLLECTION_FROM_SOURCE", "Collection-ID", "Source-ID",
        ("provenance:string",),
    ),
    "relationships/hadith_in_tradition.csv": _rel(
        "HADITH_IN_TRADITION", "Hadith-ID", "Tradition-ID",
        ("provenance:string",),
    ),
    "relationships/hadith_from_source.csv": _rel(
        "HADITH_FROM_SOURCE", "Hadith-ID", "Source-ID",
        ("provenance:string",),
    ),
    "relationships/narrator_from_source.csv": _rel(
        "NARRATOR_FROM_SOURCE", "Narrator-ID", "Source-ID",
        ("provenance:string",),
    ),
    "relationships/has_chain.csv": _rel(
        "HAS_CHAIN", "Hadith-ID", "Chain-ID",
        (
            "branch:int", "source_record_id:string", "extraction_method:string",
            "sanad_confidence:string", "provenance:string",
        ),
    ),
    "relationships/includes.csv": _rel(
        "INCLUDES", "Chain-ID", "Narrator-ID",
        (
            "position:int", "branch:int", "source_record_id:string",
            "extraction_method:string",
            "sanad_confidence:string", "provenance:string",
        ),
    ),
    "relationships/includes_mention.csv": _rel(
        "INCLUDES_MENTION", "Chain-ID", "NameMention-ID",
        (
            "position:int", "branch:int", "source_record_id:string",
            "extraction_method:string",
            "sanad_confidence:string", "provenance:string",
        ),
    ),
    "relationships/next_in_chain.csv": _rel(
        "NEXT_IN_CHAIN", "NameMention-ID", "NameMention-ID",
        (
            "chain_id:string", "hadith_id:string", "from_position:int",
            "to_position:int", "source_record_id:string",
            "extraction_method:string",
            "sanad_confidence:string", "provenance:string",
        ),
    ),
    "relationships/resolves_to.csv": _rel(
        "RESOLVES_TO", "NameMention-ID", "Narrator-ID",
        (
            "chain_id:string", "hadith_id:string", "position:int",
            "source_record_id:string", "extraction_method:string",
            "sanad_confidence:string",
            "provenance:string",
        ),
    ),
    "relationships/narrated_from.csv": _rel(
        "NARRATED_FROM", "Narrator-ID", "Narrator-ID",
        (
            "chain_id:string", "hadith_id:string", "from_position:int",
            "to_position:int", "source_record_id:string",
            "extraction_method:string",
            "sanad_confidence:string", "provenance:string",
        ),
    ),
    "relationships/attributed_to.csv": _rel(
        "ATTRIBUTED_TO", "Hadith-ID", "Alias-ID", ("provenance:string",),
    ),
    "relationships/alias_of.csv": _rel(
        "ALIAS_OF", "Alias-ID", "Narrator-ID", ("provenance:string",),
    ),
    "relationships/translation_of.csv": _rel(
        "TRANSLATION_OF", "Translation-ID", "Hadith-ID",
        ("provenance:string",),
    ),
    "relationships/translation_supported_by.csv": _rel(
        "TRANSLATION_SUPPORTED_BY", "Translation-ID", "Evidence-ID",
        ("provenance:string",),
    ),
    "relationships/report_supported_by.csv": _rel(
        "REPORT_SUPPORTED_BY", "Hadith-ID", "Evidence-ID",
        ("provenance:string",),
    ),
    "relationships/evidence_from_source.csv": _rel(
        "EVIDENCE_FROM_SOURCE", "Evidence-ID", "Source-ID",
        ("provenance:string",),
    ),
    "relationships/cites.csv": _rel(
        "CITES", "Hadith-ID", "Citation-ID", ("provenance:string",),
    ),
    "relationships/supported_by.csv": _rel(
        "SUPPORTED_BY", "Citation-ID", "Evidence-ID",
        ("provenance:string",),
    ),
    "relationships/biography_of.csv": _rel(
        "BIOGRAPHY_OF", "Biography-ID", "Narrator-ID",
        ("review_state:string", "provenance:string"),
    ),
    "relationships/biography_from_source.csv": _rel(
        "BIOGRAPHY_FROM_SOURCE", "Biography-ID", "Source-ID",
        ("review_state:string", "provenance:string"),
    ),
    "relationships/student_of.csv": _rel(
        "STUDENT_OF", "Narrator-ID", "Narrator-ID",
        (
            "evidence_fields:string", "evidence_count:int",
            "reciprocal:boolean", "review_state:string",
            "provenance:string",
        ),
    ),
}

TEXT_MULTILINE_FILES = (
    "nodes/hadiths.csv",
    "nodes/translations.csv",
    "nodes/biographies.csv",
)

_ID_NAMESPACE_RE = re.compile(r":ID\(([^)]+)\)")
_START_NAMESPACE_RE = re.compile(r":START_ID\(([^)]+)\)")
_END_NAMESPACE_RE = re.compile(r":END_ID\(([^)]+)\)")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(*parts: str, length: int = 24) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return sha256_text(payload)[:length]


def tradition_id(name: str) -> str:
    return f"tradition:{name.strip().lower()}"


def typed_column_name(header: str) -> str:
    if header.startswith(":"):
        return header
    return header.split(":", 1)[0]


def id_namespace(header: str) -> str | None:
    match = _ID_NAMESPACE_RE.search(header)
    return match.group(1) if match else None


def start_namespace(header: str) -> str | None:
    match = _START_NAMESPACE_RE.search(header)
    return match.group(1) if match else None


def end_namespace(header: str) -> str | None:
    match = _END_NAMESPACE_RE.search(header)
    return match.group(1) if match else None


def deterministic_json_bytes(value: object) -> bytes:
    rendered = json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2
    )
    return (rendered + "\n").encode("utf-8")


def graph_content_hash(files: list[dict], support_files: list[dict]) -> str:
    bound = [
        {
            "path": item["path"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
            **(
                {
                    "header": item["header"],
                    "row_count": item["row_count"],
                }
                if "header" in item
                else {}
            ),
        }
        for item in sorted(
            [*files, *support_files], key=lambda entry: entry["path"]
        )
    ]
    return sha256_text(
        json.dumps(bound, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
