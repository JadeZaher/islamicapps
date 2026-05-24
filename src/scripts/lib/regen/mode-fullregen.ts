/**
 * mode-fullregen.ts — Full idempotent isnad graph regeneration.
 * ==============================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream E
 *
 * Entry point: runModeFullregen(args)
 *
 * Processing order:
 *   1. migrateScalarAssessments()  — G-1 remediation (24,347 legacy scalars)
 *   2. SchoolOfThought migration   — FR-1.8: tombstone 4 pseudo-school nodes,
 *                                    migrate [:IN_SCHOOL]→[:FROM_TRADITION]
 *   3. Load all_rawis.csv ONCE → rawis Map (cached for entire run)
 *   4. bulkLoadNarrators()         — H2: merge all :Narrator nodes up-front
 *   5. mergeDatasetVersion(...)    — FR-0.2 provenance node
 *   6. deactivateOtherVersions()   — mark prior versions inactive
 *   7. Stream unified CSV; per row:
 *        resolveNarrators → adapt to NarratorResolutionResult
 *        loadHadith → FROM_TRADITION edge → loadChainForRow
 *        loadGradingsFull / loadAssessment / loadNoExtantEvaluation
 *        loadNameMentions for unresolved
 *   8. flagAllTransmissionEdges()  — G-6 temporal plausibility
 *
 * Invariants:
 *   - NEVER DETACH DELETE; use tombstoneByKey for soft deletes.
 *   - No scalar reliability/grade on :Narrator or :Hadith (G-1).
 *   - Parameterized Cypher only (no string interpolation of user data).
 *   - Tradition canonicalization via canonicalizeTradition() from io.ts.
 *
 * FR-0.11 / INGESTED_IN backfill note: this sweep links every loaded :Hadith
 * via linkHadithToDatasetVersion() (called inside loadHadith). Legacy hadiths
 * NOT present in the unified CSV are not tombstoned by this run — they remain
 * in the graph but lack an INGESTED_IN edge to the active DatasetVersion.
 * A separate diff-mode tombstone-by-omission pass is planned (mode-diff.ts).
 *
 * NARRATED_FROM direction (load-chain.ts:186-187): position i NARRATED_FROM
 * position i+1 — i.e., later in list = earlier in time = teacher.
 * This matches the isnad chain_indx ordering convention in the unified CSV
 * where position 0 is the collector (latest) and the final position is the
 * Prophet / ultimate authority. Direction is CONFIRMED correct per spec §FR-2.1.
 */

import path from 'path';
import crypto from 'crypto';
import fs from 'fs';
import { runWrite, runQuery } from '../../../lib/db/neo4j';
import { initializeSchema } from '../../../lib/db/schema';
import { buildPipelineKey } from '../../../lib/db/neo4j-helpers';
import {
    readUnifiedCsv,
    readAllRawis,
    createRegenLogger,
    canonicalizeTradition,
    type RawiRecord,
    type LoadContext,
} from './io';
import { mergeDatasetVersion, deactivateOtherVersions } from './dataset-version';
import { loadHadith } from './load-hadith';
import {
    loadChainForRow,
    buildTier1Resolution,
    type NarratorResolutionResult,
    type ResolvedNarrator,
    type NameMentionDraft,
} from './load-chain';
import {
    loadAssessment,
    loadNoExtantEvaluation,
    loadGradingsFull,
    migrateScalarAssessments,
    schemeForTradition,
} from './assessment';
import { bulkLoadNarrators } from './load-narrators';
import { loadNameMentions, type LoadNameMentionOpts } from './name-mention';
import { tombstoneByKey } from './tombstone';
import {
    buildBufferedRow,
    loadHadithsBatch,
    loadChainsBatch,
    loadAssessmentsBatch,
    loadNameMentionsBatch,
    type BufferedRow,
    type ChainsBatchResult,
} from './batch-loaders';
import { loadChainsBatchFresh } from './batch-loaders-fresh';
import { buildSupernodeReport, printSupernodeReport } from './supernode-detect';
import { flagAllTransmissionEdges } from './temporal-plausibility';
import {
    resolveNarrators,
    type ResolvedNarrator as ErResolvedNarrator,
    type NameMentionDraft as ErNameMentionDraft,
    type ErTier,
} from './entity-resolution';
import { CANONICAL_SOURCES } from '../../../lib/constants/sources';
import type { CliArgs } from '../../regen-isnad-graph';

// ─── Dataset paths ────────────────────────────────────────────────────────────

