#!/usr/bin/env python3
"""Validate model_registry.json and render docs/models.md from it (--check fails on drift)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
REGISTRY_PATH = HERE / "model_registry.json"
SCHEMA_PATH = HERE / "model_registry.schema.json"
PIN_PATH = HERE / "translation_model.json"
DOC_PATH = REPO_ROOT / "docs" / "models.md"

JSON_TYPES = {"string": str, "integer": int, "boolean": bool, "array": list, "object": dict, "null": type(None)}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def schema_ref_parts(ref: str):
    return [part for part in ref.removeprefix("#/").split("/") if part]


def validate(value, schema, root, where="$"):
    """Validate the JSON Schema subset the registry schema uses: $ref, type, enum, required, properties, additionalProperties, items, minItems."""
    errors = []
    if "$ref" in schema:
        target = root
        for part in schema_ref_parts(schema["$ref"]):
            target = target[part]
        return validate(value, target, root, where)
    wanted = schema.get("type")
    if wanted is not None:
        names = wanted if isinstance(wanted, list) else [wanted]
        matches = any(
            isinstance(value, JSON_TYPES[name]) and not (name == "integer" and isinstance(value, bool))
            for name in names
        )
        if not matches:
            return [f"{where}: expected {names}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing required {key!r}")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                errors += validate(child, properties[key], root, f"{where}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{where}: unexpected property {key!r}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: needs at least {schema['minItems']} items")
        if "items" in schema:
            for index, child in enumerate(value):
                errors += validate(child, schema["items"], root, f"{where}[{index}]")
    return errors


def integrity_errors(registry: dict, pin: dict) -> list[str]:
    """Cross-checks the schema cannot express."""
    errors = []
    entries = registry["entries"]
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        errors.append("duplicate entry ids")
    pinned = [entry for entry in entries if entry["pinned"]]
    if len(pinned) != 1:
        errors.append(f"exactly one entry must be pinned, found {len(pinned)}")
    for entry in pinned:
        if entry["model_id"] != pin["model_id"]:
            errors.append(f"pinned entry {entry['id']} model_id {entry['model_id']!r} differs from translation_model.json {pin['model_id']!r}")
        if entry["output_status"] != "candidate_only" or not entry["prohibited_uses"]:
            errors.append(f"pinned entry {entry['id']} must be candidate_only with prohibited_uses")
    if registry["pinned_translator"]["model_id"] != pin["model_id"]:
        errors.append("registry pinned_translator differs from translation_model.json")
    for entry in entries:
        if (entry["model_id"] is None) != (entry["model_id_status"] == "not_recorded"):
            errors.append(f"{entry['id']}: model_id null must coincide with status not_recorded")
        if entry["model_id_status"] != "namespaced_specific" and not entry["model_id_note"].strip():
            errors.append(f"{entry['id']}: an insufficiently recorded identity needs a note")
    return errors


def rows_text(entry: dict) -> str:
    counted = [(output["rows"], output["unit"]) for output in entry["outputs"] if output["rows"] is not None]
    if not counted:
        return "not counted"
    rows, unit = counted[0]
    first = unit.split(" (")[0]
    return f"{rows:,} {first}" + (f" (+{len(counted) - 1} more outputs)" if len(counted) > 1 else "")


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(registry: dict, pin: dict) -> str:
    lines = [
        "<!-- Generated from datasets/hadith-data/model_registry.json by datasets/hadith-data/render_model_docs.py. Do not edit. -->",
        "",
        "# Models used in this project",
        "",
        registry["purpose"],
        "",
        f"As of {registry['as_of']}. Source of truth: `datasets/hadith-data/model_registry.json` (schema `model_registry.schema.json`).",
        "",
        "## Pinned translator",
        "",
        f"Arabic to English machine translation uses `{pin['model_id']}` on {pin['provider']}, pinned by the {pin['decision']['decided_by']} on {pin['decision']['pinned_on']}.",
        f"Configuration: `{registry['pinned_translator']['config']}` (prompt `{pin['prompt']['version']}`, temperature {pin['generation']['temperature']}, "
        f"context {pin['generation']['context_tokens']:,} tokens, completion limit {pin['generation']['max_completion_tokens']:,}, QA screen `{pin['qa_screen']['version']}`).",
        f"{pin['decision']['change_rule']}",
        "",
    ]
    for entry in registry["entries"]:
        if entry["pinned"]:
            lines += ["What its output may and may not be used for:", ""]
            lines += [f"- May: {use}" for use in entry["allowed_uses"]]
            lines += [f"- May not: {use}" for use in entry["prohibited_uses"]]
            lines += [f"- Review state: {entry['review_state']}", ""]
    lines += [
        "## Summary",
        "",
        "| Model as recorded | Kind | Work | Output | Status | Identity |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in registry["entries"]:
        model = f"`{entry['model_id']}`" if entry["model_id"] else "(none recorded)"
        if entry["pinned"]:
            model += " **pinned**"
        work = entry["work"].split(". ")[0].rstrip(".")
        lines.append(
            f"| {cell(model)} | {entry['kind']} | {cell(work)} | {cell(rows_text(entry))} | {entry['output_status']} | {entry['model_id_status']} |"
        )
    lines += ["", registry["master_note"], ""]
    lines += ["## Entries", ""]
    for entry in registry["entries"]:
        title = entry["model_id"] or "model not recorded"
        lines += [f"### {title}: {entry['kind'].replace('_', ' ')} (`{entry['id']}`)", ""]
        lines += [
            f"- Runtime: {entry['runtime']}",
            f"- Work: {entry['work']}",
            f"- Dates: {entry['date_range']['start']} to {entry['date_range']['end']} ({entry['date_range']['basis']})",
            f"- Identity: {entry['model_id_status']}. {entry['model_id_note']}",
        ]
        lines += [f"- Identity flag: {flag}" for flag in entry.get("identity_flags", [])]
        lines += [f"- Status: {entry['output_status']}. {entry['review_state']}"]
        lines += ["- Inputs:"] + [f"  - `{path}`" for path in entry["inputs"]]
        lines += ["- Outputs:"]
        for output in entry["outputs"]:
            count = "" if output["rows"] is None else f"{output['rows']:,} {output['unit']}"
            detail = "; ".join(part for part in (count, output["note"]) if part)
            lines.append(f"  - `{output['path']}`" + (f": {detail}" if detail else ""))
        if entry["allowed_uses"]:
            lines += ["- May be used for:"] + [f"  - {use}" for use in entry["allowed_uses"]]
        if entry["prohibited_uses"]:
            lines += ["- May not be used for:"] + [f"  - {use}" for use in entry["prohibited_uses"]]
        if entry["quality_findings"]:
            lines += ["- Quality findings:"]
            lines += [f"  - {finding['finding']} (source: {finding['source']})" for finding in entry["quality_findings"]]
        lines += ["- Evidence:"] + [f"  - `{item['path']}`: {item['locator']}" for item in entry["evidence"]]
        if entry.get("notes"):
            lines += [f"- Notes: {entry['notes']}"]
        lines.append("")
    lines += ["## Coverage notes", ""] + [f"- {note}" for note in registry["coverage_notes"]] + [""]
    return "\n".join(lines)


def build() -> str:
    registry, schema, pin = load_json(REGISTRY_PATH), load_json(SCHEMA_PATH), load_json(PIN_PATH)
    errors = validate(registry, schema, schema) + integrity_errors(registry, pin)
    if errors:
        raise ValueError("model_registry.json is invalid:\n" + "\n".join(errors))
    return render(registry, pin)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if docs/models.md differs from the registry")
    args = parser.parse_args()
    text = build()
    if args.check:
        current = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
        if current.replace("\r\n", "\n") != text:
            print("docs/models.md is out of date; run render_model_docs.py", file=sys.stderr)
            return 1
        return 0
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
