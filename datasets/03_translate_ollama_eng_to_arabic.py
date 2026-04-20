#!/usr/bin/env python3
"""
03_translate_ollama.py
=======================
Translate Arabic hadith text to English using local Ollama inference (Gemma model).
Reads parsed_hadiths.json and produces translated_hadiths.json

Prerequisites:
    - Ollama installed and running locally: https://ollama.com
    - Gemma model pulled: ollama pull gemma3:12b  (or gemma3:4b for lighter)

Usage:
    python 03_translate_ollama.py --input parsed_hadiths.json --output translated_hadiths.json
    python 03_translate_ollama.py --input parsed_hadiths.json --output translated_hadiths.json --model gemma3:4b
    python 03_translate_ollama.py --input parsed_hadiths.json --output translated_hadiths.json --start 1 --end 100
"""

import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    import urllib.request
    import urllib.error

    class SimpleRequests:
        """Minimal requests-like interface using urllib."""
        @staticmethod
        def post(url, json=None, timeout=120):
            data = json_module.dumps(json).encode('utf-8') if json else None
            req = urllib.request.Request(url, data=data,
                                         headers={'Content-Type': 'application/json'})
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
                return type('Response', (), {
                    'status_code': resp.status,
                    'json': lambda: json_module.loads(resp.read().decode('utf-8')),
                    'text': resp.read().decode('utf-8'),
                    'ok': resp.status == 200,
                })()
            except urllib.error.HTTPError as e:
                return type('Response', (), {
                    'status_code': e.code,
                    'text': str(e),
                    'ok': False,
                })()

    import json as json_module
    requests = SimpleRequests()


OLLAMA_API = 'http://localhost:11434/api/generate'

SYSTEM_PROMPT = """You are an expert Islamic studies translator specializing in hadith literature.
Translate the following Arabic hadith text into English accurately.

Rules:
- Preserve narrator chain (isnad) names in transliterated form
- Use ﷺ or (peace be upon him) for the Prophet Muhammad
- Keep Islamic terminology with parenthetical English: e.g., zakāh (almsgiving)
- Translate the matn (content) faithfully
- If the text includes editorial notes from the compiler al-Rabīʿ, mark them as [Compiler's note: ...]
- Output ONLY the English translation, nothing else."""


def translate_text(arabic_text, model='gemma3:12b', max_retries=3):
    """Translate a single Arabic text using Ollama."""
    prompt = f"{SYSTEM_PROMPT}\n\nArabic text:\n{arabic_text}"

    for attempt in range(max_retries):
        try:
            resp = requests.post(OLLAMA_API, json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.2,
                    'num_predict': 1024,
                }
            }, timeout=120)

            if hasattr(resp, 'ok') and resp.ok:
                data = resp.json()
                return data.get('response', '').strip()
            elif resp.status_code == 200:
                data = resp.json()
                return data.get('response', '').strip()
            else:
                print(f"  API error (attempt {attempt+1}): {resp.status_code}")
                time.sleep(2)
        except Exception as e:
            print(f"  Connection error (attempt {attempt+1}): {e}")
            time.sleep(5)

    return f"[Translation failed for hadith text]"


def check_ollama():
    """Check if Ollama is running."""
    try:
        resp = requests.post(OLLAMA_API.replace('/generate', '/tags'),
                             json={}, timeout=5)
        return True
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description='Translate hadiths via Ollama/Gemma')
    parser.add_argument('--input', default='parsed_hadiths.json', help='Input parsed JSON')
    parser.add_argument('--output', default='translated_hadiths.json', help='Output JSON')
    parser.add_argument('--model', default='gemma3:12b', help='Ollama model name')
    parser.add_argument('--start', type=int, default=1, help='Start hadith number')
    parser.add_argument('--end', type=int, default=1005, help='End hadith number')
    parser.add_argument('--batch-save', type=int, default=10,
                        help='Save progress every N translations')
    args = parser.parse_args()

    # Check Ollama
    if not check_ollama():
        print("ERROR: Ollama is not running on localhost:11434")
        print("Please start Ollama first:")
        print("  1. Install: https://ollama.com")
        print(f"  2. Pull model: ollama pull {args.model}")
        print("  3. Ollama should auto-start, or run: ollama serve")
        sys.exit(1)

    print(f"Loading hadiths from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        hadiths = json.load(f)

    # Load existing translations for resuming
    translated = {}
    if os.path.exists(args.output):
        with open(args.output, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            for h in existing:
                if h.get('text_en') and not h['text_en'].startswith('[Translation failed'):
                    translated[h['hadith_no']] = h['text_en']
        print(f"Resuming: {len(translated)} hadiths already translated.")

    # Filter to requested range
    to_translate = [h for h in hadiths
                    if args.start <= h['hadith_no'] <= args.end
                    and h['hadith_no'] not in translated]

    print(f"Translating {len(to_translate)} hadiths using model '{args.model}'...")

    results = list(hadiths)  # Copy all
    count = 0

    for i, hadith in enumerate(to_translate):
        h_no = hadith['hadith_no']
        text_ar = hadith.get('text_ar', '')

        if not text_ar or len(text_ar) < 10:
            print(f"  Hadith {h_no}: skipped (too short)")
            continue

        print(f"  [{i+1}/{len(to_translate)}] Hadith {h_no}...", end=' ', flush=True)
        t0 = time.time()
        text_en = translate_text(text_ar, model=args.model)
        elapsed = time.time() - t0
        print(f"done ({elapsed:.1f}s, {len(text_en)} chars)")

        translated[h_no] = text_en
        count += 1

        # Save progress periodically
        if count % args.batch_save == 0:
            for r in results:
                if r['hadith_no'] in translated:
                    r['text_en'] = translated[r['hadith_no']]
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"    Progress saved: {count} new translations.")

    # Final save
    for r in results:
        if r['hadith_no'] in translated:
            r['text_en'] = translated[r['hadith_no']]
        elif 'text_en' not in r:
            r['text_en'] = ''

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {count} new translations. Total: {len(translated)}. → {args.output}")


if __name__ == '__main__':
    main()
