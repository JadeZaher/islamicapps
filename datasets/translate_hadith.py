#!/usr/bin/env python3
"""
translate_hadith.py — Generic hadith translation pipeline
==========================================================

Translates Arabic hadith text to English using a local LLM (LM Studio)
or any OpenAI-compatible API. Designed to work with any collection's
parsed_hadiths.json output from parse_openiti.py.

Features:
  - Parallel translation with configurable concurrency
  - Per-hadith confidence scoring (1-4)
  - Resume support (skips already-translated hadiths)
  - Batch mode with quality checkpoints
  - Generic: works with any collection that has text_ar field

Confidence scale:
  4 = High confidence: clear, unambiguous text
  3 = Good: minor uncertainties in phrasing
  2 = Fair: some words/phrases uncertain
  1 = Low: significant portions unclear or heavily interpolated

Usage:
    python translate_hadith.py --collection zaydi-hadith
    python translate_hadith.py --collection ibadi-hadith --batch-size 50
    python translate_hadith.py --collection rida-hadith --concurrency 2
    python translate_hadith.py --input path/to/parsed_hadiths.json --output path/to/output.jsonl

Output:
    {collection_dir}/translations.jsonl  — one JSON object per line
    Each line: {"id": "...", "text_en": "...", "confidence": 3, "model": "...", "duration_s": 1.2}
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import requests as _requests
except ImportError:
    import urllib.request
    import urllib.error

    class _MinimalRequests:
        """Minimal requests-like wrapper using urllib."""
        class Response:
            def __init__(self, data, status):
                self._data = data
                self.status_code = status
                self.headers = {}
            def json(self):
                return json.loads(self._data)

        def post(self, url, json=None, headers=None, timeout=None):
            data = __builtins__.__import__('json').dumps(json).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers or {})
            req.add_header('Content-Type', 'application/json')
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return self.Response(resp.read().decode('utf-8'), resp.status)
            except urllib.error.HTTPError as e:
                return self.Response(e.read().decode('utf-8'), e.code)
            except Exception:
                return self.Response(b'', 0)

    _requests = _MinimalRequests()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_API_URL = "http://localhost:1234/v1/chat/completions"

SYSTEM_PROMPT = """Translate the Arabic hadith text to English. Follow these rules exactly:

1. Output ONLY the translation wrapped in double quotes, then a confidence line. Nothing else.
2. Word-for-word faithful translation. Do not summarize, paraphrase, or add commentary.
3. Do not explain, analyze, or add notes. Do not write "Translation:" or any prefix.
4. Transliterate standard Islamic terms: salat, wudu, zakat, iman.
5. Honorifics: "peace be upon him", "may Allah be pleased with him/her".
6. Isnad: "X narrated from Y, from Z, who said..."

After the closing quote, write on a new line:
CONFIDENCE: N
Where N is 1-4 (4=clear text, 3=minor uncertainties, 2=some words uncertain, 1=heavily unclear)

Example output:
"Abu Ubayda narrated from Jabir ibn Zayd, from the Prophet, peace be upon him, who said: 'Actions are judged by intentions.'"
CONFIDENCE: 4"""


def load_hadiths(input_path: str) -> list:
    """Load hadiths from parsed_hadiths.json."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('hadiths', data if isinstance(data, list) else [])


def load_done(output_path: str) -> set:
    """Load successfully-translated IDs from output JSONL.

    Entries with an error or empty text are NOT counted as done, so a resume
    re-attempts hadiths that previously hit a transient refusal/failure instead
    of leaving them permanently empty.
    """
    done = set()
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get('error') or not (obj.get('text_en') or '').strip():
                        continue
                    done.add(obj['id'])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


import re

# Reasoning models (DeepSeek-R1, Qwen3) emit a chain-of-thought that LM Studio
# sometimes inlines into the answer; small models also spuriously claim no input
# was given even when the Arabic IS present. Such meta-text must NOT be stored as
# a translation — it is a refusal and the caller should retry. A regex (not a
# substring list) is required because the model phrases it many ways:
# "No Arabic text provided", "No Arabic hadith text was provided", "no text was
# found for translation", etc.
_REFUSAL_RE = re.compile(
    r'no\s+(?:specific\s+|arabic\s+|hadith\s+|input\s+)*text\s+(?:was\s+|is\s+)?'
    r'(?:provided|found|given|present)'
    r'|no\s+text\s+(?:provided|found|given)\s+for\s+translation'
    r'|the\s+prompt\s+is\s+incomplete'
    r'|no\s+accompanying\s+(?:narrative\s+)?text'
    r'|applying\s+the\s+rules\s+to\s+the\s+provided'
    r'|self-correction'
    r'|i\s+(?:cannot|can\'t|am\s+unable\s+to)\s+(?:generate|provide|complete|'
    r'output|produce)\s+(?:a\s+|the\s+|an\s+)?(?:translation|task|output)'
    r'|i\s+must\s+assume\s+the\s+user\s+intended'
    r'|final\s+decision:',
    re.IGNORECASE,
)

