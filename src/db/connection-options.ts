/** Connection settings shared by the app client, the migrator and verify (section 3.3). No server-only import. */
import type { Options } from 'postgres';

/** Reads DATABASE_URL or throws a message that names the variable but never echoes a value. */
export function requireDatabaseUrl(): string {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl || databaseUrl.trim() === '') {
    throw new Error(
      'DATABASE_URL is not set. Set it in .env.local for development, or as a Railway service variable in production.',
    );
  }
  return databaseUrl;
}

/** TLS per the URL: an explicit `sslmode` wins; else off on Railway's private network, required elsewhere. */
export function sslForUrl(databaseUrl: string): Options<Record<string, never>>['ssl'] {
  const url = new URL(databaseUrl);
  if (url.searchParams.has('sslmode')) return undefined;
  return url.hostname.endsWith('.railway.internal') ? false : 'require';
}

/** postgres.js options for a client with `maxConnections` connections. */
export function connectionOptions(databaseUrl: string, maxConnections: number): Options<Record<string, never>> {
  return {
    max: maxConnections,
    idle_timeout: 20,
    connect_timeout: 5,
    ssl: sslForUrl(databaseUrl),
  };
}
