"""Measure the Qur'an citation sidecar: coverage by tradition and work, most-quoted verses, where in the report.

    python -B datasets/hadith-data/quran/measure_quran_citations.py      # seconds; needs the build outputs

Writes quran_measurements.json. A report "quotes the Qur'an" when it has at least one span of kind `citation`
(any confidence); the stricter counts (high only, high or medium) are given beside it.
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reconciled"))
import external_source_io as xio  # noqa: E402


def read(name: str):
    with gzip.open(HERE / name, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def share(part: int, whole: int) -> float:
    return round(100 * part / whole, 2) if whole else 0.0


def main() -> None:
    citations = list(read("hadith_quran_citations.jsonl.gz"))
    phrases = list(read("hadith_quran_phrases.jsonl.gz"))
    verses = {(v["sura"], v["aya"]): v for v in read("quran_verses.jsonl.gz")}

    totals_tradition, totals_work = Counter(), Counter()
    work_names = {}
    for row in xio.iter_corpus():
        totals_tradition[row["tradition"]] += 1
        totals_work[(row["tradition"], row["source_work_id"])] += 1
        work_names[(row["tradition"], row["source_work_id"])] = row["source"]

    by_report = defaultdict(list)
    for item in citations:
        by_report[item["record_id"]].append(item)
    tradition_of = {item["record_id"]: item["tradition"] for item in citations}
    work_of = {item["record_id"]: (item["tradition"], item["source_work_id"]) for item in citations}
    levels = {"any_citation": {"high", "medium", "low"}, "high_or_medium": {"high", "medium"}, "high": {"high"}}

    def reports_at(level):
        return {record for record, items in by_report.items() if any(i["confidence"] in levels[level] for i in items)}

    result = {"reports_total": sum(totals_tradition.values()), "definition": (
        "a report quotes the Qur'an when it holds a span of kind citation; confidence levels as in README.md")}
    result["reports_with_quotation"] = {
        level: {"total": len(reports_at(level)), "percent_of_reports": share(len(reports_at(level)),
                                                                           sum(totals_tradition.values()))}
        for level in levels}
    result["by_tradition"] = {}
    for tradition, total in sorted(totals_tradition.items()):
        entry = {"reports": total}
        for level in levels:
            held = sum(1 for r in reports_at(level) if tradition_of[r] == tradition)
            entry[level] = {"reports": held, "percent": share(held, total)}
        entry["citation_spans"] = sum(1 for i in citations if i["tradition"] == tradition)
        result["by_tradition"][tradition] = entry
    result["by_work"] = []
    for key, total in sorted(totals_work.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        entry = {"tradition": key[0], "source_work_id": key[1], "source": work_names[key], "reports": total}
        for level in levels:
            held = sum(1 for r in reports_at(level) if work_of[r] == key)
            entry[level] = {"reports": held, "percent": share(held, total)}
        result["by_work"].append(entry)

    kinds = Counter()
    for item in citations + phrases:
        kinds[(item["tradition"], item["kind"], item["confidence"] or "-")] += 1
    result["spans_by_tradition_and_class"] = {f"{t}|{k}|{c}": n for (t, k, c), n in sorted(kinds.items())}
    result["spans_total"] = {"citation": len(citations), **dict(Counter(p["kind"] for p in phrases))}

    result["position_in_report"] = {
        "citations_by_part": dict(Counter(i["part"] for i in citations)),
        "note": ("matn = after the extractor's sanad/matn boundary; before_matn = before it (the isnad and any narrative "
                 "that precedes the matn); whole_text_is_matn = the source ships no isnad in the text; "
                 "no_chain_detected = no chain visible at the start, whole text treated as matn; boundary_unknown = "
                 "no reliable boundary"),
    }
    before_matn = [i for i in citations if i["part"] == "before_matn"]
    result["position_in_report"]["before_matn_examples"] = [
        {"id": i["id"], "quotation": i["quote_ar"][:80], "references": [c["ref"] for c in i["candidates"][:3]]}
        for i in before_matn[:5]]

    # verses: reports per verse, unambiguous spans only (every verse of a multi-verse span counts once)
    per_verse = defaultdict(set)
    ambiguous = 0
    for item in citations:
        if item["confidence"] not in ("high", "medium"):
            continue
        if item["ambiguous"]:
            ambiguous += 1
            continue
        candidate = item["candidates"][0]
        for aya in range(candidate["aya_from"], candidate["aya_to"] + 1):
            per_verse[(candidate["sura"], aya)].add(item["record_id"])
    ranked = sorted(per_verse.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    result["most_quoted_verses"] = {
        "basis": "reports with an unambiguous high- or medium-confidence span covering the verse",
        "ambiguous_high_medium_spans_excluded": ambiguous,
        "verses_covered": len(per_verse), "verses_total": len(verses),
        "top": [{"ref": f"{s}:{a}", "sura_name_ar": verses[(s, a)]["sura_name_ar"], "reports": len(r),
                 "text": verses[(s, a)]["text_simple_clean"][:90]} for (s, a), r in ranked[:30]]}
    result["ambiguity"] = {
        "citations_with_several_candidates": sum(1 for i in citations if i["ambiguous"]),
        "percent": share(sum(1 for i in citations if i["ambiguous"]), len(citations)),
        "by_candidate_count": dict(sorted(Counter(min(i["candidate_count"], 6) for i in citations).items())),
        "spans_across_verses": sum(1 for i in citations if any(c["aya_to"] > c["aya_from"] for c in i["candidates"])),
    }
    result["cues"] = dict(Counter(i["primary_cue"] or "none" for i in citations))
    result["words_distribution_citations"] = dict(sorted(Counter(min(i["words"], 20) for i in citations).items()))
    with open(HERE / "quran_measurements.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in ("reports_with_quotation", "by_tradition", "spans_total", "ambiguity",
                                              "cues", "position_in_report")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