# Markers after which DeepSeek dumps reasoning following a (valid) first answer.
# We keep only the text before the first such marker.
_LEAK_CUTOFFS = ("\n***", "\n---", "\n\n**", "\n#", "\n[Source", "\n(Since")


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks, including an unclosed trailing one."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Unclosed <think> with no closing tag: drop everything up to a closing tag
    # if present, otherwise drop the opening tag only.
    if "<think>" in text.lower():
        m = re.search(r"</think>", text, re.IGNORECASE)
        text = text[m.end():] if m else re.sub(r"<think>", "", text, flags=re.IGNORECASE)
    return text.strip()


def _extract_confidence(text: str) -> tuple:
    """Pull a 1-4 confidence score out, tolerating several formats.

    Returns (text_without_confidence_line, confidence_or_None).
    """
    pat = re.compile(
        r'["\']?\s*(?:CONFIDENCE|confidence)\s*["\']?\s*[:=]\s*["\']?\s*([1-4])',
    )
    m = pat.search(text)
    conf = int(m.group(1)) if m else None
    text = pat.sub("", text)
    text = re.sub(r'\n?\s*CONFIDENCE.*$', "", text, flags=re.IGNORECASE | re.MULTILINE)
    return text.strip(), conf


def parse_response(content: str) -> tuple:
    """Extract (translation, confidence) from an LLM response.

    Returns ("", 0) when the response is a refusal / pure reasoning leak so the
    caller's retry path re-requests it instead of storing garbage. A successful
    parse returns the faithful translation and a 1-4 confidence (default 3 when
    the model omitted the score but produced a valid translation).
    """
    text = _strip_think(content).strip()
    text, confidence = _extract_confidence(text)

    # Take the FIRST double-quoted segment (non-greedy). The prompt asks for the
    # translation wrapped in quotes; greedy matching would span into any later
    # leaked reasoning that also contains quotes.
    quoted = re.search(r'"([^"]{15,})"', text, re.DOTALL)
    if quoted:
        text = quoted.group(1).strip()
    else:
        # No quotes: cut at the first reasoning-leak marker, keep the prefix.
        cut = len(text)
        for marker in _LEAK_CUTOFFS:
            i = text.find(marker)
            if i != -1:
                cut = min(cut, i)
        text = text[:cut].strip().strip('"').strip()

    for prefix in ('Translation:', 'English Translation:', 'English:', 'Answer:'):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    # Refusal / meta-text leak → signal retry.
    if not text or len(text) < 15 or _REFUSAL_RE.search(text):
        return "", 0

    return text, (confidence if confidence else 3)


