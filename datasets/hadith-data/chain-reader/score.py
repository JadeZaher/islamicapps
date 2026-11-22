"""Score chain-reader outputs against the labelled pilot set (see README.md and AGENTS.md §score).

    python score.py --reports pilot/reports.jsonl --outputs outputs/run-a [--outputs-b outputs/run-b] --out outputs/run-a/score

Writes `<out>/score.md` (one table per work, Wilson 95% intervals) and `<out>/disagreements.tsv` (everything a human should read).
Denominators are the outputs that validate once offsets are re-found from the surfaces (`validate.repair_offsets`): a reader that
miscounts characters is counted in the strict-pass column, not as a wrong reading.
"""

from __future__ import annotations

import argparse
import math
import re
from collections import defaultdict
from pathlib import Path

from norm import fold_exact, fold_loose, surface_in_text
from validate import check_directory, load_reports

ISNAD_PHRASE = re.compile(r"(?:ال)?[اإ]سناد|السند|بسنده")


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(successes: int, total: int) -> str:
    if total == 0:
        return "n/a (0)"
    low, high = wilson(successes, total)
    return f"{successes}/{total} = {100 * successes / total:.0f}% ({100 * low:.0f}-{100 * high:.0f})"


def reader_routes(output: dict) -> list[tuple[str, ...]]:
    """The reader's routes as tuples of folded surfaces; a «بهذا الإسناد» back reference is dropped (stored chains never carry it)."""
    routes = []
    for route in output["routes"]:
        names = tuple(fold_exact(link["surface"]) for link in route["links"]
                      if not (link["kind"] == "back_reference" and ISNAD_PHRASE.search(fold_loose(link["surface"]))))
        if names:
            routes.append(names)
    return routes


def stored_route(chain: dict, text: str) -> tuple[tuple[str, ...], bool]:
    """The stored chain as the reader can see it: only surfaces that stand in the text; and whether any were dropped.

    A stored chain can hold names the report's own text lacks (a «و بهذا الإسناد» report whose chain was completed from the
    previous report); a reader that sees only this text cannot reproduce them, so they are left out of the comparison.
    """
    kept = tuple(fold_exact(surface) for surface in chain["surfaces"] if fold_exact(surface) and surface_in_text(surface, text))
    return kept, len(kept) < sum(1 for surface in chain["surfaces"] if fold_exact(surface))


def _contiguous(small: list[str], large: list[str]) -> bool:
    return bool(small) and any(large[i:i + len(small)] == small for i in range(len(large) - len(small) + 1))


