"""Pure logic for report correspondence: comparison text, shingles, MinHash/LSH, scores, classes, clusters.

Standard library only, no I/O. Rationale and parameter choices: README.md in this directory, sections "Method" and
"Cluster guard".
"""

from __future__ import annotations

import hashlib
import re
from array import array
from collections import defaultdict
from dataclasses import dataclass
from itertools import accumulate
from operator import sub

# ─── Parameters (README.md §Method) ─────────────────────────────────────────────────────────────────

SHINGLE_LETTERS = 5          # character shingle length, over the letters of the comparison text (spaces removed)
MIN_WORDS = 8                # a matn shorter than this (comparison words) is not matched at all
PARTIAL_MIN_WORDS = 15       # the shorter side of a partial_overlap must have at least this many words
WINDOW_WORDS = 16            # LSH window length for long reports (containment recall)
WINDOW_STRIDE = 8            # windows overlap by half
OPH_BINS = 128               # one-permutation MinHash signature length
LSH_BANDS = 42               # bands x rows <= OPH_BINS; band j uses bins j, j+42, j+84
LSH_ROWS = 3
LSH_SIGNATURE_SALTS = (0, 0x5EED5EED)   # two independent signatures per window: 84 band tables in all
STOP_SHINGLE_DOCUMENT_SHARE = 0.005  # a shingle in more than 0.5 % of matns is ignored for candidate generation

# Classification thresholds on exact scores (README.md §Classes).
SAME_WORDING_JACCARD = 0.80
VARIANT_JACCARD = 0.25
VARIANT_CONTAINMENT = 0.40
PARTIAL_CONTAINMENT = 0.60
LOCAL_TRIGGER_RATIO = 1.25   # containment is measured locally when one text is over 1.25x the other
LOCAL_WINDOW_FACTOR = 1.25   # local window = 1.25x the shorter text (room for insertions)

CLASS_SAME_WORDING = "same_wording"
CLASS_VARIANT = "same_report_variant_wording"
CLASS_PARTIAL = "partial_overlap"
STRONG_CLASSES = (CLASS_SAME_WORDING, CLASS_VARIANT)

_MASK32 = 0xFFFFFFFF
_MASK64 = 0xFFFFFFFFFFFFFFFF

# ─── Comparison text ────────────────────────────────────────────────────────────────────────────────

# Comparison-only additions to the project's blessing-formula strip (regen.strip_blessing_formulas). Text here is
# already folded by regen.narrator_normalize (alef and ya variants), so literals are written folded.
_EXTRA_FORMULAS = re.compile(
    r"(?<![ء-ي])(?:"
    r"عز وجل|جل وعز|تبارك وتعالي|سبحانه وتعالي|جل جلاله|جل ثناؤه|تعالي ذكره|"
    r"صلوات الله عليه(?:م|ما|ا)?|عليه(?:م)? الصلاة والسلام|كرم الله وجهه|عجل الله فرجه(?: الشريف)?"
    r")(?![ء-ي])"
)
_ABBREVIATION_TOKENS = frozenset({"عج", "ره", "رض", "صلعم", "صلع"})
_KEPT_ONE_LETTER_TOKENS = frozenset({"و", "ف"})
_ARABIC_LETTER_MIN, _ARABIC_LETTER_MAX = "ء", "ي"


class ComparisonNormalizer:
    """Builds the comparison text with the project's own normalizer (regen_unified_csvs) plus listed extras."""

    def __init__(self, regen):
        self._normalize = regen.narrator_normalize                 # NFKC, format controls, vocalization, alef/ya
        self._letters = regen.fold_persian_urdu_letter_variants
        self._punctuation = regen.fold_punctuation_and_whitespace  # every non-letter becomes a space
        self._blessings = regen.strip_blessing_formulas

    def words(self, text: str) -> list[str]:
        """Comparison words of a text. Never stored as data; the source text is untouched."""
        value = self._blessings(self._punctuation(self._letters(self._normalize(text or ""))))
        value = _EXTRA_FORMULAS.sub(" ", value)
        out: list[str] = []
        for token in value.split():
            token = "".join(ch for ch in token if _ARABIC_LETTER_MIN <= ch <= _ARABIC_LETTER_MAX)
            if not token or token in _ABBREVIATION_TOKENS:
                continue
            if len(token) == 1 and token not in _KEPT_ONE_LETTER_TOKENS:
                continue  # lone abbreviation letters such as ع / ص / the Zaydi "ع م"
            out.append(token)
        return out


