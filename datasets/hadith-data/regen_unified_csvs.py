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
import csv
import datetime
import gzip
import json
import os
import re
import shutil
import subprocess
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
csv.field_size_limit(10 * 1024 * 1024)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IBADI_DIR = os.path.join(BASE_DIR, 'ibadi-hadith')
ZAYDI_DIR = os.path.join(BASE_DIR, 'zaydi-hadith')
RIDA_DIR = os.path.join(BASE_DIR, 'rida-hadith')
SHIA_DIR = os.path.join(BASE_DIR, 'shia-hadith')

# classify_attribution.py lives one directory up (datasets/).
sys.path.insert(0, os.path.dirname(BASE_DIR))
from classify_attribution import classify as classify_attribution  # noqa: E402

SUNNI_ISNAD_SIDECAR = os.path.join(BASE_DIR, 'sunni_isnad.jsonl')

# ─── Classical Sunni (pure_canon.jsonl) ────────────────────────────────────
# Canonical path (archive). The tooling note says to pick the canonical
# classical file; pure_canon.jsonl is the definitive one.
PURE_CANON_JSONL = os.path.join(
    BASE_DIR, 'archive', 'sheikahmad-pure-canon', 'pure_canon.jsonl')

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
    "id", "hadith_id", "source", "tradition", "volume", "chapter_no",
    "hadith_no", "chapter", "category", "chain_indx", "text_ar", "text_en",
    "sanad", "sanad_confidence", "matn_ar", "matn_en", "school", "chain_type",
    "attributed_to", "narration_level",
    "grade_tradition", "grade_source", "grade_value",
    "gradings_full", "url", "page_ref",
]

# Derived views (column projections of the master, for backward compat).
CLEAN_COLS = [
    "id", "hadith_id", "source", "tradition", "chapter_no", "hadith_no",
    "chapter", "chain_indx", "text_ar", "text_en",
    "sanad", "school", "chain_type", "attributed_to", "narration_level",
]

SHIA_COLS = [
    "id", "hadith_id", "source", "tradition", "volume", "chapter_no",
    "hadith_no", "chapter", "category", "chain_indx", "text_ar", "text_en",
    "sanad", "matn_ar", "matn_en", "school", "chain_type",
    "attributed_to", "narration_level",
    "grade_tradition", "grade_source", "grade_value",
    "gradings_full", "url", "page_ref",
]


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


def load_openiti_hadiths(collection_dir: str) -> list:
    """Load hadiths from an OpenITI-parsed JSON file."""
    path = os.path.join(collection_dir, 'parsed_hadiths.json')
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('hadiths', [])


