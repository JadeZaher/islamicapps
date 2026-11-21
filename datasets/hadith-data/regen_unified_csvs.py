#!/usr/bin/env python3
"""
regen_unified_csvs.py
=====================
Regenerates the unified hadith CSVs from source data:
  - all_hadiths_clean.csv  (Sunni + Ibadi + Zaydi when translated)
  - all_hadiths_shia.csv   (Imami 12er + Ibadi + Zaydi when translated)

Sources:
  - Sunni K6:       Kutub al-Sittah from sunnah.com (pre-built CSV)
  - Sunni Classical:pure_canon.jsonl — Ahmad / Darimi / Shafi'i / Muwatta
  - Imami:          Thaqalayn API JSON files (via shia-hadith/build_csv.py)
  - Ibadi:          OpenITI parse (ibadi-hadith/parsed_hadiths.json)
  - Zaydi:          OpenITI parse (zaydi-hadith/parsed_hadiths.json)
  - Rida:           OpenITI parse (rida-hadith/parsed_hadiths.json)

Usage:
    python regen_unified_csvs.py              # Full rebuild
    python regen_unified_csvs.py --no-shia    # Skip Thaqalayn rebuild (use existing)
    python regen_unified_csvs.py --include-zaydi  # Force-include Zaydi (even without translations)
    python regen_unified_csvs.py --no-classical   # Skip classical Sunni ingestion
"""

import argparse
from contextlib import contextmanager
import csv
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from urllib.parse import urlsplit

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
csv.field_size_limit(10 * 1024 * 1024)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IBADI_DIR = os.path.join(BASE_DIR, 'ibadi-hadith')
ZAYDI_DIR = os.path.join(BASE_DIR, 'zaydi-hadith')
RIDA_DIR = os.path.join(BASE_DIR, 'rida-hadith')
SHIA_DIR = os.path.join(BASE_DIR, 'shia-hadith')

# classify_attribution.py lives one directory up (datasets/).
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))
from classify_attribution import classify as classify_attribution  # noqa: E402
from extract_isnad_unified import (  # noqa: E402
    IsnadExtractionLimitError,
    UnresolvedNarratorError,
    _compute_chain_indx,
    extract_isnad_branches,
)

SUNNI_ISNAD_SIDECAR = os.path.join(BASE_DIR, 'sunni_isnad.jsonl')

# ─── Classical Sunni (pure_canon.jsonl) ────────────────────────────────────
# Canonical path (archive). The tooling note says to pick the canonical
# classical file; pure_canon.jsonl is the definitive one.
PURE_CANON_JSONL = os.path.join(
    BASE_DIR, 'archive', 'sheikahmad-pure-canon', 'pure_canon.jsonl')
CLASSICAL_TRANSLATIONS_CSV = os.path.join(
    BASE_DIR, 'archive', 'classical-pipeline', 'classical_canon_enhanced.csv')
CLASSICAL_TRANSLATIONS_CLEAN_JSONL = os.path.join(
    BASE_DIR, 'archive', 'classical-pipeline', 'classical_translations_clean.jsonl')
TRANSLATION_OVERRIDES_JSONL = os.path.join(
    BASE_DIR, 'translation_overrides.jsonl')
CURATION_DISPOSITIONS_JSONL = os.path.join(
    BASE_DIR, 'curation_dispositions.jsonl')
SOURCE_REGISTRY_TS = os.path.join(
    os.path.dirname(os.path.dirname(BASE_DIR)), 'src', 'lib', 'constants',
    'sources.ts')
IMAMI_SOURCE_WORK_REGISTRY_JSON = os.path.join(
    BASE_DIR, 'imami_source_work_registry.json')
EVIDENCE_CURATION_MANIFEST_JSON = os.path.join(
    BASE_DIR, 'evidence_curation_manifest.json')
EVIDENCE_CURATION_SCHEMA_JSON = os.path.join(
    BASE_DIR, 'evidence_curation.schema.json')
EVIDENCE_CURATION_BUNDLE_JSON = os.path.join(
    BASE_DIR, 'evidence_curation.json')
UNIFIED_ISNAD_EXTRACTOR = os.path.join(
    BASE_DIR, 'extract_isnad_unified.py')
UNIFIED_ISNAD_HELPERS = os.path.join(
    BASE_DIR, 'algo_candidates', '_common.py')

SUPPORTED_TRADITIONS = {'Sunni', 'Imami', 'Ibadi', 'Zaydi'}
PUBLISHABLE_TRANSLATION_REVIEW_STATES = {
    'human_verified',
    'source_verified',
}
PUBLISHABLE_EVIDENCE_REVIEW_STATES = frozenset({
    'human_verified',
    'source_verified',
})
_MODEL_PROVENANCE_MARKER = re.compile(
    r'(?:^|[^a-z0-9])(?:ai|automated|generated|gpt|llm|machine|model|'
    r'openai|anthropic|claude|gemma|pipeline)(?=$|[^a-z0-9])',
    re.IGNORECASE,
)
PLACEHOLDER_METADATA_TOKENS = {
    '', '<missing>', '-', '?', 'n/a', 'na', 'none', 'null', 'pending',
    'tba', 'tbd', 'unknown', 'unspecified',
}
_SPECIFIC_MODEL_IDENTIFIER = re.compile(
    r'^[a-z0-9][a-z0-9._-]*(?:[/:][a-z0-9][a-z0-9._-]*)+$',
    re.IGNORECASE,
)
GENERIC_MODEL_COMPONENTS = {'ai', 'default', 'generic', 'model', 'x'}

# Arabic source name → canonical DB name (from src/lib/constants/sources.ts).
# Only the four classical collections tracked by FR-0.9 are listed; the rest
# (Albani, Tlidhi, etc.) are NOT ingested here.
CLASSICAL_SOURCE_MAP = {
    'مسند حنبل': 'Musnad Ahmad',
    'سنن الدارمي': 'Sunan al-Darimi',
    'شافعي': "Musnad al-Shafi'i",
    'موطأ مالك': "Muwatta' Malik",
}

# Shafi'i is matn-only by source (FR-0.9 allow-list isnad_optional).
ISNAD_OPTIONAL_SOURCES = {"Musnad al-Shafi'i"}

# Narrator gap output path (handoff to narrator_enrichment_20260425 track).
CLASSICAL_NARRATOR_GAP_CSV = os.path.join(BASE_DIR, 'classical_narrator_gap.csv')

# Narrator data (read-only reference).
ALL_RAWIS_CSV = os.path.join(
    os.path.dirname(BASE_DIR), 'narrator-data', 'all_rawis.csv')

# Single master schema (superset of every tradition's fields, plus the
# attribution + sanad-confidence enrichment). all_hadiths_unified.csv is the
# one source of truth; the two views below are projections of it.
UNIFIED_COLS = [
    "id", "hadith_id", "provider_file_id", "provider_book_id",
    "source", "source_work_id", "source_display_label", "tradition", "volume", "chapter_no",
    "hadith_no", "chapter", "category", "chain_indx", "text_ar", "text_en",
    "sanad", "sanad_confidence", "matn_ar", "matn_en", "school", "chain_type",
    "attributed_to", "narration_level",
    "grade_tradition", "grade_source", "grade_value",
    "gradings_full", "url", "page_ref",
    "record_id", "source_record_id", "provenance_source",
    "translation_status", "translation_source", "translation_model",
    "translation_review_status",
]

# Derived views (column projections of the master, for backward compat).
CLEAN_COLS = [
    "id", "hadith_id", "source", "tradition", "chapter_no", "hadith_no",
    "chapter", "chain_indx", "text_ar", "text_en",
    "sanad", "school", "chain_type", "attributed_to", "narration_level",
    "record_id", "source_record_id", "provenance_source",
    "translation_status", "translation_source", "translation_model",
    "translation_review_status",
]

SHIA_COLS = [
    "id", "hadith_id", "provider_file_id", "provider_book_id",
    "source", "source_work_id", "source_display_label", "tradition", "volume", "chapter_no",
    "hadith_no", "chapter", "category", "chain_indx", "text_ar", "text_en",
    "sanad", "matn_ar", "matn_en", "school", "chain_type",
    "attributed_to", "narration_level",
    "grade_tradition", "grade_source", "grade_value",
    "gradings_full", "url", "page_ref",
    "record_id", "source_record_id", "provenance_source",
    "translation_status", "translation_source", "translation_model",
    "translation_review_status",
]


def _stable_token(value: str) -> str:
    """Return a compact deterministic token for a source-owned identifier."""
    return hashlib.sha256((value or '').encode('utf-8')).hexdigest()[:24]


def thaqalayn_source_record_id(row: dict) -> str:
    """Return provider-owned coordinates without using a display book label."""
    upstream_hadith_id = str(row.get('hadith_id') or '').strip()
    provider_file_id = str(row.get('provider_file_id') or '').strip()
    provider_book_id = str(
        row.get('provider_book_id') or row.get('book_id')
        or row.get('bookId') or ''
    ).strip()

    # Numeric v2_books filenames are the strongest provider-owned book key.
    if re.fullmatch(r'\d+', provider_file_id) and upstream_hadith_id:
        return (
            f'provider-file:{provider_file_id}|hadith:{upstream_hadith_id}'
        )
    if provider_book_id and upstream_hadith_id:
        return (
            f'provider-book:{provider_book_id}|hadith:{upstream_hadith_id}'
        )

    # Compatibility for legacy projections that predate provider columns.
    raw_url = (row.get('url') or row.get('URL') or '').strip()
    volume = str(row.get('volume') or '').strip()
    if raw_url:
        path = re.sub(r'/+', '/', urlsplit(raw_url).path).rstrip('/')
        if path and volume and upstream_hadith_id:
            return (
                f'url-path:{path}|volume:{volume}|hadith:{upstream_hadith_id}'
            )
    raise ValueError(
        'Thaqalayn row lacks a complete provider file/book + hadith ID or '
        'legacy URL path + volume + hadith ID coordinate'
    )


def apply_thaqalayn_identity(row: dict) -> dict:
    """Attach a durable Thaqalayn key while leaving display metadata mutable."""
    source_record_id = thaqalayn_source_record_id(row)
    row['source_record_id'] = source_record_id
    row['record_id'] = f"thaqalayn:{_stable_token(source_record_id)}"
    return row


def apply_thaqalayn_identities(rows: list) -> list:
    """Attach identities and reject any duplicate across the full corpus."""
    identified = []
    seen = {}
    for position, original in enumerate(rows, start=1):
        row = apply_thaqalayn_identity(dict(original))
        source_record_id = row['source_record_id']
        if source_record_id in seen:
            raise ValueError(
                'Duplicate Thaqalayn source_record_id across full corpus: '
                f'{source_record_id!r} at rows {seen[source_record_id]:,} '
                f'and {position:,}'
            )
        seen[source_record_id] = position
        identified.append(row)
    if len(seen) != len(identified):
        raise ValueError('Thaqalayn identity preflight did not produce unique IDs')
    return identified


def _text_sha256(value: str) -> str:
    """Bind curated content to the exact normalized source text."""
    return hashlib.sha256((value or '').strip().encode('utf-8')).hexdigest()


def _translation_status(text_en: str) -> str:
    """Classify only structural completeness; strict QA runs in curation."""
    return 'complete' if (text_en or '').strip() else 'missing'


_LATIN_TEXT = re.compile(r'[A-Za-z]')
_ARABIC_TEXT = re.compile(
    r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]'
)
_INLINE_TRANSLATION_PLACEHOLDER = re.compile(
    r'(?<![A-Za-z])(?:TODO|PLACEHOLDER)(?![A-Za-z])', re.IGNORECASE
)
_TRANSLATION_FAILURE = re.compile(
    r"^\s*(?:translation\s+(?:failed|unavailable|missing)|"
    r"unable\s+to\s+translate|i\s+(?:cannot|can't|am unable\s+to)\s+translate|"
    r"i(?:'m| am)\s+sorry|as\s+an\s+ai\b|sorry[, :]\s*i\s+(?:cannot|can't))",
    re.IGNORECASE,
)


def translation_issue(text_en: str, text_ar: str = '') -> str:
    """Return a release-blocking translation issue or an empty string."""
    text = (text_en or '').strip()
    source_text = (text_ar or '').strip()
    if not text:
        return 'missing'
    if _TRANSLATION_FAILURE.search(text):
        return 'model_refusal_or_error'
    if (_INLINE_TRANSLATION_PLACEHOLDER.search(text)
            or re.fullmatch(r'(?:H\d+|(?:\d+[.)]?\s*)?TBA|N/?A|NONE)', text,
                            re.IGNORECASE)):
        return 'placeholder'
    if source_text and (
            text == source_text
            or _normalized_source_text(text) == _normalized_source_text(source_text)):
        return 'same_as_arabic'
    if _ARABIC_TEXT.search(text):
        return 'arabic_leakage'
    if not _LATIN_TEXT.search(text) or not _has_latin_letter_majority(text):
        return 'wrong_language'
    if len(text) < 8 and len(source_text) > 80:
        return 'suspiciously_short'
    return ''


def _normalized_source_text(value: str) -> str:
    """Normalize source content only enough to detect copied input."""
    return re.sub(
        r'[^\w]+', '', unicodedata.normalize('NFKC', value or '')
    ).casefold()


def _has_latin_letter_majority(value: str) -> bool:
    """Require at least 80 percent of output letters to be Latin script."""
    letters = [character for character in value if character.isalpha()]
    if not letters:
        return False
    latin = sum(
        'LATIN' in unicodedata.name(character, '') for character in letters
    )
    return latin / len(letters) >= 0.80


def normalized_metadata_token(value) -> str:
    text = '' if value is None else str(value)
    return re.sub(r'\s+', '', text.strip().lower())


def is_placeholder_metadata(value) -> bool:
    return normalized_metadata_token(value) in PLACEHOLDER_METADATA_TOKENS


def is_meaningful_source_record_id(value) -> bool:
    text = '' if value is None else str(value)
    return not is_placeholder_metadata(text) and any(
        character.isalnum() for character in text
    )


def is_meaningful_provenance_locator(value) -> bool:
    text = '' if value is None else str(value)
    if is_placeholder_metadata(text):
        return False
    return sum(character.isalnum() for character in text) >= 2


def is_specific_translation_model_identifier(value) -> bool:
    identifier = ('' if value is None else str(value)).strip()
    if (is_placeholder_metadata(identifier)
            or not _SPECIFIC_MODEL_IDENTIFIER.fullmatch(identifier)):
        return False
    terminal = re.split(r'[/:]', identifier)[-1].lower()
    return len(terminal) >= 3 and terminal not in GENERIC_MODEL_COMPONENTS


def translation_model_required(translation_source, review_status) -> bool:
    return bool(_MODEL_PROVENANCE_MARKER.search(
        f'{translation_source or ""} {review_status or ""}'
    ))


def write_translation_backlog(rows: list, path: str):
    """Write deterministic curation work without publishing an invalid master."""
    cols = [
        'record_id', 'source_record_id', 'source', 'tradition', 'hadith_no',
        'issue', 'text_ar', 'current_text_en', 'provenance_source',
    ]
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)
    print(f"  Written: {path} ({len(rows):,} release blockers)")


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_csv_input_path(csv_path: str) -> str:
    """Resolve a checked-in CSV from either its plain or gzip representation."""
    plain_path = csv_path[:-3] if csv_path.endswith('.gz') else csv_path
    gzip_path = plain_path + '.gz'
    plain_exists = os.path.isfile(plain_path)
    gzip_exists = os.path.isfile(gzip_path)
    if plain_exists and gzip_exists:
        plain_hash = _sha256_file(plain_path)
        gzip_hash = _sha256_gzip_logical(gzip_path)
        if plain_hash != gzip_hash:
            raise ValueError(
                f'CSV/GZIP logical content diverges: {plain_path}, {gzip_path}'
            )
        return gzip_path if csv_path.endswith('.gz') else plain_path
    if plain_exists:
        return plain_path
    if gzip_exists:
        return gzip_path
    raise FileNotFoundError(
        f"CSV input not found as plain or gzip: {csv_path}"
    )


