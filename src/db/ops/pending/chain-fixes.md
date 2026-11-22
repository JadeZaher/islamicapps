# Chain fixes: promoted 2026-11-22

Promoted as `drizzle/core/0019_chain_fixes_compiler.sql`. Declarations: `src/db/schema/chain-fixes.ts` (and `chains.chain_fix_id`
in `isnad.ts`); load invariants: `src/db/load/verify-data.ts` (§Chain fixes); apply and revert: `src/db/ops/chain-fix-apply.ts`
(`npm run db:chain-fixes`) with its flow test `src/db/ops/__tests__/chain-fix-apply.test.ts`. Design and checklist:
`docs/review/chain-fix-pipeline.md`; rationale: `src/db/AGENTS.md` §Chain fixes. The drafts that stood here were folded into
those files and removed.
