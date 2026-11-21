/**
 * Records the owner's rights decision of 2026-11-21 for all 34 works: cleared for publication, Arabic and English,
 * with the English policy `source_provided_and_machine_allowed` (source-provided and machine English, each labelled and
 * credited). One transaction through the query layer (`recordRightsDecisions`), audited as `system:owner-decision`,
 * idempotent: a re-run writes nothing. Refuses unless told which database.
 *
 *   npm run db:record-rights -- --database development [--dry-run]
 *   npm run db:record-rights -- --database production --confirm-production
 *
 * Basis per work: docs/rights/rights-register.md (evidence) and conductor/RUNBOOK.md, "Owner decisions, third round".
 */
import { sql } from 'drizzle-orm';
import { resolveTargetDatabase } from '../../db/target-database';
import type { RightsDecision } from '../../db/queries/curation';
import { sourceByCode, WORK_CREDITS, type SourceCode } from '../../lib/sources/registry';

export const RIGHTS_ACTOR = 'system:owner-decision';
const DECIDED = '2026-11-21';

/** The rights-register section that carries each text source's evidence. */
const REGISTER_SECTION: Partial<Record<SourceCode, string>> = {
  SUN: '§1 (the six books, sunnah.com via Kaggle)',
  NMC: '§2 (NabiMuhammad.com Pure Canon)',
  OITI: '§3 (OpenITI)',
  THQ: '§4 (Thaqalayn)',
};

/** The text source of a work from its registered credit: OpenITI URI, sunnah.com collection, else by tradition. */
export function textSourceForWork(sourceWorkId: string): SourceCode {
  const credit = WORK_CREDITS[sourceWorkId];
  if (credit?.openitiUri) return 'OITI';
  if (credit?.sunnahCollection) return 'SUN';
  return sourceWorkId.startsWith('sunni:') ? 'NMC' : 'THQ';
}

/** The 34 decisions, one per registered work. */
export function ownerRightsDecisions(): RightsDecision[] {
  return Object.keys(WORK_CREDITS)
    .sort()
    .map((sourceWorkId) => {
      const code = textSourceForWork(sourceWorkId);
      const record = sourceByCode(code);
      return {
        source_work_id: sourceWorkId,
        rights_status: 'cleared',
        english_policy: 'source_provided_and_machine_allowed',
        rights_note:
          `Cleared for publication, Arabic and English: owner decision ${DECIDED} (the owner holds permission with full scope; ` +
          `conductor/RUNBOOK.md, "Owner decisions, third round"). Evidence: docs/rights/rights-register.md ${REGISTER_SECTION[code]}. ` +
          'English: source-provided and machine English, each labelled and credited.',
        citation: `${record.name} [${record.code}], ${record.licence.name}; attribution wording on /sources#${record.anchor}`,
      };
    });
}

async function main() {
  const target = resolveTargetDatabase(process.argv, { required: true });
  const decisions = ownerRightsDecisions();
  console.log(`Target: ${target.name} database. Plan: ${decisions.length} works cleared, English policy source_provided_and_machine_allowed.`);
  if (process.argv.includes('--dry-run')) {
    for (const decision of decisions) console.log(`  ${decision.source_work_id}: ${decision.citation}`);
    return;
  }
  const { recordRightsDecisions } = await import('../../db/queries/curation');
  const { getDatabase } = await import('../../db/client');
  try {
    const [{ name }] = Array.from(await getDatabase().execute<{ name: string }>(sql`select current_database() as name`));
    const outcome = await recordRightsDecisions(RIGHTS_ACTOR, decisions);
    console.log(`Database ${name}: ${outcome.written.length} written (audited as ${RIGHTS_ACTOR}), ${outcome.unchanged.length} unchanged.`);
  } finally {
    await getDatabase().$client.end({ timeout: 5 });
  }
}

if (/record-rights\.ts$/.test(process.argv[1] ?? '')) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
