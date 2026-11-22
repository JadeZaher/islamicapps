"""Chain-fix engine: check one reader output, compare it with the stored chain, plan the rows (see AGENTS.md §engine).

    python -I chain_fix_engine.py < request.json > response.json

Request `{"items": [{"key", "text", "expected_id", "output", "base", "record_id", "source_work_id", "evidence",
"require_coverage", "reader_format"?, "context"?}]}`; response `{"results": [{"key", "errors", "reading", "offsets_repaired",
"comparison", "planned", "computed_evidence", "holds", "proposals", "needs_ruling"}]}`. `reader_format` `v2` (levels, no
offsets) is expanded by `chain-reader/context/expand.py` and validated by `validate_v2.py`; `text` is a text/metadata checker
output, which only files proposals. Every Arabic rule of the pipeline lives here so the submit tool, the database apply and
the projection replay share one implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
for extra in (DATA / "chain-reader" / "v3", DATA / "chain-reader" / "context", DATA / "chain-reader", DATA):   # -I drops the script directory
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from extract_isnad_unified import _strip_arabic_marks, name_normalize  # noqa: E402  (the projection's own forms)
from norm import fold_loose  # noqa: E402
from score import ISNAD_PHRASE  # noqa: E402
from validate import repair_offsets, validate  # noqa: E402  (the reader's own validator, unchanged)
from expand import expand as expand_v2  # noqa: E402  (v2 levels -> routes with offsets)
from holds import compute_holds  # noqa: E402  (why a reading is queued, never auto-applied: HOLDS.md)
from validate_v2 import validate_chain as validate_chain_v2, validate_text as validate_text_v2  # noqa: E402
from expand_v3 import expand as expand_v3  # noqa: E402  (reader v3: spelling fold, compiler aliases, same man once)
from holds_v3 import compute_holds as compute_holds_v3  # noqa: E402  (v3 holds: chain-reader/v3/HOLDS.md)
from validate_v3 import validate_v3  # noqa: E402

# Links the reader derives rather than reads: not substrings of the report text. Kept with kind and origin; never planned rows.
DERIVED_KINDS = ("compiler_head", "inherited")

FIX_KINDS = ("no_change", "link_added", "link_removed", "surface_changed", "route_split", "routes_merged",
             "shared_tail_attached", "chain_removed", "chain_added")
LINK_KIND_FOR_READER_KIND = {"narrator": "unclassified", "relation": "unclassified", "unnamed": "anonymous",
                             "back_reference": "not_a_narrator"}
EXTRACTION_METHOD = "chain_fix_reader"
TRAILING_BLESSING_MARK = re.compile(r"\s+\(?ع\)?$")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def comparison_key(surface: str) -> str:
    """One form for a stored and a read surface: the extractor's trailing «ع» dropped, normalized, folded."""
    return fold_loose(name_normalize(TRAILING_BLESSING_MARK.sub("", surface or "").strip()))


def is_isnad_phrase(link: dict) -> bool:
    """«بهذا الإسناد» and the like: stored chains never carry it (score.py drops it the same way)."""
    return link["kind"] == "back_reference" and bool(ISNAD_PHRASE.search(fold_loose(link["surface"])))


def check(text: str, output: object, expected_id: str) -> tuple[object, list[str], bool]:
    """(reading, errors, offsets_repaired): the reader's validator, after offsets are re-found from the surfaces if needed."""
    errors = validate(output, text, expected_id)
    if not errors:
        return output, [], False
    if not isinstance(output, dict):
        return output, errors, False
    repaired = repair_offsets(output, text)
    repaired_errors = validate(repaired, text, expected_id)
    if repaired_errors:
        return output, errors, False                     # report the reader's own errors, not the repair's
    return repaired, [], True