# ─── Shingles and hashing ───────────────────────────────────────────────────────────────────────────

# Arabic letters U+0621..U+064A map to bytes 1..42, so a 5-letter shingle is an exact 40-bit integer.
_LETTER_BYTES = {code: code - 0x0620 for code in range(0x0621, 0x064B)}


def _mix64(value: int) -> int:
    """SplitMix64 finalizer (Steele, Lea, Flood 2014): a bijective 64-bit mixer."""
    value = (value + 0x9E3779B97F4A7C15) & _MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
    return value ^ (value >> 31)


def letters_bytes(words: list[str]) -> bytes:
    """The comparison words joined without spaces, one byte per letter."""
    return "".join(words).translate(_LETTER_BYTES).encode("latin-1")


def shingle_hashes_at(letters: bytes, start: int = 0, end: int | None = None) -> list[int]:
    """32-bit hash of every SHINGLE_LETTERS-letter shingle that lies inside letters[start:end]."""
    end = len(letters) if end is None else end
    k = SHINGLE_LETTERS
    return [_mix64(int.from_bytes(letters[i:i + k], "big")) & _MASK32 for i in range(start, end - k + 1)]


def shingle_set(words: list[str]) -> array:
    """Sorted, de-duplicated shingle hashes of a whole comparison text."""
    return array("I", sorted(set(shingle_hashes_at(letters_bytes(words)))))


def window_letter_spans(words: list[str]) -> list[tuple[int, int]]:
    """Letter spans of overlapping word windows; a text of at most WINDOW_WORDS words is one window."""
    offsets = [0]
    for word in words:
        offsets.append(offsets[-1] + len(word))
    count = len(words)
    if count <= WINDOW_WORDS:
        return [(0, offsets[-1])]
    starts = list(range(0, count - WINDOW_WORDS + 1, WINDOW_STRIDE))
    if starts[-1] != count - WINDOW_WORDS:
        starts.append(count - WINDOW_WORDS)  # the last window is anchored to the end of the text
    return [(offsets[s], offsets[s + WINDOW_WORDS]) for s in starts]


# ─── MinHash (one-permutation hashing with rotation densification) and LSH bands ─────────────────────

_EMPTY = -1
_BIN_BITS = OPH_BINS.bit_length() - 1
_DENSIFY_STEP = 1 << (32 - _BIN_BITS)


def one_permutation_minhash(hashes, salt: int = 0) -> list[int] | None:
    """One-permutation MinHash, densified by rotation; None for an empty set.

    One Permutation Hashing: Li, Owen, Zhang, NIPS 2012 (https://arxiv.org/abs/1208.1259).
    Rotation densification: Shrivastava, Li, ICML 2014 (https://proceedings.mlr.press/v32/shrivastava14.html).
    """
    if salt:
        hashes = [_mix64(value ^ salt) & _MASK32 for value in hashes]   # an independent permutation
    signature = [_EMPTY] * OPH_BINS
    mask = OPH_BINS - 1
    for value in hashes:
        index = value & mask
        rest = value >> _BIN_BITS
        current = signature[index]
        if current == _EMPTY or rest < current:
            signature[index] = rest
    if all(v == _EMPTY for v in signature):
        return None
    dense = list(signature)
    for index in range(OPH_BINS):
        if signature[index] != _EMPTY:
            continue
        distance = 1
        while signature[(index + distance) % OPH_BINS] == _EMPTY:
            distance += 1
        dense[index] = signature[(index + distance) % OPH_BINS] + distance * _DENSIFY_STEP
    return dense


def band_keys(signature: list[int]) -> list[int]:
    """One 64-bit key per LSH band (banding: Leskovec, Rajaraman, Ullman, Mining of Massive Datasets, ch. 3.4)."""
    keys = []
    for band in range(LSH_BANDS):
        key = band
        # Rows are spread across the signature: densified neighbours copy one bin, so contiguous rows would be
        # correlated and a band would behave like fewer rows.
        for value in signature[band:LSH_BANDS * LSH_ROWS:LSH_BANDS]:
            key = _mix64(key ^ value)
        keys.append(key)
    return keys


def lsh_candidate_probability(jaccard: float) -> float:
    """Probability that a window pair with this Jaccard shares at least one band."""
    return 1.0 - (1.0 - jaccard ** LSH_ROWS) ** (LSH_BANDS * len(LSH_SIGNATURE_SALTS))


