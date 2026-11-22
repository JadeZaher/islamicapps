"""Build prompt-v2.md (chain reader) and prompt-v2-text.md (text/metadata checker); every worked example is validated here.

    python -I -X utf8 tools/make_prompt_v2.py

v1's body (../tools/prompt_body.md) is reused with small replacements, then chain_addendum.md and the examples are added.
Contexts for the examples are real, built by build_context.cjs for reports outside the pilot (examples-v2/*.jsonl).
Design notes: ../AGENTS.md (prompt v2). Never edits v1.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTEXT = HERE.parent
ROOT = CONTEXT.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(CONTEXT))
import make_prompt as v1p  # noqa: E402  (locate, EXAMPLES, format_output; never edited)
from validate_v2 import validate_chain, validate_text  # noqa: E402
from expand import expand  # noqa: E402



def load(name: str) -> dict[str, dict]:
    return {row["id"]: row for row in (json.loads(line) for line in (CONTEXT / "examples-v2" / name).read_text(encoding="utf-8").splitlines() if line.strip())}


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
        lines.append("  ]}" + ("," if g < len(output["groups"]) - 1 else ""))
    lines.append(" ],")
    if output["shared_tail"] is None:
        lines.append(' "shared_tail": null,')
    else:
        lines.append(' "shared_tail": [')
        lines += fmt_levels(output["shared_tail"], "  ")
        lines.append(" ],")
    lines.append(f' "needs_ruling": {json.dumps(output["needs_ruling"])},')
    lines.append(' "notes": ' + json.dumps(output["notes"], ensure_ascii=False) + ",")
    lines.append(' "fixes": ' + json.dumps(output["fixes"], ensure_ascii=False) + "}")
    return "\n".join(lines)


def shown_context(context: dict, drop: tuple[str, ...]) -> dict:
    return {key: value for key, value in context.items() if key not in drop}


def chain_examples() -> list[str]:
    rows = load("chain-contexts.jsonl")
    blocks = []

    def add(title, row_id, groups, tail, notes, fixes=None, ruling=False, status="read", drop=("correspondences", "sources_absent", "name_facts", "archive_flags"), context=None, expect_routes=None):
        row = rows[row_id]
        text = row["text"]
        context = context if context is not None else row["context"]
        output = {"id": f"ex{len(blocks) + 1}", "status": status, "groups": [{"levels": [[item(s) for s in level] for level in levels]} for levels in groups],
                  "shared_tail": None if tail is None else [[item(s) for s in level] for level in tail], "needs_ruling": ruling, "notes": notes, "fixes": fixes or []}
        errors = validate_chain(output, text, output["id"], context)
        assert not errors, (title, errors)
        if expect_routes is not None:
            reading, _ = expand(output, text, context)
            assert len(reading["routes"]) == expect_routes, (title, len(reading["routes"]))
        shown = {"id": output["id"], "text": text, "context": shown_context(context, drop)}
        shown["context"].get("work", {}).pop("convention", None)
        blocks.append(f"### Example {len(blocks) + 1}. {title}\n\nInput:\n```\n{json.dumps(shown, ensure_ascii=False)}\n```\n\nOutput:\n```\n{format_chain_output(output)}\n```\n")

    N_, U_ = "narrator", "unnamed"
    add("Sunni: two taḥwīl branches are two groups; what the text writes once after «قالا» is the shared tail (the tool adds the compiler)", "cx-0001",
        [[[("أبو بكر بن نافع", N_)], [("غندر", N_)]], [[("زهير بن حرب", N_)], [("عبد، الرحمن", N_)]]],
        [[("شعبة", N_)], [("بهذا الإسناد", "back_reference")]], ["«- يعني ابن مهدي -» is a gloss and is left out; «وحدثنيه» is a verb"], expect_routes=2)
    add("al-Kafi: co-transmitters share a level; one group is enough", "cx-0002",
        [[[("عدة من أصحابنا", U_)], [("سهل بن زياد", N_), ("أحمد بن محمد", N_)], [("ابن محبوب", N_)], [("عبد الله بن سنان", N_)], [("أبي عبد الله", N_)]]], None,
        ["the blessing after أبي عبد الله is not part of the name"], drop=("correspondences", "sources_absent", "archive_flags"), expect_routes=2)
    add("al-Kafi: the Imam named only after the chain is the last link, kind `imam_in_text`", "cx-0003",
        [[[("علي بن إبراهيم", N_)], [("محمد بن عيسى", N_)], [("يونس", N_)], [("معاوية بن وهب", N_)], [("أبا عبد الله", "imam_in_text")]]], None,
        ["the Imam is named only in «سألت أبا عبد الله»; written as the report names him"])
    add("Imami: «وبهذا الإسناد» takes over names of the previous report (`inherited`, citing prev1)", "cx-0004",
        [[[("INH", "أحمد بن إدريس", "prev1")], [("INH", "علي بن محمد", "prev1")], [("الفضل بن شاذان", N_)], [("عبد الرحمن بن أبي نجران", N_)], [("علي بن أبي حمزة", N_)], [("أبي بصير", N_)], [("أبي جعفر", N_)]]], None,
        ["«وبهذا الإسناد» stands for أحمد بن إدريس، علي بن محمد of the previous report, up to the name the text repeats (الفضل بن شاذان)"],
        drop=("correspondences", "sources_absent", "archive_flags"))
    flagged = json.loads(json.dumps(rows["cx-0004"]["context"]))
    flagged.pop("previous_reports", None)
    flagged["needs_previous_report"] = True
    add("The same report when no previous report could be supplied: no short chain, `cannot_read_without_previous_report`", "cx-0004", [], None,
        ["the report opens with «وبهذا الإسناد»; its chain begins in the previous report, which the packet does not carry"], status="cannot_read_without_previous_report",
        drop=("correspondences", "sources_absent", "archive_flags"), context=flagged)
    add("al-Kafi: «عنه» is a back_reference; two branches that meet (alternatives in a level, a shared tail)", "cx-0005",
        [[[("عنه", "back_reference")], [("أحمد بن محمد", N_)]], [[("علي بن إبراهيم", N_)], [("أبيه", "relation")]]],
        [[("ابن أبي عمير", N_)], [("عمر بن شهاب", N_), ("سليم الفراء", N_)], [("رجل", U_)], [("أبي عبد الله", N_)]],
        ["four routes: two heads x two names after ابن أبي عمير; «جميعا» joins them at ابن أبي عمير"], drop=("correspondences", "sources_absent", "name_facts"), expect_routes=4)
    fixes = [{"kind": "chain_differs_from_source", "reason": "K6I index stops at عبد الله بن يزيد although the text goes on to an unnamed man and سرق.",
              "evidence": [{"source": "text", "quote": "عن رجل، من أهل مصر عن سرق"}, {"source": "K6I", "quote": "عبد الله بن يزيد المدني مولى المنبعث"}], "confidence": "high"}]
    add("Sunni: a source stops early; the reading follows the text and a fix is filed", "cx-0007",
        [[[("أبو بكر بن أبي شيبة", N_)], [("يزيد بن هارون", N_)], [("جويرية بن أسماء", N_)], [("عبد الله بن يزيد", N_)], [("رجل، من أهل مصر", U_)], [("سرق", N_)]]], None,
        ["«- مولى المنبعث -» is a gloss and is left out"], fixes=fixes, drop=("correspondences", "sources_absent"), expect_routes=1)
    return blocks


def text_examples() -> list[str]:
    rows = load("text-contexts.jsonl")
    blocks = []

    def add(title: str, row_id: str, output: dict, keep=("work", "text_and_metadata")):
        row = rows[row_id]
        output["id"] = f"ex{len(blocks) + 1}"
        errors = validate_text(output, row["text"], output["id"], row["context"])
        assert not errors, (title, errors)
        context = shown_context(row["context"], tuple(k for k in row["context"] if k not in keep))
        context["work"] = {k: v for k, v in context["work"].items() if k in ("name", "tradition", "book", "chapter", "report_number")}
        tm = dict(context["text_and_metadata"]); tm.pop("lookup", None); tm.pop("source_file_hashes", None); tm.pop("stored_text_sha256", None)
        context["text_and_metadata"] = tm
        shown = {"id": output["id"], "text": row["text"], "context": context}
        blocks.append(f"### Example {len(blocks) + 1}. {title}\n\nInput:\n```\n{json.dumps(shown, ensure_ascii=False)}\n```\n\nOutput:\n```\n{json.dumps(output, ensure_ascii=False, indent=1)}\n```\n")

    add("Two local copies agree; the metadata matches Thaqalayn's", "cx-0002", {
        "text_check": {"status": "matches", "compared": ["RWY", "THQ"], "differences": []},
        "metadata_check": {"status": "matches", "compared": ["THQ", "RWY"], "differences": []}, "fixes": [],
        "notes": ["page is not stored and no source gives it"]})
    add("No second local copy: say so; nothing is guessed", "cx-0001", {
        "text_check": {"status": "not_checked", "compared": [], "differences": [], "reason": "no second local copy of this text exists and no web access in this run"},
        "metadata_check": {"status": "not_checked", "compared": [], "differences": [], "reason": "no local source gives volume, page, url or grading, and no web access in this run"}, "fixes": [], "notes": []})
    add("A copy differs: both readings are quoted, a fix is filed, the stored Arabic is not changed", "cx-0008", {
        "text_check": {"status": "differs", "compared": ["HKG", "RWY"], "differences": [
            {"ours": "أن ينتهك شىء من محارم الله", "theirs": "ينتهك شيء منمحارم الله", "source": "HKG"}]},
        "metadata_check": {"status": "not_checked", "compared": [], "differences": [], "reason": "the local copies number this report 4303, another edition's numbering; no web access to settle it"},
        "fixes": [{"kind": "text_differs_from_source", "reason": "HKG's copy glues «من» to «محارم»; ours reads «من محارم». The glue looks like HKG's defect; both readings are filed.",
                   "evidence": [{"source": "text", "quote": "أن ينتهك شىء من محارم الله"}, {"source": "HKG", "quote": "شيء منمحارم الله"}], "confidence": "low"}],
        "notes": ["both copies also continue with a second isnad after the saying; that is their segmentation"]})
    return blocks


def build_chain_prompt() -> str:
    v1_body = (ROOT / "tools" / "prompt_body.md").read_text(encoding="utf-8")
    conventions = v1_body.split("## How each tradition writes its chains")[1].split("## Worked examples")[0].strip()
    body = (CONTEXT / "tools" / "chain_body.md").read_text(encoding="utf-8")
    return body.replace("{{CONVENTIONS}}", conventions).replace("{{EXAMPLES}}", "\n".join(chain_examples()).rstrip("\n"))


def build_text_prompt() -> str:
    return (CONTEXT / "tools" / "text_body.md").read_text(encoding="utf-8").replace("{{EXAMPLES}}", "\n".join(text_examples()).rstrip("\n"))


def main() -> None:
    for name, text in (("prompt-v2.md", build_chain_prompt()), ("prompt-v2-text.md", build_text_prompt())):
        data = text.replace("\r\n", "\n").encode("utf-8")
        (CONTEXT / name).write_bytes(data)
        print(name, hashlib.sha256(data).hexdigest(), len(text), "chars")


if __name__ == "__main__":
    main()
