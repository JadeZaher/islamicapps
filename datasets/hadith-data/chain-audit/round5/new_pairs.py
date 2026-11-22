"""Round 5: the teacher-student pairs the recalibrated gate adds, computed from the projection round 4 read. Read-only.

  python -I -X utf8 datasets/hadith-data/chain-audit/round5/new_pairs.py <pairs-before.json> <production_status.json> <out.json>
A pair is two adjacent mentions of one chain that both carry a narrator id (the projection's standing identities); the view's
other guards (seams, basis) only remove pairs, so this is an upper bound of the new rows. Chains released by the recalibration
are those the round-4 gate marked uncertain and the new gate checks; chains newly flagged are the reverse.
"""

import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

csv.field_size_limit(2**31 - 1)
before = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
status = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
old_uncertain, new_uncertain = set(status["round4"]), set(status["final"])
canonical = lib.READ_R4 / "canonical"
chain_hadith, chain_work = {}, {}
with (canonical / "chains.csv").open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
        chain_hadith[row["id"]] = row["hadith_id"]
mentions = collections.defaultdict(list)
with (canonical / "chain_mentions.csv").open(encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
        mentions[row["chain_id"]].append((int(row["position"]), row["narrator_id"], row["surface_ar"]))
had = {(p["student_id"], p["teacher_id"]) for p in before["pairs"]}


def pairs_of(chain_id):
    found = sorted(mentions[chain_id])
    return [(a, b) for a, b in zip(found, found[1:]) if a[1] and b[1] and a[1] != b[1]]


released = [c for c in chain_hadith if c in old_uncertain and c not in new_uncertain]
flagged = [c for c in chain_hadith if c not in old_uncertain and c in new_uncertain]
new_pairs, tradition_new = {}, collections.Counter()
for chain_id in released:
    for a, b in pairs_of(chain_id):
        key = (a[1], b[1])
        if key not in had and key not in new_pairs:
            new_pairs[key] = {"student": a[1], "teacher": b[1], "chain_id": chain_id, "hadith_id": chain_hadith[chain_id],
                              "student_surface": a[2], "teacher_surface": b[2]}
            tradition_new[chain_hadith[chain_id].split(":")[1]] += 1
supported_by_flagged_only = collections.Counter()
by_old = collections.defaultdict(set)
for chain_id in chain_hadith:
    if chain_id not in old_uncertain:
        for a, b in pairs_of(chain_id):
            by_old[(a[1], b[1])].add(chain_id in new_uncertain)
lost = [k for k, v in by_old.items() if v == {True}]
print("released chains", len(released), "newly flagged chains", len(flagged))
print("new pairs (upper bound)", len(new_pairs), dict(tradition_new))
print("pairs whose every supporting checked chain is now flagged (upper bound of pairs lost)", len(lost))
Path(sys.argv[3]).write_text(json.dumps({"new_pairs": list(new_pairs.values()), "lost_pairs": [list(k) for k in lost],
                                         "released": len(released), "flagged": len(flagged)}, ensure_ascii=False), encoding="utf-8")
