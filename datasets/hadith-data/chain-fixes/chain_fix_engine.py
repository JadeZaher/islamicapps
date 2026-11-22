"""Chain-fix engine: check one reader output, compare it with the stored chain, plan the rows (see AGENTS.md §engine).

    python -I chain_fix_engine.py < request.json > response.json

Request `{"items": [{"key", "text", "expected_id", "output", "base", "record_id", "source_work_id", "evidence",
"require_coverage", "reader_format"?, "tool_version"?, "context"?, "previous"?}]}`; response `{"results": [{"key", "errors",
"reading", "offsets_repaired", "comparison", "planned", "computed_evidence", "holds", "proposals", "needs_ruling",
"derived_links", "disposition"}]}`. `reader_format` `v2` (levels, no offsets) is expanded by `chain-reader/context/expand.py`
and validated by `validate_v2.py`; `v3`/`v3_1` readings by the tool `tool_version` names (AGENTS.md §reader formats); `text` is a
text/metadata checker output, which only files proposals. Every Arabic rule of the pipeline lives here so the submit tool, the
database apply and the projection replay share one implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
for extra in (DATA / "pg_export", DATA / "chain-reader" / "v3_4", DATA / "chain-reader" / "v3_3", DATA / "chain-reader" / "v3_2", DATA / "chain-reader" / "v3_1", DATA / "chain-reader" / "v3",
              DATA / "chain-reader" / "context", DATA / "chain-reader", DATA):   # -I drops the script directory
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
from expand_v3_1 import expand as expand_v3_1  # noqa: E402  (tool v3.1: folds, empty readings, asker rule; v3_1/AGENTS.md)
from holds_v3_1 import compute_holds as compute_holds_v3_1  # noqa: E402  (v3.1 holds: chain-reader/v3_1/HOLDS.md)
from validate_v3_1 import validate_v3_1  # noqa: E402
from expand_v3_2 import expand as expand_v3_2, link_key as link_key_v3_2, readings_agree as readings_agree_v3_2  # noqa: E402  (tool v3.2: a variant group is a remark, never a route; v3_2/README.md)
from holds_v3_2 import compute_holds as compute_holds_v3_2  # noqa: E402  (v3.2 holds: chain-reader/v3_2/HOLDS.md)
from validate_v3_2 import validate_v3_2  # noqa: E402
from holds_v3_3_pipeline import compute_holds as compute_holds_v3_3  # noqa: E402  (tool v3.3, half-route hold taken back to v3.2's: AGENTS.md §tool v3.3)
import holds_v3_3_pipeline  # noqa: E402
import holds_v3_4  # noqa: E402
from expand_v3_4 import expand as expand_v3_4, readings_agree as readings_agree_v3_4  # noqa: E402  (tool v3.4: the saying label; v3_4/README.md)
from validate_v3_4 import validate_v3_4  # noqa: E402

holds_v3_4.base = holds_v3_3_pipeline          # v3.4's holds stand on the pipeline's v3.3 (the corrected half-route hold), per saying

# Links the reader derives rather than reads: not substrings of the report text. Kept with kind and origin; the compiler head is
# never a row (the projection derives it); an inherited name is a row that repeats the cited report's written mention.
DERIVED_KINDS = ("compiler_head", "inherited")
# The reader toolchain per tool version: (validate, expand, holds). A reading names the prompt it ran under (its format) and the
# tool that expanded and held it; batch 001 was read under prompt v3 and is re-triaged by tool v3.1 (AGENTS.md §reader formats).
TOOLS = {"v3": (validate_v3, expand_v3, compute_holds_v3), "v3_1": (validate_v3_1, expand_v3_1, compute_holds_v3_1),
         "v3_2": (validate_v3_2, expand_v3_2, compute_holds_v3_2), "v3_3": (validate_v3_2, expand_v3_2, compute_holds_v3_3),
         "v3_4": (validate_v3_4, expand_v3_4, holds_v3_4.compute_holds)}
# The tools that may read a reading made under each prompt: a later tool reads an earlier prompt's output, never the reverse.
TOOLS_FOR_FORMAT = {"v3": ("v3", "v3_1", "v3_2", "v3_3", "v3_4"), "v3_1": ("v3_1", "v3_2", "v3_3", "v3_4"), "v3_2": ("v3_2", "v3_3", "v3_4"), "v3_4": ("v3_4",)}
V3_SHAPED = tuple(TOOLS_FOR_FORMAT)
# Tools that keep a variant group as a remark (never a route) and read the second pass for the union of remarks.
VARIANT_TOOLS = ("v3_2", "v3_3", "v3_4")
AGREE = {"v3_2": readings_agree_v3_2, "v3_3": readings_agree_v3_2, "v3_4": readings_agree_v3_4}
# A cited report's chain may lend its names only when a tested rule or a person stands behind it.
INHERITABLE_STATUSES = ("checked_by_rule", "verified_by_reviewer")
NO_CHAIN_DISPOSITION = "no_chain_by_reading"

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


def stored_neighbours_of(base: dict) -> dict[str, tuple[str | None, str | None]]:
    """Stored mention id -> (teacher id, student id) in its stored branch: what the carry rule compares."""
    neighbours = {}
    for branch in base["chains"]:
        ids = [m["id"] for m in branch["mentions"]]
        for index, mention_id in enumerate(ids):
            neighbours[mention_id] = (ids[index + 1] if index + 1 < len(ids) else None, ids[index - 1] if index > 0 else None)
    return neighbours


def chain_rows(index: int, entries: list[dict], suspension: str | None, record_id: str, source_work_id: str,
               stored_neighbours: dict) -> dict:
    """One planned chain from its entries (surface, reader kind, span, kept id, inherited root), ids, contexts and carry computed."""
    normalized = [name_normalize(entry["surface_ar"]) for entry in entries]
    kept = [entry["kept_mention_id"] for entry in entries]
    mentions = []
    for p, entry in enumerate(entries):
        teacher = normalized[p + 1] if p + 1 < len(entries) else None
        student = normalized[p - 1] if p > 0 else None
        coarse, fine = review_unit_ids(normalized[p], teacher, student, source_work_id)
        # Identity is carried only when the name and both neighbours are the stored ones (same fine review unit).
        carry = bool(kept[p]) and stored_neighbours[kept[p]] == (kept[p + 1] if p + 1 < len(entries) else None, kept[p - 1] if p > 0 else None)
        mentions.append({
            "id": f"mention:{record_id}:{index:04d}:{p:04d}", "position": p, "surface_ar": entry["surface_ar"],
            "surface_normalized": normalized[p], "teacher_context_normalized": teacher, "student_context_normalized": student,
            "review_unit_id": coarse, "review_unit_fine_id": fine, "reader_kind": entry["reader_kind"],
            "link_kind_if_new": entry["link_kind_if_new"], "span": entry["span"],
            "kept_mention_id": kept[p], "carry_identity": carry,
            "inherited_from_mention_id": entry.get("inherited_from_mention_id"),
        })
    return {"id": f"chain:{record_id}:{index:04d}", "branch": index, "length": len(entries), "suspension": suspension,
            "extraction_method": EXTRACTION_METHOD, "mentions": mentions}


def plan(text: str, reading: dict, base: dict, comparison: dict, record_id: str, source_work_id: str) -> dict:
    """The chain and mention rows this reading becomes, ids in the projection's scheme (see AGENTS.md §rows)."""
    reader = _reader_routes(reading)
    stored_by_id = {m["id"]: m for branch in base["chains"] for m in branch["mentions"]}
    neighbours = stored_neighbours_of(base)
    relies_elsewhere = _ends_with_back_reference(reading)
    chains = []
    for index, route in enumerate(reader):
        kept = comparison["kept_mention_ids"][index]
        entries = [{"surface_ar": stored_by_id[kept[p]]["surface_ar"] if kept[p] else _strip_arabic_marks(text[link["start"]:link["end"]]),
                    "reader_kind": link["kind"], "link_kind_if_new": LINK_KIND_FOR_READER_KIND[link["kind"]],
                    "span": [link["start"], link["end"]], "kept_mention_id": kept[p]} for p, link in enumerate(route)]
        suspension = "back_reference" if route[0]["kind"] == "back_reference" or index in relies_elsewhere else None
        chains.append(chain_rows(index, entries, suspension, record_id, source_work_id, neighbours))
    return {"chains": chains}


