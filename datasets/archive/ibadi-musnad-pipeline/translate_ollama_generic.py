#!/usr/bin/env python3
"""
translate_ollama_generic.py
============================
Generic, dataset-agnostic Ollama translator.
Reads a JSONL file, translates a specified field, writes a JSONL file.
Fully resumable via checkpoint (incremental append to output).

Prerequisites:
    - Ollama installed and running locally: https://ollama.com
    - A model pulled: ollama pull gemma3:12b

Usage:
    python translate_ollama_generic.py \\
        --input datasets/hadith-data/pure_canon_classical.jsonl \\
        --output datasets/hadith-data/pure_canon_classical_en.jsonl \\
        --source-field text_ar \\
        --dest-field text_en \\
        --prompt-file datasets/hadith-data/pure_canon_prompt.txt

    # Resume after interruption:
    python translate_ollama_generic.py ... --resume

    # Translate a range:
    python translate_ollama_generic.py ... --start 0 --end 500
"""

import argparse
import io
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ---------------------------------------------------------------------------
# HTTP layer: prefer requests, fall back to urllib
# ---------------------------------------------------------------------------
try:
    import requests as _requests

    class _Http:
        @staticmethod
        def post(url, payload, timeout):
            resp = _requests.post(url, json=payload, timeout=timeout)
            return resp.status_code, resp.json() if resp.ok else {}

        @staticmethod
        def get(url, timeout):
            resp = _requests.get(url, timeout=timeout)
            return resp.status_code, resp.json() if resp.ok else {}

except ImportError:
    import json as _json_mod
    import urllib.request
    import urllib.error

    class _Http:
        @staticmethod
        def post(url, payload, timeout):
            data = _json_mod.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status, _json_mod.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                return e.code, {}
            except Exception as e:
                raise

        @staticmethod
        def get(url, timeout):
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status, _json_mod.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                return e.code, {}


OLLAMA_BASE = "http://localhost:11434"
OLLAMA_GENERATE = f"{OLLAMA_BASE}/api/generate"
OLLAMA_TAGS = f"{OLLAMA_BASE}/api/tags"


def check_ollama(model: str) -> None:
    """Verify Ollama is running; exit with instructions if not."""
    try:
        status, _ = _Http.get(OLLAMA_TAGS, timeout=5)
        if status == 200:
            return
    except Exception:
        pass
    print("ERROR: Ollama is not running on localhost:11434")
    print("To fix:")
    print("  1. Install Ollama: https://ollama.com")
    print(f"  2. Pull model:     ollama pull {model}")
    print("  3. Start server:   ollama serve  (or it auto-starts after install)")
    sys.exit(1)


def warmup_ollama(model: str, warmup_timeout: int = 300) -> None:
    """
    Force Ollama to load the model into memory with a trivial request before
    the real translation loop starts. Without this, the first few real calls
    race the model load and can exhaust retries (observed: 5/5 initial rows
    failing with llama3.1:8b cold-start).
    """
    print(f"Warming up model {model} (loading into memory, up to {warmup_timeout}s)...")
    t0 = time.time()
    payload = {
        "model": model,
        "prompt": "Say OK.",
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 4},
    }
    try:
        status, _data = _Http.post(OLLAMA_GENERATE, payload, timeout=warmup_timeout)
        elapsed = time.time() - t0
        if status == 200:
            print(f"  Warmup OK ({elapsed:.1f}s). Model is resident.")
            return
        print(f"  Warmup returned HTTP {status} after {elapsed:.1f}s — proceeding anyway.")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  Warmup raised {type(e).__name__} after {elapsed:.1f}s: {e}")
        print(f"  Proceeding anyway — the main loop has its own retries.")


def translate_one(
    text: str,
    system_prompt: str,
    model: str,
    temperature: float,
    num_predict: int,
    max_retries: int,
    timeout: int,
) -> tuple[str, str | None]:
    """
    Translate a single text.
    Returns (translated_text, error_message).
    On success error_message is None.
    On failure translated_text is "".
    """
    full_prompt = f"{system_prompt}\n\n{text}"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    for attempt in range(1, max_retries + 1):
        try:
            status, data = _Http.post(OLLAMA_GENERATE, payload, timeout=timeout)
            if status == 200:
                return data.get("response", "").strip(), None
            else:
                msg = f"HTTP {status}"
                print(f"    API error (attempt {attempt}/{max_retries}): {msg}")
                time.sleep(2)
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
    """Read existing output JSONL and return set of ids that already have dest_field."""
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


def compute_eta(completed: int, total_remaining: int, times: list[float]) -> str:
    if not times or completed == 0:
        return "unknown"
    recent = times[-20:]  # rolling window
    avg = sum(recent) / len(recent)
    eta_sec = avg * total_remaining
    if eta_sec < 60:
        return f"{eta_sec:.0f}s"
    elif eta_sec < 3600:
        return f"{eta_sec/60:.1f}m"
    else:
        return f"{eta_sec/3600:.1f}h"


