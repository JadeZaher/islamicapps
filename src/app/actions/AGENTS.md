# Graph action contracts

## Historical context

`createHistoricalEvent` defaults new records to unverified and non-publication. The legacy `year_hijri` / `year_gregorian` properties remain synchronized aliases for canonical `start_year_hijri` / `start_year_gregorian`; zero is a valid year and must be handled with nullish checks.

Narrator timeline reads are public-facing and fail closed. They expose an event only when it is explicitly publication-ready, human- or source-verified, has a named citation source plus a locator or stable URL, and overlaps at least one known narrator lifetime bound. The deterministic historical seed intentionally fails this gate and therefore remains invisible while it is uncited.

The embedded citation fields are an interim gate. The target reified assertion/citation model and memory constraints are documented in [`../../lib/db/AGENTS.md`](../../lib/db/AGENTS.md).

## Hadith chain reads

Hadith detail reads prefer the direct `HAS_CHAIN` graph. If it has no linked narrator rows, the read layer may fall back to the legacy `HAS_VARIATION` / `TRANSMITTED_VIA` graph. This compatibility path is read-only. Legacy `HEARD_FROM` edges are global rather than chain-scoped evidence, so the UI must expose those linked identities without asserting an order unless `INCLUDES.position` is present.

Every returned narrator and transmission edge retains its `chain_id`; direct-chain rows also retain `chain_index` and `INCLUDES.position`. Consumers must group by chain before ordering so taḥwīl branches are never flattened into one synthetic isnad. Shared legacy source labels may be filtered as unresolved labels, but must not be assigned to one of several possible Imami works.

## Result contract (curation actions, `curation/*.ts`)

Next masks errors thrown by server actions in production, so expected refusals are returned, not thrown:

```ts
type ActionResult<T> = { ok: true; data: T } | { ok: false; message: string; fieldErrors?: Record<string, string[]> };
```

- Every curation action is `attempt(async () => { const actor = await requireCurator(); ... })` (`curation/result.ts`).
  `attempt` returns `ok: false` for `ZodError` (message `field: text`, plus `fieldErrors` by dotted path), `CurationError`
  (validation, publish gate `refused`, `not_found`, `conflict`, `load_in_progress`) and `UnauthorizedError`; anything else
  rethrows and stays a failure.
- Admin clients call `unwrapAction(action(...))` (`src/app/admin/_components/actionError.ts`), which throws an
  `ActionRefusal` carrying the real message; `describeActionError` shows it inline. Only a masked unexpected failure uses
  the caller's fallback sentence.
- `result.ts` is not a `'use server'` module (those may export only async functions); clients import only its type.
- Query functions in `src/db/queries` still throw `CurationError`; the wrapping happens once, in the action.

