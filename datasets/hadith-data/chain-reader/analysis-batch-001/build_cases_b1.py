"""Write analysis-batch-001/cases.md.   python -X utf8 analysis-batch-001/numbers_b1.py && python -X utf8 analysis-batch-001/build_cases_b1.py"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numbers_b1 as N          # re-runs the numbers; exposes V, E
from common_b1 import *

V, E, T, K = N.V, N.E, N.T, N.K
NAMES = {"r": "right", "p": "representation only", "w": "wrong", "c": "cannot tell"}
QUESTIONS = {
    "Q1d": "Is the person who only asks («و سأل X Y», «و كتب X إلى Y») a link? Readers dropped him (right under the ruling as given; wrong if he is a link).",
    "Q1k": "Same question: one reader kept the writer of a question (cr 4cbe02, «و كتب البزنطي إلى أبي الحسن»).",
    "Q1e": "Same question for the empty readings: «و سأله X: عن …» with the Imam only a pronoun: no chain (asker dropped), or [X]? Includes the first-person «قال قلت» (7425f4).",
    "Q2": "«قضى أمير المؤمنين … في» (a judgment of the Imam, no transmitter): is he the person whose words are relayed? (550aae)",
    "Q3": "The author of a cited book («و في نوادر إبراهيم بن هاشم: أن الصادق …») is he a link? (86d128; the reader wrote him as one)",
    "Q4": "A narrated encounter in which the Imam speaks and acts (b2ad9c, 941f93, dcfca3): is he the person whose words the report relays?",
    "Q5": "Two sayings in one report, the second with its own isnad («حدثني أبي، عن أبيه … عن الصادق»): which is the report? (cb13de)",
    "Q6": "A remark «ورواه شعبة عن السدي فلم يرفعه» (a partial, lower variant): written as a route? (57c34c)",
    "Q7": "«روي عن الأئمة عليه السلام»: is a collective of Imams a link? (3fe7a2)",
    "Q8": "«وقال عليه السلام» / «و قضى عليه السلام» with the Imam named only in an earlier report: empty reading, or a back-reference link? (0fcaaf, 38f586, 5755a4, 7c6342, c172ef, df799e, 74b4de)",
    "Q9": "First-person narrative with an implicit transmission («فلما سمعت ذلك من هشام عملت به»): a chain or none? (549073)",
}
ROUTES_END = {
    "160be9": ("agreed", "wrong", "«عن أبيه، وعن أمه زينب … عن أم سلمة - يحدثانه جميعا ذاك عنها»: the routes through «أبيه» stop before أم سلمة"),
    "162ebe": ("agreed", "wrong", "three ح branches: Zuhri > Humayd > the mother is written once after the last branch; routes one and two stop"),
    "21210d": ("agreed", "right", "«حدثنا علي بن مسهر، عن الأعمش، فذكر نحوه»: the third route is short because the text abbreviates"),
    "21b3e7": ("disagree", "B right", "A stops three routes at إسماعيل بن أبي خالد; the tail «قيس > المغيرة» is written once"),
    "398b6f": ("disagree", "A right", "B stops route one at «أبي»; the tail «همام > قتادة» follows the ح"),
    "3c59ef": ("agreed", "right", "two separate isnads that end at different Companions («سمرة بن جندب», «المغيرة بن شعبة»)"),
    "41356f": ("disagree", "B closer", "A drops the tail from the first route; the remark «ولم يذكر قتيبة … عن عبيد الله» is not applied by either"),
    "844adb": ("agreed", "wrong", "route one «ابن المثنى > وهب بن جرير» stops; «شعبة» is written after the second branch"),
    "a22a43": ("disagree", "B right", "A stops three routes at شعبة"),
    "aa60d7": ("disagree", "neither", "both write the later isnads of «روي» as routes of «قال علي»; B adds علي"),
    "c47be8": ("disagree", "neither", "nested «؛» and «جميعا»"),
    "cc4d10": ("disagree", "B right", "A stops two routes at ابن جريج"),
    "d2bb6c": ("agreed", "wrong", "«أبي وائل > مسروق > عائشة» is written once after the last branch; route one stops at الأعمش"),
    "d55665": ("disagree", "B right", "A stops route one at شعبة"),
    "ee5c9a": ("agreed", "wrong", "nested «؛» and «جميعا»: four fragments instead of the combined routes"),
}
RULING = {
    "162ebe": ("agreed", "wrong", "settled by the tail rule (written once after the last ح): flag not needed, reading wrong"),
    "223908": ("agreed", "cannot tell", "six ح branches with «جميعا عن موسى بن عقبة» and «كل هؤلاء عن نافع»; the reading drops «عبيد الله»; nesting not decidable"),
    "549073": ("agreed", "cannot tell", "Q9"),
    "5e3cb7": ("disagree", "cannot tell", "«أن أسامة بن زيد، أخبر والده، سعد بن أبي وقاص»: B adds سعد after أسامة; who is the source is not settled"),
    "63a547": ("agreed", "wrong", "«قال لهم تنفر»: ابن عباس answers the people who asked him; he is the person whose words are relayed and the reading ends at عكرمة"),
    "7425f4": ("agreed", "cannot tell", "Q1e, first person «قال قلت»"),
    "747357": ("disagree", "cannot tell", "Q1: A empty, B [asker]"),
    "8a1368": ("disagree", "A right", "ابن عباس speaks («فقال لو كنت أنا لقتلتهم»); both flagged although the ruling settles it"),
    "aa60d7": ("disagree", "neither", "see routes_end"),
    "c47be8": ("disagree", "neither", "nested"),
    "d6d6e1": ("agreed", "right", "the appended father-and-son exchange is a scene; the chain ends at جابر بن سمرة; flag on a real but harmless ambiguity"),
    "e262e1": ("agreed", "right", "the later chains are variants of the same saying, marked variant; flags on a settled case"),
    "eb1e57": ("agreed", "right", "«و سأله: عن الخلاخل»: no name anywhere, empty is right"),
}


def main():
    out = ["# Read cases (batch 001)", "", "Reader: right / representation only / wrong / cannot tell. Stored: right / defective (kind). Every quote is from the text; the full per-report table is `sample.tsv`.", ""]
    out += ["## 1. Eligible readings that are not 'reader right', and the stored chains that are right", ""]
    for i, v in sorted(V.items()):
        if v["reader"] in "wc":
            out += [f"- **{i}** {v['group']} / {T[i]['work'].split(':')[1]}: reader **{NAMES[v['reader']]}**, stored {'right' if v['stored'] == 'r' else 'defective (' + v['kind'] + ')'} {','.join(v['tags'])}: «{v['quote']}»"]
    out += ["", "## 2. Stored chain right (and the reader reproduces it)", ""]
    for g in N.GROUPS:
        ids = [i for i, v in sorted(V.items()) if v["group"] == g and v["stored"] == "r"]
        out += [f"- {g} ({len(ids)}): " + ", ".join(i[3:] for i in ids)]
    out += ["", "## 3. Empty readings (57): who is right", ""]
    cats = {}
    for i, v in sorted(E.items()):
        cats.setdefault(next(t for t in v["tags"] if t.startswith("cat:")), []).append(i)
    for c, ids in cats.items():
        out += [f"### {c} ({len(ids)})", ""]
        for i in ids:
            v = E[i]
            out += [f"- {i[3:]} {v['work']} reader {NAMES[v['reader']]} {','.join(t for t in v['tags'] if not t.startswith('cat:'))}: «{v['quote']}»  stored: " + " > ".join(K[i]["stored_chains"][0]["surfaces"])[:90]]
        out += [""]
    out += ["## 4. The 30 disagreements read (random of 50)", ""]
    for l in (HERE / "v_dis.txt").read_text(encoding="utf-8").splitlines():
        p = l.split("|")
        out += [f"- **{p[0]}** {p[1]}; right: {p[2]}: «{p[3]}»"]
    out += ["", "## 5. `routes_end_at_different_links` (15 reports)", ""]
    for i, (a, v, n) in ROUTES_END.items():
        out += [f"- {i} ({a}): {v}. {n}"]
    out += ["", "## 6. `needs_ruling` by both readers (13 reports)", ""]
    for i, (a, v, n) in RULING.items():
        out += [f"- {i} ({a}): {v}. {n}"]
    out += ["", "## 7. Owner questions (the verdicts above turn on these)", ""]
    for q, text in QUESTIONS.items():
        ids = [i[3:] for i, v in sorted({**V, **E}.items()) if q in v["tags"]]
        out += [f"- **{q}** ({len(ids)}): {text} Ids: {', '.join(ids)}"]
    (HERE / "cases.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(len(out), "lines")


main()
