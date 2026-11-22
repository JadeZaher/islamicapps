"""Build v3_4/prompt-v3_4.md (chain reader v3.4: the owner's third-round rulings) and record its hash; every worked example and every quoted fragment is validated here.

    python -B -X utf8 v3_4/tools/make_prompt_v3_4.py            (from chain-reader/; run tools/build_example_packets_v3_4.py first)

The body is tools/chain_body_v3_4.md (v3.2's body with rule 4a, the encounter paragraph of rule 6, the narrowed rule 11 and owner rulings 5-6), the tradition conventions are v1's
block (../tools/prompt_body.md, read-only), the examples are v2's cx-0001 (shown with its work only) and five real reports (examples/example-packets.jsonl). v3.2's examples 2 («بمثل حديث سليمان بن بلال»), 4 (kunya, comma, name),
5 (the one asked answers), 6 (al-Faqih «و كتب X إلى Y») and 8 (`groups: []`) are dropped: their rules stay in the text with their quotes (rules 4, 5, 6, 7, 10). Build checks (the v3.2 generator's, v3_2/tools/make_prompt_v3_2.py, reused):
 - every example output passes validate_v3_4 against its real text and expands to the stated routes, variant remarks and sayings;
 - every fragment the v3.2 rules quote stands in its pilot report, and every fragment the new rules quote stands in its tranche report and in the prompt;
 - the v3.2 generator's eight pilot readings still validate under v3.2 (the tests check that v3.4 accepts unlabelled outputs alike);
 - the prompt is not longer than v3.2's (v3_2/prompt-v3_2.md, 27,023 letters): replace, do not append.
Writes prompt-v3_4.md (LF) and prompt-v3_4.json {version, sha256, chars, inputs}. See v3_4/AGENTS.md §prompt.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V34 = HERE.parent
ROOT = V34.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_2" / "tools"), str(V34)):
    if path not in sys.path:
        sys.path.insert(0, path)
import make_prompt_v3_2 as v32  # noqa: E402  (helpers and the pilot checks; it writes nothing on import)
from expand_v3_4 import expand  # noqa: E402
from norm_v3_2 import fold_v3  # noqa: E402
from validate_v3_4 import validate_chain  # noqa: E402

N_, R_, U_, B_, I_ = "narrator", "relation", "unnamed", "back_reference", "imam_in_text"
# fragments the NEW rules quote, by tranche report ('…' splits a quote into fragments that must each stand in the report)
NEW_QUOTES = {
    ("02", "t02-1061e3"): ["تابعه قتيبة حدثنا العنقزي عن حنظلة"],
    ("01", "t01-520f51"): ["قال الزهري وأخبرني عروة، عن عائشة، أنها لم تكن تفعل ذلك"],
    ("01", "t01-a20cb6"): ["كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى، فنظر إلى الناس فقال"],
    ("01", "t01-755db5"): ["كنت عند أبي الحسن موسى بن جعفر", "وعنده علي ابنه، فقال: يا علي"],
}


def example_packets() -> dict[str, dict]:
    path = V34 / "examples" / "example-packets.jsonl"
    return {row["id"]: row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}


def group_output(spec) -> dict:
    """A group is its list of levels, ("variant", levels), or ("saying", n, opens, levels)."""
    if spec and spec[0] == "variant":
        return {"levels": [[v32.item(s) for s in level] for level in spec[1]], "variant": True}
    if spec and spec[0] == "saying":
        return {"levels": [[v32.item(s) for s in level] for level in spec[3]], "saying": spec[1], "saying_opens": spec[2]}
    return {"levels": [[v32.item(s) for s in level] for level in spec]}


def format_output(output: dict) -> str:
    """v3.2's layout, with `variant` and `saying` / `saying_opens` printed after a group's levels."""
    lines = ['{"id": ' + json.dumps(output["id"]) + ', "status": ' + json.dumps(output["status"]) + ",", ' "groups": [']
    for g, group in enumerate(output["groups"]):
        lines.append('  {"levels": [')
        lines += v32.fmt_levels(group["levels"], "    ")
        extra = (', "variant": true' if group.get("variant") else "") + (f', "saying": {group["saying"]}, "saying_opens": {json.dumps(group["saying_opens"], ensure_ascii=False)}' if "saying" in group else "")
        lines.append("  ]" + extra + "}" + ("," if g < len(output["groups"]) - 1 else ""))
    lines.append(" ],")
    lines.append(' "shared_tail": null,' if output["shared_tail"] is None else ' "shared_tail": [')
    if output["shared_tail"] is not None:
        lines += v32.fmt_levels(output["shared_tail"], "  ")
        lines.append(" ],")
    lines.append(f' "needs_ruling": {json.dumps(output["needs_ruling"])},')
    lines.append(' "notes": ' + json.dumps(output["notes"], ensure_ascii=False) + ",")
    lines.append(' "fixes": ' + json.dumps(output["fixes"], ensure_ascii=False) + "}")
    return "\n".join(lines)


def chain_examples() -> list[str]:
    blocks: list[str] = []
    rows = v32.load_examples()
    # example 1: v2's cx-0001, exactly as v3.2 builds it
    row = rows["cx-0001"]
    context = row["context"]
    shown_ctx = v32.shown_context(context, ("work",))
    shown_ctx["work"] = {key: shown_ctx["work"][key] for key in ("key", "tradition")}          # v3.4: the work only (budget); v3.2 showed its previous report too
    output = {"id": "ex1", "status": "read", "groups": [group_output([[("أبو بكر بن نافع", N_)], [("غندر", N_)]]), group_output([[("زهير بن حرب", N_)], [("عبد، الرحمن", N_)]])],
              "shared_tail": [[v32.item(("شعبة", N_))], [v32.item(("بهذا الإسناد", B_))]], "needs_ruling": False, "notes": ["«- يعني ابن مهدي -» is a gloss and is left out; «وحدثنيه» is a verb"], "fixes": []}
    full_context = dict(context, work=dict(context["work"], key=shown_ctx["work"]["key"]))
    assert not validate_chain(output, row["text"], "ex1", full_context)
    reading, _ = expand(output, row["text"], full_context)
    assert len(reading["routes"]) == 2
    blocks.append(f"### Example 1. Sunni: two taḥwīl branches are two groups; what the text writes once after «قالا» is the shared tail (the tool adds the compiler)\n\nInput:\n```\n"
                  f"{json.dumps({'id': 'ex1', 'text': row['text'], 'context': shown_ctx}, ensure_ascii=False)}\n```\n\nOutput:\n```\n{format_output(output)}\n```\n")
    packets = example_packets()

    def add(title, report_id, groups, notes, keep, routes, variants=0, sayings=0, last=None):
        packet = packets[report_id]
        context = packet["context"]
        output = {"id": f"ex{len(blocks) + 1}", "status": "read", "groups": [group_output(spec) for spec in groups], "shared_tail": None, "needs_ruling": False, "notes": notes, "fixes": []}
        errors = validate_chain(output, packet["text"], output["id"], context)
        assert not errors, (title, errors)
        reading, _ = expand(output, packet["text"], context)
        assert (len(reading["routes"]), len(reading["variant_remarks"]), len(reading["sayings"])) == (routes, variants, sayings), (title, len(reading["routes"]), len(reading["variant_remarks"]), len(reading["sayings"]))
        if last is not None:
            assert all(r["links"][-1]["surface"] == last for r in reading["routes"]), (title, [r["links"][-1]["surface"] for r in reading["routes"]])
        shown = {key: json.loads(json.dumps(value)) for key, value in context.items() if key in keep}
        shown["work"] = {key: value for key, value in shown["work"].items() if key in ("key", "tradition")}
        for previous in shown.get("previous_reports", []):
            for key in ("source", "text_head", "number"):
                previous.pop(key, None)
        input_json = json.dumps({"id": output["id"], "text": packet["text"], "context": shown}, ensure_ascii=False)
        blocks.append("\n".join([f"### Example {len(blocks) + 1}. {title}", "", "Input:", "```", input_json, "```", "", "Output:", "```", format_output(output), "```", ""]))

    add("A mutabaʿa is a remark about another version: a `variant` group, never a route («تابعه قتيبة حدثنا العنقزي عن حنظلة»)", "t02-1061e3",
        [[[("عبيد الله بن موسى", N_)], [("حنظلة", N_)], [("سالم", N_)], [("ابن عمر", N_)]], ("variant", [[("قتيبة", N_)], [("العنقزي", N_)], [("حنظلة", N_, 2)]])],
        ["«تابعه قتيبة ...»: another man followed عبيد الله بن موسى; a remark, not a route"], ("work",), routes=1, variants=1)
    add("«قال وحدثني X» continues the chain from the man who speaks: the new route keeps the shared head (مسدد > يحيى > سفيان)", "t01-6d7565",
        [[[("مسدد", N_)], [("يحيى", N_)], [("سفيان", N_)], [("منصور", N_), ("سليمان", N_)], [("أبي وائل", N_)], [("أبي ميسرة", N_)], [("عبد الله", N_)]],
         [[("مسدد", N_)], [("يحيى", N_)], [("سفيان", N_)], [("واصل", N_)], [("أبي وائل", N_)], [("عبد الله", N_)]]],
        ["«قال وحدثني واصل»: سفيان speaks again, so the second route starts at مسدد, not at واصل"], ("work",), routes=3)
    add("A narrated encounter: the Imam speaks in the narrator's story, so he is the last link", "t01-a20cb6",
        [[[("أبى", R_)], [("سعد بن عبد الله", N_)], [("بإسناد يرفعه", U_)], [("منصور الصيقل", N_)], [("أبي عبد الله", I_)]]],
        ["the Imam speaks in منصور's story: the last link (owner ruling 5)"], ("work",), routes=1, last="أبي عبد الله")
    add("Two sayings, each with its own isnad: both are stored, each group labelled with its saying", "t01-520f51",
        [("saying", 1, "أن أبا بكر، وعمر، وابن، عمر كانوا ينزلون الأبطح", [[("عبد بن حميد", N_)], [("عبد الرزاق", N_)], [("معمر", N_)], [("الزهري", N_)], [("سالم", N_)]]),
         ("saying", 2, "أنها لم تكن تفعل ذلك", [[("عبد بن حميد", N_)], [("عبد الرزاق", N_)], [("معمر", N_)], [("الزهري", N_)], [("عروة", N_)], [("عائشة", N_)]])],
        ["«قال الزهري وأخبرني عروة» opens a second saying with its own isnad; its group keeps the head up to الزهري"], ("work",), routes=2, sayings=2)
    add("al-Faqih: «و سأله X» with the one asked only a pronoun: the asker, then the Imam the previous report writes (`inherited`, the last link)", "b1-05f29e",
        [[[("سماعة", N_)], [("INH", "أبي عبد الله", "prev1")]]], ["«وسأله» points at the Imam of prev1, the last name of its chain; the asker is written first"], ("work", "previous_reports"), routes=1)
    return blocks


def tranche_text(tranche: str, report_id: str) -> str:
    for path in sorted((ROOT / "tranches" / f"tranche-{tranche}" / "packets").glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if report_id in line:
                row = json.loads(line)
                if row["id"] == report_id:
                    return row["text"]
    raise KeyError(report_id)


def check_new_quotes(prompt: str) -> int:
    """Every fragment the new rules quote stands in its real report and in the built prompt (folded)."""
    count = 0
    for (tranche, report_id), fragments in NEW_QUOTES.items():
        text = tranche_text(tranche, report_id)
        for fragment in fragments:
            assert fold_v3(fragment) in fold_v3(text), (report_id, fragment)
            assert fold_v3(fragment) in fold_v3(prompt), ("not in the prompt", report_id, fragment)
            count += 1
    return count


def main() -> None:
    pilot_quotes = v32.check_quotes()
    pilot_readings = v32.check_readings()
    body = (HERE / "chain_body_v3_4.md").read_text(encoding="utf-8")
    v1_body = (ROOT / "tools" / "prompt_body.md").read_text(encoding="utf-8")
    conventions = v1_body.split("## How each tradition writes its chains")[1].split("## Worked examples")[0].strip()
    examples = chain_examples()
    text = body.replace("{{CONVENTIONS}}", conventions).replace("{{EXAMPLES}}", "\n".join(examples).rstrip("\n"))
    new_quotes = check_new_quotes(text)
    data = text.replace("\r\n", "\n").encode("utf-8")
    budget = len((ROOT / "v3_2" / "prompt-v3_2.md").read_text(encoding="utf-8"))
    assert len(text) <= budget, f"prompt-v3.4 is {len(text)} characters, prompt-v3.2 is {budget}: replace, do not append"
    (V34 / "prompt-v3_4.md").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    inputs = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in {
        "v3_4/tools/chain_body_v3_4.md": HERE / "chain_body_v3_4.md", "v3_4/tools/make_prompt_v3_4.py": Path(__file__), "v3_4/examples/example-packets.jsonl": V34 / "examples" / "example-packets.jsonl",
        "context/examples-v2/chain-contexts.jsonl": ROOT / "context" / "examples-v2" / "chain-contexts.jsonl", "tools/prompt_body.md": ROOT / "tools" / "prompt_body.md"}.items()}
    record = {"reader": "chain-reader", "version": "3.4.0", "base_version": "3.2.0", "status": "not yet run by a model", "output_format": "shura-chain-reader-output/3.4", "file": "prompt-v3_4.md",
              "sha256": digest, "chars": len(text), "budget_chars_prompt_v3_2": budget, "owner_rulings": "2026-11-22, third round: (a) narrated encounter, (b) two sayings",
              "build_checks": {"examples_validated": len(examples), "pilot_fragments_found": pilot_quotes, "pilot_readings_validated": pilot_readings, "new_rule_fragments_found": new_quotes},
              "inputs_sha256": inputs}
    (V34 / "prompt-v3_4.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("prompt-v3_4.md", digest, len(text), "chars (budget", budget, ")", pilot_quotes, "pilot fragments,", new_quotes, "new fragments,", pilot_readings, "readings,", len(examples), "examples")


if __name__ == "__main__":
    main()
