/**
 * mode-diff.ts — Incremental diff-and-patch for the isnad graph.
 * ==============================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream E
 *
 * Entry point: runModeDiff(args)
 *
 * For each row in the unified CSV, compare to the existing :Hadith node in DB
 * on the stable business key (dataset_row_id else pipeline_key). Only MERGE
 * if the node is missing OR a tracked mutable field changed.
 *
 * A second run reports added=0, updated=0 (idempotent).
 *
 * Summary emitted: { added, updated, unchanged, tombstoned }
 *   - tombstoned: rows in DB (active, non-tombstoned) whose biz key is NOT in
 *     the current CSV — these are marked tombstoned (tombstone-by-omission).
 *     This handles the FR-0.11 backfill gap that fullregen leaves open.
 *
 * Tracked mutable fields (a change in any of these triggers an UPDATE):
 *   source, tradition, hadith_no, chapter, chapter_no, text_ar, text_en
 *   (subset of load-hadith.ts's mutableProps; legacy `title` / `primary_topic`
 *   / `text_english` columns were removed from UnifiedRow in v2)
 *
 * NEVER DETACH DELETE. Uses tombstoneByKey for soft deletes.
 */

import path from 'path';
import crypto from 'crypto';
import fs from 'fs';
import { runQuery, runWrite } from '../../../lib/db/neo4j';
import { buildPipelineKey } from '../../../lib/db/neo4j-helpers';
import { initializeSchema } from '../../../lib/db/schema';
import {
    readUnifiedCsv,
    createRegenLogger,
    canonicalizeTradition,
    type UnifiedRow,
    type LoadContext,
} from './io';
import { mergeDatasetVersion, deactivateOtherVersions } from './dataset-version';
import { loadHadith } from './load-hadith';
import { tombstoneByKey } from './tombstone';
import type { CliArgs } from '../../regen-isnad-graph';

// ─── Dataset path resolution ──────────────────────────────────────────────────

function resolveDatasetPaths(): { hadithPath: string; rawiPath: string } {
    const bases = [
        path.join(process.cwd(), 'datasets'),
        path.join(process.cwd(), '..', 'datasets'),
    ];
    for (const base of bases) {
        const hadithPath = path.join(base, 'hadith-data', 'all_hadiths_unified.csv');
        const rawiPath = path.join(base, 'narrator-data', 'all_rawis.csv');
        if (fs.existsSync(hadithPath)) {
            return { hadithPath, rawiPath };
        }
    }
    throw new Error('Could not locate datasets/hadith-data/all_hadiths_unified.csv');
}

function sha256File(filePath: string): string {
    const buf = fs.readFileSync(filePath);
    return crypto.createHash('sha256').update(buf).digest('hex');
}

// ─── Fetch a batch of existing hadith nodes keyed by dataset_row_id ──────────

interface DbHadith {
    dataset_row_id: number | null;
    pipeline_key: string | null;
    source: string;
    tradition: string;
    hadith_no: string;
    chapter: string;
    chapter_no: string;
    text_ar: string;
    text_en: string;
    tombstoned: boolean;
}

async function fetchByRowId(rowId: number): Promise<DbHadith | null> {
    const rows = await runQuery<DbHadith>(`
        MATCH (h:Hadith { dataset_row_id: $rowId })
        RETURN h.dataset_row_id AS dataset_row_id,
               h.pipeline_key AS pipeline_key,
               h.source AS source,
               h.tradition AS tradition,
               h.hadith_no AS hadith_no,
               h.chapter AS chapter,
               h.chapter_no AS chapter_no,
               h.text_ar AS text_ar,
               h.text_en AS text_en,
               h.tombstoned AS tombstoned
        LIMIT 1
    `, { rowId });
    return rows[0] ?? null;
}

async function fetchByPipelineKey(pipelineKey: string): Promise<DbHadith | null> {
    const rows = await runQuery<DbHadith>(`
        MATCH (h:Hadith { pipeline_key: $pipelineKey })
        RETURN h.dataset_row_id AS dataset_row_id,
               h.pipeline_key AS pipeline_key,
               h.source AS source,
               h.tradition AS tradition,
               h.hadith_no AS hadith_no,
               h.chapter AS chapter,
               h.chapter_no AS chapter_no,
               h.text_ar AS text_ar,
               h.text_en AS text_en,
               h.tombstoned AS tombstoned
        LIMIT 1
    `, { pipelineKey });
    return rows[0] ?? null;
}

// ─── Field comparison ─────────────────────────────────────────────────────────

function hasChanged(row: UnifiedRow, db: DbHadith): boolean {
    const tradition = canonicalizeTradition(row.tradition as string);
    const checks: Array<[string, string, string]> = [
        ['source', row.source, db.source ?? ''],
        ['tradition', tradition, db.tradition ?? ''],
        ['hadith_no', row.hadith_no, db.hadith_no ?? ''],
        ['chapter', row.chapter, db.chapter ?? ''],
        ['chapter_no', row.chapter_no, db.chapter_no ?? ''],
        ['text_ar', row.text_ar, db.text_ar ?? ''],
        ['text_en', row.text_en, db.text_en ?? ''],
    ];
    return checks.some(([, a, b]) => a !== b);
}

// ─── Tombstone-by-omission: find DB hadiths not present in CSV ───────────────

