#!/usr/bin/env python3
"""
extract_isnad_sunni.py — isnad / narrator extraction for the Sunni canon
========================================================================

The Sunni Kutub al-Sittah rows (from sunnah.com, ~34.4k) carry the full
chain inside text_ar but have NO structured sanad — every other tradition
does. This closes that gap so the unified dataset has narrator data for
every row.

Sunni isnad form is highly regular:

    حدثنا <N1>، قال حدثنا <N2>، عن <N3>، عن <N4>، عن <Sahabi> رضي الله عنه
    [matn boundary] قال رسول الله ﷺ "..."

What is extracted per hadith:
  - sanad        : ordered list of narrator names (transmitter → ... → Companion)
  - sanad_count  : chain length
  - companion    : the last narrator before the matn (the Sahabi)
  - matn_ar      : the text after the isnad/matn boundary
  - isnad_ar     : the raw isnad span (for audit)

It writes a sidecar JSONL (sunni_isnad.jsonl) keyed by hadith id rather than
rewriting the 40 MB CSV in place; regen_unified_csvs.py joins it back in.

Heuristic, not a parser: classical isnad analysis is a research problem.
This targets the clean, well-structured canon text and is conservative —
chain-switch (ح taḥwīl) takes the first chain; ambiguous spans are kept
whole rather than mis-split. Deterministic and auditable (no LLM).

Usage:
    python extract_isnad_sunni.py            # build the sidecar
    python extract_isnad_sunni.py --stats    # coverage stats only
    python extract_isnad_sunni.py --sample 15
"""

import argparse
import csv
import json
import os
import re
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
csv.field_size_limit(10 * 1024 * 1024)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "hadith-data")
CLEAN_CSV = os.path.join(BASE_DIR, "all_hadiths_clean.csv")
OUT_JSONL = os.path.join(BASE_DIR, "sunni_isnad.jsonl")

# Where the isnad ends and the matn begins. The canon almost always opens
# the matn with one of these once the last (Companion) narrator is reached.
_MATN_BOUNDARY = re.compile(
    r"(?:قال|يقول|قالت)\s*:?\s*(?:سمعت\s+)?رسول\s+الله"
    r"|(?:قال|قالت)\s+(?:كان\s+)?(?:رسول\s+الله|النبي)"
    r"|أن\s+رسول\s+الله|أن\s+النبي"
    r"|أنه?\s+سأل\s+رسول\s+الله"
    r"|سمعت\s+(?:رسول\s+الله|النبي)\s+صلى\s+الله\s+عليه\s+وسلم"
    r"|(?:رسول\s+الله|النبي)\s+صلى\s+الله\s+عليه\s+وسلم\s+(?:قال|يقول|أنه)"
    r"|في\s+قوله\s+تعالى"
)

# A narrator-introducing verb at the START of a comma segment.
_LEAD_VERB = re.compile(
    r"^(?:و?قال\s+)?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا|"
    r"سمعت|عن|أن|أنه|أنها|يقول|عنه?\s+)?\s*"
)

# taḥwīl — switch to a parallel chain; keep the first chain only.
_TAHWIL = re.compile(r"(?:^|\s)ح\s+و?(?:حدثنا|أخبرنا)")

# Trailing honorifics / titles to drop from a name token. The canon uses
# رضى (with ى) and decorative spacing; match generously.
_HONORIFIC = re.compile(
    r"\s*رض[ىي]\s*الله\s*عنه?[امه]*\s*"
    r"|\s*رحمه\s*الله\s*|\s*عليه\s*السلام\s*"
    r"|\s*أم\s+المؤمنين\s*|\s*على\s+المنبر\s*"
)
_PUNCT = re.compile(r"[،,.:؛!؟\"'\(\)\[\]‏‎‏‎]+")


def _clean_name(raw: str) -> str:
    n = _LEAD_VERB.sub("", raw.strip())
    n = _HONORIFIC.sub(" ", n)
    n = _PUNCT.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip()
    # Reject fragments that are clearly not names.
    if n in ("ها", "به", "بن", "أبيه", "") or n.isdigit():
        # "أبيه" (his father) IS a valid relative link — keep it.
        if n == "أبيه":
            return n
        return ""
    return n if 2 <= len(n) <= 60 else ""


