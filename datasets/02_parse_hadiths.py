#!/usr/bin/env python3
"""
02_parse_hadiths.py  —  Smart LLM-Assisted Hadith Parser
=========================================================
Parse raw OCR text into structured hadith records using local Ollama + Gemma.

Uses Ollama's chat API with tool calling so the LLM can call register_hadith()
for each hadith it identifies in the OCR text. Falls back to JSON extraction
and then regex if tool calling is unavailable.

Input:  raw_ocr_pages.json  (from 01_ocr_extract.py)
Output: parsed_hadiths.json (consumed by 03_translate_ollama.py / 04_generate_csvs.py)

Usage:
    python 02_parse_hadiths.py --input raw_ocr_pages.json --output parsed_hadiths.json
    python 02_parse_hadiths.py --input raw_ocr_pages.json --output parsed_hadiths.json --model gemma3:12b
    python 02_parse_hadiths.py --resume          # resume from progress file
    python 02_parse_hadiths.py --part 1           # process only Part 1
    python 02_parse_hadiths.py --dry-run           # preprocess only, no LLM calls
"""

import argparse
import json
import os
import re
import sys
import time
import unicodedata

# ── HTTP client (same pattern as 03_translate_ollama.py) ─────────────────
try:
    import requests
except ImportError:
    import urllib.request
    import urllib.error
    import json as _json_mod

    class _SimpleRequests:
        @staticmethod
        def post(url, json=None, timeout=120):
            data = _json_mod.dumps(json).encode('utf-8') if json else None
            req = urllib.request.Request(url, data=data,
                                         headers={'Content-Type': 'application/json'})
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
                body = resp.read().decode('utf-8')
                return type('Resp', (), {
                    'status_code': resp.status,
                    'json': lambda: _json_mod.loads(body),
                    'text': body,
                    'ok': resp.status == 200,
                })()
            except urllib.error.HTTPError as e:
                return type('Resp', (), {
                    'status_code': e.code, 'text': str(e), 'ok': False,
                })()

        @staticmethod
        def get(url, timeout=10):
            req = urllib.request.Request(url)
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
                body = resp.read().decode('utf-8')
                return type('Resp', (), {
                    'status_code': resp.status,
                    'json': lambda: _json_mod.loads(body),
                    'text': body,
                    'ok': resp.status == 200,
                })()
            except urllib.error.HTTPError as e:
                return type('Resp', (), {
                    'status_code': e.code, 'text': str(e), 'ok': False,
                })()

    requests = _SimpleRequests()


# ── Constants ────────────────────────────────────────────────────────────
OLLAMA_CHAT_API = 'http://localhost:11434/api/chat'
OLLAMA_GENERATE_API = 'http://localhost:11434/api/generate'
OLLAMA_TAGS_API = 'http://localhost:11434/api/tags'

ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'
DIGIT_MAP = {d: str(i) for i, d in enumerate(ARABIC_DIGITS)}

PART_RANGES = {
    1: (1, 391),
    2: (392, 742),
    3: (743, 882),
    4: (883, 1005),
}

KNOWN_NARRATORS = {
    'الربيع بن حبيب': 60003,
    'أبو عبيدة': 60002,
    'آبو عبيدة': 60002,
    'أبسو عبيدة': 60002,
    'أبسو عبيحدة': 60002,
    'أبر عبيدة': 60002,
    'أبر ع بيدة': 60002,
    'جابر بن زيد': 60001,
    'جسابسر بن زيسد': 60001,
    'جسابر بن زيد': 60001,
    'ابن عباس': 60004,
    'عبدالله بن عباس': 60004,
    'عائشة': 60005,
    'عائثة': 60005,
    'أبي هريرة': 60007,
    'أبو هريرة': 60007,
    'ب هريرة': 60007,
    'أنس بن مالك': 60008,
    'أنسس بسن مال': 60008,
    'أبي سعيد الخدري': 60006,
    'أبو سعيد الخدري': 60006,
    'ابن عمر': 60012,
    'عمر بن الخطاب': 60010,
    'علي بن أبي طالب': 60011,
    'جابر بن عبد الله': 60013,
    'ضمام': 60015,
    'ضمام بن السائب': 60015,
    'محبوب': 60009,
    'أفلح': 60014,
    'عبد الأعلى': 60016,
    'عمار بن ياسر': 60018,
    'أبي ذر': 60019,
    'صحار': 60020,
}


# ── Utility Functions ────────────────────────────────────────────────────

def ar_to_int(s):
    """Convert Arabic/Eastern Arabic numeral string to int."""
    s = s.strip()
    converted = ''
    for ch in s:
        if ch in DIGIT_MAP:
            converted += DIGIT_MAP[ch]
        elif ch.isdigit():
            converted += ch
    return int(converted) if converted else None


def int_to_ar(n):
    """Convert integer to Arabic numeral string."""
    ar_digits = '٠١٢٣٤٥٦٧٨٩'
    return ''.join(ar_digits[int(d)] for d in str(n))


