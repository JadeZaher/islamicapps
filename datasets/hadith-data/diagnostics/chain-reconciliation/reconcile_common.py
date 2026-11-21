"""Shared loaders, the corroboration predicate and the order-preserving alignment for chain-reconciliation jobs.

See README.md in this directory for the method and how to read the numbers. Nothing here asserts an identity:
a source id is the source's claim, and a corroboration tier only says whether the Arabic text is consistent with it.
"""

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import diagnostic_common as common  # noqa: E402
import name_invariant  # noqa: E402

sys.dont_write_bytecode = True
csv.field_size_limit(1 << 30)

K6_ARCHIVE = common.DATASETS_DIR / "archive" / "datasets.7z"
K6_MEMBER = "datasets/hadith-data/all_hadiths_clean.csv"
PURE_CANON = common.HADITH_DATA_DIR / "archive" / "sheikahmad-pure-canon" / "pure_canon.jsonl"
THAQALAYN_DIR = common.HADITH_DATA_DIR / "shia-hadith" / "v2_books"
OPENITI_PARSED = {
    "Ibadi": common.HADITH_DATA_DIR / "ibadi-hadith" / "parsed_hadiths.json",
    "Zaydi": common.HADITH_DATA_DIR / "zaydi-hadith" / "parsed_hadiths.json",
    "Rida": common.HADITH_DATA_DIR / "rida-hadith" / "parsed_hadiths.json",
}
# Windows' bundled bsdtar reads 7z; Git Bash's GNU tar does not.
BSDTAR = os.environ.get("BSDTAR", r"C:\Windows\System32\tar.exe")
K6_SOURCES = {"Sahih Bukhari", "Sahih Muslim", "Sunan Abi Da'ud", "Jami' al-Tirmidhi",
              "Sunan an-Nasa'i", "Sunan Ibn Majah"}
PURE_CANON_SOURCES = {"Musnad Ahmad", "Sunan al-Darimi", "Musnad al-Shafi'i", "Muwatta' Malik"}

CONNECTORS = {"بن", "بنت"}
KUNYA_HEADS = {"ابو", "ام"}
FATHER_WORDS = {"ابيه", "ابوه", "ابي", "ابيها", "ابيهما"}
GRANDFATHER_WORDS = {"جده", "جدي", "جدها"}
OTHER_RELATIONAL = {"عمه", "عمي", "امه", "امي", "اخيه", "خاله", "خالي", "جدته", "عنه", "و"}

# Basis labels carried on every candidate row (README "Basis labels").
BASIS_SOURCE_INDEX = "source_index"
BASIS_CORROBORATED = "source_index_corroborated_by_text"
BASIS_ALIGNED = "source_index_aligned_partial"
BASIS_LEARNED = "learned_from_corroborated_context"
BASIS_STRICT = "canonical_exact_resolver"

CORROBORATED_FULL = ("resolver_same_id", "full_name_key", "relational_parent_attested",
                     "relational_grandparent_attested")
CORROBORATED_PARTIAL = ("name_tokens_subsumed", "name_tokens_all_present", "ism_nasab_core_agrees")
CORROBORATED = CORROBORATED_FULL + CORROBORATED_PARTIAL


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_k6_original() -> tuple:
    """Rows of the original K6 CSV inside archive/datasets.7z, plus the member's SHA-256 (read-only, in memory)."""
    result = subprocess.run([BSDTAR, "-xOf", str(K6_ARCHIVE), K6_MEMBER], capture_output=True, timeout=300,
                            check=True)
    data = result.stdout
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))
    return rows, sha256_bytes(data)


def parse_ids(value: str) -> list:
    """Comma/pipe separated positive integer ids as strings; anything else is dropped."""
    return [token.strip() for token in re.split(r"[,|;]", value or "") if token.strip().isdigit()]


