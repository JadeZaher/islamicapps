"""Standard-library tests for the canonical uniform isnad extractor."""
from __future__ import annotations

import csv
import functools
import json
import pathlib
import statistics
import sys
import unittest


_HERE = pathlib.Path(__file__).resolve().parent
_DATA_DIR = _HERE.parent
sys.path.insert(0, str(_DATA_DIR))

from extract_isnad_unified import (  # noqa: E402
    _UNIFIED_CHAIN_STATS,
    _compute_chain_indx,
    IsnadExtractionLimitError,
    MAX_ISNAD_BRANCHES,
    UnresolvedNarratorError,
    extract_isnad_branches,
    name_normalize,
    reset_stats,
    resolve_branches_to_indxs,
)


_GOLD = _HERE / "fixtures" / "all-tradition-isnad-gold-v1.jsonl"
_REQUIRED_FIELDS = {
    "case_id",
    "record_id",
    "source_record_id",
    "provenance_source",
    "input_scope",
    "source",
    "tradition",
    "hadith_no",
    "tags",
    "text_ar",
    "expected_branches",
    "annotation_basis",
}


@functools.lru_cache(maxsize=None)
def _json_asset(relative_path: str):
    return json.loads((_DATA_DIR / relative_path).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _k6_source_rows() -> dict[str, dict]:
    with (_DATA_DIR / "all_hadiths_unified.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _declared_source_record(row: dict) -> dict:
    provenance = row["provenance_source"]
    if provenance == "all_hadiths_unified.csv":
        self_id = row["source_record_id"]
        if row["record_id"] != f"k6:{self_id}":
            raise AssertionError(f"non-canonical K6 identity: {row['record_id']}")
        return _k6_source_rows()[self_id]
    if provenance.startswith("shia-hadith/v2_books/"):
        file_id, hadith_id = row["source_record_id"].split(":", 1)
        if pathlib.Path(provenance).stem != file_id:
            raise AssertionError(f"Thaqalayn file identity mismatch: {row['case_id']}")
        if row["record_id"] != f"thaqalayn:{file_id}:{hadith_id}":
            raise AssertionError(
                f"non-canonical Thaqalayn identity: {row['record_id']}"
            )
        records = _json_asset(provenance)
        return next(record for record in records if str(record.get("id")) == hadith_id)
    records = _json_asset(provenance)["hadiths"]
    parsed_id, hadith_no, page_ref = row["source_record_id"].split("|", 2)
    record = next(
        record for record in records
        if str(record.get("id") or record.get("hadith_no") or "").strip() == parsed_id
        and str(record.get("hadith_no") or "").strip() == hadith_no
        and str(record.get("page_ref") or "").strip() == page_ref
    )
    expected_record_id = f"openiti:{row['tradition'].lower()}:{row['source_record_id']}"
    if row["record_id"] != expected_record_id:
        raise AssertionError(f"non-canonical OpenITI identity: {row['record_id']}")
    return record


def _load_gold() -> list[dict]:
    rows: list[dict] = []
    with _GOLD.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_line_no"] = line_no
            rows.append(row)
    return rows


def _jaccard(left: list[str], right: list[str]) -> float:
    a = {name_normalize(value) for value in left if value.strip()}
    b = {name_normalize(value) for value in right if value.strip()}
    return 1.0 if not (a | b) else len(a & b) / len(a | b)


def _edit_distance(left: list[str], right: list[str]) -> int:
    a = [name_normalize(value) for value in left]
    b = [name_normalize(value) for value in right]
    matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for index in range(len(a) + 1):
        matrix[index][0] = index
    for index in range(len(b) + 1):
        matrix[0][index] = index
    for left_index in range(1, len(a) + 1):
        for right_index in range(1, len(b) + 1):
            cost = int(a[left_index - 1] != b[right_index - 1])
            matrix[left_index][right_index] = min(
                matrix[left_index - 1][right_index] + 1,
                matrix[left_index][right_index - 1] + 1,
                matrix[left_index - 1][right_index - 1] + cost,
            )
    return matrix[-1][-1]


def _ordered_similarity(left: list[str], right: list[str]) -> float:
    longest = max(len(left), len(right))
    return 1.0 if longest == 0 else 1.0 - _edit_distance(left, right) / longest


def _best_aligned_jaccards(
    actual: list[list[str]], expected: list[list[str]]
) -> list[float]:
    remaining = list(expected)
    scores: list[float] = []
    for branch in actual:
        if not remaining:
            scores.append(0.0)
            continue
        ranked = [(_jaccard(branch, candidate), index) for index, candidate in enumerate(remaining)]
        score, best_index = max(ranked)
        scores.append(score)
        remaining.pop(best_index)
    scores.extend(0.0 for _ in remaining)
    return scores


def _best_aligned_metrics(
    actual: list[list[str]], expected: list[list[str]]
) -> list[tuple[float, float]]:
    remaining = list(expected)
    scores = []
    for branch in actual:
        if not remaining:
            scores.append((0.0, 0.0))
            continue
        ranked = [
            (
                (_jaccard(branch, candidate) + _ordered_similarity(branch, candidate)) / 2,
                _jaccard(branch, candidate),
                _ordered_similarity(branch, candidate),
                -index,
                index,
            )
            for index, candidate in enumerate(remaining)
        ]
        _, jaccard, ordered, _, best_index = max(ranked)
        remaining.pop(best_index)
        scores.append((jaccard, ordered))
    scores.extend((0.0, 0.0) for _ in remaining)
    return scores


class GoldFixtureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _load_gold()

    def test_gold_has_at_least_thirty_unique_real_cases(self) -> None:
        self.assertGreaterEqual(len(self.rows), 30)
        case_ids = [row["case_id"] for row in self.rows]
        record_ids = [row["record_id"] for row in self.rows]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(record_ids), len(set(record_ids)))

    def test_gold_covers_every_loaded_tradition_and_edge_class(self) -> None:
        traditions = {row["tradition"] for row in self.rows}
        self.assertTrue({"Sunni", "Imami", "Ibadi", "Zaydi"} <= traditions)
        tags = {tag for row in self.rows for tag in row["tags"]}
        self.assertTrue(
            {
                "tahweel",
                "single-chain",
                "co-transmitter",
                "pronoun",
                "surface-drift",
                "diacritized",
            }
            <= tags
        )

    def test_every_gold_row_has_auditable_provenance(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row.get("case_id")):
                self.assertFalse(_REQUIRED_FIELDS - set(row))
                self.assertIn(row["input_scope"], {"full_record", "chain_bearing_excerpt"})
                self.assertTrue(row["provenance_source"].strip())
                self.assertTrue(row["source_record_id"].strip())
                self.assertRegex(
                    row["annotation_basis"], r"^Manual(?: chain)? reading\b"
                )
                self.assertTrue(row["text_ar"].strip())
                self.assertTrue(row["expected_branches"])
                self.assertTrue(all(branch for branch in row["expected_branches"]))

    def test_declared_source_text_and_excerpt_bounds_are_exact(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                source = _declared_source_record(row)
                source_text = source.get("arabicText", source.get("text_ar", ""))
                if row["input_scope"] == "full_record":
                    self.assertEqual(row["text_ar"], source_text)
                    continue
                bounds = row.get("excerpt_bounds")
                self.assertEqual(set(bounds or {}), {"start", "end"})
                self.assertIsInstance(bounds["start"], int)
                self.assertIsInstance(bounds["end"], int)
                self.assertGreaterEqual(bounds["start"], 0)
                self.assertGreater(bounds["end"], bounds["start"])
                self.assertLessEqual(bounds["end"], len(source_text))
                self.assertEqual(
                    source_text[bounds["start"]:bounds["end"]], row["text_ar"]
                )


class ExtractionQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = _load_gold()

    def setUp(self) -> None:
        reset_stats()

    def test_branch_count_and_per_case_jaccard_floor(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                actual = extract_isnad_branches(row["text_ar"])
                expected = row["expected_branches"]
                self.assertEqual(len(actual), len(expected), actual)
                scores = _best_aligned_jaccards(actual, expected)
                self.assertGreaterEqual(statistics.mean(scores), 0.80, (actual, expected, scores))

    def test_gold_macro_quality_threshold(self) -> None:
        branch_count_hits = 0
        branch_scores: list[float] = []
        ordered_scores: list[float] = []
        traditions: dict[str, dict[str, list[float]]] = {}
        for row in self.rows:
            actual = extract_isnad_branches(row["text_ar"])
            expected = row["expected_branches"]
            branch_hit = int(len(actual) == len(expected))
            branch_count_hits += branch_hit
            metrics = _best_aligned_metrics(actual, expected)
            branch_scores.extend(score[0] for score in metrics)
            ordered_scores.extend(score[1] for score in metrics)
            tradition = traditions.setdefault(
                row["tradition"], {"branch_hits": [], "ordered": []}
            )
            tradition["branch_hits"].append(branch_hit)
            tradition["ordered"].extend(score[1] for score in metrics)
        self.assertGreaterEqual(branch_count_hits / len(self.rows), 0.90)
        self.assertGreaterEqual(statistics.median(branch_scores), 0.90)
        self.assertGreaterEqual(statistics.median(ordered_scores), 0.90)
        for tradition, metrics in traditions.items():
            with self.subTest(tradition=tradition):
                self.assertGreaterEqual(statistics.mean(metrics["branch_hits"]), 0.80)
                self.assertGreaterEqual(statistics.mean(metrics["ordered"]), 0.80)

    def test_reversing_a_chain_cannot_pass_the_ordered_gate(self) -> None:
        chain = ["الأول", "الثاني", "الثالث", "الرابع"]
        self.assertEqual(_jaccard(chain, list(reversed(chain))), 1.0)
        self.assertLess(_ordered_similarity(chain, list(reversed(chain))), 0.90)

    def test_co_transmitters_are_parallel_never_adjacent(self) -> None:
        co_transmitter_pairs = {
            "sunni-muslim-1-independent-branches": [("شعبة", "سفيان")],
            "sunni-muslim-2-co-transmitters": [
                ("محمد بن المثنى", "ابن بشار")
            ],
            "imami-uyun-v2-1-cotransmitters": [
                ("أبي", "محمد بن الحسن بن أحمد بن الوليد"),
                ("سعد بن عبد الله", "عبد الله بن جعفر الحميري"),
            ],
        }
        source_order_markers = {
            "sunni-muslim-1-independent-branches": [
                ("الحكم",), ("شعبة", "حبيب"), ("سفيان", "حبيب")
            ],
            "sunni-muslim-2-co-transmitters": [
                ("أبو بكر بن أبي شيبة",),
                ("محمد بن المثنى",),
                ("ابن بشار",),
            ],
            "imami-uyun-v2-1-cotransmitters": [
                ("أبي", "سعد بن عبد الله"),
                ("أبي", "عبد الله بن جعفر الحميري"),
                ("محمد بن الحسن بن أحمد بن الوليد", "سعد بن عبد الله"),
                (
                    "محمد بن الحسن بن أحمد بن الوليد",
                    "عبد الله بن جعفر الحميري",
                ),
            ],
        }

        def contains_surface(branch: list[str], target: str) -> bool:
            normalized_target = name_normalize(target)
            return any(
                normalized_target in name_normalize(surface)
                or name_normalize(surface) in normalized_target
                for surface in branch
            )

        def contains_exact_surface(branch: list[str], target: str) -> bool:
            normalized_target = name_normalize(target)
            return any(
                name_normalize(surface) == normalized_target for surface in branch
            )

        for row in self.rows:
            if "co-transmitter" not in row["tags"]:
                continue
            with self.subTest(case_id=row["case_id"]):
                actual = extract_isnad_branches(row["text_ar"])
                expected = row["expected_branches"]
                self.assertEqual(len(actual), len(expected))
                for jaccard, ordered in _best_aligned_metrics(actual, expected):
                    self.assertGreaterEqual(jaccard, 0.80)
                    self.assertGreaterEqual(ordered, 0.80)
                for branch, markers in zip(
                    actual, source_order_markers[row["case_id"]], strict=True
                ):
                    self.assertTrue(
                        all(contains_surface(branch, marker) for marker in markers)
                    )
                for left, right in co_transmitter_pairs[row["case_id"]]:
                    self.assertTrue(all(
                        not (
                            contains_exact_surface(branch, left)
                            and contains_exact_surface(branch, right)
                        )
                        for branch in actual
                    ))

    def test_co_transmitter_cartesian_expansion_is_bounded(self) -> None:
        levels = [
            "زيد وعمرو", "بكر وخالد", "سعيد ومسعود", "نافع ومالك",
            "حسن وحسين", "سالم وقاسم", "راشد وكامل",
        ]
        text = " ".join(f"حدثنا {level}" for level in levels)
        with self.assertRaises(IsnadExtractionLimitError) as raised:
            extract_isnad_branches(text)
        self.assertEqual(raised.exception.stage, "segment_co_transmitters")
        self.assertGreater(raised.exception.projected, MAX_ISNAD_BRANCHES)
        self.assertEqual(_UNIFIED_CHAIN_STATS["rows_extraction_failed"], 1)

    def test_tahweel_stitching_projection_is_bounded(self) -> None:
        first_levels = [
            "زيد وعمرو", "بكر وخالد", "سعيد ومسعود", "نافع ومالك",
            "حسن وحسين",
        ]
        second_levels = [
            "سالم وقاسم", "راشد وكامل", "عادل وفاضل", "ثابت وحمزة",
            "منصور وموسى",
        ]
        first = " ".join(f"حدثنا {level}" for level in first_levels)
        second = " ".join(f"حدثنا {level}" for level in second_levels)
        text = f"{first} ح و{second}"
        with self.assertRaises(IsnadExtractionLimitError) as raised:
            extract_isnad_branches(text)
        self.assertEqual(raised.exception.stage, "tahweel_stitching")
        self.assertGreater(raised.exception.projected, MAX_ISNAD_BRANCHES)

    def test_four_branch_gold_case_remains_within_limit(self) -> None:
        row = next(
            row for row in self.rows
            if row["case_id"] == "imami-uyun-v2-1-cotransmitters"
        )
        actual = extract_isnad_branches(row["text_ar"])
        self.assertEqual(len(actual), 4)
        for jaccard, ordered in _best_aligned_metrics(
            actual, row["expected_branches"]
        ):
            self.assertGreaterEqual(jaccard, 0.80)
            self.assertGreaterEqual(ordered, 0.80)

    def test_empty_input_is_not_a_synthetic_branch(self) -> None:
        self.assertEqual(extract_isnad_branches(""), [])
        self.assertEqual(extract_isnad_branches(None), [])
        self.assertEqual(_UNIFIED_CHAIN_STATS["rows_empty"], 2)
        self.assertEqual(_UNIFIED_CHAIN_STATS["rows_with_text"], 0)

    def test_pronouns_and_source_surface_drift_are_preserved(self) -> None:
        by_id = {row["case_id"]: row for row in self.rows}
        pronoun = extract_isnad_branches(by_id["sunni-muslim-102-pronoun"]["text_ar"])
        self.assertIn("أبي", pronoun[1])
        drift = extract_isnad_branches(by_id["sunni-muslim-31-surface-drift"]["text_ar"])
        flattened = [name for branch in drift for name in branch]
        self.assertIn("سفيان", flattened)
        self.assertIn("سفيان بن عيينة", flattened)

    def test_diacritics_do_not_hide_transmission_links(self) -> None:
        row = next(row for row in self.rows if row["case_id"] == "imami-kafi-v4-1")
        actual = extract_isnad_branches(row["text_ar"])
        self.assertEqual(len(actual), 1)
        self.assertGreaterEqual(_jaccard(actual[0], row["expected_branches"][0]), 0.90)


class ResolverAndFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_stats()

    def test_resolution_is_atomic_when_any_surface_is_unresolved(self) -> None:
        calls: list[str] = []

        def resolver(surface: str):
            calls.append(surface)
            return {"A": 10, "B": None, "C": "20", "D": -1}[surface]

        branches = [["A", "B"], ["C", "D"]]
        with self.assertRaises(UnresolvedNarratorError) as raised:
            resolve_branches_to_indxs(branches, resolver)
        self.assertEqual(raised.exception.surface, "B")
        self.assertEqual(calls, ["A", "B"])
        self.assertEqual(_UNIFIED_CHAIN_STATS["narrators_attempted"], 2)
        self.assertEqual(_UNIFIED_CHAIN_STATS["narrators_resolved"], 1)
        self.assertEqual(_UNIFIED_CHAIN_STATS["narrators_unresolved"], 1)
        self.assertEqual(_UNIFIED_CHAIN_STATS["rows_resolution_failed"], 1)

    def test_invalid_resolver_value_fails_the_whole_row(self) -> None:
        with self.assertRaises(UnresolvedNarratorError):
            resolve_branches_to_indxs([["A", "B"]], lambda name: 10 if name == "A" else -1)
        self.assertEqual(_UNIFIED_CHAIN_STATS["narrators_invalid"], 1)

    def test_compute_chain_indx_formats_multiple_branches(self) -> None:
        row = next(
            row for row in _load_gold()
            if row["case_id"] == "sunni-tirmidhi-1-tahweel"
        )
        counter = iter(range(1, 100))
        cell = _compute_chain_indx(
            row["text_ar"], fallback=None, resolve_narrator=lambda _: next(counter)
        )
        branches = cell.split("|")
        self.assertEqual(len(branches), 2)
        self.assertTrue(all(token.isdigit() for branch in branches for token in branch.split(",")))

    def test_compute_chain_indx_fallback_and_strict_resolver_contract(self) -> None:
        self.assertEqual(_compute_chain_indx(None, fallback="10,20"), "10,20")
        self.assertEqual(_UNIFIED_CHAIN_STATS["fallback_used"], 1)
        with self.assertRaises(ValueError):
            _compute_chain_indx("حدثنا زيد", fallback=None, resolve_narrator=None)


if __name__ == "__main__":
    unittest.main()
