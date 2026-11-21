#!/usr/bin/env python3
"""J6b: regex-detect Tirmidhi's own in-text statements about a report (e.g. 'هذا حديث حسن صحيح').

Statements are quoted verbatim from the Arabic source with character spans; they are compiler statements,
not grades assigned by this project, and every hit needs review (regex-detected). The speaker hint marks
sentences that quote another authority (e.g. 'قال محمد'). Writes only under diagnostics/grading/.

Usage: python -B diagnostics/extract_tirmidhi_compiler_statements.py
"""

import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "grading"
SOURCE_LABEL = "Jami' al-Tirmidhi"
TERMS = ("صحيح", "حسن", "غريب", "ضعيف", "شاذ", "منكر", "محفوظ", "مرسل")
_TERM_GROUP = "|".join(TERMS)
_TERM_TOKEN = re.compile(rf"(?<![ء-ي])و?(?:ال)?({_TERM_GROUP})(?![ء-ي])")
_SENTENCE_SPLIT = re.compile(r"[‏]*\.[‏]*")
_THIS_HADITH = re.compile(rf"(?:هذا|وهذا)\s+(?:ال)?حديث[^.]{{0,80}}?(?:{_TERM_GROUP})")
_NAMED_HADITH = re.compile(rf"حديث(?:\s+\S+){{0,6}}?\s+حديث\s+[^.]{{0,40}}?(?:{_TERM_GROUP})")
_SUPERLATIVE = re.compile(r"أصح\s+شيء|أحسن\s+شيء")
_QALA_ABU_ISA = re.compile(r"قال\s+أبو\s+عيسى")
_OTHER_SPEAKER = re.compile(r"(?:سألت|قال|سمعت)\s+(?:محمدا|محمد|أحمد|إسحاق|علي)\b")


def extract_compiler_statements(text_ar: str) -> list[dict]:
    """Return one dict per sentence that matches a compiler-statement pattern (candidates only)."""
    statements = []
    position = 0
    for sentence in _SENTENCE_SPLIT.split(text_ar or ""):
        start = (text_ar or "").find(sentence, position) if sentence else position
        position = start + len(sentence) if start >= 0 else position
        stripped = sentence.strip(" ‏\"")
        if not stripped:
            continue
        if not (_THIS_HADITH.search(stripped) or _NAMED_HADITH.search(stripped) or _SUPERLATIVE.search(stripped)):
            continue
        terms = []
        for found_term in _TERM_TOKEN.findall(stripped):      # token-bounded, in source order
            if found_term not in terms:
                terms.append(found_term)
        statements.append({
            "statement_ar": stripped[:400], "char_start": start, "char_end": start + len(sentence),
            "terms_found": terms, "preceded_by_qala_abu_isa": bool(_QALA_ABU_ISA.search(
                (text_ar or "")[max(0, start - 30): start + len(sentence)])),
            "speaker_hint_other_authority": bool(_OTHER_SPEAKER.search(stripped)),
            "status": "compiler_statement_candidate_regex_unreviewed"})
    return statements


def main() -> None:
    started = time.time()
    rows_seen = rows_with_statement = 0
    statement_rows = []
    term_combinations = Counter()
    for row_number, row in common.iter_corpus_rows():
        if common.clean(row["source"]) != SOURCE_LABEL:
            continue
        rows_seen += 1
        found = extract_compiler_statements(row.get("text_ar") or "")
        if not found:
            continue
        rows_with_statement += 1
        reference = common.row_reference(row_number, row)
        for number, statement in enumerate(found, 1):
            term_combinations[" ".join(statement["terms_found"]) or "<superlative_only>"] += 1
            statement_rows.append({**reference, "statement_no": number, **statement})
    out = common.output_directory(JOB)
    count = common.write_jsonl(out, "tirmidhi_compiler_statements.jsonl", statement_rows)
    common.write_json(out, "tirmidhi_compiler_statements_summary.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/extract_tirmidhi_compiler_statements.py",
            common.input_fingerprints(common.CORPUS_PATH)),
        "tirmidhi_rows": rows_seen, "rows_with_at_least_one_statement": rows_with_statement,
        "statements": count,
        "statements_preceded_by_qala_abu_isa": sum(1 for s in statement_rows if s["preceded_by_qala_abu_isa"]),
        "statements_quoting_another_authority_hint": sum(1 for s in statement_rows if s["speaker_hint_other_authority"]),
        "term_combinations": dict(term_combinations.most_common(25)),
        "caveat": "Regex detection over unpunctuated source text; every hit needs review before use as a compiler statement.",
        "seconds": round(time.time() - started, 1),
    })
    print({"rows": rows_seen, "rows_with_statement": rows_with_statement, "statements": count,
           "seconds": round(time.time() - started, 1)})


if __name__ == "__main__":
    main()
