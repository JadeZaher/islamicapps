"""Per-reference provenance: every emitted reference field is traced to the source it was read from, or withdrawn.

One record per (report, field group). Shape (all keys always present):
  record_id, hadith_id, work_id, field, value, claim_by ('project_source_file' | 'external_dataset'),
  kind ('source_value' | 'derived'), derivation (rule and inputs, or null),
  source_code, source_name, licence (from src/lib/sources/registry.ts), source_file, source_sha256, source_version,
  source_record_id, source_field, edition (as the source names it, or null), review_state.
validate_record() is the gate: a record that fails it removes the field from the emitted row (a reference that cannot be
sourced is not emitted). See README.md, "Citation standard".
"""

import re
from pathlib import Path

REQUIRED = ("record_id", "field", "claim_by", "kind", "source_code", "source_name", "licence", "source_file", "source_sha256",
            "source_record_id", "source_field")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def load_registry(path):
    """{code: {name, licence}} read from src/lib/sources/registry.ts (the one list of source codes)."""
    text = Path(path).read_text(encoding="utf-8")
    registry = {}
    pattern = re.compile(r"code: '([A-Z0-9]+)',.*?name: (['\"])(.*?)\2,.*?licence: \{ name: (['\"])(.*?)\4", re.S)
    for match in pattern.finditer(text):
        registry[match.group(1)] = {"name": match.group(3), "licence": match.group(5)}
    return registry


def validate_record(record, registry, known_hashes):
    """List of problems; empty means the reference may be emitted."""
    problems = [f"missing:{key}" for key in REQUIRED if record.get(key) in (None, "")]
    if record.get("value") in (None, ""):
        problems.append("missing:value")
    code = record.get("source_code")
    if code and code not in registry:
        problems.append("unregistered_source_code")
    elif code and record.get("licence") != registry[code]["licence"]:
        problems.append("licence_differs_from_registry")
    sha = record.get("source_sha256")
    if sha and not HEX64.match(sha):
        problems.append("malformed_sha256")
    elif sha and sha not in known_hashes:
        problems.append("sha256_not_a_hash_of_an_input_file")
    if record.get("claim_by") == "external_dataset":
        for key in ("source_version",):
            if not record.get(key):
                problems.append(f"missing:{key}")
        if record.get("source_code") not in ("HKG", "RWY"):
            problems.append("external_claim_must_cite_the_external_dataset")
    if record.get("kind") == "derived" and not record.get("derivation"):
        problems.append("derived_without_derivation")
    if str(record.get("field", "")).startswith("edition") and not record.get("edition"):
        problems.append("edition_locator_without_edition_as_named")
    return problems
