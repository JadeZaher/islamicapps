#!/usr/bin/env python3
"""Q5: can an Imami narrator registry be built from the Thaqalayn provider data alone? (diagnostic only)

The provider ships no narrator ids; `thaqalaynSanad` is an English sentence. This job splits it into English name
mentions, pairs them with the Arabic extracted chain when both have the same length, and measures the resulting
surface lexicon (Arabic key -> English transliterations, teacher/student edges). A pair is a translation alignment,
never an identity. Writes output/imami_provider_sanad.json and output/imami_surface_lexicon.jsonl.gz.
Usage: python -B measure_imami_provider_sanad.py
"""

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
COMMAND = "python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_imami_provider_sanad.py"

_LEADING_NUMBER = re.compile(r"^\s*(?:H\s*)?[\d\-/\[\]\.\s]+")
_TAIL = re.compile(r"\b(?:who|that|has|have|had|is|was)?\s*(?:has |have )?(?:said|says|narrated the following|"
                   r"said the following|reported the following)\b.*$", re.I)
_LINKS = re.compile(r"\s*(?:,\s*)?\b(?:who\s+)?(?:has\s+|have\s+|had\s+)?(?:narrated|reported|transmitted|related)"
                    r"(?:\s+(?:to\s+(?:me|us)|it))?\s+(?:from|on the authority of)\b\s*|"
                    r"\s*(?:,\s*)?\bfrom\b\s*|\s*\bthat\b\s*|\s*\bon the authority of\b\s*|"
                    r"\s*(?:,\s*)?\b(?:informed|told)\s+(?:me|us)\b\s*(?:that)?\s*", re.I)
_NOISE = re.compile(r"^(?:it is|it was|and|both|all of them|he|him|his|they)\b", re.I)


def english_mentions(sanad: str) -> list:
    """English name mentions of a Thaqalayn sanad sentence, in reading order (heuristic split)."""
    text = _LEADING_NUMBER.sub("", sanad or "").strip()
    text = _TAIL.sub("", text).strip(" :,.;")
    parts = [part.strip(" :,.;\"'“”") for part in _LINKS.split(text)]
    out = []
    for part in parts:
        part = re.sub(r"\((?:a\.?s\.?|as|s\.?a\.?w\.?|MGB|p\.?b\.?u\.?h\.?)\)", "", part, flags=re.I).strip()
        part = _NOISE.sub("", part).strip(" ,")
        if part and re.search(r"[A-Za-z]", part):
            out.append(part)
    return out


def main() -> None:
    started = time.time()
    canon = rc.Canon()
    stats = Counter()
    by_book = defaultdict(Counter)
    arabic_to_english = defaultdict(Counter)
    arabic_occurrences = Counter()
    arabic_resolved = Counter()
    edges = Counter()
    for _, hadith in rc.iter_thaqalayn():
        book = hadith.get("book") or "?"
        stats["reports"] += 1
        by_book[book]["reports"] += 1
        branches = canon.extract(hadith.get("arabicText"))
        mentions = english_mentions(hadith.get("thaqalaynSanad") or "")
        if mentions:
            by_book[book]["english_sanad_with_mentions"] += 1
        if not branches:
            by_book[book]["no_arabic_chain"] += 1
            continue
        by_book[book]["arabic_chain"] += 1
        for branch in branches:
            keys = [canon.fold(surface) for surface in branch]
            for position, key in enumerate(keys):
                arabic_occurrences[key] += 1
                if canon.resolve(branch[position]):
                    arabic_resolved[key] += 1
                if position + 1 < len(keys):
                    edges[(key, keys[position + 1])] += 1
        if len(branches) == 1 and mentions:
            if len(mentions) == len(branches[0]):
                by_book[book]["single_branch_same_length_as_english"] += 1
                for surface, english in zip(branches[0], mentions):
                    arabic_to_english[canon.fold(surface)][english] += 1
            else:
                by_book[book]["single_branch_length_differs"] += 1
        elif mentions:
            by_book[book]["multi_branch"] += 1

    total_occurrences = sum(arabic_occurrences.values())
    ranked = arabic_occurrences.most_common()
    curve, running = {}, 0
    for rank, (key, count) in enumerate(ranked, 1):
        running += count
        if rank in (100, 500, 1000, 2000, 5000) or rank == len(ranked):
            curve[str(rank)] = {"occurrences": running, "percent": round(100 * running / max(total_occurrences, 1), 1)}
    paired = {key: counter for key, counter in arabic_to_english.items()}
    consistency = Counter()
    for counter in paired.values():
        top_share = counter.most_common(1)[0][1] / sum(counter.values())
        consistency["one_english_form" if len(counter) == 1 else
                    "dominant_form_share>=0.8" if top_share >= 0.8 else "mixed"] += 1
    paired_occ = sum(arabic_occurrences[key] for key in paired)

    for book in by_book.values():
        stats.update({k: v for k, v in book.items() if k != "reports"})
    result = {
        "header": common.header_object("chain-reconciliation/imami-provider-sanad", COMMAND,
                                       common.input_fingerprints(common.REGISTRY_PATH)),
        "provider_fields": "Thaqalayn V2 records carry no narrator id, no narrator list and no rijal endpoint; "
                           "thaqalaynSanad is an English sentence.",
        "totals": dict(stats),
        "by_book": {book: dict(counter) for book, counter in sorted(by_book.items())},
        "arabic_surface_census": {
            "occurrences": total_occurrences,
            "distinct_canonical_keys": len(arabic_occurrences),
            "occurrences_resolved_by_strict_resolver": sum(arabic_resolved.values()),
            "distinct_teacher_student_edges": len(edges),
            "coverage_curve_top_n_keys": curve,
        },
        "english_pairing": {
            "distinct_arabic_keys_with_english_pairing": len(paired),
            "occurrences_of_paired_keys": paired_occ,
            "percent_of_imami_occurrences": round(100 * paired_occ / max(total_occurrences, 1), 1),
            "pairing_consistency": dict(consistency),
        },
        "runtime_seconds": round(time.time() - started, 1),
    }
    common.write_json(OUTPUT, "imami_provider_sanad.json", result)

    def lexicon_rows():
        for key, count in ranked:
            teachers = Counter({t: c for (s, t), c in edges.items() if s == key}) if count >= 50 else Counter()
            yield {"arabic_key": key, "occurrences": count, "strict_resolved": arabic_resolved[key],
                   "english_forms": dict(arabic_to_english.get(key, Counter()).most_common(5)),
                   "top_teachers": dict(teachers.most_common(5)),
                   "basis": "provider_english_sanad_alignment", "status": "surface_lexicon_not_identity",
                   "review_state": "unreviewed"}
    common.write_jsonl(OUTPUT, "imami_surface_lexicon.jsonl.gz", lexicon_rows(), gzipped=True)
    print(json.dumps({k: result[k] for k in ("totals", "arabic_surface_census", "english_pairing")},
                     ensure_ascii=False, indent=1))
    print(f"{result['runtime_seconds']}s")


if __name__ == "__main__":
    main()
