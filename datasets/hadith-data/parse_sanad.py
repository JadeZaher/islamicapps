#!/usr/bin/env python3
"""
parse_sanad.py
==============
Parse Arabic isnad (chain of transmission) text from the classical collections CSV
into structured narrator segments.

Phase 1: Regex-based extraction
    - Splits chain text on Arabic transmission verbs
    - Extracts narrator name segments
    - Outputs a JSONL file: one line per hadith with parsed narrator names

Phase 2 (separate script): Match names to existing Narrator nodes in Neo4j

Transmission verbs used as delimiters:
    حدثنا / حدثني / حدثه  (haddathana/ni - narrated to us/me)
    أخبرنا / أخبرني       (akhbarana/ni - informed us/me)
    أنبأنا / أنا           (anba'ana/ana - told us)
    عن                     (an - from)
    قال                    (qala - said)
    سمعت / سمع             (sami'tu/sami'a - heard)
    ذكر / ذكره             (dhakara - mentioned)

Usage:
    python datasets/hadith-data/parse_sanad.py \\
        --input datasets/hadith-data/classical_canon_translated.csv \\
        --output datasets/hadith-data/classical_sanad_parsed.jsonl
"""

import argparse
import csv
import io
import json
import re
import sys

# UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── Transmission verb patterns ───────────────────────────────────────────────
# These verbs mark the boundary between narrator names in the chain.
# Order matters: longer patterns first to avoid partial matches.

TRANSMISSION_VERBS = [
    r"قال\s+حدثنا",
    r"قال\s+حدثني",
    r"قال\s+أخبرنا",
    r"قال\s+أخبرني",
    r"قال\s+أنبأنا",
    r"قال\s+سمعت",
    r"حدثنا",
    r"حدثني",
    r"حدثه",
    r"أخبرنا",
    r"أخبرني",
    r"أنبأنا",
    r"أنا",
    r"سمعت",
    r"سمع",
    r"عن",
    r"ذكره",
    r"ذكر",
    r"أن",
    r"قال",
]

# Build a combined pattern: match any transmission verb
# Use word boundary-like matching (Arabic doesn't have \b so use \s or start/end)
VERB_PATTERN = re.compile(
    r"(?:^|\s)(" + "|".join(TRANSMISSION_VERBS) + r")(?:\s|$)",
    re.UNICODE,
)

# Pattern to clean up narrator names
NOISE_WORDS = re.compile(
    r"\b(يعني|يعنى|يقول|قالت?|أنه[ام]?|رضي الله عنه[ام]?|صلى الله عليه وآله وسلم|صلى الله عليه وسلم)\b",
    re.UNICODE,
)


def normalize_name(name: str) -> str:
    """Clean up an extracted narrator name segment."""
    # Remove noise words
    name = NOISE_WORDS.sub("", name)
    # Remove parenthetical notes
    name = re.sub(r"\(.*?\)", "", name)
    # Collapse whitespace
    name = " ".join(name.split())
    return name.strip()


def parse_chain(chain_text: str) -> list[dict]:
    """
    Parse an Arabic chain text into a list of narrator segments.

    Returns a list of dicts with:
        - name_arabic: the extracted narrator name
        - transmission_verb: the verb that preceded this name
        - position: 0-indexed position in the chain (0 = closest to hadith compiler)
    """
    if not chain_text or not chain_text.strip():
        return []

    chain_text = chain_text.strip()

    # Find all transmission verb positions
    splits = []
    for match in VERB_PATTERN.finditer(chain_text):
        verb = match.group(1).strip()
        start = match.start()
        end = match.end()
        splits.append((start, end, verb))

    if not splits:
        # No transmission verbs found — treat the whole text as one segment
        cleaned = normalize_name(chain_text)
        if cleaned:
            return [{"name_arabic": cleaned, "transmission_verb": "", "position": 0}]
        return []

    narrators = []
    position = 0

    for i, (start, end, verb) in enumerate(splits):
        # The narrator name is the text AFTER the verb until the next verb
        if i + 1 < len(splits):
            name_text = chain_text[end : splits[i + 1][0]]
        else:
            name_text = chain_text[end:]

        cleaned = normalize_name(name_text)

        # Skip empty or very short names (likely parsing artifacts)
        if cleaned and len(cleaned) > 1:
            narrators.append(
                {
                    "name_arabic": cleaned,
                    "transmission_verb": verb,
                    "position": position,
                }
            )
            position += 1

    return narrators


def main():
    parser = argparse.ArgumentParser(description="Parse Arabic isnad chains")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", required=True, help="Output JSONL file")
    parser.add_argument("--sample", type=int, default=0, help="Process only N rows (0=all)")
    args = parser.parse_args()

    total = 0
    parsed = 0
    empty_chain = 0
    total_narrators = 0

    with (
        open(args.input, "r", encoding="utf-8-sig") as fin,
        open(args.output, "w", encoding="utf-8") as fout,
    ):
        reader = csv.DictReader(fin)
        for row in reader:
            if args.sample and total >= args.sample:
                break

            total += 1
            chain = row.get("chain", "")
            hadith_id = row.get("id", "")

            if not chain.strip():
                empty_chain += 1
                continue

            narrators = parse_chain(chain)
            if not narrators:
                empty_chain += 1
                continue

            output = {
                "hadith_id": hadith_id,
                "source_canonical": row.get("source_canonical", ""),
                "row_no": row.get("row_no", ""),
                "chain_raw": chain,
                "narrators": narrators,
                "narrator_count": len(narrators),
            }

            fout.write(json.dumps(output, ensure_ascii=False) + "\n")
            parsed += 1
            total_narrators += len(narrators)

            if total % 5000 == 0:
                print(f"  Processed {total:,} rows, {parsed:,} chains parsed...")

    print(f"\n{'='*60}")
    print(f"  Sanad Parsing Complete")
    print(f"{'='*60}")
    print(f"  Total rows:        {total:,}")
    print(f"  Chains parsed:     {parsed:,}")
    print(f"  Empty/no chain:    {empty_chain:,}")
    print(f"  Total narrators:   {total_narrators:,}")
    print(f"  Avg per chain:     {total_narrators / max(parsed, 1):.1f}")
    print(f"  Output:            {args.output}")


if __name__ == "__main__":
    main()
