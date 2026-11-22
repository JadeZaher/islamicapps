"""Write prompt.md from prompt_body.md and examples taken from real, audit-judged reports (see ../AGENTS.md §prompt).

  node --env-file=.env.local fetch_labelled.cjs <ids.json> <fetched.json>     # once; the examples' hadith ids are in EXAMPLES
  python make_prompt.py --fetched fetched.json

Offsets in the examples are computed here from the surfaces, so they are exact. The example reports are written to
../examples/examples.json and are left out of the pilot set (build_pilot.py reads that file).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from validate import validate  # noqa: E402

N, U, B, R = "narrator", "unnamed", "back_reference", "relation"
CHAIN_FIELD_WORKS = ("ahmad", "darimi", "muwatta")

# Each route: ("surface", kind) found at/after the route's cursor, or ("=", route, link) the same occurrence as an earlier route.
EXAMPLES = [
    dict(title="1. Sunni, taḥwīl «ح» and «قالا»: two routes that meet at one name (Muslim 11548; the audit found a route missing a link)",
         hadith="hadith:k6:11548", anchor="غير أن في",
         routes=[[("أبو بكر بن نافع", N), ("غندر", N), ("شعبة", N), ("بهذا الإسناد", B)],
                 [("زهير بن حرب", N), ("عبد، الرحمن", N), ("=", 0, 2), ("=", 0, 3)]],
         tails=[2, 2], notes=["«- يعني ابن مهدي -» is a gloss and is left out; «وحدثنيه» is a verb"]),
    dict(title="2. Sunni, a source named after «أنه سمع» is a link (Bukhari 1326; the audit found it dropped)",
         hadith="hadith:k6:1326", anchor="قام رسول الله",
         routes=[[("يحيى بن سليمان", N), ("ابن وهب", N), ("يونس", N), ("ابن شهاب", N), ("عروة بن الزبير", N), ("أسماء بنت أبي بكر", N)]],
         tails=[None], notes=[]),
    dict(title="3. Sunni, an unnamed transmitter and a gloss (Ibn Majah 32666)",
         hadith="hadith:k6:32666", anchor="أن النبي",
         routes=[[("أبو بكر بن أبي شيبة", N), ("يزيد بن هارون", N), ("جويرية بن أسماء", N), ("عبد الله بن يزيد", N),
                  ("رجل، من أهل مصر", U), ("سرق", N)]],
         tails=[None], notes=["«- مولى المنبعث -» is a gloss and is left out"]),
    dict(title="4. Ahmad: the source's chain field, two routes written out in full, then the matn (pc_36685)",
         hadith="hadith:pure-canon:pc_36685", anchor="أهون أهل النار",
         routes=[[("حسن", N), ("حماد ابن سلمة", N), ("ثابت البناني", N), ("أبي عثمان النهدي", N), ("ابن عباس", N)],
                 [("عفان", N), ("حماد ابن سلمة", N), ("ثابت البناني", N), ("أبي عثمان النهدي", N), ("ابن عباس", N)]],
         tails=[None, None], notes=["«المعنى» after عفان is a gloss and is left out"]),
    dict(title="5. al-Kafi: «عدة من أصحابنا», co-transmitters and «جميعا» (Thaqalayn al-Kafi report 39)",
         hadith="hadith:thaqalayn:217ebfa4b4c33529fb0fe2b1", anchor="كل شي",
         routes=[[("عدة من أصحابنا", U), ("سهل بن زياد", N), ("ابن محبوب", N), ("عبد الله بن سنان", N), ("أبي عبد الله", N)],
                 [("=", 0, 0), ("أحمد بن محمد", N), ("=", 0, 2), ("=", 0, 3), ("=", 0, 4)]],
         tails=[2, 2], notes=["the blessing after أبي عبد الله is not part of the name"]),
    dict(title="6. al-Kafi: «عنه» at the start, two levels of co-transmitters, a relation, an unnamed link (Thaqalayn al-Kafi report 6)",
         hadith="hadith:thaqalayn:1b7b115537bb2bf61aad043d", anchor="من قال هذا",
         routes=[[("عنه", B), ("أحمد بن محمد", N), ("ابن أبي عمير", N), ("عمر بن شهاب", N), ("رجل", U), ("أبي عبد الله", N)],
                 [("=", 0, 0), ("=", 0, 1), ("=", 0, 2), ("سليم الفراء", N), ("=", 0, 4), ("=", 0, 5)],
                 [("علي بن إبراهيم", N), ("أبيه", R), ("=", 0, 2), ("=", 0, 3), ("=", 0, 4), ("=", 0, 5)],
                 [("=", 2, 0), ("=", 2, 1), ("=", 0, 2), ("=", 1, 3), ("=", 0, 4), ("=", 0, 5)]],
         tails=[2, 2, 2, 2], notes=["four routes: two heads x two names after ابن أبي عمير; «جميعا» joins them at ابن أبي عمير"]),
    dict(title="7. al-Faqih: «سأل X أخاه Y» is two links, the asker first (Faqih 397; the audit found them merged)",
         hadith="hadith:thaqalayn:6170bd3f7dd702e5d70ec60f", anchor="عن الميت",
         routes=[[("علي بن جعفر", N), ("موسى بن جعفر", N)]],
         tails=[None], notes=["«أخاه» (his brother) is a relation word directly before the name, so only the name is a link; the leading number is not a name"]),
    dict(title="8. al-Rabi': «عنه» points back to the previous name (Rabi' 369; the audit found the pronoun dropped)",
         hadith="hadith:openiti:ibadi:rabi_0369|369|V01P093", anchor="أضاف رسول الله",
         routes=[[("أبو عبيدة", N), ("عنه", B)]],
         tails=[None], notes=["«عنه» points back to a name written before this report; it is not named here"]),
]
MARKS = re.compile(r"[ً-ٰۖ-ۭـ]")
MAX_TEXT = 340     # shown text is cut at a word boundary after this many characters, never after the matn anchor + 60


def reader_text(hadith: dict) -> str:
    work = hadith["collection_id"].split(":")[-1]
    if work in CHAIN_FIELD_WORKS and (hadith.get("sanad") or "").strip():
        return f"{hadith['sanad'].strip()}\n\n{hadith['text_ar']}"
    return hadith["text_ar"]


def locate(text: str, plain: str, cursor: int = 0) -> tuple[int, int] | None:
    """Span in `text` (diacritics kept) of the first occurrence at/after `cursor` of `plain` read without diacritics."""
    kept = [i for i, ch in enumerate(text) if i >= cursor and not MARKS.match(ch)]
    stripped = "".join(text[i] for i in kept)
    at = stripped.find(plain)
    if at < 0:
        return None
    start, end = kept[at], kept[at + len(plain) - 1] + 1
    while end < len(text) and MARKS.match(text[end]):
        end += 1
    return start, end


def build_example(spec: dict, hadith: dict, number: int) -> dict:
    text = reader_text(hadith)
    anchor = locate(text, spec["anchor"])
    assert anchor, spec["hadith"]
    anchor_at = anchor[0]
    limit = max(MAX_TEXT, anchor_at + 60)
    if len(text) > limit:
        text = text[:text.rfind(" ", 0, limit)]
    routes, spans = [], []
    for route_spec in spec["routes"]:
        links, cursor = [], 0
        for item in route_spec:
            if item[0] == "=":
                links.append(dict(routes[item[1]]["links"][item[2]]))
                continue
            surface, kind = item
            span = locate(text, surface, cursor)
            assert span, (spec["hadith"], surface)
            links.append({"surface": text[span[0]:span[1]], "start": span[0], "end": span[1], "kind": kind})
            cursor = span[1]
        routes.append({"links": links})
    for route, tail in zip(routes, spec["tails"]):
        route["shared_tail_from"] = tail
    output = {"id": f"ex{number}", "routes": routes, "matn_start": anchor_at, "notes": spec["notes"]}
    errors = validate(output, text, f"ex{number}")
    assert not errors, (spec["hadith"], errors)
    return {"number": number, "hadith_id": spec["hadith"], "collection_id": hadith["collection_id"], "title": spec["title"],
            "input": {"id": f"ex{number}", "text": text}, "output": output}


def format_output(output: dict) -> str:
    """JSON with one line per link so a small model can copy the shape."""
    def link(item: dict) -> str:
        return json.dumps(item, ensure_ascii=False, separators=(", ", ": "))
    lines = ['{"id": ' + json.dumps(output["id"]) + ",", ' "routes": [']
    for r, route in enumerate(output["routes"]):
        lines.append('  {"links": [')
        lines += ["    " + link(item) + ("," if i < len(route["links"]) - 1 else "") for i, item in enumerate(route["links"])]
        lines.append(f'   ], "shared_tail_from": {json.dumps(route["shared_tail_from"])}' + "}" + ("," if r < len(output["routes"]) - 1 else ""))
    lines.append(" ],")
    lines.append(f' "matn_start": {output["matn_start"]},')
    lines.append(' "notes": ' + json.dumps(output["notes"], ensure_ascii=False) + "}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetched", required=True)
    args = parser.parse_args()
    rows = json.loads(Path(args.fetched).read_text(encoding="utf-8"))["rows"]
    built = [build_example(spec, rows[spec["hadith"]]["h"], number) for number, spec in enumerate(EXAMPLES, start=1)]
    (ROOT / "examples").mkdir(exist_ok=True)
    (ROOT / "examples" / "examples.json").write_text(json.dumps(built, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    blocks = []
    for example in built:
        blocks.append(f"### Example {example['title']}\n\nInput:\n```\n{json.dumps(example['input'], ensure_ascii=False)}\n```\n\n"
                      f"Output:\n```\n{format_output(example['output'])}\n```\n")
    body = (HERE / "prompt_body.md").read_text(encoding="utf-8")
    prompt = body.replace("{{EXAMPLES}}", "\n".join(blocks).rstrip("\n"))
    (ROOT / "prompt.md").write_bytes(prompt.replace("\r\n", "\n").encode("utf-8"))
    print(hashlib.sha256((ROOT / "prompt.md").read_bytes()).hexdigest(), len(prompt), "chars")


if __name__ == "__main__":
    main()
