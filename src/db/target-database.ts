/**
 * Which database an operator script writes (no server-only import). `--database development` reads DATABASE_URL and
 * refuses the production database; `--database production` reads DATABASE_URL_PRODUCTION and also needs the explicit
 * `--confirm-production` flag. See src/db/AGENTS.md §Operator scripts and production.
 */
import { config as loadEnvironment } from 'dotenv';

export type TargetName = 'development' | 'production';

export interface TargetDatabase {
  name: TargetName;
  url: string;
}

function argument(argv: readonly string[], name: string): string | undefined {
  const index = argv.indexOf(`--${name}`);
  if (index >= 0) return argv[index + 1];
  const inline = argv.find((value) => value.startsWith(`--${name}=`));
  return inline?.slice(name.length + 3);
}

/**
 * Resolves the target from `argv` and points DATABASE_URL at it, so the app client and the query layer use it too.
 * `required`: refuse when `--database` is absent (scripts written after 2026-11-21); otherwise development.
 * Never echoes a connection string.
 */
export function resolveTargetDatabase(argv: readonly string[], options: { required: boolean }): TargetDatabase {
  loadEnvironment({ path: '.env.local', quiet: true });
  const requested = argument(argv, 'database');
  if (requested === undefined && options.required) {
    throw new Error('Say which database: --database development, or --database production --confirm-production.');
  }
  const name = (requested ?? 'development') as TargetName;
  const production = process.env.DATABASE_URL_PRODUCTION?.trim() || undefined;
  if (name === 'production') {
    if (!argv.includes('--confirm-production')) {
      throw new Error('--database production writes the live database; add --confirm-production to proceed.');
    }
    if (!production) throw new Error('DATABASE_URL_PRODUCTION is not set.');
    process.env.DATABASE_URL = production;
    return { name, url: production };
  }
  if (name !== 'development') throw new Error(`--database must be development or production, not "${name}".`);
  const development = process.env.DATABASE_URL?.trim();
  if (!development) throw new Error('DATABASE_URL is not set.');
  if ((production && development === production) || new URL(development).pathname === '/railway') {
    throw new Error('DATABASE_URL points at the production database; use --database production --confirm-production.');
  }
  return { name, url: development };
}