async function fetchAllLiveBusinessKeys(): Promise<Set<string>> {
    // Returns a set of string representations of live hadith business keys.
    // Format: "rowid:<id>" or "pipkey:<key>"
    const rows = await runQuery<{
        dataset_row_id: number | null;
        pipeline_key: string | null;
    }>(`
        MATCH (h:Hadith)
        WHERE NOT h.tombstoned = true
        RETURN h.dataset_row_id AS dataset_row_id, h.pipeline_key AS pipeline_key
    `);
    const keys = new Set<string>();
    for (const row of rows) {
        if (row.dataset_row_id !== null && row.dataset_row_id !== undefined) {
            keys.add(`rowid:${row.dataset_row_id}`);
        } else if (row.pipeline_key) {
            keys.add(`pipkey:${row.pipeline_key}`);
        }
    }
    return keys;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export async function runModeDiff(args: CliArgs): Promise<void> {
    console.log('='.repeat(64));
    console.log('  Isnad/Narrator Graph — Diff Mode');
    console.log('='.repeat(64));

    await initializeSchema();

    const { hadithPath, rawiPath } = resolveDatasetPaths();
    console.log(`\n[diff] Hadith CSV: ${hadithPath}`);

    const unifiedHash = sha256File(hadithPath);
    const rawisHash = fs.existsSync(rawiPath) ? sha256File(rawiPath) : '';
    const contentHash = crypto
        .createHash('sha256')
        .update(`unified:${unifiedHash}\nrawis:${rawisHash}`)
        .digest('hex');

    // Provenance node for this diff run.
    const { id: dvId } = await mergeDatasetVersion({
        expectedRecordCount: 99283,
        perTraditionCounts: {},
        contentHash,
        versionLabel: `diff-${contentHash.slice(0, 16)}`,
    });
    await deactivateOtherVersions(dvId);
    console.log(`[diff] DatasetVersion id: ${dvId}`);

    const logger = createRegenLogger('diff', dvId);
    const ctx: LoadContext = {
        dvId,
        mode: 'diff',
        log: logger.write.bind(logger),
    };

    // Load the full set of live biz keys from DB before streaming CSV.
    // This allows tombstone-by-omission at the end.
    console.log('[diff] Fetching live DB business keys...');
    const dbKeys = await fetchAllLiveBusinessKeys();
    const csvKeys = new Set<string>();

    let added = 0;
    let updated = 0;
    let unchanged = 0;
    let rowNum = 0;

    console.log('[diff] Streaming CSV and comparing to DB...');
    for await (const row of readUnifiedCsv(hadithPath)) {
        rowNum++;

        // Build business key for this row.
        const pipelineKey = buildPipelineKey(row.source, row.hadith_no);
        const bizKeyStr = row.dataset_row_id !== null
            ? `rowid:${row.dataset_row_id}`
            : `pipkey:${pipelineKey}`;
        csvKeys.add(bizKeyStr);

        // Look up existing DB node.
        let dbRow: DbHadith | null = null;
        try {
            if (row.dataset_row_id !== null) {
                dbRow = await fetchByRowId(row.dataset_row_id);
            } else {
                dbRow = await fetchByPipelineKey(pipelineKey);
            }
        } catch (err) {
            logger.write({ action: 'error', row: rowNum, phase: 'fetch', error: String(err) });
        }

        if (!dbRow || dbRow.tombstoned) {
            // Node missing or was tombstoned — create it.
            await loadHadith(row, ctx);
            added++;
            logger.write({ action: 'added', key: bizKeyStr, row: rowNum });
        } else if (hasChanged(row, dbRow)) {
            // Mutable fields changed — update via loadHadith (MERGE ON MATCH SET).
            await loadHadith(row, ctx);
            updated++;
            logger.write({ action: 'updated', key: bizKeyStr, row: rowNum });
        } else {
            // No change — skip the write.
            unchanged++;
            logger.write({ action: 'unchanged', key: bizKeyStr, row: rowNum });
        }

        if (rowNum % 2000 === 0) {
            console.log(`[diff] Progress: ${rowNum} rows | added=${added} updated=${updated} unchanged=${unchanged}`);
        }
    }

    // Tombstone-by-omission: DB hadiths not in the current CSV.
    const omittedKeys = [...dbKeys].filter((k) => !csvKeys.has(k));
    let tombstoned = 0;
    if (omittedKeys.length > 0) {
        console.log(`[diff] Tombstoning ${omittedKeys.length} hadiths not in current CSV...`);
        for (const key of omittedKeys) {
            try {
                if (key.startsWith('rowid:')) {
                    const rowId = parseInt(key.slice('rowid:'.length), 10);
                    await tombstoneByKey('Hadith', 'dataset_row_id', rowId, dvId);
                } else {
                    const pk = key.slice('pipkey:'.length);
                    await tombstoneByKey('Hadith', 'pipeline_key', pk, dvId);
                }
                tombstoned++;
                logger.write({ action: 'tombstoned', key, dvId });
            } catch (err) {
                logger.write({ action: 'tombstone_error', key, error: String(err) });
            }
        }
    }

    logger.close();

    const summary = { added, updated, unchanged, tombstoned };
    console.log('\n' + '='.repeat(64));
    console.log('  Diff Mode Complete');
    console.log('='.repeat(64));
    console.log(`  added=${added} updated=${updated} unchanged=${unchanged} tombstoned=${tombstoned}`);
    console.log('');
    // Machine-readable summary (last line — parseable by callers).
    process.stdout.write(JSON.stringify(summary) + '\n');
}
