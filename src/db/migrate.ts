/** Programmatic migrator for drizzle/core (section 2.6): lock and statement timeouts, data-write lock, retries. */
import path from 'node:path';
import { config as loadEnvironment } from 'dotenv';
import { drizzle } from 'drizzle-orm/postgres-js';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import postgres from 'postgres';
import { DATA_WRITE_LOCK_KEY } from './advisory-locks';
import { connectionOptions, requireDatabaseUrl } from './connection-options';

const LOCK_NOT_AVAILABLE = '55P03';
const RETRY_DELAYS_MS = [2_000, 5_000, 10_000];

function isLockTimeout(error: unknown): boolean {
  return typeof error === 'object' && error !== null && (error as { code?: string }).code === LOCK_NOT_AVAILABLE;
}

/** Runs `operation`, retrying a lock timeout three times with backoff. */
async function withLockRetry<T>(label: string, operation: () => Promise<T>): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      if (!isLockTimeout(error) || attempt >= RETRY_DELAYS_MS.length) throw error;
      const delay = RETRY_DELAYS_MS[attempt];
      console.warn(`[migrate] ${label}: lock timeout, retry ${attempt + 1}/${RETRY_DELAYS_MS.length} in ${delay} ms`);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}

async function main() {
  loadEnvironment({ path: '.env.local', quiet: true });
  const databaseUrl = requireDatabaseUrl();
  const migrationsFolder = path.resolve(process.cwd(), 'drizzle/core');
  const sql = postgres(databaseUrl, { ...connectionOptions(databaseUrl, 1), onnotice: () => {} });
  let lockHeld = false;
  try {
    await sql`set lock_timeout = '5s'`;
    await sql`set statement_timeout = '60s'`;
    await withLockRetry('data-write lock', () => sql`select pg_advisory_lock(${DATA_WRITE_LOCK_KEY}::bigint)`);
    lockHeld = true;
    await withLockRetry('migrations', () =>
      migrate(drizzle(sql), { migrationsFolder, migrationsTable: '__drizzle_migrations', migrationsSchema: 'drizzle' }),
    );
    const [{ applied }] = await sql<{ applied: number }[]>`select count(*)::int as applied from drizzle.__drizzle_migrations`;
    console.log(`[migrate] ok: ${applied} migrations recorded in drizzle.__drizzle_migrations`);
  } finally {
    if (lockHeld) await sql`select pg_advisory_unlock(${DATA_WRITE_LOCK_KEY}::bigint)`.catch(() => undefined);
    await sql.end({ timeout: 5 });
  }
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[migrate] failed: ${message}`);
  process.exit(1);
});
