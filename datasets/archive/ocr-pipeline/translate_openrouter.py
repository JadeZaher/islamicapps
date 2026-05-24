#!/usr/bin/env python3
"""
translate_openrouter.py
=======================
Translate JSONL rows using OpenRouter (OpenAI-compatible API).
Supports any model available on OpenRouter. Resumable, with concurrency.

Usage:
    python translate_openrouter.py \
        --input datasets/hadith-data/zaydi-hadith/zaydi_for_translation.jsonl \
        --output datasets/hadith-data/zaydi-hadith/zaydi_retranslated.jsonl \
        --source-field text_ar \
        --dest-field text_en \
        --prompt-file datasets/hadith-data/zaydi-hadith/zaydi_translation_prompt.txt \
        --model google/gemini-2.5-flash-preview \
        --resume

    # Retranslate only specific IDs (e.g. refused ones):
    python translate_openrouter.py ... --ids-file refused_ids.txt
"""

import argparse
import io
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    import requests as _requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def translate_one(
    text: str,
    system_prompt: str,
    model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
    timeout: int,
) -> tuple[str, str | None]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = _requests.post(
                OPENROUTER_URL, json=payload, headers=headers, timeout=timeout
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                return content, None
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "5"))
                print(f"    Rate limited (attempt {attempt}/{max_retries}), waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"    API error (attempt {attempt}/{max_retries}): {msg}")
                time.sleep(3)
        except Exception as e:
            print(f"    Connection error (attempt {attempt}/{max_retries}): {e}")
            time.sleep(5)

    return "", f"Translation failed after {max_retries} attempts"


def load_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_translated_ids(output_path: str, id_field: str, dest_field: str) -> set[str]:
    seen = set()
    if not os.path.exists(output_path):
        return seen
    with open(output_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get(dest_field):
                    seen.add(str(obj.get(id_field, "")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    return seen


def load_id_filter(path: str) -> set[str] | None:
    if not path:
        return None
    ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ids.add(line)
    print(f"  ID filter loaded: {len(ids)} IDs from {path}")
    return ids


def compute_eta(completed: int, total_remaining: int, times: list[float]) -> str:
    if not times or completed == 0:
        return "unknown"
    recent = times[-20:]
    avg = sum(recent) / len(recent)
    eta_sec = avg * total_remaining
    if eta_sec < 60:
        return f"{eta_sec:.0f}s"
    elif eta_sec < 3600:
        return f"{eta_sec / 60:.1f}m"
    else:
        return f"{eta_sec / 3600:.1f}h"


def main():
    parser = argparse.ArgumentParser(
        description="Translate JSONL rows via OpenRouter API"
    )
    parser.add_argument("--input", required=True, help="Input JSONL path")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--source-field", required=True, help="Field with source text")
    parser.add_argument("--dest-field", required=True, help="Field to write translation")
    parser.add_argument("--id-field", default="id", help="Unique ID field (default: id)")
    parser.add_argument("--prompt-file", required=True, help="System prompt .txt file")
    parser.add_argument(
        "--model",
        default="google/gemini-2.5-flash",
        help="OpenRouter model (default: google/gemini-2.5-flash)",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel requests (default: 3)")
    parser.add_argument("--batch-save", type=int, default=10)
    parser.add_argument("--resume", action="store_true", help="Skip already-translated rows")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output file")
    parser.add_argument(
        "--ids-file",
        default=None,
        help="Optional file with one ID per line — only translate these rows",
    )
    args = parser.parse_args()

    # API key
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        # Try loading from .env in project root (handles UTF-8 and UTF-16)
        env_candidates = [
            os.path.join(os.path.dirname(args.input), "..", "..", ".env"),
            os.path.join(os.getcwd(), ".env"),
        ]
        for env_path in env_candidates:
            env_path = os.path.normpath(env_path)
            if os.path.exists(env_path):
                with open(env_path, "rb") as bf:
                    raw = bf.read()
                for enc in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
                    try:
                        text = raw.decode(enc)
                        break
                    except (UnicodeDecodeError, UnicodeError):
                        continue
                else:
                    continue
                for line in text.splitlines():
                    if "OPENROUTER_API_KEY" in line and "=" in line:
                        api_key = line.split("=", 1)[1].strip().strip("'\"")
                        break
                if api_key:
                    break
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment or .env file")
        sys.exit(1)
    print(f"OpenRouter API key: ...{api_key[-8:]}")

    # Guard output
    if os.path.exists(args.output) and not args.resume and not args.overwrite:
        print(f"ERROR: Output exists: {args.output}\nUse --resume or --overwrite.")
        sys.exit(1)

    # Load prompt
    with open(args.prompt_file, "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
    print(f"Prompt: {args.prompt_file} ({len(system_prompt)} chars)")

    # Load input
    rows = load_jsonl(args.input)
    print(f"Input: {len(rows):,} rows from {args.input}")

    # Optional ID filter
    id_filter = load_id_filter(args.ids_file)
    if id_filter is not None:
        rows = [r for r in rows if str(r.get(args.id_field, "")) in id_filter]
        print(f"  Filtered to {len(rows):,} rows matching ID filter")

    # Resume
    already_done: set[str] = set()
    if args.resume:
        already_done = load_translated_ids(args.output, args.id_field, args.dest_field)
        print(f"  Resume: {len(already_done):,} already done, skipping.")
    elif args.overwrite and os.path.exists(args.output):
        os.remove(args.output)

    remaining = [
        r for r in rows if str(r.get(args.id_field, "")) not in already_done
    ]
    # Skip empty source
    real_work = []
    count_skipped = 0
    out_f = open(args.output, "a", encoding="utf-8")
    for row in remaining:
        src = row.get(args.source_field, "")
        if not src or not str(src).strip():
            out_row = dict(row)
            out_row[args.dest_field] = ""
            out_row["_skip_reason"] = "empty_source"
            out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            count_skipped += 1
        else:
            real_work.append(row)

    print(f"  {len(real_work):,} rows to translate (concurrency={args.concurrency})")
    if count_skipped:
        print(f"  Skipped {count_skipped} empty rows")

    count_new = 0
    count_failed = 0
    elapsed_times: list[float] = []
    write_lock = threading.Lock()

    def process_row(idx_row):
        idx, row = idx_row
        row_id = str(row.get(args.id_field, f"row_{idx}"))
        source_text = str(row.get(args.source_field, ""))
        t0 = time.time()
        translation, error = translate_one(
            source_text, system_prompt, args.model, api_key,
            args.temperature, args.max_tokens, args.max_retries, args.timeout,
        )
        elapsed = time.time() - t0
        out_row = dict(row)
        out_row[args.dest_field] = translation
        if error:
            out_row["_translation_error"] = error
        return idx, row_id, out_row, elapsed, error, len(translation)

    try:
        completed_count = 0
        concurrency = max(1, args.concurrency)

        if concurrency == 1:
            for i, row in enumerate(real_work, start=1):
                idx, row_id, out_row, elapsed, error, char_count = process_row((i, row))
                elapsed_times.append(elapsed)
                with write_lock:
                    out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
                    out_f.flush()
                if error:
                    count_failed += 1
                else:
                    count_new += 1
                completed_count += 1
                print(f"  [{completed_count}/{len(real_work)}] {row_id}: {elapsed:.1f}s, {char_count} chars"
                      + (f" [FAILED: {error}]" if error else ""))
                if count_new > 0 and count_new % args.batch_save == 0:
                    eta = compute_eta(count_new, len(real_work) - completed_count, elapsed_times)
                    print(f"    --- {count_new} done, {count_failed} failed | ETA: {eta} ---")
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(process_row, (i, row)): i
                    for i, row in enumerate(real_work, start=1)
                }
                for future in as_completed(futures):
                    idx, row_id, out_row, elapsed, error, char_count = future.result()
                    elapsed_times.append(elapsed)
                    with write_lock:
                        out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
                        out_f.flush()
                    if error:
                        count_failed += 1
                    else:
                        count_new += 1
                    completed_count += 1
                    print(f"  [{completed_count}/{len(real_work)}] {row_id}: {elapsed:.1f}s, {char_count} chars"
                          + (f" [FAILED: {error}]" if error else ""))
                    if count_new > 0 and count_new % args.batch_save == 0:
                        eta = compute_eta(count_new, len(real_work) - completed_count, elapsed_times)
                        print(f"    --- {count_new} done, {count_failed} failed | ETA: {eta} ---")
    finally:
        out_f.close()

    print(f"\nDone. Translated: {count_new} | Failed: {count_failed} | Skipped: {count_skipped}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
