"""Find reports whose matn corresponds across traditions and works; write unreviewed candidate pairs and clusters.

Method, parameters, outputs and the proposed table: README.md in this directory. Read-only on every input; writes
only under diagnostics/report-correspondence/output/. Standard library only, deterministic.

    python -B datasets/hadith-data/diagnostics/report-correspondence/build_report_correspondence.py
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import random
import sys
import time
from array import array
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
JOB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(JOB_DIR.parent))
sys.path.insert(0, str(JOB_DIR))

import diagnostic_common as common  # noqa: E402
import correspondence_logic as logic  # noqa: E402
import matn_isolation as isolation  # noqa: E402

JOB = "report-correspondence"
COMMAND = "python -B datasets/hadith-data/diagnostics/report-correspondence/build_report_correspondence.py"
CORPUS = common.HADITH_DATA_DIR / "development" / "incomplete-curation" / "all_hadiths_unified.incomplete.csv.gz"
RECONCILED = common.HADITH_DATA_DIR / "reconciled"
REGISTRY = common.HADITH_DATA_DIR / "neo4j_export" / "source_work_registry.json"
METHOD_VERSION = "report-correspondence-v1"
SEED = 20261121
SAMPLE_SIZE = 150
BUCKET_CAP = 60              # an LSH bucket holding more reports than this is a formula bucket (README §Method)
MIN_WINDOW_SHINGLES = 12     # a window with fewer non-stop shingles gets no signature
PAIR_SHIFT = 17              # report index < 2**17
MAX_CANDIDATES = 10_000_000  # memory guard on the candidate set

TRADITION_ORDER = ("Sunni", "Imami", "Zaydi", "Ibadi")

# Distinctive phrases of widely transmitted reports (README §Famous-report check). Search only, never forced.
FAMOUS_PHRASES = (
    ("actions_by_intentions", "إنما الأعمال بالنيات"),
    ("ghadir_mawla", "من كنت مولاه فعلي مولاه"),
    ("thaqalayn", "إني تارك فيكم الثقلين"),
    ("manzila_harun", "بمنزلة هارون من موسى"),
    ("islam_built_on_five", "بني الإسلام على خمس"),
    ("no_harm", "لا ضرر ولا ضرار"),
    ("seeking_knowledge_duty", "طلب العلم فريضة على كل مسلم"),
    ("city_of_knowledge", "أنا مدينة العلم وعلي بابها"),
    ("lying_upon_me", "من كذب علي متعمدا فليتبوأ مقعده من النار"),
    ("halal_clear_haram_clear", "الحلال بين والحرام بين"),
    ("love_for_brother", "حتى يحب لأخيه ما يحب لنفسه"),
    ("religion_is_sincerity", "الدين النصيحة"),
    ("ark_of_nuh", "كمثل سفينة نوح"),
    ("imam_of_his_time", "من مات ولم يعرف إمام زمانه"),
    ("oath_on_defendant", "اليمين على المدعى عليه"),
)


def progress(message: str, started: float) -> None:
    print(f"[{time.time() - started:7.1f}s] {message}", flush=True)


def load_work_ids() -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {(w["tradition"], w["canonical_source"]): w["source_work_id"] for w in registry["source_works"]}


class Reports:
    """Column store for the corpus: one entry per row, in corpus order."""

    def __init__(self):
        self.hadith_id: list[str] = []
        self.tradition: list[str] = []
        self.work: list[str] = []
        self.work_id: list[str] = []
        self.hadith_no: list[str] = []
        self.arabic_sha256: list[str] = []
        self.source_record_id: list[str] = []
        self.method: list[str] = []
        self.reliability: list[str] = []
        self.note: list[str] = []
        self.words: array = array("I")
        self.matn: list[str] = []
        self.comparison: list[str] = []
        self.letters: list[bytes] = []
        self.shingles: list[array] = []
        self.eligible: bytearray = bytearray()

    def __len__(self):
        return len(self.hadith_id)


def read_corpus(started: float) -> tuple[Reports, dict, object]:
    regen = common.load_regen()
    extractor = common.load_extractor()
    normalizer = logic.ComparisonNormalizer(regen)
    matn_only, no_chain = isolation.load_sidecars(RECONCILED)
    isolator = isolation.MatnIsolator(extractor, matn_only, no_chain)
    work_ids = load_work_ids()
    reports = Reports()
    df = array("I", bytes(4 * (1 << 24)))   # approximate document frequency, indexed by the top 24 hash bits
    work_id_conflicts = 0
    with gzip.open(CORPUS, "rt", encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            tradition = row["tradition"].strip()
            work = row["source"].strip()
            registry_work = work_ids.get((tradition, work), "")
            row_work = row["source_work_id"].strip()
            if row_work and registry_work and row_work != registry_work:
                work_id_conflicts += 1
            matn, method, reliability, note = isolator.isolate(row)
            words = normalizer.words(matn) if matn else []
            letters = logic.letters_bytes(words)
            shingles = logic.shingle_set(words) if words else array("I")
            eligible = bool(words) and len(words) >= logic.MIN_WORDS and len(shingles) > 0
            reports.hadith_id.append(f"hadith:{row['record_id'].strip()}")
            reports.tradition.append(tradition)
            reports.work.append(work)
            reports.work_id.append(row_work or registry_work)
            reports.hadith_no.append(row["hadith_no"].strip())
            reports.arabic_sha256.append(isolation.sha256_text(row["text_ar"]))
            reports.source_record_id.append(row["source_record_id"].strip())
            reports.method.append(method)
            reports.reliability.append(reliability)
            reports.note.append(note)
            reports.words.append(len(words))
            reports.matn.append(matn)
            reports.comparison.append(" ".join(words))
            reports.letters.append(letters if eligible else b"")
            reports.shingles.append(shingles if eligible else array("I"))
            reports.eligible.append(1 if eligible else 0)
            if eligible:
                for value in shingles:
                    df[value >> 8] += 1
            if index % 20000 == 0:
                progress(f"read {index} rows", started)
    if len(reports) >= 1 << PAIR_SHIFT:
        raise RuntimeError("corpus larger than the pair-key encoding allows")
    meta = {"work_id_conflicts": work_id_conflicts, "sidecar_hash_mismatches": isolator.sidecar_hash_mismatches}
    return reports, meta, (df, normalizer)


def signatures(reports: Reports, df: array, stop_threshold: int, started: float):
    """Band keys for every window of every eligible report (window-major array) and the owning report index."""
    keys = array("Q")
    owner = array("I")
    windows_without_signature = 0
    for index in range(len(reports)):
        if not reports.eligible[index]:
            continue
        letters = reports.letters[index]
        words = reports.comparison[index].split()
        for start, end in logic.window_letter_spans(words):
            hashes = [h for h in set(logic.shingle_hashes_at(letters, start, end)) if df[h >> 8] <= stop_threshold]
            if len(hashes) < MIN_WINDOW_SHINGLES:
                windows_without_signature += 1
                continue
            for salt in logic.LSH_SIGNATURE_SALTS:
                keys.extend(logic.band_keys(logic.one_permutation_minhash(hashes, salt)))
            owner.append(index)
        if index % 20000 == 0:
            progress(f"signatures up to row {index}: {len(owner)} windows", started)
    return keys, owner, windows_without_signature


def candidate_pairs(keys: array, owner: array, started: float) -> tuple[set, dict]:
    pairs: set[int] = set()
    sizes = Counter()
    capped_buckets = 0
    capped_reports = set()
    count = len(owner)
    columns = logic.LSH_BANDS * len(logic.LSH_SIGNATURE_SALTS)
    for band in range(columns):
        column = sorted(zip(keys[band::columns], owner)) if count else []
        position = 0
        while position < len(column):
            end = position + 1
            while end < len(column) and column[end][0] == column[position][0]:
                end += 1
            if end - position > 1:
                members = sorted({doc for _, doc in column[position:end]})
                size = len(members)
                if size > 1:
                    sizes[min(size, 1000)] += 1
                if size > BUCKET_CAP:
                    capped_buckets += 1
                    capped_reports.update(members)
                elif size > 1:
                    for i, a in enumerate(members):
                        base = a << PAIR_SHIFT
                        for b in members[i + 1:]:
                            pairs.add(base | b)
            position = end
        progress(f"band {band + 1}/{columns}: {len(pairs)} candidate pairs", started)
        if len(pairs) > MAX_CANDIDATES:
            raise RuntimeError(f"more than {MAX_CANDIDATES} candidate pairs: LSH parameters too loose for bounded memory")
    stats = {
        "buckets_with_2_or_more_reports": sum(sizes.values()),
        "buckets_over_cap": capped_buckets,
        "reports_in_capped_buckets": len(capped_reports),
        "largest_bucket_sizes": sorted(sizes.items(), reverse=True)[:10],
    }
    return pairs, stats


def make_sequence_cache(reports: Reports):
    from functools import lru_cache

    @lru_cache(maxsize=4096)
    def sequence(index: int) -> list[int]:
        return logic.shingle_hashes_at(reports.letters[index])

    return sequence


def exact_score(reports: Reports, a: int, b: int, set_a: set, sequence) -> logic.PairScore:
    """Exact scores of one pair; containment is local when one text is much longer (README §Scores)."""
    shared = len(set_a.intersection(reports.shingles[b]))
    score = logic.PairScore(shared, len(set_a), len(reports.shingles[b]))
    positions_a, positions_b = len(reports.letters[a]), len(reports.letters[b])
    gate = min(logic.VARIANT_CONTAINMENT, logic.PARTIAL_CONTAINMENT)
    if score.global_containment >= gate and logic.needs_local_containment(positions_a, positions_b):
        if positions_a <= positions_b:
            local = logic.local_containment(set_a, sequence(b), positions_a)
        else:
            local = logic.local_containment(set(reports.shingles[b]), sequence(a), positions_b)
        score = logic.PairScore(shared, score.size_a, score.size_b, local)
    return score


def score_candidates(reports: Reports, pairs: set, started: float) -> list[tuple]:
    sequence = make_sequence_cache(reports)
    kept = []
    current = -1
    current_set: set = set()
    for done, key in enumerate(sorted(pairs)):
        a, b = key >> PAIR_SHIFT, key & ((1 << PAIR_SHIFT) - 1)
        if a != current:
            current, current_set = a, set(reports.shingles[a])
        score = exact_score(reports, a, b, current_set, sequence)
        pair_class = logic.classify(score, reports.words[a], reports.words[b])
        if pair_class is not None:
            kept.append((a, b, pair_class, score))
        if done % 200000 == 0:
            progress(f"scored {done}/{len(pairs)}; kept {len(kept)}", started)
    return kept


def scope(reports: Reports, a: int, b: int) -> str:
    if reports.tradition[a] != reports.tradition[b]:
        return "cross_tradition"
    if reports.work[a] != reports.work[b]:
        return "cross_work_same_tradition"
    return "same_work"


def tradition_pair(reports: Reports, a: int, b: int) -> str:
    ta, tb = sorted((reports.tradition[a], reports.tradition[b]), key=TRADITION_ORDER.index)
    return f"{ta}-{tb}"


def pair_identifier(id_a: str, id_b: str) -> str:
    return "report-pair:" + hashlib.sha256(f"{id_a}\x1f{id_b}".encode("utf-8")).hexdigest()[:20]


PAIR_COLUMNS = [
    "pair_id", "hadith_id_a", "hadith_id_b", "tradition_a", "tradition_b", "work_a", "work_b", "source_work_id_a",
    "source_work_id_b", "hadith_no_a", "hadith_no_b", "source_record_id_a",
    "source_record_id_b", "arabic_sha256_a", "arabic_sha256_b", "scope", "tradition_pair", "class", "jaccard", "containment",
    "global_containment", "length_ratio", "shared_shingles", "shingles_a", "shingles_b", "words_a", "words_b", "score_band",
    "matn_method_a", "matn_method_b", "matn_split_a", "matn_split_b", "cluster_id", "basis", "review_state",
    "method_version",
]


def pair_rows(reports: Reports, kept: list, cluster_of: dict):
    rows = []
    for a, b, pair_class, score in kept:
        id_a, id_b = reports.hadith_id[a], reports.hadith_id[b]
        if id_b < id_a:   # unordered pair stored with the smaller id first
            a, b, id_a, id_b = b, a, id_b, id_a
            score = logic.PairScore(score.shared, score.size_b, score.size_a, score.local)
        rows.append({
            "pair_id": pair_identifier(id_a, id_b), "hadith_id_a": id_a, "hadith_id_b": id_b,
            "tradition_a": reports.tradition[a], "tradition_b": reports.tradition[b],
            "work_a": reports.work[a], "work_b": reports.work[b],
            "source_work_id_a": reports.work_id[a], "source_work_id_b": reports.work_id[b],
            "hadith_no_a": reports.hadith_no[a], "hadith_no_b": reports.hadith_no[b],
            "source_record_id_a": reports.source_record_id[a], "source_record_id_b": reports.source_record_id[b],
            "arabic_sha256_a": reports.arabic_sha256[a], "arabic_sha256_b": reports.arabic_sha256[b],
            "scope": scope(reports, a, b), "tradition_pair": tradition_pair(reports, a, b), "class": pair_class,
            "jaccard": round(score.jaccard, 4), "containment": round(score.containment, 4),
            "global_containment": round(score.global_containment, 4),
            "length_ratio": round(score.length_ratio, 4), "shared_shingles": score.shared,
            "shingles_a": score.size_a, "shingles_b": score.size_b,
            "words_a": reports.words[a], "words_b": reports.words[b],
            "score_band": logic.score_band(score, pair_class),
            "matn_method_a": reports.method[a], "matn_method_b": reports.method[b],
            "matn_split_a": reports.reliability[a], "matn_split_b": reports.reliability[b],
            "cluster_id": cluster_of[id_a], "basis": "textual_overlap", "review_state": "unreviewed",
            "method_version": METHOD_VERSION,
            "_a": a, "_b": b,
        })
    rows.sort(key=lambda r: (r["hadith_id_a"], r["hadith_id_b"]))
    return rows


def write_csv(path: Path, columns: list, rows) -> int:
    handle, _ = common.open_output(path.parent, path.name)
    count = 0
    with handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def write_jsonl(path: Path, columns: list, rows) -> int:
    return common.write_jsonl(path.parent, path.name, ({c: r[c] for c in columns} for r in rows))


def coverage_table(reports: Reports) -> list[dict]:
    table: dict = {}
    for i in range(len(reports)):
        key = (reports.tradition[i], reports.work[i])
        entry = table.setdefault(key, Counter())
        entry["reports"] += 1
        entry[f"method:{reports.method[i]}"] += 1
        if reports.method[i] == isolation.METHOD_NONE:
            entry["no_usable_matn"] += 1
        elif reports.reliability[i] == isolation.RELIABLE:
            entry["usable_reliable_split"] += 1
        else:
            entry["usable_flagged_split"] += 1
        if reports.note[i] == isolation.MATN_COLUMN_NOT_IN_TEXT:
            entry["matn_column_rejected_not_in_text"] += 1
        if reports.note[i] == isolation.MATN_COLUMN_INCLUDES_CHAIN:
            entry["matn_column_rejected_includes_chain"] += 1
        if reports.method[i] != isolation.METHOD_NONE and not reports.eligible[i]:
            entry["below_min_words"] += 1
        if reports.eligible[i]:
            entry["eligible_for_matching"] += 1
    rows = []
    for (tradition, work), entry in sorted(table.items(), key=lambda kv: (TRADITION_ORDER.index(kv[0][0]), kv[0][1])):
        rows.append({"tradition": tradition, "work": work, **entry})
    return rows


COVERAGE_COLUMNS = [
    "tradition", "work", "reports", "usable_reliable_split", "usable_flagged_split", "no_usable_matn",
    "below_min_words", "eligible_for_matching", "matn_column_rejected_not_in_text",
    "matn_column_rejected_includes_chain",
    "method:source_text_is_matn_only", "method:no_chain_in_source", "method:matn_column", "method:extractor_boundary",
    "method:whole_text_no_reliable_boundary", "method:no_usable_matn",
]


def headline(reports: Reports, rows: list, cluster_of: dict, guard: dict) -> dict:
    by_class = Counter(r["class"] for r in rows)
    by_scope = Counter(r["scope"] for r in rows)
    scope_class = Counter(f"{r['scope']}|{r['class']}" for r in rows)
    matrix = Counter(r["tradition_pair"] for r in rows if r["scope"] == "cross_tradition")
    matrix_strong = Counter(r["tradition_pair"] for r in rows
                            if r["scope"] == "cross_tradition" and r["class"] in logic.STRONG_CLASSES)
    bands = Counter(f"{r['class']}|{r['score_band']}" for r in rows)
    cross_partners: dict[str, set] = defaultdict(set)
    for r in rows:
        if r["scope"] == "cross_tradition":
            cross_partners[r["hadith_id_a"]].add(r["tradition_b"])
            cross_partners[r["hadith_id_b"]].add(r["tradition_a"])
    with_counterpart = Counter()
    index_of = {h: i for i, h in enumerate(reports.hadith_id)}
    for hadith_id in cross_partners:
        with_counterpart[reports.tradition[index_of[hadith_id]]] += 1
    clusters: dict[str, list[int]] = defaultdict(list)
    for hadith_id, cluster_id in cluster_of.items():
        clusters[cluster_id].append(index_of[hadith_id])
    span = Counter()
    span_combo = Counter()
    sizes = []
    for members in clusters.values():
        traditions = sorted({reports.tradition[i] for i in members}, key=TRADITION_ORDER.index)
        span[len(traditions)] += 1
        if len(traditions) > 1:
            span_combo["+".join(traditions)] += 1
        sizes.append(len(members))
    sizes.sort()
    eligible_by_tradition = Counter(reports.tradition[i] for i in range(len(reports)) if reports.eligible[i])
    return {
        "pairs_total": len(rows),
        "pairs_by_class": dict(sorted(by_class.items())),
        "pairs_by_scope": dict(sorted(by_scope.items())),
        "pairs_by_scope_and_class": dict(sorted(scope_class.items())),
        "cross_tradition_matrix_all_classes": dict(sorted(matrix.items())),
        "cross_tradition_matrix_strong_classes": dict(sorted(matrix_strong.items())),
        "pairs_by_class_and_band": dict(sorted(bands.items())),
        "reports_with_counterpart_in_another_tradition": dict(sorted(with_counterpart.items())),
        "reports_with_counterpart_in_another_tradition_total": sum(with_counterpart.values()),
        "eligible_reports_by_tradition": dict(sorted(eligible_by_tradition.items())),
        "clusters_total": len(clusters),
        "clusters_by_tradition_count": {str(k): v for k, v in sorted(span.items())},
        "multi_tradition_clusters_by_combination": dict(sorted(span_combo.items())),
        "cluster_size_median": sizes[len(sizes) // 2] if sizes else 0,
        "cluster_size_max": sizes[-1] if sizes else 0,
        "cluster_guard": guard,
    }


def stratified_sample(rows: list) -> list[dict]:
    """150 pairs: equal allocation over (class, score band, cross-tradition or not) strata, fixed seed."""
    strata: dict[tuple, list] = defaultdict(list)
    for r in rows:
        strata[(r["class"], r["score_band"], r["scope"] == "cross_tradition")].append(r)
    keys = sorted(strata)
    rng = random.Random(SEED)
    remaining = SAMPLE_SIZE
    chosen: list[dict] = []
    pools = {k: list(strata[k]) for k in keys}
    for k in keys:
        rng.shuffle(pools[k])
    while remaining > 0 and any(pools.values()):
        for k in keys:
            if remaining == 0:
                break
            if pools[k]:
                chosen.append(pools[k].pop())
                remaining -= 1
    chosen.sort(key=lambda r: (r["class"], r["score_band"], r["scope"], r["pair_id"]))
    return chosen


WORKSHEET_COLUMNS = [
    "sample_no", "pair_id", "class", "score_band", "jaccard", "containment", "scope", "tradition_a", "work_a",
    "hadith_no_a", "source_record_id_a", "hadith_id_a", "matn_split_a", "matn_a", "tradition_b", "work_b",
    "hadith_no_b", "source_record_id_b", "hadith_id_b", "matn_split_b", "matn_b", "shared_passage_in_longer_text",
    "reviewer_judgement", "reviewer_relation", "reviewer_note", "reviewer_id",
    "reviewed_at",
]


def shared_passage(reports: Reports, a: int, b: int) -> str:
    """Comparison-text words of the longer matn around its best local window (a reviewer aid for partials)."""
    short, long = (a, b) if len(reports.letters[a]) <= len(reports.letters[b]) else (b, a)
    words = reports.comparison[long].split()
    start, end = logic.best_window_words(set(reports.shingles[short]), words, len(reports.letters[short]))
    return " ".join(words[start:end])


def famous_check(reports: Reports, normalizer, rows: list, cluster_of: dict) -> list[dict]:
    partners: dict[str, set] = defaultdict(set)
    for r in rows:
        partners[r["hadith_id_a"]].add(r["hadith_id_b"])
        partners[r["hadith_id_b"]].add(r["hadith_id_a"])
    letters_of = [c.replace(" ", "") for c in reports.comparison]
    out = []
    for key, phrase in FAMOUS_PHRASES:
        needle = "".join(normalizer.words(phrase))
        carriers = [i for i, text in enumerate(letters_of) if needle and needle in text]
        by_tradition = Counter(reports.tradition[i] for i in carriers)
        carrier_ids = {reports.hadith_id[i] for i in carriers}
        index_of = {reports.hadith_id[i]: i for i in carriers}
        linked_cross = set()
        examples = []
        for hadith_id in sorted(carrier_ids):
            for other in sorted(partners.get(hadith_id, ())):
                if other in carrier_ids and reports.tradition[index_of[other]] != reports.tradition[index_of[hadith_id]]:
                    pair = tuple(sorted((reports.tradition[index_of[hadith_id]], reports.tradition[index_of[other]]),
                                        key=TRADITION_ORDER.index))
                    linked_cross.add("-".join(pair))
                    if len(examples) < 3 and hadith_id < other:
                        examples.append([hadith_id, other])
        eligible = Counter(reports.tradition[i] for i in carriers if reports.eligible[i])
        out.append({
            "key": key, "phrase": phrase, "carriers_by_tradition": dict(sorted(by_tradition.items())),
            "eligible_carriers_by_tradition": dict(sorted(eligible.items())),
            "traditions_with_phrase": len(by_tradition),
            "cross_tradition_links_found_between_carriers": sorted(linked_cross),
            "example_linked_pairs": examples,
        })
    return out


def main() -> None:
    started = time.time()
    out_dir = common.output_directory(f"{JOB}/output")
    reports, meta, (df, normalizer) = read_corpus(started)
    eligible_count = sum(reports.eligible)
    stop_threshold = max(1, int(eligible_count * logic.STOP_SHINGLE_DOCUMENT_SHARE))
    stop_slots = sum(1 for v in df if v > stop_threshold)
    progress(f"corpus read: {len(reports)} rows, {eligible_count} eligible; stop threshold {stop_threshold}, "
             f"{stop_slots} stop-shingle slots", started)

    keys, owner, no_signature = signatures(reports, df, stop_threshold, started)
    windows_signed = len(owner)
    del df
    progress(f"{len(owner)} windows signed; {no_signature} windows too short after stop-shingles", started)
    pairs, lsh_stats = candidate_pairs(keys, owner, started)
    del keys, owner
    kept = score_candidates(reports, pairs, started)
    candidate_count = len(pairs)
    del pairs
    progress(f"{len(kept)} pairs kept of {candidate_count} candidates", started)

    lengths = {reports.hadith_id[i]: len(reports.shingles[i]) for i in range(len(reports)) if reports.eligible[i]}
    cluster_of, centre_of, guard = logic.build_clusters(
        ((reports.hadith_id[a], reports.hadith_id[b], c) for a, b, c, _ in kept), lengths)
    rows = pair_rows(reports, kept, cluster_of)

    pair_count = write_csv(out_dir / "report_correspondence_pairs.csv", PAIR_COLUMNS, rows)
    write_jsonl(out_dir / "report_correspondence_pairs.jsonl", PAIR_COLUMNS, rows)
    index_of = {h: i for i, h in enumerate(reports.hadith_id)}
    members = sorted(cluster_of.items(), key=lambda kv: (kv[1], kv[0]))
    cluster_rows = [{
        "cluster_id": cluster_id, "hadith_id": hadith_id, "tradition": reports.tradition[index_of[hadith_id]],
        "work": reports.work[index_of[hadith_id]], "source_work_id": reports.work_id[index_of[hadith_id]],
        "hadith_no": reports.hadith_no[index_of[hadith_id]], "star_centre": centre_of[hadith_id],
        "is_star_centre": centre_of[hadith_id] == hadith_id, "basis": "textual_overlap",
        "review_state": "unreviewed", "method_version": METHOD_VERSION,
    } for hadith_id, cluster_id in members]
    cluster_columns = list(cluster_rows[0]) if cluster_rows else ["cluster_id", "hadith_id"]
    member_count = write_csv(out_dir / "report_correspondence_cluster_members.csv", cluster_columns, cluster_rows)
    coverage = coverage_table(reports)
    write_csv(out_dir / "matn_isolation_coverage.csv", COVERAGE_COLUMNS, coverage)
    flagged = [{
        "hadith_id": reports.hadith_id[i], "tradition": reports.tradition[i], "work": reports.work[i],
        "hadith_no": reports.hadith_no[i], "matn_method": reports.method[i], "matn_split": reports.reliability[i],
        "note": reports.note[i],
    } for i in range(len(reports)) if reports.reliability[i] != isolation.RELIABLE or reports.note[i]]
    flag_count = write_csv(out_dir / "matn_isolation_flags.csv", list(flagged[0]) if flagged else ["hadith_id"],
                           flagged)

    sample = stratified_sample(rows)
    worksheet = []
    for number, r in enumerate(sample, 1):
        worksheet.append({
            **{k: r[k] for k in WORKSHEET_COLUMNS if k in r}, "sample_no": number,
            "matn_a": reports.matn[r["_a"]], "matn_b": reports.matn[r["_b"]],
            "shared_passage_in_longer_text": shared_passage(reports, r["_a"], r["_b"]),
            "reviewer_judgement": "", "reviewer_relation": "", "reviewer_note": "", "reviewer_id": "",
            "reviewed_at": "",
        })
    sample_count = write_csv(out_dir / "review_worksheet_150.csv", WORKSHEET_COLUMNS, worksheet)
    famous = famous_check(reports, normalizer, rows, cluster_of)

    summary = common.header_object(JOB, COMMAND, common.input_fingerprints(
        CORPUS, RECONCILED / "pure_canon_chain.jsonl.gz", RECONCILED / "no_chain_in_source.jsonl.gz", REGISTRY,
        common.HADITH_DATA_DIR / "regen_unified_csvs.py", common.HADITH_DATA_DIR / "extract_isnad_unified.py",
        common.DATASETS_DIR / "classify_attribution.py"))
    summary["code_sha256"] = common.input_fingerprints(
        JOB_DIR / "build_report_correspondence.py", JOB_DIR / "correspondence_logic.py",
        JOB_DIR / "matn_isolation.py")
    summary["parameters"] = {
        "shingle_letters": logic.SHINGLE_LETTERS, "min_words": logic.MIN_WORDS,
        "partial_min_words": logic.PARTIAL_MIN_WORDS, "window_words": logic.WINDOW_WORDS,
        "window_stride": logic.WINDOW_STRIDE, "oph_bins": logic.OPH_BINS, "lsh_bands": logic.LSH_BANDS,
        "lsh_rows": logic.LSH_ROWS, "lsh_signatures_per_window": len(logic.LSH_SIGNATURE_SALTS), "stop_shingle_document_share": logic.STOP_SHINGLE_DOCUMENT_SHARE,
        "stop_threshold_documents": stop_threshold, "bucket_cap": BUCKET_CAP,
        "min_window_shingles": MIN_WINDOW_SHINGLES, "same_wording_jaccard": logic.SAME_WORDING_JACCARD,
        "variant_jaccard": logic.VARIANT_JACCARD, "variant_containment": logic.VARIANT_CONTAINMENT,
        "partial_containment": logic.PARTIAL_CONTAINMENT, "seed": SEED, "method_version": METHOD_VERSION,
        "lsh_candidate_probability": {f"{j:.1f}": round(logic.lsh_candidate_probability(j), 3)
                                      for j in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8)},
    }
    summary["corpus"] = {"rows": len(reports), "eligible_for_matching": eligible_count, **meta}
    summary["lsh"] = {"windows_signed": windows_signed, "windows_without_signature": no_signature,
                      "candidate_pairs": candidate_count, **lsh_stats}
    summary["headline"] = headline(reports, rows, cluster_of, guard)
    summary["famous_report_check"] = famous
    summary["outputs"] = {
        "report_correspondence_pairs.csv": pair_count, "report_correspondence_pairs.jsonl": pair_count,
        "report_correspondence_cluster_members.csv": member_count, "matn_isolation_coverage.csv": len(coverage),
        "matn_isolation_flags.csv": flag_count, "review_worksheet_150.csv": sample_count,
    }
    summary.pop("generated_at_utc", None)   # keeps summary.json byte-identical across runs
    common.write_json(out_dir, "summary.json", summary)
    common.write_json(out_dir, "run_log.json", {"runtime_seconds": round(time.time() - started, 1),
                                                 "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    progress(f"done: {pair_count} pairs, {member_count} cluster members, sample {sample_count}", started)


if __name__ == "__main__":
    main()
