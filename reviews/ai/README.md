---
type: reference
---

# AI specialist review: prompts, packets, records

An AI specialist review is a fresh model, given one saved system prompt and one packet of evidence, answering one
question about each claim in the packet. It knows nothing about how the claim was produced. Every review notes the
model and the time. Rule procedures (deterministic code) are the other kind of AI review; they are documented on
`/method` and in `docs/review/ai-review.md`, and are never recorded here.

| Path | What |
| --- | --- |
| `prompts/<specialist>.md` | The system prompt. Its front matter carries `specialist` and `version`; its SHA-256 (exact bytes, LF line endings, see `../.gitattributes`) is recorded on every review. The prompt is the documentation of what the reviewer was told |
| `specialists.json` | Generated registry: specialist, prompt version and hash, recommended model, and every model that has run it (from `records/`). `npx tsx reviews/ai/tools/build-specialist-registry.ts [--check]` |
| `packets/<specialist>/<batch>/packet-NN.json` | What the reviewer sees |
| `packets/<specialist>/<batch>/packet-NN.manifest.json` | What the reviewer must never see: the claim key and content hash behind each item, its sampling stratum, what the pipeline concluded, and any recorded answer |
| `packets/<specialist>/<batch>/batch.json` | How the batch was drawn: seed, strata, dataset version, builder code hash, prompt hash |
| `records/<specialist>/<batch>.jsonl` | One review record per claim (format below), loadable into `ai_reviews` (`docs/review/schema-proposal.ts`) |
| `tools/` | Builders, the output validator and recorder, the registry builder, tests |

## Packets

A packet (`shura-review-packet/1`) is self-contained: the Arabic text with its hash, the claim, the candidates, the
cited passages with locators, and the glossary definitions the prompt relies on. Every quotable text is a
`passages` entry with an id, so the validator can check that each quote in the answer really occurs there.

What a packet never contains: scores (Jaccard, containment, confidence), basis labels or tiers, agreement classes,
the pipeline's resolution, display decisions, or a recorded answer. The writer refuses a packet with any such key
(`LEAKING_KEYS` in `tools/specialist-lib.ts`) and the test checks the packets on disk. Candidates are ordered by
SHA-256 of a salt and the candidate id, and correspondence texts are labelled A and B the same way, so order carries
no hint. An identity candidate does say who asserts it (the K6 source index, the narrator lexicon, the Imams'
convention table): that is provenance a scholar would be given, not the verdict.

Builders read production with SELECT only, inside one `READ ONLY` transaction on a read-only session:

```
npx tsx reviews/ai/tools/build-identity-packets.ts --batch pilot-1 [--seed pilot-1] [--per-stratum 8]
npx tsx reviews/ai/tools/build-correspondence-packets.ts --batch pilot-1 [--seed pilot-1] [--per-stratum 5]
```

## Isolation: how an orchestrator runs a specialist

1. Launch a **fresh** subagent per packet (no shared conversation, no memory, no tools beyond reading one file).
2. Give it exactly two things: the system prompt file's contents as its instructions, and the packet path with the
   line "Read only this file. Answer with the JSON object your instructions define."
3. Do not pass the manifest, `batch.json`, the README, earlier outputs or any other packet. Do not tell it the
   stratum or that some items have recorded answers.
4. Note the exact model id the runtime reports and the UTC time immediately before launch and after the answer.
5. Save the answer verbatim as `packets/<specialist>/<batch>/packet-NN.<model>.output.json`.
6. Record it:

```
npx tsx reviews/ai/tools/record-specialist-run.ts --packet <packet.json> --output <output.json> \
  --model claude-opus-5-5 --runtime "Claude Code subagent" \
  --started 2026-11-21T14:00:00Z --finished 2026-11-21T14:01:10Z --run-id <orchestrator run id>
npx tsx reviews/ai/tools/build-specialist-registry.ts
```

The recorder refuses an output that misses a claim, answers one twice, steps outside the vocabulary, quotes text
that is not in the passage it names (a fabricated or normalised quote), was produced under another prompt version,
or comes with a non-UTC or reversed time. It prints agreement with the manifest's recorded answers, item by item.

A subagent that can read the file system could open other files; the protocol relies on the instruction plus the
orchestrator never placing answers where the reviewer is told to look. For a stricter run, copy the packet alone to
an empty temporary directory and give the subagent only that path.

## Review record (`shura-ai-review-record/1`)

`record_id`, `review_kind: "specialist"`, `specialist_id`, `specialist_version`, `prompt_path`, `prompt_version`,
`prompt_sha256`, `model_id` (exact, as the runtime reports it), `provider_runtime`, `started_at`, `finished_at` (UTC),
`orchestrator_run_id`, `packet_path`, `packet_id`, `packet_sha256`, `output_sha256`, `item_id`, `claim_id`,
`claim_kind`, `claim_key`, `content_sha256`, `outcome` (`supports`, `contradicts`, `contested`,
`insufficient_evidence`), `reading` (correspondence), `reasons`, `evidence` (passage id and exact quote),
`uncertainty`, `uncertainty_note`, `proposals`.

## Reproducing a review

The packet (by hash), the prompt (by hash), the model id and the output are all on disk; re-running the same prompt
on the same packet with the same model is the reproduction. Models are not deterministic, so a re-run is a second
review with its own record, not a replacement: disagreement between runs is itself a measurement of the specialist.