def mark_named_in_text(planned: dict, expanded: dict) -> None:
    """A planned mention that is an Imam named in the text (`imam_in_text`) keeps that kind, so the page can label it."""
    spans = {(link["start"], link["end"]) for route in expanded["routes"] for link in route["links"]
             if link["kind"] == "imam_in_text" and link["start"] is not None}
    for chain in planned["chains"]:
        for mention in chain["mentions"]:
            if mention["span"] and tuple(mention["span"]) in spans:
                mention["reader_kind"] = "imam_in_text"


def resolve_inherited(links: list[dict], previous: dict | None) -> tuple[list[dict] | None, dict | None]:
    """The cited report's written mentions these inherited links repeat, in order (the root of each), or (None, hold).

    Held, never guessed: no previous report given; its chain not rule-checked or verified (an uncertain chain lends no names);
    a name not found, in order, in one of its branches (comparison key equality, the same fold as the comparison)."""
    if not previous:
        return None, {"code": "inherited_previous_report_unknown",
                      "detail": "the reading takes names from an earlier report the submission could not identify in the archive"}
    statuses = sorted({chain.get("structure_status") or "none" for chain in previous["chains"]})
    if not previous["chains"] or any(status not in INHERITABLE_STATUSES for status in statuses):
        return None, {"code": "inherited_source_chain_uncertain",
                      "detail": f"the earlier report {previous['hadith_id']} has a chain no tested rule or person stands behind ({', '.join(statuses) or 'no chain'}); its names are not repeated"}
    wanted = [comparison_key(link["surface"]) for link in links]
    for branch in sorted(previous["chains"], key=lambda chain: chain["branch"]):
        keys = [comparison_key(mention["surface_ar"]) for mention in branch["mentions"]]
        pairs = _lcs_pairs(wanted, keys)
        if len(pairs) == len(wanted):
            return [{"id": branch["mentions"][j].get("inherited_from_mention_id") or branch["mentions"][j]["id"],
                     "surface_ar": branch["mentions"][j]["surface_ar"]} for _, j in pairs], None
    return None, {"code": "inherited_name_not_in_source_chain",
                  "detail": f"a name the reading takes from {previous['hadith_id']} is not, in that order, in one of its chains"}


