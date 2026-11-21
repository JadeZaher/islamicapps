#!/usr/bin/env python3
"""J3: narrator-resolution review queue with ranked CANDIDATE identities (never decisions).

Needs J1 output (surface_census.jsonl.gz). Writes only under diagnostics/narrator-resolution/:
  review_queue_surfaces.jsonl.gz   top-N surfaces, cumulative coverage, name+graph ranked candidates
  review_queue.jsonl               review units (surface, context) for the top-500 surfaces
  review_queue_top500_surfaces.csv skim view
  review_queue_summary.json        coverage numbers and candidate-availability statistics
Every candidate is `candidate_only`; every unit has decision=null. See diagnostics/AGENTS.md.

Usage: python -B diagnostics/rank_narrator_resolution_candidates.py [--surfaces 10000] [--unit-surfaces 500]
"""

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from narrator_surface_logic import (  # noqa: E402
    parse_components, parse_father_indx, parse_generation, parse_indx_list,
    score_candidate,
)

JOB = "narrator-resolution"
START, END = "<START>", "<END>"
RELATIONAL_AXIS = {"relational_or_fragment"}
FATHER_SURFACES = {"ابيه", "ابوه"}
GRANDFATHER_SURFACES = {"جده"}
STOP_UNITS = {"بن", "ابن", "بنت", "ابو"}
MAX_POSTING = 1500
GRAPH_RESCORE_POOL = 100      # name-ranked pool re-scored with graph evidence before truncation
WEAK_NEIGHBOR_MAX = 10        # a neighbour with more name candidates than this carries no edge signal
SURFACE_CANDIDATES_KEPT = 10
UNIT_CANDIDATES_KEPT = 5
CONTEXT_SHARE = 0.8


class RegistryIndex:
    """Registry name components with an inverted unit index and graph fields."""

    def __init__(self, regen) -> None:
        self.views: dict[str, list] = {}
        self.name_raw: dict[str, str] = {}
        self.teachers: dict[str, set] = {}
        self.students: dict[str, set] = {}
        self.generation: dict[str, int | None] = {}
        self.death: dict[str, int | None] = {}
        self.father: dict[str, str | None] = {}
        postings: dict[str, set] = defaultdict(set)
        skipped_without_arabic = 0
        with open(common.REGISTRY_PATH, encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle):
                indx = (row.get("scholar_indx") or "").strip()
                name = (row.get("name") or "").strip()
                if not indx or not name:
                    continue
                arabic = regen._extract_arabic_name(name)
                if not arabic:
                    skipped_without_arabic += 1
                    continue
                views = [("name", parse_components(regen.narrator_normalize(arabic)))]
                self.views[indx] = views
                self.name_raw[indx] = name
                self.teachers[indx] = parse_indx_list(row.get("teachers_inds"))
                self.students[indx] = parse_indx_list(row.get("students_inds"))
                self.generation[indx] = parse_generation(row.get("grade"))
                death = (row.get("death_date_hijri") or "").strip()
                self.death[indx] = int(death) if death.lstrip("-").isdigit() else None
                self.father[indx] = parse_father_indx(row.get("parents"))
                for _, components in views:
                    for unit in components.units:
                        if unit not in STOP_UNITS:
                            postings[unit].add(indx)
        self.postings = postings
        self.skipped_without_arabic = skipped_without_arabic
        total = max(1, len(self.views))
        self.idf = {unit: math.log(total / len(ids)) for unit, ids in postings.items()}

    def retrieve(self, norm: str, limit: int = 25) -> list[dict]:
        """Name-component candidates for a normalized surface, best first (candidate only)."""
        surface = parse_components(norm)
        query = [u for u in surface.units if u not in STOP_UNITS]
        informative = [u for u in query if len(self.postings.get(u, ())) <= MAX_POSTING] or query
        accumulator: dict[str, float] = defaultdict(float)
        for unit in informative:
            for indx in self.postings.get(unit, ()):
                accumulator[indx] += self.idf.get(unit, 0.0)
        shortlist = sorted(accumulator.items(), key=lambda item: (-item[1], int(item[0])))[:150]
        scored = []
        for indx, _ in shortlist:
            best = None
            for kind, components in self.views[indx]:
                score, evidence, conflicts = score_candidate(surface, components)
                if best is None or score > best[0]:
                    best = (score, evidence, conflicts, kind)
            score, evidence, conflicts, kind = best
            if score <= 0:
                continue
            scored.append({
                "scholar_indx": indx, "name_raw": self.name_raw[indx], "name_component_score": score,
                "evidence": evidence, "conflicts": conflicts,
                "channel": "name_component",
            })
        scored.sort(key=lambda c: (-c["name_component_score"], int(c["scholar_indx"])))
        return scored[:limit]

    def teacher_edge(self, candidate: str, teacher: str) -> bool:
        return teacher in self.teachers.get(candidate, ()) or candidate in self.students.get(teacher, ())

    def student_edge(self, candidate: str, student: str) -> bool:
        return student in self.students.get(candidate, ()) or candidate in self.teachers.get(student, ())


