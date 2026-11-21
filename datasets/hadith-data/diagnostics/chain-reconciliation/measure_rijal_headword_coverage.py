#!/usr/bin/env python3
"""Q5/Q6: how many unresolved chain surfaces match a headword in the downloaded OpenITI rijal works (diagnostic only).

Each `### $ <n>` entry's headword (text before the first comma, sigla removed) yields name-prefix keys of 1-6 tokens
under the same comparison key as the agreement job. A surface matching a key gets the entries as CANDIDATES
(basis `rijal_headword_name_match`); a name match is never an identity, and Imami/Sunni works are kept per tradition.
Reads datasets/sources/external/openiti-*/ as plain text. Writes output/rijal_headword_coverage.json.
Usage: python -B measure_rijal_headword_coverage.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
EXTERNAL = common.DATASETS_DIR / "sources" / "external"
WORKS = {
    "Imami": {"najashi_rijal": "openiti-0450Najashi.Rijal/0450Najashi.Rijal.Shia002931-ara1.mARkdown",
              "tusi_rijal": "openiti-0460ShaykhTusi.Rijal/0460ShaykhTusi.Rijal.Shia002935-ara1.mARkdown",
              "tusi_fihrist": "openiti-0460ShaykhTusi.Fihrist/0460ShaykhTusi.Fihrist.Shia002934-ara1.mARkdown",
              "kashshi_ikhtiyar": "openiti-0460ShaykhTusi.IkhtiyarMacrifatRijal/"
                                  "0460ShaykhTusi.IkhtiyarMacrifatRijal.Shia002932VolsBK1-ara1.mARkdown"},
    "Sunni": {"ibn_hajar_taqrib": "openiti-0852IbnHajar.TaqribTahdhib/0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed",
              "mizzi_tahdhib_kamal": "openiti-0742Mizzi.TahdhibKamal/0742Mizzi.TahdhibKamal.Shamela0003722-ara1.mARkdown"},
}
_ENTRY = re.compile(r"^### \$\s*(\d+)?\s*-?\s*(.*)$")
_SIGLA = re.compile(r"^[ء-ي ]{1,12}:\s*")
_MS = re.compile(r"\bms\d+\b|\bPage\S*|[0-9()\[\]«»]")


def headwords(path: Path):
    """(entry number, headword) per biography entry."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = _ENTRY.match(line.rstrip("\n"))
            if not match:
                continue
            body = _MS.sub(" ", match.group(2))
            body = _SIGLA.sub("", body.strip())
            yield match.group(1) or "", re.split(r"[،,.]", body, maxsplit=1)[0], body


def main() -> None:
    canon = rc.Canon()
    index = {tradition: defaultdict(set) for tradition in WORKS}
    entries = Counter()
    hashes = {}
    for tradition, works in WORKS.items():
        for work, relative in works.items():
            path = EXTERNAL / relative
            hashes[common.relative_path(path)] = common.sha256_file(path)
            for number, head, line in headwords(path):
                entries[work] += 1
                entry = (work, number)
                tokens = canon.comparison_key(head).split()[:6]
                for length in range(1, len(tokens) + 1):
                    prefix = tokens[:length]
                    if prefix[-1] in rc.CONNECTORS or (length == 1 and prefix[0] in rc.KUNYA_HEADS):
                        continue
                    index[tradition][" ".join(prefix)].add(entry)
                # Ibn-name forms ('بن ابو عمير', 'بن محبوب') and kunyas stated in the entry line ('ابو بصير').
                for k, token in enumerate(tokens[1:], 1):
                    if token == "بن" and k + 1 < len(tokens):
                        tail = tokens[k + 1:k + 3] if tokens[k + 1] in rc.KUNYA_HEADS else tokens[k + 1:k + 2]
                        index[tradition][" ".join(["بن"] + tail)].add(entry)
                line_tokens = canon.comparison_key(line).split()[:25]
                for k, token in enumerate(line_tokens[:-1]):
                    if token in rc.KUNYA_HEADS:
                        index[tradition][" ".join(line_tokens[k:k + 2])].add(entry)

    unresolved = {tradition: Counter() for tradition in ("Imami", "Sunni", "Ibadi", "Zaydi")}
    for _, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition"))
        for branch in canon.extract(row.get("text_ar")) or []:
            for surface in branch:
                if not canon.resolve(surface):
                    unresolved[tradition][canon.comparison_key(surface)] += 1

    coverage = {}
    for tradition, counter in unresolved.items():
        work_tradition = "Imami" if tradition in ("Imami", "Zaydi") else "Sunni"
        table = index[work_tradition]
        ranked = counter.most_common()
        result = {"unresolved_occurrences": sum(counter.values()), "distinct_keys": len(ranked),
                  "matched_against": work_tradition + " works"}
        for top in (100, 500, 2000, len(ranked)):
            subset = ranked[:top]
            occ = sum(c for _, c in subset)
            one = sum(c for k, c in subset if len(table.get(k, ())) == 1)
            few = sum(c for k, c in subset if 2 <= len(table.get(k, ())) <= 5)
            many = sum(c for k, c in subset if len(table.get(k, ())) > 5)
            result[f"top_{top}"] = {"occurrences": occ, "one_entry": one, "two_to_five_entries": few,
                                    "more_than_five_entries": many,
                                    "percent_with_any_entry": round(100 * (one + few + many) / max(occ, 1), 1)}
        result["examples_top_20"] = [{"key": k, "occurrences": c,
                                      "entries": sorted(table.get(k, ()))[:4], "entry_count": len(table.get(k, ()))}
                                     for k, c in ranked[:20]]
        coverage[tradition] = result
    out = {"header": common.header_object(
               "chain-reconciliation/rijal-headwords",
               "python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_rijal_headword_coverage.py",
               {**common.input_fingerprints(common.CORPUS_PATH), **hashes}),
           "basis": "rijal_headword_name_match (candidate only, unreviewed)",
           "entries_per_work": dict(entries), "coverage": coverage}
    common.write_json(OUTPUT, "rijal_headword_coverage.json", out)
    print(json.dumps({"entries": out["entries_per_work"],
                      "coverage": {t: {k: v for k, v in c.items() if k != "examples_top_20"}
                                   for t, c in coverage.items()}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
