#!/usr/bin/env python3
"""Resumable OpenRouter scoring of extracted hadith records against their source window.

    python score_with_model.py --limit 20                       # first 20 pending records
    python score_with_model.py --model qwen/qwen3.7-flash --batch-size 4 --max-cost-usd 2
    python score_with_model.py --dry-run                        # token and cost estimate only, no network

Reads output/records_with_windows.jsonl.gz (made by deterministic_checks.py) and prompt.md. Appends one strict-JSON
verdict per record to output/model_verdicts.jsonl (re-running skips records already stored with status ok) and writes
output/run_manifest.json. The API key is read at run time from the pi models.json file and is never printed or logged.
Stops cleanly on HTTP 402 (out of credit). Sends no referer, title or project identifier.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(HERE, "prompt.md")
DEFAULT_INPUT = os.path.join(HERE, "output", "records_with_windows.jsonl.gz")
DEFAULT_OUT = os.path.join(HERE, "output", "model_verdicts.jsonl")
DEFAULT_MANIFEST = os.path.join(HERE, "output", "run_manifest.json")
KEY_FILE = "C:/Users/atooz/.pi/agent/models.json"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.7-flash"
FLAGS = {"footnote_leak", "markup_leak", "fragment_only_chain", "merged_records", "commentary_tail",
         "sanad_matn_split_wrong", "truncated", "not_a_report"}
SCORE_KEYS = ("boundaries", "cleanliness", "sanad_matn_split")
PROPOSAL_STRING_KEYS = ("text_ar", "sanad_ar", "matn_ar")
PROPOSAL_LIST_KEYS = ("footnotes", "commentary")
CHARS_PER_TOKEN = 2.2  # Arabic on a Qwen-family tokenizer; a deliberately pessimistic planning figure
OUTPUT_TOKENS_PER_RECORD = 420


class PaymentRequired(Exception):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def collapse(text: str) -> str:
    return " ".join((text or "").split())


# --------------------------------------------------------------------------- key and transport
def load_api_key(path: str = KEY_FILE) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)["providers"]["openrouter-free"]["apiKey"]


def http_transport(url: str, headers: dict, body: dict, timeout: float = 120.0):
    """Default transport: returns (status, parsed JSON or text). Never raises on HTTP status codes."""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            return response.status, _maybe_json(raw)
    except urllib.error.HTTPError as error:
        return error.code, _maybe_json(error.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError) as error:  # network failure: report without the URL's query or headers
        return 0, {"error": {"message": type(error).__name__}}


def _maybe_json(raw: str):
    try:
        return json.loads(raw)
    except ValueError:
        return raw[:500]


# --------------------------------------------------------------------------- request / response
def build_user_message(records: list) -> str:
    payload = {"records": [{"id": r["id"], "extracted_text": r["text_ar"], "extracted_sanad": r.get("sanad"),
                            "extracted_matn": r.get("matn_ar"), "source_window": r["window_ar"]} for r in records]}
    return json.dumps(payload, ensure_ascii=False)


def build_body(model: str, system_prompt: str, records: list, max_tokens: int, reasoning: str) -> dict:
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": build_user_message(records)}],
            "response_format": {"type": "json_object"},
            "provider": {"data_collection": "deny"}}
    if reasoning == "off":
        body["reasoning"] = {"enabled": False}
    return body


def extract_json(content: str):
    """Parse the model's answer as one JSON object; tolerate a code fence or a leading think block."""
    text = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except ValueError:
                return None
    return None


