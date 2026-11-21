/**
 * Operator script (design section 11, question 13): records the owner's approval to serve the current NON-RELEASE
 * dataset version publicly, or revokes it. Writes the override columns and a curation_audit row in one transaction.
 *
 *   npx tsx src/scripts/db/approve-preview.ts --by owner --reason "preview while data is under review"
 *   npx tsx src/scripts/db/approve-preview.ts --revoke --by owner --reason "first release is current"
 *
 * Targets DATABASE_URL only and refuses when it equals DATABASE_URL_PRODUCTION. See conductor/RUNBOOK.md.
 */
import { config as loadEnvironment } from 'dotenv';
import postgres from 'postgres';
import { connectionOptions, requireDatabaseUrl } from '../../db/connection-options';

const AUDIT_ACTOR = 'system:owner';
const MAX_TEXT = 500;

function iso(value: unknown): string | null {
  return value ? new Date(value as string | Date).toISOString() : null;
}

function option(name: string): string | undefined {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1]?.trim() || undefined : undefined;
}

async function main() {
  loadEnvironment({ path: '.env.local', quiet: true });
  const revoke = process.argv.includes('--revoke');
  const approver = option('by');
  const reason = option('reason');
  if (!approver || !reason || approver.length > MAX_TEXT || reason.length > MAX_TEXT) {
    throw new Error('Usage: approve-preview.ts [--revoke] --by <name> --reason <text> (both required, at most 500 characters).');
  }
  const databaseUrl = requireDatabaseUrl();
  if (process.env.DATABASE_URL_PRODUCTION && databaseUrl === process.env.DATABASE_URL_PRODUCTION) {
    throw new Error('DATABASE_URL points at the production database; this script is not run against production from here.');
  }
  const sql = postgres(databaseUrl, { ...connectionOptions(databaseUrl, 1), onnotice: () => {} });
  try {
    await sql.begin(async (tx) => {
      const [{ name }] = await tx`select current_database() as name`;
      const [loading] = await tx`select 1 from dataset_versions where load_status = 'loading' limit 1`;
      if (loading) throw new Error('A dataset load is in progress; try again when it has finished.');
      const [current] = await tx`
        select id, version_label, release_class, load_status, public_override_by, public_override_reason, public_override_at
        from dataset_versions where is_current for update`;
      if (!current) throw new Error('No current dataset version.');
      if (current.load_status !== 'complete') throw new Error(`The current dataset version is ${current.load_status}, not complete.`);
      if (current.release_class !== 'non_release') throw new Error('The current dataset version is a release; no approval is needed.');

      const before = { by: current.public_override_by, reason: current.public_override_reason, at: iso(current.public_override_at) };
      if (revoke) {
        if (!current.public_override_by) throw new Error('The current dataset version has no approval to revoke.');
        await tx`update dataset_versions set public_override_by = null, public_override_reason = null, public_override_at = null
                 where id = ${current.id}`;
      } else {
        if (current.public_override_by) throw new Error(`Already approved by ${current.public_override_by}; revoke first to change it.`);
        await tx`update dataset_versions
                 set public_override_by = ${approver}, public_override_reason = ${reason}, public_override_at = now()
                 where id = ${current.id}`;
      }
      const [after] = await tx`select public_override_by as by, public_override_reason as reason, public_override_at as at
                               from dataset_versions where id = ${current.id}`;
      await tx`insert into curation_audit (actor, action, entity_type, entity_id, before, after)
               values (${AUDIT_ACTOR}, ${revoke ? 'revoke_preview' : 'approve_preview'}, 'dataset_versions', ${current.id},
                       ${tx.json(before)}, ${tx.json({ by: after.by, reason: after.reason, at: iso(after.at), requested_by: approver, requested_reason: reason })})`;
      console.log(`${revoke ? 'Revoked' : 'Approved'} preview for dataset version ${current.id} in database ${name}.`);
    });
  } finally {
    await sql.end({ timeout: 5 });
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
