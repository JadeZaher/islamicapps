"""Find Qur'an quotations in every report's Arabic and write load-ready, credited citation sidecars.

    python -B datasets/hadith-data/quran/build_quran_citations.py        # about 1 minute, streaming

Inputs (read only): the Tanzil Qur'an texts in datasets/sources/external/quran-tanzil/ and the record_id corpus.
Outputs (this directory, deterministic bytes): hadith_quran_citations.jsonl.gz, hadith_quran_phrases.jsonl.gz,
quran_verses.jsonl.gz, quran_citations.manifest.json. See README.md.
"""

from __future__ import annotations

import gzip
import hashlib
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

TANZIL = xio.EXTERNAL / "quran-tanzil"
ISOLATION = xio.isolation
SURA_NAMES = ext.SURA_NAMES
ALGORITHM = "maximal exact letter-skeleton match, k-gram seeds at report word starts; two Tanzil editions"


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl_gz(path: Path, rows) -> dict:
    count = 0
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        for row in rows:
            handle.write((dumps(row) + "\n").encode("utf-8"))
            count += 1
    return {"file": path.name, "rows": count, "sha256": sha256_file(path)}


def reference_text(candidate: dict) -> str:
    low, high = candidate["aya_from"], candidate["aya_to"]
    return f"{candidate['sura']}:{low}" if low == high else f"{candidate['sura']}:{low}-{high}"


def matn_offset(text: str, matn: str) -> int:
    """Offset in `text` where the isolated matn starts: exact substring, else by Arabic letters (the extractor's segment
    is not always a byte substring of the stored text); -1 when absent."""
    if not matn.strip():
        return -1
    exact = text.rfind(matn.strip())
    if exact >= 0:
        return exact
    positions = [i for i, char in enumerate(text) if "ء" <= char <= "ي"]
    letters = "".join(text[i] for i in positions)
    needle = ISOLATION.arabic_letters(matn)
    found = letters.rfind(needle) if needle else -1
    return positions[found] if found >= 0 else -1


def part_of_report(isolator, row, text, start, end, cache: dict) -> str:
    """Where a span sits: matn, before_matn, straddles_boundary, whole_text_is_matn, no_chain_detected or boundary_unknown."""
    if "matn" not in cache:
        matn, method, reliability, _ = isolator.isolate(row)
        offset = matn_offset(text, matn)
        cache["matn"] = (offset, method, reliability)
    offset, method, reliability = cache["matn"]
    if method in (ISOLATION.METHOD_SOURCE_MATN_ONLY, ISOLATION.METHOD_NO_CHAIN_IN_SOURCE):
        return "whole_text_is_matn"
    if method == ISOLATION.METHOD_WHOLE_TEXT_FALLBACK:
        return "no_chain_detected"
    if offset < 0 or reliability != ISOLATION.RELIABLE:
        return "boundary_unknown"
    if start >= offset:
        return "matn"
    return "before_matn" if end <= offset else "straddles_boundary"


def candidates_of(span) -> list[dict]:
    """One entry per distinct verse reference; an edition pair that agrees gives the simple-clean text."""
    unique = {}
    for candidate in span.candidates:
        key = (candidate["sura"], candidate["aya_from"], candidate["aya_to"])
        entry = {"sura": candidate["sura"], "aya_from": candidate["aya_from"], "aya_to": candidate["aya_to"],
                 "ref": reference_text(candidate), "sura_name_ar": SURA_NAMES[candidate["sura"] - 1],
                 "quran_text": candidate["quran_text"], "quran_edition": candidate["edition"]}
        if key not in unique or candidate["edition"] == "simple-clean":
            unique[key] = entry
    return [unique[key] for key in sorted(unique)]


TANZIL_URL = "https://tanzil.net/"
TANZIL_LICENCE = {"name": "CC BY 3.0", "url": "https://creativecommons.org/licenses/by/3.0/"}
TANZIL_ATTRIBUTION = ("Qur'an text: Tanzil Quran Text (%s, version %s), (C) 2007-2026 Tanzil Project, https://tanzil.net/, "
                      "Creative Commons Attribution 3.0. Unmodified; Tanzil does not endorse this archive.")