def validate_verdict(verdict, window: str):
    """Return (clean verdict or None, problems). Proposals that are not substrings of the window are dropped, not trusted."""
    problems = []
    if not isinstance(verdict, dict):
        return None, ["verdict_not_an_object"]
    scores = verdict.get("scores")
    if not isinstance(scores, dict) or any(not isinstance(scores.get(k), int) or isinstance(scores.get(k), bool) or not 0 <= scores.get(k) <= 3 for k in SCORE_KEYS):
        return None, ["scores_invalid"]
    flags = verdict.get("flags")
    if not isinstance(flags, list) or any(not isinstance(f, str) for f in flags):
        return None, ["flags_invalid"]
    unknown = [f for f in flags if f not in FLAGS]
    if unknown:
        problems.append("unknown_flags:" + ",".join(unknown))
    reason = verdict.get("reason")
    if not isinstance(reason, str):
        return None, ["reason_invalid"]
    haystack = collapse(window)
    proposals_in = verdict.get("proposals") or {}
    if not isinstance(proposals_in, dict):
        proposals_in = {}
        problems.append("proposals_not_an_object")
    kept, rejected = {}, []
    for key in PROPOSAL_STRING_KEYS:
        value = proposals_in.get(key)
        if value in (None, ""):
            kept[key] = None
        elif isinstance(value, str) and collapse(value) in haystack:
            kept[key] = value
        else:
            kept[key] = None
            rejected.append(key)
    for key in PROPOSAL_LIST_KEYS:
        out = []
        values = proposals_in.get(key) or []
        for i, value in enumerate(values if isinstance(values, list) else []):
            if isinstance(value, str) and value.strip() and collapse(value) in haystack:
                out.append(value)
            else:
                rejected.append(f"{key}[{i}]")
        kept[key] = out
    clean = {"scores": {k: scores[k] for k in SCORE_KEYS}, "flags": [f for f in flags if f in FLAGS],
             "reason": reason[:400], "proposals": kept, "rejected_proposals": rejected}
    return clean, problems


def parse_response(content: str, records: list):
    """Map a model answer onto the batch: {id: (clean verdict | None, problems)}; ids missing from the answer get 'missing'."""
    result = {r["id"]: (None, ["missing_from_answer"]) for r in records}
    data = extract_json(content)
    if not isinstance(data, dict) or not isinstance(data.get("verdicts"), list):
        return {r["id"]: (None, ["answer_not_json_with_verdicts"]) for r in records}
    windows = {r["id"]: r["window_ar"] for r in records}
    for verdict in data["verdicts"]:
        rid = verdict.get("id") if isinstance(verdict, dict) else None
        if rid in windows:
            result[rid] = validate_verdict(verdict, windows[rid])
    return result


def usage_cost(usage: dict, price_in: float, price_out: float) -> float:
    if isinstance(usage, dict) and isinstance(usage.get("cost"), (int, float)):
        return float(usage["cost"])
    prompt = (usage or {}).get("prompt_tokens", 0) or 0
    completion = (usage or {}).get("completion_tokens", 0) or 0
    return (prompt * price_in + completion * price_out) / 1_000_000


# --------------------------------------------------------------------------- run
def load_records(path: str) -> list:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def load_done(path: str) -> set:
    done = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("status") == "ok":
                    done.add(row["id"])
    return done


def estimate_tokens(records: list, system_prompt: str) -> int:
    chars = sum(len(r["text_ar"] or "") + len(r.get("matn_ar") or "") + len(r["window_ar"]) + 120 for r in records)
    return int(chars / CHARS_PER_TOKEN) + int(len(system_prompt) / 3.5)


