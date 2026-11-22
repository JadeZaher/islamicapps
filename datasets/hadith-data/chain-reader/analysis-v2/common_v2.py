"""Shared loading for the v2 analysis: reports, packets, expanded readings of both passes, holds (context/ is imported, never written)."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # chain-reader/
CTX = ROOT / "context"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CTX))
from validate import load_reports, parse_output          # noqa: E402
from expand import expand, canonical, DERIVED_KINDS       # noqa: E402
from holds import compute_holds                           # noqa: E402
from norm import fold_exact, fold_loose, MARKS            # noqa: E402
from score import wilson, stored_route, judge, items_of   # noqa: E402

ISNAD = re.compile(r"(?:ال)?[اإ]سناد|السند|بسنده")
EXCLUDED = set((CTX / "pilot-v2" / "exclude_prompt_fragments.txt").read_text(encoding="utf-8").split())
RIGHT = ("right", "rep", "label_wrong")


def pct(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.0f}% ({100 * lo:.0f}-{100 * hi:.0f})"


def load_packets():
    out = {}
    for p in sorted((CTX / "pilot-v2" / "packets").glob("packet-*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def tradition_group(report):
    work = f"{report['tradition']}:{report['work']}"
    if report["tradition"] == "sunni":
        return "sunni six-book" if report["work"] in ("bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah") else "pure canon"
    if work == "imami:al-kafi":
        return "al-kafi"
    if work == "imami:man-la-yahduruhu-al-faqih":
        return "al-faqih"
    if report["tradition"] == "imami":
        return "other imami"
    return {"ibadi": "al-rabi", "zaydi": "zayd"}[report["tradition"]]


def read_output(folder: str, rid: str):
    path = CTX / "outputs-v2" / folder / f"{rid}.json"
    if not path.is_file():
        return None, "missing"
    try:
        parsed, _ = parse_output(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, f"not_json: {e}"
    if not isinstance(parsed, dict):
        return None, "not_object"
    return parsed, ""


def v1_routes(reading: dict, imam: str = "keep"):
    """Routes as folded surfaces the way v1's scorer sees them: derived links dropped, imam_in_text kept (or dropped), isnad back references dropped."""
    out = []
    for route in reading["routes"]:
        names = tuple(fold_exact(l["surface"]) for l in route["links"]
                      if l["kind"] not in DERIVED_KINDS and not (l["kind"] == "imam_in_text" and imam == "drop")
                      and not (l["kind"] == "back_reference" and ISNAD.search(fold_loose(l["surface"]))))
        if names and names not in out:
            out.append(names)
    return out
