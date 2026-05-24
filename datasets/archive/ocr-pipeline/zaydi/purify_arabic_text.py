#!/usr/bin/env python3
"""
purify_arabic_text.py
=====================
Send all Zaydi hadiths to an LLM (Gemma) for Arabic text purification.

For each hadith the LLM receives:
  - The original raw OCR text (from parsed JSON before mechanical cleanup)
  - The mechanically-cleaned version (after strip_artifacts)

It returns:
  - The purified Arabic text
  - A confidence score 1-4:
      1 = text is clean/near-perfect, minimal or no correction needed
      2 = minor fixes applied (removed stray marks, fixed a letter or two)
      3 = moderate reconstruction (several garbled words fixed, meaning preserved)
      4 = heavy reconstruction (significant portions were garbled/unreadable)

Usage:
    python purify_arabic_text.py                     # Prepare + run
    python purify_arabic_text.py --prepare-only       # Just prepare JSONL
    python purify_arabic_text.py --merge              # Merge results back
    python purify_arabic_text.py --stats              # Show confidence stats
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    import requests as _requests
except ImportError:
    print("ERROR: 'requests' package required.  pip install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARSED_PATH = os.path.join(SCRIPT_DIR, "parsed_zaydi_hadiths.json")
INPUT_PATH = os.path.join(SCRIPT_DIR, "zaydi_for_purification.jsonl")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "zaydi_purified.jsonl")

# Default to local LM Studio; override with --api-url for OpenRouter etc.
DEFAULT_API_URL = "http://localhost:1234/v1/chat/completions"

SYSTEM_PROMPT = """\
You are an expert in classical Arabic hadith manuscripts. You will receive two versions of the same hadith text:

1. **RAW**: The original OCR extraction (may contain symbols, digit noise, broken words)
2. **CLEANED**: A mechanically-cleaned version (artifacts partially removed)

STRICT RULES — follow these exactly:
- ONLY remove garbled/non-Arabic characters: stray digits, ©, ٠, format marks, broken Unicode, misplaced Latin chars, footnote markers
- ONLY fix obvious single-letter OCR substitutions where the correct letter is unambiguous (e.g. ه↔ة when clear from grammar)
- Do NOT reconstruct, rephrase, or add words that aren't in either version
- Do NOT translate or transliterate anything
- Do NOT remove Arabic words even if they seem out of place — they may be correct
- PRESERVE the exact original word order, narrator chain (isnad), and honorifics
- If text appears truncated or cut off mid-sentence, set "snipped": true

Output format — return ONLY valid JSON with exactly these fields:
{"text": "<cleaned Arabic text>", "confidence": <1-4>, "snipped": <true/false>}

Confidence scale:
  1 = text was already clean, minimal or no correction needed
  2 = minor cleanup (removed a few stray marks or symbols)
  3 = moderate cleanup (multiple garbled characters removed, but all Arabic words intact)
  4 = heavy noise (many artifacts removed; some Arabic text may be damaged beyond repair)

"snipped" = true if the hadith appears truncated, cut off mid-sentence, or missing its ending.