function resolveDatasetPaths(): { hadithPath: string; rawiPath: string } {
    const bases = [
        path.join(process.cwd(), 'datasets'),
        path.join(process.cwd(), '..', 'datasets'),
        path.join(process.cwd(), 'data'),
    ];
    for (const base of bases) {
        const hadithPath = path.join(base, 'hadith-data', 'all_hadiths_unified.csv');
        const rawiPath = path.join(base, 'narrator-data', 'all_rawis.csv');
        if (fs.existsSync(hadithPath) && fs.existsSync(rawiPath)) {
            return { hadithPath, rawiPath };
        }
    }
    throw new Error(
        'Could not locate datasets/hadith-data/all_hadiths_unified.csv ' +
        'and datasets/narrator-data/all_rawis.csv. Run from repo root.'
    );
}

function sha256File(filePath: string): string {
    const buf = fs.readFileSync(filePath);
    return crypto.createHash('sha256').update(buf).digest('hex');
}

// ─── Adapter: resolveNarrators → NarratorResolutionResult ────────────────────
//
// entity-resolution.ts (Workstream D) uses ResolvedNarrator.extraction_method.
// load-chain.ts (Workstream C) uses ResolvedNarrator.method.
// The shape is otherwise identical. We adapt here in mode-fullregen, keeping
// both read-only modules untouched.
//
// D also returns a flat { resolved, mentions, method } (no chain_index).
// We wrap it in chain_index=0 since Tier-1 / Tier-2 produce one chain per row.
// Multi-isnad hadiths with real chain_indx arrays go through buildTier1Resolution
// which already handles multi-chain logic.

function adaptErResult(
    erResult: { resolved: ErResolvedNarrator[]; mentions: ErNameMentionDraft[]; method: ErTier },
    chainIndex: number
): NarratorResolutionResult {
    const adapted: ResolvedNarrator[] = erResult.resolved.map((r) => ({
        scholar_indx: r.scholar_indx,
        position: r.position,
        confidence: r.confidence,
        // D's field is `extraction_method`; C's field is `method` — map it.
        method: r.extraction_method,
    }));

    const mentions: NameMentionDraft[] = erResult.mentions.map((m) => ({
        surface_form: m.surface_form,
        normalized_form: m.normalized_form,
        position: m.position,
        // C's NameMentionDraft requires hadith_key and hadith_key_prop.
        // These are filled by loadChainForRow from the row itself; we stub them
        // here and loadChainForRow will re-derive from the row parameter.
        hadith_key: 0,
        hadith_key_prop: 'dataset_row_id' as const,
    }));

    return {
        resolved: adapted,
        mentions,
        method: erResult.method,
        chain_index: chainIndex,
    };
}

// ─── FR-1.8: SchoolOfThought → ReligiousTradition migration ──────────────────
//
// The old importer created 4 pseudo-school :SchoolOfThought nodes and linked
// hadiths/narrators with [:IN_SCHOOL] edges. The corrected schema uses
// [:FROM_TRADITION]->(:ReligiousTradition).
//
// Migration steps:
//   1. MATCH all [:IN_SCHOOL] edges → write [:FROM_TRADITION] to the
//      corresponding :ReligiousTradition node (keyed on tradition name).
//   2. Tombstone the 4 :SchoolOfThought nodes using tombstoneByKey.
//
// NEVER deletes the old edges or nodes (NFR-2 / no-delete directive).
// The old [:IN_SCHOOL] edges remain in the graph but are superseded.

const PSEUDO_SCHOOL_NAMES = ['Sunni', 'Imami', 'Zaydi', 'Ibadi'] as const;