def main():
    parser = argparse.ArgumentParser(
        description="Generic Ollama JSONL translator — dataset-agnostic"
    )
    parser.add_argument("--input", required=True, help="Input JSONL path")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument(
        "--source-field", required=True, help="Field name containing source text"
    )
    parser.add_argument(
        "--dest-field", required=True, help="Field name to write translation into"
    )
    parser.add_argument(
        "--id-field", default="id", help="Field name used as unique id (default: id)"
    )
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Path to .txt file containing the system prompt",
    )
    parser.add_argument("--model", default="gemma3:12b", help="Ollama model name")
    parser.add_argument(
        "--temperature", type=float, default=0.2, help="Sampling temperature"
    )
    parser.add_argument(
        "--num-predict", type=int, default=1024, help="Max tokens to generate"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="0-indexed row to start from (skip first N rows)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="0-indexed exclusive row end (process up to row N)",
    )
    parser.add_argument(
        "--batch-save",
        type=int,
        default=10,
        help="Print ETA every N successful translations",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Retry attempts per translation"
    )
    parser.add_argument(
        "--timeout", type=int, default=120, help="Seconds per Ollama call"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip rows that already have dest-field in the output JSONL",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file (ignored if --resume is set)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of parallel Ollama requests (default: 1, try 3-5 for speedup)",
    )
    args = parser.parse_args()

    # Guard output file
    if os.path.exists(args.output) and not args.resume and not args.overwrite:
        print(
            f"ERROR: Output file already exists: {args.output}\n"
            "Use --resume to continue, or --overwrite to start fresh."
        )
        sys.exit(1)

    # Load prompt
    if not os.path.exists(args.prompt_file):
        print(f"ERROR: Prompt file not found: {args.prompt_file}")
        sys.exit(1)
    with open(args.prompt_file, "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
    print(f"Loaded prompt from: {args.prompt_file}  ({len(system_prompt)} chars)")

    # Check Ollama + warm the model so the first real row doesn't race the load
    check_ollama(args.model)
    print(f"Ollama is running. Model: {args.model}")
    warmup_ollama(args.model)

    # Load input
    print(f"Loading input: {args.input}...")
    rows = load_jsonl(args.input)
    print(f"  {len(rows):,} rows loaded.")

    # Slice to requested range
    start = args.start
    end = args.end if args.end is not None else len(rows)
    rows_slice = rows[start:end]
    print(f"  Processing rows {start}..{min(end, len(rows))-1} ({len(rows_slice):,} rows).")

    # Resume: build set of already-translated ids
    already_done: set[str] = set()
    if args.resume:
        already_done = load_translated_ids(args.output, args.id_field, args.dest_field)
        print(f"  Resume mode: {len(already_done):,} rows already translated, skipping them.")
    elif args.overwrite and os.path.exists(args.output):
        os.remove(args.output)
        print(f"  Overwrite mode: removed existing {args.output}")

    # Open output in append mode (incremental checkpoint)
    out_f = open(args.output, "a", encoding="utf-8")

    count_new = 0
    count_skipped = 0
    count_failed = 0
    elapsed_times: list[float] = []
    write_lock = threading.Lock()

    try:
        remaining = [
            r for r in rows_slice
            if str(r.get(args.id_field, "")) not in already_done
        ]
        total_to_do = len(remaining)
        concurrency = max(1, args.concurrency)
        print(f"  {total_to_do:,} rows to translate (concurrency={concurrency}).")

        # Handle empty-source rows first (fast, no API calls)
        real_work = []
        for row in remaining:
            source_text = row.get(args.source_field, "")
            if not source_text or not str(source_text).strip():
                out_row = dict(row)
                out_row[args.dest_field] = ""
                out_row["_skip_reason"] = "empty_source"
                out_f.write(json.dumps(out_row, ensure_ascii=False) + "\n")
                out_f.flush()
                count_skipped += 1
            else:
                real_work.append(row)

        if count_skipped > 0:
            print(f"  Skipped {count_skipped} rows with empty source field.")

        completed_count = 0

        def process_row(idx_row):
            """Translate a single row. Returns (index, out_row, elapsed, error)."""
            idx, row = idx_row
            row_id = str(row.get(args.id_field, f"row_{idx}"))
            source_text = str(row.get(args.source_field, ""))

            t0 = time.time()
            translation, error = translate_one(
                source_text,
                system_prompt,
                args.model,
                args.temperature,
                args.num_predict,
                args.max_retries,
                args.timeout,
            )
            elapsed = time.time() - t0

            out_row = dict(row)
            out_row[args.dest_field] = translation
            if error:
                out_row["_translation_error"] = error

            return idx, row_id, out_row, elapsed, error, len(translation)

        if concurrency == 1:
            # Sequential path (original behavior)
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

                print(
                    f"  [{completed_count}/{len(real_work)}] {row_id}: {elapsed:.1f}s, {char_count} chars"
                    + (f" [FAILED: {error}]" if error else "")
                )

                if count_new > 0 and count_new % args.batch_save == 0:
                    remaining_count = len(real_work) - completed_count
                    eta = compute_eta(count_new, remaining_count, elapsed_times)
                    print(
                        f"    --- Progress: {count_new} translated, "
                        f"{count_failed} failed, {count_skipped} skipped | "
                        f"ETA: {eta} ---"
                    )
        else:
            # Parallel path
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

                    print(
                        f"  [{completed_count}/{len(real_work)}] {row_id}: {elapsed:.1f}s, {char_count} chars"
                        + (f" [FAILED: {error}]" if error else "")
                    )

                    if count_new > 0 and count_new % args.batch_save == 0:
                        remaining_count = len(real_work) - completed_count
                        eta = compute_eta(count_new, remaining_count, elapsed_times)
                        print(
                            f"    --- Progress: {count_new} translated, "
                            f"{count_failed} failed, {count_skipped} skipped | "
                            f"ETA: {eta} ---"
                        )

    finally:
        out_f.close()

    print()
    print(
        f"Done. New translations: {count_new} | "
        f"Failed: {count_failed} | "
        f"Skipped (empty): {count_skipped}"
    )
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
