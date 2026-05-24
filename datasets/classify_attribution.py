#!/usr/bin/env python3
"""
classify_attribution.py — terminal-authority classifier for hadith narrations
=============================================================================

Determines, for each narration, WHO the saying/action is ultimately
attributed to and at what level of the isnad it stops. This is essential
across traditions: in the Zaydi Musnad alone, hundreds of reports stop at
Imam Ali (mawquf to the Imam) rather than being raised to the Prophet ﷺ —
conflating the two is a serious scholarly error.

Two fields are produced (per the agreed "person + level" design):

  narration_level  — classical isnad terminus:
      marfu   : raised to the Prophet ﷺ (his statement/act/tacit approval),
                including an Imam who narrates *from* the Prophet
      imam    : an Infallible Imam's own statement (Shia: Imami/Zaydi),
                NOT raised to the Prophet — the category being tracked here
      mawquf  : stopped at a Companion (Sunni context)
      maqtu   : stopped at a Successor (Tabi'i)
      unknown : cannot be determined from text/sanad (left honest, not guessed)

  attributed_to    — the specific terminal authority:
      "Prophet Muhammad", "Prophet Muhammad (qudsi)",
      "Imam Ali", "Imam al-Sadiq", "Imam al-Baqir", "Imam al-Kazim",
      "Imam al-Rida", "Imam al-Jawad", "Imam al-Hadi", "Imam al-Askari",
      "Imam al-Mahdi", "Imam al-Hasan", "Imam al-Husayn",
      "Fatima al-Zahra", "Zayd ibn Ali", "Ahl al-Bayt",
      "Companion", "Successor", "unknown"

Design notes:
  - Deterministic and rule-based on Arabic markers (NOT an LLM): attribution
    is scholarly-sensitive and must be auditable and reproducible. Recent
    research also shows LLMs degrade on classical Arabic without grounding.
  - Conservative: ambiguous cases return "unknown" rather than a wrong guess.
  - Prophet attribution always wins: if an Imam narrates from the Prophet,
    the terminus is the Prophet (the Imam is merely a link in the chain).

Usage (standalone, prints a distribution for scholarly review):
    python classify_attribution.py --stats
    python classify_attribution.py --collection zaydi-hadith --sample 20
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "hadith-data")

# Arabic diacritics (tashkeel), tatweel, and Quranic annotation marks. The
# Imami corpus (al-Kafi, etc.) is fully vocalized — "أَبِي عَبْدِ اللَّهِ" —
# so every marker regex MUST run on a diacritic-stripped copy or it silently
# fails to match. Names/text are still stored verbatim; only matching is
# normalized (standard Arabic text-processing practice).
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF = re.compile(r"[آأإٱ]")  # آ أ إ ٱ → ا


def _norm(s: str) -> str:
    """Strip tashkeel/tatweel and unify alef/ya for marker matching."""
    s = _DIACRITICS.sub("", s or "")
    s = _ALEF.sub("ا", s)
    s = s.replace("ى", "ي")  # ى → ي
    return s

# NOTE: every pattern below matches _norm()-ed text — no diacritics, alef
# variants folded to ا, ى folded to ي. Write literals in that normalized form
# (e.g. ابي not أبي, ابائه not آبائه).

# ── Prophet ﷺ attribution (→ marfu) ──────────────────────────────────────
_PROPHET_RE = re.compile(
    r"رسول\s+الله"
    r"|النبي\b"
    r"|صلي\s+الله\s+عليه\s+و(?:سلم|اله|الـه)"
    r"|سمعت\s+رسول\s+الله"
    r"|كان\s+رسول\s+الله"
    r"|ان\s+النبي"
    r"|عن\s+النبي"
)

# Hadith qudsi: Prophet relating directly from God (still marfu, flagged).
_QUDSI_RE = re.compile(
    r"قال\s+الله\s+(?:تعالي|عز\s+وجل|تبارك)"
    r"|في(?:ما)?\s+يرويه?\s+عن\s+رب"
    r"|الحديث\s+القدسي"
)

# ── Imam markers (→ imam, when not raised to the Prophet) ─────────────────
# Ordered: more specific kunya/laqab first. Value = canonical attributed_to.
_IMAM_MARKERS = [
    (re.compile(r"ابي\s+عبد\s+الله(?:\s+الصادق|\s+جعفر)?|جعفر\s+بن\s+محمد|الصادق"), "Imam al-Sadiq"),
    # "Abu Ja'far" alone is ambiguous: al-Baqir vs al-Kulayni (compiler of
    # al-Kafi, "ابو جعفر محمد بن يعقوب", at the head of every chain) vs
    # al-Jawad. Require a Baqir-disambiguating form and explicitly exclude the
    # al-Kulayni patronymic so the compiler is never read as the Imam.
    (re.compile(r"الباقر|ابي\s+جعفر\s+محمد\s+بن\s+علي"
                r"|ابي\s+جعفر(?!\s+محمد\s+بن\s+يعقوب)(?!\s+الثاني)"
                r"\s+عليه\s+السلام"), "Imam al-Baqir"),
    (re.compile(r"ابي\s+الحسن\s+الرضا|علي\s+بن\s+موسي\s+الرضا|الرضا"), "Imam al-Rida"),
    (re.compile(r"ابي\s+الحسن\s+موسي|موسي\s+بن\s+جعفر|الكاظم|ابي\s+ابراهيم"), "Imam al-Kazim"),
    (re.compile(r"ابي\s+جعفر\s+(?:الثاني|الجواد)|الجواد|محمد\s+بن\s+علي\s+التقي"), "Imam al-Jawad"),
    (re.compile(r"ابي\s+الحسن\s+(?:الثالث|علي\s+بن\s+محمد)|الهادي|علي\s+بن\s+محمد\s+النقي"), "Imam al-Hadi"),
    (re.compile(r"ابي\s+محمد\s+(?:الحسن\s+بن\s+علي)?\s*العسكري|العسكري|الحسن\s+بن\s+علي\s+العسكري"), "Imam al-Askari"),
    (re.compile(r"القائم\b|المهدي|صاحب\s+(?:الزمان|الامر)|الحجة\s+بن\s+الحسن"), "Imam al-Mahdi"),
    (re.compile(r"الحسين\s+بن\s+علي|ابي\s+عبد\s+الله\s+الحسين"), "Imam al-Husayn"),
    (re.compile(r"الحسن\s+بن\s+علي(?!\s+العسكري)|ابي\s+محمد\s+الحسن(?!\s+العسكري)"), "Imam al-Hasan"),
    (re.compile(r"زين\s+العابدين|علي\s+بن\s+الحسين|السجاد"), "Imam Zayn al-Abidin"),
    (re.compile(r"فاطمة(?:\s+الزهراء)?|الزهراء"), "Fatima al-Zahra"),
    (re.compile(r"زيد\s+بن\s+علي"), "Zayd ibn Ali"),
    (re.compile(r"امير\s+المؤمنين|علي\s+بن\s+ابي\s+طالب|قال\s+علي\b|عن\s+علي\b"), "Imam Ali"),
]

# Generic Ahl al-Bayt phrasing when a specific Imam can't be pinned down.
_AHL_BAYT_RE = re.compile(r"عن\s+ابائه|اهل\s+البيت|عليهم\s+السلام|عليه\s+السلام")

# Successor (Tabi'i) self-statement cue, Sunni context.
_MAQTU_RE = re.compile(r"عن\s+(?:الحسن|مجاهد|عطاء|قتادة|الزهري|ابراهيم\s+النخعي)\s+قال")

# Musnad Zayd: "حدثني زيد بن علي عن أبيه عن جده عن علي" is the *isnad opener*
# (Zayd is the narrator, not the speaker). The terminus is decided by where
# the matn stops — at the Prophet, at Imam Ali, or at Zayd's own fiqh ruling.
_ZAYDI_OPENER_RE = re.compile(
    r"حدثني\s+زيد\s+بن\s+علي\s+عن\s+ابيه\s+عن\s+جده\s+عن\s+علي"
    r"|زيد\s+بن\s+علي\s+عن\s+ابائه"
)
# Zayd ibn Ali speaking in his own juristic voice (not as isnad link).
_ZAYD_SPEAKER_RE = re.compile(r"(?:^|\s|\.)\(?\s*(?:و)?قال\s+زيد\s+بن\s+علي")
# Imam Ali as the terminal speaker (the saying stops at Ali). Covers the
# Musnad Zayd chain tails "عن (جده) علي بن ابي طالب ... قال" and a bare
# "قال علي" / "امير المؤمنين", where no Prophet attribution follows.
_ALI_SPEAKER_RE = re.compile(
    r"علي\s+بن\s+ابي\s+طالب[^.؟!]*?قال"
    r"|عن\s+علي\b[^.؟!]*?قال"
    r"|قال\s+علي\b"
    r"|امير\s+المؤمنين"
)


def classify(text_ar, sanad=None, tradition="", source=""):
    """Return (attributed_to, narration_level) for one narration.

    Resolution order (Prophet always wins over an Imam in the chain):
      1. Prophet markers           → marfu
      2. Hadith qudsi              → marfu (qudsi)
      3. Specific Imam markers     → imam (Shia traditions)
      4. Ahl al-Bayt, no specific  → imam / Ahl al-Bayt
      5. Sunni Companion stop      → mawquf
      6. Successor self-statement  → maqtu
      7. otherwise                 → unknown
    """
    # All marker regexes expect normalized text (the Imami corpus is fully
    # vocalized; without this, every marker silently fails to match).
    text = _norm(text_ar or "")
    sanad = sanad or []
    sanad_blob = _norm(" ".join(sanad) if isinstance(sanad, list) else str(sanad))

    # Prophet attribution always wins (an Imam may merely be a chain link).
    if _PROPHET_RE.search(text):
        if _QUDSI_RE.search(text):
            return "Prophet Muhammad (qudsi)", "marfu"
        return "Prophet Muhammad", "marfu"
    if _QUDSI_RE.search(text):
        return "Prophet Muhammad (qudsi)", "marfu"

    is_zaydi = tradition == "Zaydi" or "Zayd" in source
    is_imami = tradition == "Imami" or "Rida" in source

    # ── Zaydi Musnad Zayd: resolve the matn terminus, not the isnad opener ──
    if is_zaydi:
        # Strip the standard isnad opener so "زيد بن علي" in the chain head
        # isn't mistaken for the speaker.
        matn = _ZAYDI_OPENER_RE.sub("", text)
        if _ZAYD_SPEAKER_RE.search(matn):
            return "Zayd ibn Ali", "imam"        # Zayd's own fiqh ruling
        if _ALI_SPEAKER_RE.search(text):
            return "Imam Ali", "imam"            # stops at Imam Ali
        for rx, name in _IMAM_MARKERS:
            if name in ("Imam Ali", "Zayd ibn Ali"):
                continue
            if rx.search(matn):
                return name, "imam"
        if _AHL_BAYT_RE.search(text):
            return "Ahl al-Bayt", "imam"
        return "unknown", "unknown"

    # ── Imami (Twelver) and Musnad al-Rida ──
    if is_imami:
        for rx, name in _IMAM_MARKERS:
            if rx.search(text) or rx.search(sanad_blob):
                return name, "imam"
        if _AHL_BAYT_RE.search(text):
            return "Ahl al-Bayt", "imam"
        return "unknown", "unknown"

    # ── Sunni / Ibadi: no Shia Imams; non-Prophet → Companion/Successor ──
    if _MAQTU_RE.search(text):
        return "Successor", "maqtu"
    # A clearly attributed non-Prophet saying by a named early authority is a
    # Companion statement (mawquf) in Sunni/Ibadi usul — never a Shia Imam.
    if _ALI_SPEAKER_RE.search(text) or re.search(r"قال\s+(?:عمر|ابو\s+بكر|عثمان|ابن\s+عباس|ابن\s+مسعود|عائشة)\b", text):
        return "Companion", "mawquf"

    return "unknown", "unknown"


# ── Standalone: distribution + samples for scholarly sanity-check ─────────

def _iter_collection(coll):
    p = os.path.join(BASE_DIR, coll, "parsed_hadiths.json")
    data = json.load(open(p, encoding="utf-8"))
    trad = data.get("tradition", "")
    for h in data.get("hadiths", []):
        yield h, trad


def main():
    ap = argparse.ArgumentParser(description="Classify narration attribution")
    ap.add_argument("--stats", action="store_true",
                    help="Print attribution distribution for every collection")
    ap.add_argument("--collection", help="Show a sample for one collection")
    ap.add_argument("--sample", type=int, default=15)
    args = ap.parse_args()

    colls = ["zaydi-hadith", "ibadi-hadith", "rida-hadith"]

    if args.collection:
        n = 0
        for h, trad in _iter_collection(args.collection):
            who, lvl = classify(h.get("text_ar"), h.get("sanad"),
                                trad, h.get("source", ""))
            print(f"  {h['id']} [{lvl:7} | {who}]  {(h.get('text_ar') or '')[:90]}")
            n += 1
            if n >= args.sample:
                break
        return

    if args.stats:
        for coll in colls:
            who_c, lvl_c = Counter(), Counter()
            for h, trad in _iter_collection(coll):
                who, lvl = classify(h.get("text_ar"), h.get("sanad"),
                                    trad, h.get("source", ""))
                who_c[who] += 1
                lvl_c[lvl] += 1
            total = sum(lvl_c.values())
            print(f"\n=== {coll} (n={total}) ===")
            print("  level :", dict(lvl_c))
            print("  who   :", dict(who_c.most_common(12)))


if __name__ == "__main__":
    main()
