"""Pre-load check: the db:verify-data chain invariants that a projection's files alone can decide (pg_export/AGENTS.md).

Usage: python -I datasets/hadith-data/pg_export/check_projection.py <projection dir>
Exits 1 on any violation. Runs in about a minute, so a nine-minute load never fails on one of these.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)
NAME_BASES = {"name_exact", "name_spelling_fold", "name_kunya_only"}
TIER_BASES = {"source_index_confirmed_by_text", "source_hadith_kg_confirmed_by_text", "source_riwayat_confirmed_by_text",
              "imam_kunya_convention"}


def rows(directory: Path, table: str):
    with (directory / "canonical" / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def main(directory: Path) -> int:
    hadiths = {row["id"]: (row["tradition_id"], row["collection_id"], row["sanad_inherits_from"]) for row in rows(directory, "hadiths")}
    narrators = {row["id"] for row in rows(directory, "narrators")}
    chains = {row["id"]: row for row in rows(directory, "chains")}
    mentions = {row["id"]: row for row in rows(directory, "chain_mentions")}
    candidates_by_mention: dict[str, list[dict]] = defaultdict(list)
    failures: Counter = Counter()
    examples: dict[str, str] = {}

    def fail(name: str, example: str) -> None:
        failures[name] += 1
        examples.setdefault(name, example)

    positions: dict[str, list[int]] = defaultdict(list)
    for mention in mentions.values():
        positions[mention["chain_id"]].append(int(mention["position"]))
        chain = chains.get(mention["chain_id"])
        if chain is None or chain["hadith_id"] != mention["hadith_id"]:
            fail("mention on a missing chain or another hadith's chain", mention["id"])
        if mention["narrator_id"] and mention["link_kind"] in ("anonymous", "not_a_narrator"):
            fail("unnamed transmitter or back-reference with an identity", mention["id"])
        if mention["narrator_id"] and mention["narrator_id"] not in narrators:
            fail("narrator_id names no narrator", mention["id"])
        if mention["identity_withheld_reason"] and mention["resolution_basis"] == "source_index":
            fail("withheld identity still stands", mention["id"])
        source = mention["inherited_from_mention_id"]
        if source:
            written = mentions.get(source)
            owner = hadiths.get(mention["hadith_id"])
            if (written is None or written["inherited_from_mention_id"] or written["surface_ar"] != mention["surface_ar"]
                    or hadiths[written["hadith_id"]][1] != owner[1]
                    or (not owner[2] and chain["extraction_method"] != "thaqalayn_inherited_chain")):
                fail("inherited mention does not repeat a written mention of its collection in an inheriting chain", mention["id"])
    for chain_id, chain in chains.items():
        found = sorted(positions.get(chain_id, []))
        if found != list(range(int(chain["length"]))):
            fail("chain positions not contiguous 0..length-1", chain_id)
        if chain["missing_link_after"] and not 0 <= int(chain["missing_link_after"]) < int(chain["length"]) - 1:
            fail("missing_link_after outside the chain", chain_id)
        if chain["hadith_id"] not in hadiths:
            fail("chain on a missing hadith", chain_id)
    for candidate in rows(directory, "chain_mention_candidates"):
        mention = mentions.get(candidate["mention_id"])
        candidates_by_mention[candidate["mention_id"]].append(candidate)
        if mention is None or mention["hadith_id"] != candidate["hadith_id"]:
            fail("candidate on a missing mention or another hadith", candidate["id"])
            continue
        if candidate["narrator_id"] not in narrators:
            fail("candidate names no narrator", candidate["id"])
        tradition, collection, _ = hadiths[candidate["hadith_id"]]
        basis = candidate["basis"]
        if basis in NAME_BASES and tradition != "tradition:sunni":
            fail("name candidate on a non-Sunni report", candidate["id"])
        if basis == "edition_identification" and tradition != "tradition:sunni":
            fail("edition identification outside a Sunni report", candidate["id"])
        if basis == "named_in_opening_isnad" and collection != "collection:zaydi:musnad-zayd":
            fail("opening-isnad rule outside Musnad Zayd", candidate["id"])
        if basis.startswith("imam_kunya") and tradition != "tradition:imami":
            fail("Imam kunya outside an Imami report", candidate["id"])
    for mention in mentions.values():
        if mention["identity_withheld_reason"] and not any(
                c["basis"] in TIER_BASES for c in candidates_by_mention.get(mention["id"], [])):
            fail("withheld identity without a confirmed candidate", mention["id"])
        if mention["narrator_id"] and mention["resolution_basis"] == "source_index" and not any(
                c["narrator_id"] == mention["narrator_id"] for c in candidates_by_mention.get(mention["id"], [])):
            fail("standing identity without its candidate", mention["id"])
    print(f"checked {len(chains)} chains, {len(mentions)} mentions")
    for name, count in sorted(failures.items()):
        print(f"FAIL {name}: {count} (e.g. {examples[name]})")
    if not failures:
        print("PASS every file-level chain invariant")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
