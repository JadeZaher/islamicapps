"""Projection replay of accepted chain fixes (see AGENTS.md §replay). Imported by pg_export at integration; pure otherwise.

`accepted_overrides.jsonl.gz` holds one row per report whose chain the projection must take from an accepted fix. Each row
is bound to the report's `arabic_sha256` and to the SHA-256 of the exact text the readers read; a row whose binding no
longer holds is dropped, counted, and stays queued in the store (the fix is re-read, never silently re-applied).
`rewrite_rows` turns the rule-built rows of a report into the fix's rows by the database apply's own rule
(`src/db/ops/chain-fix-apply.ts` `writeRoutes`), so a load after an apply changes nothing (AGENTS.md §replay).
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

OVERRIDES_FORMAT = "shura-chain-fix-override/1"
DEFAULT_PATH = Path(__file__).resolve().parent / "accepted_overrides.jsonl.gz"
EFFECTS = ("replace_routes", "set_status", "annotate")
DISPOSITIONS = (None, "no_chain_by_reading")
CHAIN_COLUMNS = ("id", "hadith_id", "branch", "length", "resolved", "extraction_method", "confidence", "sanad_confidence",
                 "suspension", "missing_link_after", "structure_status", "structure_reasons", "chain_fix_id",
                 "compiler_narrator_id", "compiler_link")
MENTION_COLUMNS = ("id", "chain_id", "hadith_id", "position", "surface_ar", "surface_normalized", "teacher_context_normalized",
                   "student_context_normalized", "review_unit_id", "review_unit_fine_id", "link_kind", "resolution",
                   "resolution_basis", "narrator_id", "confidence", "extraction_method", "name_latin", "name_latin_basis",
                   "name_latin_narrator_id", "identity_withheld_reason", "inherited_from_mention_id")
# Carried from a kept name only with its identity (chain-fix-apply.ts DERIVED_MENTION_COLUMNS; decision_id is loader-derived).
IDENTITY_COLUMNS = ("link_kind", "resolution", "resolution_basis", "narrator_id", "confidence", "extraction_method",
                    "identity_withheld_reason")
LATIN_COLUMNS = ("name_latin", "name_latin_basis", "name_latin_narrator_id")
STATUSES = ("read_by_model", "verified_by_reviewer")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def reader_text(layout: str, text_ar: str, sanad: str | None) -> str:
    """The exact string the readers read (chain-reader/tools/build_pilot.py `reader_text`)."""
    if layout == "chain_field_then_matn" and (sanad or "").strip():
        return f"{sanad.strip()}\n\n{text_ar}"
    return text_ar


def load_overrides(path: Path = DEFAULT_PATH) -> dict[str, dict]:
    """hadith id -> override row; an absent file means no fixes. Refuses a malformed or duplicated row."""
    if not path.is_file():
        return {}
    rows: dict[str, dict] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if (row.get("format") != OVERRIDES_FORMAT or row.get("effect") not in EFFECTS
                    or row.get("structure_status") not in STATUSES + (None,) or row.get("disposition") not in DISPOSITIONS):
                raise ValueError(f"{path}:{number}: not a {OVERRIDES_FORMAT} row")
            if row["hadith_id"] in rows:
                raise ValueError(f"{path}:{number}: second override for {row['hadith_id']}")
            rows[row["hadith_id"]] = row
    return rows


def binding_problem(row: dict, text_ar: str, arabic_sha256: str, sanad: str | None) -> str | None:
    """Why an override no longer applies to the loaded report, or None."""
    if row["arabic_sha256"] != arabic_sha256 or sha256_text(text_ar) != arabic_sha256:
        return "arabic_changed"
    if sha256_text(reader_text(row["text_layout"], text_ar, sanad)) != row["reader_text_sha256"]:
        return "reader_text_changed"
    return None


def candidate_id(mention_id: str, basis: str, narrator_id: str) -> str:
    """The projection's candidate id (export_postgres.py `candidate_id`; chain-fix-apply.ts `candidateId`)."""
    return f"candidate:{mention_id.removeprefix('mention:')}:{basis}:{narrator_id.removeprefix('narrator:')}"


def variant_remarks_of(row: dict) -> list[dict]:
    """The variant remarks an override carries (any effect): remarks about another version, never a route, mention or pair."""
    return list(row.get("variant_remarks") or [])