def rebuild_shia_csv():
    """Rebuild all_hadiths_shia.csv from Thaqalayn JSONs."""
    print("  Rebuilding Imami data from Thaqalayn JSONs...")
    build_csv_path = os.path.join(SHIA_DIR, 'build_csv.py')
    if not os.path.exists(build_csv_path):
        print("  WARNING: shia-hadith/build_csv.py not found, using existing CSV")
        return
    result = subprocess.run(
        [sys.executable, build_csv_path],
        cwd=SHIA_DIR, capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.stdout.strip():
        print(f"  {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        sys.exit(1)


def load_sunni_rows() -> list:
    """Load K6 (Kutub al-Sittah) Sunni rows from all_hadiths_clean.csv.

    Filters strictly to the six canonical K6 source names so that classical
    rows added by this script in a previous run are NOT re-ingested (the
    all_hadiths_clean.csv is this script's own output and contains all Sunni
    rows after the first run).
    """
    csv_path = os.path.join(BASE_DIR, 'all_hadiths_clean.csv')
    rows = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = (row.get('source') or '').strip()
            # Accept only K6 source names — reject classical Sunni sources.
            if src in SOURCE_TO_TRADITION or row.get('source') in K6_CANONICAL_SOURCES:
                row['tradition'] = 'Sunni'
                rows.append(row)
    return rows


def load_imami_rows() -> list:
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

    csv_path = os.path.join(BASE_DIR, 'all_hadiths_shia.csv')
    if not os.path.exists(csv_path):
        # Try decompressing
        gz_path = csv_path + '.gz'
        if os.path.exists(gz_path):
            print("  Decompressing all_hadiths_shia.csv.gz...")
            with gzip.open(gz_path, 'rb') as gz, open(csv_path, 'wb') as out:
                shutil.copyfileobj(gz, out)
        else:
            print("  WARNING: all_hadiths_shia.csv not found")
            return []
    rows = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
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


def openiti_to_clean_row(h: dict, row_id: int) -> dict:
    """Convert an OpenITI-parsed hadith to clean CSV row."""
    return {
        'id': row_id,
        'hadith_id': h.get('hadith_no', ''),
        'source': h['source'],
        'tradition': h['tradition'],
        'chapter_no': h.get('bab_no', h.get('kitab_no', '')),
        'hadith_no': h.get('hadith_no', ''),
        'chapter': h.get('bab', h.get('kitab', '')),
        'chain_indx': '',
        'text_ar': h['text_ar'],
        'text_en': h.get('text_en', ''),
        'sanad': _format_sanad(h),
        'school': h.get('school', ''),
        'chain_type': h.get('chain_type', ''),
    }


def openiti_to_shia_row(h: dict, row_id: int) -> dict:
    """Convert an OpenITI-parsed hadith to shia/extended CSV row."""
    return {
        'id': row_id,
        'hadith_id': h.get('hadith_no', ''),
        'source': h['source'],
        'tradition': h['tradition'],
        'volume': 1,
        'chapter_no': h.get('bab_no', h.get('kitab_no', '')),
        'hadith_no': h.get('hadith_no', ''),
        'chapter': h.get('bab', h.get('kitab', '')),
        'category': h.get('kitab', h.get('bab', '')),
        'chain_indx': '',
        'text_ar': h['text_ar'],
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
    """Gzip a CSV file alongside the original."""
    gz_path = path + '.gz'
    with open(path, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    size_mb = os.path.getsize(gz_path) / (1024 * 1024)
    print(f"  Compressed: {gz_path} ({size_mb:.1f} MB)")


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


def _extract_arabic_name(name_field: str) -> str:
    """Extract the Arabic portion from an all_rawis name field.

    all_rawis names follow the pattern: 'English Name ( Arabic Name ( grade )'
    e.g. 'Abu Bakr As-Siddique ( أبو بكر الصديق ( رضي الله عنه'
    Extract the first parenthesised block that contains Arabic letters,
    then strip trailing parenthetical grade/honorific info.
    """
    # Try to find Arabic text in parentheses
    for m in _ARABIC_IN_PARENS.finditer(name_field):
        candidate = m.group(1).strip()
        # If it has enough Arabic chars and isn't a grade/honorific only
        arabic_chars = len(_ARABIC_RANGE.findall(candidate))
        if arabic_chars >= 3:
            # Strip trailing honorifics
            candidate = _CLASSICAL_HONORIFIC.sub("", candidate).strip()
            # Strip nested paren leftovers
            candidate = re.sub(r'\(.*', '', candidate).strip()
            if arabic_chars >= 3:
                return candidate
    # Fallback: take Arabic chars directly from the full name
    arabic_parts = ''.join(c for c in name_field if _ARABIC_RANGE.match(c) or c == ' ')
    return arabic_parts.strip()


def build_narrator_index(all_rawis_path: str):
    """Load all_rawis.csv and return two lookup dicts:
        exact_index  : normalized_arabic_name → scholar_indx  (unique only)
        blocked_index: first 4 chars of normalized → [(scholar_indx, norm_name)]

    The all_rawis `name` field is English with Arabic in parentheses.
    Both the full normalized name AND the extracted Arabic portion are indexed
    so that pure-Arabic surface forms from pure_canon chains can be resolved.

    This is the Tier-1 (exact) and Tier-2 (blocked) resolver from FR-0.9.
    Intentionally side-effect-free so workstream D can import it.

    Proposed reusable module: datasets/narrator_resolver.py
    Signature:
        build_narrator_index(all_rawis_path: str)
            -> tuple[dict[str,str], dict[str,list[tuple[str,str]]]]
        resolve_narrator(surface: str, exact_index, blocked_index)
            -> str | None   # returns scholar_indx string or None
    """
    from classify_attribution import _norm  # noqa: PLC0415

    exact_index = {}    # norm_name -> scholar_indx
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

    with open(all_rawis_path, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            indx = row.get('scholar_indx', '').strip()
            name = row.get('name', '').strip()
            if not indx or not name:
                continue
            # Index the full (English+Arabic mixed) normalized name
            _add(_norm(name), indx)
            # Also index the Arabic-only portion extracted from parentheses
            arabic_name = _extract_arabic_name(name)
            if arabic_name:
                _add(_norm(arabic_name), indx)

    # Remove ambiguous entries from exact_index
    for dn in dup_norms:
        exact_index.pop(dn, None)

    return exact_index, blocked_index


def resolve_narrator(surface: str, exact_index: dict, blocked_index: dict):
    """Resolve a surface-form narrator name to a scholar_indx string.

    Tier 1: exact match on normalized form.
    Tier 2: blocked match — take the unique candidate in the block whose
            normalized form is a prefix/suffix of the query (conservative).
    Returns scholar_indx string on success, None on failure/ambiguity.
    """
    from classify_attribution import _norm  # noqa: PLC0415
    norm = _norm(surface)
    # Tier 1
    if norm in exact_index:
        return exact_index[norm]
    # Tier 2: block lookup
    block = norm[:4] if len(norm) >= 4 else norm
    candidates = blocked_index.get(block, [])
    if len(candidates) == 1:
        return candidates[0][0]
    # Narrow by containment: check if query norm starts with or contains
    # the candidate's normalized name (handles kunya/nasab prefix matches).
    matches = [c for c in candidates
               if c[1] and (norm.startswith(c[1]) or c[1].startswith(norm))]
    if len(matches) == 1:
        return matches[0][0]
    return None


def load_classical_sunni_rows(pure_canon_path: str,
                               exact_index: dict,
                               blocked_index: dict) -> tuple:
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

            # Isnad extraction
            sanad_list = []
            sanad_confidence = 0
            chain_indx = ''

            if canonical_src in ISNAD_OPTIONAL_SOURCES:
                # Shafi'i: matn-only — do NOT extract isnad, leave sanad/chain_indx empty.
                stats['isnad_optional_skipped'] += 1
            else:
                stats['isnad_attempted'] += 1
                sanad_list = extract_classical_isnad(chain_text)
                if sanad_list:
                    stats['isnad_extracted'] += 1
                    sanad_confidence = 2 if chain_text.strip() else 1

                    # Resolver: map sanad surface forms → chain_indx
                    resolved_indxs = []
                    for surface in sanad_list:
                        stats['chain_indx_total_attempted'] += 1
                        indx = resolve_narrator(surface, exact_index, blocked_index)
                        if indx:
                            resolved_indxs.append(indx)
                            stats['chain_indx_resolved'] += 1
                        else:
                            # Track gap
                            from classify_attribution import _norm as _nc  # noqa: PLC0415
                            norm_form = _nc(surface)
                            if surface not in gap_records:
                                gap_records[surface] = {
                                    'normalized_form': norm_form,
                                    'sources': {},
                                    'first_seen_at': hadith_no,
                                }
                            src_entry = gap_records[surface]['sources']
                            if canonical_src not in src_entry:
                                src_entry[canonical_src] = {'count': 0, 'first_hadith_no': hadith_no}
                            src_entry[canonical_src]['count'] += 1

                    chain_indx = ','.join(resolved_indxs) if resolved_indxs else ''

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
                'text_en': '',
                'sanad': ', '.join(sanad_list) if sanad_list else '',
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
                'hadith_id': hadith_no,
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


def main():
    parser = argparse.ArgumentParser(description='Regenerate the unified hadith dataset')
    parser.add_argument('--no-shia', action='store_true',
                        help='Skip Thaqalayn rebuild, reuse existing Imami data')
    parser.add_argument('--include-zaydi', action='store_true',
                        help='(kept for compat; Zaydi is always included now)')
    parser.add_argument('--no-classical', action='store_true',
                        help='Skip classical Sunni ingestion (Ahmad/Darimi/Shafi\'i/Muwatta)')
    args = parser.parse_args()

    print("=" * 60)
    print("Building the unified hadith dataset (single source of truth)")
    print("=" * 60)

    sunni_isnad = load_sunni_isnad_sidecar()
    print(f"\nSunni isnad sidecar: {len(sunni_isnad):,} rows "
          f"({'present' if sunni_isnad else 'MISSING — run extract_isnad_sunni.py'})")

    print("\n1. Sunni K6 (Kutub al-Sittah)...")
    sunni = load_sunni_rows()
    print(f"  {len(sunni):,}")

    classical_rows = []
    classical_stats = {}
    gap_records = {}

    if not args.no_classical:
        print("\n2. Sunni Classical (Ahmad / Darimi / Shafi'i / Muwatta)...")
        print("   Loading narrator index from all_rawis.csv...")
        exact_index, blocked_index = build_narrator_index(ALL_RAWIS_CSV)
        print(f"   Narrator index: {len(exact_index):,} exact entries, "
              f"{len(blocked_index):,} blocks")
        classical_rows, gap_records, classical_stats = load_classical_sunni_rows(
            PURE_CANON_JSONL, exact_index, blocked_index)
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

    print("\n5. Imami (Thaqalayn)...")
    if not args.no_shia:
        rebuild_shia_csv()
    imami = load_imami_rows()
    print(f"  {len(imami):,}")

    rida = load_openiti_hadiths(RIDA_DIR) if os.path.isdir(RIDA_DIR) else []
    print(f"\n5b. Rida (Sahifat al-Imam al-Rida, Imami-family): {len(rida):,}")

    # --- Backup before overwriting (per feedback_no_delete_backup) ---
    unified_path = os.path.join(BASE_DIR, 'all_hadiths_unified.csv')
    print(f"\n6. Backing up existing unified CSV...")
    backup_unified_csv(unified_path)

    # --- Assemble the single master, fresh sequential ids ---
    print("\n7. Assembling all_hadiths_unified.csv (master)...")
    master = []
    next_id = 0
    for r in sunni:
        next_id += 1
        r['id'] = next_id
        master.append(_enrich(dict(r), sunni_isnad))
    for row in classical_rows:
        next_id += 1
        row['id'] = next_id
        master.append(_enrich(dict(row), sunni_isnad))
    for h in imami:
        next_id += 1
        h['id'] = next_id
        master.append(_enrich(dict(h), sunni_isnad))
    for coll in (ibadi, zaydi, rida):
        for h in coll:
            next_id += 1
            master.append(_enrich(openiti_to_shia_row(h, next_id), sunni_isnad))

    write_csv(unified_path, UNIFIED_COLS, master)
    compress_csv(unified_path)

    # --- Classical narrator gap CSV ---
    if gap_records:
        print("\n8. Writing classical narrator gap CSV...")
        write_classical_narrator_gap(gap_records, CLASSICAL_NARRATOR_GAP_CSV)
    elif not args.no_classical:
        print("\n8. No unresolved narrators — classical_narrator_gap.csv not written.")

    # --- Derived views (column projections of the master) ---
    print("\n9. Deriving clean.csv (Sunni+Ibadi+Zaydi) and "
          "shia.csv (Imami+Rida+Ibadi+Zaydi)...")
    clean = [r for r in master if r['tradition'] in ('Sunni', 'Ibadi', 'Zaydi')]
    shia = [r for r in master if r['tradition'] in ('Imami', 'Ibadi', 'Zaydi')]
    write_csv(os.path.join(BASE_DIR, 'all_hadiths_clean.csv'),
              CLEAN_COLS, _project(clean, CLEAN_COLS))
    shia_path = os.path.join(BASE_DIR, 'all_hadiths_shia.csv')
    write_csv(shia_path, SHIA_COLS, _project(shia, SHIA_COLS))
    compress_csv(shia_path)

    # --- Verify ---
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    verify(unified_path)
    verify(os.path.join(BASE_DIR, 'all_hadiths_clean.csv'))
    verify(shia_path)

    # Attribution + sanad coverage on the master
    lvl, withsan = {}, 0
    with open(unified_path, encoding='utf-8', errors='replace') as f:
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
        sys.exit(1)
    else:
        print(f"\nRecord count check: {total:,} (target ~99,285) — OK")

    print("\nDone!")


if __name__ == '__main__':
    main()
