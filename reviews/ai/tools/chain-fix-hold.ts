/**
 * Record archive holds: facts about the archive, not the reading, that keep a fix from being applied (reviews/ai/AGENTS.md
 * §Chain fixes). Appends to reviews/ai/records/chain-fixes/archive-holds.jsonl; run chain-fix-decide.ts afterwards.
 *
 *   npx tsx reviews/ai/tools/chain-fix-hold.ts --scan --database production      every fix not yet applied, checked in production
 *   npx tsx reviews/ai/tools/chain-fix-hold.ts --fix <chain-fix:id> --code <code> --detail "<why>" --by <name>
 */
import { existsSync, readFileSync } from 'node:fs';
import {
  appendRecords,
  ARCHIVE_HOLD_FORMAT,
  argumentsOf,
  DEFAULT_STORE,
  readArchiveHolds,
  storePaths,
  utcNow,
  type ArchiveHold,
  type FixState,
} from './chain-fix-lib';

/** The archive check every scan runs: later reports repeat this report's chain, so rewriting it would break theirs. */
export const CITED_BY_LATER_REPORT = 'cited_by_later_report';

async function main(): Promise<number> {
  const args = argumentsOf(process.argv.slice(2));
  const paths = storePaths(args.get('store') ?? DEFAULT_STORE);
  const known = new Set(readArchiveHolds(paths).map((hold) => `${hold.fix_id}\u001f${hold.code}`));
  const fresh: ArchiveHold[] = [];
  if (args.has('scan')) {
    if (args.get('database') !== 'production') throw new Error('--scan reads production: add --database production');
    if (!existsSync(paths.state)) throw new Error(`${paths.state} is missing: run chain-fix-decide.ts first`);
    const fixes = (JSON.parse(readFileSync(paths.state, 'utf8')) as { fixes: FixState[] }).fixes
      .filter((fix) => fix.database !== 'applied' && (fix.state === 'accepted' || fix.state === 'held'));
    const { readCitingReports } = await import('./chain-fix-database');
    const citing = await readCitingReports(fixes.map((fix) => fix.hadith_id));
    for (const fix of fixes) {
      const reports = citing.get(fix.hadith_id);
      if (!reports) continue;
      fresh.push({ format: ARCHIVE_HOLD_FORMAT, fix_id: fix.fix_id, hadith_id: fix.hadith_id, code: CITED_BY_LATER_REPORT, at: utcNow(), by: 'chain-fix-hold --scan',
        detail: `${reports.length} later report(s) repeat this report's chain (${reports.slice(0, 3).join(', ')}${reports.length > 3 ? ', ...' : ''}); rewriting it would break theirs` });
    }
  } else {
    const [fixId, code, detail, by] = ['fix', 'code', 'detail', 'by'].map((name) => args.get(name));
    if (!fixId || !code || !detail || !by) throw new Error('give --fix, --code, --detail and --by, or --scan --database production');
    const state = (JSON.parse(readFileSync(paths.state, 'utf8')) as { fixes: FixState[] }).fixes.find((fix) => fix.fix_id === fixId);
    if (!state) throw new Error(`${fixId} is not in ${paths.state}`);
    fresh.push({ format: ARCHIVE_HOLD_FORMAT, fix_id: fixId, hadith_id: state.hadith_id, code, detail, at: utcNow(), by });
  }
  const unseen = fresh.filter((hold) => !known.has(`${hold.fix_id}\u001f${hold.code}`));
  appendRecords(paths.archiveHolds, unseen);
  for (const hold of unseen) console.log(`hold ${hold.fix_id} ${hold.hadith_id}: ${hold.code}: ${hold.detail}`);
  console.log(`recorded ${unseen.length} archive hold(s) (${fresh.length - unseen.length} already recorded); run chain-fix-decide.ts`);
  return 0;
}

main().then(
  (code) => (process.exitCode = code),
  (error) => {
    console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  },
);