def plan_inherited(planned: dict, expanded: dict, previous: dict, base: dict, record_id: str,
                   source_work_id: str) -> tuple[dict | None, list[dict]]:
    """Planned rows with inherited names spliced in at their places (AGENTS.md §inherited links), or (None, holds).

    Each expanded route with an inherited link: its written links keep their planned entries (matched by span), its inherited
    links become mentions repeating the cited written mention (its surface, `inherited_from_mention_id` its root). Routes are
    renumbered in order: routes that start inherited first (their chain precedes the text), then by first written offset."""
    written_by_span = {tuple(m["span"]): m for chain in planned["chains"] for m in chain["mentions"] if m["span"]}
    neighbours = stored_neighbours_of(base)
    holds: list[dict] = []
    rebuilt: list[tuple[tuple, list[dict], str | None]] = []
    used_spans: set[tuple] = set()
    for route in expanded["routes"]:
        links = [link for link in route["links"] if link["kind"] != "compiler_head" and not is_isnad_phrase(link)]
        if not any(link["kind"] == "inherited" for link in links):
            continue
        groups: dict[str, list[dict]] = {}
        for link in links:
            if link["kind"] == "inherited":
                groups.setdefault(link.get("from") or "", []).append(link)
        roots: dict[int, dict] = {}
        for ref, group in groups.items():
            found, hold = resolve_inherited(group, previous.get(ref))
            if hold:
                holds.append(hold)
                continue
            roots.update({id(link): root for link, root in zip(group, found)})
        if holds:
            continue
        entries = []
        for link in links:
            if link["kind"] == "inherited":
                root = roots[id(link)]
                entries.append({"surface_ar": root["surface_ar"], "reader_kind": "inherited", "link_kind_if_new": "unclassified",
                                "span": None, "kept_mention_id": None, "inherited_from_mention_id": root["id"]})
            else:
                mention = written_by_span[(link["start"], link["end"])]
                used_spans.add((link["start"], link["end"]))
                entries.append({key: mention[key] for key in ("surface_ar", "reader_kind", "link_kind_if_new", "span", "kept_mention_id")})
        first_written = min((entry["span"][0] for entry in entries if entry["span"]), default=-1)
        starts_inherited = entries[0]["span"] is None
        rebuilt.append(((0 if starts_inherited else 1, first_written), entries, None))
    if holds:
        return None, holds
    for chain in planned["chains"]:
        spans = [tuple(m["span"]) for m in chain["mentions"]]
        if any(span in used_spans for span in spans):
            continue
        entries = [{key: m[key] for key in ("surface_ar", "reader_kind", "link_kind_if_new", "span", "kept_mention_id")} for m in chain["mentions"]]
        rebuilt.append(((1, chain["mentions"][0]["span"][0]), entries, chain["suspension"]))
    rebuilt.sort(key=lambda item: item[0])
    return {"chains": [chain_rows(index, entries, suspension, record_id, source_work_id, neighbours)
                       for index, (_, entries, suspension) in enumerate(rebuilt)]}, []