def translate_one(
    hadith: dict, model: str, api_url: str,
    api_key: str = "", max_retries: int = 3, timeout: int = 300
) -> dict:
    """Translate a single hadith. Returns result dict."""
    text_ar = hadith.get('text_ar', '')
    if not text_ar or len(text_ar) < 10:
        return {
            'id': hadith['id'],
            'text_en': '',
            'confidence': 0,
            'error': 'Text too short',
            'model': model,
            'duration_s': 0,
        }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Include source context for better translation
    source_info = hadith.get('source', '')
    tradition = hadith.get('tradition', '')
    context_note = ""
    if source_info or tradition:
        context_note = f"\n[Source: {source_info} ({tradition} tradition)]"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{text_ar}{context_note}"},
        ],
        "temperature": 0.15,
        # A faithful hadith translation + confidence line is well under 2k
        # tokens even for the longest narrations. The old 8192 (sized for
        # reasoning models) let non-reasoning models ramble for minutes on
        # rare inputs; 2048 bounds worst-case latency without truncating.
        "max_tokens": 2048,
    }

    t0 = time.time()
    for attempt in range(1, max_retries + 1):
        try:
            resp = _requests.post(api_url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                msg = resp.json()["choices"][0]["message"]
                # Handle thinking models (Qwen3.5, DeepSeek) where output
                # may be in 'content' or 'reasoning_content'
                content = (msg.get("content") or "").strip()
                if not content:
                    # Some thinking models put everything in reasoning_content
                    reasoning = (msg.get("reasoning_content") or "").strip()
                    if reasoning:
                        # Extract the translation from the end of reasoning
                        content = reasoning
                text_en, confidence = parse_response(content)
                duration = round(time.time() - t0, 1)

                if not text_en or len(text_en) < 5:
                    continue  # refusal/empty → retry

                return {
                    'id': hadith['id'],
                    'text_en': text_en,
                    'confidence': confidence,
                    'model': model,
                    'duration_s': duration,
                    '_raw': content,  # popped to .raw.jsonl sidecar by run_batch
                }
            elif resp.status_code == 429:
                wait = min(int(resp.headers.get("Retry-After", "10")), 60)
                time.sleep(wait)
            else:
                time.sleep(3)
        except Exception as e:
            if attempt < max_retries:
                time.sleep(5)

    return {
        'id': hadith['id'],
        'text_en': '',
        'confidence': 0,
        'error': f'Failed after {max_retries} attempts',
        'model': model,
        'duration_s': round(time.time() - t0, 1),
    }


def run_batch(
    hadiths: list, output_path: str, model: str, api_url: str,
    api_key: str = "", concurrency: int = 2, batch_size: int = 0,
):
    """Translate hadiths with parallelism, resume support, and progress reporting."""
    done_ids = load_done(output_path)
    todo = [h for h in hadiths if h['id'] not in done_ids]

    if batch_size > 0:
        todo = todo[:batch_size]

    if not todo:
        print("  All hadiths already translated!")
        return 0, 0

    total = len(todo)
    completed = 0
    failed = 0
    confidences = []
    t_start = time.time()

    print(f"  {total} to translate (concurrency={concurrency})")
    print(f"  Model: {model}")
    print(f"  API: {api_url}")

    # Open output file for appending. Raw model responses go to a sidecar so a
    # future parser fix can re-derive translations without re-running the model.
    outfile = open(output_path, 'a', encoding='utf-8')
    raw_path = output_path.rsplit('.', 1)[0] + '.raw.jsonl'
    rawfile = open(raw_path, 'a', encoding='utf-8')

    try:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(translate_one, h, model, api_url, api_key): h
                for h in todo
            }

            for future in as_completed(futures):
                result = future.result()
                completed += 1

                if result.get('error'):
                    failed += 1
                    tag = "FAIL"
                else:
                    confidences.append(result['confidence'])
                    tag = f"C{result['confidence']}"

                # Split raw response to the sidecar; keep translations.jsonl clean
                raw = result.pop('_raw', None)
                if raw is not None:
                    rawfile.write(json.dumps(
                        {'id': result['id'], 'raw': raw}, ensure_ascii=False) + '\n')
                    rawfile.flush()

                # Write immediately
                outfile.write(json.dumps(result, ensure_ascii=False) + '\n')
                outfile.flush()

                # Progress every 10 or at the end
                if completed % 10 == 0 or completed == total:
                    elapsed = time.time() - t_start
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta_s = (total - completed) / rate if rate > 0 else 0
                    eta_m = eta_s / 60
                    avg_conf = sum(confidences) / len(confidences) if confidences else 0
                    print(f"  [{completed}/{total}] {failed} failed | "
                          f"avg confidence: {avg_conf:.1f} | "
                          f"ETA: {eta_m:.1f}m")
                elif completed <= 5:
                    # Show first few for quick feedback
                    preview = result.get('text_en', '')[:60]
                    print(f"  [{completed}/{total}] {result['id']}: {tag} | "
                          f"{result.get('duration_s', 0)}s | {preview}...")
    finally:
        outfile.close()
        rawfile.close()

    elapsed = time.time() - t_start
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    print(f"\n  Done in {elapsed/60:.1f}m. "
          f"Translated: {completed - failed} | Failed: {failed} | "
          f"Avg confidence: {avg_conf:.2f}")

    return completed - failed, failed


