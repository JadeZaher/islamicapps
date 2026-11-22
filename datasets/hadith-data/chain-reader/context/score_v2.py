"""Score v2 chain outputs with the unchanged v1 scorer, after the tool expands them (see score_v2_notes.md).

    python context/score_v2.py --reports pilot/reports.jsonl --outputs outputs-v2/run-a [--outputs-b outputs-v2/run-b]
        --out outputs-v2/run-a/score [--imam drop|keep] [--packets context/pilot-v2/packets] [--exclude ids.txt]

Per output: levels -> routes with offsets (expand.py), derived links (compiler head, inherited) dropped, imam_in_text dropped or kept as a
narrator, then v1's score.py. The scorer is run twice: with its attached-«و» artifact corrected (<out>, the figure to read) and as v1 would
have it (<out>-v1wa). With --packets the holds of every reading are written to <out>-holds.tsv. v1 files are never edited.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import score  # noqa: E402  (v1 scorer: reused, never edited)
import validate as v1  # noqa: E402
from expand import DERIVED_KINDS, expand  # noqa: E402
from holds import compute_holds  # noqa: E402
from norm import fold_loose, surface_in_text as v1_surface_in_text  # noqa: E402


def surface_in_text_with_attached_wa(surface: str, text: str) -> bool:
    """v1's whole-word test, also true when the name's first word carries an attached «و» in the text («وأحمد بن عبدة»)."""
    if v1_surface_in_text(surface, text):
        return True
    needle = fold_loose(surface)
    return bool(needle) and bool(re.search(r"(?:^|\s)و" + re.escape(needle) + r"(?:\s|$)", fold_loose(text)))


def to_v1_shape(reading: dict, imam: str = "drop") -> dict:
    """The expanded reading as v1 would have written it: compiler head and inherited links dropped, imam_in_text dropped or kept as a narrator."""
    routes, seen = [], set()
    for route in reading["routes"]:
        tail = route.get("shared_tail_from")
        links, shift = [], 0
        for index, link in enumerate(route["links"]):
            kind = link["kind"]
            if kind in DERIVED_KINDS or (kind == "imam_in_text" and imam == "drop"):
                if isinstance(tail, int) and index < tail:
                    shift += 1
                continue
            links.append(dict(link, kind="narrator") if kind == "imam_in_text" else {k: link[k] for k in ("surface", "start", "end", "kind")})
        if not links:
            continue
        key = tuple((l["start"], l["end"]) for l in links)
        if key in seen:
            continue
        seen.add(key)
        new_tail = tail - shift if isinstance(tail, int) else None
        routes.append({"links": links, "shared_tail_from": new_tail if new_tail is not None and 0 <= new_tail < len(links) else None})
    ends = [l["end"] for r in routes for l in r["links"]]
    return {"id": reading["id"], "routes": routes, "matn_start": max(ends) if ends else 0, "notes": reading.get("notes", [])}


def convert_directory(source: Path, target: Path, reports: dict[str, dict], imam: str, contexts: dict[str, dict], holds_rows: list | None) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    stats = {"converted": 0, "left_unconverted": 0, "cannot_read": 0}
    for path in sorted(source.glob("*.json")):
        report = reports.get(path.stem)
        try:
            parsed, _ = v1.parse_output(path.read_text(encoding="utf-8"))
        except ValueError:
            (target / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")   # the scorer reports it as not_json
            stats["left_unconverted"] += 1
            continue
        if report is None or not isinstance(parsed, dict) or not isinstance(parsed.get("groups"), list):
            (target / path.name).write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
            stats["left_unconverted"] += 1
            continue
        context = contexts.get(path.stem)
        if parsed.get("status") == "cannot_read_without_previous_report":
            stats["cannot_read"] += 1
        reading, errors = expand(parsed, report["text"], context)
        if holds_rows is not None:
            stored = [s for chain in report.get("stored_chains", []) for s in chain["surfaces"]]
            holds_rows.append((path.stem, errors[:1], [h["code"] for h in compute_holds(reading, parsed, report["text"], context, stored)]))
        if reading is None:
            (target / path.name).write_text(json.dumps({"id": path.stem, "routes": "invalid: " + "; ".join(errors)[:200]}, ensure_ascii=False), encoding="utf-8")
            stats["left_unconverted"] += 1
            continue
        (target / path.name).write_text(json.dumps(to_v1_shape(reading, imam), ensure_ascii=False), encoding="utf-8")
        stats["converted"] += 1
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", required=True)
    parser.add_argument("--outputs", required=True)
    parser.add_argument("--outputs-b")
    parser.add_argument("--out", required=True)
    parser.add_argument("--imam", choices=("drop", "keep"), default="drop")
    parser.add_argument("--packets", help="directory of v2 chain packets (their context feeds the holds)")
    parser.add_argument("--exclude", help="file with report ids to leave out of the scored set (examples used in the prompt, owner-ruling cases)")
    args = parser.parse_args(argv)
    reports = v1.load_reports(Path(args.reports))
    if args.exclude:
        skip = set(Path(args.exclude).read_text(encoding="utf-8").split())
        reports = {k: v for k, v in reports.items() if k not in skip}
        scored = Path(args.out).parent / (Path(args.out).name + "-reports.jsonl")
        scored.write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in reports.values()), encoding="utf-8")
        args.reports = str(scored)
    contexts: dict[str, dict] = {}
    if args.packets:
        for path in sorted(Path(args.packets).glob("packet-*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    contexts[row["id"]] = row["context"]
    out = Path(args.out)
    holds_rows: list | None = [] if args.packets else None
    shaped_a = out.parent / (out.name + "-v1shape-a")
    stats = convert_directory(Path(args.outputs), shaped_a, reports, args.imam, contexts, holds_rows)
    print("converted", stats, file=sys.stderr)
    if holds_rows is not None:
        (out.parent / (out.name + "-holds.tsv")).write_text("id\texpand_error\tholds\n" + "".join(f"{i}\t{' '.join(e)}\t{','.join(h)}\n" for i, e, h in holds_rows), encoding="utf-8")
    forwarded = ["--reports", args.reports, "--outputs", str(shaped_a)]
    if args.outputs_b:
        shaped_b = out.parent / (out.name + "-v1shape-b")
        convert_directory(Path(args.outputs_b), shaped_b, reports, args.imam, contexts, None)
        forwarded += ["--outputs-b", str(shaped_b)]
    original = score.surface_in_text
    try:
        score.surface_in_text = surface_in_text_with_attached_wa
        status = score.main(forwarded + ["--out", args.out])
        score.surface_in_text = original
        score.main(forwarded + ["--out", args.out + "-v1wa"])
    finally:
        score.surface_in_text = original
    return status


if __name__ == "__main__":
    raise SystemExit(main())
