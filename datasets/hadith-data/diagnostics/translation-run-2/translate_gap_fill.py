#!/usr/bin/env python3
"""Gap-fill translation run 2: tencent/hy-mt2-30b-a3b over reports with no creditable public English.

Reuses generate_hy_mt2_candidates.py (sentence splitting, transport with backoff, QA screen, budget, journal) and adds
a per-request terminology block (translation_model.json prompt_terminology). Candidates only; no database or canonical
write. Subcommands: snapshot, gap, pilot, run, finalize, sample, flags. See README.md in this directory.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import random
import re
import subprocess
import sys
import threading
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent
REPO = DATA.parent.parent
CANDIDATES = DATA / "machine_translation_candidates"

_spec = importlib.util.spec_from_file_location("hy_gen", DATA / "generate_hy_mt2_candidates.py")
hy = importlib.util.module_from_spec(_spec)
sys.modules["hy_gen"] = hy
_spec.loader.exec_module(hy)
gen = hy.gen
hy.PROMPT_TEMPLATE = "{source_text}"  # this runner builds the whole user turn itself and passes it as the "text"

PIN = json.loads((DATA / "translation_model.json").read_text(encoding="utf-8"))
TERMS_BLOCK = PIN.get("prompt_terminology")
BASE_VERSION = PIN["prompt"]["version"]
BASE_TEMPLATE = PIN["prompt"]["template"]
csv.field_size_limit(2**31 - 1)

HARAKAT = re.compile(r"[\u064B-\u065F\u0670\u0640]")
SNAPSHOT_COLUMNS = (
    "h.record_id, h.tradition_id, c.name as work, h.arabic_sha256, h.text_ar, t.state, t.quality_status, "
    "t.model, t.source as tsource, h.chain_status, h.chapter_title"
)
SNAPSHOT_QUERY = (
    f"select {SNAPSHOT_COLUMNS} from public_hadiths h join collections c on c.id=h.collection_id "
    "left join translations t on t.hadith_id=h.id and t.language='en' and t.retired_at is null "
    "where t.id is null or t.quality_status<>'complete' or t.arabic_sha256<>h.arabic_sha256 order by h.record_id"
)


# ------------------------------------------------------------------ terminology


def fold(text: str) -> str:
    """Diacritics, tatweel and alef variants removed so terms match undiacritized or vocalized source."""
    return re.sub(r"[أإآٱ]", "ا", HARAKAT.sub("", text))


def compile_terms(block: dict | None):
    if not block:
        return []
    compiled = []
    for entry in block["terms"]:
        key = fold(entry["ar"])
        pattern = re.compile(r"(?<![ء-يٱ-ە])[وفبلك]?" + re.escape(key).replace(r"\ ", r"\s+") + r"(?![ء-يٱ-ە])")
        compiled.append((entry, pattern, len(key)))
    compiled.sort(key=lambda item: -item[2])
    return compiled


COMPILED_TERMS = compile_terms(TERMS_BLOCK)


def select_terms(text_ar: str, max_terms: int | None = None) -> list[dict]:
    """Longest-match-wins terminology entries that occur in the text, in order of first appearance."""
    if not COMPILED_TERMS:
        return []
    limit = max_terms or TERMS_BLOCK["max_terms_per_request"]
    view = fold(text_ar)
    taken, found = [], {}
    for entry, pattern, _ in COMPILED_TERMS:
        for match in pattern.finditer(view):
            span = (match.start(), match.end())
            if any(span[0] < other[1] and other[0] < span[1] for other in taken):
                continue
            taken.append(span)
            found.setdefault(entry["ar"], (span[0], entry))
    ordered = sorted(found.values(), key=lambda item: item[0])
    return [entry for _, entry in ordered[:limit]]


def build_prompt(chunk: str, variant: str) -> tuple[str, str, list[dict]]:
    """(user turn, prompt_version actually used, terms used). A chunk with no match falls back to the base prompt."""
    terms = select_terms(chunk) if variant == "terminology" else []
    if not terms:
        return BASE_TEMPLATE.format(source_text=chunk), BASE_VERSION, []
    lines = "\n".join(TERMS_BLOCK["line_template"].format(ar=t["ar"], en=t["en"]) for t in terms)
    return TERMS_BLOCK["template"].format(terminology_lines=lines, source_text=chunk), TERMS_BLOCK["version"], terms


# ------------------------------------------------------------------ screen extras


ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
NEGATION_AR = re.compile(r"(?<![ء-ي])(?:لا|لم|لن|ليس|ليست|لما)(?![ء-ي])")
NEGATION_EN = re.compile(r"\b(?:not|no|never|none|nothing|nobody|neither|nor|without|cannot|n't|un\w+|forbid\w*|prohibit\w*|refus\w+)\b", re.I)
HONORIFIC_AR = re.compile(r"صلى الله عليه|عليه السلام|عليهم السلام|عليها السلام|رضي الله عن")
HONORIFIC_EN = re.compile(r"peace|blessings|pleased with|salla|\(s\)|\(a\.?s\.?\)", re.I)
TERMS_ECHO = re.compile(r"translates to|reference the following translations", re.I)


def digit_groups(text: str) -> list[str]:
    return sorted(re.findall(r"\d+", text.translate(ARABIC_DIGITS)))


def extra_guards(text_en: str, text_ar: str) -> list[str]:
    """Guards beyond screen-v2 for the terminology prompt: an echoed reference list; macron/dot transliteration."""
    found = []
    if TERMS_ECHO.search(text_en or "") and not TERMS_ECHO.search(text_ar or ""):
        found.append("terminology_echo")
    if any(unicodedata.category(c) == "Mn" for c in unicodedata.normalize("NFD", text_en or "")):
        found.append("diacritic_transliteration")
    return found


# ------------------------------------------------------------------ data


def read_snapshot(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    return hy.read_journal(path)


def latest_events(paths) -> dict:
    """Last event per (record_id, arabic_sha256) across journals; a later event supersedes an earlier one."""
    out = {}
    for path in paths:
        for event in read_jsonl(Path(path)):
            out[(event["record_id"], event["arabic_sha256"])] = event
    return out


PRIOR_FILES = [
    "openrouter_hy_mt2_30b_a3b_pilot_2026-11-21_rescreened_screen_v2.jsonl",
    "openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21.jsonl",
    "openrouter_hy_mt2_30b_a3b_batch_names_terms_2026-11-21.jsonl",
]
SKIPPED_FILES = [
    "openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21_skipped.jsonl",
    "openrouter_hy_mt2_30b_a3b_batch_names_terms_2026-11-21_skipped.jsonl",
]
GLYPH_FILE = "honorific_glyph_substitution_candidates_2026-11-21.jsonl"


def classify(rows: list[dict]) -> list[dict]:
    """Attach `coverage` to each snapshot row: prior_hy_mt2 | mechanical_glyph | skipped_unsplittable | to_translate."""
    prior = {}
    for name in PRIOR_FILES:
        for event in read_jsonl(CANDIDATES / name):
            if event["validation_status"] == "accepted_machine_unreviewed":
                prior[(event["record_id"], event["arabic_sha256"])] = event
    glyph = {(e["record_id"], e["arabic_sha256"]) for e in read_jsonl(CANDIDATES / GLYPH_FILE)}
    skipped = {(e["record_id"], e["arabic_sha256"]) for name in SKIPPED_FILES for e in read_jsonl(CANDIDATES / name)}
    for row in rows:
        key = (row["record_id"], row["arabic_sha256"])
        row["coverage"] = (
            "prior_hy_mt2" if key in prior else "mechanical_glyph" if key in glyph else "skipped_unsplittable" if key in skipped else "to_translate"
        )
    return rows


def plan(row: dict) -> dict | None:
    text = row["text_ar"].strip()
    if gen.arabic_letter_count(text) < 3:
        return None
    chunks = hy.split_sentences(text)
    return {"row": row, "text_ar": text, "chunks": chunks} if chunks else None


# ------------------------------------------------------------------ translation


def compute_event(item: dict, key: str, args, budget, variant: str) -> dict:
    row, text_ar = item["row"], item["text_ar"]
    started = time.time()
    parts, chunk_events, cost, usage_total = [], [], 0.0, Counter()
    finish_reasons, response_ids, attempts, versions, terms_used, error = [], [], 0, set(), [], None
    for index, (start, end) in enumerate(item["chunks"]):
        chunk = text_ar[start:end].strip()
        prompt, version, terms = build_prompt(chunk, variant)
        prompt_tokens_estimate = int(len(prompt) * hy.ARABIC_TOKENS_PER_CHAR) + 60
        max_tokens = min(hy.MAX_COMPLETION_TOKENS, hy.CONTEXT_TOKENS - prompt_tokens_estimate - 32)
        worst = prompt_tokens_estimate * hy.PRICE_PROMPT + max_tokens * hy.PRICE_COMPLETION
        if max_tokens < 256 or not budget.reserve(worst):
            error = "budget_stop" if max_tokens >= 256 else "context_budget"
            break
        try:
            response = hy.call_model(key, prompt, max_tokens)
        except hy.TransportError as failure:
            budget.settle(worst, worst if failure.cost_unknown else 0.0)
            cost += worst if failure.cost_unknown else 0.0
            error = failure.kind
            break
        usage = response.get("usage") or {}
        actual = usage.get("cost")
        if actual is None:
            actual = usage.get("prompt_tokens", 0) * hy.PRICE_PROMPT + usage.get("completion_tokens", 0) * hy.PRICE_COMPLETION
        budget.settle(worst, float(actual))
        cost += float(actual)
        choice = (response.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content") or "").strip()
        finish_reasons.append(choice.get("finish_reason"))
        response_ids.append(response.get("id"))
        attempts += response.get("_attempts", 1)
        for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage_total[name] += usage.get(name, 0)
        versions.add(version)
        terms_used.extend(t["ar"] for t in terms)
        parts.append(text)
        chunk_events.append(
            {"chunk_index": index, "source_start": start, "source_end": end, "translation": text,
             "finish_reason": choice.get("finish_reason"), "response_model": response.get("model"), "usage": usage}
        )
    event = {
        "record_id": row["record_id"],
        "arabic_sha256": row["arabic_sha256"],
        "run_label": args.run_label,
        "candidate_only": True,
        "translation_source": hy.PIPELINE,
        "translation_model": hy.MODEL,
        "translation_review_status": "machine_unreviewed",
        "prompt_version": sorted(versions)[0] if len(versions) == 1 else "+".join(sorted(versions)) if versions else None,
        "prompt_variant_requested": variant,
        "terminology_terms_sent": terms_used,
        "screen_version": hy.SCREEN_VERSION,
        "created_at": args.timestamp,
        "source_row": {"tradition": row["tradition_id"], "work": row["work"]},
        "source_length_chars": len(text_ar),
        "split": {"chunks": len(item["chunks"]), "boundary": "sentence", "offsets": [list(c) for c in item["chunks"]]},
        "generation": {"temperature": hy.TEMPERATURE, "stream": False, "provider_policy": dict(hy.PROVIDER_POLICY)},
        "model_cost_usd": cost,
        "model_usage": dict(usage_total),
        "model_response_ids": response_ids,
        "finish_reasons": finish_reasons,
        "transport_attempts": attempts,
        "latency_seconds": round(time.time() - started, 2),
    }
    if len(chunk_events) > 1:
        event["chunk_results"] = chunk_events
    elif chunk_events:
        event["response_model"] = chunk_events[0]["response_model"]
    if error or len(parts) != len(item["chunks"]):
        event.update({"validation_status": "error", "validation_errors": [error or "incomplete"], "text_en": None})
    else:
        text_en = hy.joined_english(parts)
        finish = "stop" if all(f == "stop" for f in finish_reasons) else "length"
        errors = hy.screen_translation(text_en, text_ar, finish) + extra_guards(text_en, text_ar)
        event.update(
            {
                "text_en": text_en,
                "translation_sha256": gen.exact_text_sha256(text_en),
                "validation_errors": errors,
                "validation_status": "accepted_machine_unreviewed" if not errors else "rejected",
            }
        )
    return event


GUARD_NAMES = {"terminology_echo", "diacritic_transliteration"}


def translate_row(item: dict, key: str, args, budget, output: Path, variant: str) -> dict:
    """Terminology prompt first; a guard failure falls back once to the base prompt (costs of both are recorded)."""
    event = compute_event(item, key, args, budget, variant)
    if variant == "terminology" and event["validation_status"] == "rejected" and GUARD_NAMES & set(event["validation_errors"]):
        retry = compute_event(item, key, args, budget, "base")
        retry["fallback_from"] = {"prompt_version": event["prompt_version"], "validation_errors": event["validation_errors"],
                                  "model_cost_usd": event["model_cost_usd"], "model_response_ids": event["model_response_ids"]}
        retry["model_cost_usd"] += event["model_cost_usd"]
        event = retry
    hy.append_event(output, event)
    return event


def run_batch(items: list[dict], args, output: Path, variant: str, prior_spend: float) -> dict:
    key = hy.load_key()
    budget = hy.Budget(prior_spend, args.max_cost_usd)
    counts, lock, tick = Counter(), threading.Lock(), time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(translate_row, item, key, args, budget, output, variant) for item in items]
        for future in as_completed(futures):
            event = future.result()
            with lock:
                counts[event["validation_status"]] += 1
                for err in event["validation_errors"]:
                    counts["err:" + err] += 1
                done = sum(counts[s] for s in ("accepted_machine_unreviewed", "rejected", "error"))
                if done % 200 == 0:
                    print(json.dumps({"done": done, "of": len(items), "counts": dict(counts), "spent_usd": round(budget.spent, 4),
                                      "elapsed_s": int(time.time() - tick)}), flush=True)
    return {"counts": dict(counts), "spent_usd_cumulative": round(budget.spent, 5), "budget_stopped": budget.stopped}


def journal_spend(paths) -> float:
    return sum(float(e.get("model_cost_usd") or 0) for p in paths for e in read_jsonl(Path(p)))


def my_journals() -> list[Path]:
    journals = CANDIDATES.glob("openrouter_hy_mt2_30b_a3b_gapfill_terminology_*.jsonl")
    return sorted(HERE.glob("pilot_*.jsonl")) + sorted(p for p in journals if not p.name.endswith("_skipped.jsonl"))


# ------------------------------------------------------------------ subcommands


def command_snapshot(args) -> int:
    """Read-only production snapshot of reports without public English (SELECT only; the URL is never printed)."""
    env = {}
    for line in (REPO / ".env.local").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL_PRODUCTION="):
            env["url"] = line.split("=", 1)[1].strip().strip('"')
    out = Path(args.output)
    query = SNAPSHOT_QUERY
    result = subprocess.run(
        [args.psql, "-X", "-c", f"\\copy ({query}) to '{out.as_posix()}' csv header", env["url"]],
        capture_output=True, text=True, env={**__import__("os").environ, "PGCLIENTENCODING": "UTF8"},
    )
    print(result.stdout.strip(), result.returncode)
    return result.returncode


def command_gap(args) -> int:
    rows = classify(read_snapshot(Path(args.snapshot)))
    table = Counter((r["tradition_id"], r["work"], r["coverage"]) for r in rows)
    state = Counter((r["tradition_id"], r["work"], r["quality_status"] or "no_english_row") for r in rows)
    summary = {
        "gap_total": len(rows),
        "by_coverage": dict(Counter(r["coverage"] for r in rows)),
        "by_tradition_work_coverage": {f"{t} | {w} | {c}": n for (t, w, c), n in sorted(table.items())},
        "by_tradition_work_existing_english": {f"{t} | {w} | {c}": n for (t, w, c), n in sorted(state.items())},
        "to_translate_arabic_chars": sum(len(r["text_ar"]) for r in rows if r["coverage"] == "to_translate"),
        "generated_at": args.timestamp,
    }
    Path(args.output).write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with gzip.open(Path(args.manifest), "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["record_id", "tradition", "work", "arabic_sha256", "existing_english_status", "coverage"])
        for r in rows:
            writer.writerow([r["record_id"], r["tradition_id"], r["work"], r["arabic_sha256"], r["quality_status"] or "no_english_row", r["coverage"]])
    print(json.dumps(summary["by_coverage"]))
    return 0


def pilot_selection(rows: list[dict], size: int, seed: int) -> list[dict]:
    """Stratified by tradition (Sunni split over its four gap works) and length band; two long rows forced in."""
    rng = random.Random(seed)
    pool = [r for r in rows if r["coverage"] == "to_translate"]
    bands = [(0, 150), (150, 600), (600, 2500)]
    cells = []
    for tradition, works in (
        ("tradition:sunni", ["Musnad Ahmad", "Musnad al-Shafi'i", "Muwatta' Malik", "Sunan al-Darimi"]),
        ("tradition:imami", [None]),
        ("tradition:zaydi", [None]),
        ("tradition:ibadi", [None]),
    ):
        for work in works:
            for band in bands:
                cells.append((tradition, work, band))
    picked, seen = [], set()

    def take(candidates, n):
        candidates = [c for c in candidates if c["record_id"] not in seen]
        rng.shuffle(candidates)
        for c in candidates[:n]:
            seen.add(c["record_id"])
            picked.append(c)

    take([r for r in pool if len(r["text_ar"]) > 2500 and len(r["text_ar"]) <= 5500], 2)
    per_cell = max(1, (size - len(picked)) // len(cells))
    for tradition, work, (low, high) in cells:
        take([r for r in pool if r["tradition_id"] == tradition and (work is None or r["work"] == work) and low <= len(r["text_ar"]) < high], per_cell)
    take(pool, size - len(picked))
    rng.shuffle(picked)
    return picked[:size]


def command_pilot(args) -> int:
    rows = classify(read_snapshot(Path(args.snapshot)))
    chosen = pilot_selection(rows, args.size, args.seed)
    items = [plan(r) for r in chosen]
    items = [i for i in items if i]
    print(json.dumps({"pilot_rows": len(items), "by_tradition": dict(Counter(i["row"]["tradition_id"] for i in items))}))
    (HERE / "pilot_rows.json").write_text(json.dumps([i["row"]["record_id"] for i in items], indent=0), encoding="utf-8")
    for variant, name in (("terminology", "pilot_v2_terminology.jsonl"), ("base", "pilot_v1_base.jsonl")):
        output = HERE / name
        done = {(e["record_id"], e["arabic_sha256"]) for e in read_jsonl(output) if e["validation_status"] != "error"}
        todo = [i for i in items if (i["row"]["record_id"], i["row"]["arabic_sha256"]) not in done]
        result = run_batch(todo, args, output, variant, journal_spend(my_journals()))
        print(variant, json.dumps(result))
    return 0


def command_run(args) -> int:
    rows = classify(read_snapshot(Path(args.snapshot)))
    output = Path(args.output).resolve()
    if output.parent != CANDIDATES.resolve():
        print("output must be under machine_translation_candidates/", file=sys.stderr)
        return 2
    items = [plan(r) for r in rows if r["coverage"] == "to_translate"]
    unsplittable = [r for r, i in zip([r for r in rows if r["coverage"] == "to_translate"], items) if i is None]
    items = [i for i in items if i]
    final = {k: e for k, e in latest_events([output]).items() if e["validation_status"] == "accepted_machine_unreviewed"
             or (e["validation_status"] == "rejected" and not args.retry_rejected)}
    if args.redo_term:
        # revision pass: re-translate accepted rows whose source now matches a terminology entry that was not in force
        redo_keys = set()
        for entry, pattern, _ in COMPILED_TERMS:
            if entry["ar"] in args.redo_term:
                redo_keys |= {(i["row"]["record_id"], i["row"]["arabic_sha256"]) for i in items if pattern.search(fold(i["text_ar"]))}
        final = {k: e for k, e in final.items() if k not in redo_keys or e.get("run_label") == args.run_label}
    todo = [i for i in items if (i["row"]["record_id"], i["row"]["arabic_sha256"]) not in final]
    if args.limit:
        todo = todo[: args.limit]
    todo.sort(key=lambda i: i["row"]["record_id"])
    prior = journal_spend(my_journals())
    estimate = sum((len(i["text_ar"]) * 0.6 + 260) * hy.PRICE_PROMPT + (len(i["text_ar"]) * 0.75) * hy.PRICE_COMPLETION for i in todo)
    print(json.dumps({"to_translate": len(items), "already_final": len(items) - len(todo), "to_run": len(todo),
                      "unsplittable_skipped": len(unsplittable), "spent_so_far_usd": round(prior, 4), "estimated_cost_usd": round(estimate, 2)}))
    if unsplittable:
        skip = output.with_name(output.stem + "_skipped.jsonl")
        with skip.open("w", encoding="utf-8", newline="\n") as handle:
            for r in unsplittable:
                handle.write(json.dumps({"record_id": r["record_id"], "arabic_sha256": r["arabic_sha256"], "tradition": r["tradition_id"], "work": r["work"],
                                         "source_length_chars": len(r["text_ar"].strip()), "reason": "no_arabic_letters_in_source" if gen.arabic_letter_count(r["text_ar"]) < 3 else "sentence_over_hard_limit_no_defensible_split",
                                         "created_at": args.timestamp}, ensure_ascii=False) + "\n")
    if args.dry_run:
        return 0
    result = run_batch(todo, args, output, args.variant, prior)
    print(json.dumps({"final": result}))
    return 0


def command_finalize(args) -> int:
    """Combine prior accepted pinned-model rows and this run's accepted rows into one load-ready candidate file."""
    rows = classify(read_snapshot(Path(args.snapshot)))
    wanted = {(r["record_id"], r["arabic_sha256"]): r for r in rows}
    chosen = {}
    for name in PRIOR_FILES:
        for e in read_jsonl(CANDIDATES / name):
            k = (e["record_id"], e["arabic_sha256"])
            if k in wanted and e["validation_status"] == "accepted_machine_unreviewed":
                chosen[k] = (e, name, "prompt v1 (earlier run)")
    for journal in args.journal:
        for k, e in latest_events([journal]).items():
            if k in wanted and e["validation_status"] == "accepted_machine_unreviewed" and k not in chosen:
                chosen[k] = (e, Path(journal).name, "gap-fill run 2")
    out = Path(args.output)
    counts = Counter()
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for k in sorted(chosen):
            e, origin, run = chosen[k]
            row = wanted[k]
            counts[(row["tradition_id"], row["work"])] += 1
            handle.write(json.dumps({
                "record_id": e["record_id"],
                "arabic_sha256": e["arabic_sha256"],
                "text_en": e["text_en"],
                "translation_sha256": e.get("translation_sha256"),
                "translation_source": e["translation_source"],
                "translation_model": e["translation_model"],
                "prompt_version": e.get("prompt_version") or BASE_VERSION,
                "translation_review_status": "machine_unreviewed",
                "candidate_only": True,
                "qa": {"screen_version": e.get("screen_version"), "status": e["validation_status"], "errors": e["validation_errors"]},
                "model_cost_usd": e.get("model_cost_usd"),
                "created_at": e.get("created_at"),
                "run": run,
                "origin_journal": origin,
                "tradition": row["tradition_id"],
                "work": row["work"],
                "existing_english_status": row["quality_status"] or "no_english_row",
            }, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {f"{t} | {w}": n for (t, w), n in sorted(counts.items())}
    print(json.dumps({"rows": sum(counts.values()), "by_work": summary}, ensure_ascii=False, indent=1))
    return 0


def command_sample(args) -> int:
    """Stratified random worksheet from the load-ready file, with the Arabic and blank judgement fields."""
    snapshot = {r["record_id"]: r for r in read_snapshot(Path(args.snapshot))}
    ready = [json.loads(line) for line in Path(args.ready).read_text(encoding="utf-8").splitlines() if line.strip()]
    ready = [r for r in ready if r["run"] == "gap-fill run 2"]
    rng = random.Random(args.seed)
    by_work = defaultdict(list)
    for r in ready:
        by_work[(r["tradition"], r["work"])].append(r)
    total = sum(len(v) for v in by_work.values())
    sample = []
    for key, group in sorted(by_work.items()):
        quota = max(4, round(args.size * len(group) / total)) if len(group) >= 4 else len(group)
        quota = min(quota, len(group))
        long_rows = [r for r in group if len(snapshot[r["record_id"]]["text_ar"]) > 600]
        short_rows = [r for r in group if len(snapshot[r["record_id"]]["text_ar"]) <= 600]
        want_long = min(len(long_rows), max(1, quota // 3))
        picks = rng.sample(long_rows, want_long) + rng.sample(short_rows, min(len(short_rows), quota - want_long))
        sample.extend(picks)
    rng.shuffle(sample)
    while len(sample) > args.size:
        sample.pop()
    have = {r["record_id"] for r in sample}
    extra = [r for r in ready if r["record_id"] not in have]
    rng.shuffle(extra)
    sample.extend(extra[: max(0, args.size - len(sample))])
    with Path(args.output).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["n", "record_id", "tradition", "work", "arabic_chars", "arabic", "english", "meaning_correct (y/n/partial)",
                         "error_type (mistranslation/omission/addition/name/formula/other)", "severity (minor/major)", "reviewer_notes", "reviewer", "reviewed_on"])
        for n, r in enumerate(sample, 1):
            row = snapshot[r["record_id"]]
            writer.writerow([n, r["record_id"], r["tradition"], r["work"], len(row["text_ar"]), row["text_ar"].strip(), r["text_en"], "", "", "", "", "", ""])
    print(json.dumps({"worksheet_rows": len(sample), "by_tradition": dict(Counter(r["tradition"] for r in sample))}))
    return 0


FLAG_WEIGHTS = {
    "screen_error": 5, "length_ratio_outlier": 3, "numbers_differ": 3, "honorific_mismatch": 2.5, "very_short_source": 2,
    "negation_possibly_dropped": 2, "low_length_ratio": 2, "rare_name_spellings": 2, "very_long_source": 1.5, "short_chainless": 1,
}
REVIEW_FIRST_THRESHOLD = 3
TOP_TIER_THRESHOLD = 4.5
CHAIN_MARKER = re.compile(r"(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|اخبرنا|اخبرني|حدثنى|سمعت)|(?:^|\s)عن\s")
SIGLA = re.compile(r"ﷺ|\(\s*[صع]\s*\)|\"\s*[صع]\s*[م]?\s*\"|\(ع م\)|عليه الصلاة والسلام|صلعم")
NEGATION_IDIOM = re.compile(r"لا بأس|لا باس|إلا|الا ")


def command_flags(args) -> int:
    """Rank outputs most likely to be wrong into a 'review first' file with the reasons (weights: FLAG_WEIGHTS)."""
    snapshot = {r["record_id"]: r for r in read_snapshot(Path(args.snapshot))}
    ready = [json.loads(line) for line in Path(args.ready).read_text(encoding="utf-8").splitlines() if line.strip()]
    ready = [r for r in ready if r["run"] == "gap-fill run 2" or args.include_prior]
    terms_en = set()
    for entry in (TERMS_BLOCK or {}).get("terms", []):
        terms_en.update(re.findall(r"[A-Za-zʿʾ-]+", entry["en"]))
    name_re = re.compile(r"(?<![.!?\"“]\s)(?<!^)\b[A-Z][a-zʿʾ’']{3,}(?:-[A-Za-z]+)?\b")
    name_counts, tokens_by_row = Counter(), {}
    for r in ready:
        names = set(name_re.findall(r["text_en"]))
        tokens_by_row[r["record_id"]] = names
        name_counts.update(names)
    ratios = []
    for r in ready:
        letters = gen.arabic_letter_count(snapshot[r["record_id"]]["text_ar"])
        ratios.append(gen.latin_letter_count(r["text_en"]) / letters if letters >= 40 else None)
    valid = sorted(x for x in ratios if x)
    low, high = valid[int(len(valid) * 0.01)], valid[int(len(valid) * 0.99)]
    flagged, reasons_count = [], Counter()
    for r, ratio in zip(ready, ratios):
        row = snapshot[r["record_id"]]
        ar, en = row["text_ar"], r["text_en"]
        folded = fold(ar)
        letters = gen.arabic_letter_count(ar)
        reasons = []
        if letters < 40:
            reasons.append("very_short_source")
        if letters > 2500:
            reasons.append("very_long_source")
        if letters < 100 and not CHAIN_MARKER.search(folded):
            reasons.append("short_chainless")
        if ratio is not None and (ratio < max(low, 1.2) or ratio > min(high, 3.0)):
            reasons.append("length_ratio_outlier")
        elif ratio is not None and ratio < 1.4:
            reasons.append("low_length_ratio")
        if digit_groups(ar) != digit_groups(en):
            reasons.append("numbers_differ")
        negation = NEGATION_AR.search(folded) and not NEGATION_IDIOM.search(folded)
        if negation and not NEGATION_EN.search(en):
            reasons.append("negation_possibly_dropped")
        has_sigla = bool(SIGLA.search(ar))
        if HONORIFIC_AR.search(folded) and not HONORIFIC_EN.search(en):
            reasons.append("honorific_mismatch")
        elif HONORIFIC_EN.search(en) and not HONORIFIC_AR.search(folded) and not has_sigla:
            reasons.append("honorific_mismatch")
        rare = sorted(n for n in tokens_by_row[r["record_id"]] if name_counts[n] <= 2 and n not in terms_en)
        if rare:
            reasons.append("rare_name_spellings")
        if r["qa"]["errors"]:
            reasons.append("screen_error")
        score = sum(FLAG_WEIGHTS[x] for x in reasons)
        if score >= REVIEW_FIRST_THRESHOLD:
            flagged.append((score, r, reasons, rare))
            reasons_count.update(reasons)
    flagged.sort(key=lambda item: (-item[0], item[1]["record_id"]))
    with Path(args.output).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["priority", "tier", "score", "record_id", "tradition", "work", "reasons", "arabic_chars", "arabic", "english", "rare_names"])
        for n, (score, r, reasons, rare) in enumerate(flagged, 1):
            row = snapshot[r["record_id"]]
            writer.writerow([n, "A" if score >= TOP_TIER_THRESHOLD else "B", score, r["record_id"], r["tradition"], r["work"], ";".join(reasons), len(row["text_ar"]),
                             row["text_ar"].strip()[:1500], r["text_en"][:2500], ";".join(rare)])
    print(json.dumps({"scored": len(ready), "review_first_rows": len(flagged), "tier_A_rows": sum(1 for f in flagged if f[0] >= TOP_TIER_THRESHOLD),
                      "threshold": REVIEW_FIRST_THRESHOLD,
                      "by_reason_within_review_first": dict(reasons_count), "ratio_bounds": [round(low, 2), round(high, 2)]}, indent=1))
    return 0


PUBLIC_TOTALS_QUERY = (
    "select h.tradition_id, c.name, count(*) from public_hadiths h join collections c on c.id=h.collection_id group by 1,2 order by 1,2"
)


def command_summary(args) -> int:
    """Before/after table by tradition and work, plus batch statistics, from the snapshot and the journals."""
    rows = classify(read_snapshot(Path(args.snapshot)))
    journals = [Path(j) for j in args.journal]
    latest = latest_events(journals)
    every = [e for j in journals for e in read_jsonl(j)]
    own_skipped = {(e["record_id"], e["arabic_sha256"]): e["reason"] for j in journals if j.with_name(j.stem + "_skipped.jsonl").exists()
                   for e in read_jsonl(j.with_name(j.stem + "_skipped.jsonl"))}
    totals = {}
    for line in Path(args.public_totals).read_text(encoding="utf-8").splitlines():
        tradition, work, count = line.split("|")
        totals[(tradition, work)] = int(count)
    table = defaultdict(Counter)
    for r in rows:
        e = latest.get((r["record_id"], r["arabic_sha256"]))
        key = (r["tradition_id"], r["work"])
        if r["coverage"] == "prior_hy_mt2":
            state = "covered_prior_hy_mt2"
        elif r["coverage"] == "mechanical_glyph":
            state = "covered_mechanical_glyph"
        elif r["coverage"] == "skipped_unsplittable":
            state = "skipped_sentence_over_limit"
        elif e and e["validation_status"] == "accepted_machine_unreviewed":
            state = "covered_new_hy_mt2"
        elif e and e["validation_status"] == "rejected":
            state = "failed_screen:" + e["validation_errors"][0]
        elif (r["record_id"], r["arabic_sha256"]) in own_skipped:
            state = "skipped_" + own_skipped[(r["record_id"], r["arabic_sha256"])]
        else:
            state = "pending_translation"
        table[key][state] += 1
    out_rows = []
    for key, total in sorted(totals.items()):
        gap = sum(table[key].values())
        covered = sum(n for s, n in table[key].items() if s.startswith("covered"))
        out_rows.append({"tradition": key[0], "work": key[1], "public_reports": total, "public_english_before": total - gap, "gap_before": gap,
                         "gap_states": dict(table[key]), "creditable_english_after": total - gap + covered, "still_without_english": gap - covered})
    attempted = [e for e in every if e.get("run_label", "").startswith("gapfill-run-2")]
    statuses = Counter(e["validation_status"] for e in latest.values())
    errors = Counter(err for e in latest.values() for err in e["validation_errors"])
    all_events = Counter(e["validation_status"] for e in attempted)
    summary = {
        "generated_at": args.timestamp,
        "per_work": out_rows,
        "totals": {
            "public_reports": sum(totals.values()),
            "public_english_before": sum(r["public_english_before"] for r in out_rows),
            "gap_before": sum(r["gap_before"] for r in out_rows),
            "creditable_english_after": sum(r["creditable_english_after"] for r in out_rows),
            "still_without_english": sum(r["still_without_english"] for r in out_rows),
        },
        "batch": {
            "journal_events_total": len(every),
            "events_by_status": dict(all_events),
            "final_status_per_report": dict(statuses),
            "final_errors_by_reason": dict(errors),
            "fallback_to_base_prompt": sum(1 for e in latest.values() if e.get("fallback_from")),
            "prompt_versions_in_accepted": dict(Counter(e.get("prompt_version") for e in latest.values() if e["validation_status"] == "accepted_machine_unreviewed")),
            "split_rows": sum(1 for e in latest.values() if e["split"]["chunks"] > 1),
            "cost_usd_all_events": round(sum(float(e.get("model_cost_usd") or 0) for e in every), 6),
            "tokens": {k: sum(e["model_usage"].get(k, 0) for e in every) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
        },
    }
    Path(args.output).write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"totals": summary["totals"], "batch": summary["batch"]}, indent=1, ensure_ascii=False))
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--output", required=True)
    s.add_argument("--psql", default="C:/Program Files/PostgreSQL/16/bin/psql.exe")
    g = sub.add_parser("gap")
    g.add_argument("--snapshot", required=True)
    g.add_argument("--output", required=True)
    g.add_argument("--manifest", required=True)
    g.add_argument("--timestamp", required=True)
    for name in ("pilot", "run"):
        p = sub.add_parser(name)
        p.add_argument("--snapshot", required=True)
        p.add_argument("--timestamp", required=True)
        p.add_argument("--run-label", required=True)
        p.add_argument("--concurrency", type=int, default=8)
        p.add_argument("--max-cost-usd", type=float, default=20.0)
        if name == "pilot":
            p.add_argument("--size", type=int, default=60)
            p.add_argument("--seed", type=int, default=20261121)
        else:
            p.add_argument("--output", required=True)
            p.add_argument("--variant", choices=["terminology", "base"], default="terminology")
            p.add_argument("--limit", type=int, default=0)
            p.add_argument("--retry-rejected", action="store_true")
            p.add_argument("--redo-term", action="append", help="re-translate rows matching this terminology entry (its Arabic); repeatable")
            p.add_argument("--dry-run", action="store_true")
    f = sub.add_parser("finalize")
    f.add_argument("--snapshot", required=True)
    f.add_argument("--journal", action="append", required=True)
    f.add_argument("--output", required=True)
    sm = sub.add_parser("summary")
    sm.add_argument("--snapshot", required=True)
    sm.add_argument("--journal", action="append", required=True)
    sm.add_argument("--public-totals", required=True, help="text file of 'tradition|work|count' lines (PUBLIC_TOTALS_QUERY)")
    sm.add_argument("--output", required=True)
    sm.add_argument("--timestamp", required=True)
    for name in ("sample", "flags"):
        p = sub.add_parser(name)
        p.add_argument("--snapshot", required=True)
        p.add_argument("--ready", required=True)
        p.add_argument("--output", required=True)
        if name == "flags":
            p.add_argument("--include-prior", action="store_true", help="also score the earlier run's rows")
        if name == "sample":
            p.add_argument("--size", type=int, default=200)
            p.add_argument("--seed", type=int, default=20261121)
    args = parser.parse_args()
    return {"snapshot": command_snapshot, "gap": command_gap, "pilot": command_pilot, "run": command_run,
            "finalize": command_finalize, "summary": command_summary, "sample": command_sample, "flags": command_flags}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