def run(args, transport=http_transport, key_loader=load_api_key, sleep=time.sleep) -> dict:
    system_prompt = open(PROMPT_PATH, "r", encoding="utf-8").read()
    prompt_sha = sha256_file(PROMPT_PATH)
    records = load_records(args.input)
    if args.work:
        records = [r for r in records if r["work"] == args.work]
    done = load_done(args.output)
    pending = [r for r in records if r["id"] not in done]
    if args.limit:
        pending = pending[:args.limit]
    run_id = hashlib.sha256((utc_now() + args.model).encode()).hexdigest()[:12]
    manifest = {"run_id": run_id, "model": args.model, "prompt_file": "prompt.md", "prompt_sha256": prompt_sha, "temperature": 0,
                "batch_size": args.batch_size, "max_cost_usd": args.max_cost_usd, "price_per_million_tokens_usd": {"input": args.price_in, "output": args.price_out},
                "started_utc": utc_now(), "finished_utc": None, "status": "running", "records_selected": len(pending),
                "records_ok": 0, "records_failed": 0, "requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "stopped_because": None}
    write_manifest(args.manifest, manifest)
    est_in = estimate_tokens(pending, system_prompt)
    est_out = len(pending) * OUTPUT_TOKENS_PER_RECORD
    manifest["estimate"] = {"input_tokens": est_in, "output_tokens": est_out,
                            "cost_usd": round((est_in * args.price_in + est_out * args.price_out) / 1_000_000, 4)}
    if args.dry_run:
        manifest.update(status="dry_run", finished_utc=utc_now())
        write_manifest(args.manifest, manifest)
        return manifest
    key = key_loader()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    try:
        with open(args.output, "a", encoding="utf-8", newline="\n") as sink:
            for i in range(0, len(pending), args.batch_size):
                batch = pending[i:i + args.batch_size]
                projected = (estimate_tokens(batch, system_prompt) * args.price_in + len(batch) * OUTPUT_TOKENS_PER_RECORD * args.price_out) / 1_000_000
                if manifest["cost_usd"] + projected > args.max_cost_usd:
                    manifest["stopped_because"] = "cost_cap"
                    break
                started = utc_now()
                body = build_body(args.model, system_prompt, batch, max_tokens=len(batch) * 700 + 200, reasoning=args.reasoning)
                status, payload = call_with_retries(transport, headers, body, sleep)
                manifest["requests"] += 1
                if status == 402:
                    raise PaymentRequired()
                finished = utc_now()
                if status != 200 or not isinstance(payload, dict):
                    message = scrub(json.dumps(payload, ensure_ascii=False)[:200] if not isinstance(payload, str) else payload[:200], key)
                    for rec in batch:
                        sink.write(json.dumps(row_for(rec, args, run_id, manifest, prompt_sha, started, finished, None, ["http_" + str(status), message], 0.0), ensure_ascii=False) + "\n")
                    manifest["records_failed"] += len(batch)
                    if status in (401, 403):
                        manifest["stopped_because"] = f"http_{status}"
                        break
                    continue
                usage = payload.get("usage") or {}
                cost = usage_cost(usage, args.price_in, args.price_out)
                manifest["cost_usd"] = round(manifest["cost_usd"] + cost, 6)
                manifest["prompt_tokens"] += usage.get("prompt_tokens", 0) or 0
                manifest["completion_tokens"] += usage.get("completion_tokens", 0) or 0
                content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                parsed = parse_response(content, batch)
                for rec in batch:
                    verdict, problems = parsed[rec["id"]]
                    sink.write(json.dumps(row_for(rec, args, run_id, manifest, prompt_sha, started, finished, verdict, problems, cost / len(batch)), ensure_ascii=False) + "\n")
                    manifest["records_ok" if verdict else "records_failed"] += 1
                sink.flush()
                write_manifest(args.manifest, manifest)
        manifest["status"] = "completed" if not manifest["stopped_because"] else "stopped"
    except PaymentRequired:
        manifest["status"] = "stopped"
        manifest["stopped_because"] = "http_402_payment_required"
    manifest["finished_utc"] = utc_now()
    write_manifest(args.manifest, manifest)
    return manifest


def call_with_retries(transport, headers, body, sleep, attempts=3):
    for attempt in range(attempts):
        status, payload = transport(ENDPOINT, headers, body)
        if status in (429, 500, 502, 503, 504, 0) and attempt < attempts - 1:
            sleep(2 ** (attempt + 1))
            continue
        return status, payload
    return status, payload


def row_for(rec, args, run_id, manifest, prompt_sha, started, finished, verdict, problems, cost):
    return {"id": rec["id"], "work": rec["work"], "status": "ok" if verdict else "failed", "verdict": verdict, "problems": problems,
            "model": args.model, "prompt_sha256": prompt_sha, "run_id": run_id, "run_started_utc": manifest["started_utc"],
            "request_started_utc": started, "request_finished_utc": finished, "cost_usd_share": round(cost, 8)}


def scrub(text: str, key: str) -> str:
    return text.replace(key, "<redacted>") if key else text


def write_manifest(path: str, manifest: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--output", default=DEFAULT_OUT)
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-cost-usd", type=float, default=2.0)
    ap.add_argument("--price-in", type=float, default=0.03, help="USD per million input tokens")
    ap.add_argument("--price-out", type=float, default=0.13, help="USD per million output tokens")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--work", choices=["rabi", "zayd", "rida"])
    ap.add_argument("--reasoning", choices=["off", "default"], default="off", help="'off' sends reasoning.enabled=false")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    manifest = run(parse_args(argv))
    summary = {k: manifest[k] for k in ("run_id", "status", "stopped_because", "records_selected", "records_ok", "records_failed", "requests", "cost_usd", "estimate") if k in manifest}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if manifest.get("stopped_because") == "http_402_payment_required" else 0


if __name__ == "__main__":
    sys.exit(main())
