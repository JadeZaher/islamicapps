"""The AI reviewer's vocabulary and the pipeline's decision rule, in one place (reviewer/README.md §decision rule; the builder, the validator and the tests read it)."""

from __future__ import annotations

DECISIONS = ("confirm_reading", "confirm_with_correction", "prefer_reader_a", "prefer_reader_b", "keep_stored", "no_chain", "refer_to_human")
VARIANT_VERDICTS = ("remark_about_another_version", "route_of_this_saying")
UNCERTAINTY = ("low", "medium", "high")
REVIEWER_MODEL = "claude-opus-5-5"
OUTPUT_FORMAT = "shura-chain-review-output/1"
PACKET_FORMAT = "shura-chain-review-packet/1"
JOBS_FORMAT = "shura-chain-review-jobs/1"
SPECIALIST = "chain-reviewer"

# Every hold code (v3 to v3.4) and the reviewer-visible reasons that are not holds, in plain words; `clearable` is the owner's rule (2026-11-22):
# the reviewer may clear shape holds, variant holds, single-reader flags and disagreements between readers; never an unruled owner question, a missing previous report or stale text.
HOLDS: dict[str, tuple[str, bool]] = {
    # shape holds: the routes look wrong against each other
    "route_at_most_half_the_longest": ("one route is at most half as long as the longest and ends elsewhere: a shared head or tail may have been dropped", True),
    "routes_end_at_different_links": ("the routes end at different men (v3.2's broad shape hold)", True),
    "route_ends_inside_another_route": ("a route stops at a man who stands inside another route: the shared tail may have been dropped from it", True),
    "first_links_split_by_comma": ("two routes differ only in a first name, and the two names stand side by side with a comma: perhaps one man (kunya and name) read as two", True),
    "semicolon_in_multi_route_isnad": ("«؛» inside the isnad of a reading with several routes: names grouped after it often lose their shared tail", True),
    "nested_jami": ("«جميعا / كلهم» more than once, or with «؛»: nested convergence, often misread", True),
    "nested_semicolon": ("two or more «؛» in the chain: several isnads joined", True),
    "too_many_routes": ("more than 8 routes after expansion", True),
    "saying_route_starts_inside_another_route": ("a later saying's route starts at a man inside an earlier saying's chain: its shared head may have been dropped", True),
    "saying_openings_differ": ("the two readers open a saying at different places in the text", True),
    "back_reference_only": ("the reading is only back references, or the text opens with one, a previous report was supplied, and no inherited name was taken", True),
    "asker_not_a_link": ("the report opens with an asker («سأل / كتب / شكا X») and no route has him as a link (ruled: the asker is a link)", True),
    "empty_reading_transmission_name": ("the readers found no chain, but a transmission word and a name stand before the saying", True),
    "reading_empty_stored_has_links": ("the readers found no chain where the stored chain has names", True),
    "bracketed_insertion_differs": ("the readers agree only when a name in the editor's «[ ... ]» is left out, and they wrote it differently", True),
    # variant holds: a remark about another version
    "has_variant_group": ("a reader marked a remark about another version (variant): it is kept as a note, never stored as a route", True),
    "variant_only_reading": ("every group a reader wrote is a variant remark: nothing is left to store", True),
    "mutabaa_marker": ("the text says «تابعه ...» (a mutabaʿa) and the reading has several routes: the marked isnad should be a remark, not a route", True),
    "second_isnad_not_same_saying": ("a later isnad opens after the saying with a poem or story cue: perhaps not a route of this saying", True),
    # single-reader flags and disagreements (not holds of the tool, but why a report waits)
    "readers_differ": ("the two readers wrote different routes", True),
    "flag_one_reader": ("one reader marked a point the rules do not settle (needs_ruling); the other did not", True),
    # unruled owner questions: never cleared by the reviewer
    "needs_ruling": ("both readers marked a point the rules do not settle", False),
    "needs_ruling_faqih_route_statement": ("al-Faqih's statement of the compiler's routes («طرق») to a source, with no saying: unruled", False),
    "needs_ruling_prophet_no_transmitter": ("the Prophet speaks a one-sentence report with no transmitter: unruled", False),
    "imami_single_narrator_without_source": ("the whole reading is one narrator with no Imam or source (a first-person «سألته» / «أنه قال» with the speaker unnamed): unruled", False),
    "empty_reading_unsettled_opening": ("an implicit-speaker opening («وقال عليه السلام», «و سئل») read as no chain, with nothing to name the speaker", False),
    # a missing or doubtful previous report: never cleared by the reviewer
    "back_reference_without_previous_report": ("the report leans on an earlier report, and no earlier report that writes its chain was supplied", False),
    "cannot_read_without_previous_report": ("the reader could not read the report without the previous report's chain", False),
    "inherited_from_far_report": ("an inherited name comes from a report more than 3 back, with other chains in between", False),
    # pipeline states: never cleared by the reviewer
    "two_sayings_not_supported": ("the reading stores two sayings and the pipeline cannot yet label routes by saying", False),
    "one_reader_invalid": ("only one reader's output is valid", False),
    "stale_text": ("the report's text changed after it was read", False),
}


def plain(code: str) -> str:
    return HOLDS.get(code, (f"tool hold «{code}»", False))[0]


def clearable(code: str) -> bool:
    """Unknown codes are not clearable."""
    return HOLDS.get(code, ("", False))[1]


def outcome(status: str, decision: str, codes: list[str], readers_agree: bool, agreed_empty: bool, second_run_agrees: bool | None) -> str:
    """What the pipeline does with one reviewer decision (reviewer/README.md §decision rule). `second_run_agrees` is None when no second run exists.
    Returns one of: apply_reading, apply_reader_a, apply_reader_b, apply_correction, apply_no_chain, keep_held, queue_for_human, discard_reading, label_ai_reviewed, revert_to_stored."""
    blocked = [c for c in codes if not clearable(c)]
    if status == "held":
        if decision == "refer_to_human" or blocked:
            return "keep_held"
        if decision == "confirm_reading":
            return "apply_reading" if readers_agree else "queue_for_human"
        if decision in ("prefer_reader_a", "prefer_reader_b"):
            return ("apply_" + decision[len("prefer_"):]) if not readers_agree else "queue_for_human"
        if decision == "no_chain" and readers_agree and agreed_empty:
            return "apply_reading"
        if decision in ("confirm_with_correction", "no_chain"):
            return ("apply_correction" if decision == "confirm_with_correction" else "apply_no_chain") if second_run_agrees else "queue_for_human"
        if decision == "keep_stored":
            return "discard_reading"
        raise ValueError(decision)
    if status == "applied":
        if decision == "confirm_reading" or (decision == "no_chain" and agreed_empty):
            return "label_ai_reviewed"
        if decision in ("confirm_with_correction", "no_chain") and second_run_agrees:
            return "apply_correction" if decision == "confirm_with_correction" else "apply_no_chain"
        return "revert_to_stored"
    raise ValueError(status)