def _lcs_pairs(left: list[str], right: list[str]) -> list[tuple[int, int]]:
    """Index pairs of one longest common subsequence (equal keys), earliest match first."""
    rows, cols = len(left), len(right)
    table = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(rows - 1, -1, -1):
        for j in range(cols - 1, -1, -1):
            table[i][j] = table[i + 1][j + 1] + 1 if left[i] == right[j] else max(table[i + 1][j], table[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < rows and j < cols:
        if left[i] == right[j]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def _reader_routes(reading: dict) -> list[list[dict]]:
    """Routes in text order (by their spans), each without the «بهذا الإسناد» link; empty routes dropped."""
    routes = [[link for link in route["links"] if not is_isnad_phrase(link)] for route in reading["routes"]]
    routes = [route for route in routes if route]
    return sorted(routes, key=lambda route: [(link["start"], link["end"]) for link in route])


def _ends_with_back_reference(reading: dict) -> set[int]:
    """Indexes (in `_reader_routes` order) of routes that end in a dropped «بهذا الإسناد»."""
    marked = []
    for route in reading["routes"]:
        kept = [link for link in route["links"] if not is_isnad_phrase(link)]
        if kept:
            marked.append(([(link["start"], link["end"]) for link in kept], any(is_isnad_phrase(link) for link in route["links"])))
    marked.sort(key=lambda item: item[0])
    return {index for index, (_, flagged) in enumerate(marked) if flagged}


def compare(reading: dict, base: dict) -> dict:
    """Fix kinds and the link alignment between the reading and the stored chain (computed, never claimed)."""
    reader = _reader_routes(reading)
    stored = [branch["mentions"] for branch in sorted(base["chains"], key=lambda branch: branch["branch"])]
    reader_keys = [[comparison_key(link["surface"]) for link in route] for route in reader]
    stored_keys = [[comparison_key(mention["surface_ar"]) for mention in branch] for branch in stored]

    # Each read route is aligned with the stored branch sharing its longest run of names (ties: the earlier branch). Two read
    # routes may align with one stored branch (a split): both keep its names, so a shared tail keeps its evidence.
    route_pairs = {}
    for ri, keys in enumerate(reader_keys):
        best = max(((len(_lcs_pairs(keys, s)), -si) for si, s in enumerate(stored_keys)), default=(0, 0))
        if best[0] > 0:
            route_pairs[ri] = -best[1]

    kinds: set[str] = set()
    kept: list[list[str | None]] = []
    added, removed, changed = [], [], []
    pending_removed: list[tuple[int, dict]] = []
    kept_anywhere: set[str] = set()
    for ri, route in enumerate(reader):
        si = route_pairs.get(ri)
        kept_ids: list[str | None] = [None] * len(route)
        matched_stored = set()
        if si is not None:
            for a, b in _lcs_pairs(reader_keys[ri], stored_keys[si]):
                kept_ids[a] = stored[si][b]["id"]
                matched_stored.add(b)
        kept.append(kept_ids)
        kept_anywhere.update(mention_id for mention_id in kept_ids if mention_id)
        unmatched_stored = [b for b in range(len(stored[si])) if b not in matched_stored] if si is not None else []
        for position, link in enumerate(route):
            if kept_ids[position] is not None:
                continue
            # A stored link at the same slot whose words contain, or lie inside, the read surface: trimmed or extended.
            partner = next((b for b in unmatched_stored if stored_keys[si][b] and reader_keys[ri][position]
                            and (stored_keys[si][b] in reader_keys[ri][position] or reader_keys[ri][position] in stored_keys[si][b])), None)
            if partner is not None:
                unmatched_stored.remove(partner)
                changed.append({"route": ri, "position": position, "from": stored[si][partner]["surface_ar"],
                                "from_id": stored[si][partner]["id"], "to": link["surface"], "span": [link["start"], link["end"]]})
                kinds.add("surface_changed")
            else:
                added.append({"route": ri, "position": position, "surface": link["surface"], "span": [link["start"], link["end"]]})
                kinds.add("link_added")
        if si is not None:
            changed_ids = {item["from_id"] for item in changed}
            for b in unmatched_stored:
                if stored[si][b]["id"] not in changed_ids:
                    pending_removed.append((ri, stored[si][b]))
        tail_from = next((r["shared_tail_from"] for r in reading["routes"]
                          if [l for l in r["links"] if not is_isnad_phrase(l)] == route), None)
        if tail_from is not None and any(item["route"] == ri and item["position"] >= tail_from for item in added):
            kinds.add("shared_tail_attached")
    # A stored name is removed only when no read route keeps it (a split keeps names in the other route).
    changed_ids = {item["from_id"] for item in changed}
    seen_removed = set()
    for ri, mention in pending_removed + [(None, m) for branch in stored for m in branch]:
        if mention["id"] in kept_anywhere or mention["id"] in changed_ids or mention["id"] in seen_removed:
            continue
        seen_removed.add(mention["id"])
        removed.append({"route": ri, "stored_mention_id": mention["id"], "surface": mention["surface_ar"]})
        kinds.add("link_removed")
    if not reader and stored:
        kinds.add("chain_removed")
    elif reader and not stored:
        kinds.add("chain_added")
    elif len(reader) > len(stored):
        kinds.add("route_split")
    elif len(reader) < len(stored):
        kinds.add("routes_merged")
    if sorted(map(tuple, reader_keys)) == sorted(map(tuple, stored_keys)):
        kinds = {"no_change"}
    return {"fix_kinds": [kind for kind in FIX_KINDS if kind in kinds], "kept_mention_ids": kept, "added": added,
            "removed": removed, "changed": changed, "routes_before": len(stored), "routes_after": len(reader)}


def review_unit_ids(surface: str, teacher: str | None, student: str | None, source_work_id: str) -> tuple[str, str]:
    """Coarse and fine review-unit keys, the projection's formula (pg_export/export_postgres.py `review_unit_ids`)."""
    coarse = sha256_text("\x1f".join((surface, teacher or "", source_work_id)))
    fine = sha256_text("\x1f".join((surface, teacher or "", student or "", source_work_id)))
    return coarse, fine


def plan(text: str, reading: dict, base: dict, comparison: dict, record_id: str, source_work_id: str) -> dict:
    """The chain and mention rows this reading becomes, ids in the projection's scheme (see AGENTS.md §rows)."""
    reader = _reader_routes(reading)
    stored_by_id = {m["id"]: (branch["branch"], m) for branch in base["chains"] for m in branch["mentions"]}
    stored_neighbours = {}
    for branch in base["chains"]:
        ids = [m["id"] for m in branch["mentions"]]
        for index, mention_id in enumerate(ids):
            stored_neighbours[mention_id] = (ids[index + 1] if index + 1 < len(ids) else None, ids[index - 1] if index > 0 else None)
    relies_elsewhere = _ends_with_back_reference(reading)
    chains = []
    for index, route in enumerate(reader):
        kept = comparison["kept_mention_ids"][index]
        surfaces = [stored_by_id[kept[p]][1]["surface_ar"] if kept[p] else _strip_arabic_marks(text[link["start"]:link["end"]])
                    for p, link in enumerate(route)]
        normalized = [name_normalize(surface) for surface in surfaces]
        mentions = []
        for p, link in enumerate(route):
            teacher = normalized[p + 1] if p + 1 < len(route) else None
            student = normalized[p - 1] if p > 0 else None
            coarse, fine = review_unit_ids(normalized[p], teacher, student, source_work_id)
            # Identity is carried only when the name and both neighbours are the stored ones (same fine review unit).
            carry = bool(kept[p]) and stored_neighbours[kept[p]] == (kept[p + 1] if p + 1 < len(route) else None, kept[p - 1] if p > 0 else None)
            mentions.append({
                "id": f"mention:{record_id}:{index:04d}:{p:04d}", "position": p, "surface_ar": surfaces[p],
                "surface_normalized": normalized[p], "teacher_context_normalized": teacher, "student_context_normalized": student,
                "review_unit_id": coarse, "review_unit_fine_id": fine, "reader_kind": link["kind"],
                "link_kind_if_new": LINK_KIND_FOR_READER_KIND[link["kind"]], "span": [link["start"], link["end"]],
                "kept_mention_id": kept[p], "carry_identity": carry,
            })
        suspension = "back_reference" if route[0]["kind"] == "back_reference" or index in relies_elsewhere else None
        chains.append({"id": f"chain:{record_id}:{index:04d}", "branch": index, "length": len(route), "suspension": suspension,
                       "extraction_method": EXTRACTION_METHOD, "mentions": mentions})
    return {"chains": chains}


def evidence_problems(text: str, quotes: list[str], comparison: dict, require_coverage: bool) -> list[str]:
    """Every quote must be an exact substring; a reader who saw the stored chain must also quote around every change."""
    problems = [f"evidence: quote {index} is not an exact substring of the text: {quote!r}"
                for index, quote in enumerate(quotes) if not quote or quote not in text]
    if not quotes:
        problems.append("evidence: give at least one quote copied exactly from the text")
    if problems or not require_coverage:
        return problems
    spans = [(m.start(), m.start() + len(q)) for q in quotes for m in re.finditer(re.escape(q), text)]
    for item in comparison["added"] + comparison["changed"]:
        start, end = item["span"]
        if not any(s <= start and end <= e for s, e in spans):
            problems.append(f"evidence: no quote contains the {'added' if 'surface' in item else 'changed'} link "
                            f"{text[start:end]!r} at {start}-{end}; quote the words around it")
    folded_quotes = [comparison_key(q) for q in quotes]
    for item in comparison["removed"]:
        key = comparison_key(item["surface"])
        if key and not any(key in folded for folded in folded_quotes):
            problems.append(f"evidence: no quote shows where the removed stored link {item['surface']!r} stood; quote those words")
    return problems


def computed_evidence(text: str, comparison: dict) -> list[dict]:
    """The exact text of every added or changed link, with offsets: evidence the tool derives, labelled as such."""
    out = []
    for kind, items in (("link_added", comparison["added"]), ("surface_changed", comparison["changed"])):
        for item in items:
            start, end = item["span"]
            out.append({"quote": text[start:end], "start": start, "end": end, "for": kind})
    return out


def derived_links(reading: dict) -> list[dict]:
    """Every derived or source-named link with its route, place, kind and origin (the work profile, the previous report it
    comes from, or the text for an Imam named in it), so the page can label each one."""
    found = []
    for route_index, route in enumerate(reading["routes"]):
        for position, link in enumerate(route["links"]):
            if link["kind"] in DERIVED_KINDS or link["kind"] == "imam_in_text":
                found.append({"route": route_index, "position": position, "kind": link["kind"], "surface": link["surface"],
                              "origin": link.get("from") or ("text" if link["start"] is not None else None),
                              "span": [link["start"], link["end"]] if link["start"] is not None else None})
    return found


def v1_from_v2(reading: dict, allow_inherited: bool = False) -> tuple[dict | None, list[str]]:
    """An expanded v2 reading in the v1 shape the comparison reads: derived links (the compiler head, which the projection adds
    itself) dropped, an Imam named in the text kept as a narrator. A link inherited from another report cannot be applied here."""
    routes = []
    for index, route in enumerate(reading["routes"]):
        if not allow_inherited and any(link["kind"] == "inherited" for link in route["links"]):
            return None, [f"inherited: route {index} repeats names from an earlier report; this pipeline applies only names written in this text"]
        written = [link for link in route["links"] if link["start"] is not None]
        if not written:
            continue
        dropped_before_tail = sum(1 for link in route["links"][: route["shared_tail_from"] or 0] if link["start"] is None)
        links = [{"surface": link["surface"], "start": link["start"], "end": link["end"],
                  "kind": "narrator" if link["kind"] == "imam_in_text" else link["kind"]} for link in written]
        tail = route["shared_tail_from"] - dropped_before_tail if route["shared_tail_from"] is not None else None
        routes.append({"links": links, "shared_tail_from": tail if tail is not None and 0 < tail < len(links) else None})
    # An Imam named in the text ends its route after expand's matn start; the v1 shape needs every link before the matn.
    ends = [link["end"] for route in routes for link in route["links"]]
    matn_start = max([reading["matn_start"], *ends]) if ends else reading["matn_start"]
    return {"id": reading["id"], "routes": routes, "matn_start": matn_start, "notes": list(reading.get("notes") or [])}, []


def proposals_of(output: dict, kind: str) -> list[dict]:
    """The reader's other findings (identity, lexicon date, duplicate records, garbled text, translation, text or metadata that
    differ from a source). Never applied: filed for reviewers with both readings and their sources (AGENTS.md §proposals)."""
    found = [{"kind": fix["kind"], "reason": fix["reason"], "evidence": fix["evidence"], "confidence": fix["confidence"],
              "differences": []} for fix in output.get("fixes") or []]
    if kind == "text":
        for part, kinds in (("text_check", ("text_differs_from_source", "text_truncated_or_merged")),
                            ("metadata_check", ("wrong_number", "wrong_book_or_chapter", "grading_missing_or_misattributed", "locator_missing"))):
            check_part = output.get(part) or {}
            if check_part.get("status") != "differs":
                continue
            for proposal in found:
                if proposal["kind"] in kinds:
                    proposal["differences"] += check_part["differences"]
                    proposal["compared"] = check_part.get("compared", [])
    return found


def run_item(item: dict) -> dict:
    result = {"key": item["key"], "errors": [], "reading": None, "offsets_repaired": False, "comparison": None, "planned": None,
              "computed_evidence": [], "holds": [], "proposals": [], "needs_ruling": False, "derived_links": []}
    output, context = item["output"], item.get("context") or {}
    stored = [m["surface_ar"] for c in item["base"]["chains"] for m in c["mentions"]]
    if item.get("reader_format") == "text":
        errors = validate_text_v2(output, item["text"], item["expected_id"], context)
        if errors:
            result["errors"] = errors
        else:
            result["proposals"] = proposals_of(output, "text")
        return result
    if item.get("reader_format") == "v3":
        # The reader's own v3 output (`reader_output_v3`): validated and expanded by the v3 tool against the packet's text and
        # context; derived links are checked there (an inherited name against the previous report's text, the compiler head
        # against the work profile) and recorded with their origin; planned rows come from the written links only.
        errors = validate_v3(output, item["text"], item["expected_id"], context)
        if errors:
            result["errors"] = errors
            return result
        expanded, errors = expand_v3(output, item["text"], context) if output["status"] == "read" else (None, [])
        result["holds"] = compute_holds_v3(expanded, output, item["text"], context, stored, item.get("other_output"))
        result["proposals"] = proposals_of(output, "chain")
        result["needs_ruling"] = bool(output.get("needs_ruling"))
        if expanded is None:
            result["errors"] = errors or ["status: the reader could not read this report without the previous report's chain; nothing to apply"]
            return result
        result["derived_links"] = derived_links(expanded)
        if any(link["kind"] == "inherited" for link in result["derived_links"]):
            # Recorded and validated, not yet written as rows: an inherited mention needs the earlier report's written mention.
            result["holds"].append({"code": "inherited_links_not_applied",
                                    "detail": "the reading takes names from an earlier report; recorded with their origin, applied only by a person"})
        output, errors = v1_from_v2(expanded, allow_inherited=True)
        if errors:
            result["errors"] = errors
            return result
    if item.get("reader_format") == "v2":
        errors = validate_chain_v2(output, item["text"], item["expected_id"], context)
        if errors:
            result["errors"] = errors
            return result
        expanded, errors = expand_v2(output, item["text"], context) if output["status"] == "read" else (None, [])
        result["holds"] = compute_holds(expanded, output, item["text"], context, stored)
        result["proposals"] = proposals_of(output, "chain")
        result["needs_ruling"] = bool(output.get("needs_ruling"))
        if expanded is None:
            result["errors"] = errors or ["status: the reader could not read this report without the previous report's chain; "
                                          "nothing to apply (its other findings, if any, are filed as proposals with --proposals-only)"]
            return result
        output, errors = v1_from_v2(expanded)
        if errors:
            result["errors"] = errors
            return result
    reading, errors, repaired = check(item["text"], output, item["expected_id"])
    if errors:
        result["errors"] = errors
        return result
    comparison = compare(reading, item["base"])
    problems = evidence_problems(item["text"], item.get("evidence", []), comparison, item.get("require_coverage", False))
    if problems:
        result["errors"] = problems
        return result
    if item.get("reader_format") not in ("v2", "v3"):
        result["holds"] = compute_holds(reading, {}, item["text"], None, stored)
    result.update(reading=reading, offsets_repaired=repaired, comparison=comparison,
                  computed_evidence=computed_evidence(item["text"], comparison),
                  planned=plan(item["text"], reading, item["base"], comparison, item["record_id"], item["source_work_id"]))
    return result


def main() -> int:
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    response = {"results": [run_item(item) for item in request["items"]]}
    sys.stdout.buffer.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