def normalize_arabic(text):
    """Light normalization of Arabic text."""
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def determine_chapter(hadith_no):
    """Assign chapter based on hadith number ranges from the PDF index."""
    CHAPTER_MAP = [
        (1, 174, 13, 'الطهارة', 'Purification (al-Ṭahāra)'),
        (175, 304, 10, 'الصلاة', 'Prayer (al-Ṣalāh)'),
        (305, 330, 11, 'الصوم', 'Fasting (al-Ṣawm)'),
        (331, 391, 9, 'الزكاة', 'Almsgiving (al-Zakāh)'),
        (392, 444, 8, 'الحج', 'Pilgrimage (al-Ḥajj)'),
        (445, 470, 7, 'الجهاد', 'Jihad (al-Jihād)'),
        (471, 489, 6, 'الجنائز', 'Funerals (al-Janāʾiz)'),
        (490, 509, 2, 'الأذكار', 'Remembrance (al-Adhkār)'),
        (510, 528, 14, 'النكاح', 'Marriage (al-Nikāḥ)'),
        (529, 555, 12, 'الطلاق', 'Divorce (al-Ṭalāq)'),
        (556, 587, 5, 'البيوع', 'Sales (al-Buyūʿ)'),
        (588, 623, 1, 'الأحكام', 'Rulings (al-Aḥkām)'),
        (624, 653, 3, 'الأشربة', 'Drinks (al-Ashriba)'),
        (654, 742, 4, 'الإيمان والنذور', 'Faith & Vows (al-Īmān wa-l-Nudhūr)'),
        (743, 882, 0, 'الجزء الثالث', 'Part 3 — Supplementary Reports'),
        (883, 1005, 0, 'الجزء الرابع', 'Part 4 — Mursal Reports'),
    ]
    for start, end, ch_no, ch_ar, ch_en in CHAPTER_MAP:
        if start <= hadith_no <= end:
            return ch_no, ch_ar, ch_en
    return 0, '', ''


def extract_chain_indices(text, part=1):
    """Extract narrator indices from hadith text (enhanced for all parts)."""
    indices = []

    # Check for standard chain (with OCR variant matching)
    has_abu_ubayda = any(name in text for name in
                         ['أبو عبيدة', 'آبو عبيدة', 'أبسو عبيدة', 'أبسو عبيحدة',
                          'أبر عبيدة', 'أبر ع بيدة'])
    has_jabir = any(name in text for name in
                     ['جابر بن زيد', 'جسابسر بن زيسد', 'جسابر بن زيد',
                      'جابر ابن زيد'])
    has_rabi = 'الربيع' in text

    if has_abu_ubayda:
        if has_jabir:
            indices = [60003, 60002, 60001]
        else:
            indices = [60003, 60002]
    elif has_rabi:
        indices = [60003]

    # Part 3-4: "الامام" or "الإمام" often refers to al-Rabi'
    if ('الامام' in text or 'الإمام' in text) and 60003 not in indices:
        indices.insert(0, 60003)

    # Add end-of-chain narrators
    for name, idx in KNOWN_NARRATORS.items():
        if name in text and idx not in indices:
            indices.append(idx)

    # Default chains if nothing detected
    if not indices:
        if part <= 2:
            indices = [60003, 60002, 60001]
        else:
            indices = [60003]

    return indices


# ── Phase 1: Pre-processing ──────────────────────────────────────────────

def strip_footnotes(text):
    """
    Remove footnotes from a page's OCR text.

    Footnotes appear at the bottom of pages with patterns like:
      )ا( قوله ...
      )١( خ: ...
      (١) خ: ...
      ٤٢  (standalone page number)
    """
    lines = text.split('\n')
    if not lines:
        return text

    # Find the first footnote line by scanning from the bottom
    footnote_start = len(lines)
    for i in range(len(lines) - 1, max(0, len(lines) - 8), -1):
        line = lines[i].strip()
        if not line:
            continue
        # Standalone page number (1-3 Arabic digits alone or with minimal text)
        if re.match(r'^[٠-٩]{1,3}\s*$', line):
            footnote_start = min(footnote_start, i)
            continue
        # Footnote marker patterns
        if re.match(r'^[)\]]?\s*[اﺍ٠-٩\d]\s*[(\[]\s*(خ|قوله|نوله|توله|فوله)', line):
            footnote_start = min(footnote_start, i)
            continue
        if re.match(r'^\([٠-٩اﺍ\d]+\)\s*(خ|قوله|نوله|توله|فوله)', line):
            footnote_start = min(footnote_start, i)
            continue
        # Once we hit a non-footnote line scanning upward, stop
        if footnote_start < len(lines):
            break

    # Also strip inline footnote blocks that appear at the end of text
    main_text = '\n'.join(lines[:footnote_start])

    # Remove trailing footnote-like content after the last hadith text
    # Pattern: )ا( or (١) followed by خ: or قوله at end
    main_text = re.sub(
        r'\n\s*[)\]]?\s*[اﺍ٠-٩\d]\s*[(\[]\s*(خ\s*[:.]|قوله|نوله|توله).*$',
        '', main_text, flags=re.DOTALL
    )

    return main_text.strip()


