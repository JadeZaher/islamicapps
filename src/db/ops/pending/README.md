> **Promoted 2026-11-21** as `drizzle/core/0008_epochs.sql`; the declarations now live in `src/db/schema/history.ts`.
> `epochs.pending.sql` stays only because `src/db/queries/__tests__/timeline.test.ts` reads it (it is idempotent and
> now redundant with 0008); remove both together.

# Pending schema change: `epochs`

Written 2026-11-21 while migration `0007_report_correspondences` was uncommitted and in progress (its journal entry,
`schema/index.ts` and `verify.ts` counts were being edited), so this change was held back rather than stacked on it.
Nothing here is applied to any database; the query fixture applies `epochs.pending.sql` inside its private schema.

Promote, once `0007` is committed:

1. Move the declarations in `epochs-schema.ts` into `src/db/schema/history.ts` (fix the import paths) and delete this
   folder's `.ts` file.
2. `npx drizzle-kit generate --custom --name=epochs`, paste `epochs.pending.sql` as the body (it is idempotent).
3. `src/db/verify.ts`: expected tables + 1 (`epochs`), views + 1 (`published_epochs`).
4. `npm run db:migrate`, `npm run db:verify`, then
   `npx tsx --conditions=react-server src/scripts/db/seed-history.ts` (seeds the 38 eras; locations and events are
   already there and stay unchanged).

Reads already handle both states (`epochsAvailable()` in `src/db/queries/timeline.ts`).