def rewrite_rows(row: dict, old_chains: list[list], old_mentions: list[list], old_candidates: list[list],
                 written: dict[str, tuple[list, list[list]]], verbatim, counts: Counter,
                 route_links: list[str | None] | None = None) -> tuple[list[list], list[list], list[list]]:
    """The chain, mention and candidate rows of one `replace_routes` override, from the report's rule-built rows (CSV order).

    The database apply's rule, column for column: a kept name keeps every candidate; it keeps its identity and Latin form only
    when carried (both neighbours unchanged); else unresolved, and a Latin form survives unless it came from the identity. An
    inherited name repeats its cited written mention: surface, candidates and a Latin form not taken from an identity. A chain
    takes the report's first rule-built chain's sanad confidence and compiler (indirect when the route relies elsewhere); a
    later route's direct/indirect mark is its own (`route_links`, from its opening words: work_register.py `route_links`; a
    planned `compiler_link` wins), the first chain keeps the report's.
    `written` maps a mention id to (its row, its candidate rows) across the projection, for inherited names."""
    chain_at = {name: index for index, name in enumerate(CHAIN_COLUMNS)}
    mention_at = {name: index for index, name in enumerate(MENTION_COLUMNS)}
    first = min(old_chains, key=lambda chain: chain[chain_at["branch"]]) if old_chains else None
    old_by_id = {mention[0]: mention for mention in old_mentions}
    candidates_of: dict[str, list[list]] = {}
    for candidate in old_candidates:
        candidates_of.setdefault(candidate[1], []).append(candidate)
    compiler = first[chain_at["compiler_narrator_id"]] if first else None

    def text_cell(value):
        return verbatim(value) if value is not None else None      # a computed '' stays '', never NULL

    chains, mentions, candidates = [], [], []
    for index, chain in enumerate(row["planned"]["chains"]):
        own = chain.get("compiler_link") or (route_links[index] if route_links else None)
        link = ("indirect" if chain["suspension"] else own or first[chain_at["compiler_link"]]) if compiler else None
        chains.append([chain["id"], row["hadith_id"], chain["branch"], chain["length"], False, chain["extraction_method"], None,
                       first[chain_at["sanad_confidence"]] if first else None, chain["suspension"], None,
                       row["structure_status"], None, row["fix_id"], compiler, link])
        for mention in chain["mentions"]:
            inherited = mention.get("inherited_from_mention_id")
            if inherited:
                source_row, source_candidates = written.get(inherited) or (None, [])
                if source_row is None:
                    raise ValueError(f"{row['fix_id']}: inherited mention {inherited} is not in the projection")
            else:
                source_row = old_by_id.get(mention["kept_mention_id"]) if mention["kept_mention_id"] else None
                source_candidates = candidates_of.get(mention["kept_mention_id"], []) if source_row is not None else []
            carry = bool(mention["carry_identity"]) and source_row is not None and not inherited
            if carry:
                identity = [source_row[mention_at[column]] for column in IDENTITY_COLUMNS]
                counts["mentions_kept_identity" if source_row[mention_at["narrator_id"]] else "mentions_kept_unresolved"] += 1
            else:
                identity = [mention["link_kind_if_new"], "unresolved", None, None, None, None, None]
                counts["mentions_inherited" if inherited else "mentions_kept_candidates_only" if source_row is not None
                       else "mentions_new"] += 1
            keep_latin = source_row is not None and (carry or source_row[mention_at["name_latin_basis"]] != "identity_name")
            latin = [source_row[mention_at[column]] for column in LATIN_COLUMNS] if keep_latin else [None, None, None]
            mentions.append([mention["id"], chain["id"], row["hadith_id"], mention["position"], mention["surface_ar"],
                             verbatim(mention["surface_normalized"]), text_cell(mention["teacher_context_normalized"]),
                             text_cell(mention["student_context_normalized"]), mention["review_unit_id"],
                             mention["review_unit_fine_id"], *identity[:6], *latin, identity[6], inherited])
            for candidate in source_candidates:
                candidates.append([candidate_id(mention["id"], candidate[4], candidate[3]), mention["id"], row["hadith_id"],
                                   *candidate[3:]])
    counts["reports_replaced"] += 1
    counts["reports_no_chain_by_reading"] += row.get("disposition") == "no_chain_by_reading"
    return chains, mentions, candidates
