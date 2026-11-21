#!/usr/bin/env python3
"""Review-only English candidates: mechanical honorific substitution and tencent/hy-mt2-30b-a3b translation.

Subcommands: glyph (no API), select (dry-run row selection), translate (OpenRouter, journaled).
Design notes live in machine_translation_candidates/README.md section "Hy-MT2 pipeline".
Every event is candidate_only + machine_unreviewed; nothing here writes canonical data.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("mt_generator", HERE / "generate_machine_translation_candidates.py")
gen = importlib.util.module_from_spec(_spec)
sys.modules["mt_generator"] = gen
_spec.loader.exec_module(gen)
_regen_spec = importlib.util.spec_from_file_location("regen_unified_csvs", HERE / "regen_unified_csvs.py")
regen = importlib.util.module_from_spec(_regen_spec)
sys.modules["regen_unified_csvs"] = regen
_regen_spec.loader.exec_module(regen)

MODEL = "tencent/hy-mt2-30b-a3b"
PIPELINE = "hy-mt2-openrouter-v1"
PROMPT_VERSION = "hy-mt2-default-en-prompt-v1"
GLYPH_PIPELINE = "mechanical-honorific-glyph-substitution-v1"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
CONTEXT_TOKENS = 8192
MAX_COMPLETION_TOKENS = 4096
PRICE_PROMPT = 0.000000074
PRICE_COMPLETION = 0.000000295
CHUNK_TARGET_CHARS = 2500
CHUNK_HARD_LIMIT_CHARS = 5500
ARABIC_TOKENS_PER_CHAR = 0.6  # measured ~0.54 on 2 pilot probes; padded for safety
TEMPERATURE = 0.7  # model card recommendation for 30B-A3B
REQUEST_TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 6
USER_AGENT = "translation-batch-client/1.0"
PROMPT_TEMPLATE = (
    "Translate the following text into English. Note that you should only output the "
    "translated result without any additional explanation:\n\n{source_text}"
)
MODEL_RECORD_EXCLUSIONS = {
    "thaqalayn:06840b21d9e61e1ab351aec4",  # Kitab al-Ghayba Introduction/paratext (README)
    "thaqalayn:2a1ca7a8bc366eadfcbcb80f",
}
MASTER = HERE / "development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz"
CANDIDATE_DIR = HERE / "machine_translation_candidates"
RUN_DIR = HERE / "diagnostics/translation-run"

ARABIC_LETTER = re.compile(r"[ء-يٱ-ە]")
ARABIC_SCRIPT = gen.ARABIC_RE
# Honorific ligatures with conventional English renderings (U+FDFA, U+FDFB).
LIGATURES = {
    "\ufdfa": "peace and blessings be upon him",
    "\ufdfb": "may His glory be exalted",
}
LIGATURE_RE = re.compile(r"\(\s*([ﷺﷻ])(?:\s*\))?|([ﷺﷻ])")  # "(sig)", unclosed "(sig", or bare sig
SENTENCE_END_RE = re.compile(r"(?<=[.؟!?۔])[\s\u200f\u200e]+")
ECHO_RE = re.compile(
    r"translate the following text|without any additional explanation|only output the translated",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- pure logic


def glyph_substitution(text_en: str) -> tuple[str, int] | None:
    """Replace honorific ligatures by English; None unless every Arabic-script char is a ligature."""
    leftovers = {ch for ch in ARABIC_SCRIPT.findall(text_en)} - set(LIGATURES)
    if leftovers or not any(ch in text_en for ch in LIGATURES):
        return None
    count = 0

    def render(match: re.Match) -> str:
        nonlocal count
        count += 1
        return "(" + LIGATURES[match.group(1) or match.group(2)] + ")"

    return LIGATURE_RE.sub(render, text_en), count


def split_sentences(text_ar: str, target: int = CHUNK_TARGET_CHARS, hard: int = CHUNK_HARD_LIMIT_CHARS):
    """Greedy-pack whole sentences into chunks <= target; None when one sentence exceeds hard limit.

    Returns [(start, end)] offsets into text_ar; chunks partition the text with no gaps.
    """
    text = text_ar.strip()
    if len(text) <= target:
        return [(0, len(text))]
    bounds, last = [], 0
    for match in SENTENCE_END_RE.finditer(text):
        bounds.append((last, match.end()))
        last = match.end()
    if last < len(text):
        bounds.append((last, len(text)))
    if any(end - start > hard for start, end in bounds):
        return None
    chunks, current_start, current_end = [], bounds[0][0], bounds[0][0]
    for start, end in bounds:
        if current_end > current_start and end - current_start > target:
            chunks.append((current_start, current_end))
            current_start = start
        current_end = end
    chunks.append((current_start, current_end))
    return chunks


def classify_row(row: dict) -> dict:
    """Bucket one master row: glyph_only | needs_model(kind) | ok | not_translatable."""
    text_en, text_ar = row["text_en"], row["text_ar"]
    issue = regen.translation_issue(text_en, text_ar)
    if not issue:
        return {"issue": "", "bucket": "ok"}
    if not ARABIC_LETTER.search(text_ar or ""):
        return {"issue": issue, "bucket": "no_arabic_source"}
    if issue != "arabic_leakage":
        return {"issue": issue, "bucket": issue}
    if glyph_substitution(text_en) is not None:
        return {"issue": issue, "bucket": "glyph_only"}
    arabic_letters = len(ARABIC_LETTER.findall(text_en))
    latin_letters = len(re.findall(r"[A-Za-z]", text_en))
    if arabic_letters == 0:
        return {"issue": issue, "bucket": "non_honorific_glyph_only"}
    total = arabic_letters + latin_letters
    ratio = arabic_letters / total if total else 1.0
    runs = re.findall(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+(?:[\s،,.;:()\[\]\"'-]+[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]+)*", text_en)
    longest = max((len(run.split()) for run in runs), default=0)
    if ratio >= 0.5:
        bucket = "fully_arabic"
    elif longest > 3 or ratio >= 0.10:
        bucket = "partial_untranslated"
    else:
        bucket = "names_or_terms_only"
    return {"issue": issue, "bucket": bucket}


HONORIFIC_PHRASE_RE = re.compile(
    r"peace and blessings be upon (?:him|them)(?: and his family)?|peace be upon (?:him|them(?: all)?)|"
    r"may allah (?:be pleased with (?:him|her|them)|bless him and his family)",
    re.IGNORECASE,
)
SCREEN_VERSION = "screen-v2"
MIN_LATIN_TO_ARABIC_RATIO = 1.0  # existing accepted Gemini candidates span 1.5-2.3
MAX_LATIN_TO_ARABIC_RATIO = 3.2


def _max_repeat(words: list[str], size: int) -> int:
    grams = Counter(" ".join(words[i : i + size]) for i in range(max(0, len(words) - size + 1)))
    return max(grams.values(), default=0)


def screen_translation(text_en: str, text_ar: str, finish_reason: str) -> list[str]:
    """Release-QA screen (generator's candidate checks) plus echo, truncation, ratio and loop guards."""
    errors = list(gen.candidate_validation_errors(text_en, text_ar))
    if finish_reason != "stop":
        errors.append("truncated_finish_reason_" + str(finish_reason))
    if ECHO_RE.search(text_en or ""):
        errors.append("prompt_echo")
    arabic = gen.arabic_letter_count(text_ar)
    latin = gen.latin_letter_count(text_en)
    if arabic >= 40:
        ratio = latin / arabic
        if ratio < MIN_LATIN_TO_ARABIC_RATIO:
            errors.append("length_ratio_too_short")
        elif ratio > MAX_LATIN_TO_ARABIC_RATIO:
            errors.append("length_ratio_too_long")
    english_words = HONORIFIC_PHRASE_RE.sub(" ", text_en or "").lower().split()
    arabic_words = gen.normalized_arabic_search_view(text_ar)[0].split()
    # A repeated English 10-gram is a loop only if the Arabic does not itself repeat that often.
    if _max_repeat(english_words, 10) >= 3 and _max_repeat(english_words, 10) > _max_repeat(arabic_words, 4):
        errors.append("repetition_loop")
    return list(dict.fromkeys(errors))


def joined_english(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part.strip())


# --------------------------------------------------------------------------- data access


def iter_master():
    csv.field_size_limit(2**31 - 1)
    with gzip.open(MASTER, "rt", encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def master_sha256() -> str:
    digest = hashlib.sha256()
    with MASTER.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_row(row: dict) -> dict:
    return {key: row[key] for key in ("record_id", "source_record_id", "source", "tradition", "hadith_no", "provenance_source")}


def append_event(path: Path, event: dict) -> None:
    gen.append_jsonl(path, event, 120)


def read_journal(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def journal_cost(paths) -> float:
    total = 0.0
    for path in paths:
        for event in read_journal(path):
            total += float(event.get("model_cost_usd") or 0.0)
    return total


# --------------------------------------------------------------------------- glyph subcommand


def command_glyph(args) -> int:
    out = Path(args.output)
    if out.exists() and not args.overwrite_new_file:
        print(f"refusing: {out} exists", file=sys.stderr)
        return 2
    rows_written, replacements, skipped = 0, 0, Counter()
    tmp = out.with_suffix(".jsonl.partial")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in iter_master():
            info = classify_row(row)
            if info["bucket"] != "glyph_only":
                continue
            result = glyph_substitution(row["text_en"])
            text_en, count = result
            errors = list(gen.candidate_validation_errors(text_en, row["text_ar"]))
            if regen.translation_issue(text_en, row["text_ar"]):
                errors.append("release_issue_" + regen.translation_issue(text_en, row["text_ar"]))
            if errors:
                skipped[",".join(errors)] += 1
                continue
            event = {
                "record_id": row["record_id"],
                "arabic_sha256": gen.text_sha256(row["text_ar"]),
                "text_en": text_en,
                "original_text_en_sha256": gen.exact_text_sha256(row["text_en"]),
                "glyph_replacements": count,
                "candidate_only": True,
                "substitution_kind": "mechanical_substitution",
                "translation_source": GLYPH_PIPELINE,
                "translation_model": None,
                "translation_review_status": "machine_unreviewed",
                "validation_status": "accepted_mechanical_unreviewed",
                "validation_errors": [],
                "input_issue": "translation:arabic_leakage",
                "created_at": args.timestamp,
                "source_row": source_row(row),
                "ligature_map": {f"U+{ord(k):04X}": v for k, v in LIGATURES.items()},
            }
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            rows_written += 1
            replacements += count
    tmp.replace(out)
    print(json.dumps({"rows": rows_written, "replacements": replacements, "rejected_by_qa": dict(skipped)}))
    return 0


# --------------------------------------------------------------------------- selection


def build_work(args) -> tuple[list[dict], dict]:
    """Return deterministic work items (rows needing the model) and bucket statistics."""
    buckets, work = Counter(), []
    existing = set()
    queue = HERE / "diagnostics/translation/review_queue.jsonl"
    if queue.exists():
        existing = {json.loads(line)["record_id"] for line in queue.open(encoding="utf-8")}
    for row in iter_master():
        info = classify_row(row)
        buckets[info["bucket"]] += 1
        bucket = info["bucket"]
        if bucket in ("ok", "glyph_only", "no_arabic_source", "non_honorific_glyph_only"):
            continue
        if row["record_id"] in MODEL_RECORD_EXCLUSIONS:
            buckets["excluded_paratext"] += 1
            continue
        phase = "names_terms" if bucket == "names_or_terms_only" else "no_usable_english"
        work.append({"row": row, "bucket": bucket, "phase": phase, "has_prior_candidate": row["record_id"] in existing})
    return work, dict(buckets)


def plan_item(item: dict) -> dict:
    text_ar = item["row"]["text_ar"].strip()
    chunks = split_sentences(text_ar)
    item["text_ar"] = text_ar
    item["chunks"] = chunks
    item["skip_reason"] = None if chunks else "sentence_over_hard_limit_no_defensible_split"
    return item


def pilot_selection(work: list[dict], size: int, seed: int) -> list[dict]:
    """Stratified: tradition x length tercile, with chain-branch and Qur'an-quote rows forced in."""
    rng = random.Random(seed)
    for item in work:
        item.setdefault("text_ar", item["row"]["text_ar"].strip())
    # Pilot rows need a fully-intact master English for nothing; length drawn from Arabic.
    quran = re.compile(r"قال الله|قوله تعالى|﴿|\{.*?\}|\(.*?وَ.*?\)")
    branch = re.compile(r"(?:ح|\(ح\)|\bح\b)\s")
    pool = [i for i in work if len(i["text_ar"]) <= 5500]
    picked, seen = [], set()

    def take(candidates, n):
        candidates = [c for c in candidates if c["row"]["record_id"] not in seen]
        rng.shuffle(candidates)
        for c in candidates[:n]:
            seen.add(c["row"]["record_id"])
            picked.append(c)

    take([i for i in pool if branch.search(i["text_ar"]) and len(i["text_ar"]) > 300], 8)
    take([i for i in pool if quran.search(i["text_ar"])], 8)
    take([i for i in pool if len(i["text_ar"]) > 2500], 4)
    traditions = ["Sunni", "Imami", "Zaydi", "Ibadi"]
    bands = [(0, 300), (300, 1200), (1200, 2500)]
    per_cell = max(1, (size - len(picked)) // (len(traditions) * len(bands)) + 1)
    for tradition in traditions:
        for low, high in bands:
            take([i for i in pool if i["row"]["tradition"] == tradition and low <= len(i["text_ar"]) < high], per_cell)
    rng.shuffle(picked)
    if len(picked) < size:
        take(pool, size - len(picked))
    return picked[:size]


def command_select(args) -> int:
    work, buckets = build_work(args)
    planned = [plan_item(i) for i in work]
    summary = {
        "master_buckets": buckets,
        "model_work_rows": len(planned),
        "by_phase": dict(Counter(i["phase"] for i in planned)),
        "by_bucket": dict(Counter(i["bucket"] for i in planned)),
        "by_tradition": dict(Counter(i["row"]["tradition"] for i in planned)),
        "skipped_unsplittable": sum(1 for i in planned if i["skip_reason"]),
        "split_rows": sum(1 for i in planned if i["chunks"] and len(i["chunks"]) > 1),
        "total_chunks": sum(len(i["chunks"] or []) for i in planned),
        "total_arabic_chars": sum(len(i["text_ar"]) for i in planned),
    }
    print(json.dumps(summary, indent=1))
    return 0


# --------------------------------------------------------------------------- transport


def load_key() -> str:
    data = json.loads(Path("C:/Users/atooz/.pi/agent/models.json").read_text(encoding="utf-8"))
    return data["providers"]["openrouter-free"]["apiKey"]


class TransportError(Exception):
    def __init__(self, kind, status=None, cost_unknown=False):
        super().__init__(kind)
        self.kind, self.status, self.cost_unknown = kind, status, cost_unknown


def call_model(key: str, text_ar: str, max_tokens: int) -> dict:
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(source_text=text_ar)}],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "provider": {"data_collection": "deny", "allow_fallbacks": False},
    }
    payload = json.dumps(body).encode("utf-8")
    delay = 2.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(
            API_URL,
            data=payload,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                parsed = json.loads(response.read().decode("utf-8"))
            if parsed.get("error"):
                code = parsed["error"].get("code")
                if code in (429, 502, 503, 504) and attempt < MAX_ATTEMPTS:
                    time.sleep(delay + random.random())
                    delay = min(delay * 2, 60)
                    continue
                raise TransportError("embedded_error_%s" % code, code)
            parsed["_attempts"] = attempt
            return parsed
        except urllib.error.HTTPError as error:
            status = error.code
            retry_after = error.headers.get("Retry-After")
            error.read()
            if status in (429, 500, 502, 503, 504) and attempt < MAX_ATTEMPTS:
                wait = min(float(retry_after), 120) if retry_after and retry_after.isdigit() else delay
                time.sleep(wait + random.random())
                delay = min(delay * 2, 60)
                continue
            raise TransportError("http_%d" % status, status)
        except (TimeoutError, urllib.error.URLError, OSError) as error:
            if attempt < MAX_ATTEMPTS:
                time.sleep(delay + random.random())
                delay = min(delay * 2, 60)
                continue
            raise TransportError("network_or_timeout", None, cost_unknown=True) from error
    raise TransportError("exhausted")


# --------------------------------------------------------------------------- translate subcommand


class Budget:
    def __init__(self, spent: float, cap: float):
        self.spent, self.cap, self.lock, self.stopped = spent, cap, threading.Lock(), False

    def reserve(self, worst_case: float) -> bool:
        with self.lock:
            if self.stopped or self.spent + worst_case > self.cap:
                self.stopped = True
                return False
            self.spent += worst_case
            return True

    def settle(self, reserved: float, actual: float) -> None:
        with self.lock:
            self.spent += actual - reserved


def translate_item(item: dict, key: str, args, budget: Budget, output: Path) -> dict:
    row, text_ar = item["row"], item["text_ar"]
    arabic_hash = gen.text_sha256(row["text_ar"])
    started = time.time()
    parts, chunk_events, cost, usage_total, errors_transport = [], [], 0.0, Counter(), None
    finish_reasons, response_ids, attempts = [], [], 0
    for index, (start, end) in enumerate(item["chunks"]):
        chunk = text_ar[start:end].strip()
        prompt_estimate = int(len(chunk) * ARABIC_TOKENS_PER_CHAR) + 60
        max_tokens = min(MAX_COMPLETION_TOKENS, CONTEXT_TOKENS - prompt_estimate - 32)
        worst = prompt_estimate * PRICE_PROMPT + max_tokens * PRICE_COMPLETION
        if max_tokens < 256 or not budget.reserve(worst):
            errors_transport = "budget_stop" if max_tokens >= 256 else "context_budget"
            break
        try:
            response = call_model(key, chunk, max_tokens)
        except TransportError as error:
            budget.settle(worst, worst if error.cost_unknown else 0.0)
            cost += worst if error.cost_unknown else 0.0
            errors_transport = error.kind
            break
        usage = response.get("usage") or {}
        actual = usage.get("cost")
        if actual is None:
            actual = usage.get("prompt_tokens", 0) * PRICE_PROMPT + usage.get("completion_tokens", 0) * PRICE_COMPLETION
        budget.settle(worst, float(actual))
        cost += float(actual)
        choice = (response.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content") or "").strip()
        finish_reasons.append(choice.get("finish_reason"))
        response_ids.append(response.get("id"))
        attempts += response.get("_attempts", 1)
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage_total[k] += usage.get(k, 0)
        parts.append(text)
        chunk_events.append(
            {
                "chunk_index": index,
                "source_start": start,
                "source_end": end,
                "source_sha256": gen.exact_text_sha256(chunk),
                "translation": text,
                "finish_reason": choice.get("finish_reason"),
                "response_model": response.get("model"),
                "usage": usage,
            }
        )
    event = {
        "record_id": row["record_id"],
        "arabic_sha256": arabic_hash,
        "run_label": args.run_label,
        "phase": item["phase"],
        "input_bucket": item["bucket"],
        "input_issue": "translation:" + regen.translation_issue(row["text_en"], row["text_ar"]),
        "has_prior_machine_candidate": item["has_prior_candidate"],
        "candidate_only": True,
        "translation_source": PIPELINE,
        "translation_model": MODEL,
        "translation_review_status": "machine_unreviewed",
        "prompt_version": PROMPT_VERSION,
        "screen_version": SCREEN_VERSION,
        "created_at": args.timestamp,
        "source_row": source_row(row),
        "source_length_chars": len(text_ar),
        "split": {"chunks": len(item["chunks"]), "boundary": "sentence", "offsets": [list(c) for c in item["chunks"]]},
        "generation": {"temperature": TEMPERATURE, "stream": False, "provider_policy": {"data_collection": "deny", "allow_fallbacks": False}},
        "model_cost_usd": cost,
        "model_usage": dict(usage_total),
        "model_response_ids": response_ids,
        "finish_reasons": finish_reasons,
        "transport_attempts": attempts,
        "latency_seconds": round(time.time() - started, 2),
        "chunk_results": chunk_events,
    }
    if errors_transport or len(parts) != len(item["chunks"]):
        event.update({"validation_status": "error", "validation_errors": [errors_transport or "incomplete"], "text_en": None})
    else:
        text_en = joined_english(parts)
        errors = screen_translation(text_en, text_ar, "stop" if all(f == "stop" for f in finish_reasons) else "length")
        for chunk_event, (start, end) in zip(chunk_events, item["chunks"]):
            chunk_errors = screen_translation(chunk_event["translation"], text_ar[start:end], chunk_event["finish_reason"])
            chunk_event["validation_errors"] = chunk_errors
        event.update(
            {
                "text_en": text_en,
                "translation_sha256": gen.exact_text_sha256(text_en),
                "validation_errors": errors,
                "validation_status": "accepted_machine_unreviewed" if not errors else "rejected",
            }
        )
    append_event(output, event)
    return event


def command_translate(args) -> int:
    output = Path(args.output).resolve()
    if output.parent != CANDIDATE_DIR.resolve() and output.parent != RUN_DIR.resolve():
        print("output must be under machine_translation_candidates/ or diagnostics/translation-run/", file=sys.stderr)
        return 2
    work, _ = build_work(args)
    planned = [plan_item(i) for i in work]
    if args.phase:
        planned = [i for i in planned if i["phase"] == args.phase]
    if args.pilot_size:
        planned = pilot_selection([i for i in planned if not i["skip_reason"]], args.pilot_size, args.seed)
        planned = [plan_item(i) for i in planned]
    skipped = [i for i in planned if i["skip_reason"]]
    planned = [i for i in planned if not i["skip_reason"]]
    if args.limit:
        planned = planned[: args.limit]
    done = {}
    for event in read_journal(output):
        if event["validation_status"] in ("accepted_machine_unreviewed", "rejected") and event.get("input_bucket"):
            done[(event["record_id"], event["arabic_sha256"])] = event
    for extra in args.skip_from or []:
        for event in read_journal(Path(extra)):
            if event["validation_status"] in ("accepted_machine_unreviewed", "rejected"):
                done[(event["record_id"], event["arabic_sha256"])] = event
    todo = [i for i in planned if (i["row"]["record_id"], gen.text_sha256(i["row"]["text_ar"])) not in done]
    prior = journal_cost(sorted(p for p in CANDIDATE_DIR.glob("openrouter_hy_mt2_30b_a3b_*.jsonl") if "rescreened" not in p.name and not p.name.endswith("_skipped.jsonl")))
    print(json.dumps({"planned": len(planned), "already_done": len(planned) - len(todo), "to_run": len(todo), "skipped_unsplittable": len(skipped), "prior_spend_usd": round(prior, 6)}))
    if args.dry_run:
        return 0
    if skipped:
        skip_path = output.with_name(output.stem + "_skipped.jsonl")
        with skip_path.open("w", encoding="utf-8", newline="\n") as handle:
            for i in skipped:
                handle.write(json.dumps({"record_id": i["row"]["record_id"], "arabic_sha256": gen.text_sha256(i["row"]["text_ar"]), "source_length_chars": len(i["text_ar"]), "reason": i["skip_reason"], "created_at": args.timestamp}, ensure_ascii=False) + "\n")
    key = load_key()
    budget = Budget(prior, args.max_cost_usd)
    counts, lock = Counter(), threading.Lock()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(translate_item, i, key, args, budget, output) for i in todo]
        for future in as_completed(futures):
            event = future.result()
            with lock:
                counts[event["validation_status"]] += 1
                for err in event["validation_errors"]:
                    counts["err:" + err] += 1
                if sum(counts[s] for s in ("accepted_machine_unreviewed", "rejected", "error")) % 25 == 0:
                    print(json.dumps({"progress": dict(counts), "spent_usd": round(budget.spent, 5)}), flush=True)
    print(json.dumps({"final": dict(counts), "spent_usd_cumulative": round(budget.spent, 5), "budget_stopped": budget.stopped}))
    return 0


def command_rescreen(args) -> int:
    """Derive a new file with current screening applied to an earlier journal (original untouched)."""
    out = Path(args.output)
    if out.exists():
        print("refusing: output exists", file=sys.stderr)
        return 2
    csv.field_size_limit(2**31 - 1)
    events = read_journal(Path(args.input))
    ids = {e["record_id"] for e in events}
    arabic = {r["record_id"]: r["text_ar"] for r in iter_master() if r["record_id"] in ids}
    changed = Counter()
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            if event.get("text_en") is not None:
                finish = "stop" if all(f == "stop" for f in event["finish_reasons"]) else "length"
                errors = screen_translation(event["text_en"], arabic[event["record_id"]].strip(), finish)
                status = "accepted_machine_unreviewed" if not errors else "rejected"
                changed[(event["validation_status"], status)] += 1
                event = {**event, "validation_errors": errors, "validation_status": status, "screen_version": SCREEN_VERSION,
                         "rescreened_from": Path(args.input).name, "rescreened_at": args.timestamp}
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({f"{a}->{b}": n for (a, b), n in changed.items()}))
    return 0


def command_summarize(args) -> int:
    """Write diagnostics/translation-run/summary.json: counts, cost, latency, coverage of the 11,953+ flagged rows."""
    out = RUN_DIR / "summary.json"
    files = {
        "glyph": CANDIDATE_DIR / "honorific_glyph_substitution_candidates_2026-11-21.jsonl",
        "pilot": CANDIDATE_DIR / "openrouter_hy_mt2_30b_a3b_pilot_2026-11-21.jsonl",
        "pilot_rescreened": CANDIDATE_DIR / "openrouter_hy_mt2_30b_a3b_pilot_2026-11-21_rescreened_screen_v2.jsonl",
        "batch_no_usable_english": CANDIDATE_DIR / "openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21.jsonl",
        "batch_names_terms": CANDIDATE_DIR / "openrouter_hy_mt2_30b_a3b_batch_names_terms_2026-11-21.jsonl",
    }
    events = {name: read_journal(path) for name, path in files.items()}
    skipped = []
    for name in ("batch_no_usable_english", "batch_names_terms"):
        skipped += read_journal(files[name].with_name(files[name].stem + "_skipped.jsonl"))
    per_file = {}
    for name, rows in events.items():
        latencies = sorted(e["latency_seconds"] for e in rows if "latency_seconds" in e)
        per_file[name] = {
            "rows": len(rows),
            "status": dict(Counter(e["validation_status"] for e in rows)),
            "errors": dict(Counter(err for e in rows for err in e["validation_errors"])),
            "cost_usd": round(sum(float(e.get("model_cost_usd") or 0) for e in rows), 6),
            "tokens": sum((e.get("model_usage") or {}).get("total_tokens", 0) for e in rows),
            "latency_median_s": latencies[len(latencies) // 2] if latencies else None,
            "latency_p95_s": latencies[int(len(latencies) * 0.95)] if latencies else None,
            "latency_max_s": latencies[-1] if latencies else None,
            "split_rows": sum(1 for e in rows if e.get("split", {}).get("chunks", 1) > 1),
        }
    accepted = {}
    for name in ("pilot_rescreened", "batch_no_usable_english", "batch_names_terms"):
        for e in events[name]:
            if e["validation_status"] == "accepted_machine_unreviewed":
                accepted[(e["record_id"], e["arabic_sha256"])] = name
    glyph = {(e["record_id"], e["arabic_sha256"]) for e in events["glyph"]}
    skipped_keys = {(e["record_id"], e["arabic_sha256"]) for e in skipped}
    coverage, uncovered = Counter(), []
    for row in iter_master():
        info = classify_row(row)
        if info["bucket"] == "ok":
            continue
        key = (row["record_id"], gen.text_sha256(row["text_ar"]))
        if key in glyph:
            state = "covered_by_mechanical_glyph_candidate"
        elif key in accepted:
            state = "covered_by_hy_mt2_candidate"
        elif key in skipped_keys:
            state = "skipped_sentence_over_hard_limit"
        elif row["record_id"] in MODEL_RECORD_EXCLUSIONS:
            state = "excluded_paratext"
        else:
            state = "uncovered_" + info["bucket"]
            uncovered.append(row["record_id"])
        coverage[f"{info['bucket']} :: {state}"] += 1
    summary = {
        "generated_at": args.timestamp,
        "model": MODEL,
        "pipeline": PIPELINE,
        "screen_version": SCREEN_VERSION,
        "files": {name: str(path.relative_to(HERE.parent.parent)).replace("\\", "/") for name, path in files.items()},
        "per_file": per_file,
        "total_model_cost_usd": round(sum(per_file[n]["cost_usd"] for n in ("pilot", "batch_no_usable_english", "batch_names_terms")), 6),
        "coverage_of_master_problem_rows": dict(sorted(coverage.items())),
        "uncovered_record_ids": uncovered,
        "skipped_record_ids": [e["record_id"] for e in skipped],
    }
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("total_model_cost_usd", "coverage_of_master_problem_rows")}, indent=1))
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    glyph = sub.add_parser("glyph")
    glyph.add_argument("--output", required=True)
    glyph.add_argument("--timestamp", required=True)
    glyph.add_argument("--overwrite-new-file", action="store_true")
    select = sub.add_parser("select")
    rescreen = sub.add_parser("rescreen")
    rescreen.add_argument("--input", required=True)
    rescreen.add_argument("--output", required=True)
    rescreen.add_argument("--timestamp", required=True)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--timestamp", required=True)
    translate = sub.add_parser("translate")
    translate.add_argument("--output", required=True)
    translate.add_argument("--timestamp", required=True)
    translate.add_argument("--run-label", required=True)
    translate.add_argument("--phase", choices=["no_usable_english", "names_terms"])
    translate.add_argument("--pilot-size", type=int, default=0)
    translate.add_argument("--seed", type=int, default=20261121)
    translate.add_argument("--limit", type=int, default=0)
    translate.add_argument("--concurrency", type=int, default=4)
    translate.add_argument("--max-cost-usd", type=float, default=15.0)
    translate.add_argument("--dry-run", action="store_true")
    translate.add_argument("--skip-from", action="append", help="journal whose finished rows are not repeated")
    args = parser.parse_args()
    return {"glyph": command_glyph, "select": command_select, "translate": command_translate, "rescreen": command_rescreen, "summarize": command_summarize}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