def quality_report(output_path: str):
    """Print a quality summary from the translations JSONL."""
    if not os.path.exists(output_path):
        print("  No output file found.")
        return

    results = []
    with open(output_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not results:
        print("  No results found.")
        return

    total = len(results)
    errors = sum(1 for r in results if r.get('error'))
    confs = [r['confidence'] for r in results if not r.get('error')]

    print(f"\n  Quality Report: {output_path}")
    print(f"  Total: {total} | Errors: {errors}")
    if confs:
        from collections import Counter
        dist = Counter(confs)
        print(f"  Confidence distribution:")
        for c in [4, 3, 2, 1]:
            count = dist.get(c, 0)
            pct = count / len(confs) * 100
            bar = '#' * int(pct / 2)
            print(f"    {c}: {count:4d} ({pct:5.1f}%) {bar}")
        print(f"  Average: {sum(confs)/len(confs):.2f}")

    # Show worst translations (confidence 1)
    low = [r for r in results if r.get('confidence') == 1 and not r.get('error')]
    if low:
        print(f"\n  Low confidence translations ({len(low)}):")
        for r in low[:5]:
            preview = r.get('text_en', '')[:80]
            print(f"    {r['id']}: {preview}...")


def merge_translations(input_path: str, output_path: str):
    """Merge translations back into parsed_hadiths.json."""
    # Load translations
    translations = {}
    with open(output_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                en = (obj.get('text_en') or '').strip()
                # Skip errors, empties, and any residual refusal/leak text so a
                # contaminated line can never overwrite a good one.
                if obj.get('error') or len(en) < 15 or _REFUSAL_RE.search(en):
                    continue
                # Prefer the highest-confidence clean entry for each id.
                prev = translations.get(obj['id'])
                if prev is None or obj.get('confidence', 0) >= prev.get('confidence', 0):
                    translations[obj['id']] = obj
            except json.JSONDecodeError:
                pass

    # Load and update parsed hadiths
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = 0
    for h in data.get('hadiths', []):
        t = translations.get(h['id'])
        if t:
            h['text_en'] = t['text_en']
            h['translation_confidence'] = t['confidence']
            h['translation_model'] = t['model']
            updated += 1

    with open(input_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  Merged {updated} translations into {input_path}")
    return updated


def main():
    parser = argparse.ArgumentParser(
        description='Translate hadith collections from Arabic to English')
    parser.add_argument('--collection', type=str,
                        help='Collection directory name under hadith-data/ '
                             '(e.g., zaydi-hadith, ibadi-hadith, rida-hadith)')
    parser.add_argument('--input', type=str,
                        help='Direct path to parsed_hadiths.json')
    parser.add_argument('--output', type=str,
                        help='Direct path for translations.jsonl output')
    parser.add_argument('--model', type=str, default='',
                        help='Model name (auto-detected from LM Studio if empty)')
    parser.add_argument('--api-url', type=str, default=DEFAULT_API_URL,
                        help=f'API endpoint (default: {DEFAULT_API_URL})')
    parser.add_argument('--api-key', type=str, default='',
                        help='API key (not needed for local LM Studio)')
    parser.add_argument('--concurrency', type=int, default=2,
                        help='Parallel requests (default: 2 for local)')
    parser.add_argument('--batch-size', type=int, default=0,
                        help='Translate N hadiths then stop (0 = all)')
    parser.add_argument('--report', action='store_true',
                        help='Print quality report for existing translations')
    parser.add_argument('--merge', action='store_true',
                        help='Merge translations back into parsed_hadiths.json')

    args = parser.parse_args()

    # Resolve paths
    if args.collection:
        base = os.path.join(SCRIPT_DIR, 'hadith-data', args.collection)
        input_path = os.path.join(base, 'parsed_hadiths.json')
        output_path = os.path.join(base, 'translations.jsonl')
    elif args.input:
        input_path = args.input
        output_path = args.output or input_path.replace('.json', '_translations.jsonl')
    else:
        parser.error('Specify --collection or --input')
        return

    if args.output:
        output_path = args.output

    # Auto-detect model from LM Studio
    model = args.model
    if not model:
        try:
            models_url = args.api_url.replace('/chat/completions', '/models')
            import urllib.request as _ur
            with _ur.urlopen(models_url, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for m in data.get('data', []):
                    if 'embed' not in m['id'].lower():
                        model = m['id']
                        break
        except Exception:
            pass
        if not model:
            model = 'default'
        print(f"  Auto-detected model: {model}")

    if args.report:
        quality_report(output_path)
        return

    if args.merge:
        merge_translations(input_path, output_path)
        return

    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    hadiths = load_hadiths(input_path)
    print(f"\n{'='*60}")
    print(f"Hadith Translation Pipeline")
    print(f"{'='*60}")
    print(f"  Collection: {args.collection or input_path}")
    print(f"  Total hadiths: {len(hadiths)}")

    translated, failed = run_batch(
        hadiths, output_path, model, args.api_url,
        args.api_key, args.concurrency, args.batch_size,
    )

    quality_report(output_path)

    if failed == 0 and translated > 0:
        print(f"\n  All translations complete. Run with --merge to update parsed_hadiths.json")


if __name__ == '__main__':
    main()