EDITION_FILES = {"simple-clean": "quran-simple-clean.txt", "uthmani": "quran-uthmani.txt"}


def edition_metadata() -> dict:
    """Edition name, version and file hash exactly as each Tanzil file's own header states them."""
    import re
    meta = {}
    for edition, name in EDITION_FILES.items():
        path = TANZIL / name
        header = re.search(r"Tanzil Quran Text \(([^,]+), Version ([\d.]+)\)", path.read_text(encoding="utf-8"))
        assert header, f"no Tanzil header in {name}"
        meta[edition] = {"text_type": header.group(1), "version": header.group(2),
                         "file": f"datasets/sources/external/quran-tanzil/{name}", "file_sha256": sha256_file(path)}
    return meta


def citation_block(item: dict, editions: dict) -> dict:
    """The complete citation every emitted Qur'an citation carries (work, edition, locator, verbatim, span, source,
    hashes). Checked by validate_citations.py before any load."""
    locators = []
    for candidate in item["candidates"]:
        edition = editions[candidate["quran_edition"]]
        locators.append({"sura": candidate["sura"], "aya_from": candidate["aya_from"], "aya_to": candidate["aya_to"],
                         "ref": candidate["ref"], "verbatim_quran_text": candidate["quran_text"],
                         "edition": f"Tanzil Quran Text ({edition['text_type']}), version {edition['version']}",
                         "edition_key": candidate["quran_edition"], "quran_file_sha256": edition["file_sha256"]})
    used = editions[item["candidates"][0]["quran_edition"]]
    return {"work": "The Qur'an", "locators": locators,
            "span_in_report": {"record_id": item["record_id"], "start": item["start"], "end": item["end"],
                               "text": item["quote_ar"], "text_sha256": item["quote_sha256"],
                               "report_arabic_sha256": item["arabic_sha256"]},
            "source": {"code": "TNZ", "short": "Tanzil Quran Text, tanzil.net", "url": TANZIL_URL,
                       "licence": TANZIL_LICENCE,
                       "attribution": TANZIL_ATTRIBUTION % (used["text_type"], used["version"])}}


