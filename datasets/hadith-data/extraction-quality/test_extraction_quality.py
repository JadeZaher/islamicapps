"""Flow tests: the audit on real records with known defects, and the model harness with a fake transport.

    python -I -X utf8 -m pytest datasets/hadith-data/extraction-quality/test_extraction_quality.py -q
Needs output/production_snapshot.jsonl.gz (read-only copy of the production rows) and the OpenITI sources.
"""
import gzip
import io
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deterministic_checks as dc  # noqa: E402
import eq_source as eq  # noqa: E402
import score_with_model as sm  # noqa: E402


# ----------------------------------------------------------------------------- the audit on real records
@pytest.fixture(scope="module")
def audit(tmp_path_factory):
    out = tmp_path_factory.mktemp("audit")
    summary = dc.main(["--out", str(out)])
    rows = {}
    with gzip.open(out / "extraction_findings.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["id"].split(":")[-1].split("|")[0]] = row
    with gzip.open(out / "missed_source_reports.jsonl.gz", "rt", encoding="utf-8") as handle:
        missed = [json.loads(line) for line in handle]
    return summary, rows, missed


def flags_of(row):
    return {f["flag"] for f in row["flags"]}


def test_replay_reproduces_every_production_text_byte_for_byte(audit):
    summary, _rows, _missed = audit
    for work, counts in summary["replay"].items():
        assert counts["reproduced_exactly"] == counts["production_rows"], work
    # production lacks zayd_0118 («الثياب للصلاة:», a heading kept as a record by the parser); the replay still sees it
    assert summary["replay"]["zayd"]["replay_only_ids"] == ["zayd_0118|118|V01P137"]


@pytest.mark.parametrize("record_id, expected_flags", [
    ("rabi_0140", {"footnote_leak", "commentary_tail"}),
    ("rabi_0225", {"footnote_leak"}),
    ("rabi_0121", {"footnote_leak"}),
    ("rabi_0335", {"commentary_tail"}),
    ("rabi_0880", {"commentary_tail"}),
    ("rabi_0002", {"truncated"}),
    ("rabi_0001", {"sanad_matn_split_wrong"}),
    ("rabi_0001b", {"sanad_matn_split_wrong"}),
    ("zayd_0026", {"markup_leak"}),
    ("zayd_0429", {"fragment_only_chain"}),
    ("rida_0032", {"merged_records"}),
])
def test_known_defects_are_flagged(audit, record_id, expected_flags):
    _s, rows, _m = audit
    assert expected_flags <= flags_of(rows[record_id])


def test_footnote_and_commentary_are_separated_from_the_report(audit):
    proposal = audit[1]["rabi_0140"]["proposal"]
    assert proposal["text_ar"].endswith("عند الجنابة».")
    assert "__________" not in proposal["text_ar"]
    # the `(1) *` notes carry no text in this edition; what follows them is Rabi's second comment paragraph
    assert "footnotes" not in proposal
    assert any(c.startswith("قال الربيع: قال أبو عبيدة") for c in proposal["commentary"])
    assert any(c.startswith("قال الربيع: الفنيكة هي") and "المسربة التي في الرقبة" in c for c in proposal["commentary"])
    assert audit[1]["rabi_0225"]["proposal"]["footnotes"] == ["* خ: هذه."]
    assert audit[1]["rabi_0335"]["proposal"]["text_ar"].endswith("ذات عوار».")


def test_chain_closes_with_the_reporting_verb_and_matn_follows(audit):
    proposal = audit[1]["rabi_0001"]["proposal"]
    assert proposal["sanad_ar"].endswith("عن النبيء صلى الله عليه وسلم قال:")
    assert proposal["matn_ar"] == "«نية المؤمن خير من عمله»."
    continuation = audit[1]["rabi_0001b"]["proposal"]
    assert continuation["sanad_ar"] == "وبهذا السند في رواية أخرى عنه عليه السلام قال:"


def test_marker_stripped_and_fragment_merged_with_the_report_it_opens(audit):
    assert audit[1]["zayd_0026"]["proposal"]["text_ar"].startswith("سألت زيدا")
    fragment = audit[1]["zayd_0429"]["proposal"]
    assert fragment["merge_with_next"].startswith("zayd_0430|")
    assert fragment["merged_text_ar"].startswith("حدثني أبو خالد الواسطي قال:")
    assert fragment["merged_matn_ar"].startswith("تزوجوا فاني مكاثر")


def test_merged_rida_record_is_split_at_reports_and_chapter_headings(audit):
    parts = audit[1]["rida_0032"]["proposal"]["split_into"]
    headings = [p["text_ar"] for p in parts if p["kind"] == "heading"]
    assert "الباب التاسع في فضل الغزو والجهاد" in headings
    assert sum(1 for p in parts if p["kind"] == "report") >= 10
    assert all(p["text_ar"].startswith("وباسناده") for p in parts if p["kind"] == "report")


def test_a_whole_report_missing_from_production_is_listed(audit):
    missed = [m for m in audit[2] if m["reason"] == "numbered_report_dropped_whole"]
    assert [m["label"] for m in missed] == ["881"]
    assert missed[0]["text"].startswith("وأما ما سألت عنه من قول الحواريين")


def test_every_proposed_string_is_a_verbatim_substring_of_its_source_window(audit):
    summary = audit[0]
    for work, block in summary["works"].items():
        assert block["proposal_failures"] == [], work
        assert block["proposal_fields_validated"].get("ok", 0) > 0


@pytest.mark.parametrize("text, kind, sanad_tail, matn_head", [
    ("أبو عبيدة عن جابر بن زيد عن ابن عباس قال: «الأعمال بالنيات»", "chain_and_matn", "عن ابن عباس قال:", "«الأعمال"),
    ("أبو عبيدة عن جابر عن النبيء صلى الله عليه وسلم: «الإحسان أن تعمل لله»", "chain_and_matn", "وسلم:", "«الإحسان"),
    ("= حدثني زيد بن علي عن أبيه عن جده عن علي (ع م) من اعتل ظهر عليه", "chain_and_matn", "(ع م)", "من اعتل"),
    ("سألت زيدا بن علي عن الوضوء فقال جائز", "no_chain", None, None),
    ("حدثني أبو خالد الواسطي قال:", "chain_only", None, None),
])
def test_chain_matn_rule_split(text, kind, sanad_tail, matn_head):
    sp = dc.split_chain_matn(text)
    assert sp["kind"] == kind
    if sanad_tail:
        assert text[:sp["sanad_end"]].rstrip().endswith(sanad_tail)
        assert text[sp["matn_start"]:].startswith(matn_head)


# ----------------------------------------------------------------------------- the model harness with a fake transport
WINDOW = "أبو عبيدة عن جابر بن زيد قال: قال رسول الله «الأعمال بالنيات». ولدها، والأكولة شاة اللحم"


def make_input(tmp_path, n=3):
    path = tmp_path / "records.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for i in range(n):
            handle.write(json.dumps({"id": f"r{i}", "work": "rabi", "text_ar": WINDOW, "sanad": "x", "matn_ar": "قال:", "window_ar": WINDOW}, ensure_ascii=False) + "\n")
    return str(path)


def args_for(tmp_path, **extra):
    argv = ["--input", make_input(tmp_path), "--output", str(tmp_path / "v.jsonl"), "--manifest", str(tmp_path / "m.json"), "--batch-size", "3"]
    for key, value in extra.items():
        argv += [f"--{key.replace('_', '-')}", str(value)]
    return sm.parse_args(argv)


def good_item(rid, **proposals):
    base = {"text_ar": None, "sanad_ar": None, "matn_ar": None, "footnotes": [], "commentary": []}
    base.update(proposals)
    return {"id": rid, "scores": {"boundaries": 2, "cleanliness": 3, "sanad_matn_split": 1}, "flags": ["commentary_tail"], "reason": "tail", "proposals": base}


class FakeTransport:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, url, headers, body, timeout=0):
        self.calls.append((url, headers, body))
        return self.replies.pop(0)


