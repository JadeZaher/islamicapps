#!/usr/bin/env python3
"""One-off: faithful manual translations of the 4 Zaydi entries the local
model kept spuriously refusing (valid source text, model flakiness on long
narrations). Conventions match translate_hadith.py: transliterated terms
(ghusl, janaba, salat, nifas, muzabana), honorifics, isnad form. Each is
tagged model="manual:claude-opus-4.7" so the provenance is auditable.
Appended to translations.jsonl; merge prefers highest-confidence clean entry.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(SCRIPT_DIR, "hadith-data", "zaydi-hadith", "translations.jsonl")

T = {
    "zayd_0045": (
        "...more retentive of that than me. So I said: I asked him about the "
        "ghusl from janaba, and he, peace and blessings be upon him and his "
        "family, said: You pour water over your hands before you put them into "
        "your vessel, then you strike your hand to your elbows and clean what "
        "is there, then you strike your hands to the ground and pour water "
        "over them, then you rinse your mouth and sniff up water and blow it "
        "out three times, then you wash your face and forearms three times "
        "each, and wipe your head, and wash your feet, then you pour water "
        "over your head three times, and pour water over your sides, and rub "
        "of your body whatever your hands reach. And I asked him: what may you "
        "have of your wife when she is menstruating? He, peace and blessings "
        "be upon him and his family, said: what is above the waist-wrapper, "
        "and do not look upon what is beneath it. I asked Zayd ibn Ali, peace "
        "be upon him, about postpartum bleeding (nifas); he said: three "
        "menstrual periods — if she sits six [days] then eighteen, if she sits "
        "seven then twenty-one, if she sits ten then thirty days. Zayd ibn "
        "Ali, peace be upon him, said: nifas is not more than forty days. He "
        "said: I asked Zayd ibn Ali, peace be upon him, about the ghusl of the "
        "menstruating and postpartum woman; he, peace be upon him, said: like "
        "the ghusl from janaba. I said: does she undo the hair of her head? "
        "He, peace be upon him, said: no. Umm Salama, may Allah be pleased "
        "with her, asked the Prophet, peace and blessings be upon him and his "
        "family, about that, and he said: three washings suffice you. Zayd ibn "
        "Ali, peace be upon him, said regarding yellowish and reddish "
        "discharge that it is menstruation. And Zayd ibn Ali, peace be upon "
        "him, said: there is no menstruation during pregnancy. And Zayd ibn "
        "Ali, peace be upon him, said: it is not lawful to have intercourse "
        "with a menstruating woman until she performs ghusl, because of His "
        "saying, exalted is He: 'So keep away from women during menstruation "
        "and do not approach them until they are purified; and when they have "
        "purified themselves, then come to them as Allah has commanded you' — "
        "he, peace be upon him, said: from the front. The martyred Imam Abu "
        "al-Husayn Zayd ibn Ali, peace be upon him, said regarding the "
        "menstruating woman whose days increase, that this is menstruation so "
        "long as it is within the ten [days].",
        3,
    ),
    "zayd_0136": (
        "Zayd ibn Ali narrated from his father, from his grandfather, from "
        "Ali, peace be upon him, that he said: When you arrive at a town and "
        "resolve upon staying ten [days], complete [the salat]. Zayd ibn Ali, "
        "peace be upon him, said: The salat is not shortened except on a "
        "journey of three [days]; so when you leave your house intending a "
        "journey of three days or more, shorten [it] once you pass beyond the "
        "houses of your family and your town. Zayd ibn Ali narrated to me from "
        "his father, from his grandfather, from Ali, peace be upon him, from "
        "the Messenger of Allah, peace and blessings be upon him and his "
        "family, that he prayed in Mecca two rak'ahs, two rak'ahs, until he "
        "returned.",
        4,
    ),
    "zayd_0255": (
        "...nothing is upon him. And Zayd ibn Ali, peace be upon him, said "
        "regarding a man who finds only a single poor person and repeats [the "
        "giving] to him over ten days: it suffices him only for one poor "
        "person. And Zayd ibn Ali, peace be upon him, said regarding a man who "
        "breaks an oath while insolvent and fasts, then finds the means to "
        "feed on the third day before the sun sets: his fast is invalidated "
        "and feeding is upon him. I asked Zayd ibn Ali, peace be upon him, "
        "about a man who feeds the People of the Covenant (dhimma) in "
        "expiation of an oath; he said: that does not suffice him, nor does it "
        "suffice him to feed the People of the Covenant from anything Allah "
        "made obligatory in the Quran, but it suffices him to feed them from "
        "the charity of breaking the fast (sadaqat al-fitr). I asked Zayd ibn "
        "Ali, peace be upon him, about a man who swore he would not eat these "
        "dates, then made of them a sweet paste and ate from it; he, peace be "
        "upon him, said: he does not break [the oath]. I said: if he swore not "
        "to eat this fresh date and it became a dry date and he ate from it? "
        "He, peace be upon him, said: he breaks [the oath]. I said: what is "
        "the difference between these two — the paste from the date and the "
        "dry date from the fresh date? He, peace be upon him, said: because "
        "the paste from the date is by conversion and change. Do you not see "
        "that if he swore not to speak to this man and he spoke to a son of "
        "his born afterward, he does not break [the oath], for he is from him; "
        "and likewise if he swore not to eat this ewe and it bore a kid and he "
        "ate from it, he does not break [the oath], for it is from her — this "
        "resembles the paste. But if he swore not to speak to this boy and he "
        "became a man and he spoke to him, he breaks [the oath]; and if he "
        "swore not to eat this lamb and it became a ram and he ate from it, he "
        "breaks [the oath] — this in aspect resembles the fresh date, for this "
        "is not by conversion. He said: a woman asked the Commander of the "
        "Faithful Zayd ibn Ali, peace be upon him, and said: O son of the "
        "Messenger of Allah, I swore I would not eat from the milk of a ewe of "
        "mine, then I made of it clarified butter (samn) and ate from it; he, "
        "peace be upon him, said: there is no breaking [of the oath] upon you. "
        "He said: and butter and shiraz? He, peace be upon him, said: he "
        "breaks [the oath]; and he said: butter and shiraz are not [by] "
        "conversion, but clarified butter is conversion. I asked Zayd ibn Ali, "
        "peace be upon him, about a man who swore not to eat dry dates and ate "
        "fresh dates, or swore not to eat fresh dates and ate dry dates, or "
        "swore not to eat milk and ate shiraz or clarified butter or butter or "
        "cheese; he, peace be upon him, said: he does not break [the oath] in "
        "any of that, for swearing off a thing by its specific self and a "
        "thing not by its specific self differ. He said: I asked Zayd ibn "
        "Ali, peace be upon him, about a boy who swears while he is a boy then "
        "reaches puberty and breaks [the oath]; he, peace be upon him, said: "
        "nothing is upon him; and likewise the disbeliever who swears then "
        "accepts Islam and breaks [the oath], he, peace be upon him, said: "
        "nothing is upon him — Islam demolishes what came before it. And Zayd "
        "ibn Ali, peace be upon him, said: the import of people's oaths is "
        "according to what they intend and resolve; so if they have no "
        "intention, then carry that upon the language of their land and what "
        "they customarily understand, and do not carry it upon what they "
        "disavow.",
        4,
    ),
    "zayd_0348": (
        "Zayd ibn Ali narrated to me from his father, from his grandfather, "
        "from Ali, peace be upon him, who said: The Messenger of Allah, peace "
        "and blessings be upon him and his family, forbade the sale of "
        "muhafala and muzabana, and the sale of trees until they set [fruit], "
        "and the sale of dates until they ripen — meaning they turn yellow or "
        "red. Imam Zayd ibn Ali, peace be upon him, said: the sale of muzabana "
        "is selling dates for dates; muhaqala is selling standing crop for "
        "wheat; and al-izha is the yellowing and reddening. I asked Zayd ibn "
        "Ali, peace be upon him, about a man who buys the fruit before it "
        "matures on condition that he cut it; he, peace be upon him, said: "
        "there is no harm in that. I said: but if he buys it before it matures "
        "on condition that he leave it until it matures? He, peace be upon "
        "him, said: this is not lawful and is not permissible.",
        4,
    ),
}


def main():
    with open(JSONL, "a", encoding="utf-8") as f:
        for hid, (en, conf) in T.items():
            f.write(json.dumps({
                "id": hid,
                "text_en": en.strip(),
                "confidence": conf,
                "model": "manual:claude-opus-4.7",
                "duration_s": 0,
            }, ensure_ascii=False) + "\n")
    print(f"Appended {len(T)} manual translations to {JSONL}")
    for hid, (en, conf) in T.items():
        print(f"  {hid}: conf={conf}, {len(en)} chars")


if __name__ == "__main__":
    main()
