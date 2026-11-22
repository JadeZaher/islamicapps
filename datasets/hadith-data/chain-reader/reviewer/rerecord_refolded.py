"""Re-record a batch's EXISTING reviewer outputs under the tolerant quote rule (validate_review_v1_1.py: vowel marks, tatweel and whitespace folded in quotes only), without running a model.

    python -B -X utf8 reviewer/rerecord_refolded.py [--batch review-applied-b001]        (from chain-reader/)

Writes beside the old records (which stay untouched): <batch>/outputs-refolded/{outcomes.tsv, summary.json, requeue.txt, reviews.jsonl, results.md, replacements.md, FOR_PIPELINE.md} and the pass-2 packets for the
corrections that have no second review yet in <batch>/second-pass-refolded/ (packets and jobs only; nothing is run). Pass-1 review wins over its re-queue's (reviewer/AGENTS.md §quote rule).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
import build_review_packets_v1_1 as builder  # noqa: E402
import record_reviews_v1_1 as recorder  # noqa: E402
import review_io_v1_1 as io  # noqa: E402
import review_rules_v1_1 as rules  # noqa: E402
from validate_review_v1_1 import validate_output  # noqa: E402

GROUPS = ("six Sunni books", "al-Faqih", "other Imami")
KINDS = ("confirm_reading", "no_chain", "confirm_with_correction", "refer_to_human", "prefer_or_keep_stored", "invalid")
ACTIONS = ("label_ai_reviewed", "apply_correction", "apply_no_chain", "label_disputed", "revert_to_stored", "queue_for_human", "keep_held", "requeue")
ACTION_WORDS = {"label_ai_reviewed": "label AI reviewed (the applied reading stays)", "apply_correction": "replace with the twice-agreed correction", "apply_no_chain": "replace with `no chain` (twice agreed)",
                "label_disputed": "label disputed (the applied reading stays)", "revert_to_stored": "revert to the stored chain", "queue_for_human": "queue for a human",
                "keep_held": "keep held", "requeue": "keep as is (no valid review)"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def percent(k: int, n: int) -> str:
    low, high = wilson(k, n)
    return f"{k} / {n} | {100 * k / n:.1f}% | {100 * low:.1f}% to {100 * high:.1f}%" if n else f"{k} / {n} | n/a | n/a"


def group_of(item: dict) -> str:
    work = item["context"]["work"]
    return "six Sunni books" if work["tradition"] == "sunni" else ("al-Faqih" if work["key"] == "imami:man-la-yahduruhu-al-faqih" else "other Imami")


def reviews_by_label(out: Path) -> dict[str, dict[str, dict]]:
    """{label: {item id: valid review}} for pass 1 and each of its re-queue rounds, each validated on its own under the current rule."""
    found = {}
    for label in io.labels(out, "1"):
        found[label] = {}
        for packet_path in sorted(io.packets_dir(out, label).glob("packet-*.json")):
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            output_path = io.outputs_dir(out, label) / packet_path.name.replace(".json", ".output.json")
            if output_path.is_file():
                found[label].update(validate_output(json.loads(output_path.read_text(encoding="utf-8")), packet)["reviews"])
    return found


def route_lines(reading: dict | None) -> list[str]:
    """The groups of a reading as `a  >  b | c  >  d` lines: `>` between levels, `|` between co-transmitters of one level."""
    lines = [" > ".join(" | ".join(link["surface"] for link in level) for level in group["levels"]).replace(" > ", "  >  ") for group in (reading or {}).get("groups") or []]
    return lines or ["(no chain)"]


def bullet(claims: list[dict]) -> list[str]:
    return [f"- {r['claim'].strip()}  \n  quote: «{r['quote']}»" for r in claims]


def replacements_md(rows: list[dict], first: dict, second: dict, items: dict, manifest: dict, batch: str) -> str:
    chosen = [r for r in rows if r["outcome"] in ("apply_correction", "apply_no_chain")]
    head = ["---", "type: handoff", "---", f"# {batch}: readings the reviewer would REPLACE (quotes refolded)", "",
            f"Source: `reviewer/{batch}`, prompt 1.1.0, re-recorded without a model under the tolerant quote rule (`outputs-refolded/`). Two independent `claude-opus-5-5` reviews wrote the same corrected routes "
            "(`review_rules_v1_1.outcome` = `apply_correction` / `apply_no_chain`). Nothing was applied or changed; this is a list for the fix-pipeline owner. Routes are Arabic surfaces as the reading lists them, "
            "levels in the order the reading gives them, `>` between levels, `|` between co-transmitters of one level. Each claim is the reviewer's own words; each quote is the report text's own characters "
            "(a quote the reviewer wrote with other vowel marks was replaced by the text's, and its review carries `quote_refolded`).", "",
            f"{len(chosen)} ids: " + ", ".join(r["id"] for r in chosen), ""]
    body = []
    for r in chosen:
        item, one, two = items[r["opaque"]], first[r["opaque"]][0], second[r["opaque"]][0]
        record = manifest["items"][r["opaque"]]
        group = group_of(item)
        title = f"## {r['id']} ({group}, {item['context']['work']['key'].split(':', 1)[1]}, {record['hadith_id']})"
        section = [title, "", "Original (applied) reading:", *[f"- {line}" for line in route_lines(item["readers"]["A"])], "",
                   "Corrected (review 1; review 2 wrote the same routes):", *[f"- {line}" for line in route_lines(one["corrected_reading"])], "",
                   f"Review 1 reasons (pass {first[r['opaque']][1]}, quotes refolded: {one.get('quote_refolded', 0)}):", *bullet(one["reasons"]), "",
                   f"Review 2 reasons (quotes refolded: {two.get('quote_refolded', 0)}):", *bullet(two["reasons"]), ""]
        body += section
    return "\n".join(head + body) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", default="review-applied-b001")
    args = parser.parse_args(argv)
    out = HERE / args.batch
    dest = out / "outputs-refolded"
    dest.mkdir(exist_ok=True)
    prompt = builder.prompt_record()
    second_dir = out / "second-pass-refolded"
    builder.second_pass(args.batch, prompt, into=second_dir, skip_reviewed=True)
    summary = recorder.record(out, write_to=dest, extra_second_dirs=(second_dir,))
    manifest = json.loads((out / "private" / "manifest.json").read_text(encoding="utf-8"))
    id_map = json.loads((out / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
    lines = (dest / "outcomes.tsv").read_text(encoding="utf-8").splitlines()
    columns = lines[0].split("\t")
    rows = [dict(zip(columns, line.split("\t"))) for line in lines[1:]]
    got = io.collect(out, "1")
    items, first = got["items"], got["reviews"]
    second = io.collect(out, "2")["reviews"]
    second_new = io.collect(second_dir, "2")["reviews"] if io.packets_dir(second_dir, "2").is_dir() else {}
    second = {**second_new, **second}
    labelled = reviews_by_label(out)
    old_lines = (out / "private" / "outcomes.tsv").read_text(encoding="utf-8").splitlines()
    old = {fields[0]: dict(zip(old_lines[0].split("	"), fields)) for fields in (line.split("	") for line in old_lines[1:])}
    for r in rows:
        r["group"] = group_of(items[r["opaque"]])
        r["kind"] = r["decision"] if r["decision"] in ("confirm_reading", "no_chain", "refer_to_human") else ("confirm_with_correction" if r["effective"] == "confirm_with_correction" else
                    "cosmetic_correction" if r["decision"] == "confirm_with_correction" else "prefer_or_keep_stored" if r["decision"] else "invalid")
        r["valid_b"] = r["valid"] == "True"
    count = lambda pred: Counter(r["group"] for r in rows if pred(r))
    by_group = lambda pred: [count(pred).get(g, 0) for g in GROUPS]
    sizes = [sum(1 for r in rows if r["group"] == g) for g in GROUPS]
    table = lambda label, numbers: f"| {label} | " + " | ".join(str(n) for n in numbers) + f" | {sum(numbers)} |"
    heads = f"| | " + " | ".join(f"{g} ({n})" for g, n in zip(GROUPS, sizes)) + f" | all ({sum(sizes)}) |\n|---|" + "---|" * (len(GROUPS) + 1)

    # recovered, agreement
    was_invalid = [o for o, r in old.items() if r["valid"] != "True"]
    recovered = Counter(first[o][1] for o in was_invalid if o in first)
    still_invalid = [o for o in was_invalid if o not in first]
    both = [o for o in labelled.get("1", {}) if o in labelled.get("1r", {})]
    same = [o for o in both if labelled["1"][o]["decision"] == labelled["1r"][o]["decision"]]
    agree_by = Counter((labelled["1"][o]["decision"], labelled["1r"][o]["decision"]) for o in both)
    empty = lambda o: bool(manifest["items"][o]["agreed_empty"])
    equivalent = [o for o in both if labelled["1"][o]["decision"] == labelled["1r"][o]["decision"] or (empty(o) and {labelled["1"][o]["decision"], labelled["1r"][o]["decision"]} == {"no_chain", "confirm_reading"})]
    corrections_both = [o for o in both if labelled["1"][o]["decision"] == "confirm_with_correction" and labelled["1r"][o]["decision"] == "confirm_with_correction"]
    same_routes = [o for o in corrections_both if recorder.second_run_agrees(items[o], labelled["1"][o], labelled["1r"][o])]
    refolded_items = [r for r in rows if int(r["quote_refolded"] or 0)]
    refolded_quotes = sum(int(r["quote_refolded"]) for r in refolded_items)

    # second reviews of substantive corrections
    needed = [r for r in rows if r["second_pass"] == "True"]
    twice = [r for r in needed if r["second_run"] == "True"]
    differ = [r for r in needed if r["second_run"] == "False"]
    waiting = [r for r in needed if r["second_run"] == ""]
    differing_kind = Counter(second[r["opaque"]][0]["decision"] for r in differ if r["opaque"] in second)
    new_waiting = [r["id"] for r in waiting]
    # wrong share
    confirmed_wrong = lambda r: r["outcome"] in ("apply_correction", "apply_no_chain", "revert_to_stored")
    alleged_wrong = lambda r: confirmed_wrong(r) or r["second_pass"] == "True" or r["decision"] == "keep_stored"
    wrong_rows = []
    for label, members in [(g, [r for r in rows if r["group"] == g]) for g in GROUPS] + [("all Imami", [r for r in rows if r["group"] != GROUPS[0]]), ("all", rows)]:
        valid = [r for r in members if r["valid_b"]]
        wrong_rows.append(f"| {label} | {percent(sum(confirmed_wrong(r) for r in valid), len(valid))} | {percent(sum(alleged_wrong(r) for r in valid), len(valid))} |")

    results = ["---", "type: results", "---", f"# {args.batch}: reviewer v1.1.0 over the 348 applied readings, re-recorded under the tolerant quote rule (2026-11-22)", "",
               "Per-item records: `outcomes.tsv` (real ids and opaque ids), `summary.json`, `requeue.txt`, `reviews.jsonl` (the review recorded for each item, quotes in the text's own characters). The old records "
               "(`../outputs/`, `../private/`) are untouched. No model was run, nothing applied, reverted or relabelled, no database touched.", "",
               "## The quote rule", "",
               "A quote is valid when it is a substring of the text (or of the context item it names), or when it is one after folding out ONLY Arabic vowel marks (U+064B-0652, U+0670), Qur'anic annotation marks, tatweel, "
               "and normalising whitespace. Letters match exactly (no hamza/alef/ya folding). A quote valid only after the fold is stored as the text's own characters and its review carries `quote_refolded: n`.", "",
               f"Recovery: of the {len(was_invalid)} items recorded invalid, {sum(recovered.values())} now have a valid review ({recovered.get('1', 0)} from pass 1, {recovered.get('1r', 0)} only from the re-queue) and "
               f"{len(still_invalid)} stay invalid. {len(refolded_items)} items ({refolded_quotes} quotes) in the final records were recorded through the refold.", "",
               "## Pass 1 against the re-queue", "",
               f"Rule: the pass-1 review is the record when it is valid (written first, independently); the re-queue's review is used only when pass 1 has none. {len(both)} items have a valid review in both; "
               f"decisions agree on {len(same)} ({100 * len(same) / max(len(both), 1):.0f}%); {len(equivalent)} if `no_chain` and `confirm_reading` on an agreed-empty reading (the same verdict: no chain) are counted equal. By pair (pass 1 -> re-queue): " + "; ".join(f"{a} -> {b}: {n}" for (a, b), n in sorted(agree_by.items())) + ". "
               f"Items where both wrote a correction: {len(corrections_both)}, of which {len(same_routes)} wrote the same routes.", "",
               "## Decisions (valid reviews)", "", heads,
               table("confirm_reading", by_group(lambda r: r["kind"] == "confirm_reading")),
               table("no_chain (on an applied \"no chain\" reading)", by_group(lambda r: r["kind"] == "no_chain")),
               table("confirm_with_correction (substantive; none equals the reading)", by_group(lambda r: r["kind"] == "confirm_with_correction")),
               table("confirm_with_correction equal to the reading (counted as a confirmation)", by_group(lambda r: r["kind"] == "cosmetic_correction")),
               table("refer_to_human", by_group(lambda r: r["kind"] == "refer_to_human")),
               table("prefer_reader_*, keep_stored", by_group(lambda r: r["kind"] == "prefer_or_keep_stored")),
               table("no valid review", by_group(lambda r: not r["valid_b"])), "",
               "## Pipeline actions (`review_rules_v1_1.outcome`)", "", heads]
    results += [table(f"{a}: {ACTION_WORDS[a]}", by_group(lambda r, a=a: r["outcome"] == a)) for a in ACTIONS if any(r["outcome"] == a for r in rows)]
    results += ["", "## Second reviews of the substantive corrections", "",
                f"{len(needed)} readings have a substantive correction (or `no_chain` against routes): {len(twice)} second reviews wrote the same corrected routes, {len(differ)} wrote something else "
                f"({', '.join(f'{k}: {v}' for k, v in differing_kind.items()) or 'none'}; ids: {', '.join(r['id'] for r in differ) or 'none'}), {len(waiting)} have no second review yet.",
                "", f"Awaiting a second review (packets built, not run: `../second-pass-refolded/jobs-pass-2.json`): {', '.join(f"{r['id']} ({r['group']})" for r in waiting) or 'none'}. Until it runs, the action for each is `label_disputed` (the applied reading stays).",
                "", "## Share of applied readings the reviewer finds wrong (all valid reviews)", "",
                "Confirmed wrong = a second review wrote the same correction (the pipeline would replace or revert it). Alleged wrong = the first review wrote a substantive correction, a `no_chain` against routes or `keep_stored`, "
                "confirmed or not. Referrals are in neither. Wilson 95% interval.", "",
                "| group | confirmed wrong: k / valid | share | Wilson 95% | alleged wrong: k / valid | share | Wilson 95% |", "|---|---|---|---|---|---|---|"]
    for label, members in [(g, [r for r in rows if r["group"] == g]) for g in GROUPS] + [("all Imami", [r for r in rows if r["group"] != GROUPS[0]]), ("all", rows)]:
        valid = [r for r in members if r["valid_b"]]
        a = percent(sum(confirmed_wrong(r) for r in valid), len(valid)).split(" | ")
        b = percent(sum(alleged_wrong(r) for r in valid), len(valid)).split(" | ")
        results.append(f"| {label} | " + " | ".join(a + b) + " |")
    referrals = [r for r in rows if r["decision"] == "refer_to_human"]
    results += ["", "Caveats: one model family reviewed model readers; this is a reviewer-on-readers measurement, not a human audit. Group sizes are 184 / 91 / 73, so the Imami intervals are wide.", "",
                "## Referrals", ""] + [f"{n}. {r['id']} ({r['group']}): {r['question']}" for n, r in enumerate(referrals, 1)]
    (dest / "results.md").write_text("\n".join(results) + "\n", encoding="utf-8", newline="\n")
    (dest / "replacements.md").write_text(replacements_md(rows, first, second, items, manifest, args.batch), encoding="utf-8", newline="\n")

    with (dest / "reviews.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for r in rows:
            review, label = first[r["opaque"]]
            two = second.get(r["opaque"])
            handle.write(json.dumps({"id": r["id"], "opaque": r["opaque"], "pass": label, "outcome": r["outcome"], "quote_refolded": review.get("quote_refolded", 0), "review": review,
                                     "second_review": two[0] if two else None}, ensure_ascii=False) + "\n")

    counts = Counter(r["outcome"] for r in rows)
    pipeline = ["---", "type: handoff", "---", f"# {args.batch}: what the pipeline owner ingests", "",
                "File: `datasets/hadith-data/chain-reader/reviewer/" + f"{args.batch}/outputs-refolded/outcomes.tsv` (UTF-8, tab separated, one header line, one row per applied reading, {len(rows)} rows). "
                "Supporting file, same folder: `reviews.jsonl` (one JSON line per reading: the recorded review with quotes in the text's own characters, and the second review where one exists).", "",
                "Columns: `opaque` (the reviewer's packet id, `cr1-xxxxxx`), `id` (the reading id, `b1-xxxxxx`, as in `reviews/ai/records/chain-fixes/submissions/*.jsonl` `reading.id`: look the fix up there), `status` (`applied`), "
                "`holds`, `not_clearable`, `valid`, `decision` (the reviewer's), `effective` (after rule (a): a correction equal to the reading is a confirmation), **`outcome`** (what the pipeline does), `action_class`, "
                "`second_pass` (a second review is required), `second_run` (`True` the second review wrote the same routes, `False` it did not, empty none yet), `uncertainty`, `question`, `problem`, `quote_refolded` "
                "(how many of the review's quotes were recorded through the vowel-mark fold; 0 for none).", "",
                "## Counts by `outcome`", "", "| outcome | readings | what to do | label |", "|---|---|---|---|"]
    labels = {"label_ai_reviewed": rules.LABEL_AI_REVIEWED, "apply_correction": rules.LABEL_CORRECTED, "label_disputed": rules.LABEL_DISPUTED}
    pipeline += [f"| `{a}` | {counts[a]} | {ACTION_WORDS[a]} | {labels.get(a, '')} |" for a in ACTIONS if counts[a]]
    pipeline += ["", f"Total {sum(counts.values())}. `<date>` is the date the pipeline records the review. Each `apply_correction` replaces the applied reading with the corrected routes of `reviews.jsonl` (`second_review` agrees with `review`); the side-by-side "
                 "list is `replacements.md`. A `label_disputed` reading STAYS applied and is labelled: "
                 f"{sum(r['decision'] == 'refer_to_human' for r in rows if r['outcome'] == 'label_disputed')} are referrals to a human, {sum(r['second_run'] == 'False' for r in rows if r['outcome'] == 'label_disputed')} had a second review that wrote a different correction, "
                 f"{len(waiting)} wait for a second review in `../second-pass-refolded/` (packets and `jobs-pass-2.json`, not run): {', '.join(r['id'] for r in waiting) or 'none'}. A human decision on a reading always wins over these outcomes (`human_decides`).", "",
                 "Nothing in this folder was applied. Re-run `python -B -X utf8 reviewer/rerecord_refolded.py` (from chain-reader/) after the second pass is run into `second-pass-refolded/outputs/pass-2/`; it re-reads every output and rewrites these files."]
    (dest / "FOR_PIPELINE.md").write_text("\n".join(pipeline) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"summary": summary, "recovered": dict(recovered), "still_invalid": still_invalid, "both": len(both), "same": len(same), "agree_by": {f"{a}->{b}": n for (a, b), n in agree_by.items()},
                      "equivalent": len(equivalent), "corrections_both": len(corrections_both), "same_routes": len(same_routes), "waiting": new_waiting}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
