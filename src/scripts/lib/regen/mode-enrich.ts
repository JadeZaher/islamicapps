/**
 * mode-enrich.ts — Generic field-agnostic :Hadith enrichment from JSONL source.
 * ==============================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream E
 *
 * Entry point: runModeEnrich(args)
 *
 * Takes --field=<name> --source=<path/to/enrichment.jsonl>.
 *
 * Each JSONL line must have one of:
 *   { "dataset_row_id": <number>, "<field>": <value> }
 *   { "pipeline_key": <string>,   "<field>": <value> }
 *
 * Rules:
 *   - ONLY writes when the target field is empty/null/missing on the :Hadith node.
 *   - NEVER overwrites a populated field (idempotent, monotonically growing).
 *   - Stamps <field>_source, <field>_enriched_at, <field>_extraction_method='enrich-jsonl'
 *     on the :Hadith node alongside the field value.
 *   - Idempotent: a second run reports added=0, all rows skipped_already_filled.
 *
 * Per-row JSONL log via createRegenLogger():
 *   added | skipped_already_filled | missing_in_db | missing_in_source | error
 *
 * FR-1.11 / spec §9c
 */

import { runQuery, runWrite } from '../../../lib/db/neo4j';
import { initializeSchema } from '../../../lib/db/schema';
import { readJsonl, createRegenLogger } from './io';
import type { CliArgs } from '../../regen-isnad-graph';

// ─── JSONL source record type ─────────────────────────────────────────────────

interface EnrichRecord {
    dataset_row_id?: number;
    pipeline_key?: string;
    [field: string]: unknown;
}

// ─── Fetch current field value from DB ───────────────────────────────────────

async function fetchFieldValue(
    keyProp: 'dataset_row_id' | 'pipeline_key',
    keyValue: number | string,
    field: string
): Promise<{ exists: boolean; current: unknown }> {
    const rows = await runQuery<{ exists: boolean; current: unknown }>(`
        MATCH (h:Hadith { ${keyProp}: $keyValue })
        WHERE NOT h.tombstoned = true
        RETURN true AS exists, h[$field] AS current
        LIMIT 1
    `, { keyValue, field });

    if (!rows.length) return { exists: false, current: null };
    return { exists: true, current: rows[0].current };
}

// ─── Write enriched field + provenance stamps ─────────────────────────────────

async function writeEnrichedField(
    keyProp: 'dataset_row_id' | 'pipeline_key',
    keyValue: number | string,
    field: string,
    value: unknown,
    dvId: string
): Promise<void> {
    // Use parameterized Cypher. The field name itself is interpolated into
    // the SET clause (property names cannot be parameterized in Cypher), but
    // the VALUE is always a parameter. Field names are validated to be safe
    // (alphanumeric + underscore only) before this function is called.
    const cypher = `
        MATCH (h:Hadith { ${keyProp}: $keyValue })
        WHERE NOT h.tombstoned = true
        SET h[$fieldName] = $value,
            h[$fieldSource] = 'enrich-jsonl',
            h[$fieldEnrichedAt] = datetime(),
            h[$fieldExtractionMethod] = 'enrich-jsonl',
            h.updated_at = datetime()
    `;
    await runWrite(cypher, {
        keyValue,
        fieldName: field,
        value,
        fieldSource: `${field}_source`,
        fieldEnrichedAt: `${field}_enriched_at`,
        fieldExtractionMethod: `${field}_extraction_method`,
        dvId,
    });
}

// ─── Field name validation ─────────────────────────────────────────────────────