def resolve_no_shia_input(default_plain_path: str,
                          explicit_path: str = None) -> str:
    """Select one exact reuse asset without weakening paired-input checks."""
    if explicit_path:
        selected = os.path.abspath(explicit_path)
        if not os.path.isfile(selected):
            raise FileNotFoundError(
                f"Explicit --shia-input does not exist: {selected}"
            )
        return selected

    tracked_gzip = os.path.abspath(
        default_plain_path
        if default_plain_path.endswith('.gz')
        else default_plain_path + '.gz'
    )
    if os.path.isfile(tracked_gzip):
        return tracked_gzip
    return resolve_csv_input_path(default_plain_path)


def _open_resolved_csv_input(resolved_path: str):
    """Open one already-selected CSV asset exactly as named."""
    if resolved_path.endswith('.gz'):
        return gzip.open(resolved_path, 'rt', encoding='utf-8',
                         errors='replace', newline='')
    return open(resolved_path, 'r', encoding='utf-8', errors='replace',
                newline='')


def open_csv_input(csv_path: str):
    """Open a CSV text stream without expanding a gzip asset onto disk."""
    resolved = resolve_csv_input_path(csv_path)
    return _open_resolved_csv_input(resolved)


_SOURCE_REGISTRY_ENTRY = re.compile(
    r"\bcanonical\s*:\s*(?:'(?P<single>(?:\\.|[^'\\])*)'|"
    r'"(?P<double>(?:\\.|[^"\\])*)")[^}]*?'
    r"\btradition\s*:\s*['\"](?P<tradition>Sunni|Imami|Zaydi|Ibadi)['\"]",
    re.DOTALL,
)


def load_source_work_registry(path: str = SOURCE_REGISTRY_TS) -> dict:
    """Read the canonical source-work/tradition contract used by the loader."""
    with open(path, encoding='utf-8') as f:
        source = f.read()
    registry = {}
    for match in _SOURCE_REGISTRY_ENTRY.finditer(source):
        raw_name = match.group('single') or match.group('double') or ''
        name = re.sub(r"\\(['\"\\])", r"\1", raw_name)
        tradition = match.group('tradition')
        previous = registry.get(name)
        if previous and previous != tradition:
            raise ValueError(
                f"Conflicting source registry traditions for {name}: "
                f"{previous}, {tradition}"
            )
        registry[name] = tradition
    if not registry:
        raise ValueError(f'No canonical source entries parsed from {path}')
    return registry


def load_imami_source_work_registry(
        path: str = IMAMI_SOURCE_WORK_REGISTRY_JSON,
        source_registry: dict = None) -> dict:
    """Load provider-book-backed Imami work identities without label guessing."""
    with open(path, encoding='utf-8') as f:
        payload = json.load(f)
    if payload.get('schema_version') != 1:
        raise ValueError('Unsupported Imami source-work registry schema')
    if source_registry is None:
        source_registry = load_source_work_registry()

    by_provider_book_id = {}
    by_source_work_id = {}
    provider_entries = payload.get('source_works') or []
    non_provider_entries = payload.get('non_provider_source_works') or []
    if not isinstance(provider_entries, list) or not isinstance(
            non_provider_entries, list):
        raise ValueError('Invalid Imami source-work registry lists')
    for entry in provider_entries + non_provider_entries:
        source_work_id = str(entry.get('source_work_id') or '').strip()
        canonical_source = str(entry.get('canonical_source') or '').strip()
        compiler = str(entry.get('compiler') or '').strip()
        provider_book_ids = entry.get('provider_book_ids')
        if (not re.fullmatch(r'imami:[a-z0-9][a-z0-9-]*', source_work_id)
                or not canonical_source or not compiler
                or (entry in provider_entries and (
                    not isinstance(provider_book_ids, list)
                    or not provider_book_ids))
                or (entry in non_provider_entries and provider_book_ids)):
            raise ValueError(
                'Invalid Imami source-work registry entry: '
                f'{entry!r}'
            )
        if source_registry.get(canonical_source) != 'Imami':
            raise ValueError(
                'Imami source-work registry canonical source is absent or '
                f'not Imami: {canonical_source!r}'
            )
        if source_work_id in by_source_work_id:
            raise ValueError(
                f'Duplicate Imami source_work_id: {source_work_id!r}'
            )
        normalized = {
            'source_work_id': source_work_id,
            'canonical_source': canonical_source,
            'compiler': compiler,
        }
        by_source_work_id[source_work_id] = normalized
        for raw_provider_book_id in provider_book_ids or []:
            provider_book_id = str(raw_provider_book_id or '').strip()
            if not provider_book_id:
                raise ValueError(
                    'Blank provider_book_id in Imami source-work registry: '
                    f'{source_work_id!r}'
                )
            if provider_book_id in by_provider_book_id:
                raise ValueError(
                    'Provider book ID maps to multiple Imami works: '
                    f'{provider_book_id!r}'
                )
            by_provider_book_id[provider_book_id] = normalized
    if not by_provider_book_id:
        raise ValueError('No provider book IDs in Imami source-work registry')
    return {
        'by_provider_book_id': by_provider_book_id,
        'by_source_work_id': by_source_work_id,
    }


def reconcile_imami_source_work(row: dict, registry: dict = None) -> dict:
    """Resolve one Thaqalayn row by immutable provider book ID, never label."""
    if registry is None:
        registry = load_imami_source_work_registry()
    provider_book_id = str(
        row.get('provider_book_id') or row.get('book_id')
        or row.get('bookId') or ''
    ).strip()
    if not provider_book_id:
        raise ValueError(
            'Imami source-work reconciliation requires provider_book_id; '
            'legacy display labels cannot distinguish Al-Amali or Kitab al-Ghayba'
        )
    entry = registry['by_provider_book_id'].get(provider_book_id)
    if entry is None:
        raise ValueError(
            'Unregistered Thaqalayn provider_book_id for Imami source-work '
            f'reconciliation: {provider_book_id!r}'
        )
    reconciled = dict(row)
    reconciled['source_display_label'] = (row.get('source') or '').strip()
    reconciled['source'] = entry['canonical_source']
    reconciled['source_work_id'] = entry['source_work_id']
    return reconciled


def reconcile_imami_source_works(rows: list, registry: dict = None) -> list:
    """Reconcile a bounded in-memory Imami build after provider identity checks."""
    if registry is None:
        registry = load_imami_source_work_registry()
    return [reconcile_imami_source_work(row, registry) for row in rows]


def _json_schema_type_matches(value, expected) -> bool:
    """Match the JSON types used by the checked-in evidence schema."""
    if expected == 'null':
        return value is None
    if expected == 'object':
        return isinstance(value, dict)
    if expected == 'array':
        return isinstance(value, list)
    if expected == 'string':
        return isinstance(value, str)
    if expected == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == 'boolean':
        return isinstance(value, bool)
    return False


def _resolve_local_schema_ref(root_schema: dict, reference: str) -> dict:
    if not reference.startswith('#/'):
        raise ValueError(f'Only local evidence schema references are allowed: {reference}')
    node = root_schema
    for raw_token in reference[2:].split('/'):
        token = raw_token.replace('~1', '/').replace('~0', '~')
        node = node[token]
    if not isinstance(node, dict):
        raise ValueError(f'Evidence schema reference is not an object: {reference}')
    return node


MAX_EVIDENCE_SCHEMA_ERRORS = 1000


def _append_schema_error(errors: list, message: str):
    if len(errors) < MAX_EVIDENCE_SCHEMA_ERRORS:
        errors.append(message)


def _extend_schema_errors(errors: list, additional: list):
    remaining = MAX_EVIDENCE_SCHEMA_ERRORS - len(errors)
    if remaining > 0:
        errors.extend(additional[:remaining])


def _json_schema_errors(value, rule: dict, root_schema: dict,
                        location: str = '$') -> list[str]:
    """Validate the bounded Draft 2020-12 subset used by the evidence schema."""
    if '$ref' in rule:
        try:
            target = _resolve_local_schema_ref(root_schema, rule['$ref'])
        except (KeyError, TypeError, ValueError) as error:
            return [f'{location}: invalid schema reference ({error})']
        return _json_schema_errors(value, target, root_schema, location)
    if 'anyOf' in rule:
        alternatives = rule['anyOf']
        if not isinstance(alternatives, list) or not alternatives:
            return [f'{location}: invalid anyOf schema']
        if any(not _json_schema_errors(value, choice, root_schema, location)
               for choice in alternatives if isinstance(choice, dict)):
            return []
        return [f'{location}: does not match any allowed schema']

    errors = []
    if 'const' in rule and value != rule['const']:
        _append_schema_error(
            errors, f'{location}: expected constant {rule["const"]!r}'
        )
    if 'enum' in rule and value not in rule['enum']:
        _append_schema_error(
            errors, f'{location}: value is not in the allowed enum'
        )

    expected_types = rule.get('type')
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if (not isinstance(expected_types, list)
                or not any(_json_schema_type_matches(value, expected)
                           for expected in expected_types)):
            return [f'{location}: invalid JSON type']

    if isinstance(value, dict):
        required = rule.get('required', [])
        if not isinstance(required, list):
            _append_schema_error(errors, f'{location}: invalid required schema')
        else:
            for key in required:
                if key not in value:
                    _append_schema_error(
                        errors, f'{location}: missing required property {key!r}'
                    )
        properties = rule.get('properties', {})
        if isinstance(properties, dict):
            for key, child_rule in properties.items():
                if key in value and isinstance(child_rule, dict):
                    _extend_schema_errors(errors, _json_schema_errors(
                        value[key], child_rule, root_schema, f'{location}.{key}'
                    ))
                if len(errors) >= MAX_EVIDENCE_SCHEMA_ERRORS:
                    break
        if rule.get('additionalProperties') is False and isinstance(properties, dict):
            for key in value.keys() - properties.keys():
                _append_schema_error(
                    errors, f'{location}: unexpected property {key!r}'
                )
                if len(errors) >= MAX_EVIDENCE_SCHEMA_ERRORS:
                    break
    elif isinstance(value, list):
        item_rule = rule.get('items')
        if isinstance(item_rule, dict):
            for index, item in enumerate(value):
                _extend_schema_errors(errors, _json_schema_errors(
                    item, item_rule, root_schema, f'{location}[{index}]'
                ))
                if len(errors) >= MAX_EVIDENCE_SCHEMA_ERRORS:
                    break
    elif isinstance(value, str):
        minimum = rule.get('minLength')
        if isinstance(minimum, int) and len(value) < minimum:
            _append_schema_error(
                errors, f'{location}: string is shorter than {minimum}'
            )
        pattern = rule.get('pattern')
        if isinstance(pattern, str):
            try:
                if re.search(pattern, value) is None:
                    _append_schema_error(
                        errors,
                        f'{location}: string does not match required pattern',
                    )
            except re.error:
                _append_schema_error(
                    errors, f'{location}: invalid schema pattern'
                )
        if rule.get('format') == 'uri':
            try:
                if not urlsplit(value).scheme:
                    _append_schema_error(errors, f'{location}: invalid URI')
            except ValueError:
                _append_schema_error(errors, f'{location}: invalid URI')
        elif rule.get('format') == 'date-time':
            try:
                parsed = datetime.datetime.fromisoformat(
                    value.replace('Z', '+00:00')
                )
                if parsed.utcoffset() is None:
                    raise ValueError('timezone required')
            except ValueError:
                _append_schema_error(errors, f'{location}: invalid date-time')
    return errors


def _load_bounded_json(path: str, maximum_bytes: int = 16 * 1024 * 1024):
    if os.path.getsize(path) > maximum_bytes:
        raise ValueError(f'JSON asset exceeds {maximum_bytes} bytes: {path}')
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def evidence_curation_gate(
        manifest_path: str = EVIDENCE_CURATION_MANIFEST_JSON,
        bundle_path: str = EVIDENCE_CURATION_BUNDLE_JSON,
        schema_path: str = EVIDENCE_CURATION_SCHEMA_JSON) -> dict:
    """Validate real, citation-bound reviewed claims before graph publication."""
    counts = {
        'manifest_missing_or_invalid': 0,
        'schema_missing_or_invalid': 0,
        'bundle_missing_or_invalid': 0,
        'schema_validation_errors': 0,
        'not_ready_for_graph_publication': 0,
        'manifest_count_mismatches': 0,
        'missing_citations': 0,
        'missing_biographical_assertions': 0,
        'missing_source_author_assertions': 0,
        'missing_historical_event_assertions': 0,
        'missing_epoch_assertions': 0,
        'duplicate_citation_ids': 0,
        'duplicate_assertion_ids': 0,
        'broken_citation_references': 0,
        'broken_supersedes_references': 0,
        'uncited_claims': 0,
        'unreviewed_claims': 0,
    }
    try:
        manifest = _load_bounded_json(manifest_path)
        if not isinstance(manifest, dict):
            raise ValueError('evidence manifest must be an object')
        raw_counts = manifest.get('counts')
        if (manifest.get('schema_version') != 1
                or not isinstance(raw_counts, dict)):
            raise ValueError('invalid evidence manifest')
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        counts['manifest_missing_or_invalid'] = 1
        return {'passed': False, 'counts': counts}
    try:
        schema = _load_bounded_json(schema_path)
        if not isinstance(schema, dict) or not isinstance(schema.get('$defs'), dict):
            raise ValueError('invalid evidence schema')
        review_states = schema['$defs']['review']['enum']
        if (not isinstance(review_states, list)
                or set(review_states) != PUBLISHABLE_EVIDENCE_REVIEW_STATES):
            raise ValueError('evidence review enum must remain fail-closed')
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        counts['schema_missing_or_invalid'] = 1
        return {'passed': False, 'counts': counts}
    try:
        bundle = _load_bounded_json(bundle_path)
        if not isinstance(bundle, dict):
            raise ValueError('evidence bundle must be an object')
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        counts['bundle_missing_or_invalid'] = 1
        return {'passed': False, 'counts': counts}

    try:
        schema_errors = _json_schema_errors(bundle, schema, schema)
    except (KeyError, TypeError, ValueError, re.error):
        counts['schema_missing_or_invalid'] = 1
        return {'passed': False, 'counts': counts}
    counts['schema_validation_errors'] = len(schema_errors)
    if manifest.get('ready_for_graph_publication') is not True:
        counts['not_ready_for_graph_publication'] = 1

    list_keys = (
        'citations', 'biographical_assertions', 'source_author_assertions',
        'historical_event_assertions', 'epoch_assertions',
    )
    records = {
        key: bundle.get(key) if isinstance(bundle.get(key), list) else []
        for key in list_keys
    }
    missing_keys = {
        'citations': 'missing_citations',
        'biographical_assertions': 'missing_biographical_assertions',
        'source_author_assertions': 'missing_source_author_assertions',
        'historical_event_assertions': 'missing_historical_event_assertions',
        'epoch_assertions': 'missing_epoch_assertions',
    }
    for key, count_key in missing_keys.items():
        if not records[key]:
            counts[count_key] = 1

    citation_ids = [
        item.get('citation_id') for item in records['citations']
        if isinstance(item, dict) and isinstance(item.get('citation_id'), str)
    ]
    unique_citation_ids = set(citation_ids)
    counts['duplicate_citation_ids'] = len(citation_ids) - len(unique_citation_ids)
    claim_keys = list_keys[1:]
    claims = [
        item for key in claim_keys for item in records[key]
        if isinstance(item, dict)
    ]
    assertion_ids = [
        item.get('assertion_id') for item in claims
        if isinstance(item.get('assertion_id'), str)
    ]
    unique_assertion_ids = set(assertion_ids)
    counts['duplicate_assertion_ids'] = len(assertion_ids) - len(unique_assertion_ids)
    counts['broken_citation_references'] = sum(
        1 for claim in claims
        if claim.get('citation_id') not in unique_citation_ids
    )
    counts['broken_supersedes_references'] = sum(
        1 for claim in claims
        if claim.get('supersedes_assertion_id') is not None
        and (claim.get('supersedes_assertion_id') not in unique_assertion_ids
             or claim.get('supersedes_assertion_id') == claim.get('assertion_id'))
    )
    counts['uncited_claims'] = counts['broken_citation_references']
    counts['unreviewed_claims'] = sum(
        1 for claim in claims
        if claim.get('review_status') not in PUBLISHABLE_EVIDENCE_REVIEW_STATES
    )

    actual_counts = {key: len(records[key]) for key in list_keys}
    actual_counts.update({
        'uncited_claims': counts['uncited_claims'],
        'unreviewed_claims': counts['unreviewed_claims'],
    })
    for key, actual in actual_counts.items():
        reported = raw_counts.get(key)
        if (not isinstance(reported, int) or isinstance(reported, bool)
                or reported < 0 or reported != actual):
            counts['manifest_count_mismatches'] += 1

    return {
        'passed': not any(counts.values()),
        'counts': counts,
        'actual_counts': actual_counts,
        'schema_errors': schema_errors[:100],
    }


