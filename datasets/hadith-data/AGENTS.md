# Hadith data contract

## Canonical assets

`all_hadiths_unified.csv.gz` is the machine-readable master. The plain CSV is
an ignored working copy, while `all_hadiths_clean.csv.gz` and
`all_hadiths_shia.csv.gz` are compatibility projections. Files under
`archive/unified-snapshots/`, including the 97,550-row Excel workbooks, are
point-in-time evidence and must never be selected as current load inputs.

Excel is a review/export surface, not the production ingestion format. A full
load must stream CSV or GZIP records so memory is bounded by a small batch.

## Durable identity and provenance

The numeric `id` column is a display/order value and may change after a rebuild.
Graph merges use `record_id`, which is derived from an immutable upstream key:

- K6 legacy snapshot: preserved source row id (`k6:*`)
- Pure Canon classical collections: `pc_*` id (`pure-canon:*`)
- Thaqalayn: numeric provider-file id plus upstream hadith id (`thaqalayn:*`)
- OpenITI collections: tradition, parsed id, and hadith number (`openiti:*`)

`source_record_id` keeps the human-auditable upstream key and
`provenance_source` names the local lineage asset. Never substitute a new
sequential row number for either field.

For Thaqalayn, persist both the numeric `v2_books` filename as
`provider_file_id` and the API `bookId` as `provider_book_id`. Identity prefers
the numeric provider file plus upstream hadith id. Legacy projections fall back
only to the complete normalized `(URL path, volume, hadith_id)` tuple, never the
mutable transliterated book label. The full corpus must pass a uniqueness
preflight before master assembly.

## Source-work identity

**Current reconciliation contract (takes precedence over the historical note
below):** `source_display_label` preserves the upstream display surface;
`source` must be the canonical source-work name and `source_work_id` the
durable work key when provider metadata distinguishes a work.
`imami_source_work_registry.json` maps exact Thaqalayn V2
`provider_book_id` values to 21 durable Imami works, including separate Mufid
and Saduq *Al-Amali* plus Tusi and Nu'mani *Kitab al-Ghayba* identities. Legacy
rows with only a shared label remain blocked rather than guessed. Provider
metadata establishes work identity only; it never makes a compiler biography
or chronology claim cited or publication-ready.

`source` is a display label, not enough to identify a work or compiler. Release
loads require every observed label to resolve to the canonical source registry
under the same tradition. Never default an unknown source to Sunni. Where one
display label combines multiple works or compilers (currently `Al-Amālī` and
`Kitāb al-Ghayba`), curate a durable source-work key from the provider book ID
before attaching compiler biography or chronology metadata.

## Translation release gate

Every release row must have Arabic source text and English translation. The
only loadable `translation_status` is `complete`; blank text, model refusals,
Arabic copied into English, non-English output, and placeholders remain in
`curation_backlog.csv`. `translation_source`, `translation_model`, and
`translation_review_status` preserve how the English text was obtained.
Release QA mirrors machine-candidate screening: inline `TODO`/`PLACEHOLDER`,
NFKC-normalized copied Arabic, any Arabic-script leakage, and output with less
than 80 percent Latin letters are blockers even when a cell is non-empty.
Release publication currently accepts only `human_verified` and
`source_verified`. `source_status_unknown`, `machine_unreviewed`, blank, and a
bare `source_provided` state remain blocked until attribution, rights, and
content review are complete.

Source-record and provenance fields reject blank, placeholder, and meaningless
tokens. Machine or pipeline provenance requires a namespaced, specific model
identifier such as `google/gemma-4-e4b` or `manual:claude-opus-4.7`; generic
values such as `model`, `ai/model`, or `vendor/x` are not evidence.