function isValidFieldName(name: string): boolean {
    return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export async function runModeEnrich(args: CliArgs): Promise<void> {
    const { field, source: sourcePath } = args;

    console.log('='.repeat(64));
    console.log(`  Isnad/Narrator Graph — Enrich Mode (field: ${field})`);
    console.log('='.repeat(64));

    // Validate field name (prevent Cypher injection via SET h.FIELD).
    if (!isValidFieldName(field)) {
        console.error(`[enrich] Invalid field name: "${field}". Must match /^[a-zA-Z_][a-zA-Z0-9_]*$/`);
        process.exitCode = 1;
        return;
    }

    await initializeSchema();

    // Use a synthetic dvId for this enrich run (no DatasetVersion needed for
    // field enrichment, but we need a stable string for the logger file name).
    const runId = `enrich-${field}-${Date.now()}`;
    const logger = createRegenLogger('enrich', runId);

    let rowNum = 0;
    let added = 0;
    let skipped_already_filled = 0;
    let missing_in_db = 0;
    let missing_in_source = 0;
    let errors = 0;

    console.log(`\n[enrich] Source JSONL: ${sourcePath}`);
    console.log(`[enrich] Target field: ${field}`);
    console.log('');

    for await (const record of readJsonl<EnrichRecord>(sourcePath)) {
        rowNum++;

        // Resolve business key.
        let keyProp: 'dataset_row_id' | 'pipeline_key' | null = null;
        let keyValue: number | string | null = null;

        if (record.dataset_row_id !== undefined && record.dataset_row_id !== null) {
            keyProp = 'dataset_row_id';
            keyValue = record.dataset_row_id;
        } else if (record.pipeline_key !== undefined && record.pipeline_key !== null) {
            keyProp = 'pipeline_key';
            keyValue = record.pipeline_key as string;
        } else {
            missing_in_source++;
            logger.write({
                action: 'missing_in_source',
                row: rowNum,
                detail: 'No dataset_row_id or pipeline_key in record',
            });
            continue;
        }

        // Check that the enrichment record actually has the target field.
        if (!(field in record) || record[field] === null || record[field] === undefined || record[field] === '') {
            missing_in_source++;
            logger.write({
                action: 'missing_in_source',
                row: rowNum,
                keyProp,
                keyValue,
                detail: `Field "${field}" not present or empty in source record`,
            });
            continue;
        }

        const newValue = record[field];

        try {
            // Check current DB state.
            const { exists, current } = await fetchFieldValue(keyProp, keyValue, field);

            if (!exists) {
                missing_in_db++;
                logger.write({
                    action: 'missing_in_db',
                    row: rowNum,
                    keyProp,
                    keyValue,
                });
                continue;
            }

            // Skip if already populated (NEVER overwrite).
            if (current !== null && current !== undefined && current !== '') {
                skipped_already_filled++;
                logger.write({
                    action: 'skipped_already_filled',
                    row: rowNum,
                    keyProp,
                    keyValue,
                    field,
                });
                continue;
            }

            // Write the enriched value.
            await writeEnrichedField(keyProp, keyValue, field, newValue, runId);
            added++;
            logger.write({
                action: 'added',
                row: rowNum,
                keyProp,
                keyValue,
                field,
                value: typeof newValue === 'string' ? newValue.slice(0, 80) : newValue,
            });
        } catch (err) {
            errors++;
            logger.write({
                action: 'error',
                row: rowNum,
                keyProp,
                keyValue,
                error: String(err),
            });
            console.error(`[enrich] Error on row ${rowNum}:`, err);
        }

        if (rowNum % 1000 === 0) {
            console.log(
                `[enrich] Progress: ${rowNum} rows | ` +
                `added=${added} skipped=${skipped_already_filled} ` +
                `missing_db=${missing_in_db} missing_src=${missing_in_source} errors=${errors}`
            );
        }
    }

    logger.close();

    const summary = { added, skipped_already_filled, missing_in_db, missing_in_source, errors };
    console.log('\n' + '='.repeat(64));
    console.log(`  Enrich Mode Complete (field: ${field})`);
    console.log('='.repeat(64));
    console.log(
        `  added=${added} skipped_already_filled=${skipped_already_filled} ` +
        `missing_in_db=${missing_in_db} missing_in_source=${missing_in_source} errors=${errors}`
    );
    console.log('');
    process.stdout.write(JSON.stringify(summary) + '\n');

    if (errors > 0) {
        process.exitCode = 1;
    }
}