def load_narrator_ids(path: str = ALL_RAWIS_CSV) -> set:
    """Load the canonical positive scholar IDs used by chain_indx."""
    narrator_ids = set()
    with open(path, encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            token = (row.get('scholar_indx') or '').strip()
            if token.isdigit() and int(token) > 0:
                narrator_ids.add(int(token))
    if not narrator_ids:
        raise ValueError(f'No positive scholar_indx values parsed from {path}')
    return narrator_ids


def new_canonical_chain_stats() -> dict:
    """Create row-level telemetry shared by every canonical ingestion path."""
    return {
        'rows_attempted': 0,
        'rows_resolved': 0,
        'rows_without_extracted_chain': 0,
        'rows_resolution_failed': 0,
        'rows_extraction_failed': 0,
        'rows_empty_arabic': 0,
    }


def canonical_chain_indx(text_ar: str, resolver, stats: dict,
                         on_resolution_failure=None) -> str:
    """Resolve one Arabic row atomically; a failed surface empties the row."""
    if not (text_ar or '').strip():
        stats['rows_empty_arabic'] += 1
        return ''
    stats['rows_attempted'] += 1
    try:
        chain_indx = _compute_chain_indx(
            text_ar=text_ar,
            fallback=None,
            resolve_narrator=resolver,
        )
    except IsnadExtractionLimitError:
        stats['rows_extraction_failed'] += 1
        return ''
    except UnresolvedNarratorError as error:
        stats['rows_resolution_failed'] += 1
        if on_resolution_failure is not None:
            on_resolution_failure(error)
        return ''
    if chain_indx:
        stats['rows_resolved'] += 1
    else:
        stats['rows_without_extracted_chain'] += 1
    return chain_indx


def apply_canonical_chain(row: dict, resolver, stats: dict) -> dict:
    """Overwrite legacy chain IDs from the row's canonical Arabic text."""
    row['chain_indx'] = canonical_chain_indx(
        row.get('text_ar', ''), resolver, stats
    )
    return row


def _chain_references(value) -> list:
    """Parse the loader's comma/pipe chain_indx representation."""
    text = str(value or '').strip()
    if not text:
        return []
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1].strip()
    if not text:
        return []
    references = []
    for branch in text.split('|'):
        tokens = [token.strip() for token in branch.split(',')]
        if not tokens or any(not token for token in tokens):
            raise ValueError(f'Empty chain_indx token: {value}')
        for token in tokens:
            if not token.isdigit() or int(token) <= 0:
                raise ValueError(f'Invalid chain_indx token: {token}')
            references.append(int(token))
    return references


def assess_full_load_gates(master: list, source_registry: dict = None,
                           narrator_ids: set = None) -> dict:
    """Evaluate the same release evidence required before a full graph load."""
    registry_available = True
    narrator_registry_available = True
    imami_source_work_registry_available = True
    if source_registry is None:
        try:
            source_registry = load_source_work_registry()
        except (OSError, ValueError):
            source_registry = {}
            registry_available = False
    if narrator_ids is None:
        try:
            narrator_ids = load_narrator_ids()
        except (OSError, ValueError):
            narrator_ids = set()
            narrator_registry_available = False
    imami_source_work_registry = None
    if any((row.get('tradition') or '').strip() == 'Imami' for row in master):
        try:
            imami_source_work_registry = load_imami_source_work_registry(
                source_registry=source_registry)
        except (OSError, ValueError, TypeError):
            imami_source_work_registry_available = False

    text_counts = {
        'missing_text_ar': 0,
        'translation_content_issues': 0,
        'translation_status_not_complete': 0,
    }
    translation_issue_counts = {}
    review_state_counts = {}
    review_counts = {'not_publication_ready': 0}
    provenance_counts = {
        'missing_record_id': 0,
        'duplicate_record_id': 0,
        'missing_source_record_id': 0,
        'missing_provenance_source': 0,
        'missing_translation_source': 0,
        'missing_translation_review_status': 0,
        'missing_required_translation_model': 0,
    }
    chain_counts = {
        'missing_chain_indx': 0,
        'invalid_chain_indx': 0,
        'unknown_chain_indx_references': 0,
        'narrator_registry_unavailable': int(not narrator_registry_available),
    }
    chain_by_tradition = {}
    source_counts = {
        'missing_source': 0,
        'unsupported_tradition': 0,
        'unsupported_grade_tradition': 0,
        'source_tradition_conflicts': 0,
        'unregistered_source_rows': 0,
        'source_registry_mismatches': 0,
        'source_registry_unavailable': int(not registry_available),
        'imami_source_work_registry_unavailable': int(
            not imami_source_work_registry_available),
        'missing_imami_source_work_id': 0,
        'unknown_imami_source_work_id': 0,
        'imami_source_work_mismatches': 0,
    }

    seen_record_ids = set()
    observed_source_traditions = {}
    unregistered_source_names = set()
    mismatched_source_names = set()
    for row in master:
        tradition = (row.get('tradition') or '').strip() or '<missing>'
        tradition_chain = chain_by_tradition.setdefault(tradition, {
            'rows': 0,
            'present_chain_indx': 0,
            'missing_chain_indx': 0,
            'invalid_chain_indx': 0,
            'unknown_chain_indx_references': 0,
        })
        tradition_chain['rows'] += 1
        text_ar = (row.get('text_ar') or '').strip()
        text_en = (row.get('text_en') or '').strip()
        if not text_ar:
            text_counts['missing_text_ar'] += 1
        issue = translation_issue(text_en, text_ar)
        if issue:
            text_counts['translation_content_issues'] += 1
            translation_issue_counts[issue] = (
                translation_issue_counts.get(issue, 0) + 1
            )
        if (row.get('translation_status') or '').strip() != 'complete':
            text_counts['translation_status_not_complete'] += 1

        review_state = (
            row.get('translation_review_status') or '<missing>'
        ).strip() or '<missing>'
        review_state_counts[review_state] = review_state_counts.get(
            review_state, 0) + 1
        if review_state not in PUBLISHABLE_TRANSLATION_REVIEW_STATES:
            review_counts['not_publication_ready'] += 1

        record_id = (row.get('record_id') or '').strip()
        if not record_id:
            provenance_counts['missing_record_id'] += 1
        elif record_id in seen_record_ids:
            provenance_counts['duplicate_record_id'] += 1
        else:
            seen_record_ids.add(record_id)
        if not is_meaningful_source_record_id(row.get('source_record_id')):
            provenance_counts['missing_source_record_id'] += 1
        if not is_meaningful_provenance_locator(row.get('provenance_source')):
            provenance_counts['missing_provenance_source'] += 1
        translation_source = (row.get('translation_source') or '').strip()
        if not is_meaningful_provenance_locator(translation_source):
            provenance_counts['missing_translation_source'] += 1
        if review_state == '<missing>':
            provenance_counts['missing_translation_review_status'] += 1
        if (translation_model_required(translation_source, review_state)
                and not is_specific_translation_model_identifier(
                    row.get('translation_model'))):
            provenance_counts['missing_required_translation_model'] += 1

        chain_value = row.get('chain_indx')
        if not str(chain_value or '').strip():
            chain_counts['missing_chain_indx'] += 1
            tradition_chain['missing_chain_indx'] += 1
        else:
            tradition_chain['present_chain_indx'] += 1
            try:
                references = _chain_references(chain_value)
            except ValueError:
                chain_counts['invalid_chain_indx'] += 1
                tradition_chain['invalid_chain_indx'] += 1
                references = []
            unknown_references = sum(
                1 for reference in references if reference not in narrator_ids
            )
            chain_counts['unknown_chain_indx_references'] += unknown_references
            tradition_chain['unknown_chain_indx_references'] += unknown_references

        source = (row.get('source') or '').strip()
        tradition = (row.get('tradition') or '').strip()
        if tradition not in SUPPORTED_TRADITIONS:
            source_counts['unsupported_tradition'] += 1
        grade_tradition = (row.get('grade_tradition') or '').strip()
        if grade_tradition and grade_tradition not in SUPPORTED_TRADITIONS:
            source_counts['unsupported_grade_tradition'] += 1
        if not source:
            source_counts['missing_source'] += 1
            continue
        previous = observed_source_traditions.get(source)
        if previous and previous != tradition:
            source_counts['source_tradition_conflicts'] += 1
        else:
            observed_source_traditions[source] = tradition
        registered_tradition = source_registry.get(source)
        if registered_tradition is None:
            source_counts['unregistered_source_rows'] += 1
            unregistered_source_names.add(source)
        elif registered_tradition != tradition:
            source_counts['source_registry_mismatches'] += 1
            mismatched_source_names.add(source)
        if tradition == 'Imami':
            source_work_id = (row.get('source_work_id') or '').strip()
            if not source_work_id:
                source_counts['missing_imami_source_work_id'] += 1
            elif imami_source_work_registry is not None:
                registered_work = (
                    imami_source_work_registry['by_source_work_id']
                    .get(source_work_id)
                )
                if registered_work is None:
                    source_counts['unknown_imami_source_work_id'] += 1
                elif registered_work['canonical_source'] != source:
                    source_counts['imami_source_work_mismatches'] += 1

    gates = {
        'text_and_content': {
            'passed': not any(text_counts.values()),
            'counts': text_counts,
            'translation_issue_counts': dict(
                sorted(translation_issue_counts.items())),
        },
        'translation_review': {
            'passed': review_counts['not_publication_ready'] == 0,
            'counts': review_counts,
            'publication_ready_states': sorted(
                PUBLISHABLE_TRANSLATION_REVIEW_STATES),
            'review_state_counts': dict(sorted(review_state_counts.items())),
        },
        'provenance': {
            'passed': not any(provenance_counts.values()),
            'counts': provenance_counts,
        },
        'chain': {
            'passed': not any(chain_counts.values()),
            'counts': chain_counts,
            'by_tradition': dict(sorted(chain_by_tradition.items())),
        },
        'source_registry': {
            'passed': not any(source_counts.values()),
            'counts': source_counts,
            'unregistered_source_names': sorted(unregistered_source_names),
            'mismatched_source_names': sorted(mismatched_source_names),
        },
    }
    return gates


def write_curation_manifest(master: list, backlog: list, path: str,
                            source_registry: dict = None,
                            narrator_ids: set = None,
                            input_paths: list = None,
                            expected_record_range: tuple = None):
    """Persist the deterministic pre-load contract and its gate result."""
    traditions = {}
    sources = {}
    issues = {}
    translation_statuses = {}
    translation_review_statuses = {}
    translation_sources = {}
    translation_models = {}
    content = hashlib.sha256()
    for row in master:
        tradition = row.get('tradition', '')
        source = row.get('source', '')
        traditions[tradition] = traditions.get(tradition, 0) + 1
        sources[source] = sources.get(source, 0) + 1
        translation_status = row.get('translation_status', '') or '<missing>'
        review_status = row.get('translation_review_status', '') or '<missing>'
        translation_source = row.get('translation_source', '') or '<missing>'
        translation_model = row.get('translation_model', '') or '<missing>'
        translation_statuses[translation_status] = (
            translation_statuses.get(translation_status, 0) + 1)
        translation_review_statuses[review_status] = (
            translation_review_statuses.get(review_status, 0) + 1)
        translation_sources[translation_source] = (
            translation_sources.get(translation_source, 0) + 1)
        translation_models[translation_model] = (
            translation_models.get(translation_model, 0) + 1)
        canonical = {col: row.get(col, '') for col in UNIFIED_COLS}
        content.update(json.dumps(
            canonical, ensure_ascii=False, sort_keys=True,
            separators=(',', ':')).encode('utf-8'))
        content.update(b'\n')
    for item in backlog:
        issue = item['issue']
        issues[issue] = issues.get(issue, 0) + 1

    if input_paths is None:
        input_paths = [
            os.path.abspath(__file__),
            os.path.join(os.path.dirname(BASE_DIR), 'classify_attribution.py'),
            os.path.join(SHIA_DIR, 'build_csv.py'),
            SUNNI_ISNAD_SIDECAR,
            PURE_CANON_JSONL,
            CLASSICAL_TRANSLATIONS_CSV,
            CLASSICAL_TRANSLATIONS_CLEAN_JSONL,
            TRANSLATION_OVERRIDES_JSONL,
            CURATION_DISPOSITIONS_JSONL,
            os.path.join(IBADI_DIR, 'parsed_hadiths.json'),
            os.path.join(ZAYDI_DIR, 'parsed_hadiths.json'),
            os.path.join(RIDA_DIR, 'parsed_hadiths.json'),
            ALL_RAWIS_CSV,
            SOURCE_REGISTRY_TS,
            IMAMI_SOURCE_WORK_REGISTRY_JSON,
            EVIDENCE_CURATION_SCHEMA_JSON,
            EVIDENCE_CURATION_BUNDLE_JSON,
            EVIDENCE_CURATION_MANIFEST_JSON,
        ]
    else:
        input_paths = list(input_paths)
    for evidence_path in (
            EVIDENCE_CURATION_SCHEMA_JSON,
            EVIDENCE_CURATION_BUNDLE_JSON,
            EVIDENCE_CURATION_MANIFEST_JSON):
        if not any(
                os.path.abspath(candidate) == os.path.abspath(evidence_path)
                for candidate in input_paths):
            input_paths.append(evidence_path)
    inputs = {}
    for input_path in input_paths:
        if os.path.exists(input_path):
            inputs[os.path.relpath(input_path, BASE_DIR).replace('\\', '/')] = {
                'bytes': os.path.getsize(input_path),
                'sha256': _sha256_file(input_path),
            }

    full_load_gates = assess_full_load_gates(
        master, source_registry=source_registry, narrator_ids=narrator_ids)
    full_load_gates['citation_bound_evidence'] = evidence_curation_gate()
    full_load_gates['curation_backlog'] = {
        'passed': not backlog,
        'counts': {'rows': len(backlog)},
    }
    full_load_gates['corpus_nonempty'] = {
        'passed': bool(master),
        'counts': {'record_count': len(master)},
    }
    if expected_record_range:
        minimum, maximum = expected_record_range
        in_range = minimum <= len(master) <= maximum
        full_load_gates['corpus_shape'] = {
            'passed': in_range,
            'counts': {
                'record_count': len(master),
                'below_minimum': int(len(master) < minimum),
                'above_maximum': int(len(master) > maximum),
            },
            'expected_record_range': [minimum, maximum],
        }
    ready_for_full_load = all(
        gate['passed'] for gate in full_load_gates.values()
    )
    stable_record_ids = {
        (row.get('record_id') or '').strip()
        for row in master
        if (row.get('record_id') or '').strip()
    }

    manifest = {
        'schema_version': 2,
        'dataset_schema': UNIFIED_COLS,
        'candidate_content_sha256': content.hexdigest(),
        'record_count': len(master),
        'stable_record_id_count': len(stable_record_ids),
        'tradition_counts': dict(sorted(traditions.items())),
        'source_counts': dict(sorted(sources.items())),
        'translation_status_counts': dict(sorted(translation_statuses.items())),
        'translation_review_status_counts': dict(
            sorted(translation_review_statuses.items())),
        'translation_source_counts': dict(sorted(translation_sources.items())),
        'translation_model_counts': dict(sorted(translation_models.items())),
        'release_blockers': dict(sorted(issues.items())),
        'full_load_gates': full_load_gates,
        'ready_for_full_load': ready_for_full_load,
        'inputs': inputs,
    }
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, path)
    print(f"  Written: {path} (ready_for_full_load={ready_for_full_load})")
    return manifest


