"""Report correspondence v2: formula-aware, short-saying-aware, compiler-remark-free candidate pairs and clusters.

Method, parameters, results and the load spec: README.md in this directory. Read-only on every input; writes only
under diagnostics/report-correspondence-v2/output/. Standard library only, deterministic. Shared code is imported from
../report-correspondence (v1).

    python -B datasets/hadith-data/diagnostics/report-correspondence-v2/build_report_correspondence_v2.py
"""

from __future__ import annotations

import csv
import gzip
import json
import random
import sys
import time
from array import array
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
JOB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(JOB_DIR))

import correspondence_logic_v2 as logic2  # noqa: E402  (also puts the v1 directory on sys.path)
import correspondence_logic as v1  # noqa: E402
import build_report_correspondence as v1build  # noqa: E402
import matn_isolation as isolation  # noqa: E402

common = logic2.common
JOB = "report-correspondence-v2"
COMMAND = "python -B datasets/hadith-data/diagnostics/report-correspondence-v2/build_report_correspondence_v2.py"
V1_OUTPUT = logic2.V1_DIR / "output"
QURAN_FILE = common.DATASETS_DIR / "sources" / "external" / "quran-tanzil" / "quran-simple-clean.txt"
METHOD_VERSION = logic2.METHOD_VERSION
SEED = 20261122
PAIR_SHIFT = v1build.PAIR_SHIFT
BUCKET_CAP = v1build.BUCKET_CAP
MIN_WINDOW_SHINGLES = v1build.MIN_WINDOW_SHINGLES
MAX_CANDIDATES = 12_000_000
TRADITION_ORDER = v1build.TRADITION_ORDER
ORIGIN_WINDOW, ORIGIN_CONTENT, ORIGIN_SHORT = 1, 2, 4
ORIGIN_NAMES = ((ORIGIN_WINDOW, "window_lsh"), (ORIGIN_CONTENT, "content_lsh"), (ORIGIN_SHORT, "short_index"))
progress = v1build.progress


class Reports(v1build.Reports):
    """v1 column store plus the v2 fields."""

    def __init__(self):
        super().__init__()
        self.cut: list[bool] = []
        self.words_before_cut: array = array("I")
        self.word_lists: list[list[str]] = []
        self.prepared: list = []          # logic2.Prepared or None (not eligible)
        self.residual_count: array = array("I")