def ok_reply(items, cost=0.0001):
    content = json.dumps({"verdicts": items}, ensure_ascii=False)
    return 200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": cost}}


def read_rows(path):
    return [json.loads(line) for line in open(path, encoding="utf-8")]


SECRET = "sk-or-test-SECRET-KEY"


def test_verdicts_are_validated_proposals_must_be_window_substrings(tmp_path):
    items = [good_item("r0", matn_ar="«الأعمال بالنيات»."),
             good_item("r1", matn_ar="invented text not in the window", footnotes=["ولدها، والأكولة"]),
             {"id": "r2", "scores": {"boundaries": 9, "cleanliness": 3, "sanad_matn_split": 1}, "flags": [], "reason": "x", "proposals": {}}]
    transport = FakeTransport([ok_reply(items)])
    manifest = sm.run(args_for(tmp_path), transport=transport, key_loader=lambda: SECRET)
    rows = {r["id"]: r for r in read_rows(tmp_path / "v.jsonl")}
    assert rows["r0"]["verdict"]["proposals"]["matn_ar"] == "«الأعمال بالنيات»."
    assert rows["r1"]["verdict"]["proposals"]["matn_ar"] is None and rows["r1"]["verdict"]["rejected_proposals"] == ["matn_ar"]
    assert rows["r1"]["verdict"]["proposals"]["footnotes"] == ["ولدها، والأكولة"]
    assert rows["r2"]["status"] == "failed" and rows["r2"]["problems"] == ["scores_invalid"]
    assert (manifest["records_ok"], manifest["records_failed"]) == (2, 1)
    # provenance on every row and in the manifest; no key anywhere; no referer-style headers
    for row in rows.values():
        assert row["prompt_sha256"] == manifest["prompt_sha256"] and row["model"] == "qwen/qwen3.7-flash"
        assert row["request_started_utc"] and row["request_finished_utc"]
    assert SECRET not in open(tmp_path / "v.jsonl", encoding="utf-8").read() + open(tmp_path / "m.json", encoding="utf-8").read()
    headers = transport.calls[0][1]
    assert set(headers) == {"Authorization", "Content-Type"}
    assert transport.calls[0][2]["temperature"] == 0


