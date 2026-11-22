"""Machine English overlay for the projection: which hash-bound, screened machine translations become `translations` rows."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

# Source-provided English that always wins over a machine draft (owner, 2026-11-22: source first, machine only where none).
SOURCE_ENGLISH_STATES = frozenset({"human_verified", "source_verified", "source_provided"})
ARABIC_SCRIPT = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
HONORIFIC_SYMBOLS = re.compile(r"[ﷺﷻ﷽ؐ-ؓ]")
ARABIC_LETTER = re.compile(r"[ء-يٱ-ە]")
LATIN_LETTER = re.compile(r"[A-Za-zÀ-ɏ]")
# Same bounds as screen-v2 (generate_hy_mt2_candidates.py); re-applied here so nothing unscreened can be shown.
MIN_LATIN_TO_ARABIC = 1.0
MAX_LATIN_TO_ARABIC = 3.2
RATIO_MIN_ARABIC_LETTERS = 40
MIN_LATIN_SHARE = 0.8
REFUSAL_OR_META = re.compile(
    r"as an ai\b|language model|\bi (?:cannot|can't|am unable to) (?:translate|assist|help|comply)|\bi'm sorry,? but\b|"
    r"cannot fulfill|^\s*(?:(?:sure|certainly)[,!]|here(?: is|'s) (?:the|your|an?) (?:english )?translation)|^\s*(?:translation|english)\s*:|\bTODO\b|\bPLACEHOLDER\b|"
    r"reference the following translations|translates to\b.*\btranslates to\b",
    re.IGNORECASE,
)
PROVENANCE_DIRECTORY = "machine_translation_candidates"


def read_overlay(path: Path) -> list[dict]:
    """Candidate rows (one JSON object per line), as written by translate_gap_fill.py finalize."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def gate(candidate: dict, text_ar: str, arabic_sha256: str, pinned_model: str) -> list[str]:
    """Why a machine draft must not be shown: empty when it may be. Every check is a published-English invariant."""
    reasons = []
    if candidate.get("arabic_sha256") != arabic_sha256:
        reasons.append("stale_arabic_hash")
    qa = candidate.get("qa") or {}
    if qa.get("status") != "accepted_machine_unreviewed" or qa.get("errors"):
        reasons.append("not_accepted_by_screen")
    if candidate.get("translation_model") != pinned_model or candidate.get("response_model", pinned_model) != pinned_model:
        reasons.append("model_not_pinned")
    if not (candidate.get("translation_source") or "").strip():
        reasons.append("source_not_recorded")
    if not (candidate.get("prompt_version") or "").strip():
        reasons.append("prompt_not_recorded")
    if any(reason != "stop" for reason in candidate.get("finish_reasons", ["stop"])):
        reasons.append("truncated")
    text = (candidate.get("text_en") or "").strip()
    if not text:
        reasons.append("empty")
        return reasons
    if ARABIC_SCRIPT.search(HONORIFIC_SYMBOLS.sub("", text)):
        reasons.append("arabic_leakage")
    latin, arabic = len(LATIN_LETTER.findall(text)), len(ARABIC_LETTER.findall(text_ar))
    letters = latin + len(ARABIC_LETTER.findall(text))
    if letters and latin / letters < MIN_LATIN_SHARE:
        reasons.append("mostly_not_latin")
    if arabic >= RATIO_MIN_ARABIC_LETTERS and not MIN_LATIN_TO_ARABIC <= latin / arabic <= MAX_LATIN_TO_ARABIC:
        reasons.append("length_ratio_out_of_bounds")
    if REFUSAL_OR_META.search(text):
        reasons.append("refusal_or_meta_text")
    return reasons


def provenance(candidate: dict) -> str:
    """One text field naming journal, prompt (version and hash), provider and time, so a row can be traced to its call."""
    prompt_hash = (candidate.get("prompt_sha256") or "unrecorded")[:12]
    return (f"{PROVENANCE_DIRECTORY}/{candidate.get('origin_journal') or 'unrecorded'}"
            f"|prompt={candidate['prompt_version']}|prompt_sha256={prompt_hash}"
            f"|provider={candidate.get('response_provider') or 'unrecorded'}|at={candidate.get('created_at') or 'unrecorded'}")


def translation_row(candidate: dict, hadith_id: str, record_id: str, source_record_id: str | None, existing_id: str | None) -> list:
    """A `translations` row (column order of export_postgres.py). An existing failing row keeps its id: replaced, not added."""
    return [
        existing_id or f"translation:{record_id}:en", hadith_id, "en", candidate["text_en"].strip(), None, "machine_unreviewed",
        "complete", "machine_unreviewed", candidate["translation_source"], candidate.get("response_model") or candidate["translation_model"],
        None, provenance(candidate), source_record_id, candidate["arabic_sha256"],
    ]


def overlay_translations(translations: list[list], hadith_info: dict[str, dict], hadith_text: dict[str, str],
                         record_to_hadith: dict[str, str], candidates: list[dict], pinned_model: str) -> tuple[list[list], dict]:
    """Fill reports that have no usable source English with their gated machine draft; return the rows and a count report.

    translations: rows already built from the bundle (id at 0, hadith_id at 1, state at 5, quality at 6).
    A report with complete source-provided or reviewed English keeps it (one row per hadith and language: source first).
    """
    by_hadith = {row[1]: index for index, row in enumerate(translations)}
    out = list(translations)
    counts: dict[str, int] = {"candidates": len(candidates), "used": 0, "replaced_failing_row": 0, "kept_source_english": 0, "unknown_report": 0}
    held_out: dict[str, int] = {}
    seen: set[str] = set()
    for candidate in sorted(candidates, key=lambda c: c["record_id"]):
        hadith_id = record_to_hadith.get(candidate["record_id"])
        if hadith_id is None:
            counts["unknown_report"] += 1
            continue
        if hadith_id in seen:
            raise ValueError(f"{candidate['record_id']}: two machine drafts for one report")
        seen.add(hadith_id)
        index = by_hadith.get(hadith_id)
        if index is not None and out[index][6] == "complete" and out[index][5] in SOURCE_ENGLISH_STATES:
            counts["kept_source_english"] += 1
            continue
        info = hadith_info[hadith_id]
        reasons = gate(candidate, hadith_text[hadith_id], info["arabic_sha256"], pinned_model)
        if reasons:
            for reason in reasons:
                held_out[reason] = held_out.get(reason, 0) + 1
            held_out["any"] = held_out.get("any", 0) + 1
            continue
        row = translation_row(candidate, hadith_id, candidate["record_id"], info.get("source_record_id"),
                              out[index][0] if index is not None else None)
        if index is None:
            by_hadith[hadith_id] = len(out)
            out.append(row)
        else:
            out[index] = row
            counts["replaced_failing_row"] += 1
        counts["used"] += 1
    counts["held_out_by_reason"] = dict(sorted(held_out.items()))
    return out, counts
