"""Pre-load validator: every emitted Qur'an citation must carry one complete, checkable citation.

    python -B datasets/hadith-data/quran/validate_citations.py      # about 30 seconds; exit 1 on any failure

Checks per row of hadith_quran_citations.jsonl.gz: work; edition name/version equal to the Tanzil file's own header;
locator(s) with valid sura/aya ranges (all candidates kept); verbatim Qur'an text present in the verse text of that
edition; span reproducible in the stored report text (slice hash, report hash); source short reference, licence and
attribution; the Qur'an file hash equals the file on disk. Writes quran_citation_validation.json.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "reconciled"))
import quran_logic as logic  # noqa: E402
import external_source_io as xio  # noqa: E402

TANZIL = xio.EXTERNAL / "quran-tanzil"
FILES = {"simple-clean": "quran-simple-clean.txt", "uthmani": "quran-uthmani.txt"}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    verse_text, file_hash, header = {}, {}, {}
    for edition, name in FILES.items():
        raw = (TANZIL / name).read_bytes()
        file_hash[edition] = hashlib.sha256(raw).hexdigest()
        match = re.search(r"Tanzil Quran Text \(([^,]+), Version ([\d.]+)\)", raw.decode("utf-8"))
        header[edition] = (match.group(1), match.group(2))
        verse_text[edition] = {(s, a): t for s, a, t in logic.parse_tanzil(raw.decode("utf-8").splitlines())}
    rows = []
    with gzip.open(HERE / "hadith_quran_citations.jsonl.gz", "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    need = {r["record_id"] for r in rows}
    texts = {r["record_id"]: r["text_ar"] or "" for r in xio.iter_corpus() if r["record_id"] in need}
    failures, reasons = [], Counter()
    for row in rows:
        problems = []
        cite = row.get("citation")
        if not cite:
            problems.append("no_citation_block")
        else:
            if cite.get("work") != "The Qur'an":
                problems.append("work")
            if not cite.get("locators"):
                problems.append("no_locator")
            if len(cite.get("locators", [])) != row["candidate_count"]:
                problems.append("candidates_dropped")
            for loc in cite.get("locators", []):
                edition = loc.get("edition_key")
                if edition not in FILES:
                    problems.append("edition_key")
                    continue
                if loc["edition"] != f"Tanzil Quran Text ({header[edition][0]}), version {header[edition][1]}":
                    problems.append("edition_name_version")
                if loc["quran_file_sha256"] != file_hash[edition]:
                    problems.append("quran_file_hash")
                low, high, sura = loc["aya_from"], loc["aya_to"], loc["sura"]
                if not (1 <= sura <= 114 and 1 <= low <= high and (sura, low) in verse_text[edition]
                        and (sura, high) in verse_text[edition]):
                    problems.append("locator_range")
                    continue
                joined = " ".join(verse_text[edition][(sura, a)] for a in range(low, high + 1))
                verbatim = loc["verbatim_quran_text"]
                if not verbatim or verbatim not in joined:
                    problems.append("verbatim_not_in_verse_text")
                if "".join(logic.skeleton_words(verbatim)) != "".join(logic.skeleton_words(row["quote_ar"])):
                    problems.append("verbatim_differs_from_report_span")
            span = cite.get("span_in_report", {})
            text = texts[row["record_id"]]
            if (span.get("start"), span.get("end")) != (row["start"], row["end"]) or \
                    text[span["start"]:span["end"]] != span.get("text"):
                problems.append("span_not_in_stored_text")
            if span.get("text_sha256") != sha(span.get("text", "")) or span.get("report_arabic_sha256") != sha(text):
                problems.append("report_hashes")
            source = cite.get("source", {})
            if not (source.get("code") and source.get("short") and source.get("licence", {}).get("url")
                    and "Tanzil" in source.get("attribution", "") and "tanzil.net" in source.get("url", "")):
                problems.append("source_credit")
        if problems:
            failures.append({"id": row["id"], "problems": sorted(set(problems))})
            reasons.update(set(problems))
    result = {"citations_checked": len(rows), "passed": len(rows) - len(failures), "failed": len(failures),
              "failure_reasons": dict(reasons), "failure_examples": failures[:10]}
    with open(HERE / "quran_citation_validation.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
