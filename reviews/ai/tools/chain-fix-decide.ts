/**
 * Decide every chain fix from the store: pair independent readings per report, mark agreement or dispute, apply the
 * auto-apply rule, append a transition per change, and rewrite the overrides the projection replays
 * (datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz) and the queue. Idempotent: a second run changes nothing.
 */
import path from 'node:path';
import { argumentsOf, DEFAULT_OVERRIDES, DEFAULT_STORE, reconcile, REPOSITORY_ROOT, storePaths, utcNow } from './chain-fix-lib';

const USAGE = `usage: npx tsx reviews/ai/tools/chain-fix-decide.ts [--store <dir>] [--overrides <file.jsonl.gz>]
  Rule: a reading is accepted when at least two reader runs gave it, at least one of them blind to the stored chain, and
  it has at least twice the runs of every other reading together; readings that disagree otherwise are disputed and nothing
  is applied. A lone reading that leaves the stored chain unchanged is recorded beside it. Human reviews then decide.`;

const args = argumentsOf(process.argv.slice(2));
if (args.has('help')) {
  console.log(USAGE);
} else {
  try {
    const overrides = args.get('overrides') ?? DEFAULT_OVERRIDES;
    const { states, transitions } = reconcile(storePaths(args.get('store') ?? DEFAULT_STORE), overrides, utcNow());
    const count = (state: string) => states.filter((s) => s.state === state).length;
    console.log(`fixes ${states.length}: accepted ${count('accepted')}, confirmed ${count('confirmed')}, disputed ${count('disputed')}, submitted ${count('submitted')}, rejected ${count('rejected')}, other ${states.length - count('accepted') - count('confirmed') - count('disputed') - count('submitted') - count('rejected')}`);
    for (const transition of transitions as { fix_id: string; from: string | null; to: string; why: string }[]) {
      console.log(`     ${transition.fix_id}: ${transition.from ?? 'new'} -> ${transition.to} (${transition.why})`);
    }
    console.log(`wrote ${path.relative(REPOSITORY_ROOT, overrides).replace(/\\/g, '/')} (${states.filter((s) => s.effect).length} reports)`);
  } catch (error) {
    console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}