def preprocess_page(text):
    """Clean a single page's OCR text."""
    # Strip footnotes
    text = strip_footnotes(text)
    # Normalize unicode
    text = unicodedata.normalize('NFC', text)
    # Collapse excessive whitespace but preserve newlines
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Remove zero-width characters
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]', '', text)
    return text.strip()


def create_batches(pages, batch_size=3, overlap=1):
    """Create overlapping batches of pages."""
    batches = []
    step = batch_size - overlap
    for i in range(0, len(pages), step):
        batch = pages[i:i + batch_size]
        if batch:
            batches.append(batch)
    return batches


# ── Phase 2: LLM Extraction ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "register_hadith",
            "description": "Register a hadith found in the OCR text. Call this for EVERY hadith you identify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hadith_no": {
                        "type": "integer",
                        "description": "The hadith number (Arabic numeral converted to integer)"
                    },
                    "text_start": {
                        "type": "string",
                        "description": "The first 8-12 words of this hadith's text (copy exactly from OCR, including errors)"
                    },
                    "text_end": {
                        "type": "string",
                        "description": "The last 8-12 words of this hadith's text (copy exactly from OCR, including errors)"
                    }
                },
                "required": ["hadith_no", "text_start", "text_end"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "register_chapter",
            "description": "Register a chapter header (باب) found in the text. These are NOT hadiths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter_no": {
                        "type": "integer",
                        "description": "The chapter number"
                    },
                    "title": {
                        "type": "string",
                        "description": "The chapter title in Arabic"
                    }
                },
                "required": ["chapter_no", "title"]
            }
        }
    },
]

PART_HINTS = {
    1: ("Parts 1-2 hadiths typically start with 'أبو عبيدة عن جابر بن زيد' or "
        "'قال الربيع بن حبيب حدثني'. The standard chain is: "
        "al-Rabi' -> Abu 'Ubayda -> Jabir b. Zayd -> Companion."),
    2: ("Parts 1-2 hadiths typically start with 'أبو عبيدة عن جابر بن زيد' or "
        "'ومن طريقه'. Watch for chapter transitions marked by 'باب' headers."),
    3: ("Part 3 hadiths have diverse chains. Many start with 'قال الربيع بلغنى' or "
        "'قال وأخبرنا' followed by various narrator chains."),
    4: ("Part 4 has disconnected (mursal) reports. Many start with 'الامام عن' or "
        "'جابر بن زيد عن النبى'. Very short hadiths, often 4-5 per page."),
}


def build_system_prompt(part, expected_start, expected_end):
    """Build the system prompt for LLM extraction."""
    return f"""You are a hadith text extraction expert for the Musnad al-Rabi' b. Habib, a classical Islamic hadith collection.
Your task: identify ALL individual hadiths in the OCR text and call register_hadith() for each one.

CRITICAL OCR NOISE PATTERNS (the text has many OCR errors):
- "تال" or "نال" = "قال" (he said)
- "أبسو عبيحدة" or "أبر عبيدة" = "أبو عبيدة" (narrator name)
- "علنه", "عتلته", "عكلنه", "عتلإنة", "يكلظإاتة", "لظإنو" = "عليه" / "صلى الله عليه وسلم"
- "ني" or "نى" = "في" (in)
- Letters may be garbled but the structure is recognizable

HADITH STRUCTURE:
- A hadith starts with an Arabic numeral (٣, ١٠, ٢٥, ١٧٤) followed by a separator (-, _, ., space, parentheses) then the narrator chain
- Numbers may appear as: "٣ -", "(٣)", "٣_", "_٣", "١٠ _", "(١٥٢)", "١٥٧_" etc.
- After the number comes the isnad (chain): names of narrators connected by "عن" (from)

THINGS THAT ARE NOT HADITHS (do NOT register these):
- Footnotes: text starting with "(١) خ:" or "(ا) قوله" — these are manuscript variant notes
- Chapter headers: "باب (N) في [topic]" — register these with register_chapter() instead
- Page numbers: standalone 2-3 digit numbers at line edges
- Commentary by al-Rabi' starting with "قال الربيع" AFTER a hadith (this is part of the previous hadith, not a new one)

CURRENT CONTEXT:
- This text is from Part {part} of the Musnad
- Expected hadith numbers in this batch: approximately {expected_start} to {expected_end}
- {PART_HINTS.get(part, '')}

INSTRUCTIONS:
1. Read through the OCR text carefully
2. For EACH hadith you find, call register_hadith() with:
   - hadith_no: the integer number
   - text_start: first ~8-12 words of the hadith (copied exactly from OCR text, including any errors)
   - text_end: last ~8-12 words of the hadith (copied exactly, before the next hadith number)
3. For chapter headers, call register_chapter()
4. Be thorough — there are typically 3-8 hadiths per page
5. Do NOT skip hadiths even if the text is garbled"""