def test_http_402_stops_cleanly_and_nothing_is_marked_done(tmp_path):
    transport = FakeTransport([(402, {"error": {"message": "insufficient credits"}}), ok_reply([])])
    manifest = sm.run(args_for(tmp_path), transport=transport, key_loader=lambda: SECRET)
    assert manifest["status"] == "stopped" and manifest["stopped_because"] == "http_402_payment_required"
    assert len(transport.calls) == 1  # no retry, no second batch
    assert not os.path.exists(tmp_path / "v.jsonl") or read_rows(tmp_path / "v.jsonl") == []


def test_resume_skips_stored_records_and_cost_cap_blocks_requests(tmp_path):
    items = [good_item(f"r{i}") for i in range(3)]
    first = FakeTransport([ok_reply(items)])
    sm.run(args_for(tmp_path), transport=first, key_loader=lambda: SECRET)
    second = FakeTransport([])
    again = sm.run(args_for(tmp_path), transport=second, key_loader=lambda: SECRET)
    assert second.calls == [] and again["records_selected"] == 0
    capped = args_for(tmp_path / "other") if (tmp_path / "other").mkdir() is None else None
    capped.max_cost_usd = 0.0
    blocked = sm.run(capped, transport=FakeTransport([]), key_loader=lambda: SECRET)
    assert blocked["stopped_because"] == "cost_cap" and blocked["requests"] == 0


def test_answer_parsing_tolerates_fence_and_reports_missing_ids():
    records = [{"id": "a", "window_ar": WINDOW}, {"id": "b", "window_ar": WINDOW}]
    content = "```json\n" + json.dumps({"verdicts": [good_item("a")]}) + "\n```"
    parsed = sm.parse_response(content, records)
    assert parsed["a"][0]["scores"]["boundaries"] == 2
    assert parsed["b"] == (None, ["missing_from_answer"])
    assert all(v == (None, ["answer_not_json_with_verdicts"]) for v in sm.parse_response("sorry, I cannot", records).values())