def loosely_equal(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
    """Same number of links, each pair equal or one a contiguous word run of the other (a gloss or verb left in or out)."""
    if len(a) != len(b):
        return False
    for left, right in zip(a, b):
        x, y = fold_loose(left).split(), fold_loose(right).split()
        if x != y and not _contiguous(x, y) and not _contiguous(y, x):
            return False
    return True


def contains_name(routes: list[tuple[str, ...]], name: str) -> bool:
    words = fold_loose(name).split()
    return any(_contiguous(words, fold_loose(surface).split()) for route in routes for surface in route)


def items_of(report: dict) -> list[dict]:
    """What the human labels say about this report: labelled chains and report-level labels, each with the stored routes it covers."""
    stored = [stored_route(chain, report["text"]) for chain in report["stored_chains"]]
    items = []
    for chain, (route, reduced) in zip(report["stored_chains"], stored):
        if chain["verdict"] != "unlabelled":
            items.append({"scope": "chain", "verdict": chain["verdict"], "kind": chain["kind"], "note": chain["note"],
                          "state": chain["label_state"], "routes": [route], "reduced": reduced, "chain_id": chain["chain_id"]})
    for label in report["report_labels"]:
        items.append({"scope": "report", "verdict": label["verdict"], "kind": label["kind"], "note": label["note"],
                      "state": label["label_state"], "routes": [route for route, _ in stored if route], "reduced": any(r for _, r in stored), "chain_id": ""})
    return items


def judge(item: dict, routes: list[tuple[str, ...]]) -> dict:
    """Exact and loose agreement between the reader's routes and the stored routes an item covers."""
    stored = item["routes"]
    if item["scope"] == "chain":
        exact = stored[0] in routes
        loose = exact or any(loosely_equal(stored[0], route) for route in routes)
    else:
        exact = set(stored) == set(routes)
        loose = exact or (len(stored) == len(routes) and all(any(loosely_equal(s, r) for r in routes) for s in stored))
    return {"exact": exact, "loose": loose}


class Tally:
    def __init__(self) -> None:
        self.counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    def add(self, name: str, success: bool) -> None:
        self.counts[name][0] += bool(success)
        self.counts[name][1] += 1

    def show(self, name: str) -> str:
        successes, total = self.counts.get(name, (0, 0))
        return rate(successes, total)


def score(reports: dict[str, dict], outputs_a: Path, outputs_b: Path | None, out_dir: Path) -> dict:
    strict = check_directory(reports, outputs_a)
    repaired = check_directory(reports, outputs_a, repair=True)
    second = check_directory(reports, outputs_b, repair=True) if outputs_b else None
    tallies: dict[str, Tally] = defaultdict(Tally)
    disagreements: list[list[str]] = []

    def groups(report: dict) -> list[str]:
        return [f"{report['tradition']}:{report['work']}", f"{report['tradition']} (all)", "ALL"]

    def row(source: str, why: str, report: dict, extra: dict | None = None, reader: list | None = None) -> list[str]:
        head = re.sub(r"\s+", " ", report["text"][:240])
        extra = extra or {}
        return [source, why, report["id"], report["hadith_id"], f"{report['tradition']}:{report['work']}",
                extra.get("verdict", report["report_verdict"]), extra.get("kind", ""), extra.get("state") or "", extra.get("note", ""),
                " || ".join(" > ".join(r) for r in extra.get("routes", [])), " || ".join(" > ".join(r) for r in (reader or [])),
                head]

    for report_id, report in reports.items():
        for group in groups(report):
            tallies[group].add("strict_valid", strict[report_id]["status"] == "valid")
            tallies[group].add("repaired_valid", repaired[report_id]["status"] == "valid")
            tallies[group].add("fenced", bool(strict[report_id]["warnings"]))
        outcome = repaired[report_id]
        if outcome["status"] != "valid":
            disagreements.append(row("validation", f"no valid output ({outcome['status']}): " + outcome["errors"][0][:140], report))
            continue
        routes = reader_routes(outcome["output"])
        notes = bool(outcome["output"]["notes"])
        for item in items_of(report):
            verdict = judge(item, routes)
            for group in groups(report):
                tallies[group].add("stored_reduced", item["reduced"])
                if item["verdict"] == "correct":
                    tallies[group].add("correct_exact", verdict["exact"])
                    tallies[group].add("correct_loose", verdict["loose"])
                    if item["state"] == "current":
                        tallies[group].add("correct_exact_current", verdict["exact"])
                else:
                    tallies[group].add("defective_differs", not verdict["exact"])
                    firm = item["state"] in ("current", "confirmed")
                    if firm:
                        tallies[group].add("defective_differs_firm", not verdict["exact"])
            if item["verdict"] == "correct" and not verdict["exact"]:
                disagreements.append(row("label", "labelled correct, reader differs" + ("" if not verdict["loose"] else " (loosely equal)"), report, item, routes))
            if item["verdict"] == "defective" and verdict["exact"]:
                disagreements.append(row("label", "labelled defective, reader reproduces stored (missed, or label stale)", report, item, routes))
        if report["report_verdict"] == "defective" and report["expected_names"]:
            found = all(contains_name(routes, name) for name in report["expected_names"])
            for group in groups(report):
                tallies[group].add("expected_found", found)
            if not found:
                disagreements.append(row("label", "reader lacks the name the note says was lost: " + ", ".join(report["expected_names"]), report,
                                         {"verdict": "defective", "routes": [stored_route(c, report["text"])[0] for c in report["stored_chains"]]}, routes))
        if second is not None:
            other = second[report_id]
            if other["status"] == "valid":
                routes_b = reader_routes(other["output"])
                agree = set(routes) == set(routes_b)
                for group in groups(report):
                    tallies[group].add("run_agreement", agree)
                if not agree:
                    disagreements.append(row("run_pair", "run A and run B routes differ (A shown first; B after |||)", report,
                                             {"routes": [stored_route(c, report["text"])[0] for c in report["stored_chains"]]}, routes + [("|||",)] + routes_b))
    out_dir.mkdir(parents=True, exist_ok=True)
    header = ["source", "why", "id", "hadith_id", "work", "label_verdict", "label_kind", "label_state", "label_note", "stored_routes", "reader_routes", "text_head"]
    with (out_dir / "disagreements.tsv").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(header) + "\n")
        for line in disagreements:
            handle.write("\t".join(cell.replace("\t", " ").replace("\n", " ") for cell in line) + "\n")
    (out_dir / "score.md").write_text(render(tallies, reports, second is not None), encoding="utf-8", newline="\n")
    return {group: {name: list(value) for name, value in tally.counts.items()} for group, tally in tallies.items()}