# Marks a quote may differ in (letters stay exact): harakat, superscript alef, tatweel, Qur'anic annotation marks (AGENTS.md §quotes).
IGNORED_QUOTE_MARKS = re.compile("[ً-ْٰـۖ-ۭ]")


def locate_quotes(text: str, quote: str) -> list[tuple[int, int]]:
    """Every place a quote stands in the text, letters exact, the ignored marks aside on both sides; spans are in the text's own characters."""
    if not quote:
        return []
    kept = [index for index, char in enumerate(text) if not IGNORED_QUOTE_MARKS.match(char)]
    bare = "".join(text[index] for index in kept)
    needle = IGNORED_QUOTE_MARKS.sub("", quote)
    if not needle:
        return []
    spans, start = [], bare.find(needle)
    while start >= 0:
        end = kept[start + len(needle) - 1] + 1
        while end < len(text) and IGNORED_QUOTE_MARKS.match(text[end]):      # the last letter's own marks belong to the quote
            end += 1
        spans.append((kept[start], end))
        start = bare.find(needle, start + 1)
    return spans


def text_quotes(text: str, quotes: list[str]) -> list[str]:
    """Each quote as the text writes it (its own marks), for storing; a quote that does not stand in the text is kept as given."""
    out = []
    for quote in quotes:
        spans = locate_quotes(text, quote)
        out.append(text[spans[0][0]:spans[0][1]] if spans else quote)
    return out


def evidence_problems(text: str, quotes: list[str], comparison: dict, require_coverage: bool) -> list[str]:
    """Every quote must stand in the text (letters exact; vowel marks, tatweel and Qur'anic marks ignored); a reader who saw the stored chain must also quote around every change."""
    problems = [f"evidence: quote {index} is not in the text (letters must be exact): {quote!r}"
                for index, quote in enumerate(quotes) if not locate_quotes(text, quote)]
    if not quotes:
        problems.append("evidence: give at least one quote copied exactly from the text")
    if problems or not require_coverage:
        return problems
    spans = [span for q in quotes for span in locate_quotes(text, q)]
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


def variant_remarks_union(expanded_a: dict, expanded_b: dict | None) -> list[dict]:
    """The variant remarks of the two passes as one list, each marked with the pass(es) that wrote it (`passes`: a, b).

    A remark is about another version of the saying («بمثل حديث X»): never a route, never part of agreement. The two passes may
    differ on remarks without disagreeing; the stored remark is the union, a remark both wrote kept once (pass A's span)."""
    merged: dict[tuple, dict] = {}
    for tag, expanded in (("a", expanded_a), ("b", expanded_b)):
        for remark in (expanded or {}).get("variant_remarks") or []:
            key = tuple(sorted(link_key_v3_2(name) for level in remark["surfaces"] for name in level))
            entry = merged.setdefault(key, {"surfaces": remark["surfaces"], "quote": remark["quote"], "start": remark["start"],
                                            "end": remark["end"], "passes": []})
            entry["passes"].append(tag)
    return sorted(merged.values(), key=lambda entry: (entry["start"], entry["end"]))


