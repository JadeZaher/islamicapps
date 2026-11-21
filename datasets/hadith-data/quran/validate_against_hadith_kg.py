"""Compare the text matcher's spans with hadith-kg's Qur'an quotation markings where the two datasets overlap.

    python -B datasets/hadith-data/quran/validate_against_hadith_kg.py     # about 1 minute; needs the build outputs

hadith-kg (CC BY 4.0) is a reference here, not ground truth: it marks what its authors' pipeline found. Reads
hadith_quran_citations.jsonl.gz and hadith_quran_phrases.jsonl.gz, the report crosswalk (used matches only), the
hadith-kg database (read only) and the corpus. Writes quran_validation.json.
"""

from __future__ import annotations

import bisect
import gzip
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reconciled"))
import quran_logic as logic  # noqa: E402
import external_source_io as xio  # noqa: E402
import external_source_logic as ext  # noqa: E402

WORD_BINS = [(2, 3), (4, 4), (5, 5), (6, 6), (7, 9), (10, 14), (15, 10**6)]


def bin_of(words: int) -> str:
    for low, high in WORD_BINS:
        if low <= words <= high:
            return f"{low}" if low == high else (f"{low}-{high}" if high < 10**6 else f"{low}+")
    return "1"


def read_rows(name: str):
    with gzip.open(HERE / name, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def merge_intervals(intervals):
    merged = []
    for low, high in sorted(intervals):
        if merged and low <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    return merged


def covered(merged, low, high) -> int:
    total = 0
    for a, b in merged:
        total += max(0, min(b, high) - max(a, low))
    return total


def main() -> None:
    started = time.time()
    ours = defaultdict(list)
    for name in ("hadith_quran_citations.jsonl.gz", "hadith_quran_phrases.jsonl.gz"):
        for row in read_rows(name):
            ours[row["record_id"]].append(row)
    placed = defaultdict(list)
    for row in xio.read_jsonl_gz(xio.io_.RECONCILED_DIR / "hadith_kg_quran_citations.jsonl.gz"):
        placed[row["record_id"]].append(row)

    crosswalk = {}
    for row in xio.read_jsonl_gz(xio.io_.RECONCILED_DIR / xio.CROSSWALK):
        if row["dataset"] == "hadith_kg" and row["used"]:
            crosswalk[row["record_id"]] = row
    connection = xio.connect(xio.HADITH_KG)

    reports_overlap = reports_with_kg_quotes = 0
    precision = defaultdict(Counter)       # key -> {outcome: n}   (our spans)
    recall = defaultdict(Counter)          # key -> {outcome: n}   (kg quotes)
    placed_stats = Counter()
    reference_agreement = Counter()
    agreement_rows = []
    for row in xio.iter_corpus():
        record_id = row["record_id"]
        if record_id not in crosswalk:
            continue
        reports_overlap += 1
        text = row["text_ar"] or ""
        kg_id = int(crosswalk[record_id]["external_report_id"])
        kg_spans = connection.execute("select seq, start, end from hadith_ayas where hadith_id = ? order by seq",
                                      (kg_id,)).fetchall()
        mine = ours.get(record_id, [])
        if not kg_spans and not mine:
            continue
        nass = connection.execute("select nass from hadiths where id = ?", (kg_id,)).fetchone()[0] if kg_spans else ""
        skeleton = logic.build_skeleton(text)
        origins = logic.letter_origins(text)
        # kg quotations: letters, located in our skeleton
        kg_quotes = []
        for seq, start, end in kg_spans:
            quote, references = ext.parse_quran_span(nass[start:end])
            letters = "".join(logic.skeleton_words(quote))
            kg_quotes.append({"letters": letters, "references": references,
                              "words": len(logic.skeleton_words(quote)), "seq": seq})
        if kg_quotes:
            reports_with_kg_quotes += 1
        # our spans as letter intervals
        intervals = []
        for item in mine:
            a = bisect.bisect_left(origins, item["start"])
            b = bisect.bisect_left(origins, item["end"])
            intervals.append((a, b, item))
        merged_ours = merge_intervals([(a, b) for a, b, _ in intervals])
        # precision: is each of our spans inside a kg quotation?
        for a, b, item in intervals:
            letters = skeleton.letters[a:b]
            outcome = "not_marked_by_hadith_kg"
            for quote in kg_quotes:
                if letters in quote["letters"]:
                    outcome = "inside_kg_quotation"
                    break
                if quote["letters"] and quote["letters"] in letters:
                    outcome = "contains_kg_quotation"
                    break
            group = item["kind"] if item["kind"] != "citation" else f"citation:{item['confidence']}"
            precision[group][outcome] += 1
            precision[f"words:{bin_of(item['words'])}"][outcome] += 1
            if item["kind"] == "citation":
                cue = "cued" if any(c["kind"] in logic.STRONG_CUES for c in item["cues"]) else "uncued"
                precision[f"citation:{cue}:words:{bin_of(item['words'])}"][outcome] += 1
            agreement_rows.append({"id": item["id"], "hadith_kg": outcome})
            # reference agreement where hadith-kg labels the quotation we found
            if outcome in ("inside_kg_quotation", "contains_kg_quotation"):
                for quote in kg_quotes:
                    if quote["letters"] and (letters in quote["letters"] or quote["letters"] in letters):
                        for reference in quote["references"]:
                            hit = any(c["sura"] == reference["sura_number"] and c["aya_from"] <= reference["aya_to"]
                                      and reference["aya_from"] <= c["aya_to"] for c in item["candidates"])
                            reference_agreement["kg_reference_inside_our_candidates" if hit else "kg_reference_not_in_our_candidates"] += 1
                        break
        # recall: how much of each hadith-kg quotation do our spans cover?
        for quote in kg_quotes:
            letters = quote["letters"]
            band = bin_of(quote["words"]) if quote["words"] >= 2 else "1"
            if len(letters) < logic.MIN_SPAN_LETTERS:
                recall[f"words:{band}"]["kg_quote_under_10_letters"] += 1
                continue
            position = skeleton.letters.find(letters)
            if position == -1:
                recall[f"words:{band}"]["kg_quote_absent_from_our_text_skeleton"] += 1
                continue
            low, high = position, position + len(letters)
            share = covered(merged_ours, low, high) / (high - low)
            outcome = "found_whole" if share >= 0.9 else "found_partly" if share >= 0.5 else (
                "touched" if share > 0 else "missed")
            recall[f"words:{band}"][outcome] += 1
            recall["all"][outcome] += 1
            if outcome in ("missed", "touched"):
                recall["missed_by_cue"]["x"] += 0
        # the 1,197 spans already placed by the crosswalk (character offsets): who covers them?
        for span in placed.get(record_id, []):
            if span["arabic_sha256"] != (mine[0]["arabic_sha256"] if mine else span["arabic_sha256"]):
                placed_stats["arabic_hash_differs"] += 1
            best = None
            for item in mine:
                overlap = max(0, min(item["end"], span["end"]) - max(item["start"], span["start"]))
                if overlap and (best is None or overlap > best[0]):
                    best = (overlap, item)
            length = span["end"] - span["start"]
            placed_stats["placed_spans"] += 1
            if best is None:
                placed_stats["no_overlapping_span"] += 1
                continue
            share = best[0] / length
            item = best[1]
            placed_stats["overlap_ge_90pct" if share >= 0.9 else "overlap_50_90pct" if share >= 0.5 else
                         "overlap_under_50pct"] += 1
            placed_stats[f"best_span_kind:{item['kind']}" + (f":{item['confidence']}" if item["confidence"] else "")] += 1
            for reference in span["references"]:
                if reference["sura_number"] is None:
                    placed_stats["kg_reference_without_sura"] += 1
                    continue
                hit = any(c["sura"] == reference["sura_number"] and c["aya_from"] <= reference["aya_to"]
                          and reference["aya_from"] <= c["aya_to"] for c in item["candidates"])
                placed_stats["reference_in_candidates" if hit else "reference_not_in_candidates"] += 1
    result = {
        "reports_in_overlap": reports_overlap, "overlap_reports_with_kg_quotations": reports_with_kg_quotes,
        "precision_of_our_spans_by_group": {k: dict(sorted(v.items())) for k, v in sorted(precision.items())},
        "recall_of_kg_quotations_by_words": {k: dict(sorted(v.items())) for k, v in sorted(recall.items())},
        "placed_1197_spans": dict(sorted(placed_stats.items())),
        "kg_reference_vs_our_candidates_on_overlapping_quotations": dict(reference_agreement),
        "note": ("inside_kg_quotation = our span's letters occur inside a hadith-kg quotation of the same report; "
                 "not_marked_by_hadith_kg means hadith-kg marks no quotation there, not that the span is wrong "
                 "(see the reading in README.md)."),
    }
    with open(HERE / "quran_span_hadith_kg_agreement.jsonl.gz", "wb") as raw, gzip.GzipFile(filename="", mtime=0, mode="wb", fileobj=raw) as handle:
        for entry in sorted(agreement_rows, key=lambda e: e["id"]):
            line = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.write(f"{line}\n".encode("utf-8"))
    with open(HERE / "quran_validation.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"[{time.time() - started:6.1f}s] reports in overlap {reports_overlap}", flush=True)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
