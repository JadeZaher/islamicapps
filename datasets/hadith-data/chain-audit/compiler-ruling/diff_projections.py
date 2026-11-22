"""Identities and compiler heads, before and after the 2026-11-22 rulings: one projection against another (read-only).

    python -X utf8 diff_projections.py <before projection> <after projection> <out dir>

Writes summary.json (standing identities per tradition, gained and lost by cause, compiler heads per work) and three reading
samples of 30 (seed 20261122): kunya_gained.tsv, kunya_lost.tsv, compiler_pairs.tsv, each row with the report text's opening.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pg_export"))
import external_identity as xid  # noqa: E402


def rows(directory: Path, table: str):
    with (directory / "canonical" / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def main(before: Path, after: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    hadiths = {r["id"]: r for r in rows(after, "hadiths")}
    tradition = {h: r["tradition_id"].split(":")[1] for h, r in hadiths.items()}
    old = {r["id"]: r for r in rows(before, "chain_mentions")}
    new = {r["id"]: r for r in rows(after, "chain_mentions")}
    names = {r["id"]: (r["name_latin"] or r["name_en"] or r["name_ar"] or r["name"]) for r in rows(after, "narrators")}
    names.update({r["id"]: (r["name_latin"] or r["name_en"] or r["name_ar"] or r["name"]) for r in rows(before, "narrators")})
    standing = {"before": Counter(), "after": Counter()}
    changes: dict[str, list[dict]] = defaultdict(list)
    cause_counts: Counter = Counter()
    for side, table in (("before", old), ("after", new)):
        for row in table.values():
            if row["narrator_id"]:
                standing[side][tradition.get(row["hadith_id"], "?")] += 1
    for mention_id in set(old) | set(new):
        a, b = old.get(mention_id), new.get(mention_id)
        if a is None or b is None or a["surface_ar"] != b["surface_ar"]:
            cause_counts["mention_added_or_retired_or_resurfaced"] += 1
            continue
        if a["narrator_id"] == b["narrator_id"]:
            continue
        trad = tradition.get(b["hadith_id"], "?")
        kunya = xid.bare_kunya_key(b["surface_ar"]) is not None
        if b["extraction_method"] == "named_in_opening_isnad" and "work:" in (b["narrator_id"] or ""):
            cause = "named_in_full_by_work"
        elif kunya and not b["narrator_id"] and (b["identity_withheld_reason"] or "").startswith("kunya only:"):
            cause = "kunya_lost"
        elif kunya and b["narrator_id"] and not a["narrator_id"]:
            cause = "kunya_gained"
        elif a["narrator_id"] and b["narrator_id"]:
            cause = "identity_changed_other"
        else:
            cause = "gained_other" if b["narrator_id"] else "lost_other"
        cause_counts[f"{trad}:{cause}"] += 1
        changes[cause].append({"mention_id": mention_id, "hadith_id": b["hadith_id"], "tradition": trad, "surface": b["surface_ar"],
                               "before": a["narrator_id"] or "", "before_name": names.get(a["narrator_id"], ""),
                               "after": b["narrator_id"] or "", "after_name": names.get(b["narrator_id"], ""),
                               "method_after": b["extraction_method"] or "", "reason": b["identity_withheld_reason"] or "",
                               "position": b["position"], "chain_id": b["chain_id"]})
    # Compiler heads.
    chains = list(rows(after, "chains"))
    heads: Counter = Counter()
    for chain in chains:
        work = hadiths[chain["hadith_id"]]["collection_id"].removeprefix("collection:")
        heads[f"{work}:{chain['compiler_link'] or 'none'}"] += 1
    by_chain_position = {(r["chain_id"], int(r["position"])): r for r in new.values()}
    pairs = defaultdict(list)
    for chain in chains:
        first = by_chain_position.get((chain["id"], 0))
        if (chain["compiler_link"] == "direct" and not chain["suspension"] and chain["structure_status"] == "checked_by_rule"
                and first and first["narrator_id"] and first["link_kind"] not in ("anonymous", "not_a_narrator")):
            pairs[(chain["compiler_narrator_id"], first["narrator_id"])].append(chain["hadith_id"])
    rng = random.Random(20261122)

    def opening(hadith_id: str) -> str:
        return " ".join(hadiths[hadith_id]["text_ar"].split())[:220]

    samples = {}
    for cause in ("kunya_gained", "kunya_lost"):
        pool = sorted(changes[cause], key=lambda c: c["mention_id"])
        samples[cause] = rng.sample(pool, min(30, len(pool)))
    pair_pool = sorted(pairs)
    samples["compiler_pairs"] = [{"compiler": c, "compiler_name": names.get(c, ""), "teacher": t, "teacher_name": names.get(t, ""),
                                  "reports": len(pairs[(c, t)]), "hadith_id": sorted(pairs[(c, t)])[0]}
                                 for c, t in rng.sample(pair_pool, min(30, len(pair_pool)))]
    for name, sample in samples.items():
        with (out / f"{name}.tsv").open("w", encoding="utf-8", newline="\n") as handle:
            keys = list(sample[0].keys()) + ["opening"] if sample else []
            handle.write("\t".join(keys + ["verdict", "note"]) + "\n")
            for row in sample:
                handle.write("\t".join([str(row[k]) for k in keys[:-1]] + [opening(row["hadith_id"]), "", ""]) + "\n")
    summary = {"standing_identities": {side: dict(sorted(c.items())) for side, c in standing.items()},
               "changes_by_cause": dict(sorted(cause_counts.items())),
               "compiler_heads_by_work": dict(sorted(heads.items())),
               "compiler_pairs_possible": {"distinct_pairs": len(pairs), "reports": sum(len(v) for v in pairs.values())}}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
