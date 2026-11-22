"""Write items.tsv and numbers.json: one adjudicator's reading of all 81 pilot items against the judge and the pass-1 reviewer (see README.md here).

    python -B -X utf8 reviewer/pilot-001/adjudication/adjudicate.py      (from chain-reader/)

The verdicts in VERDICTS are a single model reader's (claude-opus-5-5) reading of the Arabic, made by hand with dump_items.py; this script only joins them to the key,
the packets and the reviewer's outputs, checks every quote is an exact substring of the item's text, validates each review on its own, and computes the rates
with Wilson 95% intervals. Exits 1 if a quote is not found.
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
sys.path.insert(0, str(PILOT.parent))
from validate_review import validate_review  # noqa: E402

SAMPLE_SEED = 20261122  # the both-confirmed re-read: 15 of the 41 scored items where judge says right and reviewer confirms

# opaque id -> (actual, verdict, correction, referral, quote from text, note)
# actual: right / wrong / unruled (structure right, storing it at all is an unruled owner question)
# verdict (disagreements): reviewer_right / judge_right / both_acceptable / neither / unruled; agreements: agree_right / agree_wrong
# correction: right / right_medium / cosmetic / right_invalid_format / '' ; referral: justified / unjustified / ''
VERDICTS: dict[str, tuple[str, str, str, str, str, str]] = {
    # --- judge right, reviewer did not confirm (12) ---
    "cr1-2fc4ff": ("unruled", "unruled", "", "justified", "و ما كان فيه عن الحسين بن المختار فقد رويته",
                   "al-Faqih route statement with no saying (unruled); the readers' five routes are structurally right; the non-clearable hold keeps it held anyway"),
    "cr1-1d4e8b": ("unruled", "unruled", "", "justified", "و ما كان فيه عن ثعلبة بن ميمون فقد رويته",
                   "al-Faqih route statement (unruled); «عنهم» left as a back reference is representation"),
    "cr1-efd81b": ("unruled", "unruled", "", "justified", "و ما كان فيه عن محمّد بن سنان فقد رويته",
                   "al-Faqih route statement (unruled); two routes structurally right"),
    "cr1-d695ec": ("wrong", "reviewer_right", "", "justified", "فنظرت فإذا عمر قال إني قد رأيتك جئت آنفا قال",
                   "a second saying relayed by the man who speaks inside the encounter (rulings 9, 10) is missing; also «ح وحدثني أبو عثمان» names no speaker, so the join of the second branch is genuinely open"),
    "cr1-5415bf": ("wrong", "reviewer_right", "", "justified", "ونحن مع أمير المؤمنين علي بصفين",
                   "the one who speaks inside the narrator's encounter («قال: قد بلغتماني») is not written as the last link (ruling 9); whether «وذكر أبان أنه سمعه أيضا عن عمر بن أبي سلمة» adds routes is a real ambiguity"),
    "cr1-37ccb6": ("wrong", "reviewer_right", "", "justified", "بمثل حديث مالك بن أنس بإسناده عن نافع",
                   "the chain continues past the last name by another report's isnad («بإسناده»); the readers end it there with no back-reference link; the continuation needs a report not in the packet"),
    "cr1-b567d7": ("wrong", "reviewer_right", "", "justified", "عن سالم، أنحدثه قال قبل عمر بن الخطاب الحجر ثم قال أم والله لقد علمت أنك حجر",
                   "the one who speaks in the scene is the last link (ruling 9) and is missing; the unnamed transmitter in «أنحدثه» is the unruled implicit-transmission question"),
    "cr1-593d35": ("right", "both_acceptable", "cosmetic", "", "قالا أخبرنا الثوري، عن أيوب بن موسى، في هذا الإسناد",
                   "corrected routes equal the readers' (compare_corrections.py: same_routes=True); only the back-reference link's placement"),
    "cr1-23cc42": ("wrong", "reviewer_right", "right_medium", "", "وقال عثمان والحسن بن علي عن محمد بن عباد بن جعفر",
                   "the compiler states that two of the four co-transmitters named a different man at one link of THIS chain; the readers send them through the written name. Placing «وغيرهم» on the written chain is a default the text does not state"),
    "cr1-80cd84": ("wrong", "reviewer_right", "right", "", "قال ابن عيسى لم يذكر أمية أحد إلا معتمر",
                   "the text says only one of three routes has that link; the judge's own caveat says the same. Applied: reverting gives the stored chain, which has the same error"),
    "cr1-cd74d5": ("right", "both_acceptable", "cosmetic", "", "عن وهب بن منبه أن النبي صلى الله عليه وسلم أمر عبد الله بن عمرو",
                   "correction touches only the variant group (the man commanded is not a link of the remark); routes identical"),
    "cr1-e87ace": ("right", "both_acceptable", "cosmetic", "", "عمن سمع أبا عبد الله الصادق (عليه السلام) يقول",
                   "kind imam_in_text -> narrator only; routes identical. Applied: the current rule would revert a right reading to a stored chain that fuses the gap phrase into a name"),
    # --- judge cannot tell (4) ---
    "cr1-c785d5": ("wrong", "reviewer_right", "right", "", "ثُمَّ قَالَ عَلَيْهِ اَلسَّلاَمُ",
                   "narrated encounter, the Imam speaks: ruling 9 makes him the last link; the readers stopped at the narrator because the question was then unruled"),
    "cr1-ad25ec": ("wrong", "reviewer_right", "", "justified", "وَقَالَ اَلْحَلَبِيُّ لَهُ",
                   "«له» points back to an earlier report's source (back-reference opening); the one asked is missing and no previous report is in the packet"),
    "cr1-d1ccde": ("wrong", "reviewer_right", "right", "", "كُنْتُ يَوْماً عَلَى رَأْسِ الْمَأمُونِ، فَقالَ",
                   "the man who speaks inside the narrator's encounter and tells the whole story is the last link (ruling 9); the seven-shaykh level is unchanged"),
    "cr1-f890c7": ("wrong", "reviewer_right", "right_medium", "", "وأخبرني خارجة بن زيد بن ثابت أن زيد بن ثابت لم يكن يبيع ثمار أرضه",
                   "a second saying with its own isnad (ruling 10); the one whose practice is described is not a link. That «وأخبرني» continues the speaker of «كان عروة بن الزبير يحدث» is the better but not the only reading"),
    # --- judge wrong (16) ---
    "cr1-6dfc38": ("wrong", "agree_wrong", "right_medium", "", "وَ سَأَلَهُ لَيْثٌ اَلْمُرَادِيُّ",
                   "readers inherit an earlier ASKER as the one asked (context «وَ رُوِيَ عَنِ اَلْحَلَبِيِّ قَالَ : سَأَلْتُهُ»); correction inherits the source named in prev1 «عَنْ أَبِي عَبْدِ اَللَّهِ», the best the packet allows"),
    "cr1-723cba": ("wrong", "agree_wrong", "right", "", "حدثنا أبو أسامة، ح وحدثنا إسحاق بن منصور، أنبأنا النضر بن شميل، عن بهز بن حكيم",
                   "branches meet after the second head; correction gives the shared tail"),
    "cr1-36837c": ("wrong", "agree_wrong", "right", "", "عن إسماعيل بن كثير، وكان، يكنى أبا هاشم ح",
                   "the text's own kunya statement marks the join; correction keeps both names as written and shares the tail"),
    "cr1-eedf77": ("wrong", "agree_wrong", "", "justified", "جميعا عن أحمد بن محمّد بن عيسى؛ و الفضل بن عامر",
                   "al-Faqih route statement (unruled) AND misread: the second-level co-transmitter is made a compiler's shaykh; the reviewer names the error in its reasons"),
    "cr1-c5386a": ("wrong", "agree_wrong", "right", "", "حدثنا أبو داود، حدثنا شعبة، ح وحدثنا",
                   "join at the restated name; correction shares the tail"),
    "cr1-f8eeeb": ("wrong", "agree_wrong", "right", "", "عن شريك، - قال ابن العلاء وقيس - عن أبي حصين",
                   "a co-source inside the isnad for one shaykh's route; correction adds it on that route only"),
    "cr1-519567": ("wrong", "agree_wrong", "right", "", "حدثنا زهير، ح وحدثنا محمد بن الصباح البزاز، حدثنا إسماعيل بن زكريا، عن سهيل",
                   "join at the shared tail; the father's closing advice («قال فقال لي أبي») is left aside as implicit transmission (unruled), stated by the reviewer"),
    "cr1-0ea0a3": ("wrong", "agree_wrong", "right", "", "عن ابن أبي ذئب، والأوزاعي، - عن الزهري",
                   "a co-source inside the isnad for one shaykh; correction adds that route"),
    "cr1-7c8879": ("wrong", "agree_wrong", "right", "", "حدثنا وكيع، - المعنى - عن سعد بن أوس",
                   "join after the second head; correction shares the tail"),
    "cr1-750b73": ("wrong", "agree_wrong", "right_invalid_format", "", "حدثنا بذلك إسحاق بن منصور حدثنا عبد الرحمن بن مهدي",
                   "the correction (one route: the compiler's connection, then the stated isnad) is right in substance; the reader format's text-order rule cannot express a connection isnad written after the names it connects to"),
    "cr1-0b5d5a": ("wrong", "agree_wrong", "right_medium", "", "عن هشام، قال وحدثنا مخلد بن حسين، عن هشام، عن محمد بن سيرين",
                   "«قال وحدثنا» shows the later isnads are spoken by the first shaykh; correction keeps that head and ends the second route at the speaker"),
    "cr1-4d44fd": ("wrong", "agree_wrong", "right", "", "قال أبو بصرة أترغب عن سنة رسول الله",
                   "join at the shared name, the added co-source on one route («وزاد، جعفر والليث»), and the speaker inside the encounter as last link (ruling 9)"),
    "cr1-c0e535": ("wrong", "agree_wrong", "right", "", "عَنْ مُحَمَّدِ بْنِ أُورَمَةَ وَ حَدَّثَنِي أَبِي",
                   "two isnads meet at the restated name; correction writes the tail into both"),
    "cr1-b61479": ("wrong", "agree_wrong", "right", "", "- إلا الضحاك وابن عجلان فإنهما زادا عن ابن عباس، عن علي، -",
                   "the clause states the shape of two of the routes; correction adds the link on exactly those two"),
    "cr1-9c5eae": ("wrong", "agree_wrong", "right", "", "حدثنا مروان، ح حدثنا عبد الوهاب",
                   "join at the restated name; correction shares the tail"),
    "cr1-a494cc": ("wrong", "agree_wrong", "", "justified", "عن سعد بن عبد اللّه؛ و الحميريّ جميعا عن أحمد",
                   "al-Faqih route statement (unruled) AND misread: the co-transmitter beside the second-level name is made a compiler's shaykh; the reviewer names it"),
    # --- both say right: the 15 re-read (seed 20261122) ---
    "cr1-0fd844": ("right", "agree_right", "", "", "دخلت على عثمان فتشهد ثم قال", "the one who speaks inside the encounter is the last link; «تابعه» is a remark"),
    "cr1-18f33f": ("right", "agree_right", "", "", "عن عمه، إسحاق بن طلحة عن عائشة", "relation word and name are one link; «وروى بعضهم» is a remark"),
    "cr1-250b50": ("right", "agree_right", "", "", "وساق الحديث بمثل حديث يونس", "pointer is a remark"),
    "cr1-300e9b": ("right", "agree_right", "", "", "قرأت على مالك عن نافع، عن ابن عمر", ""),
    "cr1-448b02": ("right", "agree_right", "", "", "قالا حدثنا شعبة، عن أبي التياح", "two heads meet at «قالا»"),
    "cr1-6138e8": ("right", "agree_right", "", "", "بِهذَا الإِسناد قالَ: قالَ رَسُولَ اللَّهِ",
                   "inherited from the far report that writes the chain (prev8); its doubled name has its own «حَدَّثَني» each time, so two links as written"),
    "cr1-701f37": ("right", "agree_right", "", "", "جميعا عن الأعمش، بهذا الإسناد", "back-reference link marks the continuation"),
    "cr1-9203c4": ("right", "agree_right", "", "", "وغير العلاء بن المسيب قال في هذا الحديث عن طلحة عن رجل عن حذيفة", "the compiler's remark on another version"),
    "cr1-972027": ("right", "agree_right", "", "", "أنه سمع أبا هريرة، يقول قال رسول الله", ""),
    "cr1-bc86da": ("right", "agree_right", "", "", "واقتصوا الحديث بمعنى حديث يحيى بن أبي كثير عن أبي سلمة", "pointer is a remark; two branches"),
    "cr1-c75278": ("right", "agree_right", "", "", "حدثوه عن أبي هريرة", "three co-transmitters; the second isnad with its own «وحدثنا» is a route, «بمثل حديث مالك» a remark"),
    "cr1-d66a32": ("right", "agree_right", "", "", "واقتص الحديث بمثل حديث يونس ومعمر", "pointer is a remark"),
    "cr1-e3a079": ("right", "agree_right", "", "", "قال عبد الله بن دينار كان ابن عمر يفعل ذلك", "the closing statement has no isnad of its own and describes an act: not a second chain"),
    "cr1-e708f5": ("right", "agree_right", "", "", "تابعه عبد الرزاق عن معمر في الآية", "mutabaʿa is a remark"),
    "cr1-f24679": ("right", "agree_right", "", "", "قال سألت رافع بن خديج عن كراء الأرض، فقال", "asker and the one who answers are links; «ولم يرفعه» is a remark"),
    # --- packet 04, both say right (8) ---
    "cr1-7e8e53": ("right", "agree_right", "", "", "عن ابن طاوس، عن أبيه، أنه كان يكره", ""),
    "cr1-25de39": ("right", "agree_right", "", "", "قال حدثني أبي، - قال ابن عوف ورأيت في أصل إسماعيل - قال حدثني ضمضم", "the dashed note is not a link"),
    "cr1-e25ac5": ("right", "agree_right", "", "", "- قال عثمان سيف بن سليمان -", "a fuller name for the same link: no route"),
    "cr1-eb03bd": ("right", "agree_right", "", "", "عن أبيه، جبير بن مطعم قال أضللت بعيرا لي", "relation word and the name are the same man (representation)"),
    "cr1-2c29bb": ("right", "agree_right", "", "", "جميعا عن ابن، عيينة - قال أبو بكر حدثنا سفيان بن عيينة، -", "the dashed fuller name is one link"),
    "cr1-7e756d": ("right", "agree_right", "", "", "و سَأَلَهُ بَعْضُ أَصْحَابِهِ", "back reference inherits the source named in prev2"),
    "cr1-fa1729": ("right", "agree_right", "", "", "عن أبي قلابة، قال حدثنا مالك، أتينا إلى النبي", ""),
    "cr1-a3a8fb": ("right", "agree_right", "", "", "عن عروة بن عامر، - قال أحمد القرشي - قال ذكرت الطيرة", "the dashed nisba is not a link"),
}


def wilson(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(successes: int, n: int) -> dict:
    low, high = wilson(successes, n)
    return {"k": successes, "n": n, "rate": round(successes / n, 3) if n else None, "wilson95": [round(low, 3), round(high, 3)]}


def judge_class(row: dict) -> str:
    if row["judge_reader"] == "W" or row["judge_group"] == "genuine_route":
        return "wrong"
    if row["judge_reader"] in ("R", "RO"):
        return "right"
    return "cannot_tell"


def main() -> int:
    with (PILOT / "private" / "key.tsv").open(encoding="utf-8", newline="") as handle:
        key = {row["opaque"]: row for row in csv.DictReader(handle, delimiter="\t")}
    items, reviews, packet_of = {}, {}, {}
    for packet_path in sorted((PILOT / "packets").glob("packet-*.json")):
        number = packet_path.stem.split("-")[1]
        for item in json.loads(packet_path.read_text(encoding="utf-8"))["items"]:
            items[item["id"]], packet_of[item["id"]] = item, number
        for review in json.loads((PILOT / "outputs" / "pass-1" / f"packet-{number}.output.json").read_text(encoding="utf-8"))["reviews"]:
            reviews[review["id"]] = review

    scored_both_right = sorted(o for o in items if packet_of[o] != "04" and judge_class(key[o]) == "right" and reviews[o]["decision"] == "confirm_reading")
    sample = set(random.Random(SAMPLE_SEED).sample(scored_both_right, 15))

    bad_quotes, rows = [], []
    for opaque in sorted(items, key=lambda o: (packet_of[o], o)):
        item, review, row = items[opaque], reviews[opaque], key[opaque]
        errors = validate_review(review, item)
        judged = judge_class(row)
        accepted = review["decision"] == "confirm_reading"
        agree = (judged == "right" and accepted) or (judged == "wrong" and not accepted)
        actual, verdict, correction, referral, quote, note = VERDICTS.get(opaque, ("assumed_right", "not_adjudicated", "", "", "", "judge right and reviewer confirmed; spot-read text and routes only"))
        if quote and quote not in item["text"]:
            bad_quotes.append(opaque)
        rows.append({"opaque": opaque, "report_id": row["id"], "packet": packet_of[opaque], "set": row["set"], "status": item["status"],
                     "judge": judged, "judge_raw": f"{row['judge_reader']}/{row['judge_group']}".rstrip("/"), "reviewer_decision": review["decision"],
                     "review_valid": "yes" if not errors else "invalid: " + errors[0], "reviewer_uncertainty": review["uncertainty"],
                     "judge_reviewer_agree": "yes" if agree else "no", "in_both_right_sample": "yes" if opaque in sample else "",
                     "actual": actual, "my_verdict": verdict, "correction_check": correction, "referral_check": referral, "quote": quote, "note": note})
    if bad_quotes:
        print("quotes not found in text:", bad_quotes)
        return 1
    missing = sample - set(VERDICTS)
    if missing:
        print("sample items without a verdict:", sorted(missing))
        return 1

    with (HERE / "items.tsv").open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    def count(predicate) -> int:
        return sum(1 for r in rows if predicate(r))

    wrong = [r for r in rows if r["actual"] == "wrong"]
    right = [r for r in rows if r["actual"] in ("right", "assumed_right")]
    corrections = [r for r in rows if r["reviewer_decision"] == "confirm_with_correction"]
    valid_corrections = [r for r in corrections if r["review_valid"] == "yes"]
    judge_decided = [r for r in rows if r["judge"] in ("right", "wrong") and r["actual"] != "unruled"]
    judge_errors = [r for r in judge_decided if (r["judge"] == "right") != (r["actual"] in ("right", "assumed_right"))]
    read_both_right = [r for r in rows if r["my_verdict"] == "agree_right"]
    numbers = {
        "adjudicator": "single model reader (claude-opus-5-5), by hand; see README",
        "items": len(rows), "actual": dict(Counter(r["actual"] for r in rows)),
        "actually_wrong": {"n": len(wrong), "caught": rate(count(lambda r: r in wrong and r["reviewer_decision"] != "confirm_reading"), len(wrong)),
                           "confirmed_missed": rate(count(lambda r: r in wrong and r["reviewer_decision"] == "confirm_reading"), len(wrong)),
                           "by_decision": dict(Counter(r["reviewer_decision"] for r in wrong))},
        "actually_right": {"n": len(right), "read_by_adjudicator": count(lambda r: r in right and r["actual"] == "right"),
                           "confirmed": rate(count(lambda r: r in right and r["reviewer_decision"] == "confirm_reading"), len(right)),
                           "corrected_substantively": rate(count(lambda r: r in right and r["reviewer_decision"] == "confirm_with_correction" and r["correction_check"] != "cosmetic"), len(right)),
                           "corrected_cosmetically": rate(count(lambda r: r in right and r["correction_check"] == "cosmetic"), len(right)),
                           "referred": rate(count(lambda r: r in right and r["reviewer_decision"] == "refer_to_human"), len(right))},
        "unruled": {"n": count(lambda r: r["actual"] == "unruled"), "referred": count(lambda r: r["actual"] == "unruled" and r["reviewer_decision"] == "refer_to_human")},
        "corrections": {"n": len(corrections), "valid": len(valid_corrections), "checks": dict(Counter(r["correction_check"] for r in corrections)),
                        "right_of_valid": rate(sum(r["correction_check"] in ("right", "right_medium", "cosmetic") for r in valid_corrections), len(valid_corrections)),
                        "right_in_substance_of_all": rate(sum(r["correction_check"] != "" for r in corrections), len(corrections)),
                        "substantive_and_right_of_valid": rate(sum(r["correction_check"] in ("right", "right_medium") for r in valid_corrections), len(valid_corrections))},
        "referrals": {"n": count(lambda r: r["reviewer_decision"] == "refer_to_human"), "justified": count(lambda r: r["referral_check"] == "justified")},
        "disagreements_judge_vs_reviewer": dict(Counter(r["my_verdict"] for r in rows if r["judge_reviewer_agree"] == "no")),
        "both_right_reread": {"sample_seed": SAMPLE_SEED, "sample": sorted(sample), "plus_packet_04": 8, "read": len(read_both_right),
                              "right": rate(sum(r["actual"] == "right" for r in read_both_right), len(read_both_right))},
        "judge": {"decided_and_ruled": len(judge_decided), "errors": rate(len(judge_errors), len(judge_decided)), "error_ids": [r["opaque"] for r in judge_errors],
                  "cannot_tell": count(lambda r: r["judge"] == "cannot_tell"), "cannot_tell_decidable_now": count(lambda r: r["judge"] == "cannot_tell" and r["actual"] in ("right", "wrong"))},
        "applied_items_not_confirmed": [{"opaque": r["opaque"], "decision": r["reviewer_decision"], "actual": r["actual"], "correction": r["correction_check"]}
                                        for r in rows if r["status"] == "applied" and r["reviewer_decision"] != "confirm_reading"],
        "packet_04_valid_reviews": count(lambda r: r["packet"] == "04" and r["review_valid"] == "yes"),
    }
    (HERE / "numbers.json").write_text(json.dumps(numbers, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(numbers, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