def compiler_links_for(planned: dict, text: str, source_work_id: str) -> None:
    """Mark each later planned route with the compiler's own direct/indirect from ITS opening words (pg_export/work_register.py
    `route_links`, the rule the projection uses); the first chain keeps the report's mark, so no key is written for it."""
    from work_register import WorkRegister  # noqa: E402  (pg_export; imported late: only a work with a compiler needs it)
    global _REGISTER
    if _REGISTER is None:
        _REGISTER = WorkRegister()
    for chain, mark in zip(planned["chains"], _REGISTER.route_links(source_work_id, text, planned["chains"])):
        if mark is not None:
            chain["compiler_link"] = mark


_REGISTER = None


def label_sayings(planned: dict, expanded: dict) -> None:
    """Tool v3.4: each planned chain carries the saying its route belongs to (by the spans of its written links), and the fix carries the
    sayings with their page label and opening words (`planned.sayings`), computed from the reading, never taken from the envelope."""
    saying_of_span = {(link["start"], link["end"]): route.get("saying") for route in expanded["routes"] for link in route["links"]
                      if link["start"] is not None and route.get("saying") is not None}
    for chain in planned["chains"]:
        numbers = sorted({saying_of_span[tuple(m["span"])] for m in chain["mentions"] if m["span"] and tuple(m["span"]) in saying_of_span})
        if numbers:
            chain["saying"] = numbers[0]
    planned["sayings"] = [{"saying": s["saying"], "label": s["label"], "opens": s["opens"], "start": s["start"], "end": s["end"]} for s in expanded["sayings"]]


def route_marks(item: dict) -> dict:
    """Repair mode (`mode: route_links`): the compiler mark each planned chain of an applied fix should carry, by the projection's rule."""
    planned = {"chains": [{key: value for key, value in chain.items() if key != "compiler_link"} for chain in item["planned"]["chains"]]}
    compiler_links_for(planned, item["text"], item["source_work_id"])
    return {"key": item["key"], "marks": [chain.get("compiler_link") for chain in planned["chains"]]}