def read_pure_canon() -> dict:
    """pure_canon.jsonl rows keyed by stripped Arabic text (list, because some texts repeat)."""
    by_text = defaultdict(list)
    with open(PURE_CANON, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                by_text[(row.get("text_ar") or "").strip()].append(row)
    return by_text


def iter_thaqalayn():
    """(provider_file_id, hadith dict) for every Thaqalayn V2 record on disk."""
    for path in sorted(THAQALAYN_DIR.glob("*.json"), key=lambda p: (len(p.stem), p.stem)):
        if not path.stem.isdigit():
            continue
        for hadith in json.load(open(path, encoding="utf-8")):
            yield path.stem, hadith


class Canon:
    """The canonical pipeline's normalizer, extractor and strict resolver, imported at runtime (never copied)."""

    def __init__(self):
        self.regen = common.load_regen()
        self.extractor = common.load_extractor()
        self.exact_index, self.blocked_index = self.regen.build_narrator_index(str(common.REGISTRY_PATH))
        self._fold = getattr(self.regen, "narrator_fold_normalize", self.regen.narrator_normalize)
        self._resolve_cache: dict = {}
        self._key_cache: dict = {}
        self._fold_cache: dict = {}
        self.registry = self._load_registry()
        self.normalizer_features = sorted(
            name for name in ("narrator_fold_normalize", "fold_kunya_case_forms", "kunya_fold_allowed",
                              "strip_blessing_formulas", "_extract_arabic_name_raw")
            if hasattr(self.regen, name))

    def fold(self, surface: str) -> str:
        """Canonical lookup key (narrator_fold_normalize when present, else narrator_normalize)."""
        cached = self._fold_cache.get(surface)
        if cached is None:
            cached = sys.intern(self._fold(surface or ""))
            self._fold_cache[surface] = cached
        return cached

    def resolve(self, surface: str):
        """Canonical strict resolver result (scholar_indx string or None)."""
        if surface not in self._resolve_cache:
            hit = self.regen.resolve_narrator(surface, self.exact_index, self.blocked_index)
            self._resolve_cache[surface] = str(hit) if hit else None
        return self._resolve_cache[surface]

    def comparison_key(self, text: str) -> str:
        """Canonical fold plus the diagnostic name-invariant rules: a comparison aid, never a lookup key."""
        cached = self._key_cache.get(text)
        if cached is None:
            cached = name_invariant.compute_name_invariant(text, base_normalize=self._fold)
            self._key_cache[text] = cached
        return cached

    def _registry_forms(self, name_field: str) -> list:
        raw_extract = getattr(self.regen, "_extract_arabic_name_raw", None)
        raw = raw_extract(name_field) if raw_extract else self.regen._extract_arabic_name(name_field)
        pieces = [raw] + [piece for piece in re.split(r"\s[-–]\s|،|/", raw or "") if piece.strip()]
        forms = []
        for piece in pieces:
            key = self.comparison_key(piece)
            if key and key not in forms:
                forms.append(key)
        return forms

    def _load_registry(self) -> dict:
        registry = {}
        with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                indx = (row.get("scholar_indx") or "").strip()
                if not indx.isdigit():
                    continue
                registry[indx] = {
                    "forms": self._registry_forms(row.get("name") or ""),
                    "parents": re.findall(r"\[(\d+)\]", row.get("parents") or ""),
                    "teachers": set(parse_ids(row.get("teachers_inds") or "")),
                    "students": set(parse_ids(row.get("students_inds") or "")),
                    "grade": (row.get("grade") or "").strip(),
                }
        return registry

    def extract(self, text_ar: str):
        """Extractor branches, or None when the typed branch limit is hit."""
        try:
            return self.extractor.extract_isnad_branches(text_ar or "")
        except self.extractor.IsnadExtractionLimitError:
            return None


def _is_subsequence(short: list, long: list) -> bool:
    iterator = iter(long)
    return all(token in iterator for token in short)


def _bare(token: str) -> str:
    """Token without a leading definite article (comparison only: العباس ~ عباس)."""
    return token[2:] if token.startswith("ال") and len(token) > 4 else token


def _ism_nasab_core(tokens: list) -> list:
    """Leading 'X بن Y [بن Z]' run of a surface; [] when the surface has no nasab."""
    end = 0
    while end + 2 < len(tokens) and tokens[end + 1] in CONNECTORS:
        end += 2
    return tokens[:end + 1] if end else []


def name_tier(canon: Canon, surface: str, source_id: str, previous_source_id) -> str:
    """Name-only relation between an Arabic surface and a registry id (ignores the resolver)."""
    entry = canon.registry.get(source_id)
    if entry is None:
        return "source_id_not_in_registry"
    key = canon.comparison_key(surface)
    tokens = key.split()
    if not tokens:
        return "empty_surface"
    if key in FATHER_WORDS or key in GRANDFATHER_WORDS:
        previous = canon.registry.get(previous_source_id or "")
        if previous is not None:
            if key in FATHER_WORDS and source_id in previous["parents"]:
                return "relational_parent_attested"
            if key in GRANDFATHER_WORDS and any(
                    source_id in canon.registry.get(parent, {}).get("parents", ()) for parent in previous["parents"]):
                return "relational_grandparent_attested"
        return "relational_unattested"
    if key in OTHER_RELATIONAL:
        return "relational_unattested"
    if key in entry["forms"]:
        return "full_name_key"
    content = [_bare(token) for token in tokens if token not in CONNECTORS and token not in KUNYA_HEADS]
    if not content:
        return "no_content_tokens"
    bare_tokens = [_bare(token) for token in tokens]
    bare_forms = [[_bare(token) for token in form.split()] for form in entry["forms"]]
    if any(_is_subsequence(bare_tokens, form) for form in bare_forms):
        return "name_tokens_subsumed"
    if any(set(content) <= set(form) for form in bare_forms):
        return "name_tokens_all_present"
    core = _ism_nasab_core(bare_tokens)
    if core and any(_is_subsequence(core, form) for form in bare_forms):
        return "ism_nasab_core_agrees"
    if {token for form in bare_forms for token in form}.intersection(content):
        return "partial_token_overlap"
    return "no_token_overlap"


def corroboration_tier(canon: Canon, surface: str, source_id: str, previous_source_id) -> str:
    """How the Arabic surface relates to the source's id at the same position (one tier label, README table)."""
    if canon.resolve(surface) == source_id:
        return "resolver_same_id"
    return name_tier(canon, surface, source_id, previous_source_id)


def resolver_conflict(canon: Canon, surface: str, source_id: str) -> bool:
    """The strict resolver completes this surface to a different registry id than the source index."""
    resolved = canon.resolve(surface)
    return resolved is not None and resolved != source_id


def align(canon: Canon, source_ids: list, surfaces: list) -> list:
    """Order-preserving alignment maximising corroborated pairs (LCS dynamic programme).

    Returns [(source_position, surface_position, tier)] for aligned corroborated pairs only.
    """
    m, n = len(source_ids), len(surfaces)
    tiers = [[corroboration_tier(canon, surfaces[j], source_ids[i], source_ids[i - 1] if i else None)
              for j in range(n)] for i in range(m)]
    score = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            best = max(score[i + 1][j], score[i][j + 1])
            if tiers[i][j] in CORROBORATED:
                best = max(best, 1 + score[i + 1][j + 1])
            score[i][j] = best
    pairs, i, j = [], 0, 0
    while i < m and j < n:
        if tiers[i][j] in CORROBORATED and score[i][j] == 1 + score[i + 1][j + 1]:
            pairs.append((i, j, tiers[i][j]))
            i, j = i + 1, j + 1
        elif score[i + 1][j] >= score[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def write_text(directory: Path, name: str, text: str) -> None:
    handle, _ = common.open_output(directory, name)
    with handle:
        handle.write(text)