def check_ollama():
    """Check if Ollama is running."""
    try:
        resp = requests.get(OLLAMA_TAGS_API, timeout=5)
        return resp.ok or resp.status_code == 200
    except Exception:
        return False


def call_ollama_chat(messages, tools, model='gemma3:12b', max_retries=3, timeout=300):
    """Call Ollama chat API with tool calling support."""
    for attempt in range(max_retries):
        try:
            payload = {
                'model': model,
                'messages': messages,
                'tools': tools,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': 8192,
                }
            }
            resp = requests.post(OLLAMA_CHAT_API, json=payload, timeout=timeout)
            if resp.ok or resp.status_code == 200:
                return resp.json()
            else:
                print(f"    API error (attempt {attempt+1}): {resp.status_code}")
                time.sleep(3 * (attempt + 1))
        except Exception as e:
            print(f"    Connection error (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))
    return None


def call_ollama_generate(prompt, model='gemma3:12b', max_retries=3, timeout=300):
    """Fallback: call Ollama generate API for JSON output."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(OLLAMA_GENERATE_API, json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': 8192,
                }
            }, timeout=timeout)
            if resp.ok or resp.status_code == 200:
                return resp.json().get('response', '')
            else:
                print(f"    Generate API error (attempt {attempt+1}): {resp.status_code}")
                time.sleep(3 * (attempt + 1))
        except Exception as e:
            print(f"    Connection error (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))
    return None


def parse_tool_calls(response_data):
    """Extract hadith markers from Ollama tool call response."""
    hadiths = []
    chapters = []

    if not response_data:
        return hadiths, chapters

    message = response_data.get('message', {})
    tool_calls = message.get('tool_calls', [])

    for tc in tool_calls:
        func = tc.get('function', {})
        name = func.get('name', '')
        args = func.get('arguments', {})

        # Handle arguments as string or dict
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue

        if name == 'register_hadith':
            h_no = args.get('hadith_no')
            if h_no and isinstance(h_no, (int, float)):
                hadiths.append({
                    'hadith_no': int(h_no),
                    'text_start': args.get('text_start', ''),
                    'text_end': args.get('text_end', ''),
                })
        elif name == 'register_chapter':
            chapters.append({
                'chapter_no': args.get('chapter_no', 0),
                'title': args.get('title', ''),
            })

    return hadiths, chapters


def parse_json_fallback(response_text):
    """Parse JSON array from free-form LLM response."""
    if not response_text:
        return []

    # Strip markdown code fences
    text = re.sub(r'```json\s*', '', response_text)
    text = re.sub(r'```\s*', '', text)

    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Extract JSON array
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        # Fix trailing commas
        fixed = re.sub(r',\s*([\]}])', r'\1', match.group(0))
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    return []


def build_json_fallback_prompt(ocr_text, part, expected_start, expected_end):
    """Build a prompt for JSON-based extraction (fallback if tool calling fails)."""
    return f"""You are a hadith text extraction expert for the Musnad al-Rabi' b. Habib.
Identify ALL hadiths in this OCR text from Part {part}. Expected numbers: ~{expected_start}-{expected_end}.

OCR ERRORS: "تال"/"نال"="قال", "أبسو عبيحدة"="أبو عبيدة", "علنه"/"عتلته"="عليه"
STRUCTURE: Arabic numeral + separator + narrator chain starting with أبو عبيدة/الربيع
IGNORE: footnotes "(١) خ:", chapter headers "باب (N) في...", page numbers

Return ONLY a JSON array:
[{{"hadith_no": 152, "text_start": "أبو عبيدة عن جابر بن زيد عن ابن عباس", "text_end": "ولم يغسله"}}]

If no hadiths found, return: []

OCR TEXT:
---
{ocr_text}
---"""


def _parse_json_hadiths(json_hadiths):
    """Parse hadith entries from JSON array (handles various key names)."""
    parsed = []
    for h in json_hadiths:
        h_no = h.get('hadith_no') or h.get('number') or h.get('no') or h.get('hadith_number')
        if h_no:
            try:
                parsed.append({
                    'hadith_no': int(h_no),
                    'text_start': h.get('text_start', ''),
                    'text_end': h.get('text_end', ''),
                })
            except (ValueError, TypeError):
                continue
    return parsed


def process_batch_with_tools(pages, part, expected_range, model, try_tools=True):
    """Process a batch of pages using Ollama LLM extraction."""
    # Combine page texts
    ocr_text = ''
    for page in pages:
        ocr_text += f"\n--- Page {page.get('book_page', '?')} ---\n"
        ocr_text += page.get('clean_text', page.get('text', ''))
        ocr_text += '\n'

    expected_start, expected_end = expected_range

    # Strategy 1: Try tool calling (if enabled and model supports it)
    if try_tools:
        system_prompt = build_system_prompt(part, expected_start, expected_end)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract all hadiths from this OCR text:\n\n{ocr_text}"},
        ]
        response = call_ollama_chat(messages, TOOL_DEFINITIONS, model=model,
                                     max_retries=1)  # Only 1 attempt for tools
        if response:
            hadiths, chapters = parse_tool_calls(response)
            if hadiths:
                return hadiths, chapters, 'tools'
            # Check if model returned content instead
            content = response.get('message', {}).get('content', '')
            if content:
                parsed = _parse_json_hadiths(parse_json_fallback(content))
                if parsed:
                    return parsed, [], 'json_from_chat'

    # Strategy 2: JSON generation (primary method for most models)
    json_prompt = build_json_fallback_prompt(ocr_text, part, expected_start, expected_end)
    gen_response = call_ollama_generate(json_prompt, model=model)
    if gen_response:
        parsed = _parse_json_hadiths(parse_json_fallback(gen_response))
        if parsed:
            # Filter to expected range (LLM sometimes returns numbers from wrong parts)
            filtered = [h for h in parsed
                        if expected_start - 20 <= h['hadith_no'] <= expected_end + 20]
            if filtered:
                return filtered, [], 'json_generate'
            # If filtering removed everything, return unfiltered
            return parsed, [], 'json_generate'

    return [], [], 'failed'


# ── Phase 3: Post-processing ─────────────────────────────────────────────

def find_hadith_number_positions(combined_text, confirmed_numbers):
    """
    Find positions of confirmed hadith numbers (as Arabic numerals) in the text.

    Searches for Arabic numeral sequences, keeping only those matching
    LLM-confirmed hadith numbers. When a number appears multiple times
    (e.g., as a footnote or page number), picks the position that fits
    sequentially with surrounding hadiths.
    """
    # Pattern: Arabic numeral sequence with typical hadith number context
    # Must be preceded by start-of-line, whitespace, or bracket
    # Must be followed by optional separator then content
    numeral_pattern = re.compile(
        r'(?:^|\n|\s|[(\[»])'
        r'([٠-٩]{1,4})'
        r'\s*[)\]»]?\s*[-–—_ـ.\s]*',
        re.UNICODE | re.MULTILINE
    )

    confirmed_set = set(confirmed_numbers)
    sorted_confirmed = sorted(confirmed_numbers)

    # Collect all candidate positions for each confirmed number
    candidates = {}  # num -> list of (match_start, text_start_after_num)
    for m in numeral_pattern.finditer(combined_text):
        num = ar_to_int(m.group(1))
        if num is not None and num in confirmed_set:
            candidates.setdefault(num, []).append((m.start(), m.end()))

    # Assign positions: single candidates are easy, multiples need sequencing
    number_positions = {}  # num -> (match_start, text_start)

    # First pass: assign unambiguous (single candidate) positions
    for num in sorted_confirmed:
        if num in candidates and len(candidates[num]) == 1:
            number_positions[num] = candidates[num][0]

    # Second pass: resolve ambiguous positions using sequential context
    for idx, num in enumerate(sorted_confirmed):
        if num in number_positions:
            continue
        if num not in candidates:
            continue

        cands = candidates[num]

        # Find nearest assigned neighbors for context
        prev_end = None
        for p in range(idx - 1, -1, -1):
            if sorted_confirmed[p] in number_positions:
                prev_end = number_positions[sorted_confirmed[p]][1]
                break

        next_start = None
        for n in range(idx + 1, len(sorted_confirmed)):
            if sorted_confirmed[n] in number_positions:
                next_start = number_positions[sorted_confirmed[n]][0]
                break

        # Pick the candidate that fits between prev and next
        best = None
        for start, end in sorted(cands, key=lambda x: x[0]):
            if prev_end is not None and start < prev_end:
                continue
            if next_start is not None and start > next_start:
                continue
            best = (start, end)
            break  # Take the first valid one

        if best is None:
            # Fallback: take whichever is after prev_end (or just the first)
            for start, end in sorted(cands, key=lambda x: x[0]):
                if prev_end is None or start >= prev_end:
                    best = (start, end)
                    break
            if best is None:
                best = cands[0]

        number_positions[num] = best

    return number_positions


def extract_texts_from_combined(combined_text, markers, part_range):
    """
    Extract actual hadith texts using number-based boundary detection.

    Instead of fuzzy-matching text anchors (which fails when many hadiths
    share identical opening phrases), finds Arabic numeral positions of
    LLM-confirmed hadith numbers and extracts text between them.
    """
    if not markers:
        return []

    # Get confirmed numbers from LLM markers
    confirmed_numbers = [m['hadith_no'] for m in markers]

    # Find Arabic numeral positions in the text
    number_positions = find_hadith_number_positions(combined_text, confirmed_numbers)

    # Sort markers by hadith number
    markers_sorted = sorted(markers, key=lambda m: m['hadith_no'])

    results = []
    for i, marker in enumerate(markers_sorted):
        h_no = marker['hadith_no']

        if h_no in number_positions:
            _, text_start = number_positions[h_no]

            # Find end: position of the next found hadith number
            next_start = len(combined_text)
            for j in range(i + 1, len(markers_sorted)):
                next_no = markers_sorted[j]['hadith_no']
                if next_no in number_positions:
                    next_start = number_positions[next_no][0]
                    break

            text_ar = combined_text[text_start:next_start].strip()
        else:
            # Number not found in text — use LLM-provided anchors as content
            text_ar = marker.get('text_start', '')
            text_end = marker.get('text_end', '')
            if text_end and text_end != text_ar:
                text_ar += ' ... ' + text_end

        results.append({
            'hadith_no': h_no,
            'text_ar': text_ar,
        })

    return results


def clean_hadith_text(text):
    """Clean extracted hadith text of footnotes and noise."""
    # Remove inline footnote markers: (١), (٢), (ا)
    text = re.sub(r'\([٠-٩]+\)', '', text)
    text = re.sub(r'\(ا\)', '', text)
    # Remove footnote content lines: )ا( خ: ... or )١( قوله ...
    text = re.sub(r'[)\]]?\s*[اﺍ٠-٩]+\s*[(\[]\s*(خ\s*[:.]|قوله|نوله|توله|فوله)[^\n]*', '', text)
    # Remove standalone page numbers
    text = re.sub(r'\n\s*[٠-٩]{1,3}\s*\n', '\n', text)
    text = re.sub(r'\n\s*[٠-٩]{1,3}\s*$', '', text)
    # Remove page markers we inserted
    text = re.sub(r'---\s*Page\s*\d+\s*---', '', text)
    # Remove chapter headers that leaked in
    text = re.sub(r'[ا]?باب\s*[(\[«]?\s*[٠-٩\d]+\s*[)\]»]?\s*(في|فى|نى)\s+[^\n]{3,50}', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def resolve_duplicates(all_hadiths):
    """Keep the best version when same hadith_no appears from overlapping batches."""
    by_number = {}
    for h in all_hadiths:
        num = h['hadith_no']
        if num not in by_number:
            by_number[num] = h
        else:
            # Keep the one with longer text
            existing_len = len(by_number[num].get('text_ar', ''))
            new_len = len(h.get('text_ar', ''))
            if new_len > existing_len:
                by_number[num] = h
    return list(by_number.values())


def validate_sequence(hadiths):
    """Validate hadith numbers are within expected ranges and remove outliers."""
    validated = []
    for h in hadiths:
        num = h['hadith_no']
        # Check it falls within any known part range
        valid = False
        for part, (start, end) in PART_RANGES.items():
            if start <= num <= end:
                valid = True
                h.setdefault('part', part)
                break
        if valid:
            validated.append(h)
        else:
            # Allow numbers slightly outside ranges (OCR might have small errors)
            if 1 <= num <= 1020:
                validated.append(h)
    return validated


# ── Regex Fallback ───────────────────────────────────────────────────────

def regex_fallback_extract(combined_text, part):
    """
    Last-resort regex extraction without strict lookahead.
    More permissive than the original parser.
    """
    start_range, end_range = PART_RANGES.get(part, (1, 1005))

    # Very permissive: find Arabic numerals that could be hadith numbers
    # Allow various separators and don't require specific following text
    pattern = re.compile(
        r'(?:^|\s|[(\[»])\s*'
        r'([٠-٩]{1,4})'
        r'\s*[)\]»]?\s*[-–—_ـ.]?\s*'
        r'(?=[أآابتجقمونه])',  # Just require any Arabic letter after
        re.UNICODE | re.MULTILINE
    )

    candidates = []
    for m in pattern.finditer(combined_text):
        num = ar_to_int(m.group(1))
        if num and start_range <= num <= end_range:
            candidates.append((m.start(), m.end(), num))

    # Deduplicate and validate sequence
    seen = set()
    unique = []
    candidates.sort(key=lambda x: x[0])
    last_num = 0
    for start, end, num in candidates:
        if num in seen:
            continue
        if num >= last_num or abs(num - last_num) <= 10:
            seen.add(num)
            unique.append((start, end, num))
            last_num = max(last_num, num)

    # Extract text between markers
    hadiths = []
    for i, (start, end, num) in enumerate(unique):
        text_start = end
        text_end = unique[i + 1][0] if i + 1 < len(unique) else len(combined_text)
        raw_text = combined_text[text_start:text_end].strip()
        text_ar = normalize_arabic(raw_text)
        if len(text_ar) > 10:
            hadiths.append({
                'hadith_no': num,
                'text_ar': text_ar,
                'part': part,
            })

    return hadiths


# ── Progress Tracking ────────────────────────────────────────────────────

def save_progress(hadiths, processed_batches, output_path):
    """Save progress for resume capability."""
    progress = {
        'hadiths': hadiths,
        'processed_batches': list(processed_batches),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    progress_path = output_path + '.progress'
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_progress(output_path):
    """Load previous progress."""
    progress_path = output_path + '.progress'
    if os.path.exists(progress_path):
        with open(progress_path, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        return progress.get('hadiths', []), set(progress.get('processed_batches', []))
    return [], set()


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Smart LLM-assisted hadith parser for Musnad al-Rabi\'')
    parser.add_argument('--input', default='raw_ocr_pages.json',
                        help='Input OCR JSON file')
    parser.add_argument('--output', default='parsed_hadiths.json',
                        help='Output parsed JSON file')
    parser.add_argument('--model', default='gemma3:latest',
                        help='Ollama model name')
    parser.add_argument('--batch-size', type=int, default=3,
                        help='Pages per LLM batch (default: 3)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from progress file')
    parser.add_argument('--part', type=int, default=0,
                        help='Process only this part (0=all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preprocess only, no LLM calls')
    parser.add_argument('--regex-only', action='store_true',
                        help='Use regex fallback only (no LLM)')
    args = parser.parse_args()

    # ── Check Ollama ──
    if not args.dry_run and not args.regex_only:
        if not check_ollama():
            print("ERROR: Ollama is not running on localhost:11434")
            print("Please start Ollama first:")
            print(f"  1. Pull model: ollama pull {args.model}")
            print("  2. Ollama should auto-start, or run: ollama serve")
            print("\nAlternatively, use --regex-only for algorithmic extraction.")
            sys.exit(1)
        print(f"Ollama connected. Model: {args.model}")

    # ── Load OCR data ──
    print(f"Loading OCR data from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        pages_data = json.load(f)
    print(f"Loaded {len(pages_data)} pages.")

    # ── Phase 1: Preprocess ──
    print("Phase 1: Pre-processing pages...")
    pages_sorted = sorted(pages_data, key=lambda p: p['pdf_page'])
    for page in pages_sorted:
        page['clean_text'] = preprocess_page(page.get('text', ''))

    # Group by part
    parts_grouped = {}
    for page in pages_sorted:
        p = page.get('part', 1)
        parts_grouped.setdefault(p, []).append(page)

    for p in sorted(parts_grouped):
        print(f"  Part {p}: {len(parts_grouped[p])} pages")

    if args.dry_run:
        print("\nDry run complete. Pre-processed pages ready.")
        # Show a sample preprocessed page
        sample = pages_sorted[0]
        sample_text = sample['clean_text'][:500]
        try:
            print(f"\nSample (page {sample.get('book_page', '?')}):")
            print(sample_text)
        except UnicodeEncodeError:
            print(f"\nSample (page {sample.get('book_page', '?')}): "
                  f"[{len(sample['clean_text'])} chars, cannot display on this console]")
        return

    # ── Load progress ──
    all_markers = []
    processed_batches = set()
    if args.resume:
        all_markers, processed_batches = load_progress(args.output)
        if all_markers:
            print(f"Resumed: {len(all_markers)} hadiths from {len(processed_batches)} batches.")

    # ── Phase 2: Extract ──
    parts_to_process = sorted(parts_grouped.keys())
    if args.part:
        parts_to_process = [p for p in parts_to_process if p == args.part]

    total_batches = 0
    tools_supported = True  # Will be set to False after first tool-calling failure
    method_counts = {'tools': 0, 'json_from_chat': 0, 'json_generate': 0,
                     'regex': 0, 'failed': 0}

    for part_num in parts_to_process:
        part_pages = parts_grouped[part_num]
        expected_range = PART_RANGES.get(part_num, (1, 1005))
        print(f"\nPhase 2: Processing Part {part_num} "
              f"({len(part_pages)} pages, hadiths {expected_range[0]}-{expected_range[1]})...")

        # Create batches
        batches = create_batches(part_pages, batch_size=args.batch_size, overlap=1)
        print(f"  {len(batches)} batches (size={args.batch_size}, overlap=1)")

        for batch_idx, batch in enumerate(batches):
            batch_id = f"p{part_num}_b{batch_idx}"
            if batch_id in processed_batches:
                continue

            # Estimate expected range for this batch
            batch_start_pct = batch_idx / max(len(batches), 1)
            batch_end_pct = min(1.0, (batch_idx + 1) / max(len(batches), 1))
            est_start = int(expected_range[0] + batch_start_pct * (expected_range[1] - expected_range[0]))
            est_end = int(expected_range[0] + batch_end_pct * (expected_range[1] - expected_range[0]))
            est_range = (max(expected_range[0], est_start - 10),
                         min(expected_range[1], est_end + 10))

            page_nums = [p.get('book_page', '?') for p in batch]
            print(f"  Batch {batch_idx+1}/{len(batches)} "
                  f"(pages {page_nums[0]}-{page_nums[-1]}, "
                  f"est. hadiths {est_range[0]}-{est_range[1]})...",
                  end=' ', flush=True)

            t0 = time.time()

            if args.regex_only:
                # Regex-only mode
                combined = '\n'.join(p.get('clean_text', '') for p in batch)
                batch_hadiths = regex_fallback_extract(combined, part_num)
                method = 'regex'
            else:
                # LLM extraction (skip tool calling if it failed before)
                batch_hadiths, batch_chapters, method = process_batch_with_tools(
                    batch, part_num, est_range, args.model,
                    try_tools=tools_supported
                )

                # Disable tool calling after first failure
                if method in ('json_generate', 'json_from_chat') and tools_supported:
                    if batch_idx == 0:
                        tools_supported = False
                        print("(tools disabled) ", end='', flush=True)

                # If LLM failed, try regex fallback
                if not batch_hadiths:
                    combined = '\n'.join(p.get('clean_text', '') for p in batch)
                    batch_hadiths = regex_fallback_extract(combined, part_num)
                    method = 'regex' if batch_hadiths else 'failed'

            elapsed = time.time() - t0
            method_counts[method] = method_counts.get(method, 0) + 1
            print(f"found {len(batch_hadiths)} hadiths ({method}, {elapsed:.1f}s)")

            # If LLM provided anchors, extract actual text from raw OCR
            if method in ('tools', 'json_from_chat', 'json_generate') and batch_hadiths:
                combined_raw = '\n'.join(p.get('clean_text', p.get('text', '')) for p in batch)
                extracted = extract_texts_from_combined(
                    combined_raw, batch_hadiths, est_range
                )
                # Merge extracted text back
                for marker, extracted_h in zip(batch_hadiths, extracted):
                    marker['text_ar'] = extracted_h.get('text_ar', '')
                    marker['part'] = part_num

            all_markers.extend(batch_hadiths)
            processed_batches.add(batch_id)
            total_batches += 1

            # Save progress periodically
            if total_batches % 5 == 0:
                save_progress(all_markers, processed_batches, args.output)
                print(f"    Progress saved: {len(all_markers)} hadiths total.")

    # ── Phase 3: Post-processing ──
    print(f"\nPhase 3: Post-processing {len(all_markers)} raw markers...")

    # Resolve duplicates from overlapping batches
    all_hadiths = resolve_duplicates(all_markers)
    print(f"  After deduplication: {len(all_hadiths)} hadiths")

    # Validate sequence
    all_hadiths = validate_sequence(all_hadiths)
    print(f"  After validation: {len(all_hadiths)} hadiths")

    # Clean texts and assign chapters/chains
    for h in all_hadiths:
        h['text_ar'] = clean_hadith_text(h.get('text_ar', ''))
        ch_no, ch_ar, ch_en = determine_chapter(h['hadith_no'])
        h['chapter_no'] = ch_no
        h['chapter_name'] = ch_ar
        h['chapter_name_en'] = ch_en
        part = h.get('part', 1)
        h['chain_indx'] = ','.join(
            str(x) for x in extract_chain_indices(h['text_ar'], part)
        )
        # Remove internal fields
        h.pop('text_start', None)
        h.pop('text_end', None)

    # Sort by hadith number
    all_hadiths.sort(key=lambda h: h['hadith_no'])

    # ── Stats ──
    print(f"\n{'='*60}")
    print(f"  Results")
    print(f"{'='*60}")
    print(f"  Total hadiths parsed: {len(all_hadiths)}")

    parts_count = {}
    for h in all_hadiths:
        p = h.get('part', 0)
        parts_count[p] = parts_count.get(p, 0) + 1
    for p in sorted(parts_count):
        expected = PART_RANGES.get(p, (0, 0))
        expected_count = expected[1] - expected[0] + 1
        print(f"  Part {p}: {parts_count[p]} hadiths "
              f"(expected ~{expected_count})")

    print(f"\n  Extraction methods: {method_counts}")

    # Report gaps
    all_nums = set(h['hadith_no'] for h in all_hadiths)
    for p, (start, end) in PART_RANGES.items():
        expected = set(range(start, end + 1))
        missing = expected - all_nums
        if missing:
            missing_sorted = sorted(missing)
            if len(missing_sorted) > 20:
                print(f"  Part {p} missing {len(missing_sorted)} hadiths: "
                      f"{missing_sorted[:10]}...{missing_sorted[-5:]}")
            else:
                print(f"  Part {p} missing: {missing_sorted}")

    # Show samples
    for h in all_hadiths[:3]:
        try:
            print(f"\n  Hadith {h['hadith_no']}: {h['text_ar'][:100]}...")
        except UnicodeEncodeError:
            print(f"\n  Hadith {h['hadith_no']}: [{len(h['text_ar'])} chars]")

    # ── Save output ──
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(all_hadiths, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_hadiths)} hadiths -> {args.output}")

    # Clean up progress file
    progress_path = args.output + '.progress'
    if os.path.exists(progress_path):
        os.remove(progress_path)
        print(f"Cleaned up progress file.")


if __name__ == '__main__':
    main()