async function migrateSchoolOfThought(dvId: string): Promise<void> {
    console.log('\n[fullregen] FR-1.8: Migrating :SchoolOfThought -> :ReligiousTradition...');

    // Ensure :ReligiousTradition nodes exist for the 4 canonical traditions.
    for (const trad of PSEUDO_SCHOOL_NAMES) {
        await runWrite(`
            MERGE (rt:ReligiousTradition { name: $name })
            ON CREATE SET
                rt.id = randomUUID(),
                rt.created_at = datetime()
        `, { name: trad });
    }

    // For every node with an [:IN_SCHOOL] edge, write an equivalent
    // [:FROM_TRADITION] edge to the matching :ReligiousTradition.
    //
    // Cypher: match the [:IN_SCHOOL] source and the SchoolOfThought.name,
    // then MERGE [:FROM_TRADITION] to the :ReligiousTradition of the same name.
    await runWrite(`
        MATCH (src)-[:IN_SCHOOL]->(school:SchoolOfThought)
        WHERE school.name IN $traditions
        MATCH (rt:ReligiousTradition { name: school.name })
        MERGE (src)-[r:FROM_TRADITION]->(rt)
        ON CREATE SET
            r.source = $dvId,
            r.migrated_from = 'IN_SCHOOL',
            r.created_at = datetime()
    `, { traditions: [...PSEUDO_SCHOOL_NAMES], dvId });

    // Tombstone the 4 pseudo-school nodes (soft-delete by name biz key).
    for (const name of PSEUDO_SCHOOL_NAMES) {
        try {
            await tombstoneByKey('SchoolOfThought', 'name', name, dvId);
        } catch {
            // Node may not exist in a fresh DB — that is fine.
        }
    }

    console.log('[fullregen] FR-1.8: SchoolOfThought migration complete.');
}

// ─── Traditions tracked for per-row assessment ───────────────────────────────

type Tradition = 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';
const ALL_TRADITIONS: Tradition[] = ['Sunni', 'Imami', 'Zaydi', 'Ibadi'];

// ─── Build canonical source set for unregistered-source warning ───────────────

const CANONICAL_SOURCE_NAMES = new Set(
    Object.values(CANONICAL_SOURCES).map((e) => e.canonical)
);

// ─── GIGO confidence report (G-2) ────────────────────────────────────────────