def read_corpus(started: float):
    """Rows to isolated matns, compiler remarks cut, comparison words. Returns (reports, meta, normalizer)."""
    regen = common.load_regen()
    extractor = common.load_extractor()
    normalizer = v1.ComparisonNormalizer(regen)
    matn_only, no_chain = isolation.load_sidecars(v1build.RECONCILED)
    isolator = isolation.MatnIsolator(extractor, matn_only, no_chain)
    rules = logic2.CompilerRules()
    work_ids = v1build.load_work_ids()
    reports = Reports()
    cut_by_work: Counter = Counter()
    left_nothing = 0
    with gzip.open(v1build.CORPUS, "rt", encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            tradition, work = row["tradition"].strip(), row["source"].strip()
            matn, method, reliability, note = isolator.isolate(row)
            before = normalizer.words(matn) if matn else []
            cut_text, was_cut = rules.cut(matn, work) if matn else (matn, False)
            words = normalizer.words(cut_text) if was_cut else before
            if was_cut:
                cut_by_work[work] += 1
                left_nothing += len(words) < logic2.SHORT_MIN_WORDS
            reports.hadith_id.append(f"hadith:{row['record_id'].strip()}")
            reports.tradition.append(tradition)
            reports.work.append(work)
            reports.work_id.append(row["source_work_id"].strip() or work_ids.get((tradition, work), ""))
            reports.hadith_no.append(row["hadith_no"].strip())
            reports.arabic_sha256.append(isolation.sha256_text(row["text_ar"]))
            reports.source_record_id.append(row["source_record_id"].strip())
            reports.method.append(method)
            reports.reliability.append(reliability)
            reports.note.append(note)
            reports.matn.append(matn)
            reports.cut.append(was_cut)
            reports.words_before_cut.append(len(before))
            reports.word_lists.append(words)
            reports.words.append(len(words))
            if index % 25000 == 0:
                progress(f"read {index} rows", started)
    meta = {"rows": len(reports), "compiler_remark_cut_by_work": dict(sorted(cut_by_work.items())),
            "compiler_remark_cut_total": sum(cut_by_work.values()), "cut_left_fewer_than_3_words": left_nothing,
            "sidecar_hash_mismatches": isolator.sidecar_hash_mismatches}
    return reports, meta, normalizer


class Vocabulary:
    def __init__(self):
        self.ids: dict[str, int] = {}

    def id(self, word: str) -> int:
        return self.ids.setdefault(word, len(self.ids))


def load_quran(normalizer) -> list[list[str]]:
    verses = []
    for line in QURAN_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            words = normalizer.words(parts[2])
            if len(words) >= logic2.QURAN_GRAM_WORDS:
                verses.append(words)
    return verses


def build_formula_inventory(reports: Reports, vocabulary: Vocabulary, quran_keys: set, started: float):
    """Frequent word 4-grams over all reports (document frequency >= FORMULA_MIN_DOCUMENTS) plus Qur'an spans."""
    counter = logic2.GramCounter()
    id_lists = []
    for words in reports.word_lists:
        id_lists.append([vocabulary.id(w) for w in words])
    for ids in id_lists:
        counter.first_pass(logic2.gram_keys(ids, logic2.GRAM_WORDS))
    for ids in id_lists:
        counter.second_pass(logic2.gram_keys(ids, logic2.GRAM_WORDS), logic2.FORMULA_MIN_DOCUMENTS)
    frequent = counter.frequent()
    progress(f"formula inventory: {len(frequent)} frequent word 4-grams (DF >= {logic2.FORMULA_MIN_DOCUMENTS}), "
             f"{len(quran_keys)} Qur'an 5-word spans", started)
    return frequent, counter.exact, id_lists


def prepare_reports(reports: Reports, id_lists: list, frequent: set, quran_keys: set, started: float):
    """Prepared (full and residual shingles) for every report with at least SHORT_MIN_WORDS words."""
    removed_by_kind: Counter = Counter()
    run_documents: dict[tuple, int] = {}
    for index, words in enumerate(reports.word_lists):
        eligible = len(words) >= logic2.SHORT_MIN_WORDS
        flags = logic2.formula_flags(id_lists[index], frequent, quran_keys) if len(words) >= logic2.GRAM_WORDS else None
        prepared = logic2.prepare(words, flags) if eligible else None
        if prepared is not None and len(prepared.full_shingles) == 0:
            prepared = None
        reports.prepared.append(prepared)
        reports.eligible.append(1 if prepared is not None else 0)
        reports.residual_count.append(len(prepared.residual) if prepared is not None else 0)
        if flags is not None and any(flags):
            removed_by_kind["reports_with_formula_words"] += 1
            for run in set(logic2.formula_runs(words, flags)):
                run_documents[run] = run_documents.get(run, 0) + 1
        if index % 25000 == 0:
            progress(f"prepared {index}", started)
    return removed_by_kind, run_documents


def window_signatures(reports: Reports, df: array, stop_threshold: int, started: float):
    keys, owner = array("Q"), array("I")
    without_signature = 0
    for index, prepared in enumerate(reports.prepared):
        if prepared is None or len(prepared.words) < v1.MIN_WORDS:
            continue
        for start, end in v1.window_letter_spans(prepared.words):
            hashes = [h for h in set(v1.shingle_hashes_at(prepared.full_letters, start, end)) if df[h >> 8] <= stop_threshold]
            if len(hashes) < MIN_WINDOW_SHINGLES:
                without_signature += 1
                continue
            for salt in v1.LSH_SIGNATURE_SALTS:
                keys.extend(v1.band_keys(v1.one_permutation_minhash(hashes, salt)))
            owner.append(index)
        if index % 25000 == 0:
            progress(f"window signatures to row {index}: {len(owner)} windows", started)
    return keys, owner, without_signature


def content_signatures(reports: Reports, eligible_count: int, started: float):
    """The v2 third signature: one MinHash per report over its rare content-word stems (formula words removed)."""
    stem_lists = []
    document_frequency: Counter = Counter()
    for prepared in reports.prepared:
        if prepared is None:
            stem_lists.append(None)
            continue
        stems = {logic2.content_stem(w) for w in prepared.residual}
        stem_lists.append(stems)
        document_frequency.update(stems)
    maximum = max(2, int(logic2.CONTENT_MAX_DOCUMENT_SHARE * eligible_count))
    keys, owner = array("Q"), array("I")
    for index, stems in enumerate(stem_lists):
        if stems is None:
            continue
        hashes = sorted({logic2.content_hash(s) for s in stems if 2 <= document_frequency[s] <= maximum})
        if len(hashes) < logic2.CONTENT_MIN_TOKENS:
            continue
        keys.extend(v1.band_keys(v1.one_permutation_minhash(hashes, logic2.CONTENT_SALT)))
        owner.append(index)
    progress(f"content signatures: {len(owner)} reports signed (stem frequency cap {maximum})", started)
    return keys, owner, maximum


def bucket_pairs(keys: array, owner: array, columns: int, origin: int, pairs: dict, started: float) -> dict:
    """Candidate pairs from LSH band buckets (v1 procedure, generalised to a column count); formula buckets emit none."""
    capped_buckets, capped_reports = 0, set()
    count = len(owner)
    for band in range(columns):
        column = sorted(zip(keys[band::columns], owner)) if count else []
        position = 0
        while position < len(column):
            end = position + 1
            while end < len(column) and column[end][0] == column[position][0]:
                end += 1
            if end - position > 1:
                members = sorted({doc for _, doc in column[position:end]})
                if len(members) > BUCKET_CAP:
                    capped_buckets += 1
                    capped_reports.update(members)
                elif len(members) > 1:
                    for i, a in enumerate(members):
                        base = a << PAIR_SHIFT
                        for b in members[i + 1:]:
                            pairs[base | b] = pairs.get(base | b, 0) | origin
            position = end
        if len(pairs) > MAX_CANDIDATES:
            raise RuntimeError(f"more than {MAX_CANDIDATES} candidate pairs: LSH parameters too loose")
    progress(f"{columns} band tables (origin {origin}): {len(pairs)} candidate pairs, {capped_buckets} formula buckets",
             started)
    return {"formula_buckets": capped_buckets, "reports_in_formula_buckets": len(capped_reports)}


def short_index_pairs(reports: Reports, pairs: dict, started: float) -> dict:
    """Candidates for short sayings (3 to 14 words): reports sharing one of the saying's two rarest residual shingles.

    Inverted index over residual shingles, limited to the shingles of short reports; a shingle held by more than
    SHORT_POSTING_CAP reports seeds nothing (it is common wording, so the saying has no distinctive anchor).
    """
    short_ids = [i for i, p in enumerate(reports.prepared)
                 if p is not None and logic2.SHORT_MIN_WORDS <= len(p.words) <= logic2.QUOTED_MAX_SAYING_WORDS
                 and len(p.residual) >= logic2.SHORT_MIN_WORDS]
    postings: dict[int, array] = {}
    for i in short_ids:
        for shingle in reports.prepared[i].residual_shingles:
            if shingle not in postings:
                postings[shingle] = array("I")
    for index, prepared in enumerate(reports.prepared):
        if prepared is None:
            continue
        for shingle in prepared.residual_shingles:
            listing = postings.get(shingle)
            if listing is not None and len(listing) <= logic2.SHORT_POSTING_CAP:
                listing.append(index)
    without_anchor = 0
    for i in short_ids:
        prepared = reports.prepared[i]
        prepared.anchor_documents = min((len(postings[sh]) for sh in prepared.residual_shingles), default=logic2.NO_ANCHOR)
        usable = sorted((len(postings[s]), s) for s in reports.prepared[i].residual_shingles
                        if len(postings[s]) <= logic2.SHORT_POSTING_CAP)
        if not usable:
            without_anchor += 1
            continue
        for _, shingle in usable[:2]:
            for j in postings[shingle]:
                if j != i:
                    low, high = (i, j) if i < j else (j, i)
                    pairs[(low << PAIR_SHIFT) | high] = pairs.get((low << PAIR_SHIFT) | high, 0) | ORIGIN_SHORT
    progress(f"short index: {len(short_ids)} short reports, {without_anchor} without a distinctive shingle; "
             f"{len(pairs)} candidates in all", started)
    return {"short_reports": len(short_ids), "short_reports_without_distinctive_shingle": without_anchor}


def score_candidates(reports: Reports, pairs: dict, started: float) -> list[tuple]:
    sequence_cache = lru_cache(maxsize=4096)(
        lambda index, residual: v1.shingle_hashes_at(
            reports.prepared[index].residual_letters if residual else reports.prepared[index].full_letters))
    kept = []
    current, set_full, set_residual = -1, set(), set()
    for done, key in enumerate(sorted(pairs)):
        a, b = key >> PAIR_SHIFT, key & ((1 << PAIR_SHIFT) - 1)
        prepared_a, prepared_b = reports.prepared[a], reports.prepared[b]
        if prepared_a is None or prepared_b is None:
            continue
        if a != current:
            current = a
            set_full = set(prepared_a.full_shingles)
            set_residual = set_full if prepared_a.residual_shingles is prepared_a.full_shingles else set(prepared_a.residual_shingles)
        verdict = logic2.compare(prepared_a, prepared_b, set_full, set_residual,
                                 lambda a=a: sequence_cache(a, True), lambda b=b: sequence_cache(b, True))
        if verdict is not None:
            kept.append((a, b, verdict, pairs[key]))
        if done % 250000 == 0:
            progress(f"scored {done}/{len(pairs)}; kept {len(kept)}", started)
    return kept


def candidate_pairs_for_all(reports: Reports, started: float) -> tuple[dict, dict]:
    eligible_long = sum(1 for p in reports.prepared if p is not None and len(p.words) >= v1.MIN_WORDS)
    stop_threshold = max(1, int(eligible_long * v1.STOP_SHINGLE_DOCUMENT_SHARE))
    df = array("I", bytes(4 * (1 << 24)))
    for prepared in reports.prepared:
        if prepared is not None and len(prepared.words) >= v1.MIN_WORDS:
            for value in prepared.full_shingles:
                df[value >> 8] += 1
    keys, owner, no_signature = window_signatures(reports, df, stop_threshold, started)
    windows = len(owner)
    del df
    pairs: dict[int, int] = {}
    stats = {"stop_threshold_documents": stop_threshold, "windows_signed": windows,
             "windows_without_signature": no_signature}
    stats.update({f"window_{k}": v for k, v in bucket_pairs(
        keys, owner, v1.LSH_BANDS * len(v1.LSH_SIGNATURE_SALTS), ORIGIN_WINDOW, pairs, started).items()})
    stats["pairs_after_window_lsh"] = len(pairs)
    del keys, owner
    keys, owner, maximum = content_signatures(reports, sum(1 for p in reports.prepared if p is not None), started)
    stats["content_signed_reports"] = len(owner)
    stats["content_stem_frequency_cap"] = maximum
    stats.update({f"content_{k}": v for k, v in bucket_pairs(
        keys, owner, v1.LSH_BANDS, ORIGIN_CONTENT, pairs, started).items()})
    stats["pairs_after_content_lsh"] = len(pairs)
    del keys, owner
    stats.update(short_index_pairs(reports, pairs, started))
    stats["candidate_pairs_total"] = len(pairs)
    return pairs, stats


PAIR_COLUMNS = v1build.PAIR_COLUMNS + [
    "jaccard_full", "containment_full", "words_residual_a", "words_residual_b", "short_side", "compiler_cut_a",
    "compiler_cut_b", "found_by",
]


def origin_label(bits: int) -> str:
    return "+".join(name for bit, name in ORIGIN_NAMES if bits & bit)


def pair_rows(reports: Reports, kept: list, cluster_of: dict) -> list[dict]:
    rows = []
    for a, b, verdict, origin in kept:
        id_a, id_b = reports.hadith_id[a], reports.hadith_id[b]
        score, full, side = verdict.score, verdict.full, verdict.short_side
        if id_b < id_a:   # the unordered pair is stored with the smaller id first, as in v1
            a, b, id_a, id_b = b, a, id_b, id_a
            score = v1.PairScore(score.shared, score.size_b, score.size_a, score.local)
            full = v1.PairScore(full.shared, full.size_b, full.size_a, full.local)
            side = {"a": "b", "b": "a", "": ""}[side]
        pair_class = verdict.pair_class
        band_class = v1.CLASS_PARTIAL if pair_class in (logic2.CLASS_PARTIAL, logic2.CLASS_QUOTED) else v1.CLASS_VARIANT
        rows.append({
            "pair_id": v1build.pair_identifier(id_a, id_b), "hadith_id_a": id_a, "hadith_id_b": id_b,
            "tradition_a": reports.tradition[a], "tradition_b": reports.tradition[b],
            "work_a": reports.work[a], "work_b": reports.work[b],
            "source_work_id_a": reports.work_id[a], "source_work_id_b": reports.work_id[b],
            "hadith_no_a": reports.hadith_no[a], "hadith_no_b": reports.hadith_no[b],
            "source_record_id_a": reports.source_record_id[a], "source_record_id_b": reports.source_record_id[b],
            "arabic_sha256_a": reports.arabic_sha256[a], "arabic_sha256_b": reports.arabic_sha256[b],
            "scope": v1build.scope(reports, a, b), "tradition_pair": v1build.tradition_pair(reports, a, b),
            "class": pair_class,
            "jaccard": round(score.jaccard, 4), "containment": round(score.containment, 4),
            "global_containment": round(score.global_containment, 4), "length_ratio": round(score.length_ratio, 4),
            "shared_shingles": score.shared, "shingles_a": score.size_a, "shingles_b": score.size_b,
            "words_a": reports.words[a], "words_b": reports.words[b],
            "score_band": v1.score_band(score, band_class),
            "matn_method_a": reports.method[a], "matn_method_b": reports.method[b],
            "matn_split_a": reports.reliability[a], "matn_split_b": reports.reliability[b],
            "cluster_id": cluster_of.get(id_a, ""), "basis": "textual_overlap", "review_state": "unreviewed",
            "method_version": METHOD_VERSION,
            "jaccard_full": round(full.jaccard, 4), "containment_full": round(full.containment, 4),
            "words_residual_a": reports.residual_count[a], "words_residual_b": reports.residual_count[b],
            "short_side": side, "compiler_cut_a": int(reports.cut[a]), "compiler_cut_b": int(reports.cut[b]),
            "found_by": origin_label(origin), "_a": a, "_b": b,
        })
    rows.sort(key=lambda r: (r["hadith_id_a"], r["hadith_id_b"]))
    return rows


CLUSTER_INPUT_CLASS = {
    logic2.CLASS_SAME_WORDING: v1.CLASS_SAME_WORDING, logic2.CLASS_VARIANT: v1.CLASS_VARIANT,
    logic2.CLASS_SHORT_SAME_WORDING: v1.CLASS_SAME_WORDING, logic2.CLASS_PARTIAL: v1.CLASS_PARTIAL,
    logic2.CLASS_QUOTED: "quoted_node_only",
}


def make_clusters(reports: Reports, kept: list):
    """v1 star clustering with its one-to-one compound guard over the shown classes; formula_only pairs add nothing."""
    pairs = [(reports.hadith_id[a], reports.hadith_id[b], CLUSTER_INPUT_CLASS[v.pair_class])
             for a, b, v, _ in kept if v.pair_class in CLUSTER_INPUT_CLASS]
    lengths = {reports.hadith_id[i]: len(p.residual_shingles) for i, p in enumerate(reports.prepared) if p is not None}
    return v1.build_clusters(pairs, lengths)


def headline(reports: Reports, rows: list, cluster_of: dict, guard: dict) -> dict:
    shown = [r for r in rows if r["class"] in logic2.SHOWN_CLASSES]
    by_class = Counter(r["class"] for r in rows)
    scope_class = Counter(f"{r['scope']}|{r['class']}" for r in rows)
    matrix = Counter(f"{r['tradition_pair']}|{r['class']}" for r in rows if r["scope"] == "cross_tradition")
    bands = Counter(f"{r['class']}|{r['score_band']}" for r in rows)
    partners: dict[str, set] = defaultdict(set)
    for r in shown:
        if r["scope"] == "cross_tradition":
            partners[r["hadith_id_a"]].add(r["tradition_b"])
            partners[r["hadith_id_b"]].add(r["tradition_a"])
    index_of = {h: i for i, h in enumerate(reports.hadith_id)}
    with_counterpart = Counter(reports.tradition[index_of[h]] for h in partners)
    clusters: dict[str, list] = defaultdict(list)
    for hadith_id, cluster_id in cluster_of.items():
        clusters[cluster_id].append(index_of[hadith_id])
    span, span_combo, sizes = Counter(), Counter(), []
    for members in clusters.values():
        traditions = sorted({reports.tradition[i] for i in members}, key=TRADITION_ORDER.index)
        span[len(traditions)] += 1
        if len(traditions) > 1:
            span_combo["+".join(traditions)] += 1
        sizes.append(len(members))
    sizes.sort()
    return {
        "pairs_total": len(rows), "pairs_shown_classes": len(shown),
        "pairs_cross_tradition_shown_classes": sum(1 for r in shown if r["scope"] == "cross_tradition"),
        "pairs_by_class": dict(sorted(by_class.items())), "pairs_by_scope_and_class": dict(sorted(scope_class.items())),
        "cross_tradition_matrix_by_class": dict(sorted(matrix.items())),
        "pairs_by_class_and_band": dict(sorted(bands.items())),
        "reports_with_counterpart_in_another_tradition": dict(sorted(with_counterpart.items())),
        "reports_with_counterpart_in_another_tradition_total": sum(with_counterpart.values()),
        "clusters_total": len(clusters), "clusters_by_tradition_count": {str(k): v for k, v in sorted(span.items())},
        "multi_tradition_clusters_by_combination": dict(sorted(span_combo.items())),
        "cluster_size_median": sizes[len(sizes) // 2] if sizes else 0, "cluster_size_max": sizes[-1] if sizes else 0,
        "cluster_sizes_largest_20": sizes[::-1][:20], "cluster_guard": guard,
    }


# ─── Comparison with v1 ─────────────────────────────────────────────────────────────────────────────


def read_v1_pairs() -> dict:
    mapping = {}
    with open(V1_OUTPUT / "report_correspondence_pairs.csv", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mapping[(row["hadith_id_a"], row["hadith_id_b"])] = (row["class"], row["scope"], row["jaccard"])
    return mapping


def v1_cluster_sizes() -> tuple[dict, dict]:
    members: dict[str, list] = defaultdict(list)
    with open(V1_OUTPUT / "report_correspondence_cluster_members.csv", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            members[row["cluster_id"]].append((row["hadith_id"], row["work"], row["tradition"]))
    return members, {c: len(m) for c, m in members.items()}


def transition_table(rows: list, v1_pairs: dict) -> dict:
    v2 = {(r["hadith_id_a"], r["hadith_id_b"]): r for r in rows}
    table: Counter = Counter()
    cross: Counter = Counter()
    for key, (old_class, scope, _) in v1_pairs.items():
        new = v2.get(key)
        label = new["class"] if new else "absent_in_v2"
        table[f"{old_class} -> {label}"] += 1
        if scope == "cross_tradition":
            cross[f"{old_class} -> {label}"] += 1
    new_only = Counter(r["class"] for key, r in v2.items() if key not in v1_pairs)
    new_only_cross = Counter(r["class"] for key, r in v2.items() if key not in v1_pairs and r["scope"] == "cross_tradition")
    new_by_origin = Counter(f"{r['class']}|{r['found_by']}" for key, r in v2.items() if key not in v1_pairs)
    return {"v1_to_v2": dict(sorted(table.items())), "v1_to_v2_cross_tradition": dict(sorted(cross.items())),
            "v2_pairs_not_in_v1_by_class": dict(sorted(new_only.items())),
            "v2_pairs_not_in_v1_cross_tradition_by_class": dict(sorted(new_only_cross.items())),
            "v2_pairs_not_in_v1_by_class_and_origin": dict(sorted(new_by_origin.items()))}


def cluster_comparison(reports: Reports, cluster_of: dict) -> dict:
    members_v1, sizes_v1 = v1_cluster_sizes()
    v2_members: dict[str, list] = defaultdict(list)
    for hadith_id, cluster_id in cluster_of.items():
        v2_members[cluster_id].append(hadith_id)
    v2_size = {h: len(v2_members[c]) for h, c in cluster_of.items()}
    out = []
    for cluster_id, size in sorted(sizes_v1.items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
        ids = [h for h, _, _ in members_v1[cluster_id]]
        parts = Counter(cluster_of.get(h, "singleton_or_unlinked") for h in ids)
        largest = parts.most_common(1)[0]
        out.append({"v1_cluster_size": size, "works": dict(Counter(w for _, w, _ in members_v1[cluster_id]).most_common(3)),
                    "traditions": sorted({t for _, _, t in members_v1[cluster_id]}),
                    "v2_pieces": len(parts), "v2_largest_piece_of_these_members": largest[1],
                    "members_no_longer_in_any_shown_pair": parts.get("singleton_or_unlinked", 0),
                    "example_member": ids[0]})
    v2_largest = sorted(((len(m), c) for c, m in v2_members.items()), reverse=True)[:20]
    tahlil = "".join(["لا", "اله", "الا", "الله", "وحده", "لا", "شريك", "له"])
    letters_of_id = {h: "".join(w) for h, w in zip(reports.hadith_id, reports.word_lists)}
    carrying = []
    for cluster_id, size in sorted(sizes_v1.items(), key=lambda kv: (-kv[1], kv[0])):
        if size < 10:
            break
        ids = [h for h, _, _ in members_v1[cluster_id]]
        share = sum(1 for h in ids if tahlil in letters_of_id[h]) / size
        if share >= 0.3:
            parts = Counter(cluster_of.get(h, "unlinked") for h in ids)
            carrying.append({"v1_cluster_size": size, "share_of_members_with_tahlil": round(share, 2),
                             "v2_pieces": len(parts), "v2_largest_piece": parts.most_common(1)[0][1],
                             "example_member": ids[0]})
    return {"v1_largest_20_and_what_became_of_them": out, "v2_largest_20_sizes": [s for s, _ in v2_largest],
            "v1_clusters_of_10_or_more_where_30_percent_of_members_carry_the_tahlil": carrying[:15]}


# ─── Review worksheet ───────────────────────────────────────────────────────────────────────────────

SAMPLE_PLAN = (  # (class, number of pairs per score band); the bands of v1 are kept so readings are comparable
    (logic2.CLASS_VARIANT, 10), (logic2.CLASS_PARTIAL, 9), (logic2.CLASS_SAME_WORDING, 7),
    (logic2.CLASS_SHORT_SAME_WORDING, 12), (logic2.CLASS_QUOTED, 14), (logic2.CLASS_FORMULA_ONLY, 14))
WORKSHEET_COLUMNS = [
    "sample_no", "pair_id", "class", "score_band", "jaccard", "containment", "jaccard_full", "scope", "tradition_a",
    "work_a", "hadith_no_a", "hadith_id_a", "words_a", "words_residual_a", "matn_a", "compared_a", "tradition_b",
    "work_b", "hadith_no_b", "hadith_id_b", "words_b", "words_residual_b", "matn_b", "compared_b",
    "formula_spans_a", "formula_spans_b", "short_side", "reviewer_judgement", "reviewer_relation", "reviewer_note",
]


def stratified_sample(rows: list) -> list[dict]:
    rng = random.Random(SEED)
    chosen = []
    for pair_class, per_band in SAMPLE_PLAN:
        bands: dict[str, list] = defaultdict(list)
        for r in rows:
            if r["class"] == pair_class:
                bands[r["score_band"] if pair_class in (logic2.CLASS_VARIANT, logic2.CLASS_PARTIAL, logic2.CLASS_SAME_WORDING)
                      else "all"].append(r)
        if pair_class == logic2.CLASS_SAME_WORDING:   # the two same-wording bands are read together, as in v1
            merged = [r for key in sorted(bands) for r in bands[key]]
            bands = {"all": merged}
            per_band = per_band * 2
        for band in sorted(bands):
            pool = sorted(bands[band], key=lambda r: r["pair_id"])
            rng.shuffle(pool)
            # alternate cross-tradition and other pairs so the rare cross-tradition pairs are read
            cross = [r for r in pool if r["scope"] == "cross_tradition"]
            other = [r for r in pool if r["scope"] != "cross_tradition"]
            picked = []
            while len(picked) < per_band and (cross or other):
                for source in (cross, other):
                    if source and len(picked) < per_band:
                        picked.append(source.pop())
            chosen.extend(picked)
    chosen.sort(key=lambda r: (r["class"], r["score_band"], r["scope"], r["pair_id"]))
    return chosen


def spans_text(reports: Reports, index: int, id_lists: list, frequent: set, quran_keys: set) -> str:
    ids = id_lists[index]
    if len(ids) < logic2.GRAM_WORDS:
        return ""
    flags = logic2.formula_flags(ids, frequent, quran_keys)
    return " | ".join(f"{kind}: {text}" for kind, text in logic2.formula_runs(reports.word_lists[index], flags))


def write_csv(path: Path, columns: list, rows) -> int:
    return v1build.write_csv(path, columns, rows)


def famous_check(reports: Reports, normalizer, rows: list) -> list[dict]:
    shown = [r for r in rows if r["class"] in logic2.SHOWN_CLASSES]
    letters_of = ["".join(words) for words in reports.word_lists]
    out = []
    for key, phrase in v1build.FAMOUS_PHRASES:
        needle = "".join(normalizer.words(phrase))
        carriers = {i for i, text in enumerate(letters_of) if needle and needle in text}
        carrier_ids = {reports.hadith_id[i] for i in carriers}
        by_tradition = Counter(reports.tradition[i] for i in carriers)
        linked: Counter = Counter()
        formula_only_cross = 0
        examples = []
        for r in rows:
            if r["hadith_id_a"] in carrier_ids and r["hadith_id_b"] in carrier_ids and r["scope"] == "cross_tradition":
                if r["class"] in logic2.SHOWN_CLASSES:
                    linked[f"{r['tradition_pair']}|{r['class']}"] += 1
                    if len(examples) < 3:
                        examples.append([r["hadith_id_a"], r["hadith_id_b"], r["class"], r["jaccard"]])
                else:
                    formula_only_cross += 1
        out.append({"key": key, "phrase": phrase, "carriers_by_tradition": dict(sorted(by_tradition.items())),
                    "cross_tradition_links_by_traditions_and_class": dict(sorted(linked.items())),
                    "cross_tradition_formula_only_pairs": formula_only_cross, "example_linked_pairs": examples})
    return out


def output_subdirectory() -> str:
    """'output' by default; --out NAME writes elsewhere (used to compare two runs byte for byte)."""
    return sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "output"


def main() -> None:
    started = time.time()
    out_dir = common.output_directory(f"{JOB}/{output_subdirectory()}")
    reports, meta, normalizer = read_corpus(started)
    vocabulary = Vocabulary()
    quran_words = load_quran(normalizer)
    quran_keys = logic2.quran_gram_keys(quran_words, vocabulary.id)
    frequent, exact_counts, id_lists = build_formula_inventory(reports, vocabulary, quran_keys, started)
    gram_text = {}
    for words, ids in zip(reports.word_lists, id_lists):
        for position, key in enumerate(logic2.gram_keys(ids, logic2.GRAM_WORDS)):
            if key in frequent and key not in gram_text:
                gram_text[key] = " ".join(words[position:position + logic2.GRAM_WORDS])
    formula_stats, run_documents = prepare_reports(reports, id_lists, frequent, quran_keys, started)
    eligible = sum(1 for p in reports.prepared if p is not None)
    progress(f"{eligible} reports eligible (>= {logic2.SHORT_MIN_WORDS} words)", started)

    pairs, lsh_stats = candidate_pairs_for_all(reports, started)
    kept = score_candidates(reports, pairs, started)
    progress(f"{len(kept)} pairs kept of {len(pairs)} candidates", started)
    cluster_of, centre_of, guard = make_clusters(reports, kept)
    rows = pair_rows(reports, kept, cluster_of)

    pair_count = write_csv(out_dir / "report_correspondence_pairs.csv", PAIR_COLUMNS, rows)
    v1build.write_jsonl(out_dir / "report_correspondence_pairs.jsonl", PAIR_COLUMNS, rows)
    index_of = {h: i for i, h in enumerate(reports.hadith_id)}
    cluster_rows = [{
        "cluster_id": cluster_id, "hadith_id": hadith_id, "tradition": reports.tradition[index_of[hadith_id]],
        "work": reports.work[index_of[hadith_id]], "source_work_id": reports.work_id[index_of[hadith_id]],
        "hadith_no": reports.hadith_no[index_of[hadith_id]], "star_centre": centre_of[hadith_id],
        "is_star_centre": centre_of[hadith_id] == hadith_id, "basis": "textual_overlap",
        "review_state": "unreviewed", "method_version": METHOD_VERSION,
    } for hadith_id, cluster_id in sorted(cluster_of.items(), key=lambda kv: (kv[1], kv[0]))]
    member_count = write_csv(out_dir / "report_correspondence_cluster_members.csv", list(cluster_rows[0]), cluster_rows)

    # formula inventory outputs
    gram_rows = [{"documents": exact_counts[key], "text": text} for key, text in sorted(
        gram_text.items(), key=lambda kv: (-exact_counts[kv[0]], kv[1]))]
    write_csv(out_dir / "formula_inventory_4grams.csv", ["documents", "text"], gram_rows)
    run_rows = [{"kind": kind, "documents": count, "text": text, "words": len(text.split())}
                for (kind, text), count in sorted(run_documents.items(), key=lambda kv: (-kv[1], kv[0]))[:400]]
    formula_runs_count = write_csv(out_dir / "formula_inventory_top_runs.csv", ["kind", "documents", "words", "text"], run_rows)
    quran_runs = [r for r in run_rows if r["kind"] == "quran"][:25]

    sample = stratified_sample(rows)
    worksheet = []
    for number, r in enumerate(sample, 1):
        a, b = r["_a"], r["_b"]
        worksheet.append({
            **{k: r[k] for k in WORKSHEET_COLUMNS if k in r}, "sample_no": number,
            "matn_a": reports.matn[a], "matn_b": reports.matn[b],
            "compared_a": " ".join(reports.word_lists[a]), "compared_b": " ".join(reports.word_lists[b]),
            "formula_spans_a": spans_text(reports, a, id_lists, frequent, quran_keys),
            "formula_spans_b": spans_text(reports, b, id_lists, frequent, quran_keys),
            "reviewer_judgement": "", "reviewer_relation": "", "reviewer_note": "",
        })
    sample_count = write_csv(out_dir / "review_worksheet_150.csv", WORKSHEET_COLUMNS, worksheet)
    coverage = v1build.coverage_table(reports)
    famous = famous_check(reports, normalizer, rows)
    transitions = transition_table(rows, read_v1_pairs())
    clusters_cmp = cluster_comparison(reports, cluster_of)
    common.write_json(out_dir, "transition_v1_to_v2.json", transitions)
    common.write_json(out_dir, "cluster_comparison.json", clusters_cmp)

    summary = common.header_object(JOB, COMMAND, common.input_fingerprints(
        v1build.CORPUS, v1build.RECONCILED / "pure_canon_chain.jsonl.gz", v1build.RECONCILED / "no_chain_in_source.jsonl.gz",
        v1build.REGISTRY, common.HADITH_DATA_DIR / "regen_unified_csvs.py",
        common.HADITH_DATA_DIR / "extract_isnad_unified.py", common.DATASETS_DIR / "classify_attribution.py",
        QURAN_FILE, logic2.GRADING_RECOVERY_DIR / "mine_grading_sources.py",
        logic2.DIAGNOSTICS_DIR / "extract_tirmidhi_compiler_statements.py"))
    summary["code_sha256"] = common.input_fingerprints(
        JOB_DIR / "build_report_correspondence_v2.py", JOB_DIR / "correspondence_logic_v2.py",
        logic2.V1_DIR / "correspondence_logic.py", logic2.V1_DIR / "matn_isolation.py",
        logic2.V1_DIR / "build_report_correspondence.py")
    summary["parameters"] = {k: getattr(logic2, k) for k in (
        "GRAM_WORDS", "FORMULA_MIN_DOCUMENTS", "FORMULA_MIN_RUN_WORDS", "QUOTED_MIN_SHINGLES", "QUOTED_MAX_ANCHOR_DOCUMENTS", "RESCUE_RESIDUAL_JACCARD", "RESCUE_RESIDUAL_CONTAINMENT", "QURAN_GRAM_WORDS", "MIN_RESIDUAL_WORDS", "MIN_SHARED_RESIDUAL_SHINGLES",
        "PARTIAL_MIN_RESIDUAL_WORDS", "SHORT_MIN_WORDS", "SHORT_SAME_WORDING_JACCARD", "SHORT_MIN_SHARED_SHINGLES",
        "SHORT_LENGTH_RATIO", "QUOTED_CONTAINMENT", "QUOTED_MIN_RATIO", "QUOTED_MIN_EXTRA_WORDS",
        "QUOTED_MAX_SAYING_WORDS", "SHORT_POSTING_CAP", "CONTENT_MAX_DOCUMENT_SHARE", "CONTENT_MIN_TOKENS")}
    summary["parameters"].update({"method_version": METHOD_VERSION, "seed": SEED, "bucket_cap": BUCKET_CAP,
                                  "v1_parameters_reused": {"shingle_letters": v1.SHINGLE_LETTERS, "lsh_bands": v1.LSH_BANDS,
                                                           "lsh_rows": v1.LSH_ROWS, "window_words": v1.WINDOW_WORDS}})
    summary["corpus"] = {**meta, "eligible_for_matching_3_words_or_more": eligible,
                         "frequent_word_4grams_in_inventory": len(frequent), "quran_5word_spans": len(quran_keys),
                         "reports_with_formula_words": formula_stats["reports_with_formula_words"]}
    summary["lsh"] = lsh_stats
    summary["headline"] = headline(reports, rows, cluster_of, guard)
    summary["famous_report_check"] = famous
    summary["quran_runs_top"] = quran_runs
    summary["outputs"] = {"report_correspondence_pairs.csv": pair_count, "report_correspondence_pairs.jsonl": pair_count,
                          "report_correspondence_cluster_members.csv": member_count,
                          "formula_inventory_top_runs.csv": formula_runs_count, "formula_inventory_4grams.csv": len(gram_rows), "review_worksheet_150.csv": sample_count}
    summary.pop("generated_at_utc", None)
    common.write_json(out_dir, "summary.json", summary)
    common.write_json(out_dir, "run_log.json", {"runtime_seconds": round(time.time() - started, 1),
                                                 "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    progress(f"done: {pair_count} pairs, {member_count} cluster members, sample {sample_count}", started)


if __name__ == "__main__":
    main()
