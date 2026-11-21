/** The single app database client: lazy, one pool per process, survives dev hot reload. See src/db/AGENTS.md §Client. */
import 'server-only';
import { drizzle, type PostgresJsDatabase } from 'drizzle-orm/postgres-js';
import postgres, { type Sql } from 'postgres';
import { connectionOptions, requireDatabaseUrl } from './connection-options';
import * as schema from './schema';

export type Database = PostgresJsDatabase<typeof schema> & { $client: Sql };

type DatabaseCache = { sql: Sql; database: Database; shutdownHookInstalled: boolean };

const globalCache = globalThis as typeof globalThis & { __islamicappsDatabase?: DatabaseCache };

/** Closes the pool on SIGTERM so draining deploys end connections cleanly (section 3.3). */
function installShutdownHook(cache: DatabaseCache) {
  if (cache.shutdownHookInstalled) return;
  cache.shutdownHookInstalled = true;
  process.once('SIGTERM', () => {
    const onlyListener = process.listenerCount('SIGTERM') === 0;
    void cache.sql.end({ timeout: 5 }).finally(() => {
      // If nothing else (Next.js) handles SIGTERM, exit ourselves; our listener disabled the default.
      if (onlyListener) process.exit(0);
    });
  });
}

/** Returns the process-wide client, creating it on first use (never at import, so builds never connect). */
export function getDatabase(): Database {
  if (!globalCache.__islamicappsDatabase) {
    const databaseUrl = requireDatabaseUrl();
    const sql = postgres(databaseUrl, connectionOptions(databaseUrl, 5));
    const database = drizzle(sql, { schema });
    globalCache.__islamicappsDatabase = { sql, database, shutdownHookInstalled: false };
  }
  installShutdownHook(globalCache.__islamicappsDatabase);
  return globalCache.__islamicappsDatabase.database;
}

/** `db` facade: every property access resolves the lazily created client. */
export const db: Database = new Proxy({} as Database, {
  get(_target, property) {
    const database = getDatabase();
    const value = Reflect.get(database, property, database);
    return typeof value === 'function' ? value.bind(database) : value;
  },
});