# ─── Exact scores and classes ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PairScore:
    shared: int
    size_a: int
    size_b: int
    local: float | None = None   # local containment when one text is much longer (see local_containment)

    @property
    def jaccard(self) -> float:
        union = self.size_a + self.size_b - self.shared
        return self.shared / union if union else 0.0

    @property
    def global_containment(self) -> float:
        """Share of the SHORTER text's shingles found anywhere in the longer one."""
        smaller = min(self.size_a, self.size_b)
        return self.shared / smaller if smaller else 0.0

    @property
    def containment(self) -> float:
        """Containment used for classes: local when computed, else global."""
        return self.local if self.local is not None else self.global_containment

    @property
    def length_ratio(self) -> float:
        larger = max(self.size_a, self.size_b)
        return min(self.size_a, self.size_b) / larger if larger else 0.0


def local_containment(short_set, long_sequence, short_positions: int) -> float:
    """Best share of the shorter text's shingles inside ONE window of the longer text.

    The window is LOCAL_WINDOW_FACTOR x the shorter text's length. A short report's letter 5-grams occur scattered
    through any very long text by chance; requiring them in one place is what makes containment mean "contains this
    passage". Sliding-window maximum over prefix sums.
    """
    width = max(1, int(LOCAL_WINDOW_FACTOR * short_positions))
    flags = [1 if value in short_set else 0 for value in long_sequence]
    if len(flags) <= width:
        hits = sum(flags)
    else:
        prefix = list(accumulate(flags, initial=0))
        hits = max(map(sub, prefix[width:], prefix))
    return min(1.0, hits / len(short_set)) if short_set else 0.0


def best_window_words(short_set, long_words: list[str], short_positions: int) -> tuple[int, int]:
    """Word span [start, end) of the longer text holding the most shingles of the shorter one (display only)."""
    sequence = shingle_hashes_at(letters_bytes(long_words))
    width = max(1, int(LOCAL_WINDOW_FACTOR * short_positions))
    flags = [1 if value in short_set else 0 for value in sequence]
    if len(flags) <= width:
        return 0, len(long_words)
    prefix = list(accumulate(flags, initial=0))
    best = max(range(len(flags) - width + 1), key=lambda i: (prefix[i + width] - prefix[i], -i))
    offsets, position = [], 0
    for word in long_words:
        offsets.append(position)
        position += len(word)
    first = max((i for i, o in enumerate(offsets) if o <= best), default=0)
    last = max((i for i, o in enumerate(offsets) if o < best + width + SHINGLE_LETTERS), default=len(long_words) - 1)
    return first, last + 1


def needs_local_containment(positions_a: int, positions_b: int) -> bool:
    return max(positions_a, positions_b) > LOCAL_TRIGGER_RATIO * min(positions_a, positions_b)


def score_sets(set_a, set_b, sequence_a=None, sequence_b=None) -> PairScore:
    """Exact scores for two shingle collections; with position sequences, containment is local."""
    a = set(set_a)
    b = set(set_b)
    local = None
    if sequence_a is not None and sequence_b is not None and needs_local_containment(len(sequence_a), len(sequence_b)):
        if len(sequence_a) <= len(sequence_b):
            local = local_containment(a, sequence_b, len(sequence_a))
        else:
            local = local_containment(b, sequence_a, len(sequence_b))
    return PairScore(len(a & b), len(a), len(b), local)


def classify(score: PairScore, words_a: int, words_b: int) -> str | None:
    """Class of a scored pair, or None when the evidence is too weak to keep (README.md §Classes)."""
    if min(words_a, words_b) < MIN_WORDS:
        return None
    if score.jaccard >= SAME_WORDING_JACCARD:
        return CLASS_SAME_WORDING
    if score.jaccard >= VARIANT_JACCARD and score.containment >= VARIANT_CONTAINMENT:
        return CLASS_VARIANT
    if score.containment >= PARTIAL_CONTAINMENT and min(words_a, words_b) >= PARTIAL_MIN_WORDS:
        return CLASS_PARTIAL
    return None


def score_band(score: PairScore, pair_class: str) -> str:
    """Display band: Jaccard for the two strong classes, containment for partial overlaps."""
    value = score.containment if pair_class == CLASS_PARTIAL else score.jaccard
    lower = min(int(round(value, 6) * 10), 9) / 10
    metric = "containment" if pair_class == CLASS_PARTIAL else "jaccard"
    return f"{metric}_{lower:.1f}-{lower + 0.1:.1f}"


