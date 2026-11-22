"""Build v3_2/prompt-v3_2.md (chain reader v3.2, a DRAFT: no model has run it and it is not to be used on existing outputs) and record its hash; every worked example and every quoted pilot case is validated here.

    python -B -X utf8 v3_2/tools/make_prompt_v3_2.py            (from chain-reader/)

The body is tools/chain_body_v3_2.md (v3.1's body plus three one-line additions for the judge's reader-error classes of tranche 01), the tradition conventions are v1's block (../tools/prompt_body.md, read-only),
the worked examples are v2's cx-0001 (context/examples-v2/chain-contexts.jsonl, read-only, trimmed), four real batch-001 reports of v3.1 and FOUR real tranche-01 reports the judge named, shortened
(examples/example-packets.jsonl, built by tools/build_example_packets_v3_2.py). v3.1's examples 2, 3 and 4 (al-Kafi imam, `وبهذا الإسناد` inherited, `cannot_read_without_previous_report`) and 7 («وقال عليه السلام», b1-38f586) were dropped to make room
(their rules stay in the text; example 6 still shows an `inherited` Imam). Build checks:
 - every example output passes validate_v3_2 against its real text (and expands to the stated number of routes);
 - every Arabic fragment the rules quote from the pilot stands in that pilot report (fold-insensitive);
 - eight full readings of the pilot cases the rules teach (cr-0133, 0177, 0144, 0200, 0202, 0136, 0205, 0008) pass validate_v3_2 and expand to what the rule says;
 - the prompt is not longer than v3_1/prompt-v3_1.md (27,173 letters).
Writes prompt-v3_2.md (LF) and prompt-v3_2.json {version, sha256, chars, inputs}. See v3_2/AGENTS.md §prompt.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V3 = HERE.parent
ROOT = V3.parent
CTX = ROOT / "context"
for path in (str(ROOT), str(V3)):
    sys.path.insert(0, path)

from expand_v3_2 import canonical, expand  # noqa: E402
from norm_v3_2 import fold_v3  # noqa: E402
from validate_v3_2 import validate_chain  # noqa: E402
from validate import load_reports  # noqa: E402

N_, U_, B_ = "narrator", "unnamed", "back_reference"
KEYS = {"Sahih Muslim": "sunni:muslim", "Al-Kafi": "imami:al-kafi", "Kitab al-Ghayba (Tusi)": "imami:kitab-al-ghayba-tusi", "Sahih Bukhari": "sunni:bukhari", "Sunan Ibn Majah": "sunni:ibnmajah"}
REPORTS = load_reports(ROOT / "pilot" / "reports.jsonl")

# Arabic fragments the rules quote, by pilot report: '...' / '…' in a quote splits it into fragments that must each stand in the report
QUOTES = {
    "cr-0133": ["ح وأنبأنا حميد بن مسعدة، عن سفيان بن حبيب، عن الأوزاعي، قال حدثنا أبو كثير، قال سمعت أبا هريرة", "قال حدثني أبو كثير", "وقال سويد في هاتين الشجرتين النخلة والعنبة"],
    "cr-0147": ["وفي حديث الليث وصالح أن الصعب بن جثامة أخبره", "بهذا الإسناد"],
    "cr-0213": ["قال محمد بن رافع وأخبرنا محمد بن بشر", "نحوه"],
    "cr-0136": ["قال: وأنشدني أبو الفرج البرقي الداودي قال: أنشدني شيخ"],
    "cr-0205": ["وقد روى شيبان عن يحيى بن أبي كثير مثل هذا"],
    "cr-0177": ["أنه سمع هانئا، مولى عثمان قال كان عثمان إذا وقف على قبر بكى", "فقال إن رسول الله صلى الله عليه وسلم قال"],
    "cr-0015": ["أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة"],
    "cr-0264": ["ونحن عند سعيد بن المسيب عن أبي هريرة", "حدثنا رجل، من مزينة"],
    "cr-0026": ["فسره قتادة لم يدخر"],
    "cr-0144": ["كلاهما عن المعتمر، قال ابن حبيب حدثنا معتمر بن سليمان"],
    "cr-0200": ["حدثني محمد بن الحسن قال حدثني محمد بن الحسن الصفار"],
    "cr-0202": ["أخبرني من، شهد النبي", "قلت من حدثك قال ابن عباس"],
    "cr-0060": ["قالت لأبي جعفر"],
    "cr-0027": ["فقال عبد الله ابن عمر ليس لها صداق"],
    "cr-0091": ["بهذا الإسناد نحو حديث عفان", "حدثنا إسحاق بن إبراهيم، ومحمد بن المثنى، جميعا عن عبد الصمد"],
}
# the rules' own wording of those fragments (what the prompt prints), checked against the quotes above by containment of the folded words
RULE_FRAGMENTS = {
    "cr-0133": ["ح وأنبأنا حميد بن مسعدة، عن سفيان بن حبيب، عن الأوزاعي، قال حدثنا أبو كثير، قال سمعت أبا هريرة", "وقال سويد في هاتين الشجرتين النخلة والعنبة", "حدثني أبو كثير"],
    "cr-0147": ["وفي حديث الليث وصالح أن الصعب بن جثامة أخبره"],
    "cr-0213": ["قال محمد بن رافع وأخبرنا محمد بن بشر"],
    "cr-0136": ["وأنشدني أبو الفرج البرقي الداودي"],
    "cr-0205": ["وقد روى شيبان عن يحيى بن أبي كثير مثل هذا"],
    "cr-0177": ["فقال إن رسول الله صلى الله عليه وسلم قال", "أنه سمع هانئا، مولى عثمان", "كان عثمان إذا وقف على قبر بكى"],
    "cr-0015": ["أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة"],
    "cr-0264": ["ونحن عند سعيد بن المسيب عن أبي هريرة", "حدثنا رجل، من مزينة"],
    "cr-0026": ["فسره قتادة لم يدخر"],
    "cr-0144": ["كلاهما عن المعتمر، قال ابن حبيب حدثنا معتمر بن سليمان"],
    "cr-0200": ["حدثني محمد بن الحسن قال حدثني محمد بن الحسن الصفار"],
    "cr-0202": ["قلت من حدثك قال ابن عباس"],
    "cr-0060": ["قالت لأبي جعفر"],
    "cr-0027": ["فقال عبد الله ابن عمر ليس لها صداق"],
}


def load_examples() -> dict[str, dict]:
    return {row["id"]: row for row in (json.loads(line) for line in (CTX / "examples-v2" / "chain-contexts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}


def batch_packets() -> dict[str, dict]:
    path = V3 / "examples" / "example-packets.jsonl"
    return {row["id"]: row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}


def item(spec) -> dict:
    """('surface', kind) | ('surface', kind, occurrence) | ('INH', 'surface', 'prev1') to a reader item."""
    if spec[0] == "INH":
        return {"surface": spec[1], "kind": "inherited", "from": spec[2]}
    result = {"surface": spec[0], "kind": spec[1]}
    if len(spec) > 2:
        result["occurrence"] = spec[2]
    return result


def fmt_levels(levels: list[list[dict]], indent: str) -> list[str]:
    return [indent + json.dumps(level, ensure_ascii=False, separators=(", ", ": ")) + ("," if i < len(levels) - 1 else "") for i, level in enumerate(levels)]


def format_chain_output(output: dict) -> str:
    lines = ['{"id": ' + json.dumps(output["id"]) + ', "status": ' + json.dumps(output["status"]) + ",", ' "groups": [']
    for g, group in enumerate(output["groups"]):
        lines.append('  {"levels": [')
        lines += fmt_levels(group["levels"], "    ")
        lines.append("  ]" + (', "variant": true' if group.get("variant") else "") + "}" + ("," if g < len(output["groups"]) - 1 else ""))
    lines.append(" ],")
    lines.append(' "shared_tail": null,' if output["shared_tail"] is None else ' "shared_tail": [')
    if output["shared_tail"] is not None:
        lines += fmt_levels(output["shared_tail"], "  ")
        lines.append(" ],")
    lines.append(f' "needs_ruling": {json.dumps(output["needs_ruling"])},')
    lines.append(' "notes": ' + json.dumps(output["notes"], ensure_ascii=False) + ",")
    lines.append(' "fixes": ' + json.dumps(output["fixes"], ensure_ascii=False) + "}")
    return "\n".join(lines)


def shown_context(context: dict, keep: tuple[str, ...]) -> dict:
    shown = {key: json.loads(json.dumps(value)) for key, value in context.items() if key in keep}
    shown["work"].pop("convention", None)
    shown["work"] = {"key": KEYS[context["work"]["name"]], **shown["work"]}
    for previous in shown.get("previous_reports", []):
        previous["has_written_chain"] = True
        previous.pop("text_head", None)
    for claim in shown.get("source_claims", []):
        if claim["source"] == "RWY":
            claim["what"] = "the Riwayat corpus's chain mentions as it read them (a machine reading)"
        if claim["source"] == "K6I":
            claim["what"] = "the K6 dataset's narrator index, in source order (the lexicon's names for those ids)"
        if claim["source"] == "THQ":
            claim["what"] = "Thaqalayn's English sanad"
    return shown


def chain_examples() -> list[str]:
    rows = load_examples()
    blocks: list[str] = []

    def add(title, row_id, groups, tail, notes, keep, fixes=None, ruling=False, status="read", context=None, expect_routes=None):
        row = rows[row_id]
        text = row["text"]
        context = context if context is not None else row["context"]
        output = {"id": f"ex{len(blocks) + 1}", "status": status, "groups": [{"levels": [[item(s) for s in level] for level in levels]} for levels in groups],
                  "shared_tail": None if tail is None else [[item(s) for s in level] for level in tail], "needs_ruling": ruling, "notes": notes, "fixes": fixes or []}
        shown_ctx = shown_context(context, keep)
        errors = validate_chain(output, text, output["id"], dict(context, work=dict(context["work"], key=shown_ctx["work"]["key"])))
        assert not errors, (title, errors)
        if expect_routes is not None:
            reading, _ = expand(output, text, dict(context, work=dict(context["work"], key=shown_ctx["work"]["key"])))
            assert len(reading["routes"]) == expect_routes, (title, len(reading["routes"]))
        shown = {"id": output["id"], "text": text, "context": shown_ctx}
        blocks.append(f"### Example {len(blocks) + 1}. {title}\n\nInput:\n```\n{json.dumps(shown, ensure_ascii=False)}\n```\n\nOutput:\n```\n{format_chain_output(output)}\n```\n")

    add("Sunni: two taḥwīl branches are two groups; what the text writes once after «قالا» is the shared tail (the tool adds the compiler)", "cx-0001",
        [[[("أبو بكر بن نافع", N_)], [("غندر", N_)]], [[("زهير بن حرب", N_)], [("عبد، الرحمن", N_)]]],
        [[("شعبة", N_)], [("بهذا الإسناد", B_)]], ["«- يعني ابن مهدي -» is a gloss and is left out; «وحدثنيه» is a verb"], ("work", "previous_reports"), expect_routes=2)
    # v3.2: real batch-001 reports the judge named, with the contexts the v3.2 builder wrote (examples/example-packets.jsonl)
    packets = batch_packets()

    def group_output(spec) -> dict:
        """A group is its list of levels, or ("variant", levels): a remark about another version."""
        if spec and spec[0] == "variant":
            return {"levels": [[item(s) for s in level] for level in spec[1]], "variant": True}
        return {"levels": [[item(s) for s in level] for level in spec]}

    def add_batch(title, report_id, groups, notes, keep, expect_routes=None, expect_variants=0):
        packet = packets[report_id]
        context = packet["context"]
        output = {"id": f"ex{len(blocks) + 1}", "status": "read", "groups": [group_output(spec) for spec in groups], "shared_tail": None,
                  "needs_ruling": False, "notes": notes, "fixes": []}
        errors = validate_chain(output, packet["text"], output["id"], context)
        assert not errors, (title, errors)
        if expect_routes is not None:
            reading, _ = expand(output, packet["text"], context)
            assert len(reading["routes"]) == expect_routes, (title, len(reading["routes"]))
            assert len(reading["variant_remarks"]) == expect_variants, (title, len(reading["variant_remarks"]))
        shown = {key: json.loads(json.dumps(value)) for key, value in context.items() if key in keep}
        shown["work"] = {key: value for key, value in shown["work"].items() if key in ("key", "tradition")}
        for previous in shown.get("previous_reports", []):
            previous.pop("source", None)
            previous.pop("text_head", None)
            previous.pop("number", None)
        input_json = json.dumps({"id": output["id"], "text": packet["text"], "context": shown}, ensure_ascii=False)
        blocks.append(chr(10).join([f"### Example {len(blocks) + 1}. {title}", "", "Input:", "```", input_json, "```", "", "Output:", "```", format_chain_output(output), "```", ""]))

    # v3.2: four real tranche-01 reports (the judge's reader-error classes), shortened; each reading validated against the shown text
    add_batch("A remark about another version is a `variant` group, never a route of this saying: «بمثل حديث سليمان بن بلال»", "t01-30fa50",
              [[[("محمد بن المثنى", N_)], [("عبد الوهاب", N_)], [("يحيى بن سعيد", N_)], [("عبد الله بن عامر بن ربيعة", N_)], [("عائشة", N_)]], ("variant", [[("سليمان بن بلال", N_)]])],
              ["«بمثل حديث سليمان بن بلال» names another version: a variant group, not a second route"], ("work",), expect_routes=1, expect_variants=1)
    add_batch("«قال وحدثني X» continues the chain from the man who speaks: the new route keeps the shared head (مسدد > يحيى > سفيان)", "t01-6d7565",
              [[[("مسدد", N_)], [("يحيى", N_)], [("سفيان", N_)], [("منصور", N_), ("سليمان", N_)], [("أبي وائل", N_)], [("أبي ميسرة", N_)], [("عبد الله", N_)]],
               [[("مسدد", N_)], [("يحيى", N_)], [("سفيان", N_)], [("واصل", N_)], [("أبي وائل", N_)], [("عبد الله", N_)]]],
              ["«قال وحدثني واصل»: سفيان speaks again, so the second route starts at مسدد, not at واصل"], ("work",), expect_routes=3)
    add_batch("A kunya, a comma and a name are ONE man: «أبو الطاهر، أحمد بن عمرو بن سرح»", "t01-05c2d0",
              [[[("أبو الطاهر، أحمد بن عمرو بن سرح", N_)], [("ابن وهب", N_)], [("يونس، بن يزيد", N_)], [("ابن شهاب", N_)], [("عروة بن الزبير", N_)], [("عائشة", N_)]]],
              ["a kunya, a comma and a name with no «و» between them are one man, one link"], ("work",), expect_routes=1)
    add_batch("The one who is asked and answers is a link: «قلت لعطاء ... قال ... فأخبرني ابن أبي مليكة»", "t01-0706da",
              [[[("حسن بن علي الحلواني", N_), ("محمد بن رافع", N_)], [("عبد الرزاق", N_)], [("ابن جريج", N_)], [("عطاء", N_)], [("ابن أبي مليكة", N_)], [("عائشة", N_)]]],
              ["عطاء is asked and answers, then ابن جريج goes on with «فأخبرني ابن أبي مليكة»: عطاء is a link before him"], ("work",), expect_routes=2)
    add_batch("al-Faqih: the asker is a link: «و كتب X إلى Y» is X, then the one he wrote to", "b1-4cbe02",
              [[[("البزنطي", N_)], [("أبي الحسن", "imam_in_text")]]], ["the writer of the question transmits the answer; the Imam is written as the report names him"], ("work",), expect_routes=1)
    add_batch("al-Faqih: «و سأله X» with the one asked only a pronoun: the asker, then the Imam the previous report writes (`inherited`, the last link)", "b1-05f29e",
              [[[("سماعة", N_)], [("INH", "أبي عبد الله", "prev1")]]], ["«وسأله» points at the Imam of prev1, the last name of its chain; the asker is written first"], ("work", "previous_reports"), expect_routes=1)
    add_batch("A saying with no isnad: `groups` is `[]`", "b1-2c405e", [], ["a saying of the compiler's own words, no transmitter, no name before it"], ("work",))
    return blocks


def fold_contains(haystack: str, needle: str) -> bool:
    return fold_v3(needle) in fold_v3(haystack)


def check_quotes() -> int:
    """Every fragment the rules quote stands in its pilot report."""
    count = 0
    for report_id, fragments in {**QUOTES, **RULE_FRAGMENTS}.items():
        for fragment in fragments:
            assert fold_contains(REPORTS[report_id]["text"], fragment), (report_id, fragment)
            count += 1
    return count


def check_readings() -> int:
    """Full readings of the pilot cases the rules teach: they validate against the real text and expand as the rule says."""
    def lv(*names):
        return [[{"surface": s, "kind": N_} for s in (n if isinstance(n, list) else [n])] for n in names]

    def out(report_id, groups, tail=None):
        return {"id": report_id, "status": "read", "groups": groups, "shared_tail": tail, "needs_ruling": False, "notes": [], "fixes": []}

    checks = 0
    contexts = {i: {"work": {"key": f"{r['tradition']}:{r['work']}", "tradition": r["tradition"], "compiler": {"head_of_every_chain": False}}} for i, r in REPORTS.items()}
    # (a) cr-0133: «سمعت أبا هريرة» ends both routes
    o = out("cr-0133", [{"levels": lv("سويد بن نصر", "عبد الله", "الأوزاعي", "أبو كثير")}, {"levels": lv("حميد بن مسعدة", "سفيان بن حبيب", "الأوزاعي", "أبو كثير")}], lv("أبا هريرة"))
    reading, errors = expand(o, REPORTS["cr-0133"]["text"], contexts["cr-0133"])
    assert not errors and not validate_chain(o, REPORTS["cr-0133"]["text"], "cr-0133", contexts["cr-0133"]), errors
    assert len(reading["routes"]) == 2 and all(r["links"][-1]["surface"].startswith("أبا هريرة") for r in reading["routes"]); checks += 1
    # (b) cr-0177: عثمان, who speaks the saying, is the last link after هانئ
    o = out("cr-0177", [{"levels": lv("هناد", "يحيى بن معين", "هشام بن يوسف", "عبد الله بن بحير", "هانئا، مولى عثمان", "عثمان")}])
    reading, errors = expand(o, REPORTS["cr-0177"]["text"], contexts["cr-0177"])
    assert not errors and not validate_chain(o, REPORTS["cr-0177"]["text"], "cr-0177", contexts["cr-0177"]), errors
    last = reading["routes"][0]["links"][-1]
    assert last["surface"] == "عثمان" and last["start"] > REPORTS["cr-0177"]["text"].index("مولى عثمان") + 10; checks += 1
    # (e) cr-0144: the short and the full form are one link; cr-0200: two men are two links
    o = out("cr-0144", [{"levels": [[{"surface": "يحيى بن حبيب", "kind": N_}, {"surface": "محمد بن عبد الأعلى", "kind": N_}], [{"surface": "المعتمر", "kind": N_}], [{"surface": "معتمر بن سليمان", "kind": N_}],
                                      [{"surface": "أبي", "kind": "relation"}], [{"surface": "أبو نضرة", "kind": N_}], [{"surface": "جابر بن عبد الله", "kind": N_}]]}])
    reading, errors = expand(o, REPORTS["cr-0144"]["text"], contexts["cr-0144"])
    assert not errors and all(sum(1 for l in r["links"] if l["kind"] == N_) == 4 for r in reading["routes"]) and len(reading["routes"]) == 2; checks += 1
    o = out("cr-0200", [{"levels": lv("محمد بن الحسن", "محمد بن الحسن الصفار", "محمد بن عيسى")}])
    reading, errors = expand(o, REPORTS["cr-0200"]["text"], contexts["cr-0200"])
    assert not errors and sum(l["kind"] == N_ for l in reading["routes"][0]["links"]) == 3 and not reading["tool_notes"]; checks += 1
    # (g) cr-0202: one link for the man the answer names
    o = out("cr-0202", [{"levels": lv("مسلم", "شعبة", "الشيباني", "الشعبي", "ابن عباس")}])
    reading, errors = expand(o, REPORTS["cr-0202"]["text"], contexts["cr-0202"])
    assert not errors and sum(l["kind"] == N_ for l in reading["routes"][0]["links"]) == 5; checks += 1
    # (c) cr-0136: the poem's isnad is not a route; cr-0205: the remark naming another transmitter is a `variant` group
    o = out("cr-0136", [{"levels": lv("أبو حفص عمر بن محمد المعروف بابن الزيات", "علي بن مهرويه القزويني")}])
    assert not validate_chain(o, REPORTS["cr-0136"]["text"], "cr-0136", contexts["cr-0136"]); checks += 1
    o = out("cr-0205", [{"levels": [[{"surface": "يحيى بن موسى", "kind": N_}, {"surface": "محمود بن غيلان", "kind": N_}], [{"surface": "الوليد بن مسلم", "kind": N_}], [{"surface": "الأوزاعي", "kind": N_}],
                                      [{"surface": "يحيى بن أبي كثير", "kind": N_}], [{"surface": "أبي سلمة", "kind": N_}], [{"surface": "أبي هريرة", "kind": N_}]]},
                        {"variant": True, "levels": lv("شيبان", "يحيى بن أبي كثير")}])
    reading, errors = expand(o, REPORTS["cr-0205"]["text"], contexts["cr-0205"])
    assert not errors and [r["variant"] for r in reading["routes"]] == [False, False] and len(reading["variant_remarks"]) == 1; checks += 1
    # (d) cr-0008: the names stand in prev3; the reading takes them as inherited from prev3
    previous = [{"ref": "prev1", "number": "348", "has_written_chain": False, "chain_text": "348 - وَبِهذَا الإسناد"}, {"ref": "prev2", "number": "347", "has_written_chain": False, "chain_text": "347 - وَبِهذَا الإسناد"},
                {"ref": "prev3", "number": "346", "has_written_chain": True, "chain_text": "346 - حَدَّثَنا مُحَمَّدِ بْنِ أَحْمَدِ بْنِ الحُسَيْنِ بْنِ يُـوسِف البَـغدْادي قـالَ: حَدَّثَنا عَلِيُّ بْنُ مُوسَى"}]
    context = dict(contexts["cr-0008"], previous_reports=previous)
    o = out("cr-0008", [{"levels": [[{"surface": "مُحَمَّدِ بْنِ أَحْمَدِ بْنِ الحُسَيْنِ بْنِ يُـوسِف", "kind": "inherited", "from": "prev3"}]]}])
    assert not validate_chain(o, REPORTS["cr-0008"]["text"], "cr-0008", context), validate_chain(o, REPORTS["cr-0008"]["text"], "cr-0008", context); checks += 1
    return checks


def main() -> None:
    quotes = check_quotes()
    readings = check_readings()
    body = (V3 / "tools" / "chain_body_v3_2.md").read_text(encoding="utf-8")
    (V3 / "examples").mkdir(exist_ok=True)
    v1_body = (ROOT / "tools" / "prompt_body.md").read_text(encoding="utf-8")
    conventions = v1_body.split("## How each tradition writes its chains")[1].split("## Worked examples")[0].strip()
    examples = chain_examples()
    text = body.replace("{{CONVENTIONS}}", conventions).replace("{{EXAMPLES}}", "\n".join(examples).rstrip("\n"))
    data = text.replace("\r\n", "\n").encode("utf-8")
    v3_chars = len((ROOT / "v3_1" / "prompt-v3_1.md").read_text(encoding="utf-8"))
    assert len(text) <= v3_chars, f"prompt-v3.2 is {len(text)} characters, prompt-v3.1 is {v3_chars}: replace, do not append"
    (V3 / "prompt-v3_2.md").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    record = {"reader": "chain-reader", "version": "3.2.0", "base_version": "3.1.0", "status": "draft: no model has run it", "output_format": "shura-chain-reader-output/3", "file": "prompt-v3_2.md", "sha256": digest, "chars": len(text),
              "prompt_v3_1_chars": v3_chars,
              "build_checks": {"examples_validated": len(examples), "pilot_fragments_found": quotes, "pilot_readings_validated": readings},
              "inputs_sha256": {"tools/chain_body_v3_2.md": hashlib.sha256((V3 / "tools" / "chain_body_v3_2.md").read_bytes()).hexdigest(), "tools/make_prompt_v3_2.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                "context/examples-v2/chain-contexts.jsonl": hashlib.sha256((CTX / "examples-v2" / "chain-contexts.jsonl").read_bytes()).hexdigest(),
                                "tools/prompt_body.md": hashlib.sha256((ROOT / "tools" / "prompt_body.md").read_bytes()).hexdigest()}}
    (V3 / "prompt-v3_2.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("prompt-v3_2.md", digest, len(text), "chars (v3.1:", v3_chars, ")", quotes, "fragments,", readings, "readings")


if __name__ == "__main__":
    main()
