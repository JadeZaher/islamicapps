"""The judges' real cases for the v3.4 rulings, read by hand as prompt v3.4 says (v3_4/README.md §tests): packets are loaded from their tranche, never copied."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N, R, U, I = "narrator", "relation", "unnamed", "imam_in_text"


def packet(tranche: str, report_id: str) -> dict:
    for path in sorted((ROOT / "tranches" / f"tranche-{tranche}" / "packets").glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and f'"id":"{report_id}"' in line.replace(" ", ""):
                row = json.loads(line)
                if row["id"] == report_id:
                    return row
    raise KeyError(report_id)


def level(*items) -> list[dict]:
    """('surface', kind) or ('surface', kind, occurrence) per co-transmitter."""
    return [{"surface": s[0], "kind": s[1], **({"occurrence": s[2]} if len(s) > 2 else {})} for s in items]


def output(report_id: str, groups: list[dict], notes: list[str] | None = None) -> dict:
    return {"id": report_id, "status": "read", "groups": groups, "shared_tail": None, "needs_ruling": False, "notes": notes or [], "fixes": []}


HEAD_023097 = [level(("يزيد بن سنان", N)), level(("الحسن بن عمر بن شقيق", N)), level(("جرير بن عبد الحميد", N)), level(("حصين بن عبد الرحمن", N)), level(("جابر بن سمرة", N))]
HEAD_102AF2 = [level(("عبد الله بن وهب", N)), level(("عمرو بن الحارث", N)), level(("بكير بن الأشج", N))]
HEAD_520F51 = [level(("عبد بن حميد", N)), level(("عبد الرزاق", N)), level(("معمر", N)), level(("الزهري", N))]

# (tranche, id, the v3.4 reading, what the test checks)
TWO_SAYINGS = {
    # Jabir b. Samura hears the Prophet (saying 1); he asks his father, who answers «كلهم من قريش» (saying 2: the one asked and answering is the last link)
    "t02-023097": ("02", output("t02-023097", [
        {"levels": HEAD_023097, "saying": 1, "saying_opens": "يقوم في أمّتي بعدي اثنا عشر أميراً"},
        {"levels": HEAD_023097 + [level(("أبي", R))], "saying": 2, "saying_opens": "كلهم من قريش"}])),
    # Yunus's version adds «قال بكير وحدثني رجل عن ابن حنين أنه قال رأيت ذلك الأسود»: saying 2 runs through Yunus only, keeps the head to بكير, then the unnamed man and Ibn Hunayn
    "t02-102af2": ("02", output("t02-102af2", [
        {"levels": [level(("أبو الطاهر", N), ("يونس بن عبد الأعلى", N))] + HEAD_102AF2 + [level(("بسر بن سعيد", N)), level(("عبيد الله بن أبي رافع", N))], "saying": 1, "saying_opens": "أن الحرورية لما خرجت"},
        {"levels": [level(("يونس بن عبد الأعلى", N))] + HEAD_102AF2 + [level(("رجل", U)), level(("ابن حنين", N))], "saying": 2, "saying_opens": "رأيت ذلك الأسود"}])),
    # the prompt's example 5: al-Zuhri goes on «وأخبرني عروة، عن عائشة»; Aisha's own act is saying 2
    "t01-520f51": ("01", output("t01-520f51", [
        {"levels": HEAD_520F51 + [level(("سالم", N))], "saying": 1, "saying_opens": "أن أبا بكر، وعمر، وابن، عمر كانوا ينزلون الأبطح"},
        {"levels": HEAD_520F51 + [level(("عروة", N)), level(("عائشة", N))], "saying": 2, "saying_opens": "أنها لم تكن تفعل ذلك"}])),
}
ENCOUNTERS = {
    # Ali speaks inside Said's story («فقال علي ما تريد»): Ali is the last link; Uthman is only in the scene
    "t02-8b818b": ("02", output("t02-8b818b", [{"levels": [level(("قتيبة بن سعيد", N)), level(("حجاج بن محمد الأعور", N)), level(("شعبة", N)), level(("عمرو بن مرة", N)), level(("سعيد بن المسيب", N)),
                                                           level(("علي", N, 2))]}]), "علي"),
    # al-Harith walks with Amir al-Muminin, who speaks («فقال علي بن أبي طالب عليه السلام: يا حارث»): the Imam is the last link, named only in the story
    "t02-1cc0f4": ("02", output("t02-1cc0f4", [{"levels": [level(("صالح بن عيسى العجلي", N)), level(("أبو بكر محمد بن محمد بن علي الفقيه", N)), level(("أبو نصر الشعراني", N)),
                                                           level(("سلمة بن صالح الوضاح", N)), level(("أبيه", R)), level(("أبي إسرائيل", N)), level(("أبي إسحاق الهمداني", N)),
                                                           level(("عاصم بن ضمرة", N)), level(("الحارث الأعور", N)), level(("أمير المؤمنين علي بن أبي طالب", I))]}]), "أمير المؤمنين علي بن أبي طالب"),
    # the owner's own example: «كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى، فنظر إلى الناس فقال»
    "t01-a20cb6": ("01", output("t01-a20cb6", [{"levels": [level(("أبى", R)), level(("سعد بن عبد الله", N)), level(("بإسناد يرفعه", U)), level(("منصور الصيقل", N)),
                                                           level(("أبي عبد الله", I))]}]), "أبي عبد الله"),
}
# the mutaba'a the tranche-02 judge found written as a route by both passes (1061e3): a variant group in v3.4
MUTABAA_1061E3 = ("02", output("t02-1061e3", [
    {"levels": [level(("عبيد الله بن موسى", N)), level(("حنظلة", N)), level(("سالم", N)), level(("ابن عمر", N))]},
    {"levels": [level(("قتيبة", N)), level(("العنقزي", N)), level(("حنظلة", N, 2))], "variant": True}]))
