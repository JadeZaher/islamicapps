/** Loader connection: one long-lived session (advisory lock, COPY, merge), optional throwaway schema. */
import { config as loadEnvironment } from 'dotenv';
import postgres from 'postgres';
import { connectionOptions, requireDatabaseUrl } from '../connection-options';

export type LoaderSql = ReturnType<typeof openLoaderClient>;

/** Refuses the production variable outright; the loader reads DATABASE_URL only. */
export function developmentDatabaseUrl(): string {
  loadEnvironment({ path: '.env.local', quiet: true });
  const databaseUrl = requireDatabaseUrl();
  if (process.env.DATABASE_URL_PRODUCTION && process.env.DATABASE_URL_PRODUCTION === databaseUrl) {
    throw new Error('DATABASE_URL equals DATABASE_URL_PRODUCTION; the loader refuses to run against production from here.');
  }
  return databaseUrl;
}

/** A single-connection client with no idle or lifetime recycling, so session locks survive the load. */
export function openLoaderClient(databaseUrl: string, schema?: string) {
  if (schema !== undefined && !/^[a-z_][a-z0-9_]*$/.test(schema)) throw new Error(`unsafe schema name: ${schema}`);
  return postgres(databaseUrl, {
    ...connectionOptions(databaseUrl, 1),
    idle_timeout: 0,
    max_lifetime: null,
    connect_timeout: 30,
    onnotice: () => {},
    connection: {
      application_name: 'islamicapps-db-load',
      ...(schema ? { search_path: `${schema}, public` } : {}),
    },
  });
}