async function printGigoReport(): Promise<void> {
    console.log('\n[fullregen] G-2 GIGO Report — Edge confidence strata:');
    try {
        const rows = await runQuery<{
            rel_type: string;
            count: number;
            min_conf: number;
            max_conf: number;
            avg_conf: number;
        }>(`
            MATCH ()-[r]->()
            WHERE r.confidence IS NOT NULL
            RETURN type(r) AS rel_type,
                   count(r) AS count,
                   min(r.confidence) AS min_conf,
                   max(r.confidence) AS max_conf,
                   avg(r.confidence) AS avg_conf
            ORDER BY count DESC
        `);
        if (rows.length === 0) {
            console.log('  (no edges with confidence found)');
        }
        for (const r of rows) {
            console.log(
                `  ${r.rel_type.padEnd(20)} count=${r.count} ` +
                `min=${r.min_conf?.toFixed(3) ?? 'n/a'} ` +
                `max=${r.max_conf?.toFixed(3) ?? 'n/a'} ` +
                `avg=${r.avg_conf?.toFixed(3) ?? 'n/a'}`
            );
        }
        console.log('  NOTE (G-2 / G-4): every edge MUST carry confidence + extraction_method.');
    } catch (err) {
        console.warn('[fullregen] G-2 GIGO report query failed:', err);
    }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export async function runModeFullregen(args: CliArgs): Promise<void> {
    console.log('='.repeat(64));
    console.log('  Isnad/Narrator Graph — Full Regen');
    console.log('='.repeat(64));

    // 1. Schema init (IF NOT EXISTS — safe to re-run).
    console.log('\n[fullregen] Initializing Neo4j schema...');
    await initializeSchema();

    // 2. G-1 remediation: migrate legacy scalar assessments FIRST.
    console.log('\n[fullregen] G-1: Migrating legacy scalar assessments...');
    const migReport = await migrateScalarAssessments();
    console.log(
        `[fullregen] G-1 migration: narrators=${migReport.narrators_migrated} hadiths=${migReport.hadiths_migrated} ` +
        `scalars_nulled=${migReport.scalars_nulled} errors=${migReport.errors.length}`
    );
    if (migReport.errors.length > 0) {
        console.warn('[fullregen] G-1 migration errors:', migReport.errors.slice(0, 5));
    }

    // 3. Resolve dataset paths and compute content hash.
    const { hadithPath, rawiPath } = resolveDatasetPaths();
    console.log(`\n[fullregen] Hadith CSV: ${hadithPath}`);
    console.log(`[fullregen] Rawis CSV:  ${rawiPath}`);

    const unifiedHash = sha256File(hadithPath);
    const rawisHash = sha256File(rawiPath);
    const contentHash = crypto
        .createHash('sha256')
        .update(`unified:${unifiedHash}\nrawis:${rawisHash}`)
        .digest('hex');
    console.log(`[fullregen] content_hash: ${contentHash}`);

    // 4. Load all_rawis.csv ONCE — cache Map for entire run (D handoff note 1).
    console.log('\n[fullregen] Loading all_rawis.csv...');
    const rawis: Map<number, RawiRecord> = await readAllRawis(rawiPath);
    console.log(`[fullregen] Loaded ${rawis.size} rawis.`);

    // 5. Pre-scan: count per-tradition records, unknown fraction, per-source
    //    counts, and unregistered source names for startup warnings (FR-0.3,
    //    FR-0.5, task 8). Definition of "truly unknown" row: grade_tradition,
    //    gradings_full, AND grade_value are all empty (spec FR-0.3 / task 0.10).
    console.log('\n[fullregen] Pre-scan: counting per-tradition records...');
    const perTraditionCounts: Record<string, number> = { Sunni: 0, Imami: 0, Ibadi: 0, Zaydi: 0 };
    const perSourceCounts = new Map<string, number>();
    let totalRecords = 0;
    let unknownRows = 0;
    const csvSourceNames = new Set<string>();

    for await (const row of readUnifiedCsv(hadithPath)) {
        totalRecords++;
        const trad = row.tradition;
        if (trad in perTraditionCounts) {
            perTraditionCounts[trad]++;
        }
        // FR-0.3: truly unknown = no grade_tradition AND no gradings_full AND no grade_value
        const hasGrading =
            (row.grade_tradition && (row.grade_tradition as string).trim()) ||
            (row.gradings_full && (row.gradings_full as string).trim()) ||
            (row.grade_value && (row.grade_value as string).trim());
        if (!hasGrading) unknownRows++;

        // FR-0.5: per-source counts
        const src = (row.source as string | undefined ?? '').trim();
        if (src) {
            perSourceCounts.set(src, (perSourceCounts.get(src) ?? 0) + 1);
            csvSourceNames.add(src);
        }
    }

    const measuredUnknownFraction = totalRecords > 0 ? unknownRows / totalRecords : 0;
    console.log(
        `[fullregen] Records: ${totalRecords} | ` +
        `Sunni=${perTraditionCounts.Sunni} Imami=${perTraditionCounts.Imami} ` +
        `Ibadi=${perTraditionCounts.Ibadi} Zaydi=${perTraditionCounts.Zaydi}`
    );
    console.log(`[fullregen] Truly unknown rows (no grading info): ${unknownRows} ` +
        `(fraction=${measuredUnknownFraction.toFixed(4)})`);

    // Task 8: Unregistered-source warning at startup.
    const unregisteredSources = [...csvSourceNames].filter(
        (s) => !CANONICAL_SOURCE_NAMES.has(s)
    );
    if (unregisteredSources.length > 0) {
        console.warn(
            `[fullregen] WARNING: Unregistered source(s) in unified CSV ` +
            `(will default to Sunni tradition): ${unregisteredSources.join(', ')}`
        );
    }

    // 6. Merge :DatasetVersion provenance node.
    const { id: dvId } = await mergeDatasetVersion({
        expectedRecordCount: 99283,
        perTraditionCounts,
        contentHash,
        measuredUnknownFraction,
        versionLabel: `unified-${contentHash.slice(0, 16)}`,
    });
    console.log(`\n[fullregen] DatasetVersion id: ${dvId}`);

    // 7. Deactivate other versions (not this one).
    await deactivateOtherVersions(dvId);
    console.log('[fullregen] Prior DatasetVersion nodes marked active=false.');

    // 8. FR-1.8: SchoolOfThought → ReligiousTradition migration.
    await migrateSchoolOfThought(dvId);

    // 9. Task 1: Bulk-merge :Narrator nodes from rawis ONCE before streaming loop.
    console.log('\n[fullregen] Bulk-merging :Narrator nodes from rawis...');
    const narratorResult = await bulkLoadNarrators(rawis, dvId);
    console.log(
        `[fullregen] Narrators: created=${narratorResult.created} ` +
        `matched=${narratorResult.matched} errors=${narratorResult.errors}`
    );

    // 10. Create JSONL logger.
    const logger = createRegenLogger('fullregen', dvId);
    const ctx: LoadContext = {
        dvId,
        mode: 'fullregen',
        log: logger.write.bind(logger),
    };

    // 11. Main streaming load loop (UNWIND-batched — see batch-loaders.ts).
    //
    // We buffer K rows of (UnifiedRow, NarratorResolutionResult[]) pairs, then
    // flush each buffer in 7-10 UNWIND transactions covering:
    //   loadHadithsBatch        →  3 tx  (sources, hadiths, edges)
    //   loadChainsBatch         →  4 tx  (chains, HAS_CHAIN, INCLUDES, NARRATED_FROM)
    //   loadAssessmentsBatch    →  2 tx  (real grades, no_extant placeholders)
    //   loadNameMentionsBatch   →  0-1 tx (skipped if no mentions in buffer)
    //
    // Replaces the prior per-row dispatch (~27 tx/row × Railway proxy 215ms RTT
    // = ~5-6 days for 99,283 rows). With K=100 the same workload is ~1000
    // buffers × ~10 tx = ~10,000 transactions total, ~30-60 min wall-clock.
    //
    // Idempotent against partial DBs: every MERGE is on the stable business key
    // (dataset_row_id for Hadith; pipeline_key for Chain/Assessment/NameMention;
    // scholar_indx for Narrator). Re-running over a partially-loaded DB is safe.
    //
    // Note: load-hadith.ts's `tombstoneOrphanPipelineKey` is intentionally NOT
    // ported here. That guard handled rows where a prior run merged on
    // pipeline_key (no dataset_row_id) but the current run has a dataset_row_id.
    // The unified CSV has 100% dataset_row_id coverage (validated 2026-05-22),
    // so the guard is a no-op for this dataset.
    console.log('\n[fullregen] Streaming unified CSV (batched, K=100)...');
    const BUFFER_SIZE = 100;
    const sourceCache = new Set<string>();
    let buffer: BufferedRow[] = [];
    let rowNum = 0;
    let chainLoaded = 0;
    let assessmentLoaded = 0;
    let noExtantLoaded = 0;
    let mentionLoaded = 0;
    let errors = 0;

    // Retry-with-split: if a batch flush hits the runWrite 30s per-tx timeout
    // (or any transient error), halve the slice and retry each half. Recurses
    // down to single rows. At depth 0 a slice of 100 can recurse to depth 7
    // before reaching a single row.
    //
    // Transient/timeout detection: Neo4j driver throws Neo4jError with
    // "transaction has been terminated" + "timeout" message for the
    // runWrite-imposed 30s per-tx cap. We also retry on TransientError code.
    const isTransientError = (err: unknown): boolean => {
        const msg = String(err);
        if (msg.includes('transaction has been terminated') && msg.includes('timeout')) return true;
        if (msg.includes('Neo.TransientError')) return true;
        if (msg.includes('SessionExpired')) return true;
        if (msg.includes('ServiceUnavailable')) return true;
        return false;
    };

    const flushSlice = async (slice: BufferedRow[], depth: number): Promise<void> => {
        if (slice.length === 0) return;
        try {
            await loadHadithsBatch(slice, ctx, sourceCache);
            const chainRes = await loadChainsBatch(slice, ctx);
            for (const ids of chainRes.chainIdsByRow.values()) chainLoaded += ids.length;
            const asmtRes = await loadAssessmentsBatch(slice, ctx);
            assessmentLoaded += asmtRes.real;
            noExtantLoaded += asmtRes.noExtant;
            mentionLoaded += await loadNameMentionsBatch(slice, chainRes.chainIdsByRow, ctx);
        } catch (err) {
            if (isTransientError(err) && slice.length > 1 && depth < 8) {
                console.warn(
                    `[fullregen] Transient flush failure at depth=${depth} size=${slice.length} — splitting`,
                );
                const mid = Math.floor(slice.length / 2);
                await flushSlice(slice.slice(0, mid), depth + 1);
                await flushSlice(slice.slice(mid), depth + 1);
            } else {
                errors += slice.length;
                for (const it of slice) {
                    logger.write({
                        action: 'error',
                        dataset_row_id: it.hadithKey,
                        depth,
                        size: slice.length,
                        error: String(err),
                    });
                }
                console.error(
                    `[fullregen] Permanent failure on ${slice.length} rows (depth=${depth}):`,
                    err,
                );
            }
        }
    };

    const flushBuffer = async (): Promise<void> => {
        if (buffer.length === 0) return;
        const slice = buffer;
        buffer = [];
        await flushSlice(slice, 0);
    };

    for await (const row of readUnifiedCsv(hadithPath)) {
        rowNum++;
        // Per-row CPU work: entity resolution. No DB calls.
        let resolutions: NarratorResolutionResult[];
        if (row.chain_indx.length > 0) {
            // Tier-1: deterministic join from chain_indx.
            resolutions = buildTier1Resolution(row);
        } else {
            // Tier-2/3: sanad text entity resolution via workstream D.
            const erRow = {
                dataset_row_id: row.dataset_row_id ?? undefined,
                source: row.source,
                hadith_no: row.hadith_no,
                tradition: row.tradition,
                text_ar: row.text_ar,
                sanad: row.sanad,
                chain_indx: '',
            };
            try {
                const erResult = await resolveNarrators(
                    erRow,
                    rawis as unknown as Map<number, import('./entity-resolution').RawiRecord>,
                );
                resolutions = [adaptErResult(erResult, 0)];
            } catch (err) {
                errors++;
                logger.write({ action: 'er_error', row: rowNum, error: String(err) });
                console.error(`[fullregen] ER error on row ${rowNum}:`, err);
                continue;
            }
        }

        try {
            buffer.push(buildBufferedRow(row, resolutions));
        } catch (err) {
            errors++;
            logger.write({ action: 'buffer_error', row: rowNum, error: String(err) });
            console.error(`[fullregen] Buffer error on row ${rowNum}:`, err);
            continue;
        }

        if (buffer.length >= BUFFER_SIZE) {
            await flushBuffer();
            if (rowNum % 1000 === 0 || rowNum === BUFFER_SIZE) {
                console.log(
                    `[fullregen] Progress: ${rowNum} rows | chains=${chainLoaded} ` +
                    `assessments=${assessmentLoaded} noExtant=${noExtantLoaded} ` +
                    `mentions=${mentionLoaded} errors=${errors}`,
                );
            }
        }
    }

    // Final flush for the tail (<BUFFER_SIZE rows).
    await flushBuffer();
    console.log(
        `[fullregen] Progress: ${rowNum} rows | chains=${chainLoaded} ` +
        `assessments=${assessmentLoaded} noExtant=${noExtantLoaded} ` +
        `mentions=${mentionLoaded} errors=${errors}  (final)`,
    );

    // 12. G-6: Flag all [:NARRATED_FROM] transmission edges with temporal plausibility.
    console.log('\n[fullregen] G-6: Flagging transmission edges with temporal plausibility...');
    const temporalReport = await flagAllTransmissionEdges(rawis, dvId);
    console.log(
        `[fullregen] G-6: total=${temporalReport.total_edges_assessed} ` +
        `plausible=${temporalReport.plausible} impossible=${temporalReport.impossible} ` +
        `unknown=${temporalReport.unknown} errors=${temporalReport.errors.length}`
    );

    // 13. Task 7: G-2 GIGO report — edge confidence strata.
    await printGigoReport();

    logger.close();

    // 14. Summary.
    console.log('\n' + '='.repeat(64));
    console.log('  Full Regen Complete');
    console.log('='.repeat(64));
    console.log(`  DatasetVersion id:   ${dvId}`);
    console.log(`  content_hash:        ${contentHash}`);
    console.log(`  Rows processed:      ${rowNum}`);
    console.log(`  Chains loaded:       ${chainLoaded}`);
    console.log(`  Assessments:         ${assessmentLoaded}`);
    console.log(`  No-extant markers:   ${noExtantLoaded}`);
    console.log(`  Name mentions:       ${mentionLoaded}`);
    console.log(`  Errors:              ${errors}`);
    console.log(`  Temporal flagged:    ${temporalReport.total_edges_assessed}`);
    console.log('');

    // Task 6: FR-0.5 per-source counts.
    console.log('[fullregen] Per-source counts:');
    const sortedSources = [...perSourceCounts.entries()].sort((a, b) => b[1] - a[1]);
    for (const [src, count] of sortedSources) {
        console.log(`  ${src}: ${count}`);
    }
    console.log('');

    // Task 5: G-3 disclaimer (spec §5 G-3) — must appear in run report.
    // Guardrail grep matches the literal substring "DISCLAIMER (spec §5 G-3)".
    console.log(
        '[fullregen] ⚠️  DISCLAIMER (spec §5 G-3): Per-narrator and per-hadith reliability ' +
        'scores in this dataset reflect "kathrat al-riwāya" (frequency of transmission) ' +
        '— NOT classical ʿadāla/ḍabṭ (justice/precision) verdicts. They are NOT ' +
        'authoritative authenticity rulings and must not be presented as such.'
    );

    if (errors > 0) {
        console.warn(`[fullregen] WARNING: ${errors} rows had errors. Check logs/regen-fullregen-${dvId}.jsonl`);
        process.exitCode = 1;
    }
}