def extract(text_ar: str) -> dict:
    """Extract sanad / matn from one Sunni hadith's Arabic text.

    Strategy: cut at the matn boundary, take the first chain (pre-taḥwīl),
    then split the isnad on Arabic commas — the canon delimits every
    narrator with ، — and strip the leading transmission verb + trailing
    honorific from each segment. Comma-primary splitting is far more robust
    than verb-splitting because narrator names themselves contain no commas.
    """
    text = (text_ar or "").strip()
    if len(text) < 30:
        return {"sanad": [], "sanad_count": 0, "companion": "",
                "matn_ar": text, "isnad_ar": "", "sanad_confidence": 0}

    # Primary signal: the Companion is the last narrator and is overwhelmingly
    # tagged with رضى الله عنه/عنها/عنهما; the matn starts right after it
    # (optionally after a "أنه/أنها قال/قالت" or "أن X ..." narration cue).
    # This is far more reliable across the canon than matching the matn opener,
    # which varies wildly (story-form hadith have no early قال رسول الله).
    boundary = None
    last_sahabi = None
    for hm in re.finditer(r"رض[ىي]\s*الله\s*عنه?[امه]*", text):
        last_sahabi = hm
    if last_sahabi:
        after = text[last_sahabi.end():]
        cue = re.search(r"^\s*(?:أن|أنه|أنها|قال|قالت|يقول|عن)\b", after)
        boundary = last_sahabi.end() + (cue.end() if cue else 0)

    m = _MATN_BOUNDARY.search(text)
    # Use whichever boundary comes first and is plausible (some isnads have no
    # رضى الله عنه; some matns mention it mid-text — the earliest valid wins).
    cut = None
    if boundary is not None and m is not None:
        cut = min(boundary, m.start())
    elif boundary is not None:
        cut = boundary
    elif m is not None:
        cut = m.start()

    isnad = text[:cut] if cut is not None else ""
    matn = text[cut:] if cut is not None else text

    th = _TAHWIL.search(isnad)
    chain = isnad[: th.start()] if th else isnad

    sanad = []
    for seg in chain.split("،"):
        nm = _clean_name(seg)
        if nm and (not sanad or sanad[-1] != nm):
            sanad.append(nm)

    # Plausibility guard: a real narrator name has no narrative connectors and
    # is short. If any token looks like a sentence fragment (story-form hadith
    # the boundary heuristic can't split), the chain is untrustworthy — emit
    # NO structured sanad rather than misleading garbage. text_ar still holds
    # the verbatim chain as ground truth.
    _NARRATIVE = re.compile(r"\b(?:ثم|حتى|فقال|فقالت|فكان|فلما|إذ|فأخذني|فرجع|فدخل|قلت)\b")
    if any(len(n) > 45 or _NARRATIVE.search(n) for n in sanad):
        sanad = []

    # Confidence: 2 = clean boundary + plausible chain; 1 = chain but no
    # boundary match (matn may include isnad tail); 0 = no chain found.
    if sanad and m:
        conf = 2
    elif sanad:
        conf = 1
    else:
        conf = 0

    return {
        "sanad": sanad,
        "sanad_count": len(sanad),
        "companion": sanad[-1] if sanad else "",
        "matn_ar": matn.strip(),
        "isnad_ar": isnad.strip(),
        "sanad_confidence": conf,
    }


def _iter_sunni():
    with open(CLEAN_CSV, encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            if row.get("tradition") == "Sunni":
                yield row


def main():
    ap = argparse.ArgumentParser(description="Extract Sunni isnad/narrators")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    args = ap.parse_args()

    if args.sample:
        n = 0
        for row in _iter_sunni():
            r = extract(row.get("text_ar"))
            print(f"--- {row.get('source','')[:18]} #{row.get('hadith_no','')} "
                  f"({r['sanad_count']} narrators) ---")
            print("  sanad:", " ← ".join(r["sanad"]))
            print("  matn :", r["matn_ar"][:90])
            n += 1
            if n >= args.sample:
                break
        return

    total = with_chain = 0
    lens = []
    conf_dist = {0: 0, 1: 0, 2: 0}
    out = None if args.stats else open(OUT_JSONL, "w", encoding="utf-8")
    try:
        for row in _iter_sunni():
            r = extract(row.get("text_ar"))
            total += 1
            if r["sanad_count"] >= 2:
                with_chain += 1
            lens.append(r["sanad_count"])
            conf_dist[r["sanad_confidence"]] += 1
            if out is not None:
                out.write(json.dumps({
                    "id": row.get("id"),
                    "hadith_no": row.get("hadith_no"),
                    "source": row.get("source"),
                    "sanad": r["sanad"],
                    "sanad_count": r["sanad_count"],
                    "companion": r["companion"],
                    "matn_ar": r["matn_ar"],
                    "sanad_confidence": r["sanad_confidence"],
                }, ensure_ascii=False) + "\n")
    finally:
        if out is not None:
            out.close()

    avg = sum(lens) / len(lens) if lens else 0
    print(f"Sunni rows: {total:,}")
    print(f"  with a chain (>=2 narrators): {with_chain:,} "
          f"({100 * with_chain // max(total, 1)}%)")
    print(f"  avg chain length: {avg:.1f}")
    print(f"  confidence: clean={conf_dist[2]:,} "
          f"chain-no-boundary={conf_dist[1]:,} none={conf_dist[0]:,}")
    if not args.stats:
        print(f"  written: {OUT_JSONL}")


if __name__ == "__main__":
    main()