Return ONLY the JSON object. No markdown, no explanation, no commentary."""


# ── Mechanical strip (same as clean_arabic_text.py) ──

def strip_artifacts(text: str) -> str:
    text = re.sub(r'\)\s*[٠-٩0-9]+\s*\(\s*‏?\s*', ' ', text)
    text = re.sub(r'\(\s*[؟\?"0-9٠-٩]*\s*["\']?\s*\)', ' ', text)
    text = text.replace('©', '')
    text = re.sub(r'[#*+_|^~\\\[\]{}]', '', text)
    text = text.replace('٠‏', '').replace('٠\u200f', '')
    for ch in '\u200f\u200e\u200c\u200b\u200d\u202c\u202b\u202a\u2069\u2068\u2066\u2067':
        text = text.replace(ch, '')
    text = re.sub(r'\b0{2,}\b', '', text)
    text = re.sub(r'\b0\d{2,}\b', '', text)
    text = re.sub(r'\s[0-9]\s', ' ', text)
    text = re.sub(r'\s\d{3}\s\d{3}\b', '', text)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'«\s*»', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.strip('.,;:!? ')
    return text


# ── Prepare JSONL ──

def prepare():
    """Build input JSONL with both raw and cleaned versions of every hadith."""
    # Load the *original* parsed JSON (with text_arabic as-is from OCR)
    # We need to get the raw text before our mechanical cleanup ran.
    # Since mechanical cleanup already modified parsed_zaydi_hadiths.json,
    # we regenerate raw from the current text (already cleaned) — but we also
    # have the original in zaydi_translated.jsonl which still has text_ar.
    # Use that as the raw source.

    translated_path = os.path.join(SCRIPT_DIR, "zaydi_translated.jsonl")
    raw_texts = {}
    with open(translated_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            raw_texts[row["id"]] = row.get("text_ar", "")

    with open(PARSED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for h in data["hadiths"]:
        hid = f"zayd_{h['hadith_no']:04d}"
        raw = raw_texts.get(hid, h["text_arabic"])
        cleaned = strip_artifacts(raw)
        rows.append({
            "id": hid,
            "hadith_no": h["hadith_no"],
            "text_ar_raw": raw,
            "text_ar_cleaned": cleaned,
        })

    with open(INPUT_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Prepared {len(rows)} hadiths for purification")
    print(f"  Output: {INPUT_PATH}")
    return rows


# ── Call LLM ──

def purify_one(
    raw: str, cleaned: str, model: str, api_url: str,
    api_key: str = "", max_retries: int = 3, timeout: int = 180
) -> tuple[str, int, bool, str | None]:
    """Send both versions to LLM, get purified text + confidence + snipped flag."""
    user_msg = f"**RAW**:\n{raw}\n\n**CLEANED**:\n{cleaned}"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = _requests.post(
                api_url, json=payload, headers=headers, timeout=timeout
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip()
                return parse_llm_response(content, cleaned)
            elif resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "5"))
                time.sleep(wait)
            else:
                time.sleep(3)
        except Exception as e:
            time.sleep(5)

    return cleaned, 0, False, f"Failed after {max_retries} attempts"


def parse_llm_response(content: str, fallback: str) -> tuple[str, int, bool, str | None]:
    """Parse JSON response from LLM. Returns (text, confidence, snipped, error)."""
    content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'\s*```\s*$', '', content, flags=re.MULTILINE)
    content = content.strip()

    try:
        obj = json.loads(content)
        text = obj.get("text", "").strip()
        conf = int(obj.get("confidence", 0))
        snipped = bool(obj.get("snipped", False))
        if not text:
            return fallback, 0, False, "Empty text in response"
        conf = max(1, min(4, conf))
        return text, conf, snipped, None
    except (json.JSONDecodeError, ValueError, TypeError):
        text_match = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
        conf_match = re.search(r'"confidence"\s*:\s*(\d)', content)
        snip_match = re.search(r'"snipped"\s*:\s*(true|false)', content, re.IGNORECASE)
        if text_match:
            text = text_match.group(1)
            text = text.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
            conf = int(conf_match.group(1)) if conf_match else 0
            conf = max(1, min(4, conf)) if conf else 0
            snipped = snip_match and snip_match.group(1).lower() == "true"
            return text, conf, bool(snipped), None
        return fallback, 0, False, f"Unparseable response: {content[:100]}"


# ── Run purification ──

def run(model: str, api_url: str, concurrency: int = 5, resume: bool = True):
    """Run LLM purification on all hadiths."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if "openrouter" in api_url:
        if not api_key:
            env_path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".env"))
            if os.path.exists(env_path):
                with open(env_path, "rb") as bf:
                    raw_bytes = bf.read()
                for enc in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
                    try:
                        text = raw_bytes.decode(enc)
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                for line in text.splitlines():
                    if "OPENROUTER_API_KEY" in line and "=" in line:
                        api_key = line.split("=", 1)[1].strip().strip("'\"")
                        break
        if not api_key:
            print("ERROR: OPENROUTER_API_KEY not found (needed for OpenRouter)")
            sys.exit(1)
        print(f"API key: ...{api_key[-8:]}")
    print(f"API URL: {api_url}")

    # Load input
    rows = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    print(f"Input: {len(rows)} hadiths")

    # Resume support
    done_ids = set()
    if resume and os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line)
                        if obj.get("text_ar_purified"):
                            done_ids.add(obj["id"])
                    except json.JSONDecodeError:
                        pass
        print(f"  Resume: {len(done_ids)} already done")

    remaining = [r for r in rows if r["id"] not in done_ids]
    print(f"  {len(remaining)} to process (concurrency={concurrency})")

    if not remaining:
        print("Nothing to do.")
        return

    out_f = open(OUTPUT_PATH, "a", encoding="utf-8")
    write_lock = threading.Lock()
    completed = 0
    failed = 0
    times = []

    def process(idx_row):
        idx, row = idx_row
        t0 = time.time()
        text, conf, snipped, error = purify_one(
            row["text_ar_raw"], row["text_ar_cleaned"],
            model, api_url, api_key
        )
        elapsed = time.time() - t0
        out_row = {
            "id": row["id"],
            "hadith_no": row["hadith_no"],
            "text_ar_purified": text,
            "confidence": conf,
            "snipped": snipped,
        }
        if error:
            out_row["_error"] = error
        return idx, row["id"], out_row, elapsed, error, conf, snipped

    try:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            futures = {
                executor.submit(process, (i, r)): i
                for i, r in enumerate(remaining, 1)
            }
            snipped_ids = []
            for future in as_completed(futures):
                idx, hid, out_row, elapsed, error, conf, snipped = future.result()
                times.append(elapsed)
                with write_lock:
                    out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
                    out_f.flush()
                if error:
                    failed += 1
                if snipped:
                    snipped_ids.append(hid)
                completed += 1

                snip_tag = " [SNIPPED]" if snipped else ""
                status = f"conf={conf}{snip_tag}" if not error else f"FAILED: {error}"
                print(f"  [{completed}/{len(remaining)}] {hid}: {elapsed:.1f}s {status}")

                if completed % 10 == 0:
                    avg = sum(times[-20:]) / len(times[-20:])
                    eta_s = avg * (len(remaining) - completed)
                    eta = f"{eta_s/60:.1f}m" if eta_s > 60 else f"{eta_s:.0f}s"
                    print(f"    --- {completed} done, {failed} failed | ETA: {eta} ---")
    finally:
        out_f.close()

    print(f"\nDone. Completed: {completed} | Failed: {failed} | Snipped: {len(snipped_ids)}")
    if snipped_ids:
        print(f"  Snipped hadiths: {', '.join(snipped_ids)}")
    print(f"Output: {OUTPUT_PATH}")


