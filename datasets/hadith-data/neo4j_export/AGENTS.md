# Neo4j graph bundle invariants

## Publication boundary

This directory builds an additive bulk-import bundle. It never mutates the
canonical CSVs or connects to Neo4j. The generated PowerShell loader performs a
dry run first and imports only when the operator also supplies `-Execute`.
Overwrite mode is always disabled.

`source_release_state` describes the supplied source snapshot. Its default is
`unreviewed_local_snapshot`; neither a successful export nor a valid bulk-import
shape changes that state. `import_ready` means structural integrity only.
`publication_ready` remains a separate, stricter validation result.

Machine translation and narrator-alias candidate assets are rejected as inputs.
Rows marked `machine_unreviewed` are omitted from the canonical Translation
surface and counted on Hadith nodes and in the manifest. Blank/unprovenanced
translations are omitted too. Eligible source translations are exported with
`candidate_only=false`, their original status/provenance/review fields intact,
and no implicit promotion.

## Identity

Every ID is immutable and namespaced. Hadiths use `hadith:<record_id>`, rawi
people use `narrator:rawi:<scholar_indx>`, and chains/mentions are keyed by the
record plus zero-padded branch and position. Collections resolve through
`source_work_registry.json`; display labels are never hashed into collection
identity.

Thaqalayn Chapter identity uses the category/chapter components of its provider
URL. OpenITI chapter ordinals reset, so the only supported flattened identity
is volume plus local ordinal plus NFC-normalized source heading; the heading
hash is retained as a provider locator instead of pretending the ordinal is
globally unique.

Each CSV has a Neo4j import-only ID token plus the same value as a persisted
`id` property. Post-import constraints apply to that persisted property.

The registry is the complete 34-work contract. Imami IDs are preserved from the
provider reconciliation registry. Non-Imami IDs use the stable slugs already
used by `src/lib/constants/sources.ts`.

## Isnad evidence

`extract_isnad_branches` and `name_normalize` are reused exactly. Every
extractable source branch becomes a Chain plus ordered NameMention nodes.
`NEXT_IN_CHAIN` preserves source adjacency even when no narrator identity is
resolved.

`chain_indx` is materialized only when its branch count and every branch length
match the extracted surface graph and every rawi ID exists. Resolution is
all-or-nothing per report: only then are `RESOLVES_TO`, narrator `INCLUDES`, and
occurrence-bound `NARRATED_FROM` emitted. Extraction-limit failures are
reported and never replaced with guessed chains.

The canonical extractor keeps its normal 64-branch guard. The offline bundle
may retry a finite rejected expansion up to 256 branches; the exporter restores
the shared limit immediately and records every retry. Empty branches contain
no occurrence evidence and are dropped before contiguous branch numbering.

## Evidence gates

Per-report Evidence nodes retain upstream locators, Arabic hashes, and
translation provenance. They are not curated scholarly citations.

The selected schema-v2 curation manifest is a required, hash-bound input for a
`development_nonrelease` export. Its evidence gate currently binds an
empty/non-ready `evidence_curation.json`; Citation, Place, and Event node files
and their claim relationships therefore remain header-only.

Every rawi row has one `Biography:Profile:SourceProfile` node with immutable ID
`biography:narrator-lexicon:<scholar_indx>`. It preserves all 23 profile columns
verbatim, binds them with `raw_profile_sha256`, and records
`source_status_unknown`, `source:narrator-lexicon`, and the exact row locator.
These are source-provided lexicon surfaces, not citation-curated biographical
claims. Dates, places, family names, interests, tags, and books remain raw
profile properties until separately cited identity resolution can justify
dedicated Place, Person, or bibliographic nodes.

Indexed `teachers_inds` and `students_inds` values may emit `STUDENT_OF` only
when both positive rawi endpoints exist and differ. Direction is always
student to teacher: a student's `teachers_inds` and a teacher's
`students_inds` are aggregated as named evidence fields on one stable pair.
Missing endpoints and source self-links remain raw profile evidence, are
omitted from graph edges, and are counted in the manifest. An edge corroborated
by both fields still has `source_status_unknown`; agreement inside one lexicon
does not become human or citation verification.

Repeated indices within one source field deduplicate to the same graph edge,
but never disappear from the audit. The manifest separately records raw
indexed-token count, fields containing duplicates, and excess duplicate
occurrences; the validator re-derives each count from the bound rawi input.
`source_status_unknown` is an explicit publication blocker independent of the
empty citation-curation gate.

The two documented Thaqalayn source-quality exclusions remain visible as
flagged Hadith and Evidence records. Neither emits translation or attribution
claims. The confirmed paratext omits chain assertions; the long report keeps
extractable source-surface chain evidence.

## Determinism

Inputs are streamed. Rows are staged in SQLite and written in stable key order
as UTF-8, LF-terminated RFC4180 CSV. Hash-bearing JSON contains no runtime
timestamps or output-directory paths. A bundle manifest binds every graph and
support file by header, row count, byte size, and SHA-256.

The rawi header is exact rather than open-ended. A new profile field must be
added to the contract before export so upstream columns cannot disappear
silently. Every `DictReader` row must also have exactly that shape: surplus
cells under the `None` key and missing trailing values are hard failures.
Complete-corpus validation requires the hash-bound rawi input to remain
available; otherwise the profile-binding gate reports both unavailable and
unperformed and cannot pass.