The classical English join is by immutable `pc_*` id plus exact Arabic-text
equality. Do not join on `(source, hadith_no)`: those values are heavily
duplicated. The enhanced CSV has precedence. The clean JSONL is a narrow
fallback for a unique complete `(pc_* ID, canonical source, Arabic)` identity,
including an ID absent from the enhanced index. Any duplicate or conflicting
identity is rejected as fallback evidence (identity conflicts abort), and
application still requires exact source and Arabic equality; failed/retranslated
attempts are not eligible merely because their English is nonblank.

Reviewed or source-recovered values belong in `translation_overrides.jsonl`.
Each override must name `record_id`, `arabic_sha256`, `text_en`,
`translation_source`, and `translation_review_status`; model-produced text also
records `translation_model`. Unknown IDs, stale Arabic hashes, duplicate
overrides, and structurally invalid English abort the rebuild.

An exact identity/Arabic join is necessary but not sufficient for an override.
The 2026-07-20 audit rejected 19 historical OpenITI backup candidates (15
Zaydi and four Ibadi): every complete backup `text_en` value contained prompt
instructions, model self-correction or missing-input commentary, or text from a
different hadith. Do not strip a plausible-looking final sentence out of those
responses; that would create a new, unaudited derivative. No entry is eligible
until the complete candidate is a clean translation of the hash-bound Arabic
and receives the required content/provenance review.

`curation_manifest.json` records input hashes, candidate content hash, counts,
and aggregated text, review, provenance, chain, and source-registry gates. A
failed gate may update the audit manifest/backlog but must not replace canonical
CSV/GZIP data. Successful builds stage and verify all three CSV/GZIP pairs,
write deterministic gzip bytes, then replace the manifest last; its logical
hash is the publication commit guard.

Canonical backup and replacement run under a bounded process-wide file lock.
`--allow-incomplete-curation` never writes canonical CSV, GZIP, backlog, or
manifest assets: it writes explicitly named `.incomplete` artifacts under
`development/incomplete-curation/`, which is local and ignored.

`curation_manifest.json` is the active release commit. A failed attempt writes
`curation_candidate_manifest.json` and the latest backlog; if the active
manifest remains ready and byte/hash-bound, it is preserved byte-for-byte. Only
when no valid active publication exists may a non-ready candidate also bootstrap
the canonical manifest path.

`curation_dispositions.jsonl` is provenance, identity, and legal-workflow
metadata only. It supplies no Arabic or English text, is not a translation
override, and never satisfies the translation release gate. Source recovery
still requires rights clearance, Arabic identity validation, and a reviewed
entry in `translation_overrides.jsonl`.

## Sanad and narrator completeness

Blank `sanad`/`chain_indx` and unresolved narrators are evidence gaps, not
permission to invent a chain. Preserve the source text, record the gap, and
attach a cited resolution later. Biographical dates and claims likewise need a
source citation and uncertainty/range representation rather than a guessed
single year.

### Uniform source-surface extraction

`extract_isnad_unified.py` is the canonical text extractor. It returns ordered
Arabic source surfaces and never claims that two surfaces are the same person.
Arabic vocalization and tatweel are removed for parsing and comparison, while
lexical differences, kinship pronouns (`أبيه`, `جده`), collective surfaces
(`بعض أصحابنا`, `آبائه`), and source order remain intact. Identity expansion is
the cited narrator resolver's job.

Taḥwīl reconstruction uses the former candidate C suffix-alignment strategy.
For an earlier branch, the extractor keeps that branch's own (often fuller)
convergence spelling and appends only the unmatched tail of the last branch.
A one-token relational/collective pronoun is too weak to establish convergence.
When no defensible alignment exists, branches remain independent; the extractor
increments `branches_unstitched` instead of guessing a shared path.

