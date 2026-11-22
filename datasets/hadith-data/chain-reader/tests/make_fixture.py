"""Regenerate the tiny hand-made scoring fixture (tests/fixtures): 7 reports, two reader runs. Offsets are computed here."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent / "fixtures"
N, U, B = "narrator", "unnamed", "back_reference"


def chain(chain_id, surfaces, verdict="unlabelled", kind="", note="", state=None):
    return {"chain_id": chain_id, "branch": 0, "structure_status": "checked_by_rule", "surfaces": surfaces, "verdict": verdict,
            "kind": kind, "note": note, "label_round": "round4" if state else None, "label_state": state}


def report(number, work, text, chains, verdict, report_labels=(), expected=()):
    tradition = {"bukhari": "sunni", "muslim": "sunni", "al-kafi": "imami", "musnad-rabi": "ibadi"}[work]
    return {"id": f"cr-{number:04d}", "hadith_id": f"hadith:fixture:{number}", "tradition": tradition, "work": work, "text": text,
            "text_layout": "full_text", "stored_chains": chains, "report_verdict": verdict, "report_labels": list(report_labels),
            "expected_names": list(expected), "label_rounds": ["round4"], "evidence_rank": 0, "snapshot_at": "fixture"}


TEXTS = {
    1: "حدثنا أحمد بن علي، حدثنا سالم، عن ابن عمر، أن رسول الله صلى الله عليه وسلم قال: الأعمال بالنيات",
    2: "حدثنا يحيى، أخبرنا يونس، عن الزهري، أخبرني عروة، أنه سمع أسماء تقول قام رسول الله خطيبا",
    3: "3- عِدَّةٌ مِنْ أَصْحَابِنَا عَنْ أَحْمَدَ بْنِ مُحَمَّدٍ عَنْ أَبِي عَبْدِ اللهِ قَالَ مَنْ صَامَ يوما",
    4: "حدثنا خالد، عن بكر، عن أنس، قال كان النبي يصلي",
    5: "حدثنا عمرو، عن ابن شهاب، أنه سمع سالما يقول كان رسول الله يصوم",
    6: "أبو عبيدة عن جابر بن زيد عن ابن عباس قال: كان رسول الله يصوم",
    7: "حدثنا زهير، ح وحدثني بشر، قالا حدثنا شعبة، بهذا الإسناد. غير أنه قال كذا",
}
ANCHORS = {1: "الأعمال", 2: "قام رسول", 3: "مَنْ صَامَ", 4: "كان النبي", 5: "كان رسول", 6: "كان رسول", 7: "غير أنه"}
REPORTS = [
    report(1, "bukhari", TEXTS[1], [chain("c1", ["أحمد بن علي", "سالم", "ابن عمر"], "correct", state="current")], "correct"),
    report(2, "muslim", TEXTS[2], [chain("c2", ["يحيى", "يونس", "الزهري", "عروة"], "defective", "missing_link", "أسماء not stored", "current")], "defective",
           expected=["اسماء"]),
    report(3, "al-kafi", TEXTS[3], [chain("c3", ["عدة من أصحابنا", "أحمد بن محمد", "أبي عبد الله"], "correct", state="current")], "correct"),
    report(4, "muslim", TEXTS[4], [chain("c4", ["خالد", "بكر", "أنس"], "correct", state="current")], "correct"),
    report(5, "muslim", TEXTS[5], [chain("c5", ["عمرو", "ابن شهاب"], "defective", "missing_link", "سالما not stored", "current")], "defective", expected=["سالما"]),
    report(6, "musnad-rabi", TEXTS[6], [chain("c6", ["أبو عبيدة", "جابر بن زيد", "ابن عباس"], "correct", state="current")], "correct"),
    report(7, "muslim", TEXTS[7], [chain("c7a", ["زهير", "شعبة"], "correct", state="current"), chain("c7b", ["بشر", "شعبة"], "correct", state="current")], "correct"),
]


def find(text, plain, cursor=0):
    import re
    marks = re.compile(r"[ً-ٰ]")
    kept = [i for i, ch in enumerate(text) if i >= cursor and not marks.match(ch)]
    stripped = "".join(text[i] for i in kept)
    at = stripped.find(plain)
    start, end = kept[at], kept[at + len(plain) - 1] + 1
    while end < len(text) and marks.match(text[end]):
        end += 1
    return start, end


def make_output(number, routes, tails=None, shift=0, fenced=False, notes=()):
    text = TEXTS[number]
    out_routes = []
    for r, route in enumerate(routes):
        cursor, links = 0, []
        for plain, kind in route:
            start, end = find(text, plain, cursor)
            links.append({"surface": text[start:end], "start": start + shift, "end": end + shift, "kind": B if plain == "بهذا الإسناد" else N})
            cursor = end
        out_routes.append({"links": links, "shared_tail_from": (tails or [None] * len(routes))[r]})
    body = {"id": f"cr-{number:04d}", "routes": out_routes, "matn_start": find(text, ANCHORS[number])[0], "notes": list(notes)}
    raw = json.dumps(body, ensure_ascii=False, indent=1)
    return f"```json\n{raw}\n```" if fenced else raw


def ns(*names):
    return [(name, "x") for name in names]


RUN_A = {
    1: make_output(1, [ns("أحمد بن علي", "سالم", "ابن عمر")]),
    2: make_output(2, [ns("يحيى", "يونس", "الزهري", "عروة", "أسماء")]),
    3: make_output(3, [ns("عدة من أصحابنا", "أحمد بن محمد", "أبي عبد الله")], fenced=True),
    4: make_output(4, [ns("خالد", "أنس")], notes=["Bakr skipped by mistake"]),
    5: make_output(5, [ns("عمرو", "ابن شهاب")]),
    7: make_output(7, [ns("زهير", "شعبة", "بهذا الإسناد"), ns("بشر", "شعبة", "بهذا الإسناد")], tails=[1, 1], shift=2),
}
RUN_B = {
    1: make_output(1, [ns("أحمد بن علي", "سالم", "ابن عمر")]),
    2: make_output(2, [ns("يحيى", "يونس", "الزهري", "عروة")]),
    3: make_output(3, [ns("عدة من أصحابنا", "أحمد بن محمد", "أبي عبد الله")]),
    4: make_output(4, [ns("خالد", "بكر", "أنس")]),
    5: make_output(5, [ns("عمرو", "ابن شهاب")]),
    6: make_output(6, [ns("أبو عبيدة", "جابر بن زيد", "ابن عباس")]),
    7: make_output(7, [ns("زهير", "شعبة", "بهذا الإسناد"), ns("بشر", "شعبة", "بهذا الإسناد")], tails=[1, 1]),
}

if __name__ == "__main__":
    (HERE / "reports.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in REPORTS), encoding="utf-8", newline="\n")
    for folder, run in (("run_a", RUN_A), ("run_b", RUN_B)):
        for number, raw in run.items():
            (HERE / folder / f"cr-{number:04d}.json").write_text(raw, encoding="utf-8", newline="\n")
