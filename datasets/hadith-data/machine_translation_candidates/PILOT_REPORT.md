# Local candidate pilots — 2026-07-21/22

The local LM Studio server at `127.0.0.1:1234` was used with the installed
`google/gemma-4-e4b` model. LM Studio reported architecture `gemma4` and
quantization `Q4_K_M`; the hardened run supplied the explicit build-version
identifier `gguf:gemma4:Q4_K_M`. Both pilots used prompt
`hadith-machine-translation-v1`, temperature `0`, top-p `1`, seed `20260721`,
and streamed output.

The historical one-row pilot processed `k6:3631`. It remains in the append-only
artifact as machine-unreviewed evidence, but predates the hardened run-ID,
response-bound telemetry, and explicit caller-supplied build-version contract.
It must not be promoted.

After the legacy-master identity compatibility check was hardened and its six
focused tests passed, two concurrent workers shared the same SQLite claim ledger
and append-only artifact. Each attempted ten rows. The combined bounded run:

- accepted 20 distinct K6 missing-translation candidates;
- rejected zero rows and recorded zero transport/model errors;
- lost zero claims, recovered zero stale claims, and found zero invalid backlog
  identities;
- observed 13 `claimed_elsewhere` skips across the two workers, demonstrating
  that overlapping scans did not duplicate work.

The artifact now contains 21 distinct `translation:missing` records in total.
Every event is `candidate_only: true`, has review state `machine_unreviewed`,
and has validation status `accepted_machine_unreviewed`; no event has mechanical
validation errors. The 20 hardened events record their generation run IDs,
response byte/chunk counts, exact Arabic SHA-256 values, source-row identities,
and `gguf:gemma4:Q4_K_M` version string.

These checks only detect refusals, placeholders, copied input, Arabic leakage,
wrong-language shape, suspiciously short output, stale identity, and candidate
collisions. They do not establish translation accuracy, completeness, edition
fidelity, scholarly acceptance, rights clearance, or publication fitness. No
candidate was written to `translation_overrides.jsonl`; no review state,
canonical corpus, manifest, or publication gate was changed. The full 853-row
K6 gap therefore remains blocked until qualified reviewers verify and promote
individual hash-bound translations through the documented workflow.