def read_census(path: Path, limit: int) -> list[dict]:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def contexts_reaching(counter_items: list, share: float) -> list:
    """Largest-first contexts covering `share` of the total (the unit cut)."""
    total = sum(count for _, count in counter_items)
    kept, running = [], 0
    for key, count in sorted(counter_items, key=lambda item: (-item[1], item[0])):
        kept.append((key, count))
        running += count
        if running >= share * total:
            break
    return kept


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surfaces", type=int, default=10000)
    parser.add_argument("--unit-surfaces", type=int, default=500)
    args = parser.parse_args()
    started = time.time()
    out = common.output_directory(JOB)
    census_path = out / "surface_census.jsonl.gz"
    if not census_path.exists():
        raise SystemExit("run build_narrator_surface_census.py (J1) first")
    census = read_census(census_path, args.surfaces)
    all_total = json.loads((out / "surface_curve.json").read_text(encoding="utf-8"))["totals"]["unresolved_surface_occurrences"]
    rank_of = {row["surface_normalized"]: row["rank"] for row in census}
    category_of = {row["surface_normalized"]: row["category"] for row in census}
    unit_scope = {row["surface_normalized"] for row in census if row["rank"] <= args.unit_surfaces}
    regen = common.load_regen()
    extractor = common.load_extractor()
    exact_index, _ = regen.build_narrator_index(str(common.REGISTRY_PATH))
    registry = RegistryIndex(regen)

    # Pass: full contexts for in-scope surfaces, unit row credit, resolved-in-source frequency.
    teacher_ctx: dict[str, Counter] = defaultdict(Counter)
    student_ctx: dict[str, Counter] = defaultdict(Counter)
    unit_data: dict[tuple, dict] = {}
    resolved_by_source: Counter = Counter()
    scope_rows_completable = Counter()
    for row_number, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition")) or "<missing>"
        source = common.clean(row.get("source")) or "<missing>"
        try:
            branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
        except extractor.IsnadExtractionLimitError:
            continue
        row_surfaces: set[str] = set()
        row_units: dict[tuple, int] = defaultdict(int)
        for branch in branches:
            norms = [regen.narrator_normalize(raw) for raw in branch]
            for position, norm in enumerate(norms):
                indx = exact_index.get(norm)
                if indx:
                    resolved_by_source[(source, indx)] += 1
                    continue
                row_surfaces.add(norm)
                teacher = norms[position + 1] if position + 1 < len(norms) else END
                student = norms[position - 1] if position > 0 else START
                if norm in rank_of:
                    teacher_ctx[norm][teacher] += 1
                    student_ctx[norm][student] += 1
                if norm in unit_scope:
                    axis = "student" if category_of[norm] in RELATIONAL_AXIS else "teacher"
                    context = student if axis == "student" else teacher
                    other = teacher if axis == "student" else student
                    key = (norm, axis, context)
                    entry = unit_data.get(key)
                    if entry is None:
                        entry = unit_data[key] = {
                            "occurrences": 0, "rows": 0, "credit": 0.0, "completable_rows": 0,
                            "by_tradition": Counter(), "by_source": Counter(), "other": Counter(),
                            "terminal": 0, "refs": [],
                        }
                    entry["occurrences"] += 1
                    entry["by_tradition"][tradition] += 1
                    entry["by_source"][source] += 1
                    entry["other"][other] += 1
                    if position + 1 == len(norms):
                        entry["terminal"] += 1
                    if len(entry["refs"]) < 5 and not any(r["line"] == row_number for r in entry["refs"]):
                        entry["refs"].append(common.row_reference(row_number, row))
                    row_units[key] += 1
        if row_surfaces and row_surfaces <= unit_scope:
            scope_rows_completable[tradition] += 1
            per_surface_units: dict[str, list] = defaultdict(list)
            for key in row_units:
                per_surface_units[key[0]].append(key)
            for surface_norm, keys in per_surface_units.items():
                for key in keys:
                    unit_data[key]["credit"] += 1.0 / len(row_surfaces) / len(keys)
                    unit_data[key]["completable_rows"] += 1
        for key in row_units:
            unit_data[key]["rows"] += 1

    # Candidate ranking per surface (name components + aggregated graph support over contexts).
    candidate_cache: dict[str, list] = {}

    def name_candidates(norm: str) -> list:
        if norm in candidate_cache:
            return candidate_cache[norm]
        found = registry.retrieve(norm, GRAPH_RESCORE_POOL)
        if norm in unit_scope:       # only unit-scope pools are kept for context re-scoring
            candidate_cache[norm] = found
        return found

    surface_rows = []
    availability = Counter()
    for row in census:
        norm = row["surface_normalized"]
        category = row["category"]
        occurrences = row["occurrences"]
        if category == "collective_or_anonymous":
            candidates = []
        elif category == "relational_or_fragment":
            candidates = []     # derived relations are resolved from the neighbour at unit level
        else:
            candidates = [dict(c) for c in name_candidates(norm)]
        teacher_resolved = sum(c for t, c in teacher_ctx[norm].items() if exact_index.get(t))
        student_resolved = sum(c for s, c in student_ctx[norm].items() if exact_index.get(s))
        for candidate in candidates:
            teacher_support = sum(c for t, c in teacher_ctx[norm].items()
                                  if exact_index.get(t) and registry.teacher_edge(candidate["scholar_indx"], exact_index[t]))
            student_support = sum(c for s, c in student_ctx[norm].items()
                                  if exact_index.get(s) and registry.student_edge(candidate["scholar_indx"], exact_index[s]))
            candidate["graph_support"] = {
                "teacher_edge_occurrences": teacher_support, "student_edge_occurrences": student_support,
                "teacher_edge_share_of_all_occurrences": round(teacher_support / occurrences, 4),
                "student_edge_share_of_all_occurrences": round(student_support / occurrences, 4),
            }
            candidate["score"] = round(candidate["name_component_score"]
                                       + 0.5 * teacher_support / occurrences
                                       + 0.3 * student_support / occurrences, 4)
            candidate["status"] = "candidate_only"
        candidates.sort(key=lambda c: (-c["score"], int(c["scholar_indx"])))
        kept = candidates[:SURFACE_CANDIDATES_KEPT]
        top = kept[0]["score"] if kept else 0.0
        margin = round(top - kept[1]["score"], 4) if len(kept) > 1 else (top if kept else 0.0)
        bucket = ("not_a_single_identity" if category in ("collective_or_anonymous", "relational_or_fragment")
                  else "none" if not kept else "strong>=0.7" if top >= 0.7
                  else "moderate>=0.4" if top >= 0.4 else "weak<0.4")
        availability[(bucket, row["rank"] <= args.unit_surfaces)] += 1
        surface_rows.append({
            "rank": row["rank"], "surface_normalized": norm, "raw_examples": row["raw_examples"],
            "occurrences": occurrences, "cumulative_occurrences": row["cumulative_occurrences"],
            "cumulative_share_of_unresolved": row["cumulative_share_of_unresolved"],
            "category": category, "by_tradition": row["by_tradition"],
            "context_resolved_share": {"teacher": round(teacher_resolved / occurrences, 4),
                                       "student": round(student_resolved / occurrences, 4)},
            "candidates": kept, "top_score": top, "margin_top1_top2": margin, "candidate_bucket": bucket,
            "candidate_status": "candidate_only", "decision": None, "review_state": "unreviewed",
        })
    surfaces_written = common.write_jsonl(out, "review_queue_surfaces.jsonl.gz", surface_rows, gzipped=True)
    surface_lookup = {r["surface_normalized"]: r for r in surface_rows}

    # Units for the top surfaces: 80% context cut per surface, unit candidates re-scored with context.
    units_by_surface: dict[str, list] = defaultdict(list)
    for key, entry in unit_data.items():
        units_by_surface[key[0]].append((key, entry["occurrences"]))
    weak_cache: dict[str, set] = {}

    def weak_neighbors(neighbor_norm: str) -> set:
        if neighbor_norm not in weak_cache:
            pool = registry.retrieve(neighbor_norm, WEAK_NEIGHBOR_MAX + 1)
            weak_cache[neighbor_norm] = (
                {c["scholar_indx"] for c in pool if c["name_component_score"] >= 0.15}
                if len(pool) <= WEAK_NEIGHBOR_MAX else set())
        return weak_cache[neighbor_norm]

    unit_rows = []
    residuals = []
    for row in census:
        norm = row["surface_normalized"]
        if norm not in unit_scope:
            continue
        category = row["category"]
        keep_keys = [k for k, _ in contexts_reaching(units_by_surface[norm], CONTEXT_SHARE)]
        kept_set = set(keep_keys)
        residual_occurrences = sum(e["occurrences"] for k, e in unit_data.items()
                                   if k[0] == norm and k not in kept_set)
        residuals.append({"surface_normalized": norm, "units_kept": len(kept_set),
                          "units_not_listed": len(units_by_surface[norm]) - len(kept_set),
                          "occurrences_not_listed": residual_occurrences})
        base = candidate_cache.get(norm, []) if category not in (
            "collective_or_anonymous", "relational_or_fragment") else []
        for key in keep_keys:
            _, axis, context = key
            entry = unit_data[key]
            context_indx = exact_index.get(context)
            candidates = []
            if category == "relational_or_fragment" and context_indx and norm in (FATHER_SURFACES | GRANDFATHER_SURFACES):
                hops = 2 if norm in GRANDFATHER_SURFACES else 1
                ancestor, trail = context_indx, [context_indx]
                for _ in range(hops):
                    ancestor = registry.father.get(ancestor) if ancestor else None
                    trail.append(ancestor)
                if ancestor and ancestor in registry.views:
                    candidates.append({
                        "scholar_indx": ancestor, "name_raw": registry.name_raw[ancestor],
                        "name_component_score": 0.0, "score": 0.5, "channel": "derived_relation",
                        "evidence": [f"registry parents field chain {'>'.join(str(t) for t in trail)} (previous narrator {context_indx})"],
                        "conflicts": [], "status": "candidate_only"})
            for candidate in base:
                scored = dict(candidate)
                indx = scored["scholar_indx"]
                score = scored["name_component_score"]
                features = {"name_component_score": score, "teacher_edge": "none", "student_edge": "none",
                            "tabaqah_gap": None, "resolved_in_same_source": 0,
                            "generation": registry.generation.get(indx), "death_hijri": registry.death.get(indx)}
                dominant_source = entry["by_source"].most_common(1)[0][0]
                features["resolved_in_same_source"] = resolved_by_source[(dominant_source, indx)]
                for side, neighbor in (("teacher", context if axis == "teacher" else None),
                                       ("student", context if axis == "student" else None)):
                    if neighbor is None:
                        # secondary context: dominant opposite-axis neighbour
                        neighbor = entry["other"].most_common(1)[0][0]
                    neighbor_indx = exact_index.get(neighbor)
                    edge = registry.teacher_edge if side == "teacher" else registry.student_edge
                    if neighbor_indx and edge(indx, neighbor_indx):
                        features[f"{side}_edge"] = "exact"
                        score += 0.5 if side == "teacher" else 0.3
                    elif not neighbor_indx and neighbor not in (START, END):
                        pool = weak_neighbors(neighbor)
                        if pool and any(edge(indx, w) for w in pool):
                            features[f"{side}_edge"] = "weak_via_unresolved_neighbour_candidates"
                            features[f"{side}_neighbour_candidate_count"] = len(pool)
                            score += 0.1 if side == "teacher" else 0.05
                    if side == "teacher" and neighbor_indx:
                        mine, theirs = registry.generation.get(indx), registry.generation.get(neighbor_indx)
                        if mine is not None and theirs is not None:
                            gap = mine - theirs
                            features["tabaqah_gap"] = gap
                            if gap < 0 or gap >= 3:
                                score -= 0.3
                                scored["conflicts"] = scored["conflicts"] + [f"tabaqah_gap_implausible:{gap}"]
                scored["features"] = features
                scored["score"] = round(max(score, 0.0), 4)
                scored["status"] = "candidate_only"
                candidates.append(scored)
            candidates.sort(key=lambda c: (-c["score"], -c.get("features", {}).get("resolved_in_same_source", 0),
                                           int(c["scholar_indx"])))
            kept = candidates[:UNIT_CANDIDATES_KEPT]
            margin = round(kept[0]["score"] - kept[1]["score"], 4) if len(kept) > 1 else (kept[0]["score"] if kept else 0.0)
            unit_rows.append({
                "unit_id": hashlib.sha256(f"{norm}|{axis}:{context}|".encode("utf-8")).hexdigest()[:24],
                "surface_normalized": norm, "category": category,
                "context_axis": axis, "context_surface": context,
                "context_resolved_registry_id": context_indx,
                "secondary_context_top": [[s, c] for s, c in entry["other"].most_common(3)],
                "occurrences": entry["occurrences"], "rows": entry["rows"],
                "rows_completable_if_scope_resolved": entry["completable_rows"],
                "row_credit_if_scope_resolved": round(entry["credit"], 4),
                "terminal_position_share": round(entry["terminal"] / entry["occurrences"], 4),
                "by_tradition": dict(entry["by_tradition"].most_common()),
                "by_source_top5": dict(entry["by_source"].most_common(5)),
                "source_work_id": None,
                "candidates": kept, "margin_top1_top2": margin,
                "evidence_rows": entry["refs"],
                "candidate_status": "candidate_only", "decision": None, "review_state": "unreviewed",
            })
    unit_rows.sort(key=lambda u: (-u["row_credit_if_scope_resolved"], -u["occurrences"], u["unit_id"]))
    units_written = common.write_jsonl(out, "review_queue.jsonl", unit_rows)

    with open(out / "review_queue_top500_surfaces.csv", "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "surface", "occurrences", "cumulative_share", "category", "traditions",
                         "top_candidate_indx", "top_candidate_name", "top_score", "margin", "bucket", "status"])
        for r in surface_rows[:args.unit_surfaces]:
            top = r["candidates"][0] if r["candidates"] else {}
            writer.writerow([r["rank"], r["surface_normalized"], r["occurrences"], r["cumulative_share_of_unresolved"],
                             r["category"], json.dumps(r["by_tradition"], ensure_ascii=False),
                             top.get("scholar_indx", ""), top.get("name_raw", ""), r["top_score"],
                             r["margin_top1_top2"], r["candidate_bucket"], "candidate_only_unreviewed"])

    def coverage_at(n: int) -> dict:
        n = min(n, len(census))
        covered = census[n - 1]["cumulative_occurrences"]
        return {"top_n_surfaces": n, "occurrences_covered": covered,
                "percent_of_unresolved": round(100 * covered / all_total, 1)}

    bucket_summary = defaultdict(lambda: {"surfaces": 0, "occurrences": 0})
    for r in surface_rows:
        b = bucket_summary[r["candidate_bucket"]]
        b["surfaces"] += 1
        b["occurrences"] += r["occurrences"]
    top500_buckets = defaultdict(lambda: {"surfaces": 0, "occurrences": 0})
    for r in surface_rows[:args.unit_surfaces]:
        b = top500_buckets[r["candidate_bucket"]]
        b["surfaces"] += 1
        b["occurrences"] += r["occurrences"]
    tradition_buckets = defaultdict(lambda: defaultdict(int))
    for r in surface_rows[:args.unit_surfaces]:
        for tradition, count in r["by_tradition"].items():
            tradition_buckets[tradition][r["candidate_bucket"]] += count
    summary = {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/rank_narrator_resolution_candidates.py",
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH, census_path)),
        "coverage_curve": [coverage_at(n) for n in (100, 500, 2000, 10000)],
        "files": {"review_queue_surfaces.jsonl.gz": surfaces_written, "review_queue.jsonl": units_written},
        "unit_scope_surfaces": args.unit_surfaces,
        "unit_context_cut": CONTEXT_SHARE,
        "units_listed": units_written,
        "unit_graph_evidence": {
            "units_with_exact_teacher_or_student_edge_on_a_candidate": sum(
                1 for u in unit_rows if any(
                    "exact" in (c.get("features", {}).get("teacher_edge", ""), c.get("features", {}).get("student_edge", ""))
                    for c in u["candidates"])),
            "units_with_only_weak_edges": sum(
                1 for u in unit_rows if not any(
                    "exact" in (c.get("features", {}).get("teacher_edge", ""), c.get("features", {}).get("student_edge", ""))
                    for c in u["candidates"]) and any(
                    "weak" in (c.get("features", {}).get("teacher_edge", "") + c.get("features", {}).get("student_edge", ""))
                    for c in u["candidates"])),
            "units_with_no_candidates": sum(1 for u in unit_rows if not u["candidates"]),
            "units_with_top1_margin_at_least_0.2": sum(1 for u in unit_rows if u["margin_top1_top2"] >= 0.2),
            "units_with_derived_relation_candidate": sum(
                1 for u in unit_rows if any(c["channel"] == "derived_relation" for c in u["candidates"])),
        },
        "units_not_listed_residual": sum(r["units_not_listed"] for r in residuals),
        "occurrences_not_listed_residual": sum(r["occurrences_not_listed"] for r in residuals),
        "rows_completable_if_whole_unit_scope_resolved_by_tradition": dict(scope_rows_completable),
        "rows_completable_if_whole_unit_scope_resolved": sum(scope_rows_completable.values()),
        "candidate_buckets_by_surface_all_queue": {k: v for k, v in sorted(bucket_summary.items())},
        "candidate_buckets_by_surface_unit_scope": {k: v for k, v in sorted(top500_buckets.items())},
        "unit_scope_occurrences_by_tradition_and_bucket": {t: dict(b) for t, b in tradition_buckets.items()},
        "registry_narrators_indexed": len(registry.views),
        "registry_narrators_without_arabic_name": registry.skipped_without_arabic,
        "unit_scope_surface_residuals_top20": sorted(residuals, key=lambda r: -r["occurrences_not_listed"])[:20],
        "notes": ["All candidates are candidate_only; no decision is asserted.",
                  "bucket thresholds are triage labels for reviewer attention, not confidence in identity.",
                  "tabaqah gap outside 0..2 demotes (-0.3) rather than prunes."],
        "seconds": round(time.time() - started, 1),
    }
    common.write_json(out, "review_queue_summary.json", summary)
    print(json.dumps({"surfaces": surfaces_written, "units": units_written, "seconds": summary["seconds"]}))


if __name__ == "__main__":
    main()