def run_item(item: dict) -> dict:
    if item.get("mode") == "route_links":
        return route_marks(item)
    result = {"key": item["key"], "errors": [], "reading": None, "offsets_repaired": False, "comparison": None, "planned": None,
              "computed_evidence": [], "holds": [], "proposals": [], "needs_ruling": False, "derived_links": [], "disposition": None, "variant_remarks": []}
    output, context = item["output"], item.get("context") or {}
    stored = [m["surface_ar"] for c in item["base"]["chains"] for m in c["mentions"]]
    if item.get("reader_format") == "text":
        errors = validate_text_v2(output, item["text"], item["expected_id"], context)
        if errors:
            result["errors"] = errors
        else:
            result["proposals"] = proposals_of(output, "text")
        return result
    expanded_v3 = None
    if item.get("reader_format") in V3_SHAPED:
        # The reader's own v3-shaped output (`reader_output_v3`), validated, expanded and held by the tool `tool_version` names
        # (v3 or v3_1; a v3.1 reading only by the v3.1 tool) against the packet's text and context; derived links are checked
        # there (an inherited name against the previous report's text, the compiler head against the work profile).
        tool = item.get("tool_version") or item["reader_format"]
        if tool not in TOOLS_FOR_FORMAT[item["reader_format"]]:
            result["errors"] = [f"tool_version: {tool!r} cannot read a {item['reader_format']} reading (tools for it: {', '.join(TOOLS_FOR_FORMAT[item['reader_format']])})"]
            return result
        validate_tool, expand_tool, holds_tool = TOOLS[tool]
        errors = validate_tool(output, item["text"], item["expected_id"], context)
        if errors:
            result["errors"] = errors
            return result
        expanded, errors = expand_tool(output, item["text"], context) if output["status"] == "read" else (None, [])
        result["holds"] = holds_tool(expanded, output, item["text"], context, stored, item.get("other_output"))
        result["proposals"] = proposals_of(output, "chain")
        result["needs_ruling"] = bool(output.get("needs_ruling"))
        if expanded is None:
            result["errors"] = errors or ["status: the reader could not read this report without the previous report's chain; nothing to apply"]
            return result
        result["derived_links"] = derived_links(expanded)
        # v3.2: a variant group is a remark about another version, kept with the fix and never a route; the v3.2 holds keep such a
        # reading back (has_variant_group) until the page shows the remark.
        other_expanded = None
        if tool in VARIANT_TOOLS and isinstance(item.get("other_output"), dict) and item["other_output"].get("status") == "read":
            # The second pass: it must be a valid reading of the same text whose ROUTES agree with the first's (variant remarks
            # may differ); only its remarks are used here (the agreement itself was found by the triage and is re-checked).
            other_errors = validate_tool(item["other_output"], item["text"], item["expected_id"], item.get("context") or {})
            other_expanded, other_expand_errors = (None, []) if other_errors else expand_tool(item["other_output"], item["text"], item.get("context") or {})
            if other_errors or other_expanded is None:
                result["errors"] = ["second reading: not a valid reading of this text: " + "; ".join((other_errors or other_expand_errors)[:2])]
                return result
            if not AGREE[tool](expanded, other_expanded):
                result["errors"] = ["second reading: its routes differ from the first's; agreement is on the routes (variant remarks may differ)"]
                return result
        result["variant_remarks"] = variant_remarks_union(expanded, other_expanded) if tool in VARIANT_TOOLS else (expanded.get("variant_remarks") or [])
        if tool in VARIANT_TOOLS and item.get("variant_notes_supported"):
            # The pipeline carries a variant remark (planned.variant_remarks, shown on the page): the reading is no longer held for having one.
            result["holds"] = [hold for hold in result["holds"] if hold["code"] != "has_variant_group"]
        if tool == "v3_4" and item.get("sayings_supported"):
            # The pipeline stores each route's saying (planned.chains[].saying, planned.sayings) and the page labels it (AGENTS.md §sayings).
            result["holds"] = [hold for hold in result["holds"] if hold["code"] != "two_sayings_not_supported"]
        if any(route.get("variant") for route in expanded["routes"]):
            # A variant group is a remark that another version names another transmitter («بمثل حديث X»), never a route: until it is
            # kept as a labelled remark, the whole reading waits (AGENTS.md §reader formats, tranche-01 judge 2026-11-22).
            result["holds"].append({"code": "has_variant_group",
                                    "detail": "the reading marks a variant route (another version's transmitter); it would be written as a chain"})
        # "This report has no isnad": an agreed reading with no route (v3_1/AGENTS.md §empty readings); the stored chain retires.
        result["disposition"] = NO_CHAIN_DISPOSITION if not expanded["routes"] else None
        expanded_v3 = expanded
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
    if item.get("reader_format") not in ("v2", *V3_SHAPED):
        result["holds"] = compute_holds(reading, {}, item["text"], None, stored)
    planned = plan(item["text"], reading, item["base"], comparison, item["record_id"], item["source_work_id"])
    if expanded_v3 is not None:
        mark_named_in_text(planned, expanded_v3)
        if any(link["kind"] == "inherited" for link in result["derived_links"]):
            # Inherited names become rows that repeat the cited report's written mentions (AGENTS.md §inherited links), or hold.
            spliced, holds = plan_inherited(planned, expanded_v3, item.get("previous") or {}, item["base"], item["record_id"],
                                            item["source_work_id"])
            result["holds"] += holds
            planned = spliced or planned
    compiler_links_for(planned, item["text"], item["source_work_id"])
    if expanded_v3 is not None and expanded_v3.get("sayings"):
        label_sayings(planned, expanded_v3)
    if result["variant_remarks"]:
        planned["variant_remarks"] = result["variant_remarks"]       # kept with the fix, never a route (AGENTS.md §variant remarks)
    result["evidence_quotes"] = text_quotes(item["text"], item.get("evidence", []))      # stored in the text's own characters
    result.update(reading=reading, offsets_repaired=repaired, comparison=comparison,
                  computed_evidence=computed_evidence(item["text"], comparison), planned=planned)
    return result


def main() -> int:
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    response = {"results": [run_item(item) for item in request["items"]]}
    sys.stdout.buffer.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
