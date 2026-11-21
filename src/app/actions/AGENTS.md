# Graph action contracts

## Historical context

`createHistoricalEvent` defaults new records to unverified and non-publication. The legacy `year_hijri` / `year_gregorian` properties remain synchronized aliases for canonical `start_year_hijri` / `start_year_gregorian`; zero is a valid year and must be handled with nullish checks.

Narrator timeline reads are public-facing and fail closed. They expose an event only when it is explicitly publication-ready, human- or source-verified, has a named citation source plus a locator or stable URL, and overlaps at least one known narrator lifetime bound. The deterministic historical seed intentionally fails this gate and therefore remains invisible while it is uncited.

The embedded citation fields are an interim gate. The target reified assertion/citation model and memory constraints are documented in [`../../lib/db/AGENTS.md`](../../lib/db/AGENTS.md).

## Hadith chain reads

Hadith detail reads prefer the direct `HAS_CHAIN` graph. If it has no linked narrator rows, the read layer may fall back to the legacy `HAS_VARIATION` / `TRANSMITTED_VIA` graph. This compatibility path is read-only. Legacy `HEARD_FROM` edges are global rather than chain-scoped evidence, so the UI must expose those linked identities without asserting an order unless `INCLUDES.position` is present.

Every returned narrator and transmission edge retains its `chain_id`; direct-chain rows also retain `chain_index` and `INCLUDES.position`. Consumers must group by chain before ordering so taḥwīl branches are never flattened into one synthetic isnad. Shared legacy source labels may be filtered as unresolved labels, but must not be assigned to one of several possible Imami works.