# ── Merge results back ──

def merge():
    """Merge purified text + confidence back into parsed JSON."""
    if not os.path.exists(OUTPUT_PATH):
        print(f"ERROR: {OUTPUT_PATH} not found")
        sys.exit(1)

    purified = {}
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            hid = obj["id"]
            text = obj.get("text_ar_purified", "")
            conf = obj.get("confidence", 0)
            snipped = obj.get("snipped", False)
            if text and len(text) > 20:
                purified[hid] = (text, conf, snipped)

    with open(PARSED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged = 0
    snipped_count = 0
    for h in data["hadiths"]:
        hid = f"zayd_{h['hadith_no']:04d}"
        if hid in purified:
            h["text_arabic"] = purified[hid][0]
            h["ocr_confidence"] = purified[hid][1]
            h["snipped"] = purified[hid][2]
            if purified[hid][2]:
                snipped_count += 1
            merged += 1

    with open(PARSED_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Merged {merged}/{len(data['hadiths'])} purified hadiths ({snipped_count} flagged as snipped)")

    # Also regenerate CSVs with confidence column
    regen_csvs(data)


def regen_csvs(data):
    """Regenerate Zaydi CSVs including ocr_confidence column."""
    SOURCE_NAME = "Musnad al-Imam Zayd ibn Ali"
    hadiths = data["hadiths"]

    # Full CSV
    full_path = os.path.join(SCRIPT_DIR, "zaydi_hadiths_full.csv")
    full_fields = [
        "id", "hadith_id", "source", "volume", "chapter_no", "hadith_no",
        "chapter", "category", "chain_indx", "text_ar", "text_en",
        "sanad", "matn_en", "grading_majlisi", "grading_mohseni",
        "grading_behbudi", "gradings_full", "url", "ocr_confidence",
    ]
    with open(full_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=full_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for h in hadiths:
            writer.writerow({
                "id": f"zayd_{h['hadith_no']:04d}",
                "hadith_id": h["hadith_no"],
                "source": SOURCE_NAME,
                "volume": 1,
                "chapter_no": h["chapter_no"],
                "hadith_no": h["hadith_no"],
                "chapter": h["chapter_name_ar"],
                "category": h["chapter_name_ar"],
                "chain_indx": "",
                "text_ar": h["text_arabic"],
                "text_en": h.get("text_english", ""),
                "sanad": h["sanad"],
                "matn_en": "",
                "grading_majlisi": "", "grading_mohseni": "",
                "grading_behbudi": "", "gradings_full": "", "url": "",
                "ocr_confidence": h.get("ocr_confidence", ""),
            })
    print(f"Wrote {full_path}")

    # Clean CSV
    clean_path = os.path.join(SCRIPT_DIR, "zaydi_hadiths_clean.csv")
    clean_fields = [
        "id", "hadith_id", "source", "chapter_no", "hadith_no",
        "chapter", "chain_indx", "text_ar", "text_en", "ocr_confidence",
    ]
    with open(clean_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for h in hadiths:
            writer.writerow({
                "id": f"zayd_{h['hadith_no']:04d}",
                "hadith_id": h["hadith_no"],
                "source": SOURCE_NAME,
                "chapter_no": h["chapter_no"],
                "hadith_no": h["hadith_no"],
                "chapter": h["chapter_name_ar"],
                "chain_indx": "",
                "text_ar": h["text_arabic"],
                "text_en": h.get("text_english", ""),
                "ocr_confidence": h.get("ocr_confidence", ""),
            })
    print(f"Wrote {clean_path}")


def stats():
    """Show confidence distribution from purification results."""
    if not os.path.exists(OUTPUT_PATH):
        print(f"No results yet: {OUTPUT_PATH}")
        return

    counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    errors = 0
    total = 0
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            total += 1
            conf = obj.get("confidence", 0)
            counts[conf] = counts.get(conf, 0) + 1
            if obj.get("_error"):
                errors += 1

    print(f"Purification results ({total} hadiths):")
    labels = {
        1: "Clean/near-perfect",
        2: "Minor fixes",
        3: "Moderate reconstruction",
        4: "Heavy reconstruction",
        0: "Failed/unknown",
    }
    for c in [1, 2, 3, 4, 0]:
        bar = "=" * counts[c]
        print(f"  {c} ({labels[c]:25s}): {counts[c]:>4}  {bar}")
    if errors:
        print(f"  Errors: {errors}")


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Purify Zaydi hadith Arabic text via LLM")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare JSONL, don't run")
    parser.add_argument("--merge", action="store_true", help="Merge results back into parsed JSON + CSVs")
    parser.add_argument("--stats", action="store_true", help="Show confidence distribution")
    parser.add_argument("--model", default="gemma-3-27b-it", help="Model name")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API endpoint (default: local LM Studio)")
    parser.add_argument("--concurrency", type=int, default=1, help="Parallel requests (default: 1 for local)")
    args = parser.parse_args()

    if args.stats:
        stats()
    elif args.merge:
        merge()
    elif args.prepare_only:
        prepare()
    else:
        prepare()
        run(model=args.model, api_url=args.api_url, concurrency=args.concurrency)


if __name__ == "__main__":
    main()
