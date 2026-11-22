import json, sys
from collections import Counter
S = r"C:\Users\atooz\AppData\Local\Temp\claude\8b9ecadf913d98e6\95b7dde3-527e-49ce-8f56-83c964db48b2\scratchpad"
rows = json.load(open(S + r"\eval.json", encoding="utf8"))
OPENITI = {"ibadi:musnad-rabi", "zaydi:musnad-zayd", "imami:sahifat-al-imam-ali-al-rida"}

def share(r):
    return min((mine / total if total else 0) for _, mine, total, _, _ in r["stats"])

def carriers(r):
    return max(d for _, _, _, d, _ in r["stats"])

def opt(r, name):
    """True when the identity stands under the option."""
    one = carriers(r) == 1
    if name == "now":
        return one
    if name == "a":
        return True if r["work"] not in OPENITI else one
    if name.startswith("b"):
        x = int(name[1:]) / 100
        return one or share(r) >= x
    if name.startswith("c"):
        x = int(name[1:]) / 100
        chron = r["prev"] != "conflict" and r["next"] != "conflict" and (r["prev"] in ("possible", "attested") or r["next"] in ("possible", "attested"))
        return one or share(r) >= x or chron
    raise ValueError(name)

if __name__ == "__main__":
    print(len(rows), Counter(r["tradition"] for r in rows))
    loss = [r for r in rows if not r["now_standing"] and r["work"] not in OPENITI]
    print("non-openiti withheld now:", len(loss), Counter(r["tradition"] for r in loss))
    opn = [r for r in rows if r["work"] in OPENITI]
    print("openiti:", len(opn), "stand now", sum(r["now_standing"] for r in opn), Counter(r["work"] for r in opn))
    for name in ["a", "b90", "b95", "b98", "c90", "c95", "c98"]:
        res = Counter()
        for r in rows:
            if r["now_standing"] and r["work"] not in OPENITI:
                res["stood_now_nonopeniti"] += 1
            if r["work"] in OPENITI:
                res["openiti_standing" if opt(r, name) else "openiti_withheld"] += 1
            elif not r["now_standing"]:
                res["restored" if opt(r, name) else "still_withheld"] += 1
            elif r["now_standing"] and not opt(r, name):
                res["now_standing_but_withheld_by_opt"] += 1
        print(name, dict(res))