def _sha256_gzip_logical(path: str) -> str:
    digest = hashlib.sha256()
    with gzip.open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def bind_published_dataset_manifest(manifest_path: str, csv_path: str,
                                    published_csv_path: str = None):
    """Bind a successful manifest to the exact published CSV/GZIP bytes."""
    gzip_path = csv_path + '.gz'
    if not os.path.exists(csv_path) or not os.path.exists(gzip_path):
        raise FileNotFoundError(
            'Candidate CSV and GZIP must both exist before manifest binding')
    with open(manifest_path, encoding='utf-8') as f:
        manifest = json.load(f)
    if manifest.get('ready_for_full_load') is not True:
        raise ValueError('Refusing to bind a non-ready curation manifest')

    logical_hash = _sha256_file(csv_path)
    gzip_logical_hash = _sha256_gzip_logical(gzip_path)
    if gzip_logical_hash != logical_hash:
        raise ValueError('Published GZIP does not expand to the canonical CSV')
    published_csv_path = published_csv_path or csv_path
    published_gzip_path = published_csv_path + '.gz'
    manifest['published_dataset'] = {
        'logical_sha256': logical_hash,
        'csv': {
            'path': os.path.relpath(
                published_csv_path, BASE_DIR).replace('\\', '/'),
            'bytes': os.path.getsize(csv_path),
            'sha256': logical_hash,
        },
        'gzip': {
            'path': os.path.relpath(
                published_gzip_path, BASE_DIR).replace('\\', '/'),
            'bytes': os.path.getsize(gzip_path),
            'sha256': _sha256_file(gzip_path),
            'logical_sha256': gzip_logical_hash,
        },
    }
    tmp = manifest_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, manifest_path)
    print(f"  Bound manifest to published dataset: {manifest['published_dataset']['logical_sha256']}")


def load_classical_translation_index() -> dict:
    """Load the completed classical translation asset by immutable ``pc_*`` id.

    Enhanced rows take precedence. A clean-JSONL-only ID is eligible only when
    its ID, canonical source, and Arabic identity are complete and unique; the
    application join independently requires exact source and Arabic equality.
    """
    index = {}
    enhanced_ids = set()
    if os.path.exists(CLASSICAL_TRANSLATIONS_CSV):
        with open(CLASSICAL_TRANSLATIONS_CSV, encoding='utf-8',
                  errors='replace') as f:
            for row_no, row in enumerate(csv.DictReader(f), 2):
                source_record_id = (row.get('id') or '').strip()
                if not source_record_id:
                    continue
                if source_record_id in enhanced_ids:
                    raise ValueError(
                        f'Duplicate enhanced classical translation ID '
                        f'{source_record_id} at row {row_no}'
                    )
                enhanced_ids.add(source_record_id)
                text_en = ((row.get('text_en_enhanced') or '').strip()
                           or (row.get('text_en') or '').strip())
                index[source_record_id] = {
                    'text_ar': (row.get('text_ar') or '').strip(),
                    'text_en': text_en,
                    'source_canonical': (row.get('source_canonical') or '').strip(),
                    'translation_source': (
                        'archive/classical-pipeline/classical_canon_enhanced.csv'),
                    'translation_review_status': 'machine_unreviewed',
                }
    else:
        print(f"  WARNING: {CLASSICAL_TRANSLATIONS_CSV} not found")

    # The enhanced CSV is authoritative when populated. The clean JSONL may
    # safely supply a unique identity absent from, or blank in, that product.
    if os.path.exists(CLASSICAL_TRANSLATIONS_CLEAN_JSONL):
        clean_candidates = {}
        duplicate_clean_ids = set()
        with open(CLASSICAL_TRANSLATIONS_CLEAN_JSONL, encoding='utf-8',
                  errors='replace') as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                source_record_id = (row.get('id') or '').strip()
                text_en = (row.get('text_en') or '').strip()
                if not text_en:
                    continue
                if not source_record_id:
                    raise ValueError(
                        f'Clean classical translation missing ID at line {line_no}'
                    )
                text_ar = (row.get('text_ar') or '').strip()
                source_canonical = (
                    row.get('source_canonical') or '').strip()
                if not text_ar or not source_canonical:
                    raise ValueError(
                        f'Clean classical translation {source_record_id} lacks '
                        f'exact source/Arabic identity at line {line_no}'
                    )
                if source_record_id in clean_candidates:
                    previous = clean_candidates[source_record_id]
                    previous_identity = (
                        (previous.get('source_canonical') or '').strip(),
                        (previous.get('text_ar') or '').strip(),
                    )
                    if previous_identity != (source_canonical, text_ar):
                        raise ValueError(
                            f'Conflicting clean classical translation identity '
                            f'for {source_record_id} at line {line_no}'
                        )
                    duplicate_clean_ids.add(source_record_id)
                    continue
                clean_candidates[source_record_id] = row
        for source_record_id, row in clean_candidates.items():
            if source_record_id in duplicate_clean_ids:
                continue
            current = index.get(source_record_id)
            if current:
                current_identity = (
                    (current.get('source_canonical') or '').strip(),
                    (current.get('text_ar') or '').strip(),
                )
                clean_identity = (
                    (row.get('source_canonical') or '').strip(),
                    (row.get('text_ar') or '').strip(),
                )
                if current_identity != clean_identity:
                    raise ValueError(
                        f'Conflicting classical translation identity for '
                        f'{source_record_id}'
                    )
                if (current.get('text_en') or '').strip():
                    continue
            text_en = (row.get('text_en') or '').strip()
            index[source_record_id] = {
                'text_ar': (row.get('text_ar') or '').strip(),
                'text_en': text_en,
                'source_canonical': (row.get('source_canonical') or '').strip(),
                'translation_source': (
                    'archive/classical-pipeline/classical_translations_clean.jsonl'),
                'translation_review_status': 'machine_unreviewed',
            }
    else:
        print(f"  WARNING: {CLASSICAL_TRANSLATIONS_CLEAN_JSONL} not found")
    return index


