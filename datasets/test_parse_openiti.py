"""Flow tests for parse_openiti.py: the real parsers on the real OpenITI sources, asserting the observable records.

    python -I -X utf8 -m pytest datasets/test_parse_openiti.py -q

Needs the three sources under hadith-data/openiti-sources and, for the id-preservation flow, the read-only production snapshot
hadith-data/extraction-quality/output/production_snapshot.jsonl.gz (a missing snapshot fails the test). Nothing is written.
"""
import gzip
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_openiti as po  # noqa: E402

RABI = os.path.join(po.OPENITI_DIR, "rabi", "jamic_sahih_ibadiyya.txt")
ZAYD = os.path.join(po.OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown")
SNAPSHOT = os.path.join(HERE, "hadith-data", "extraction-quality", "output", "production_snapshot.jsonl.gz")
ARABIC_LETTER = re.compile("[ء-ي]")


@pytest.fixture(scope="module")
def parsed():
    return {"rabi": po.parse_rabi(RABI), "zayd": po.parse_zayd(ZAYD), "rida": po.parse_rida_appendix(ZAYD)}


def record(parsed, work, record_id):
    found = [r for r in parsed[work]["hadiths"] if r["id"] == record_id]
    assert len(found) == 1, f"{record_id}: {len(found)} records"
    return found[0]


# --------------------------------------------------------------------------- rabi: footnotes, commentary, headings, recovery
def test_rabi_0140_comment_and_footnote_block_leave_the_report(parsed):
    r = record(parsed, "rabi", "rabi_0140")
    assert r["text_ar"].endswith("عند الجنابة».")
    assert "__________" not in r["text_ar"] and "*" not in r["text_ar"] and "قال الربيع" not in r["text_ar"]
    assert r["footnotes"] == [] and r["footnote_markers_without_text"] == 3        # «(1) *» x3: numbers whose notes the edition left out
    assert r["commentary_kinds"] == ["rabi_comment", "rabi_comment"]
    assert r["commentary"][0].startswith("قال الربيع: قال أبو عبيدة: وعليه مع ذلك غسل رفغيه")
    assert r["commentary"][1].startswith("قال الربيع: الفنيكة هي:")
    assert r["commentary"][1].endswith("والمسربة هي: التي فصلت الصدر إلى السرة.")  # joined across the page break


def test_rabi_0225_footnote_text_is_a_footnote_not_report_text(parsed):
    r = record(parsed, "rabi", "rabi_0225")
    assert r["footnotes"] == ["خ: هذه."]
    assert r["text_ar"].endswith("فيما جهر به من الصلاة.") and "خ: هذه" not in r["text_ar"]
    assert len(r["commentary"]) == 1 and r["commentary"][0].startswith("قال الربيع: قال أبو عبيدة: إلا بفاتحة الكتاب")


def test_rabi_0335_comment_split_over_a_page_break_stays_out_of_the_text(parsed):
    r = record(parsed, "rabi", "rabi_0335")
    assert r["text_ar"].endswith("ولا ذات هزال ولا ذات عوار».")
    assert "ولدها" not in r["text_ar"]
    assert r["commentary"] == ["قال الربيع: السخلة التي تتبع أمها وهي ترضع عليها، والربى التي تربي ولدها، والأكولة شاة اللحم، وهي السمينة."]
    # «... قال للسعاة: «...»» has no colon after the reporting verb: not a confident cut, so nothing is invented
    assert (r["sanad_ar"], r["matn_ar"], r["split_confidence"]) == (None, None, "low")


def test_rabi_0880_editorial_section_is_one_arranger_note(parsed):
    r = record(parsed, "rabi", "rabi_0880")
    assert r["text_ar"].endswith("واستوى فلان على مال فلان يريدون أنه احتوى عليه وحازه ونحو ذلك.")
    assert r["commentary_kinds"] == ["arranger_note"]
    assert r["commentary"][0].startswith("تنبيه فإن سأل المسترشد") and len(r["commentary"][0]) > 3000
    assert "الحواريين" not in r["text_ar"] + r["commentary"][0]                 # report 881 does not hide inside 880


def test_rabi_0881_report_behind_a_page_marker_is_recovered(parsed):
    r = record(parsed, "rabi", "rabi_0881")
    assert r["hadith_no"] == 881 and r["page_ref"] == r["page_start"] == "V01P247"
    assert r["text_ar"].startswith("وأما ما سألت عنه من قول الحواريين لعيسى صلوات الله عليه:")
    assert r["text_ar"].endswith("بلا زوال وانتقال.")
    assert r["legacy_id"] is None and r["bab"].startswith("في قوله تعالى: {هل يستطيع ربك")


def test_rabi_0002_orphan_line_is_text_and_its_comment_is_its_own(parsed):
    r = record(parsed, "rabi", "rabi_0002")
    assert "فيكلمني فأعي ما يقول" in r["text_ar"] and "يتمثل لي الملك رجلا" in r["text_ar"]
    assert r["commentary"] == ["قال الربيع: «فيفصم عنه» أي فينجلي."]
    assert record(parsed, "rabi", "rabi_0001")["commentary"] == [] and record(parsed, "rabi", "rabi_0001b")["commentary"] == []


def test_rabi_sanad_and_matn_are_arabic_spans_of_the_text(parsed):
    first = record(parsed, "rabi", "rabi_0001")
    assert first["sanad_ar"].startswith("قال أبو عمرو الربيع بن حبيب بن عمرو البصري: حدثني أبو عبيدة")
    assert first["sanad_ar"].endswith("عن النبيء صلى الله عليه وسلم قال:")
    assert first["matn_ar"] == "«نية المؤمن خير من عمله»."
    again = record(parsed, "rabi", "rabi_0001b")
    assert again["sanad_ar"] == "وبهذا السند في رواية أخرى عنه عليه السلام قال:"
    assert again["sanad_inherits_from"] == "rabi_0001" and again["matn_ar"] == "«الأعمال بالنيات ولكل امرئ ما نوى»."


def test_rabi_duplicate_number_keeps_both_production_identities(parsed):
    both = [r for r in parsed["rabi"]["hadiths"] if r["id"] == "rabi_0387"]
    assert sorted(r["page_ref"] for r in both) == ["V01P096", "V01P097"]


# --------------------------------------------------------------------------- zayd
def test_zayd_edition_markers_are_gone_without_losing_text(parsed):
    for work in ("zayd", "rida", "rabi"):
        for r in parsed[work]["hadiths"]:
            assert not r["text_ar"].startswith(("=", "V")) and "=" not in r["text_ar"], r["id"]
            assert not re.search(r"(?:^|\s)\*(?:\s|$|\.)", r["text_ar"]) and "PageV" not in r["text_ar"] and "~~" not in r["text_ar"], r["id"]
    r = record(parsed, "zayd", "zayd_0026")
    assert r["text_ar"] == "سألت زيدا بن علي عليه السلام عن الوضوء مرة مرة فقال جائز والثلاث أفضل."
    assert (r["sanad_ar"], r["matn_ar"]) == ("", r["text_ar"])                      # a question to the imam: no isnad at all


def test_zayd_0429_chain_fragment_is_merged_into_the_report_it_opens(parsed):
    r = record(parsed, "zayd", "zayd_0429")
    assert r["text_ar"] == ("حدثني أبو خالد الواسطي قال: حدثني زيد بن علي عن ابيه عن جده عن علي (ع م) قال: "
                            "قال رسول الله صلى الله عليه وآله تزوجوا فاني مكاثر بكم الامم.")
    assert r["absorbed_ids"] == ["zayd_0430"]
    assert r["matn_ar"] == "تزوجوا فاني مكاثر بكم الامم." and r["sanad_ar"].endswith("قال رسول الله صلى الله عليه وآله")
    assert not any(h["id"] == "zayd_0430" for h in parsed["zayd"]["hadiths"])


def test_zayd_chain_opener_glued_to_the_end_moves_to_the_next_report(parsed):
    first, second = record(parsed, "zayd", "zayd_0001"), record(parsed, "zayd", "zayd_0002")
    assert first["text_ar"].endswith("فان كان اكثر من قدر الدرهم فاغسله.") and not first["text_ar"].endswith("(حدثني) أبو خالد قال:")
    assert second["text_ar"].startswith("(حدثني) أبو خالد قال: حدثني زيد بن علي عن آبائه") and second["prefix_from_id"] == "zayd_0001"
    assert second["text_ar"].endswith("ولم يغسل قدما.")                              # the page-break head «يغسل قدما.» rejoined its sentence


def test_zayd_two_reports_in_one_paragraph_split_with_a_suffix(parsed):
    first, second = record(parsed, "zayd", "zayd_0007"), record(parsed, "zayd", "zayd_0007#2")
    assert first["text_ar"].endswith("كرم الله وجهه عن النبي صلى الله عليه وآله.")
    assert second["text_ar"].startswith("حدثني زيد بن علي عن أبيه عن جده عن علي بن أبي طالب (ع م) قال جاء رجل")
    assert second["split_from"] == "zayd_0007" and second["hadith_no"] == first["hadith_no"]
    assert (second["sanad_ar"], second["matn_ar"], second["split_confidence"]) == (None, None, "low")   # «قال» without a colon


def test_zayd_orphan_line_and_heading_tail_are_placed_correctly(parsed):
    assert record(parsed, "zayd", "zayd_0611")["text_ar"].endswith("يوشك ان يقدح الشك في قلبه فإذا هو في وادي الهلكات.")
    r = record(parsed, "zayd", "zayd_0149")
    assert r["text_ar"].startswith("حدثني زيد بن علي") and "الطاهرين" not in r["text_ar"]
    assert r["bab"].endswith("الطاهرين:")                                          # the '~~' line after a heading belongs to the heading
    assert not any(h["id"] == "zayd_0118" for h in parsed["zayd"]["hadiths"])


# --------------------------------------------------------------------------- rida
def test_rida_0032_is_split_per_isnad_and_headings_become_chapter_titles(parsed):
    ids = [r["id"] for r in parsed["rida"]["hadiths"] if r["id"].split("#")[0] == "rida_0032"]
    assert ids == ["rida_0032"] + [f"rida_0032#{n}" for n in range(2, 13)]
    first = record(parsed, "rida", "rida_0032")
    assert first["text_ar"] == "وباسناده قال: قال رسول الله صلى الله عليه وآله ان الله يبغض الرجل يدخل عليه الرجل في بيته فلا يقاتله."
    assert first["sanad_ar"] == "وباسناده قال: قال رسول الله صلى الله عليه وآله" and first["sanad_inherits_from"] == "rida_0031#24"
    assert record(parsed, "rida", "rida_0032#2")["bab"] == "الباب التاسع في فضل الغزو والجهاد"
    assert record(parsed, "rida", "rida_0032#3")["bab"] == "الباب العاشر في أحاديث المتفرقة"
    assert not any("الباب التاسع" in r["text_ar"] or "الباب العاشر" in r["text_ar"] for r in parsed["rida"]["hadiths"])
    assert record(parsed, "rida", "rida_0032#12")["sanad_inherits_from"] == "rida_0032#11"


def test_rida_0001_chain_cut_by_a_page_break_is_one_report(parsed):
    r = record(parsed, "rida", "rida_0001")
    assert r["absorbed_ids"] == ["rida_0002"] and r["text_ar"].endswith("فمن دخل حصني أمن من عذابي")
    assert (r["sanad_ar"], r["matn_ar"], r["split_confidence"]) == (None, None, "low")  # the chain's own «قال حدثني» links: not a confident cut


# --------------------------------------------------------------------------- invariants over every record
@pytest.mark.parametrize("work", ["rabi", "zayd", "rida"])
def test_every_emitted_string_is_verbatim_source_and_splits_are_consistent(parsed, work):
    data = parsed[work]
    assert data["verification"]["failures"] == [] and data["verification"]["strings_checked"] > 400
    keys = [f"{r['id']}|{r['hadith_no']}|{r['page_ref']}" for r in data["hadiths"]]
    assert len(keys) == len(set(keys))
    earlier = set()
    for r in data["hadiths"]:
        text, sanad, matn = r["text_ar"], r["sanad_ar"], r["matn_ar"]
        if r["split_confidence"] == "low":
            assert sanad is None and matn is None, r["id"]
        else:
            assert matn is not None and text.startswith(sanad or "") and text.endswith(matn), r["id"]
            cut = len(sanad or "")
            assert not (cut and ARABIC_LETTER.match(text[cut - 1]) and ARABIC_LETTER.match(text[cut:cut + 1] or " ")), r["id"]
            assert not po.RE_VERB_START.match(matn) or sanad == "", r["id"]
        if r["sanad_inherits_from"]:
            assert r["sanad_inherits_from"] in earlier, r["id"]
        earlier.add(r["id"])
        assert all(c.strip() for c in r["commentary"]) and len(r["commentary"]) == len(r["commentary_kinds"])


@pytest.mark.parametrize("text, sanad, matn", [
    ("أبو عبيدة عن جابر بن زيد عن النبيء صلى الله عليه وسلم قال: «نية المؤمن خير من عمله».", "أبو عبيدة عن جابر بن زيد عن النبيء صلى الله عليه وسلم قال:", "«نية المؤمن خير من عمله»."),
    ("وباسناده قال: قال رسول الله صلى الله عليه وآله ان الله يبغض الرجل", "وباسناده قال: قال رسول الله صلى الله عليه وآله", "ان الله يبغض الرجل"),
    ("حدثني زيد بن علي عن أبيه عن جده عن علي (ع م) إذا صليت الظهر في منزلك", "حدثني زيد بن علي عن أبيه عن جده عن علي (ع م)", "إذا صليت الظهر في منزلك"),
    ("حدثني زيد بن علي عن أبيه عن جده عن علي عليه السلام. قال كنت رجلا مذءا فاستحييت", None, None),
    ("وقال زيد بن علي (ع م) الشفيع على شفعته إذا علم ما بينه وبين ثلاثة ايام", None, None),
    ("سألت زيدا بن علي عليه السلام عن الوضوء مرة مرة", "", "سألت زيدا بن علي عليه السلام عن الوضوء مرة مرة"),
])
def test_sanad_matn_split_table(text, sanad, matn):
    fields = po.sanad_matn_fields(text)
    assert (fields["sanad_ar"], fields["matn_ar"]) == (sanad, matn)
    assert fields["split_confidence"] == ("low" if sanad is None else "high")


# --------------------------------------------------------------------------- ids against production
@pytest.mark.parametrize("work, source", [("rabi", RABI), ("zayd", ZAYD), ("rida", ZAYD)])
def test_legacy_replay_reproduces_every_production_id_and_page_ref(work, source):
    assert os.path.exists(SNAPSHOT), "production snapshot missing: " + SNAPSHOT
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as handle:
        production = {json.loads(line)["source_record_id"] for line in handle}
    production = {k for k in production if k.startswith(work + "_")}
    replayed = {f"{s.id}|{s.hadith_no}|{s.page_ref}" for s in po.legacy_spans(source, work).spans}
    assert production <= replayed and replayed - production <= {"zayd_0118|118|V01P137"}


def test_every_production_report_id_survives_or_is_listed_as_absorbed(parsed):
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as handle:
        production = {json.loads(line)["source_record_id"] for line in handle}
    kept, absorbed = set(), set()
    for work, data in parsed.items():
        for r in data["hadiths"]:
            kept.add(f"{r['id']}|{r['hadith_no']}|{r['page_ref']}")
            absorbed.update(r["absorbed_ids"])
    lost = {k for k in production if k not in kept}
    assert {k.split("|")[0] for k in lost} == absorbed
    assert len(lost) == len(absorbed) and "rabi_0881|881|V01P247" in kept


def test_parse_is_deterministic():
    first = json.dumps(po.parse_zayd(ZAYD), ensure_ascii=False)
    assert first == json.dumps(po.parse_zayd(ZAYD), ensure_ascii=False)