def render(tallies: dict[str, Tally], reports: dict[str, dict], paired: bool) -> str:
    order = sorted(tallies, key=lambda g: (g == "ALL", g.endswith("(all)"), g))
    size = defaultdict(lambda: [0, 0])
    for report in reports.values():
        for group in (f"{report['tradition']}:{report['work']}", f"{report['tradition']} (all)", "ALL"):
            size[group][report["report_verdict"] == "defective"] += 1
    lines = ["# Chain reader pilot: score", "",
             "Wilson 95% intervals in brackets. Match and agreement denominators are the outputs that validate after offsets are re-found from the surfaces;",
             "`strict valid` counts offsets exactly as the reader gave them. Comparisons are diacritic- and whitespace-insensitive; a back reference",
             "to an isnad (بهذا الإسناد) is dropped from the reader's route before comparing, as stored chains never carry it.", ""]
    total = tallies["ALL"]
    lines += ["## Go / no-go numbers (all works)", "",
              f"- Passing `validate.py`, offsets as given: {total.show('strict_valid')}; after offset repair: {total.show('repaired_valid')}; answers wrapped in a markdown fence: {total.show('fenced')}",
              f"- Labelled-correct chains reproduced exactly: {total.show('correct_exact')}; loosely (gloss/verb left in or out): {total.show('correct_loose')}; labels from round 4 only: {total.show('correct_exact_current')}",
              f"- Labelled-defective items where the reader differs from the stored chain: {total.show('defective_differs')}; confirmed/current labels only: {total.show('defective_differs_firm')}",
              f"- Defective reports whose note names the lost name, and the reader's routes contain it: {total.show('expected_found')}",
              f"- Labelled items whose stored chain holds names the report text lacks (compared on the names the text has): {total.show('stored_reduced')}"]
    if paired:
        lines.append(f"- Two runs, exact same routes per report: {total.show('run_agreement')}")
    lines += ["", "## Per work", "",
              "| work | reports (def/corr) | strict valid | valid after repair | correct chains exact | correct chains loose | defective differs | defective differs (firm) | lost name found" + (" | run agreement |" if paired else " |"),
              "|---|---|---|---|---|---|---|---|---" + ("|---|" if paired else "|")]
    for group in order:
        tally = tallies[group]
        cells = [group, f"{size[group][1]}/{size[group][0]}", tally.show("strict_valid"), tally.show("repaired_valid"), tally.show("correct_exact"),
                 tally.show("correct_loose"), tally.show("defective_differs"), tally.show("defective_differs_firm"), tally.show("expected_found")]
        if paired:
            cells.append(tally.show("run_agreement"))
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "`disagreements.tsv` lists every labelled-correct mismatch, every labelled-defective item the reader reproduced, every missed lost name, every invalid output and every run-to-run difference.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", required=True)
    parser.add_argument("--outputs", required=True, help="directory of <report id>.json from run A")
    parser.add_argument("--outputs-b", help="a second independent run on the same packets")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    score(load_reports(Path(args.reports)), Path(args.outputs), Path(args.outputs_b) if args.outputs_b else None, Path(args.out))
    print((Path(args.out) / "score.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
