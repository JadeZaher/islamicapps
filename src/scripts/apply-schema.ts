/**
 * apply-schema.ts
 *
 * Idempotently applies constraints and indexes from src/lib/db/schema.ts
 * to the Neo4j database. Safe to re-run.
 *
 * Usage: tsx src/scripts/apply-schema.ts
 */

import { loadEnv } from './lib/env';
import { initializeSchema } from '../lib/db/schema';
import { closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
    try {
        await initializeSchema();
    } catch (err) {
        console.error('❌ Schema apply failed:', err);
        process.exit(1);
    } finally {
        await closeDriver();
    }
}

main();
