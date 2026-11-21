# OpenRouter hadith translation model decision

- Retrieved: 2026-07-21 (America/Denver)
- Intent: choose a cost-conscious Arabic-to-English model and harden a resumable translation run for 12,833 structurally blocked hadith rows.

## Decision

Use `google/gemini-2.5-flash` as the primary generator. Use a stronger model only for mechanically rejected or explicitly uncertain rows; do not silently mix fallback output into the primary provenance stream.

The queue contains 4,644,990 Arabic characters. A conservative estimate of 8-10 million prompt tokens and 1.6-2.0 million output tokens places primary inference near $6.40-$8.00 at list price, or roughly $6.75-$8.45 after OpenRouter's published 5.5% pay-as-you-go fee. Retries and fallback review are outside that estimate.

## Evidence

- OpenRouter model and pricing: https://openrouter.ai/google/gemini-2.5-flash/pricing
  - Model ID: `google/gemini-2.5-flash`
  - List price observed: $0.30/M input tokens and $2.50/M output tokens.
  - Context observed: 1M tokens.
- Google model documentation: https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash
  - Stable model; structured output and thinking controls supported.
- Google language support: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/gemini-experimental
  - Arabic is explicitly listed among supported languages.
- OpenRouter structured output: https://openrouter.ai/docs/guides/features/structured-outputs
  - Use strict JSON Schema and `provider.require_parameters=true`.
- OpenRouter provider routing: https://openrouter.ai/docs/guides/routing/provider-selection
  - Require parameter support and set `data_collection=deny`.
- OpenRouter reasoning controls: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
  - Disable reasoning for deterministic translation; reasoning tokens otherwise bill as output.
- OpenRouter errors/retries: https://openrouter.ai/docs/api/reference/errors-and-debugging
  - Retry transient 429/5xx conditions and honor `Retry-After`; fail fast on authentication, payment, and request-shape errors.
- OpenRouter usage accounting: https://openrouter.ai/docs/cookbook/administration/usage-accounting
  - Persist response ID, native token usage, and response cost for audit and budget enforcement.
- OpenRouter platform pricing: https://openrouter.ai/pricing
  - Pay-as-you-go credit purchases carry a 5.5% fee.

## Run constraints

- The Arabic payload is untrusted data, never model instructions.
- Require a complete translation of isnad and matn without summarization, doctrinal normalization, additions, or omissions.
- Use non-streaming, atomic, strict-schema responses with `translation`, `uncertain`, and `uncertainties` fields.
- Keep every output `candidate_only` and `machine_unreviewed`; no automatic promotion to publication data.
- Preserve exact `record_id`, Arabic SHA-256, source identity, model/response metadata, prompt version, usage, and cost.
- Use a separate OpenRouter artifact and checkpoint from the existing local-Gemma pilot.
- Raise the input bound above the observed 55,003-character maximum and dynamically cap output at 32,768 tokens.
- Enforce a shared client-side spend ceiling because the validated API key has no key-level limit.

## Quality limitation

Strict prompting, structured output, identity binding, and mechanical validation guarantee the shape and provenance of a candidate, not scholarly fidelity. Publication still requires qualified review against the exact Arabic and an authoritative edition/source.

## Pilot outcome

The 14-row rejection pilot completed on 2026-07-22 UTC for `$0.0701776`
(48,242 prompt tokens and 22,282 completion tokens). Thirteen rows passed
mechanical checks; the non-text `* * * * *` source was correctly rejected.
Independent review found eight passes, four concerns, and one semantic failure
among the accepted rows. The failure was a silent internal omission in the
30,498-character Al-Kafi output despite a normal stop and no declared
uncertainty. Do not launch the full queue until long-input coverage and source
prefiltering are improved and a larger reviewed pilot passes.