def load_translation_overrides(path: str = TRANSLATION_OVERRIDES_JSONL) -> dict:
    """Load reviewed/source-recovered translations bound to an Arabic hash."""
    if not os.path.exists(path):
        return {}
    overrides = {}
    with open(path, encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            record_id = (row.get('record_id') or '').strip()
            required = ('arabic_sha256', 'text_en', 'translation_source',
                        'translation_review_status')
            missing = [key for key in required if not (row.get(key) or '').strip()]
            if not record_id or missing:
                raise ValueError(
                    f"Invalid translation override at line {line_no}: "
                    f"record_id/required fields missing ({', '.join(missing)})")
            if record_id in overrides:
                raise ValueError(
                    f"Duplicate translation override for {record_id} at line {line_no}")
            overrides[record_id] = row
    return overrides


def apply_translation_overrides(master: list, overrides: dict) -> int:
    """Apply only exact-text-bound overrides and reject stale/invalid entries."""
    if not overrides:
        return 0
    rows_by_id = {str(row.get('record_id') or '').strip(): row for row in master}
    unknown = sorted(set(overrides) - set(rows_by_id))
    if unknown:
        raise ValueError(
            f"Translation overrides reference {len(unknown)} unknown record_id values: "
            f"{unknown[:5]}")

    applied = 0
    for record_id, override in overrides.items():
        row = rows_by_id[record_id]
        expected_hash = _text_sha256(row.get('text_ar', ''))
        if override['arabic_sha256'].strip().lower() != expected_hash:
            raise ValueError(
                f"Stale translation override for {record_id}: Arabic hash mismatch")
        text_en = override['text_en'].strip()
        issue = translation_issue(text_en, row.get('text_ar', ''))
        if issue:
            raise ValueError(
                f"Invalid translation override for {record_id}: {issue}")
        row['text_en'] = text_en
        row['translation_status'] = 'complete'
        row['translation_source'] = override['translation_source'].strip()
        row['translation_model'] = (override.get('translation_model') or '').strip()
        row['translation_review_status'] = (
            override['translation_review_status'].strip())
        applied += 1
    return applied


def source_translation_collision_ids(master: list) -> set:
    """Find reused English attached to divergent rows under one source ID."""
    groups = {}
    for row in master:
        key = (
            (row.get('source') or '').strip(),
            (row.get('hadith_id') or '').strip(),
            str(row.get('hadith_no') or '').strip(),
        )
        text_en = (row.get('text_en') or '').strip()
        if not all(key) or not text_en:
            continue
        groups.setdefault(key, []).append(row)

    collided = set()
    for rows in groups.values():
        if len({(row.get('text_ar') or '').strip() for row in rows}) < 2:
            continue
        by_english = {}
        for row in rows:
            by_english.setdefault((row.get('text_en') or '').strip(), []).append(row)
        for duplicates in by_english.values():
            if len(duplicates) < 2:
                continue
            collided.update(
                (row.get('record_id') or '').strip() for row in duplicates)
    return collided


def _sunni_key(source: str, hadith_no) -> str:
    """Stable join key for the Sunni sidecar: (source, hadith_no).

    Master ids are reassigned every rebuild, so they cannot be the join key;
    (source, hadith_no) is unique within the canon and survives rebuilds.
    """
    return f"{(source or '').strip()}|{str(hadith_no).strip()}"


def load_sunni_isnad_sidecar() -> dict:
    """Map (source,hadith_no) → extracted {sanad, sanad_confidence}.

    Built by extract_isnad_sunni.py. When absent or a row is missing, Sunni
    keeps an empty structured sanad — text_ar always holds the verbatim chain.
    """
    out = {}
    if os.path.exists(SUNNI_ISNAD_SIDECAR):
        with open(SUNNI_ISNAD_SIDECAR, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                out[_sunni_key(r.get('source'), r.get('hadith_no'))] = r
    return out

# Canonical K6 source names (sunnah.com export — note leading/trailing spaces
# in the raw CSV). These are the ONLY sources loaded from all_hadiths_clean.csv
# to avoid re-ingesting classical rows that regen_unified_csvs.py itself wrote.
K6_CANONICAL_SOURCES = {
    "Sahih Muslim", "Sahih Bukhari", "Sunan an-Nasa'i",
    "Sunan Abi Da'ud", "Sunan Ibn Majah", "Jami' al-Tirmidhi",
    # With the leading space that the sunnah.com CSV export includes:
    " Sahih Muslim ", " Sahih Bukhari ", " Sunan an-Nasa'i ",
    " Sunan Abi Da'ud ", " Sunan Ibn Majah ", " Jami' al-Tirmidhi ",
}

SOURCE_TO_TRADITION = {
    "Sahih Muslim": "Sunni",
    "Sahih Bukhari": "Sunni",
    "Sunan an-Nasa'i": "Sunni",
    "Sunan Abi Da'ud": "Sunni",
    "Sunan Ibn Majah": "Sunni",
    "Jami' al-Tirmidhi": "Sunni",
}

NON_THAQALAYN_IMAMI_SOURCE_WORK_IDS = {
    'Sahifat al-Imam Ali al-Rida': 'imami:sahifat-al-imam-ali-al-rida',
}


def load_openiti_hadiths(collection_dir: str) -> list:
    """Load hadiths from an OpenITI-parsed JSON file."""
    path = os.path.join(collection_dir, 'parsed_hadiths.json')
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    provenance_source = (
        f"{os.path.basename(collection_dir)}/parsed_hadiths.json"
    )
    return [
        {**row, '_provenance_source': provenance_source}
        for row in data.get('hadiths', [])
    ]


def rebuild_shia_csv(output_path: str) -> bool:
    """Build a raw Thaqalayn CSV at a caller-owned staging path."""
    print("  Rebuilding Imami data from Thaqalayn JSONs into staging...")
    build_csv_path = os.path.join(SHIA_DIR, 'build_csv.py')
    if not os.path.exists(build_csv_path):
        print("  WARNING: shia-hadith/build_csv.py not found, using existing CSV")
        return False
    runner = (
        "import runpy, sys\n"
        "namespace = runpy.run_path(sys.argv[1])\n"
        "main = namespace['main']\n"
        "main.__globals__['OUTPUT_PATH'] = sys.argv[2]\n"
        "main()\n"
    )
    result = subprocess.run(
        [sys.executable, '-c', runner, build_csv_path, output_path],
        cwd=SHIA_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.stdout.strip():
        print(f"  {result.stdout.strip()}")
    if result.returncode != 0:
        raise RuntimeError(
            f"Staged Thaqalayn build failed: {result.stderr.strip()}"
        )
    if not os.path.isfile(output_path):
        raise RuntimeError(
            f"Staged Thaqalayn build did not create {output_path}"
        )
    return True


def load_sunni_rows(csv_path: str = None) -> list:
    """Load K6 (Kutub al-Sittah) Sunni rows from all_hadiths_clean.csv.

    Filters strictly to the six canonical K6 source names so that classical
    rows added by this script in a previous run are NOT re-ingested (the
    all_hadiths_clean.csv is this script's own output and contains all Sunni
    rows after the first run).
    """
    csv_path = csv_path or os.path.join(BASE_DIR, 'all_hadiths_clean.csv')
    rows = []
    with open_csv_input(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = (row.get('source') or '').strip()
            # Accept only K6 source names — reject classical Sunni sources.
            if src in SOURCE_TO_TRADITION or row.get('source') in K6_CANONICAL_SOURCES:
                row['tradition'] = 'Sunni'
                rows.append(row)
    return rows


def load_imami_rows(csv_path: str = None,
                    authoritative_input: bool = False) -> list:
    """Load Imami rows from all_hadiths_shia.csv.

    all_hadiths_shia.csv is also this script's OUTPUT (Imami + Ibadi + Zaydi).
    With --no-shia the rebuild is skipped, so this would re-ingest the previous
    combined output and mislabel Ibadi/Zaydi rows as Imami. Guard against that
    by excluding rows whose source is a known OpenITI (non-Imami) collection,
    making a --no-shia re-run idempotent.
    """
    openiti_sources = set()
    for d in (IBADI_DIR, ZAYDI_DIR, RIDA_DIR):
        pj = os.path.join(d, 'parsed_hadiths.json')
        if os.path.exists(pj):
            with open(pj, 'r', encoding='utf-8') as fh:
                hs = json.load(fh).get('hadiths', [])
            openiti_sources.update(h.get('source', '') for h in hs)
    openiti_sources.discard('')

    csv_path = csv_path or os.path.join(BASE_DIR, 'all_hadiths_shia.csv')
    try:
        if authoritative_input:
            resolved_path = os.path.abspath(csv_path)
            if not os.path.isfile(resolved_path):
                raise FileNotFoundError(resolved_path)
        else:
            resolved_path = resolve_csv_input_path(csv_path)
    except FileNotFoundError:
        print("  WARNING: all_hadiths_shia.csv(.gz) not found")
        return []
    rows = []
    with _open_resolved_csv_input(resolved_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('source', '') in openiti_sources:
                continue  # Ibadi/Zaydi/Rida — appended separately, not Imami
            row['tradition'] = 'Imami'
            rows.append(row)
    return rows


def _format_sanad(h: dict) -> str:
    """Format sanad list as comma-separated English names."""
    sanad = h.get('sanad', [])
    if isinstance(sanad, list):
        return ', '.join(sanad) if sanad else ''
    return str(sanad)


def openiti_to_clean_row(h: dict, row_id: int, resolver,
                         chain_stats: dict) -> dict:
    """Convert an OpenITI-parsed hadith to clean CSV row."""
    text_ar = h['text_ar']
    return {
        'id': row_id,
        'hadith_id': h.get('hadith_no', ''),
        'source': h['source'],
        'tradition': h['tradition'],
        'chapter_no': h.get('bab_no', h.get('kitab_no', '')),
        'hadith_no': h.get('hadith_no', ''),
        'chapter': h.get('bab', h.get('kitab', '')),
        'chain_indx': canonical_chain_indx(
            text_ar, resolver, chain_stats
        ),
        'text_ar': text_ar,
        'text_en': h.get('text_en', ''),
        'sanad': _format_sanad(h),
        'school': h.get('school', ''),
        'chain_type': h.get('chain_type', ''),
    }


def openiti_to_shia_row(h: dict, row_id: int, resolver,
                        chain_stats: dict) -> dict:
    """Convert an OpenITI-parsed hadith to shia/extended CSV row."""
    parsed_id = str(h.get('id') or h.get('hadith_no') or '').strip()
    source_record_id = '|'.join(str(value or '').strip() for value in (
        parsed_id, h.get('hadith_no'), h.get('page_ref'),
    ))
    tradition = str(h.get('tradition') or '').strip()
    text_ar = h['text_ar']
    return {
        'id': row_id,
        'hadith_id': parsed_id,
        'source': h['source'],
        'source_work_id': NON_THAQALAYN_IMAMI_SOURCE_WORK_IDS.get(
            h['source'], '') if tradition == 'Imami' else '',
        'source_display_label': h['source'],
        'tradition': tradition,
        'volume': 1,
        'chapter_no': h.get('bab_no', h.get('kitab_no', '')),
        'hadith_no': h.get('hadith_no', ''),
        'chapter': h.get('bab', h.get('kitab', '')),
        'category': h.get('kitab', h.get('bab', '')),
        'chain_indx': canonical_chain_indx(
            text_ar, resolver, chain_stats
        ),
        'text_ar': text_ar,
        'text_en': h.get('text_en', ''),
        'sanad': _format_sanad(h),
        'matn_ar': h.get('matn_ar', ''),
        'matn_en': '',
        'school': h.get('school', ''),
        'chain_type': h.get('chain_type', ''),
        'grade_tradition': h['tradition'],
        'grade_source': '',
        'grade_value': '',
        'gradings_full': '',
        'url': '',
        'page_ref': h.get('page_ref', ''),
        'record_id': (
            f"openiti:{tradition.lower()}:{source_record_id}"
        ),
        'source_record_id': source_record_id,
        'provenance_source': h.get(
            '_provenance_source',
            f"{tradition.lower()}-hadith/parsed_hadiths.json",
        ),
        'translation_status': _translation_status(h.get('text_en', '')),
        'translation_source': (
            h.get('_provenance_source',
                  f"{tradition.lower()}-hadith/parsed_hadiths.json")
            if (h.get('text_en') or '').strip() else ''
        ),
        'translation_model': h.get('translation_model', ''),
        'translation_review_status': 'machine_unreviewed',
    }


def write_csv(path: str, fieldnames: list, rows: list):
    """Write rows to CSV with proper quoting."""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL,
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    shutil.move(tmp, path)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  Written: {path} ({len(rows):,} rows, {size_mb:.1f} MB)")


def compress_csv(path: str):
    """Write a byte-deterministic gzip companion alongside a CSV."""
    gz_path = path + '.gz'
    tmp_path = gz_path + '.tmp'
    with open(path, 'rb') as f_in, open(tmp_path, 'wb') as raw_out:
        with gzip.GzipFile(
            filename='', mode='wb', fileobj=raw_out, mtime=0
        ) as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.replace(tmp_path, gz_path)
    size_mb = os.path.getsize(gz_path) / (1024 * 1024)
    print(f"  Compressed: {gz_path} ({size_mb:.1f} MB)")


@contextmanager
def publication_lock(directory: str, timeout_seconds: float = 30.0,
                     poll_seconds: float = 0.05):
    """Bound concurrent publication with an operating-system file lock."""
    if timeout_seconds < 0 or poll_seconds <= 0:
        raise ValueError('Publication lock bounds must be positive')
    lock_path = os.path.join(directory, '.regen-publication.lock')
    handle = open(lock_path, 'a+b')
    acquired = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b'\0')
            handle.flush()
            os.fsync(handle.fileno())
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt  # noqa: PLC0415
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl  # noqa: PLC0415
                    fcntl.flock(
                        handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                acquired = True
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f'Timed out waiting for publication lock: {lock_path}'
                    ) from error
                time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))
        yield lock_path
    finally:
        if acquired:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt  # noqa: PLC0415
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl  # noqa: PLC0415
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def publish_staged_files(staged_to_target: list, commit_target: str = None):
    """Replace staged outputs with rollback and an optional last commit file."""
    if commit_target:
        if (not staged_to_target
                or os.path.realpath(staged_to_target[-1][1])
                != os.path.realpath(commit_target)):
            raise ValueError('Publication commit target must be replaced last')
    transaction_id = uuid.uuid4().hex
    installed = []
    backups = {}
    try:
        for staged_path, target_path in staged_to_target:
            if not os.path.isfile(staged_path):
                raise FileNotFoundError(
                    f'Publication stage missing: {staged_path}'
                )
            backup_path = None
            if os.path.exists(target_path):
                backup_path = f'{target_path}.rollback-{transaction_id}'
                os.replace(target_path, backup_path)
                backups[target_path] = backup_path
            try:
                os.replace(staged_path, target_path)
            except Exception:
                if backup_path and os.path.exists(backup_path):
                    os.replace(backup_path, target_path)
                    backups.pop(target_path, None)
                raise
            installed.append(target_path)
    except Exception:
        for target_path in reversed(installed):
            backup_path = backups.pop(target_path, None)
            if backup_path and os.path.exists(backup_path):
                os.replace(backup_path, target_path)
            elif os.path.exists(target_path):
                os.remove(target_path)
        for target_path, backup_path in list(backups.items()):
            if os.path.exists(backup_path):
                os.replace(backup_path, target_path)
        raise
    else:
        for backup_path in backups.values():
            if os.path.exists(backup_path):
                os.remove(backup_path)


def publish_incomplete_development_artifacts(
        staged_unified: str, staged_clean: str, staged_shia: str,
        staged_backlog: str, staged_manifest: str,
        staged_gap_path: str = None, development_root: str = None) -> dict:
    """Publish a non-ready build only under the isolated development tree."""
    development_root = development_root or os.path.join(
        BASE_DIR, 'development', 'incomplete-curation'
    )
    base = os.path.realpath(BASE_DIR)
    resolved_root = os.path.realpath(development_root)
    try:
        within_base = os.path.commonpath([base, resolved_root]) == base
    except ValueError:
        within_base = False
    if not within_base or resolved_root == base:
        raise ValueError(
            'Incomplete curation artifacts must stay in a child of BASE_DIR'
        )
    os.makedirs(resolved_root, exist_ok=True)
    targets = {
        'unified_csv': os.path.join(
            resolved_root, 'all_hadiths_unified.incomplete.csv'),
        'clean_csv': os.path.join(
            resolved_root, 'all_hadiths_clean.incomplete.csv'),
        'shia_csv': os.path.join(
            resolved_root, 'all_hadiths_shia.incomplete.csv'),
        'backlog': os.path.join(
            resolved_root, 'curation_backlog.incomplete.csv'),
        'manifest': os.path.join(
            resolved_root, 'curation_manifest.incomplete.json'),
    }
    publication = [
        (staged_unified, targets['unified_csv']),
        (staged_unified + '.gz', targets['unified_csv'] + '.gz'),
        (staged_clean, targets['clean_csv']),
        (staged_clean + '.gz', targets['clean_csv'] + '.gz'),
        (staged_shia, targets['shia_csv']),
        (staged_shia + '.gz', targets['shia_csv'] + '.gz'),
        (staged_backlog, targets['backlog']),
    ]
    if staged_gap_path:
        targets['narrator_gap'] = os.path.join(
            resolved_root, 'classical_narrator_gap.incomplete.csv')
        publication.append((staged_gap_path, targets['narrator_gap']))
    publication.append((staged_manifest, targets['manifest']))
    with publication_lock(resolved_root):
        publish_staged_files(publication, commit_target=targets['manifest'])
    return targets


def publish_canonical_dataset(publication: list, manifest_path: str,
                              unified_path: str):
    """Lock the complete canonical backup-and-replace transaction."""
    with publication_lock(os.path.dirname(os.path.realpath(manifest_path))):
        backup_unified_csv(unified_path)
        publish_staged_files(publication, commit_target=manifest_path)


def cleanup_stage_dir(stage_dir: str):
    """Remove only a generator-owned staging directory under BASE_DIR."""
    resolved = os.path.realpath(stage_dir)
    if (os.path.dirname(resolved) != os.path.realpath(BASE_DIR)
            or not os.path.basename(resolved).startswith('.regen-stage-')):
        raise ValueError(f'Refusing to remove unexpected staging path: {stage_dir}')
    shutil.rmtree(resolved)


def run_with_stage_dir(build):
    """Run a staged build and clean its validated temporary directory."""
    stage_dir = tempfile.mkdtemp(prefix='.regen-stage-', dir=BASE_DIR)
    try:
        return build(stage_dir)
    finally:
        if os.path.isdir(stage_dir):
            cleanup_stage_dir(stage_dir)


def has_valid_bound_manifest(manifest_path: str, csv_path: str) -> bool:
    """Return whether the active manifest is bound to the current CSV pair."""
    gzip_path = csv_path + '.gz'
    try:
        with open(manifest_path, encoding='utf-8') as f:
            manifest = json.load(f)
        published = manifest['published_dataset']
        csv_metadata = published['csv']
        gzip_metadata = published['gzip']
        logical_hash = _sha256_file(csv_path)
        return (
            manifest.get('ready_for_full_load') is True
            and os.path.isfile(gzip_path)
            and published.get('logical_sha256') == logical_hash
            and csv_metadata.get('sha256') == logical_hash
            and gzip_metadata.get('sha256') == _sha256_file(gzip_path)
            and _sha256_gzip_logical(gzip_path) == logical_hash
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def publish_failed_candidate(staged_backlog: str, backlog_path: str,
                             staged_manifest: str, candidate_manifest_path: str,
                             active_manifest_path: str,
                             active_csv_path: str) -> str:
    """Publish failed-attempt evidence without invalidating an active release."""
    publication_directory = os.path.dirname(
        os.path.realpath(active_manifest_path)
    )
    with publication_lock(publication_directory):
        return _publish_failed_candidate_locked(
            staged_backlog, backlog_path, staged_manifest,
            candidate_manifest_path, active_manifest_path, active_csv_path,
        )


def _publish_failed_candidate_locked(
        staged_backlog: str, backlog_path: str, staged_manifest: str,
        candidate_manifest_path: str, active_manifest_path: str,
        active_csv_path: str) -> str:
    """Commit failed-candidate evidence while the publication lock is held."""
    if has_valid_bound_manifest(active_manifest_path, active_csv_path):
        publish_staged_files([
            (staged_backlog, backlog_path),
            (staged_manifest, candidate_manifest_path),
        ], commit_target=candidate_manifest_path)
        return 'preserved_active_manifest'

    bootstrap_manifest = staged_manifest + '.bootstrap'
    shutil.copyfile(staged_manifest, bootstrap_manifest)
    publish_staged_files([
        (staged_backlog, backlog_path),
        (staged_manifest, candidate_manifest_path),
        (bootstrap_manifest, active_manifest_path),
    ], commit_target=active_manifest_path)
    return 'bootstrapped_nonready_manifest'


def verify(path: str):
    """Print source breakdown for a CSV."""
    sources = {}
    traditions = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = row.get('source', '?')
            t = row.get('tradition', '?')
            sources[s] = sources.get(s, 0) + 1
            traditions[t] = traditions.get(t, 0) + 1
    total = sum(sources.values())
    print(f"\n  {os.path.basename(path)}: {total:,} rows")
    for t, c in sorted(traditions.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c:,}")


def _enrich(urow: dict, sunni_isnad: dict) -> dict:
    """Fill the superset schema + attribution for one normalized row.

    - Sunni: structured sanad joined from the best-effort sidecar (text_ar
      always retains the verbatim chain regardless).
    - attributed_to / narration_level: from classify_attribution, which is
      tradition-aware (Prophet ﷺ vs which Imam vs Companion).
    """
    for col in UNIFIED_COLS:
        urow.setdefault(col, '')

    urow['source'] = (urow.get('source') or '').strip()

    trad = urow.get('tradition', '')
    if trad == 'Sunni':
        side = sunni_isnad.get(_sunni_key(urow.get('source'),
                                          urow.get('hadith_no')))
        if side:
            urow['sanad'] = ', '.join(side.get('sanad', []))
            urow['sanad_confidence'] = side.get('sanad_confidence', 0)
            if not (urow.get('matn_ar') or '').strip():
                urow['matn_ar'] = side.get('matn_ar', '')
        else:
            urow['sanad_confidence'] = 0
    elif urow.get('sanad_confidence') == '':
        # OpenITI/Thaqalayn sanad is sourced/parsed, not heuristic.
        urow['sanad_confidence'] = 2 if (urow.get('sanad') or '').strip() else 0

    who, level = classify_attribution(
        urow.get('text_ar', ''), urow.get('sanad', ''),
        trad, urow.get('source', ''))
    urow['attributed_to'] = who
    urow['narration_level'] = level
    if not (urow.get('record_id') or '').strip():
        identity_seed = '|'.join((
            str(urow.get('tradition') or ''),
            str(urow.get('source') or ''),
            str(urow.get('source_record_id') or urow.get('hadith_id') or ''),
            str(urow.get('text_ar') or ''),
        ))
        urow['record_id'] = f"legacy:{_stable_token(identity_seed)}"
    if not (urow.get('source_record_id') or '').strip():
        urow['source_record_id'] = str(
            urow.get('hadith_id') or urow.get('hadith_no') or ''
        ).strip()
    issue = translation_issue(urow.get('text_en', ''), urow.get('text_ar', ''))
    urow['translation_status'] = issue or 'complete'
    return urow


def _project(rows: list, cols: list) -> list:
    """Column-projection of master rows into a derived view's schema."""
    return [{c: r.get(c, '') for c in cols} for r in rows]


# ─── Classical Sunni isnad extraction ──────────────────────────────────────

# Transmission-introducing verbs — used to SPLIT the chain into segments.
# The pure_canon `chain` field uses these as delimiters between narrators,
# NOT Arabic commas (unlike K6 which comes from sunnah.com).
_CHAIN_VERB_SPLIT = re.compile(
    r"(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)\s+"
)
# 'عن' links — each introduces a new narrator name.
_AAN_SPLIT = re.compile(r"\bعن\b")
# Trailing narrative cues to drop from the last segment.
_TRAILING_NARRATIVE = re.compile(r"\s*(?:قال|قالت|قالوا|يقول|وهو|قد|في|عن)\s*$")
# Trailing honorifics to strip.
_CLASSICAL_HONORIFIC = re.compile(
    r"\s*رض[ىي]\s*الله\s*عنه?[امه]*\s*"
    r"|\s*رحمه\s*الله\s*|\s*عليه\s*السلام\s*"
    r"|\s*صلى\s*الله\s*عليه\s*(?:وآله\s*)?وسلم\s*"
    r"|\s*أم\s+المؤمنين\s*"
)
_CLASSICAL_PUNCT = re.compile(r"[،,.:؛!؟\"'\(\)\[\]‏‎]+")
# Plausibility guard — tokens with narrative connectors are not name segments.
_NARRATIVE_RE = re.compile(
    r"\b(?:ثم|حتى|فقال|فقالت|فكان|فلما|إذ|فأخذ|فرجع|فدخل|قلت|قال|أن|وهو)\b")


def _clean_chain_segment(raw: str) -> str:
    """Strip honorifics, punctuation, and trailing narrative from a segment."""
    n = _CLASSICAL_HONORIFIC.sub(" ", raw.strip())
    n = _CLASSICAL_PUNCT.sub(" ", n)
    n = _TRAILING_NARRATIVE.sub("", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def extract_classical_isnad(chain_text: str) -> list:
    """Parse the pre-extracted `chain` field from pure_canon.jsonl into a
    list of narrator surface-form names.

    pure_canon separates the isnad into the `chain` key using transmission
    verbs (حدثنا, عن, etc.) as delimiters — NOT Arabic commas. Strategy:
    1. Split on taḥwīl boundary (keep first chain only).
    2. Split on transmission verbs to isolate narrator segments.
    3. For each segment, split further on 'عن' links.
    4. Clean honorifics and trailing cues from each candidate name.

    Returns an empty list when the chain is blank or untrustworthy.
    """
    if not chain_text or not chain_text.strip():
        return []

    # taḥwīl guard — keep first chain only.
    th = re.search(r"(?:^|\s)ح\s+و?(?:حدثنا|أخبرنا)", chain_text)
    chain = chain_text[: th.start()] if th else chain_text

    # Split on transmission verbs first, then on عن links within each part.
    raw_segments = []
    verb_parts = _CHAIN_VERB_SPLIT.split(chain)
    for part in verb_parts:
        aan_parts = _AAN_SPLIT.split(part)
        raw_segments.extend(aan_parts)

    sanad = []
    for seg in raw_segments:
        nm = _clean_chain_segment(seg)
        if not nm or nm.isdigit() or len(nm) < 2 or len(nm) > 80:
            continue
        # Reject segments that look like narrative fragments.
        if _NARRATIVE_RE.search(nm) and len(nm) > 15:
            continue
        if not sanad or sanad[-1] != nm:
            sanad.append(nm)

    # Final plausibility: if any token is absurdly long it means boundary failed.
    if any(len(n) > 60 for n in sanad):
        return []

    return sanad


# ─── Narrator resolver (reusable helper — see module proposal below) ────────

_ARABIC_IN_PARENS = re.compile(r'\(\s*([^\)]*[؀-ۿ][^\)]*)\)')
_ARABIC_RANGE = re.compile(r'[؀-ۿ]')


def narrator_normalize(surface: str) -> str:
    """Normalize only Unicode presentation and format variants for name lookup."""
    from classify_attribution import _norm  # noqa: PLC0415

    compatibility = unicodedata.normalize('NFKC', surface or '')
    without_format_controls = ''.join(
        char for char in compatibility if unicodedata.category(char) != 'Cf'
    )
    return _norm(without_format_controls)


# --- Narrator spelling folds (adopted 2026-11-21; contract in AGENTS.md "Narrator identity lookup") ---
# Rules are ordered and applied on top of narrator_normalize. They never strip the definite article and never
# drop a name component. Not adopted (diagnostics only): hamza on waw/ya carriers, ta marbuta to ha.
_PERSIAN_URDU_LETTERS = str.maketrans({
    'ی': 'ي', 'ے': 'ي', 'ک': 'ك', 'ھ': 'ه', 'ہ': 'ه', 'ە': 'ه', 'ۃ': 'ة',
})
_THEOPHORIC_JOINED = re.compile(r'^عبد(ال[ء-ي]{2,})$')
_KUNYA_JOINED = re.compile(r'^(ابو|ابي|ابا)(ال[ء-ي]{2,})$')
_NASAB_CONNECTOR_FORMS = {'ابن': 'بن', 'ابنة': 'بنت'}
_KUNYA_HEADS = ('ابو', 'ابي', 'ابا', 'ام')
_NASAB_CONNECTORS = ('بن', 'بنت')
_BLESSING_FORMULA = re.compile(
    r'(?<![ء-ي])(?:'
    r'رضي الله(?: تعالي)? عن(?:ه|ها|هما|هم|هن)(?: اجمعين)?|'
    r'عليه(?:ما|م)? السلام|عليها السلام|'
    r'صلي الله عليه(?: واله)?(?: وسلم)?|سلام الله عليه(?:ا|م)?|'
    r'رحمه(?:م|ا)? الله(?: تعالي)?'
    r')(?![ء-ي])'
)


def fold_persian_urdu_letter_variants(text: str) -> str:
    """Persian/Urdu yeh, kaf and heh forms to the Arabic letters."""
    return text.translate(_PERSIAN_URDU_LETTERS)


def fold_punctuation_and_whitespace(text: str) -> str:
    """Replace every non-letter character with a space and collapse spaces (letters of any script stay)."""
    return ' '.join(''.join(
        char if unicodedata.category(char).startswith('L') else ' ' for char in text
    ).split())


def fold_nasab_connector_forms(text: str) -> str:
    """ابن to بن and ابنة to بنت; the relational pronoun ابنه ('his son') is left alone."""
    return ' '.join(_NASAB_CONNECTOR_FORMS.get(token, token) for token in text.split())


def fold_theophoric_compound_spacing(text: str) -> str:
    """عبدالله to 'عبد الله' (ال-names only; عبيد is a different name)."""
    out: list = []
    for token in text.split():
        match = _THEOPHORIC_JOINED.match(token)
        out.extend(['عبد', match.group(1)] if match else [token])
    return ' '.join(out)


def fold_kunya_compound_spacing(text: str) -> str:
    """ابوالقاسم to 'ابو القاسم' (joined kunya head plus an ال-name)."""
    out: list = []
    for token in text.split():
        match = _KUNYA_JOINED.match(token)
        out.extend([match.group(1), match.group(2)] if match else [token])
    return ' '.join(out)


NARRATOR_FOLD_RULES = (
    ('persian_urdu_letter_variants', fold_persian_urdu_letter_variants),
    ('punctuation_and_whitespace', fold_punctuation_and_whitespace),
    ('nasab_connector_forms', fold_nasab_connector_forms),
    ('theophoric_compound_spacing', fold_theophoric_compound_spacing),
    ('kunya_compound_spacing', fold_kunya_compound_spacing),
)


def narrator_fold_normalize(surface: str) -> str:
    """narrator_normalize plus the adopted spelling folds: the tier-1 lookup key."""
    text = narrator_normalize(surface)
    for _, rule in NARRATOR_FOLD_RULES:
        text = rule(text)
    return text


def fold_kunya_case_forms(key: str) -> str:
    """ابي/ابا to ابو when a non-connector token follows (keeps the name Ubayy in 'ابي بن كعب')."""
    tokens = key.split()
    return ' '.join(
        'ابو' if token in ('ابي', 'ابا') and index + 1 < len(tokens)
        and tokens[index + 1] not in _NASAB_CONNECTORS else token
        for index, token in enumerate(tokens)
    )


def kunya_fold_allowed(key: str) -> bool:
    """Specificity guard: only a surface with a nasab, or several components not led by a kunya, may use the fold."""
    tokens = key.split()
    if any(token in _NASAB_CONNECTORS for token in tokens[1:]):
        return True
    return len(tokens) >= 2 and tokens[0] not in _KUNYA_HEADS and tokens[0] not in ('ابن', 'بن', 'بنت')


def strip_blessing_formulas(normalized_text: str) -> str:
    """Remove blessing formulas (token-bounded phrases) from an already folded name; never lone letters."""
    return ' '.join(_BLESSING_FORMULA.sub(' ', normalized_text).split())


def _extract_arabic_name(name_field: str, strip_formulas: bool = True) -> str:
    """Extract the Arabic portion from an all_rawis name field.

    By default blessing formulas (رضي الله عنه, ...) are removed from the name, including on the unclosed-parenthesis
    fallback path, and the result is returned already folded (idempotent under narrator_fold_normalize).
    strip_formulas=False returns the historical extraction used for tier-0 keys and legacy audit comparison.

    all_rawis names follow the pattern: 'English Name ( Arabic Name ( grade )'
    e.g. 'Abu Bakr As-Siddique ( أبو بكر الصديق ( رضي الله عنه'
    Extract the first parenthesised block that contains Arabic letters,
    then strip trailing parenthetical grade/honorific info.
    """
    extracted = _extract_arabic_name_raw(name_field)
    if not strip_formulas:
        return extracted
    return strip_blessing_formulas(narrator_fold_normalize(extracted))


_NAME_FIELD_SEPARATOR = re.compile(r'\(\s+')     # the ' ( ' between English label, Arabic name and grade
_INNER_ALTERNATIVE = re.compile(r'\([^()]*\)')   # an alternative inside the Arabic name: (عبد رب), (الصغرى)


def _arabic_block_without_alternatives(name_field: str) -> str:
    """Whole Arabic name segment of 'English ( Arabic ( grade', inner alternatives removed; '' when absent."""
    for part in _NAME_FIELD_SEPARATOR.split(name_field)[1:]:
        if len(_ARABIC_RANGE.findall(part)) >= 3:
            return ' '.join(_INNER_ALTERNATIVE.sub(' ', part).replace('(', ' ').replace(')', ' ').split())
    return ''


def _extract_arabic_name_raw(name_field: str) -> str:
    """Historical extraction (formulas kept on the unclosed-parenthesis fallback)."""
    # Try to find Arabic text in parentheses
    for m in _ARABIC_IN_PARENS.finditer(name_field):
        candidate = m.group(1).strip()
        # If it has enough Arabic chars and isn't a grade/honorific only
        arabic_chars = len(_ARABIC_RANGE.findall(candidate))
        if arabic_chars >= 3:
            # Strip trailing honorifics
            candidate = _CLASSICAL_HONORIFIC.sub("", candidate).strip()
            if '(' in candidate:
                # Inner alternative: 'عبد الله (عبد رب) بن حق' is the whole name, not 'عبد الله' (AGENTS.md).
                whole = _CLASSICAL_HONORIFIC.sub("", _arabic_block_without_alternatives(name_field)).strip()
                if len(_ARABIC_RANGE.findall(whole)) >= 3:
                    return whole
            # Strip nested paren leftovers
            candidate = re.sub(r'\(.*', '', candidate).strip()
            if arabic_chars >= 3:
                return candidate
    # Fallback: take Arabic chars directly from the full name
    arabic_parts = ''.join(c for c in name_field if _ARABIC_RANGE.match(c) or c == ' ')
    return arabic_parts.strip()


# Phase-4 kunya alias support. Operate on raw (pre-_norm) Arabic surface so
# both ابو/أبو and ابي/أبي variants are reachable; the caller _norm()s before
# indexing (matches the existing build_narrator_index pattern).
_KUNYA_PREFIXES = ("أبو", "أبي", "ابو", "ابي", "أم", "ام")


def _extract_alias_segments(arabic_name: str) -> list[str]:
    """Extract candidate kunya alias surfaces from a raw Arabic name.

    Given an Arabic name like "أبو عوانة اليشكري وضاح بن خالد", return:
      ["أبو عوانة", "أبو عوانة اليشكري"]

    For "ابن عمر بن الخطاب":
      ["ابن عمر", "ابن عمر بن"]   (caller dedupes via _norm)

    Returns surfaces in their original Arabic surface form (NOT _norm'd; the
    caller applies _norm before indexing). Intentionally narrow: only emits
    aliases anchored on a kunya prefix token, with 1 or 2 following name
    tokens. Wider windows would over-generate noise.

    Aliases that map to ≥2 scholars are rejected by the caller's uniqueness
    check; this function may emit ambiguous candidates without harm.
    """
    tokens = (arabic_name or "").split()
    aliases: list[str] = []
    for i, tok in enumerate(tokens):
        if tok in _KUNYA_PREFIXES and i + 1 < len(tokens):
            aliases.append(" ".join(tokens[i:i + 2]))
            if i + 2 < len(tokens):
                aliases.append(" ".join(tokens[i:i + 3]))
    return aliases


class NarratorExactIndex(dict):
    """Tier-0 exact index (dict content, unchanged semantics) carrying the tier-1/tier-2 lookup tables.

    folded         : narrator_fold_normalize(formula-free registry name) -> set of scholar_indx
    kunya_folded   : fold_kunya_case_forms(folded key) -> set of scholar_indx (guarded use only)
    exact_ambiguous: tier-0 keys shared by several scholars, or held by a placeholder entry (never resolve)
    withheld_bare_names: scholar_indx whose formula-stripped name is a single token (not indexed in tier 1)
    placeholders   : scholar_indx -> reason; never an automatic match target (registry_placeholder_reason)
    """

    folded: dict
    kunya_folded: dict
    exact_ambiguous: set
    withheld_bare_names: list
    placeholders: dict


_PLACEHOLDER_MARKER = re.compile(r'\bShykh\b')


def registry_placeholder_reason(name_field: str) -> str:
    """Why a registry row can never be an automatic match target ('' for a person entry); see AGENTS.md.

    unidentified_shaykh_marker: the label carries the lexicon's 'Shykh' marker ('Sh'bh Shykh شعبة').
    no_arabic_name / bare_single_token_name: the formula-free Arabic name has 0 or 1 tokens ('يحيى').
    kunya_only_name: the name is a kunya alone ('ابو معاوية'), which many people share.
    """
    if _PLACEHOLDER_MARKER.search(name_field or ''):
        return 'unidentified_shaykh_marker'
    tokens = _extract_arabic_name(name_field or '').split()
    if not tokens:
        return 'no_arabic_name'
    if len(tokens) == 1:
        return 'bare_single_token_name'
    if len(tokens) == 2 and tokens[0] in _KUNYA_HEADS:
        return 'kunya_only_name'
    return ''


def build_narrator_index(all_rawis_path: str):
    """Load all_rawis.csv and return two lookup dicts:
        exact_index  : exact normalized registry names, unique only
        blocked_index: auditable prefix/kunya candidates, never auto-resolved

    See `AGENTS.md` under "Sanad and narrator completeness".
    """
    exact_index = NarratorExactIndex()    # norm_name -> scholar_indx (tier 0)
    folded_index: dict = {}               # tier 1: folded formula-free name -> {scholar_indx}
    kunya_folded_index: dict = {}         # tier 2: kunya-case-folded tier-1 key -> {scholar_indx}
    withheld_bare: list = []
    blocked_index = {}  # block_key -> [(scholar_indx, norm_name)]
    dup_norms = set()   # normalized names that map to multiple scholars

    def _add(norm: str, indx: str):
        if not norm:
            return
        if norm in exact_index and exact_index[norm] != indx:
            dup_norms.add(norm)
        else:
            exact_index[norm] = indx
        block = norm[:4] if len(norm) >= 4 else norm
        # Avoid duplicate (indx, norm) entries in block
        entry = (indx, norm)
        block_list = blocked_index.setdefault(block, [])
        if entry not in block_list:
            block_list.append(entry)

    # Gather kunya surfaces for review-only candidate lookup.
    alias_candidates: dict[str, set[str]] = {}  # alias_norm -> set of indxs
    placeholders: dict = {}           # scholar_indx -> reason (never a target)
    placeholder_exact_keys: set = set()

    with open(all_rawis_path, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            indx = row.get('scholar_indx', '').strip()
            name = row.get('name', '').strip()
            if not indx or not name:
                continue
            reason = registry_placeholder_reason(name)
            if reason:
                placeholders[indx] = reason
            # Index the full (English+Arabic mixed) normalized name
            _add(narrator_normalize(name), indx)
            # Also index the Arabic-only portion extracted from parentheses
            arabic_name = _extract_arabic_name(name, strip_formulas=False)
            if reason:
                # A placeholder still makes its keys ambiguous, so removing it never promotes another holder.
                placeholder_exact_keys.add(narrator_normalize(name))
                if arabic_name:
                    placeholder_exact_keys.add(narrator_normalize(arabic_name))
            if arabic_name:
                _add(narrator_normalize(arabic_name), indx)
                # Tier 1/2 keys come from the formula-free name; a name that becomes a single bare token only
                # because a formula was stripped is withheld (uniqueness is not identity: 'محمد', 'عبد الرحمن').
                folded_key = narrator_fold_normalize(_extract_arabic_name(name))
                if folded_key:
                    if (folded_key != narrator_fold_normalize(arabic_name)
                            and len(folded_key.split()) == 1):
                        withheld_bare.append(indx)
                    else:
                        folded_index.setdefault(folded_key, set()).add(indx)
                        kunya_folded_index.setdefault(
                            fold_kunya_case_forms(folded_key), set()).add(indx)
                # Collect kunya alias candidates from this Arabic name
                for alias in _extract_alias_segments(arabic_name):
                    alias_norm = narrator_normalize(alias)
                    if alias_norm:
                        alias_candidates.setdefault(alias_norm, set()).add(indx)

    # Remove ambiguous full-name entries, and every key a placeholder holds, from exact_index
    dup_norms |= {key for key in placeholder_exact_keys if key}
    for dn in dup_norms:
        exact_index.pop(dn, None)
    exact_index.folded = folded_index
    exact_index.kunya_folded = kunya_folded_index
    exact_index.exact_ambiguous = set(dup_norms)
    exact_index.withheld_bare_names = withheld_bare
    exact_index.placeholders = placeholders

    # Candidate-only: uniqueness is not identity evidence and cannot complete a chain.
    for alias_norm, indxs in alias_candidates.items():
        block = alias_norm[:4] if len(alias_norm) >= 4 else alias_norm
        for indx in sorted(indxs):
            entry = (indx, alias_norm)
            block_list = blocked_index.setdefault(block, [])
            if entry not in block_list:
                block_list.append(entry)

    return exact_index, blocked_index


def resolve_narrator(surface: str, exact_index: dict, blocked_index: dict):
    """Resolve a surface-form narrator name to a scholar_indx string.

    Only exact registry names may complete a chain, tried in order; the first tier that has the key decides and a
    key shared by several scholars is ambiguous (None):
      0. unique exact match under narrator_normalize (unchanged historical behavior);
      1. unique match of the adopted spelling folds (narrator_fold_normalize) against formula-free registry names;
      2. unique match after the kunya case fold, only for a surface with a nasab or several name components.
    Prefix, containment, and other kunya proposals remain non-resolving audit candidates.
    A plain dict (no tier tables) resolves at tier 0 only.
    """
    norm = narrator_normalize(surface)
    hit = exact_index.get(norm)
    if hit:
        return hit
    folded_index = getattr(exact_index, 'folded', None)
    if folded_index is None or norm in exact_index.exact_ambiguous:
        return None
    placeholders = getattr(exact_index, 'placeholders', {})
    key = narrator_fold_normalize(surface)
    owners = folded_index.get(key)
    if owners:
        return _sole_person(owners, placeholders)
    if kunya_fold_allowed(key):
        owners = exact_index.kunya_folded.get(fold_kunya_case_forms(key))
        if owners:
            return _sole_person(owners, placeholders)
    return None


def _sole_person(owners: set, placeholders: dict):
    """The single owner of a key, unless the key is shared or its owner is a placeholder entry."""
    if len(owners) != 1:
        return None
    owner = next(iter(owners))
    return None if owner in placeholders else owner


def narrator_resolution_candidates(surface: str, blocked_index: dict) -> list:
    """Return deterministic, non-resolving curation candidates."""
    norm = narrator_normalize(surface)
    block = norm[:4] if len(norm) >= 4 else norm
    candidates = blocked_index.get(block, [])
    matches = {
        (str(indx), candidate_norm) for indx, candidate_norm in candidates
        if candidate_norm and (norm.startswith(candidate_norm)
                               or candidate_norm.startswith(norm))
    }
    return [
        {'scholar_indx': indx, 'normalized_name': candidate_norm}
        for indx, candidate_norm in sorted(
            matches, key=lambda item: (item[1], item[0])
        )
    ]


def load_classical_sunni_rows(pure_canon_path: str,
                               exact_index: dict,
                               blocked_index: dict,
                               translation_index: dict,
                               canonical_stats: dict) -> tuple:
    """Ingest the four classical Sunni collections from pure_canon.jsonl.

    Returns:
        (rows, gap_records, stats)
        rows         : list of dicts ready for UNIFIED_COLS
        gap_records  : dict of surface_form -> gap info (for classical_narrator_gap.csv)
        stats        : dict with per-source counts and isnad stats
    """
    if not os.path.exists(pure_canon_path):
        print(f"  ERROR: pure_canon.jsonl not found at {pure_canon_path}", file=sys.stderr)
        sys.exit(1)

    rows = []
    # gap_records: surface_form -> {normalized_form, sources: {src: {hadith_nos, count}}}
    gap_records = {}
    stats = {
        'per_source': {},
        'isnad_attempted': 0,
        'isnad_extracted': 0,
        'isnad_optional_skipped': 0,
        'chain_indx_resolved': 0,
        'chain_indx_total_attempted': 0,
        'unresolved_surface_forms': 0,
    }

    # First-seen tracking per (surface_form, source) for gap CSV.
    first_seen = {}  # surface_form -> hadith_no of first occurrence

    with open(pure_canon_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            arabic_src = obj.get('source', '')
            if arabic_src not in CLASSICAL_SOURCE_MAP:
                continue  # not one of the four target collections

            canonical_src = CLASSICAL_SOURCE_MAP[arabic_src]
            hadith_no = str(obj.get('hadith_no', obj.get('row_no', '')))
            text_ar = obj.get('text_ar', '')
            chain_text = obj.get('chain', '')
            source_record_id = str(obj.get('id') or '').strip()
            translated = translation_index.get(source_record_id, {})
            # A stable id alone is insufficient if an archive was assembled
            # from a different source revision.  Require exact Arabic equality.
            if ((translated.get('text_ar') or '').strip()
                    != (text_ar or '').strip()):
                translated = {}
            if translated.get('source_canonical') != canonical_src:
                translated = {}
            text_en = (translated.get('text_en') or '').strip()

            # Isnad extraction
            sanad_branches = []
            sanad_confidence = 0
            chain_indx = ''

            if canonical_src in ISNAD_OPTIONAL_SOURCES:
                # Shafi'i: matn-only — do NOT extract isnad, leave sanad/chain_indx empty.
                stats['isnad_optional_skipped'] += 1
            else:
                stats['isnad_attempted'] += 1
                isnad_text = chain_text if (chain_text or '').strip() else text_ar
                try:
                    sanad_branches = extract_isnad_branches(isnad_text)
                except IsnadExtractionLimitError:
                    # Mirror canonical_chain_indx telemetry for this preflight path.
                    canonical_stats['rows_attempted'] += 1
                    canonical_stats['rows_extraction_failed'] += 1
                    sanad_branches = []
                if sanad_branches:
                    stats['isnad_extracted'] += 1
                    sanad_confidence = 2 if chain_text.strip() else 1
                    surface_count = sum(len(branch) for branch in sanad_branches)
                    stats['chain_indx_total_attempted'] += surface_count

                    def record_gap(error):
                        from classify_attribution import _norm as _nc  # noqa: PLC0415
                        surface = error.surface
                        if surface not in gap_records:
                            gap_records[surface] = {
                                'normalized_form': _nc(surface),
                                'sources': {},
                                'first_seen_at': hadith_no,
                            }
                        src_entry = gap_records[surface]['sources']
                        if canonical_src not in src_entry:
                            src_entry[canonical_src] = {
                                'count': 0,
                                'first_hadith_no': hadith_no,
                            }
                        src_entry[canonical_src]['count'] += 1

                    resolver = lambda surface: resolve_narrator(
                        surface, exact_index, blocked_index
                    )
                    chain_indx = canonical_chain_indx(
                        isnad_text,
                        resolver,
                        canonical_stats,
                        on_resolution_failure=record_gap,
                    )
                    if chain_indx:
                        stats['chain_indx_resolved'] += surface_count

            row = {
                'source': canonical_src,
                'tradition': 'Sunni',
                'volume': '',
                'chapter_no': '',
                'hadith_no': hadith_no,
                'chapter': '',
                'category': '',
                'chain_indx': chain_indx,
                'text_ar': text_ar,
                'text_en': text_en,
                'sanad': ' | '.join(
                    ', '.join(branch) for branch in sanad_branches
                ),
                'sanad_confidence': sanad_confidence,
                'matn_ar': '',
                'matn_en': '',
                'school': '',
                'chain_type': '',
                'grade_tradition': 'Sunni',
                'grade_source': obj.get('ruling', ''),
                'grade_value': obj.get('ruling', ''),
                'gradings_full': '',
                'url': '',
                'page_ref': '',
                'hadith_id': source_record_id,
                'record_id': f"pure-canon:{source_record_id}",
                'source_record_id': source_record_id,
                'provenance_source': 'archive/sheikahmad-pure-canon/pure_canon.jsonl',
                'translation_status': _translation_status(text_en),
                'translation_source': translated.get('translation_source', ''),
                'translation_model': '',
                'translation_review_status': translated.get(
                    'translation_review_status', ''),
            }
            rows.append(row)
            stats['per_source'][canonical_src] = stats['per_source'].get(canonical_src, 0) + 1

    stats['unresolved_surface_forms'] = len(gap_records)
    return rows, gap_records, stats


def write_classical_narrator_gap(gap_records: dict, gap_path: str):
    """Write the unresolved-narrator gap CSV for handoff to narrator_enrichment track.

    Columns: surface_form, normalized_form, source, hadith_no, first_seen_at, count
    One row per (surface_form, source) combination.
    """
    from classify_attribution import _norm  # noqa: PLC0415
    gap_rows = []
    for surface, info in sorted(gap_records.items()):
        norm_form = info['normalized_form']
        first_seen = info['first_seen_at']
        for src, src_info in sorted(info['sources'].items()):
            gap_rows.append({
                'surface_form': surface,
                'normalized_form': norm_form,
                'source': src,
                'hadith_no': src_info.get('first_hadith_no', ''),
                'first_seen_at': first_seen,
                'count': src_info['count'],
            })
    gap_cols = ['surface_form', 'normalized_form', 'source', 'hadith_no', 'first_seen_at', 'count']
    tmp = gap_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=gap_cols, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(gap_rows)
    shutil.move(tmp, gap_path)
    print(f"  Written: {gap_path} ({len(gap_rows):,} gap rows, "
          f"{len(gap_records):,} distinct surface forms)")


def backup_unified_csv(unified_path: str):
    """Backup all_hadiths_unified.csv before overwriting (per feedback_no_delete_backup)."""
    if not os.path.exists(unified_path):
        return
    utc_date = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H%M%SZ')
    bak_path = unified_path + f'.bak-{utc_date}'
    shutil.copy2(unified_path, bak_path)
    size_mb = os.path.getsize(bak_path) / (1024 * 1024)
    print(f"  Backup: {bak_path} ({size_mb:.1f} MB)")


def print_coverage_report(master: list, classical_stats: dict, gap_count: int):
    """Print per-tradition, per-source, and isnad coverage report to stdout."""
    print("\n" + "=" * 60)
    print("COVERAGE REPORT")
    print("=" * 60)

    tradition_counts = {}
    source_counts = {}
    for row in master:
        t = row.get('tradition', '?')
        s = row.get('source', '?')
        tradition_counts[t] = tradition_counts.get(t, 0) + 1
        source_counts[s] = source_counts.get(s, 0) + 1

    print(f"\nTotal records: {len(master):,}")
    print("\nPer-tradition record counts:")
    for t, c in sorted(tradition_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c:,}")

    print("\nPer-source record counts (Sunni classical):")
    classical_sources = list(CLASSICAL_SOURCE_MAP.values())
    for src in classical_sources:
        print(f"  {src}: {source_counts.get(src, 0):,}")

    if classical_stats:
        attempted = classical_stats['isnad_attempted']
        extracted = classical_stats['isnad_extracted']
        optional = classical_stats['isnad_optional_skipped']
        rate = (100 * extracted // attempted) if attempted > 0 else 0
        resolved = classical_stats['chain_indx_resolved']
        total_names = classical_stats['chain_indx_total_attempted']
        res_rate = (100 * resolved // total_names) if total_names > 0 else 0
        print(f"\nSunni classical sanad extraction:")
        print(f"  Attempted: {attempted:,} (Shafi'i skipped: {optional:,})")
        print(f"  Extracted: {extracted:,} ({rate}%)")
        print(f"  Narrator names attempted for resolution: {total_names:,}")
        print(f"  Resolved to chain_indx: {resolved:,} ({res_rate}%)")
        print(f"  Unresolved narrator gap count: {gap_count:,} distinct surface forms")


def build_curation_backlog(master: list) -> list:
    """Build row-addressable translation/content work only."""
    backlog = []
    collision_ids = source_translation_collision_ids(master)
    for row in master:
        record_id = (row.get('record_id') or '').strip()
        issue = translation_issue(row.get('text_en', ''), row.get('text_ar', ''))
        if issue:
            backlog.append({
                'record_id': record_id,
                'source_record_id': row.get('source_record_id', ''),
                'source': row.get('source', ''),
                'tradition': row.get('tradition', ''),
                'hadith_no': row.get('hadith_no', ''),
                'issue': f'translation:{issue}',
                'text_ar': row.get('text_ar', ''),
                'current_text_en': row.get('text_en', ''),
                'provenance_source': row.get('provenance_source', ''),
            })
        if record_id in collision_ids:
            backlog.append({
                'record_id': record_id,
                'source_record_id': row.get('source_record_id', ''),
                'source': row.get('source', ''),
                'tradition': row.get('tradition', ''),
                'hadith_no': row.get('hadith_no', ''),
                'issue': 'translation:source_identity_collision',
                'text_ar': row.get('text_ar', ''),
                'current_text_en': row.get('text_en', ''),
                'provenance_source': row.get('provenance_source', ''),
            })
        if not (row.get('text_ar') or '').strip():
            backlog.append({
                'record_id': record_id,
                'source_record_id': row.get('source_record_id', ''),
                'source': row.get('source', ''),
                'tradition': row.get('tradition', ''),
                'hadith_no': row.get('hadith_no', ''),
                'issue': 'source:missing_arabic',
                'text_ar': '',
                'current_text_en': row.get('text_en', ''),
                'provenance_source': row.get('provenance_source', ''),
            })
    return backlog


def _manifest_input_paths(sunni_input_path: str, imami_input_path: str,
                          rebuilt_imami: bool) -> list:
    paths = [
        os.path.abspath(__file__),
        os.path.join(os.path.dirname(BASE_DIR), 'classify_attribution.py'),
        os.path.join(SHIA_DIR, 'build_csv.py'),
        UNIFIED_ISNAD_EXTRACTOR,
        UNIFIED_ISNAD_HELPERS,
        SUNNI_ISNAD_SIDECAR,
        PURE_CANON_JSONL,
        CLASSICAL_TRANSLATIONS_CSV,
        CLASSICAL_TRANSLATIONS_CLEAN_JSONL,
        TRANSLATION_OVERRIDES_JSONL,
        CURATION_DISPOSITIONS_JSONL,
        sunni_input_path,
        os.path.join(IBADI_DIR, 'parsed_hadiths.json'),
        os.path.join(ZAYDI_DIR, 'parsed_hadiths.json'),
        os.path.join(RIDA_DIR, 'parsed_hadiths.json'),
        ALL_RAWIS_CSV,
        SOURCE_REGISTRY_TS,
        IMAMI_SOURCE_WORK_REGISTRY_JSON,
        EVIDENCE_CURATION_SCHEMA_JSON,
        EVIDENCE_CURATION_BUNDLE_JSON,
        EVIDENCE_CURATION_MANIFEST_JSON,
    ]
    if rebuilt_imami:
        books_dir = os.path.join(SHIA_DIR, 'v2_books')
        paths.extend(
            os.path.join(books_dir, name)
            for name in sorted(os.listdir(books_dir))
            if name.endswith('.json')
        )
    else:
        paths.append(imami_input_path)
    return paths


def _print_gate_failures(manifest: dict):
    print("\nFULL-LOAD CURATION GATE FAILED; canonical CSV/GZIP files were not changed.")
    for name, gate in manifest.get('full_load_gates', {}).items():
        if gate.get('passed'):
            continue
        nonzero = {
            key: value for key, value in gate.get('counts', {}).items()
            if value
        }
        print(f"  {name}: {nonzero or 'failed'}")
    print("  Resolve the manifest gate evidence, then rerun. "
          "Use --allow-incomplete-curation only for a non-release build.")


def main():
    parser = argparse.ArgumentParser(description='Regenerate the unified hadith dataset')
    parser.add_argument('--no-shia', action='store_true',
                        help=(
                            'Skip Thaqalayn rebuild and reuse the exact tracked '
                            'Shia gzip (or --shia-input)'
                        ))
    parser.add_argument(
        '--shia-input',
        help=(
            'Exact authoritative CSV/GZIP asset to reuse with --no-shia; '
            'paired plain/GZIP auto-resolution is intentionally bypassed'
        ),
    )
    parser.add_argument('--include-zaydi', action='store_true',
                        help='(kept for compat; Zaydi is always included now)')
    parser.add_argument('--no-classical', action='store_true',
                        help='Skip classical Sunni ingestion (Ahmad/Darimi/Shafi\'i/Muwatta)')
    parser.add_argument(
        '--allow-incomplete-curation', action='store_true',
        help=(
            'Write a non-ready build only to development/incomplete-curation; '
            'canonical publication remains blocked'
        ))
    args = parser.parse_args()
    if args.shia_input and not args.no_shia:
        parser.error('--shia-input requires --no-shia')

    print("=" * 60)
    print("Building the unified hadith dataset (single source of truth)")
    print("=" * 60)

    sunni_isnad = load_sunni_isnad_sidecar()
    print(f"\nSunni isnad sidecar: {len(sunni_isnad):,} rows "
          f"({'present' if sunni_isnad else 'MISSING — run extract_isnad_sunni.py'})")
    print("  The sidecar supplies display sanad/matn only; Arabic text controls chain_indx.")

    print("\nLoading the shared narrator resolver for every corpus path...")
    exact_index, blocked_index = build_narrator_index(ALL_RAWIS_CSV)
    if not exact_index or not blocked_index:
        raise RuntimeError(
            "Canonical rebuild requires non-empty narrator resolver indices"
        )
    print(f"  Narrator index: {len(exact_index):,} exact entries, "
          f"{len(blocked_index):,} blocks")
    canonical_stats = new_canonical_chain_stats()

    print("\n1. Sunni K6 (Kutub al-Sittah)...")
    sunni_input_path = resolve_csv_input_path(
        os.path.join(BASE_DIR, 'all_hadiths_clean.csv')
    )
    sunni = load_sunni_rows(sunni_input_path)
    print(f"  {len(sunni):,}")

    classical_rows = []
    classical_stats = {}
    gap_records = {}

    if not args.no_classical:
        print("\n2. Sunni Classical (Ahmad / Darimi / Shafi'i / Muwatta)...")
        print("   Loading completed classical translations by source record id...")
        classical_translations = load_classical_translation_index()
        completed = sum(
            1 for value in classical_translations.values()
            if (value.get('text_en') or '').strip()
        )
        print(f"   Translation index: {len(classical_translations):,} rows, "
              f"{completed:,} non-empty")
        classical_rows, gap_records, classical_stats = load_classical_sunni_rows(
            PURE_CANON_JSONL, exact_index, blocked_index,
            classical_translations, canonical_stats)
        for src, cnt in sorted(classical_stats['per_source'].items()):
            print(f"    {src}: {cnt:,}")
        print(f"  Total classical: {len(classical_rows):,}")
    else:
        print("\n2. Sunni Classical — SKIPPED (--no-classical)")

    print("\n3. Ibadi (OpenITI Musnad al-Rabi)...")
    ibadi = load_openiti_hadiths(IBADI_DIR)
    print(f"  {len(ibadi):,}")

    print("\n4. Zaydi (OpenITI Musnad Zayd)...")
    zaydi = load_openiti_hadiths(ZAYDI_DIR)
    print(f"  {len(zaydi):,}")

    return run_with_stage_dir(
        lambda stage_dir: _build_staged_dataset(
            stage_dir,
            args,
            sunni_isnad,
            sunni_input_path,
            sunni,
            classical_rows,
            classical_stats,
            gap_records,
            ibadi,
            zaydi,
            exact_index,
            blocked_index,
            canonical_stats,
        )
    )


def _build_staged_dataset(stage_dir: str, args, sunni_isnad: dict,
                          sunni_input_path: str, sunni: list,
                          classical_rows: list, classical_stats: dict,
                          gap_records: dict, ibadi: list, zaydi: list,
                          exact_index: dict, blocked_index: dict,
                          canonical_stats: dict):
    resolver = lambda surface: resolve_narrator(
        surface, exact_index, blocked_index
    )
    print("\n5. Imami (Thaqalayn)...")
    staged_imami_source = os.path.join(stage_dir, 'thaqalayn-source.csv')
    rebuilt_imami = (
        rebuild_shia_csv(staged_imami_source) if not args.no_shia else False
    )
    shia_path = os.path.join(BASE_DIR, 'all_hadiths_shia.csv')
    if rebuilt_imami:
        imami_input_path = staged_imami_source
        authoritative_input = False
    elif args.no_shia:
        imami_input_path = resolve_no_shia_input(
            shia_path, args.shia_input
        )
        authoritative_input = True
        print(f"  Reusing exact authoritative Shia input: {imami_input_path}")
    else:
        imami_input_path = resolve_csv_input_path(shia_path)
        authoritative_input = False
    imami = reconcile_imami_source_works(apply_thaqalayn_identities(
        load_imami_rows(
            imami_input_path, authoritative_input=authoritative_input
        )
    ))
    print(f"  {len(imami):,}")

    rida = load_openiti_hadiths(RIDA_DIR) if os.path.isdir(RIDA_DIR) else []
    print(f"\n5b. Rida (Sahifat al-Imam al-Rida, Imami-family): {len(rida):,}")

    unified_path = os.path.join(BASE_DIR, 'all_hadiths_unified.csv')

    # --- Assemble the single master, fresh sequential ids ---
    print("\n6. Assembling and validating all_hadiths_unified.csv (master)...")
    master = []
    next_id = 0
    for r in sunni:
        next_id += 1
        r = dict(r)
        legacy_row_id = str(r.get('id') or next_id).strip()
        r['source'] = (r.get('source') or '').strip()
        r['source_record_id'] = r.get('source_record_id') or legacy_row_id
        r['record_id'] = r.get('record_id') or f"k6:{legacy_row_id}"
        r['provenance_source'] = (
            r.get('provenance_source')
            or 'all_hadiths_clean.csv.gz:k6_snapshot'
        )
        apply_canonical_chain(r, resolver, canonical_stats)
        if (r.get('text_en') or '').strip():
            r['translation_source'] = (
                r.get('translation_source') or 'legacy_k6_source_export'
            )
            r['translation_review_status'] = (
                r.get('translation_review_status') or 'source_status_unknown'
            )
        r['id'] = next_id
        master.append(_enrich(r, sunni_isnad))
    for row in classical_rows:
        next_id += 1
        row['id'] = next_id
        master.append(_enrich(dict(row), sunni_isnad))
    for h in imami:
        next_id += 1
        h = dict(h)
        h['provenance_source'] = (
            h.get('provenance_source') or 'shia-hadith/v2_books'
        )
        if (h.get('text_en') or '').strip():
            h['translation_source'] = (
                h.get('translation_source') or 'Thaqalayn API V2'
            )
            h['translation_review_status'] = (
                h.get('translation_review_status') or 'source_provided'
            )
        apply_canonical_chain(h, resolver, canonical_stats)
        h['id'] = next_id
        master.append(_enrich(h, sunni_isnad))
    for coll in (ibadi, zaydi, rida):
        for h in coll:
            next_id += 1
            master.append(_enrich(
                openiti_to_shia_row(
                    h, next_id, resolver, canonical_stats
                ),
                sunni_isnad,
            ))

    translation_overrides = load_translation_overrides()
    applied_overrides = apply_translation_overrides(master, translation_overrides)
    print(f"  Curated translation overrides applied: {applied_overrides:,}")
    print(f"  Canonical isnad row telemetry: {canonical_stats}")

    curation_backlog = build_curation_backlog(master)

    backlog_path = os.path.join(BASE_DIR, 'curation_backlog.csv')
    manifest_path = os.path.join(BASE_DIR, 'curation_manifest.json')
    candidate_manifest_path = os.path.join(
        BASE_DIR, 'curation_candidate_manifest.json')
    clean_path = os.path.join(BASE_DIR, 'all_hadiths_clean.csv')
    staged_unified = os.path.join(stage_dir, 'all_hadiths_unified.csv')
    staged_clean = os.path.join(stage_dir, 'all_hadiths_clean.csv')
    staged_shia = os.path.join(stage_dir, 'all_hadiths_shia.csv')
    staged_backlog = os.path.join(stage_dir, 'curation_backlog.csv')
    staged_manifest = os.path.join(stage_dir, 'curation_manifest.json')
    staged_candidate_manifest = os.path.join(
        stage_dir, 'curation_candidate_manifest.json')

    print("\n7. Staging master and deterministic gzip companion...")
    write_csv(staged_unified, UNIFIED_COLS, master)
    compress_csv(staged_unified)

    # --- Classical narrator gap CSV ---
    staged_gap_path = None
    if gap_records:
        print("\n8. Staging classical narrator gap CSV...")
        staged_gap_path = os.path.join(stage_dir, 'classical_narrator_gap.csv')
        write_classical_narrator_gap(gap_records, staged_gap_path)
    elif not args.no_classical:
        print("\n8. No unresolved narrators — classical_narrator_gap.csv not written.")

    # --- Derived views (column projections of the master) ---
    print("\n9. Deriving clean.csv (Sunni+Ibadi+Zaydi) and "
          "shia.csv (Imami+Rida+Ibadi+Zaydi)...")
    clean = [r for r in master if r['tradition'] in ('Sunni', 'Ibadi', 'Zaydi')]
    shia = [r for r in master if r['tradition'] in ('Imami', 'Ibadi', 'Zaydi')]
    write_csv(staged_clean, CLEAN_COLS, _project(clean, CLEAN_COLS))
    write_csv(staged_shia, SHIA_COLS, _project(shia, SHIA_COLS))
    compress_csv(staged_clean)
    compress_csv(staged_shia)

    # --- Verify ---
    print("\n" + "=" * 60)
    print("Staged verification")
    print("=" * 60)
    verify(staged_unified)
    verify(staged_clean)
    verify(staged_shia)

    # Attribution + sanad coverage on the master
    lvl, withsan = {}, 0
    with open(staged_unified, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            lvl[row['narration_level']] = lvl.get(row['narration_level'], 0) + 1
            if (row.get('sanad') or '').strip():
                withsan += 1
    print(f"\n  Attribution levels: {lvl}")
    print(f"  Rows with structured sanad: {withsan:,} / {len(master):,}")

    # --- Coverage report (FR-0.9 §6) ---
    print_coverage_report(master, classical_stats, len(gap_records))

    # --- Exit criteria check ---
    total = len(master)
    expected_min = 99235
    expected_max = 99335
    if not args.no_classical and not (expected_min <= total <= expected_max):
        print(f"\nWARNING: total record count {total:,} is outside expected range "
              f"{expected_min:,}–{expected_max:,}. Investigate before proceeding.")
    else:
        print(f"\nRecord count check: {total:,} (target ~99,285) — OK")

    try:
        source_registry = load_source_work_registry()
    except (OSError, ValueError) as error:
        print(f"  WARNING: source registry unavailable: {error}")
        source_registry = None
    try:
        narrator_ids = load_narrator_ids()
    except (OSError, ValueError) as error:
        print(f"  WARNING: narrator registry unavailable: {error}")
        narrator_ids = None

    write_translation_backlog(curation_backlog, staged_backlog)
    manifest = write_curation_manifest(
        master,
        curation_backlog,
        staged_manifest,
        source_registry=source_registry,
        narrator_ids=narrator_ids,
        input_paths=_manifest_input_paths(
            sunni_input_path, imami_input_path, rebuilt_imami
        ),
        expected_record_range=(expected_min, expected_max),
    )

    if not manifest['ready_for_full_load']:
        if not args.allow_incomplete_curation:
            outcome = publish_failed_candidate(
                staged_backlog,
                backlog_path,
                staged_manifest,
                candidate_manifest_path,
                manifest_path,
                unified_path,
            )
            print(f"  Candidate manifest outcome: {outcome}")
            _print_gate_failures(manifest)
            return 2
        development_targets = publish_incomplete_development_artifacts(
            staged_unified,
            staged_clean,
            staged_shia,
            staged_backlog,
            staged_manifest,
            staged_gap_path=staged_gap_path,
        )
        print("\nDEVELOPMENT OVERRIDE: non-ready artifacts were isolated under "
              f"{os.path.dirname(development_targets['manifest'])}.")
        print("  Canonical CSV, GZIP, backlog, candidate manifest, and active "
              "manifest files were not changed.")
        return 0

    bind_published_dataset_manifest(
        staged_manifest, staged_unified, unified_path
    )

    shutil.copyfile(staged_manifest, staged_candidate_manifest)

    print("\n10. Publishing staged files (manifest commit is last)...")
    publication = [
        (staged_unified, unified_path),
        (staged_unified + '.gz', unified_path + '.gz'),
        (staged_clean, clean_path),
        (staged_clean + '.gz', clean_path + '.gz'),
        (staged_shia, shia_path),
        (staged_shia + '.gz', shia_path + '.gz'),
    ]
    if staged_gap_path:
        publication.append((staged_gap_path, CLASSICAL_NARRATOR_GAP_CSV))
    publication.extend([
        (staged_backlog, backlog_path),
        (staged_candidate_manifest, candidate_manifest_path),
        (staged_manifest, manifest_path),
    ])
    publish_canonical_dataset(publication, manifest_path, unified_path)
    print("\nDone!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