Co-transmitters joined at one transmission level are parallel alternatives,
not consecutive teacher/student nodes. Multiple co-transmitter levels expand
as source-ordered Cartesian branches and converge only where the Arabic does.
When a following dual `قالا` marks the current level as a pair, it also
disambiguates relational surfaces such as `أبي و...`; the conjunction is a branch,
not part of a patronymic. Honorific abbreviation removal is token-bounded and
must never delete letters inside names such as `عمر` or `عمرو`.
Branch expansion is capped conservatively at 64. The extractor checks each
co-transmitter product and the projected taḥwīl stitching total before list
allocation, then bounds deduplication. Larger malformed/hostile rows raise
`IsnadExtractionLimitError` rather than consuming unbounded memory.

`_compute_chain_indx(text_ar, fallback=None, resolve_narrator=None)` is the
strict integration boundary used by K6, classical, OpenITI, and Thaqalayn
ingestion. Non-empty Arabic requires a resolver callback. Resolution is atomic:
an unresolved, ambiguous, invalid, or non-positive narrator raises
`UnresolvedNarratorError`; the regeneration wrapper records the failure and
emits an empty whole-row chain, never a plausible-looking partial chain. The
same wrapper catches `IsnadExtractionLimitError` as `rows_extraction_failed`.
The classical loader's earlier surface-display extraction catches the same
typed limit and emits an empty row rather than aborting before that wrapper;
Thaqalayn's staged builder likewise records unresolved/over-limit rows and
emits an empty whole-row chain. Unexpected interface or return-type errors still
abort the staged build. The manifest's every-row chain gate therefore blocks
release. Empty source text may
reuse an explicit structured fallback, but K6 sidecar data is display-only and
never overrides an available Arabic source.

### Narrator identity lookup (exact-normalization-only, tiered)

Automatic narrator identity resolution (`regen_unified_csvs.resolve_narrator`) is exact-only. It tries three tiers
in order; the first tier that has the key decides, a key shared by several scholars is ambiguous and never resolves,
and resolution stays atomic per row.

0. **Exact normalization (unchanged).** `narrator_normalize`: Unicode compatibility, format controls, vocalization,
   tatweel, alef and ya variants, then a unique exact registry key (`exact_index`, whose dict content is exactly the
   historical tier-0 index). A tier-0 match is never replaced by a later tier.