def main() -> None:
    started = time.time()
    editions = edition_metadata()
    streams = logic.load_tanzil(TANZIL)
    sura_keys = [logic.sura_key(name) for name in SURA_NAMES]
    extractor = xio.common.load_extractor()
    matn_only, no_chain = ISOLATION.load_sidecars(xio.io_.RECONCILED_DIR)
    isolator = ISOLATION.MatnIsolator(extractor, matn_only, no_chain)
    print(f"[{time.time() - started:6.1f}s] indexed {len(streams)} editions", flush=True)

    pending, reports_total, reports_with_text = [], 0, 0
    for row in xio.iter_corpus():
        reports_total += 1
        text = row["text_ar"] or ""
        if not text.strip():
            continue
        reports_with_text += 1
        skeleton = logic.build_skeleton(text)
        spans = logic.merge_editions([logic.find_spans(skeleton, stream) for stream in streams.values()])
        if not spans:
            continue
        origins = logic.letter_origins(text)
        cache: dict = {}
        arabic_hash = sha256_text(text)
        for span in spans:
            start, end = logic.original_offsets(text, origins, span)
            letters = skeleton.letters[span.start_letter:span.end_letter]
            candidates = candidates_of(span)
            cues = logic.cues_around(text, start, end, [sura_keys[c["sura"] - 1] for c in candidates])
            pending.append({
                "record_id": row["record_id"], "hadith_id": f"hadith:{row['record_id']}",
                "tradition": row["tradition"], "source": row["source"], "source_work_id": row["source_work_id"],
                "arabic_sha256": arabic_hash, "start": start, "end": end, "quote_ar": text[start:end],
                "quote_sha256": sha256_text(text[start:end]), "words": span.words, "letters": len(letters),
                "skeleton": letters, "part": part_of_report(isolator, row, text, start, end, cache),
                "cues": cues, "candidates": candidates, "candidate_count": len(candidates),
                "ambiguous": len(candidates) > 1, "formula": logic.formula_of(letters),
            })
    print(f"[{time.time() - started:6.1f}s] {len(pending)} spans in {reports_total} reports", flush=True)

    holders = defaultdict(set)
    for item in pending:
        holders[item["skeleton"]].add(item["record_id"])
    citations, phrases, kinds = [], [], Counter()
    for item in pending:
        item["span_report_count"] = len(holders[item["skeleton"]])
        item.update(logic.classify_span(item["words"], item["formula"], item["cues"], item["span_report_count"]))
        item["id"] = f"quran:{item['record_id']}:{item['start']}:{item['end']}"
        item["basis"] = "text_match"
        item["review_state"] = "unreviewed"
        item["offsets"] = "Unicode code points of the stored text_ar, [start, end)"
        item["primary_cue"] = next((c["kind"] for c in item["cues"] if c["kind"] in logic.STRONG_CUES),
                                   item["cues"][0]["kind"] if item["cues"] else None)
        del item["skeleton"]
        kinds[item["kind"]] += 1
        if item["kind"] == "citation" and item["candidates"]:
            item["citation"] = citation_block(item, editions)
        (citations if item["kind"] == "citation" else phrases).append(item)
    for rows in (citations, phrases):
        rows.sort(key=lambda r: (r["record_id"], r["start"], r["end"]))

    simple, uthmani = streams["simple-clean"], streams["uthmani"]
    verses = []
    for index, (sura, aya) in enumerate(simple.verses):
        assert uthmani.verses[index] == (sura, aya)
        verses.append({"sura": sura, "aya": aya, "ref": f"{sura}:{aya}", "sura_name_ar": SURA_NAMES[sura - 1],
                       "text_uthmani": uthmani.verse_texts[index], "text_simple_clean": simple.verse_texts[index]})

    outputs = {
        "citations": write_jsonl_gz(HERE / "hadith_quran_citations.jsonl.gz", citations),
        "phrases": write_jsonl_gz(HERE / "hadith_quran_phrases.jsonl.gz", phrases),
        "verses": write_jsonl_gz(HERE / "quran_verses.jsonl.gz", verses),
    }
    tanzil_files = [TANZIL / "quran-uthmani.txt", TANZIL / "quran-simple-clean.txt"]
    manifest = {
        "artifact": "hadith_quran_citations", "status": "sidecar_unreviewed_not_a_release_input",
        "command": "python -B datasets/hadith-data/quran/build_quran_citations.py",
        "algorithm": ALGORITHM, "quran_editions": editions,
        "parameters": {"seed_letters": logic.SEED_LETTERS, "min_span_letters": logic.MIN_SPAN_LETTERS, **logic.PARAMS},
        "reports": {"total": reports_total, "with_text": reports_with_text},
        "spans_by_kind": dict(sorted(kinds.items())),
        "inputs_sha256": {**{f"datasets/sources/external/quran-tanzil/{p.name}": sha256_file(p) for p in tanzil_files},
                          "datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz":
                              sha256_file(xio.CORPUS)},
        "code_sha256": {p.name: sha256_file(p) for p in (HERE / "quran_logic.py", Path(__file__).resolve())},
        "outputs": outputs,
        "licence": ("Qur'an text and verse boundaries: Tanzil Quran Text (Simple Clean and Uthmani, version 1.1), "
                    "(C) 2007-2026 Tanzil Project, Creative Commons Attribution 3.0, https://tanzil.net/ ; "
                    "the text is reproduced unmodified in quran_verses.jsonl.gz and the quran_text fields. "
                    "Spans, cues and classes are this project's, unreviewed."),
    }
    with open(HERE / "quran_citations.manifest.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"[{time.time() - started:6.1f}s] done: {dict(kinds)}", flush=True)


if __name__ == "__main__":
    main()
