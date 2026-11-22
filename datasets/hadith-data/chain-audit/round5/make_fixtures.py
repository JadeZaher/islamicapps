"""Cut round 5's real-row detector fixtures (fixtures.json) from the projection round 4 read (2026.11.22.9). Read-only.

  python -I -X utf8 datasets/hadith-data/chain-audit/round5/make_fixtures.py
Each case: the report's detection text and stored chains as the gate sees them, the chain index (or all), and the codes that
chain must carry (`flag`) or must not carry (`clear`). Cases come from round 4's readings (chain-audit/round4/).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib  # noqa: E402

THAQ = "hadith:thaqalayn:"
# (hadith id, chain id suffix or None for the first chain, mode, code, why)
CASES = [
    (THAQ + "79ed28cbd09d4b084046689d", None, "flag", "not_a_name", "Faqih 175: a whole saying «الدال على الخير كفاعله» is the single link"),
    (THAQ + "05511b17dc9665d7e37e63d8", None, "flag", "not_a_name", "Faqih 20: matn «صاحبهما سبعين ميتة سوء» is the single link"),
    (THAQ + "6170bd3f7dd702e5d70ec60f", None, "flag", "not_a_name", "Faqih 24: asker and Imam in one link «علي بن جعفر أخاه موسى بن جعفر»"),
    (THAQ + "5d638b2449dce025adfae737", None, "flag", "not_a_name", "Faqih 40: «... الجعفري العبد الصالح موسى بن جعفر» in one link"),
    ("hadith:pure-canon:pc_12480", None, "flag", "not_a_name", "Ahmad: «تابع/» stored as a narrator"),
    ("hadith:k6:30303", None, "flag", "not_a_name", "Ibn Majah 89: «أبو الحسن القطان حدثناه خازم بن يحيى» in one link"),
    ("hadith:k6:30662", None, "flag", "not_a_name", "Ibn Majah 448: «أبو الحسن بن سلمة حدثناه أبو حاتم» in one link"),
    ("hadith:k6:14467", None, "flag", "text_names_more_after", "Muslim 7229: «أنه نظر إلى عبد الله بن عمر» lost after the last link"),
    ("hadith:k6:1326", None, "flag", "text_names_more_after", "Bukhari 1373: «أنه سمع أسماء بنت أبي بكر» lost after the last link"),
    ("hadith:k6:25022", None, "flag", "text_names_more_after", "«قالا نشهد على عائشة» lost after the last link"),
    ("hadith:k6:18933", None, "flag", "text_names_more_after", "«قال قرأت على عبد الله بن عمر» lost after the last link"),
    ("hadith:k6:1277", None, "flag", "text_names_more_after", "«قلت من حدثك قال ابن عباس» lost after the last link"),
    ("hadith:k6:1708", None, "flag", "text_names_more_after", "«قال عمرو بن دينار قال ابن عباس» lost after the last link"),
    (THAQ + "a8e6abfbf823602d7a6c46f9", ":0001", "flag", "text_between_links", "al-Kafi 186: two routes joined by «وعن» in one chain"),
    (THAQ + "cc6427c9e7be849e01cae759", ":0001", "flag", "text_between_links", "al-Kafi 85: two routes joined by «وعن» in one chain"),
    ("hadith:openiti:imami:rida_0016#3|16|V01P463", None, "flag", "text_names_more_after", "Rida 16#3: the continuation names Asma bint Umays"),
    ("hadith:pure-canon:pc_74461", None, "clear", "not_a_name", "Pure Canon gloss «سعيد يعني المقبري» beside a real name"),
    ("hadith:pure-canon:pc_86381", None, "clear", "not_a_name", "Pure Canon gloss «سعيد هو ابن أبي أيوب»"),
    ("hadith:pure-canon:pc_81579", None, "clear", "not_a_name", "Pure Canon glosses «علي هو ابن مسهر», «هشام هو ابن عروة»"),
    (THAQ + "7d5e9a501226e5877c3da476", None, "clear", "not_a_name", "al-Kafi «عمن حدثه» stored as a label link"),
    ("hadith:pure-canon:pc_65746", None, "clear", "text_names_more_after", "Pure Canon: the chain field's own later routes are not a lost tail"),
    ("hadith:pure-canon:pc_8394", None, "clear", "text_names_more_after", "Pure Canon: the chain field's own later routes are not a lost tail"),
    ("hadith:k6:5431", None, "clear", "text_names_more_after", "first-person «قال سمعت البراء» is the stored Companion, not a lost source"),
    ("hadith:k6:21155", None, "clear", "text_names_more_after", "first-person «قال سمعت ابن نمير» is stored"),
    (THAQ + "bdf3c6382fc55f17db7ce38b", None, "clear", "work_not_checked", "al-Amali (al-Saduq): correct chain, no longer withheld by work"),
    (THAQ + "62e8c9a4b3832add9df1bb9b", None, "clear", "work_not_checked", "Kamal al-Din: correct chain, no longer withheld by work"),
]


def main() -> None:
    reports = lib.measure.load_projection(lib.READ_R4)
    cases = []
    for hadith_id, chain_suffix, mode, code, why in CASES:
        report = reports[hadith_id]
        chains = report["chains"]
        index = 0 if chain_suffix is None else next(i for i, c in enumerate(chains) if c["id"].endswith(chain_suffix))
        work = report["collection"].split(":", 1)[1]
        cases.append({"hadith_id": hadith_id, "text": report["detection"], "chains": [c["surfaces"] for c in chains],
                      "inherited": [c["inherited"] for c in chains],
                      "tradition": next(n for p, n in lib.measure.TRADITION.items() if report["collection"].startswith(p)),
                      "work": work, "thaqalayn": hadith_id.startswith(THAQ), "routes_from_text": report["from_text"],
                      "chain": index, mode: code, "why": why})
    out = {"source": "round 4 readings (chain-audit/round4/); chains and text as in projection 2026.11.22.9", "cases": cases}
    (HERE / "fixtures.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