# ─── Clusters: star clustering plus a compound-report guard ──────────────────────────────────────────────────────────


class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        parent = self.parent.setdefault(item, item)
        if parent != item:
            parent = self.parent[item] = self.find(parent)
        return parent

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            if b < a:
                a, b = b, a
            self.parent[b] = a  # the smaller id is the root: order-independent result


def star_centres(nodes, neighbours: dict) -> dict[str, str]:
    """Star clustering: {node: centre}; every member is directly linked to its centre, so nothing chains.

    Aslam, Pelekhov, Rus, "The Star Clustering Algorithm for Static and Dynamic Information Organization",
    JGAA 8(1), 2004 (https://doi.org/10.7155/jgaa.00084). Centres are taken by degree (descending), then id.
    """
    centre_of: dict[str, str] = {}
    for node in sorted(nodes, key=lambda n: (-len(neighbours.get(n, ())), n)):
        if node in centre_of:
            continue
        centre_of[node] = node
        for neighbour in sorted(neighbours.get(node, ())):
            centre_of.setdefault(neighbour, node)
    return centre_of


def build_clusters(pairs, lengths: dict[str, int]) -> tuple[dict[str, str], dict[str, str], dict]:
    """Group reports into clusters; returns ({report: cluster id}, {report: star centre}, guard statistics).

    pairs: iterable of (id_a, id_b, class). lengths: shingle count per report (which side is the container).
    Phase 1 (chaining guard): star clustering over strong edges (same wording, variant wording).
    Phase 2 (compound guard): a partial_overlap edge merges two stars only when the relation is one-to-one: the
    container star contains no other star and the contained star lies in no other star. README.md §Clusters.
    """
    neighbours: dict[str, set] = defaultdict(set)
    nodes: set[str] = set()
    partial_edges = []
    for id_a, id_b, pair_class in pairs:
        nodes.update((id_a, id_b))
        if pair_class in STRONG_CLASSES:
            neighbours[id_a].add(id_b)
            neighbours[id_b].add(id_a)
        elif pair_class == CLASS_PARTIAL:
            partial_edges.append((id_a, id_b))
    centre_of = star_centres(nodes, neighbours)
    strong_edges = sum(len(v) for v in neighbours.values()) // 2
    strong_edges_inside_stars = sum(1 for a in neighbours for b in neighbours[a]
                                    if a < b and centre_of[a] == centre_of[b])

    contains: dict[str, set] = defaultdict(set)      # container star -> contained stars
    contained_in: dict[str, set] = defaultdict(set)  # contained star -> container stars
    directed = set()
    for id_a, id_b in partial_edges:
        ca, cb = centre_of[id_a], centre_of[id_b]
        if ca == cb:
            continue
        container, contained = (ca, cb) if (lengths[id_a], id_a) >= (lengths[id_b], id_b) else (cb, ca)
        contains[container].add(contained)
        contained_in[contained].add(container)
        directed.add((container, contained))

    merged = UnionFind()
    for centre in set(centre_of.values()):
        merged.find(centre)
    accepted = blocked = 0
    for container, contained in sorted(directed):
        if len(contains[container]) == 1 and len(contained_in[contained]) == 1:
            merged.union(container, contained)
            accepted += 1
        else:
            blocked += 1

    members: dict[str, list[str]] = defaultdict(list)
    for item, centre in centre_of.items():
        members[merged.find(centre)].append(item)
    cluster_of: dict[str, str] = {}
    for items in members.values():
        cluster_id = cluster_identifier(items)
        for item in items:
            cluster_of[item] = cluster_id
    guard = {
        "strong_edges": strong_edges,
        "strong_edges_inside_one_star": strong_edges_inside_stars,
        "strong_edges_between_stars_not_merged": strong_edges - strong_edges_inside_stars,
        "partial_edges_between_stars": len(directed),
        "partial_edges_merged_one_to_one": accepted,
        "partial_edges_blocked_by_guard": blocked,
        "compound_container_stars": sum(1 for v in contains.values() if len(v) > 1),
        "multiply_contained_stars": sum(1 for v in contained_in.values() if len(v) > 1),
    }
    return cluster_of, centre_of, guard


def cluster_identifier(member_ids) -> str:
    """Deterministic, content-addressed cluster id: SHA-256 over the sorted member report ids."""
    digest = hashlib.sha256("\n".join(sorted(member_ids)).encode("utf-8")).hexdigest()
    return f"report-cluster:{digest[:20]}"
