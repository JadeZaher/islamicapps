"""
Unit tests for `extract_isnad_unified` — the canonical taḥwīl-aware isnad
extractor (Phase 1 of the uniform_isnad_extraction_20260609 conductor track).

Covers FR-1.3 cases (a)–(g) plus the FR-3.1 `_compute_chain_indx` API.
Fixtures: __tests__/fixtures/tahweel-gold.jsonl (5 hand-annotated rows).

The Jaccard threshold (>= 0.80) reflects the FR-0.5.4 acceptance bar from
the Phase 0.5 algorithmic bake-off, where candidate C scored median 0.845
across the same fixtures.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

# Resolve the extractor module location and make it importable.
_HERE = pathlib.Path(__file__).resolve().parent
_PARENT = _HERE.parent  # datasets/hadith-data/
sys.path.insert(0, str(_PARENT))

from extract_isnad_unified import (  # noqa: E402
    _UNIFIED_CHAIN_STATS,
    _compute_chain_indx,
    extract_isnad_branches,
    name_normalize,
    reset_stats,
    resolve_branches_to_indxs,
)

_GOLD = _PARENT / "__tests__" / "fixtures" / "tahweel-gold.jsonl"

# Bukhari-style single-chain illustrative text (annotation guide §3.1).
# 4 narrators ending at Companion ʿAbdullāh b. ʿUmar, then matn (أن رسول الله…).
BUKHARI_SINGLE_CHAIN = (
    "حدثنا عبد الله بن يوسف، قال: أخبرنا مالك، عن نافع، عن عبد الله بن عمر، "
    "أن رسول الله صلى الله عليه وسلم قال"
)


# --------------------------------------------------------------------------- #
# Fixtures + helpers
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _reset_stats_between_tests():
    """Telemetry must be deterministic per test."""
    reset_stats()
    yield
    reset_stats()


@pytest.fixture
def fixtures() -> dict[str, dict]:
    """Load all hand-annotated taḥwīl-gold rows, keyed by hadith_id."""
    rows: dict[str, dict] = {}
    with open(_GOLD, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rows[r["hadith_id"]] = r
    return rows


def _jaccard(a: list[str], b: list[str]) -> float:
    """Per-branch narrator-set Jaccard using `name_normalize` — mirrors the
    Phase 0.5 bake-off scoring.
    """
    sa = {name_normalize(x) for x in a if x}
    sb = {name_normalize(x) for x in b if x}
    union = sa | sb
    if not union:
        return 1.0
    return len(sa & sb) / len(union)


def _row_mean_jaccard(actual: list[list[str]], expected: list[list[str]]) -> float:
    """Pairwise mean Jaccard with best-match alignment (greedy on actual)."""
    if not actual or not expected:
        return 0.0
    scores: list[float] = []
    expected_pool = list(expected)
    for a in actual:
        if not expected_pool:
            scores.append(0.0)
            continue
        best_i, best_s = 0, -1.0
        for i, e in enumerate(expected_pool):
            s = _jaccard(a, e)
            if s > best_s:
                best_s = s
                best_i = i
        scores.append(best_s)
        expected_pool.pop(best_i)
    return sum(scores) / len(scores)


# --------------------------------------------------------------------------- #
# FR-1.3 (a) Empty input → [[]]
# --------------------------------------------------------------------------- #


def test_empty_input_returns_empty_branch():
    """FR-1.3 (f): empty / None `text_ar` returns `[[]]`, never raises."""
    assert extract_isnad_branches("") == [[]]
    assert extract_isnad_branches(None) == [[]]
    # Stats must NOT register rows_with_text for empties.
    assert _UNIFIED_CHAIN_STATS["rows_with_text"] == 0


# --------------------------------------------------------------------------- #
# FR-1.3 (c) Single-chain (no ح) → one branch, matn stripped
# --------------------------------------------------------------------------- #


def test_single_chain_no_tahweel():
    """FR-1.3 (c): Bukhari-style single chain with no taḥwīl. Matn must
    be stripped at `أن رسول الله…`.
    """
    branches = extract_isnad_branches(BUKHARI_SINGLE_CHAIN)
    assert len(branches) == 1
    chain = branches[0]
    # 4 transmitters: ʿAbdullāh b. Yūsuf → Mālik → Nāfiʿ → ʿAbdullāh b. ʿUmar.
    # The cleaner may emit some surface variation; assert the endpoints + count.
    assert len(chain) == 4, f"expected 4 narrators, got {len(chain)}: {chain}"
    assert "عبد الله بن يوسف" in chain[0]
    assert "مالك" in chain[1]
    assert "نافع" in chain[2]
    # The final narrator is the Companion; the matn (أن رسول الله…) must NOT
    # appear inside any surface form.
    assert "عبد الله بن عمر" in chain[-1] or "عبد الله بن عمر" == chain[-1]
    for surface in chain:
        assert "رسول الله" not in surface
        assert "أن " not in surface


# --------------------------------------------------------------------------- #
# FR-1.3 (a) Tirmidhi #1 — 2-branch convergence at Simāk
# --------------------------------------------------------------------------- #


def test_tirmidhi_1_two_branches_with_convergence(fixtures):
    """FR-1.3 (a): Tirmidhi #1, the canonical 2-branch taḥwīl. Branches
    must converge on the shared post-Simāk tail.

    Acceptance: row-mean Jaccard >= 0.80 against gold (FR-0.5.4 bar).
    """
    row = fixtures["30001"]
    branches = extract_isnad_branches(row["text_ar"])
    assert len(branches) == 2, f"expected 2 branches, got {len(branches)}"

    # Both branches must reach the same Companion (after surface normalization).
    assert name_normalize(branches[0][-1]) == name_normalize(branches[1][-1])
    # Shared post-convergence tail: Muṣʿab b. Saʿd → Ibn ʿUmar appears in both.
    for br in branches:
        norms = [name_normalize(x) for x in br]
        assert any("مصعب بن سعد" in n for n in norms), (
            f"missing مصعب بن سعد in branch: {br}"
        )
        assert any("ابن عمر" in n for n in norms), (
            f"missing ابن عمر in branch: {br}"
        )

    # Row-mean Jaccard against gold.
    mean_j = _row_mean_jaccard(branches, row["expected_branches"])
    assert mean_j >= 0.80, (
        f"Tirmidhi #1 row-mean Jaccard {mean_j:.3f} below FR-0.5.4 bar of 0.80. "
        f"Branches: {branches}"
    )


# --------------------------------------------------------------------------- #
# muslim-1 — parallel branches with NO shared narrators after divergence
# --------------------------------------------------------------------------- #


def test_muslim_1_parallel_no_convergence(fixtures):
    """muslim-1: same compiler-narrator opens both ح-branches but the
    post-divergence narrators do NOT overlap. The LCS-suffix algorithm
    must NOT collapse the branches into a single shared-suffix view
    (the failure mode of candidate B's set-intersect approach).

    Both endpoints are different Companions (سمرة, المغيرة) — verify the
    branches remain distinct.
    """
    row = fixtures["muslim-1"]
    branches = extract_isnad_branches(row["text_ar"])
    assert len(branches) == 2, f"expected 2 branches, got {len(branches)}"
    # Branches must NOT be identical.
    assert branches[0] != branches[1], (
        "muslim-1 branches collapsed — candidate B-style failure mode"
    )
    # Endpoints diverge to different Companions.
    last_a = name_normalize(branches[0][-1])
    last_b = name_normalize(branches[1][-1])
    assert last_a != last_b, (
        f"endpoints expected to diverge; got identical {last_a}"
    )
    # Specifically: one branch should end at سمرة, the other at المغيرة.
    endpoints = {last_a, last_b}
    has_samura = any("سمرة" in e for e in endpoints)
    has_mughira = any("المغيرة" in e for e in endpoints)
    assert has_samura and has_mughira, (
        f"expected سمرة and المغيرة endpoints; got {endpoints}"
    )


# --------------------------------------------------------------------------- #
# muslim-2 — co-transmitter at branch head
# --------------------------------------------------------------------------- #


def test_muslim_2_co_transmitter_at_branch_head(fixtures):
    """muslim-2: Branch B starts with TWO compiler-narrators
    (محمد بن المثنى AND ابن بشار) feeding into محمد بن جعفر. Both
    must appear in the branch after `_split_co_transmitters` runs.
    """
    row = fixtures["muslim-2"]
    branches = extract_isnad_branches(row["text_ar"])
    assert len(branches) == 2, f"expected 2 branches, got {len(branches)}"

    # Find the branch that contains either co-transmitter — that's Branch B.
    def _contains(branch: list[str], needle: str) -> bool:
        return any(needle in name_normalize(n) for n in branch)

    branch_b = None
    for br in branches:
        if _contains(br, "محمد بن المثنى") or _contains(br, "ابن بشار"):
            branch_b = br
            break
    assert branch_b is not None, (
        f"neither branch contains the muslim-2 co-transmitters: {branches}"
    )
    # BOTH co-transmitters must be present.
    assert _contains(branch_b, "محمد بن المثنى"), (
        f"missing محمد بن المثنى in Branch B: {branch_b}"
    )
    assert _contains(branch_b, "ابن بشار"), (
        f"missing ابن بشار in Branch B: {branch_b}"
    )


# --------------------------------------------------------------------------- #
# muslim-31 — surface forms preserved verbatim (NOT normalized to one)
# --------------------------------------------------------------------------- #


def test_muslim_31_surface_form_drift_preserved(fixtures):
    """muslim-31: Branch A's text contains the short surface `سفيان`
    while Branch B's text contains the full `سفيان بن عيينة`. The
    extractor must preserve whatever surface form appears in the text
    verbatim — NOT normalize them to a single canonical form.

    The downstream resolver handles surface-form unification.
    """
    row = fixtures["muslim-31"]
    branches = extract_isnad_branches(row["text_ar"])
    # At minimum, at least one branch must contain the bare `سفيان` surface
    # exactly as written in the source text (no expansion to `سفيان بن عيينة`).
    all_surfaces = [s for br in branches for s in br]
    has_bare_sufyan = any(s.strip() == "سفيان" for s in all_surfaces)
    assert has_bare_sufyan, (
        "expected the bare surface form 'سفيان' to be preserved verbatim "
        "(not expanded to 'سفيان بن عيينة'); got surfaces: "
        f"{all_surfaces}"
    )


# --------------------------------------------------------------------------- #
# muslim-102 — pronoun preserved (extractor must NOT resolve أبي → معاذ)
# --------------------------------------------------------------------------- #


def test_muslim_102_pronoun_preserved(fixtures):
    """muslim-102: Branch B contains the pronoun `أبي` ("my father") which
    references معاذ via the upstream عبيد الله بن معاذ. The extractor
    must emit `أبي` VERBATIM and leave parent-resolution to the resolver.
    """
    row = fixtures["muslim-102"]
    branches = extract_isnad_branches(row["text_ar"])
    all_surfaces = [s for br in branches for s in br]
    # Must contain `أبي` (the pronoun) — NOT silently expanded to معاذ.
    assert any(s.strip() == "أبي" for s in all_surfaces), (
        f"pronoun 'أبي' missing — extractor must not resolve. "
        f"Surfaces: {all_surfaces}"
    )


# --------------------------------------------------------------------------- #
# FR-1.3 (matn anchoring): no narrator surface should contain matn cues
# --------------------------------------------------------------------------- #


def test_matn_not_in_chain(fixtures):
    """FR-1.3 (g): Matn (post-`قال رسول الله…`) MUST NOT appear inside any
    narrator surface. Tirmidhi #1's matn is `قال … لا تقبل صلاة بغير طهور`
    — the chain must stop at Ibn ʿUmar.
    """
    row = fixtures["30001"]
    branches = extract_isnad_branches(row["text_ar"])
    matn_red_flags = ["قال رسول", "صلى الله", "لا تقبل", "صدقة من غلول"]
    for br in branches:
        for surface in br:
            for flag in matn_red_flags:
                assert flag not in surface, (
                    f"matn fragment '{flag}' leaked into narrator surface "
                    f"'{surface}' in branch {br}"
                )


# --------------------------------------------------------------------------- #
# Telemetry — stats dict updates correctly
# --------------------------------------------------------------------------- #


def test_stats_telemetry_updates(fixtures):
    """`_UNIFIED_CHAIN_STATS` must reflect rows processed, rows branched,
    and total branches emitted.
    """
    reset_stats()
    # 1 multi-branch row (Tirmidhi #1) + 1 single-chain row (Bukhari illustrative)
    extract_isnad_branches(fixtures["30001"]["text_ar"])
    extract_isnad_branches(BUKHARI_SINGLE_CHAIN)
    assert _UNIFIED_CHAIN_STATS["rows_with_text"] == 2, (
        f"expected 2 rows_with_text, got {_UNIFIED_CHAIN_STATS['rows_with_text']}"
    )
    assert _UNIFIED_CHAIN_STATS["rows_branched"] == 1, (
        f"expected 1 rows_branched (Tirmidhi only), "
        f"got {_UNIFIED_CHAIN_STATS['rows_branched']}"
    )
    # Tirmidhi=2 + Bukhari=1 = 3, at minimum.
    assert _UNIFIED_CHAIN_STATS["branches_total"] >= 3, (
        f"expected >=3 branches_total, got {_UNIFIED_CHAIN_STATS['branches_total']}"
    )


# --------------------------------------------------------------------------- #
# Resolver callback — called once per surface, None tolerated
# --------------------------------------------------------------------------- #


def test_resolver_callback_called(fixtures):
    """`resolve_branches_to_indxs` must call the resolver exactly once per
    surface form across all branches. Returning None for a name must NOT
    raise; the name is silently skipped.
    """
    branches = extract_isnad_branches(fixtures["30001"]["text_ar"])
    expected_surfaces = [s for br in branches for s in br]
    calls: list[str] = []

    def mock_resolver(name: str):
        calls.append(name)
        # Return None for half the names to exercise the skip path.
        return None if len(calls) % 2 == 0 else 42

    resolved = resolve_branches_to_indxs(branches, mock_resolver)
    # Each surface form was passed to the resolver exactly once, in order.
    assert calls == expected_surfaces, (
        f"resolver call list diverged from extracted surfaces.\n"
        f"  calls    = {calls}\n  expected = {expected_surfaces}"
    )
    # Telemetry tracks attempts vs resolutions.
    assert _UNIFIED_CHAIN_STATS["narrators_attempted"] == len(expected_surfaces)
    assert _UNIFIED_CHAIN_STATS["narrators_resolved"] == sum(
        1 for i in range(1, len(expected_surfaces) + 1) if i % 2 == 1
    )
    # Resolved branches are int-only; None was skipped.
    for br in resolved:
        for idx in br:
            assert isinstance(idx, int)


# --------------------------------------------------------------------------- #
# FR-3.1 — `_compute_chain_indx` formatting
# --------------------------------------------------------------------------- #


def test_compute_chain_indx_multi_branch_format(fixtures):
    """Multi-branch text produces a `|`-delimited cell with comma-separated
    int branches on each side.
    """
    counter = {"n": 0}

    def mock_resolver(name: str):
        counter["n"] += 1
        # Cycle through 1, 2, 3 so output is deterministic and non-empty.
        return ((counter["n"] - 1) % 3) + 1

    cell = _compute_chain_indx(
        fixtures["30001"]["text_ar"],
        fallback=None,
        resolve_narrator=mock_resolver,
    )
    assert "|" in cell, f"expected multi-branch '|' cell; got {cell!r}"
    parts = cell.split("|")
    assert len(parts) >= 2
    for part in parts:
        # Each branch is non-empty and parses as csv ints.
        assert part, "empty branch in multi-branch cell"
        for token in part.split(","):
            assert token.strip().isdigit(), (
                f"non-int token {token!r} in chain_indx cell {cell!r}"
            )


def test_compute_chain_indx_single_branch_no_pipe():
    """Single-chain text returns a comma-only cell with NO `|` — backwards
    compatible with the existing CSV consumers (Imami / Bukhari rows).
    """
    counter = {"n": 0}

    def mock_resolver(name: str):
        counter["n"] += 1
        return counter["n"] * 10  # 10, 20, 30, 40

    cell = _compute_chain_indx(
        BUKHARI_SINGLE_CHAIN,
        fallback=None,
        resolve_narrator=mock_resolver,
    )
    assert "|" not in cell, (
        f"single-chain cell must not contain '|' for backwards compat; got {cell!r}"
    )
    assert cell, "expected non-empty single-branch cell"
    for token in cell.split(","):
        assert token.strip().isdigit(), (
            f"non-int token {token!r} in single-branch cell {cell!r}"
        )


def test_compute_chain_indx_fallback_when_no_text():
    """When text_ar is None/empty, return the fallback verbatim and bump
    the `fallback_used` counter.
    """
    cell = _compute_chain_indx(None, fallback="10,20,30")
    assert cell == "10,20,30"
    assert _UNIFIED_CHAIN_STATS["fallback_used"] == 1

    cell = _compute_chain_indx("", fallback="40,50")
    assert cell == "40,50"
    assert _UNIFIED_CHAIN_STATS["fallback_used"] == 2


def test_compute_chain_indx_empty_when_no_text_no_fallback():
    """No text + no fallback → empty string. No fallback counter bump."""
    assert _compute_chain_indx(None, fallback=None) == ""
    assert _compute_chain_indx("", fallback="") == ""
    assert _UNIFIED_CHAIN_STATS["fallback_used"] == 0


def test_compute_chain_indx_requires_resolver_when_text_present():
    """Non-empty text_ar with resolve_narrator=None raises ValueError —
    the unified pipeline always supplies a resolver; making the param
    optional is purely for the text-only extractor test path.
    """
    with pytest.raises(ValueError):
        _compute_chain_indx(BUKHARI_SINGLE_CHAIN, fallback=None, resolve_narrator=None)