1. **Spelling folds.** `narrator_fold_normalize` applies, in order: `persian_urdu_letter_variants` (ی ے to ي, ک to ك,
   ھ ہ ە to ه), `punctuation_and_whitespace` (every non-letter becomes a space), `nasab_connector_forms` (ابن to بن,
   ابنة to بنت; ابنه stays), `theophoric_compound_spacing` (عبدالله to عبد الله, ال-names only) and
   `kunya_compound_spacing` (ابوالقاسم to ابو القاسم). The key is matched against registry names from which blessing
   formulas have been removed at the source: `_extract_arabic_name` strips `رضي الله عنه`-style formulas (token-bounded
   phrases, also on the unclosed-parenthesis fallback). A registry name that becomes a single bare token only because
   a formula was stripped (for example the Prophet's `محمد`) is withheld from tier 1.
2. **Guarded kunya case fold.** `fold_kunya_case_forms` (ابي/ابا to ابو when a non-connector token follows) is used
   only for a surface that has a nasab (`بن`/`بنت`) or several name components not led by a kunya
   (`kunya_fold_allowed`). A kunya-only or bare single-name surface is never resolved by it, and `ابي بن كعب` keeps its
   ism.

The folds never strip the definite article and never drop a name component. Not adopted (diagnostics only, see
`diagnostics/`): hamza on waw/ya carriers and ta marbuta to ha. Kunya matches outside tier 2, four-character prefixes,
and prefix/containment matches are review candidates only and can never produce a completed narrator ID.
`_extract_arabic_name(name, strip_formulas=False)` returns the historical extraction used for tier-0 keys.
Callers must use `resolve_narrator`; a direct `exact_index.get(narrator_normalize(surface))` is tier 0 only.

### Gold-set provenance and evaluation

`__tests__/fixtures/all-tradition-isnad-gold-v1.jsonl` contains 32 manually
annotated local records: 12 Sunni, 9 Imami, 6 Ibadi, and 5 Zaydi. Thirty entries
contain the complete upstream record text. Two unusually long K6 cases use exact
contiguous chain-bearing excerpts with start/end bounds and declare
`input_scope=chain_bearing_excerpt`. The unittest resolves every declared local
record and compares the fixture text byte-for-byte. OpenITI fixture identity is
`parsed id|hadith number|page ref`, matching regeneration. Every entry records a
stable local identity, provenance asset, source/tradition, selection tags, and
annotation basis. Expected branches are independent manual readings
cross-checked against structured `sanad_detail`, `thaqalaynSanad`, or
`sunni_isnad.jsonl` where those assets exist; the Arabic controls disagreements.

`__tests__/fixtures/tahweel-gold.jsonl` remains the five-row Phase-7 annotation
fixture used by the annotation validator, calibration, IAA, and candidate-pull
tools. Its legacy `hadith_id` schema is deliberately distinct from the
provenance-backed all-tradition evaluator schema.

`algo_evaluate.py` refuses fewer than 30 fixtures and writes tradition-level
quality evidence to `.omc/research/uniform-isnad/algo-evaluation.md`. Release
acceptance requires overall branch-count accuracy >= 0.90, median branch
Jaccard >= 0.90, median normalized ordered edit similarity >= 0.90, plus
per-tradition branch-count accuracy and mean ordered similarity >= 0.80 for
`canonical_uniform`. Reversed narrator order therefore cannot pass on set
overlap alone. Legacy candidates are comparison baselines.
Do not mark the conductor evaluation gate complete until an independent run
records those metrics and the standard-library unittest suite passes.

Regeneration is local-first. A ready curation manifest does not prove the
extractor quality gate; production uniform-isnad readiness requires the saved
evaluator report and local dry-run evidence as separate approvals. Do not start
a long Railway regeneration/repair without a separately approved cutover for
the confirmed project and environment.

### Resolution-audit assets

`audit_narrator_resolution.py` streams a local source snapshot plus the
read-only narrator registry and writes `sanad_resolution_audit.json`. It reports
extracted, unresolved, and fully resolved rows by tradition and source, along
with the most frequent unresolved surfaces. Its output is diagnostic evidence,
not a curation manifest or a publication claim.

`narrator_alias_candidates.json` is deliberately narrower than an alias list (it still reports tier-0 Unicode equivalences only).
It may contain only an exact unique registry match made possible by Unicode
compatibility normalization or removal of Unicode format controls. A candidate
is machine-audited and cannot assert a scholarly alias, replace the registry,
or make an unresolved chain complete. All other surface-to-person proposals
need provenance-backed human review before they can change the registry.

The audit CLI may replace only those two durable default diagnostics or JSON
files under `diagnostics/narrator-resolution/`. It must reject input/registry,
symlink, hardlink, and output-to-output collisions before scanning the corpus.

Base narrator loads are sparse updates. Missing or blank optional fields must
never erase a richer biography already in the graph. Historical events and
epochs are not publication-ready until they have stable IDs and record-level
source citations.

## Citation-bound evidence curation

`evidence_curation.schema.json` and `EVIDENCE_CURATION.md` define
`evidence_curation.json`, the claim bundle for biographies, source authors,
historical events, epochs, bibliographic works, editions, and exact citation
locators. The checked-in bundle is empty and its companion
`evidence_curation_manifest.json` is intentionally non-ready. The gate validates
the bundle against the schema, derives counts from its contents, rejects
duplicate IDs and broken citation/supersession references, and requires every
claim to be `human_verified` or `source_verified`; manifest counts or a ready
boolean cannot substitute for claim evidence. A release needs cited, reviewed
assertions for each surface and must
retain ranges, uncertainty, and competing claims rather than invent exact
birth/death years or silently choosing a disputed date. Historical seed nodes
are not evidence and cannot be promoted through a manifest flip.
