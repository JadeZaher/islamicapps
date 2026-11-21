/** drizzle-kit config: one migration stream, drizzle/core. See src/db/AGENTS.md §Migrations. */
import { config as loadEnvironment } from 'dotenv';
import { defineConfig } from 'drizzle-kit';

loadEnvironment({ path: '.env.local', quiet: true });

export default defineConfig({
  dialect: 'postgresql',
  schema: './src/db/schema/index.ts',
  out: './drizzle/core',
  dbCredentials: { url: process.env.DATABASE_URL ?? '' },
  migrations: { table: '__drizzle_migrations', schema: 'drizzle' },
  strict: true,
  verbose: true,
});
