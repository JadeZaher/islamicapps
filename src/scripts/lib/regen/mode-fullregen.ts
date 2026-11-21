/**
 * mode-fullregen.ts — Full idempotent isnad graph regeneration.
 * ==============================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream E
 *
 * Entry point: runModeFullregen(args)
 *
 * Processing order:
 *   1. Resolve/hash/stream-preflight every input before DB mutation.
 *   2. Initialize schema and migrate legacy scalar assessments.
 *   3. Load all_rawis.csv once and sparse-merge Narrator identity metadata.
 *   4. Merge DatasetVersion and tradition/source scaffolding.
 *   5. Stream configured batches through idempotent Hadith/Chain/Assessment loads.
 *   6. Flag transmission edges for temporal plausibility.
 *
 * Invariants:
 *   - NEVER DETACH DELETE; use tombstoneByKey for soft deletes.
 *   - No scalar reliability/grade on :Narrator or :Hadith (G-1).
 *   - Parameterized Cypher only (no string interpolation of user data).
 *   - Tradition canonicalization via canonicalizeTradition() from io.ts.
 *
 * FR-0.11 / INGESTED_IN backfill note: this sweep links every loaded :Hadith
 * through the batched INGESTED_IN phase. Legacy hadiths
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
import os from 'os';
import crypto from 'crypto';
import fs from 'fs';
import { runWrite, runQuery } from '../../../lib/db/neo4j';
import { initializeSchema } from '../../../lib/db/schema';
import {
    readUnifiedCsv,
    readAllRawis,
    createRegenLogger,
    datasetInputExists,
    isSupportedTradition,
    sha256File,
    type RawiRecord,
    type LoadContext,
    type Tradition,
    type UnifiedRow,
} from './io';
import {
    activateDatasetVersion,
    FULLREGEN_LEASE_NAME,
    markDatasetVersionNonReleaseLoaded,
    mergeDatasetVersion,
    withFullregenLease,
} from './dataset-version';
import {
    buildTier1Resolution,
    type NarratorResolutionResult,
    type ResolvedNarrator,
    type NameMentionDraft,
} from './load-chain';
import { migrateScalarAssessments } from './assessment';
import { bulkLoadNarrators } from './load-narrators';
import { tombstoneByKey } from './tombstone';
import {
    buildBufferedRow,
    loadHadithsBatch,
    loadChainsBatch,
    loadAssessmentsBatch,
    loadNameMentionsBatch,
    type BufferedRow,
} from './batch-loaders';
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
        if (datasetInputExists(hadithPath) && datasetInputExists(rawiPath)) {
            return { hadithPath, rawiPath };
        }
    }
    throw new Error(
        'Could not locate datasets/hadith-data/all_hadiths_unified.csv ' +
        'and datasets/narrator-data/all_rawis.csv. Run from repo root.'
    );
}

// ─── Adapter: resolveNarrators → NarratorResolutionResult ────────────────────
//
// entity-resolution.ts (Workstream D) uses ResolvedNarrator.extraction_method.
// load-chain.ts (Workstream C) uses ResolvedNarrator.method.
// The shape is otherwise identical. We adapt here in mode-fullregen, keeping
// both read-only modules untouched.
//
// FR-2.2 (Phase 3, uniform_isnad_extraction_20260609): resolveNarrators now
// returns one result per isnad branch (taḥwīl-aware). We map each branch
// directly — the upstream `chain_index` is preserved.

function adaptErResult(
    erResult: { resolved: ErResolvedNarrator[]; mentions: ErNameMentionDraft[]; method: ErTier; chain_index: number },
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
        chain_index: erResult.chain_index,
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

// ─── Build canonical source set for unregistered-source warning ───────────────

const CANONICAL_SOURCE_TRADITIONS = new Map(
    Object.values(CANONICAL_SOURCES).map((entry) => [entry.canonical, entry.tradition] as const),
);

const MAX_BUFFER_PAYLOAD_BYTES = 16 * 1024 * 1024;

function estimateRowPayloadBytes(row: UnifiedRow): number {
    let bytes = 0;
    for (const value of Object.values(row._raw)) bytes += Buffer.byteLength(value, 'utf8');
    for (const branch of row.chain_indx) bytes += branch.length * 16;
    return bytes;
}

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

async function verifyLoadedSnapshot(
    dvId: string,
    expectedHadiths: number,
    expectedChains: number,
    expectedNarrators: number,
): Promise<void> {
    const [hadithRows, chainRows, narratorRows] = await Promise.all([
        runQuery<{ count: number }>(`
            MATCH (:DatasetVersion { id: $dvId })<-[:INGESTED_IN]-(h:Hadith)
            RETURN count(DISTINCT h) AS count
        `, { dvId }),
        runQuery<{ count: number }>(`
            MATCH (:DatasetVersion { id: $dvId })<-[:INGESTED_IN]-(h:Hadith)
                  -[:HAS_CHAIN]->(ch:Chain { source: $dvId })
            RETURN count(DISTINCT ch) AS count
        `, { dvId }),
        runQuery<{ count: number }>(`
            MATCH (n:Narrator { source: $dvId })
            RETURN count(DISTINCT n) AS count
        `, { dvId }),
    ]);
    const actual = {
        hadiths: hadithRows[0]?.count ?? 0,
        chains: chainRows[0]?.count ?? 0,
        narrators: narratorRows[0]?.count ?? 0,
    };
    if (
        actual.hadiths !== expectedHadiths ||
        actual.chains !== expectedChains ||
        actual.narrators !== expectedNarrators
    ) {
        throw new Error(
            `[fullregen] Snapshot count verification failed: ` +
            `hadiths=${actual.hadiths}/${expectedHadiths}, ` +
            `chains=${actual.chains}/${expectedChains}, ` +
            `narrators=${actual.narrators}/${expectedNarrators}`,
        );
    }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export interface FullregenPreflightReport {
    totalRecords: number;
    unknownRows: number;
    perTraditionCounts: Record<string, number>;
    perSourceCounts: Map<string, number>;
    csvSourceNames: Set<string>;
    legacyRecordIdsDerived: number;
    missingSourceRecordIds: number;
    missingProvenanceSources: number;
    missingArabic: number;
    missingEnglish: number;
    nonCompleteTranslations: number;
    invalidTranslationStatuses: number;
    missingTranslationSources: number;
    missingTranslationReviewStatuses: number;
    nonReleaseTranslationReviewStatuses: number;
    missingRequiredTranslationModels: number;
    missingNarratorReferences: number;
    missingNarratorIds: number[];
    emptyChainRows: number;
    invalidTraditions: number;
    invalidGradeTraditions: number;
    missingSources: number;
    sourceTraditionConflicts: number;
    sourceRegistryMismatches: number;
    sourceTraditions: Map<string, Tradition>;
    unregisteredSourceRows: number;
    unregisteredSources: string[];
    missingImamiSourceWorkIds: number;
    invalidImamiSourceWorkIds: number;
    oversizedRows: number;
}

export const TRANSLATION_STATUS_VALUES = [
    'complete',
    'missing',
    'model_refusal_or_error',
    'same_as_arabic',
    'copied_input',
    'arabic_leakage',
    'wrong_language',
    'no_english_text',
    'placeholder',
    'suspiciously_short',
] as const;

const TRANSLATION_STATUS_SET = new Set<string>(TRANSLATION_STATUS_VALUES);
export const TRANSLATION_RELEASE_REVIEW_STATUSES = ['human_verified', 'source_verified'] as const;
const TRANSLATION_RELEASE_REVIEW_STATUS_SET =
    new Set<string>(TRANSLATION_RELEASE_REVIEW_STATUSES);
const LATIN_TEXT = /[A-Za-z]/;
const ARABIC_TEXT = /[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]/;
const TRANSLATION_FAILURE = /^\s*(?:translation\s+(?:failed|unavailable|missing)|unable\s+to\s+translate|i\s+(?:cannot|can't|am unable\s+to)\s+translate|i(?:'m| am)\s+sorry|as\s+an\s+ai\b|sorry[, :]\s*i\s+(?:cannot|can't))/i;
const MODEL_PROVENANCE_MARKER =
    /(?:^|[^a-z0-9])(?:ai|automated|generated|gpt|llm|machine|model|openai|anthropic|claude|gemma|pipeline)(?=$|[^a-z0-9])/i;
const PLACEHOLDER_METADATA_TOKENS = new Set([
    '', '<missing>', '-', '?', 'n/a', 'na', 'none', 'null', 'pending', 'tba', 'tbd',
    'unknown', 'unspecified',
]);
const SPECIFIC_MODEL_IDENTIFIER =
    /^[a-z0-9][a-z0-9._-]*(?:[/:][a-z0-9][a-z0-9._-]*)+$/i;
const GENERIC_MODEL_COMPONENTS = new Set(['ai', 'default', 'generic', 'model', 'x']);

function normalizedMetadataToken(value: string): string {
    return value.trim().toLowerCase().replace(/\s+/g, '');
}

function isPlaceholderMetadata(value: string): boolean {
    return PLACEHOLDER_METADATA_TOKENS.has(normalizedMetadataToken(value));
}

/** Source-owned IDs may be short, but must contain identity text and not placeholders. */
export function isMeaningfulSourceRecordId(value: string): boolean {
    return !isPlaceholderMetadata(value) && /[\p{L}\p{N}]/u.test(value);
}

/** Provenance locators must contain at least two letters/digits and not placeholders. */
export function isMeaningfulProvenanceLocator(value: string): boolean {
    if (isPlaceholderMetadata(value)) return false;
    return (value.match(/[\p{L}\p{N}]/gu)?.length ?? 0) >= 2;
}

/** Require a namespaced vendor/method identifier, such as vendor/model or method:model. */
export function isSpecificTranslationModelIdentifier(value: string): boolean {
    const identifier = value.trim();
    if (isPlaceholderMetadata(identifier) || !SPECIFIC_MODEL_IDENTIFIER.test(identifier)) {
        return false;
    }
    const terminalComponent = identifier.split(/[/:]/).at(-1)?.toLowerCase() ?? '';
    return terminalComponent.length >= 3 && !GENERIC_MODEL_COMPONENTS.has(terminalComponent);
}

/** Machine/model semantics in either provenance field require an exact model identifier. */
export function translationModelRequired(
    row: Pick<UnifiedRow, 'translation_source' | 'translation_review_status'>,
): boolean {
    return MODEL_PROVENANCE_MARKER.test(row.translation_source) ||
        MODEL_PROVENANCE_MARKER.test(row.translation_review_status);
}

function normalizedSourceText(value: string): string {
    return value.normalize('NFKC').replace(/[^\p{L}\p{N}_]+/gu, '').toLowerCase();
}

function hasLatinMajority(value: string): boolean {
    const letters = [...value].filter((character) => /\p{L}/u.test(character));
    if (letters.length === 0) return false;
    const latin = letters.filter((character) => /\p{Script=Latin}/u.test(character)).length;
    return latin / letters.length >= 0.8;
}

export function translationContentIssue(row: Pick<UnifiedRow, 'text_en' | 'text_ar'>): string {
    const english = row.text_en.trim();
    const arabic = row.text_ar.trim();
    if (!english) return 'missing';
    if (TRANSLATION_FAILURE.test(english)) return 'model_refusal_or_error';
    if (/(?:^|[^A-Za-z])(?:TODO|PLACEHOLDER)(?=$|[^A-Za-z])/i.test(english)) return 'placeholder';
    if (/^(?:H\d+|(?:\d+[.)]?\s*)?TBA|N\/?A|NONE|TODO|PLACEHOLDER)$/i.test(english)) {
        return 'placeholder';
    }
    if (english === arabic || normalizedSourceText(english) === normalizedSourceText(arabic)) {
        return 'copied_input';
    }
    if (ARABIC_TEXT.test(english)) return 'arabic_leakage';
    if (!LATIN_TEXT.test(english)) return 'no_english_text';
    if (!hasLatinMajority(english)) return 'wrong_language';
    if (english.length < 8 && arabic.length > 80) return 'suspiciously_short';
    return '';
}

function deriveLegacyRecordId(row: UnifiedRow): string {
    const seed = [
        row.tradition,
        row.source,
        row.source_record_id || row.hadith_id,
        row.text_ar,
    ].join('|');
    return `legacy:${crypto.createHash('sha256').update(seed).digest('hex').slice(0, 24)}`;
}

function effectiveTranslationStatus(row: UnifiedRow, allowLegacyDerivation: boolean): string {
    if (row.translation_status) {
        if (row.translation_status === 'complete') return translationContentIssue(row) || 'complete';
        return row.translation_status;
    }
    if (
        Object.prototype.hasOwnProperty.call(row._raw, 'translation_status') &&
        !allowLegacyDerivation
    ) return '';
    if (allowLegacyDerivation) return translationContentIssue(row) || 'complete';
    return '';
}

export function prepareUnifiedRowForLoad(
    row: UnifiedRow,
    devAllowIncompleteData: boolean,
): UnifiedRow {
    if (!row.record_id) {
        if (!devAllowIncompleteData) {
            throw new Error('[fullregen] record_id missing after successful curation preflight');
        }
        row.record_id = deriveLegacyRecordId(row);
        row.source_record_id ||= row.hadith_id || String(row.dataset_row_id ?? '');
        row.provenance_source ||= 'legacy-schema-dev-bootstrap';
        row.translation_review_status ||= 'legacy_unreviewed';
    }
    if (devAllowIncompleteData) row.translation_status = effectiveTranslationStatus(row, true);
    return row;
}

export interface RawiDatePreflightReport {
    reversedHijriLifespans: number;
    reversedGregorianLifespans: number;
    inconsistentBirthCalendarPairs: number;
    inconsistentDeathCalendarPairs: number;
}

const CALENDAR_PAIR_TOLERANCE_YEARS = 3;

function isConsistentHijriGregorianPair(hijri: number | null, gregorian: number | null): boolean {
    if (hijri === null || gregorian === null) return true;
    const approximateGregorian = 621.5774 + (0.970224 * hijri);
    return Math.abs(gregorian - approximateGregorian) <= CALENDAR_PAIR_TOLERANCE_YEARS;
}

/** Reject contradictory canonical lifetime values before schema or narrator writes. */
export function preflightRawiDataset(
    rawis: ReadonlyMap<number, RawiRecord>,
): RawiDatePreflightReport {
    const report: RawiDatePreflightReport = {
        reversedHijriLifespans: 0,
        reversedGregorianLifespans: 0,
        inconsistentBirthCalendarPairs: 0,
        inconsistentDeathCalendarPairs: 0,
    };
    const examples: string[] = [];
    const note = (rawi: RawiRecord, issue: string): void => {
        if (examples.length < 10) examples.push(`scholar_indx=${rawi.scholar_indx} ${issue}`);
    };

    for (const rawi of rawis.values()) {
        if (
            rawi.birth_date_hijri !== null && rawi.death_date_hijri !== null &&
            rawi.death_date_hijri < rawi.birth_date_hijri
        ) {
            report.reversedHijriLifespans++;
            note(rawi, `death AH ${rawi.death_date_hijri} precedes birth AH ${rawi.birth_date_hijri}`);
        }
        if (
            rawi.birth_date_gregorian !== null && rawi.death_date_gregorian !== null &&
            rawi.death_date_gregorian < rawi.birth_date_gregorian
        ) {
            report.reversedGregorianLifespans++;
            note(rawi, `death CE ${rawi.death_date_gregorian} precedes birth CE ${rawi.birth_date_gregorian}`);
        }
        if (!isConsistentHijriGregorianPair(
            rawi.birth_date_hijri,
            rawi.birth_date_gregorian,
        )) {
            report.inconsistentBirthCalendarPairs++;
            note(rawi, 'birth AH/CE pair is inconsistent');
        }
        if (!isConsistentHijriGregorianPair(
            rawi.death_date_hijri,
            rawi.death_date_gregorian,
        )) {
            report.inconsistentDeathCalendarPairs++;
            note(rawi, 'death AH/CE pair is inconsistent');
        }
    }

    const issueCount = report.reversedHijriLifespans + report.reversedGregorianLifespans +
        report.inconsistentBirthCalendarPairs + report.inconsistentDeathCalendarPairs;
    if (issueCount > 0) {
        throw new Error(
            `[fullregen] Narrator date preflight failed before DB mutation: ` +
            `death_before_birth_hijri=${report.reversedHijriLifespans}, ` +
            `death_before_birth_gregorian=${report.reversedGregorianLifespans}, ` +
            `inconsistent_birth_calendar_pairs=${report.inconsistentBirthCalendarPairs}, ` +
            `inconsistent_death_calendar_pairs=${report.inconsistentDeathCalendarPairs}.\n  ` +
            examples.join('\n  '),
        );
    }
    return report;
}

export async function preflightUnifiedDataset(
    filePath: string,
    devAllowIncompleteData: boolean,
    rawis?: ReadonlyMap<number, RawiRecord>,
): Promise<FullregenPreflightReport> {
    const perTraditionCounts: Record<string, number> = { Sunni: 0, Imami: 0, Ibadi: 0, Zaydi: 0 };
    const perSourceCounts = new Map<string, number>();
    const csvSourceNames = new Set<string>();
    const recordIds = new Set<string>();
    const examples: string[] = [];
    let totalRecords = 0;
    let unknownRows = 0;
    let legacyRecordIdsDerived = 0;
    let missingRecordIds = 0;
    let duplicateRecordIds = 0;
    let missingSourceRecordIds = 0;
    let missingProvenanceSources = 0;
    let missingArabic = 0;
    let missingEnglish = 0;
    let nonCompleteTranslations = 0;
    let invalidTranslationStatuses = 0;
    let missingTranslationSources = 0;
    let missingTranslationReviewStatuses = 0;
    let nonReleaseTranslationReviewStatuses = 0;
    let missingRequiredTranslationModels = 0;
    let missingNarratorReferences = 0;
    const missingNarratorIds = new Set<number>();
    let emptyChainRows = 0;
    let invalidTraditions = 0;
    let invalidGradeTraditions = 0;
    let missingSources = 0;
    let sourceTraditionConflicts = 0;
    let sourceRegistryMismatches = 0;
    const sourceTraditions = new Map<string, Tradition>();
    let unregisteredSourceRows = 0;
    const unregisteredSources = new Set<string>();
    let missingImamiSourceWorkIds = 0;
    let invalidImamiSourceWorkIds = 0;
    let oversizedRows = 0;

    const noteExample = (row: UnifiedRow, issue: string): void => {
        if (examples.length >= 12) return;
        examples.push(
            `${issue}: row=${row.dataset_row_id ?? totalRecords} source=${row.source} hadith=${row.hadith_no}`,
        );
    };

    for await (const row of readUnifiedCsv(filePath)) {
        totalRecords++;
        const rowPayloadBytes = estimateRowPayloadBytes(row);
        if (rowPayloadBytes > MAX_BUFFER_PAYLOAD_BYTES) {
            oversizedRows++;
            noteExample(
                row,
                `row payload ${rowPayloadBytes} exceeds ${MAX_BUFFER_PAYLOAD_BYTES} bytes`,
            );
        }
        const rawTradition = row._raw['tradition'] ?? '';
        if (!isSupportedTradition(rawTradition)) {
            invalidTraditions++;
            noteExample(row, `unsupported tradition=${rawTradition || '<blank>'}`);
        }
        if (row.tradition in perTraditionCounts) perTraditionCounts[row.tradition]++;

        const hasGrading = row.grade_tradition || row.gradings_full || row.grade_value;
        if (!hasGrading) unknownRows++;
        if (row.grade_tradition && !isSupportedTradition(row.grade_tradition)) {
            invalidGradeTraditions++;
            noteExample(row, `unsupported grade_tradition=${row.grade_tradition}`);
        }
        if (row.chain_indx.length === 0) {
            emptyChainRows++;
            noteExample(row, 'missing normalized chain_indx');
        }

        if (row.source) {
            perSourceCounts.set(row.source, (perSourceCounts.get(row.source) ?? 0) + 1);
            csvSourceNames.add(row.source);

            const observedTradition = sourceTraditions.get(row.source);
            if (observedTradition && observedTradition !== row.tradition) {
                sourceTraditionConflicts++;
                noteExample(
                    row,
                    `source ${row.source} appears as both ${observedTradition} and ${row.tradition}`,
                );
            } else {
                sourceTraditions.set(row.source, row.tradition);
            }

            const registeredTradition = CANONICAL_SOURCE_TRADITIONS.get(row.source);
            if (!registeredTradition) {
                unregisteredSourceRows++;
                unregisteredSources.add(row.source);
                noteExample(row, `unregistered source=${row.source}`);
            } else if (registeredTradition !== row.tradition) {
                sourceRegistryMismatches++;
                noteExample(
                    row,
                    `source registry mismatch ${row.source}: row=${row.tradition} registry=${registeredTradition}`,
                );
            }
            if (row.tradition === 'Imami') {
                if (!row.source_work_id) {
                    missingImamiSourceWorkIds++;
                    noteExample(row, 'missing Imami source_work_id');
                } else if (!/^imami:[a-z0-9][a-z0-9-]*$/.test(row.source_work_id)) {
                    invalidImamiSourceWorkIds++;
                    noteExample(
                        row,
                        `invalid Imami source_work_id=${row.source_work_id}`,
                    );
                }
            }
        } else {
            missingSources++;
            noteExample(row, 'missing source');
        }

        let recordId = row.record_id;
        if (!recordId) {
            missingRecordIds++;
            noteExample(row, 'missing record_id');
            if (devAllowIncompleteData) {
                recordId = deriveLegacyRecordId(row);
                legacyRecordIdsDerived++;
            }
        }
        if (recordId) {
            if (recordIds.has(recordId)) {
                duplicateRecordIds++;
                noteExample(row, `duplicate record_id ${recordId}`);
            } else {
                recordIds.add(recordId);
            }
        }

        if (!isMeaningfulSourceRecordId(row.source_record_id)) {
            missingSourceRecordIds++;
            noteExample(row, 'missing or placeholder source_record_id');
        }
        if (!isMeaningfulProvenanceLocator(row.provenance_source)) {
            missingProvenanceSources++;
            noteExample(row, 'missing or placeholder provenance_source');
        }

        if (!row.text_ar) {
            missingArabic++;
            noteExample(row, 'missing text_ar');
        }
        if (!row.text_en) {
            missingEnglish++;
            noteExample(row, 'missing text_en');
        }
        const translationStatus = effectiveTranslationStatus(row, devAllowIncompleteData);
        if (translationStatus && !TRANSLATION_STATUS_SET.has(translationStatus)) {
            invalidTranslationStatuses++;
            noteExample(row, `invalid translation_status=${translationStatus}`);
        }
        if (translationStatus !== 'complete') {
            nonCompleteTranslations++;
            noteExample(row, `translation_status=${translationStatus || '<blank>'}`);
        }
        if (!isMeaningfulProvenanceLocator(row.translation_source)) {
            missingTranslationSources++;
            noteExample(row, 'missing or placeholder translation_source');
        }
        if (!row.translation_review_status) {
            missingTranslationReviewStatuses++;
            noteExample(row, 'missing translation_review_status');
        } else if (!TRANSLATION_RELEASE_REVIEW_STATUS_SET.has(row.translation_review_status)) {
            nonReleaseTranslationReviewStatuses++;
            noteExample(row, `non-release translation_review_status=${row.translation_review_status}`);
        }
        if (
            translationModelRequired(row) &&
            !isSpecificTranslationModelIdentifier(row.translation_model)
        ) {
            missingRequiredTranslationModels++;
            noteExample(row, 'machine/model translation provenance missing translation_model');
        }

        if (rawis) {
            for (const branch of row.chain_indx) {
                for (const scholarIndx of branch) {
                    if (rawis.has(scholarIndx)) continue;
                    missingNarratorReferences++;
                    missingNarratorIds.add(scholarIndx);
                    noteExample(row, `unknown chain_indx=${scholarIndx}`);
                }
            }
        }
    }

    if (totalRecords === 0) {
        throw new Error('[fullregen] Dataset curation preflight failed: unified dataset is empty');
    }
    if (oversizedRows > 0) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `${oversizedRows} row(s) exceed the ${MAX_BUFFER_PAYLOAD_BYTES}-byte transaction payload bound.\n  ` +
            examples.join('\n  '),
        );
    }
    if (duplicateRecordIds > 0) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `${duplicateRecordIds} duplicate durable record_id value(s).\n  ${examples.join('\n  ')}`,
        );
    }

    if (invalidTranslationStatuses > 0) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `${invalidTranslationStatuses} translation_status value(s) are outside the supported vocabulary ` +
            `(${TRANSLATION_STATUS_VALUES.join(', ')}).\n  ${examples.join('\n  ')}`,
        );
    }
    if (invalidTraditions > 0) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `${invalidTraditions} row(s) have a blank or unsupported tradition.\n  ` +
            `${examples.join('\n  ')}`,
        );
    }
    if (invalidGradeTraditions > 0) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `${invalidGradeTraditions} row(s) have an unsupported grade_tradition.\n  ` +
            examples.join('\n  '),
        );
    }
    if (missingSources > 0 || sourceTraditionConflicts > 0 || sourceRegistryMismatches > 0) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `missing_source=${missingSources}, source_tradition_conflicts=${sourceTraditionConflicts}, ` +
            `source_registry_mismatches=${sourceRegistryMismatches}. ` +
            `Every source must have one validated tradition; an unregistered source uses that row tradition ` +
            `and is never defaulted to Sunni.\n  ${examples.join('\n  ')}`,
        );
    }
    if (unregisteredSourceRows > 0 && !devAllowIncompleteData) {
        const names = [...unregisteredSources].sort();
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `unregistered_source_rows=${unregisteredSourceRows}, ` +
            `unregistered_source_names=${names.length} (${names.join(', ')}). ` +
            `Register each distinct work/compiler identity before a curated release; ` +
            `--dev-allow-incomplete-data retains the validated row tradition without a Sunni fallback.\n  ` +
            examples.join('\n  '),
        );
    }
    if (
        (missingImamiSourceWorkIds > 0 || invalidImamiSourceWorkIds > 0) &&
        !devAllowIncompleteData
    ) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `missing_imami_source_work_id=${missingImamiSourceWorkIds}, ` +
            `invalid_imami_source_work_id=${invalidImamiSourceWorkIds}. ` +
            `Imami works must be reconciled from provider_book_id; a shared display label ` +
            `is not sufficient to attach compiler identity.\n  ${examples.join('\n  ')}`,
        );
    }

    const releaseBlockers = missingRecordIds + missingSourceRecordIds + missingProvenanceSources +
        missingArabic + missingEnglish + nonCompleteTranslations + missingTranslationSources +
        missingTranslationReviewStatuses + nonReleaseTranslationReviewStatuses +
        missingRequiredTranslationModels +
        missingNarratorReferences + emptyChainRows;
    if (releaseBlockers > 0 && !devAllowIncompleteData) {
        throw new Error(
            `[fullregen] Dataset curation preflight failed before DB mutation: ` +
            `missing_record_id=${missingRecordIds}, missing_source_record_id=${missingSourceRecordIds}, ` +
            `missing_provenance_source=${missingProvenanceSources}, missing_text_ar=${missingArabic}, ` +
            `missing_text_en=${missingEnglish}, translation_status_not_complete=${nonCompleteTranslations}, ` +
            `missing_translation_source=${missingTranslationSources}, ` +
            `missing_translation_review_status=${missingTranslationReviewStatuses}, ` +
            `nonrelease_translation_review_status=${nonReleaseTranslationReviewStatuses}, ` +
            `missing_required_translation_model=${missingRequiredTranslationModels}, ` +
            `unknown_chain_indx_references=${missingNarratorReferences}, ` +
            `missing_chain_indx=${emptyChainRows}. ` +
            `Curate the dataset or, for disposable development only, pass --dev-allow-incomplete-data.\n` +
            `  ${examples.join('\n  ')}`,
        );
    }

    return {
        totalRecords,
        unknownRows,
        perTraditionCounts,
        perSourceCounts,
        csvSourceNames,
        legacyRecordIdsDerived,
        missingSourceRecordIds,
        missingProvenanceSources,
        missingArabic,
        missingEnglish,
        nonCompleteTranslations,
        invalidTranslationStatuses,
        missingTranslationSources,
        missingTranslationReviewStatuses,
        nonReleaseTranslationReviewStatuses,
        missingRequiredTranslationModels,
        missingNarratorReferences,
        missingNarratorIds: [...missingNarratorIds].sort((a, b) => a - b),
        emptyChainRows,
        invalidTraditions,
        invalidGradeTraditions,
        missingSources,
        sourceTraditionConflicts,
        sourceRegistryMismatches,
        sourceTraditions,
        unregisteredSourceRows,
        unregisteredSources: [...unregisteredSources].sort(),
        missingImamiSourceWorkIds,
        invalidImamiSourceWorkIds,
        oversizedRows,
    };
}

export function validateFullregenBatchSize(batchSize: number): number {
    if (!Number.isSafeInteger(batchSize) || batchSize < 1) {
        throw new Error(`[fullregen] --batch-size must be a positive integer; received ${batchSize}`);
    }
    return batchSize;
}

export const RAILWAY_PRODUCTION_PROJECT_ID = '43973172-fd19-4c41-8097-369cf805cbe6';

export interface RailwayRuntimeIdentity {
    projectId?: string;
    environmentId?: string;
    serviceId?: string;
}

export const DISPOSABLE_NEO4J_TEST_TARGET_MARKER = 'DISPOSABLE_TEST_ONLY';
export const DISPOSABLE_NEO4J_TEST_ACK =
    'I_ACKNOWLEDGE_THIS_IS_A_DISPOSABLE_NEO4J_TEST_DATABASE';

/** Refuse the incomplete-data override outside one explicitly marked loopback test target. */
export function assertDevIncompleteFullregenTarget(
    devAllowIncompleteData: boolean,
    environment: Readonly<Record<string, string | undefined>> = process.env,
): void {
    if (!devAllowIncompleteData) return;
    const remoteRuntime = [
        'RAILWAY_PROJECT_ID', 'RAILWAY_ENVIRONMENT_ID', 'RAILWAY_SERVICE_ID',
        'VERCEL', 'K_SERVICE', 'FLY_APP_NAME', 'DYNO', 'RENDER_SERVICE_ID',
    ].some((name) => Boolean(environment[name]));
    if (environment.NODE_ENV === 'production' || remoteRuntime) {
        throw new Error(
            '[fullregen] --dev-allow-incomplete-data is forbidden in production or remote runtimes',
        );
    }

    const neo4jUrl = environment.NEO4J_URL?.trim() ?? '';
    const testUri = environment.NEO4J_TEST_URI?.trim() ?? '';
    let parsed: URL;
    try {
        parsed = new URL(testUri);
    } catch {
        throw new Error(
            '[fullregen] --dev-allow-incomplete-data requires a valid NEO4J_TEST_URI',
        );
    }
    const isLoopback = parsed.hostname === 'localhost' ||
        parsed.hostname === '127.0.0.1' || parsed.hostname === '[::1]' || parsed.hostname === '::1';
    if (!isLoopback || parsed.protocol !== 'bolt:') {
        throw new Error(
            '[fullregen] --dev-allow-incomplete-data requires a direct bolt:// loopback test URI',
        );
    }
    if (!neo4jUrl || neo4jUrl !== testUri) {
        throw new Error(
            '[fullregen] NEO4J_URL must exactly equal the acknowledged NEO4J_TEST_URI',
        );
    }
    if (
        !environment.NEO4J_TEST_USERNAME || !environment.NEO4J_TEST_PASSWORD ||
        environment.NEO4J_USERNAME !== environment.NEO4J_TEST_USERNAME ||
        environment.NEO4J_PASSWORD !== environment.NEO4J_TEST_PASSWORD
    ) {
        throw new Error(
            '[fullregen] Neo4j application credentials must exactly match the disposable test credentials',
        );
    }
    if (
        environment.RUN_LIVE_NEO4J_TESTS !== '1' ||
        environment.NEO4J_TEST_TARGET_MARKER !== DISPOSABLE_NEO4J_TEST_TARGET_MARKER ||
        environment.NEO4J_TEST_DISPOSABLE_ACK !== DISPOSABLE_NEO4J_TEST_ACK
    ) {
        throw new Error(
            '[fullregen] Disposable Neo4j marker and acknowledgement are required for the development override',
        );
    }
}

/** Require an exact project acknowledgement before any full load can wake Railway. */
export function assertRailwayProductionFullregenAcknowledgement(
    neo4jUrl: string | undefined,
    devAllowIncompleteData: boolean,
    acknowledgement = process.env.RAILWAY_FULLREGEN_PROJECT_ACK,
    runtimeIdentity: RailwayRuntimeIdentity = {
        projectId: process.env.RAILWAY_PROJECT_ID,
        environmentId: process.env.RAILWAY_ENVIRONMENT_ID,
        serviceId: process.env.RAILWAY_SERVICE_ID,
    },
): void {
    const railwayRuntime = Boolean(
        runtimeIdentity.projectId || runtimeIdentity.environmentId || runtimeIdentity.serviceId,
    );
    const railwayUrl = Boolean(neo4jUrl && /(?:railway|rlwy)/i.test(neo4jUrl));
    if (!railwayRuntime && !railwayUrl) return;
    if (devAllowIncompleteData) {
        throw new Error(
            '[fullregen] --dev-allow-incomplete-data is forbidden for every Railway target',
        );
    }
    if (railwayRuntime && runtimeIdentity.projectId !== RAILWAY_PRODUCTION_PROJECT_ID) {
        throw new Error(
            `[fullregen] Railway runtime project identity mismatch: actual=` +
            `${runtimeIdentity.projectId || '<missing>'}, expected=${RAILWAY_PRODUCTION_PROJECT_ID}. ` +
            `Refusing fullregen even when an acknowledgement is present.`,
        );
    }
    if (acknowledgement !== RAILWAY_PRODUCTION_PROJECT_ID) {
        const identityNote = railwayRuntime
            ? `Railway runtime project identity was verified. `
            : `This URL-only Railway proxy identity cannot be independently proven. `;
        throw new Error(
            `[fullregen] Railway release target requires explicit cost acknowledgement before connection: ` +
            `set RAILWAY_FULLREGEN_PROJECT_ACK=${RAILWAY_PRODUCTION_PROJECT_ID}. ` +
            identityNote +
            `The acknowledgement confirms the intended project and the compute/network cost of a full load.`,
        );
    }
    if (!railwayRuntime) {
        console.warn(
            `[fullregen] Railway proxy project identity cannot be independently proven from NEO4J_URL; ` +
            `continuing only because the exact project acknowledgement was supplied.`,
        );
    }
}

export interface ExistingGraphIdentityReport {
    totalHadiths: number;
    hadithsWithRecordId: number;
    hadithsMissingRecordId: number;
    duplicateRecordIdGroups: number;
    coreNodeCount: number;
    coreRelationshipCount: number;
}

/** Require a clean production target; a DatasetVersion is metadata, not isolation. */
export async function preflightExistingGraphIdentity(
    devAllowIncompleteData = false,
    leaseOwnerToken?: string,
): Promise<ExistingGraphIdentityReport> {
    const [coverageRows, duplicateRows, coreNodeRows, coreRelationshipRows] = await Promise.all([
        runQuery<{
            total: number;
            with_record_id: number;
        }>(`
            MATCH (h:Hadith)
            RETURN count(h) AS total,
                   count(CASE WHEN h.record_id IS NOT NULL
                                   AND h.record_id = toString(h.record_id)
                                   AND h.record_id = trim(toString(h.record_id))
                                   AND h.record_id <> ''
                              THEN 1 END) AS with_record_id
        `),
        runQuery<{ groups: number }>(`
            MATCH (h:Hadith)
            WHERE h.record_id IS NOT NULL
              AND h.record_id = toString(h.record_id)
              AND h.record_id = trim(toString(h.record_id))
              AND h.record_id <> ''
            WITH h.record_id AS record_id, count(*) AS occurrences
            WHERE occurrences > 1
            RETURN count(*) AS groups
        `),
        runQuery<{ count: number }>(`
            MATCH (n)
            WHERE NOT (
                n:FullregenLease AND size(labels(n)) = 1 AND
                n.name = $leaseName AND n.owner_token = $leaseOwnerToken
            )
            RETURN count(n) AS count
        `, {
            leaseName: FULLREGEN_LEASE_NAME,
            leaseOwnerToken: leaseOwnerToken ?? '',
        }),
        runQuery<{ count: number }>(`
            MATCH ()-[r]->()
            RETURN count(r) AS count
        `),
    ]);
    const totalHadiths = coverageRows[0]?.total ?? 0;
    const hadithsWithRecordId = coverageRows[0]?.with_record_id ?? 0;
    const report: ExistingGraphIdentityReport = {
        totalHadiths,
        hadithsWithRecordId,
        hadithsMissingRecordId: totalHadiths - hadithsWithRecordId,
        duplicateRecordIdGroups: duplicateRows[0]?.groups ?? 0,
        coreNodeCount: coreNodeRows[0]?.count ?? 0,
        coreRelationshipCount: coreRelationshipRows[0]?.count ?? 0,
    };

    if (
        !devAllowIncompleteData &&
        (report.coreNodeCount > 0 || report.coreRelationshipCount > 0)
    ) {
        throw new Error(
            `[fullregen] Production fullregen requires an empty clean/blue-green target before DB mutation: ` +
            `core_nodes=${report.coreNodeCount}, core_relationships=${report.coreRelationshipCount}, ` +
            `total_hadiths=${report.totalHadiths}, with_record_id=${report.hadithsWithRecordId}, ` +
            `missing_or_noncanonical_record_id=${report.hadithsMissingRecordId}, ` +
            `duplicate_record_id_groups=${report.duplicateRecordIdGroups}. ` +
            `Create a fresh target, complete and verify the load there, then switch traffic; ` +
            `never run a release fullregen against the served graph.`,
        );
    }
    if (devAllowIncompleteData && (report.coreNodeCount > 0 || report.coreRelationshipCount > 0)) {
        console.warn(
            `[fullregen] DANGER — disposable development override permits an in-place non-empty load: ` +
            `core_nodes=${report.coreNodeCount}, core_relationships=${report.coreRelationshipCount}, ` +
            `missing_or_noncanonical_record_id=${report.hadithsMissingRecordId}, ` +
            `duplicate_record_id_groups=${report.duplicateRecordIdGroups}. Never publish this target.`,
        );
    }
    return report;
}

interface CurationManifest {
    schema_version?: unknown;
    dataset_schema?: unknown;
    candidate_content_sha256?: unknown;
    published_dataset?: unknown;
    ready_for_full_load?: unknown;
    record_count?: unknown;
    stable_record_id_count?: unknown;
    tradition_counts?: unknown;
    release_blockers?: unknown;
    full_load_gates?: unknown;
    inputs?: unknown;
}

export interface CurationHandoffPaths {
    unifiedPath: string;
    loadSnapshotPath?: string;
    rawiPath: string;
    imamiSourceWorkRegistryPath: string;
    sourceRegistryPath: string;
}

const REQUIRED_FULL_LOAD_GATES = [
    'chain',
    'citation_bound_evidence',
    'corpus_nonempty',
    'corpus_shape',
    'curation_backlog',
    'provenance',
    'source_registry',
    'text_and_content',
    'translation_review',
] as const;
const SHA256_HEX = /^[a-f0-9]{64}$/;

function isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizedPath(value: string): string {
    return path.resolve(value).replace(/\\/g, '/').toLowerCase();
}

async function sha256RawFile(filePath: string): Promise<string> {
    const hash = crypto.createHash('sha256');
    for await (const chunk of fs.createReadStream(filePath)) hash.update(chunk);
    return hash.digest('hex');
}

async function validateManifestInputs(
    manifestPath: string,
    inputsValue: unknown,
    requiredPaths: string[],
): Promise<void> {
    if (!isObject(inputsValue) || Object.keys(inputsValue).length === 0) {
        throw new Error('inputs must be a nonempty hash manifest');
    }
    const manifestDir = path.dirname(manifestPath);
    const boundPaths = new Set<string>();
    for (const [relativePath, bindingValue] of Object.entries(inputsValue)) {
        if (!relativePath || path.isAbsolute(relativePath) || !isObject(bindingValue)) {
            throw new Error(`invalid input binding ${relativePath || '<blank>'}`);
        }
        const bytes = bindingValue.bytes;
        const sha256 = bindingValue.sha256;
        if (typeof bytes !== 'number' || !Number.isSafeInteger(bytes) || bytes < 0 ||
            typeof sha256 !== 'string' || !SHA256_HEX.test(sha256)) {
            throw new Error(`invalid input size/hash binding for ${relativePath}`);
        }
        const resolved = path.resolve(manifestDir, relativePath);
        const key = normalizedPath(resolved);
        if (boundPaths.has(key)) throw new Error(`duplicate input path binding for ${relativePath}`);
        boundPaths.add(key);
        const stat = await fs.promises.stat(resolved);
        if (!stat.isFile() || stat.size !== bytes || await sha256RawFile(resolved) !== sha256) {
            throw new Error(`input hash binding mismatch for ${relativePath}`);
        }
    }
    for (const requiredPath of requiredPaths) {
        if (!boundPaths.has(normalizedPath(requiredPath))) {
            throw new Error(`required input is not hash-bound: ${requiredPath}`);
        }
    }
}

interface ImamiSourceWork {
    sourceWorkId: string;
    canonicalSource: string;
    provenanceSource: string;
    providerBacked: boolean;
}

async function validateImamiSourceWorkMappings(
    unifiedPath: string,
    registryPath: string,
    datasetSchema: string[],
    expectedImamiRows: number,
): Promise<void> {
    const registry = JSON.parse(await fs.promises.readFile(registryPath, 'utf8')) as unknown;
    if (!isObject(registry) || registry.schema_version !== 1 ||
        !Array.isArray(registry.source_works) || !Array.isArray(registry.non_provider_source_works)) {
        throw new Error('unsupported Imami source-work registry schema');
    }
    const byWorkId = new Map<string, ImamiSourceWork>();
    const byProviderBookId = new Map<string, ImamiSourceWork>();
    const register = (entryValue: unknown, providerBacked: boolean): void => {
        if (!isObject(entryValue)) throw new Error('invalid Imami source-work registry entry');
        const sourceWorkId = typeof entryValue.source_work_id === 'string'
            ? entryValue.source_work_id.trim() : '';
        const canonicalSource = typeof entryValue.canonical_source === 'string'
            ? entryValue.canonical_source.trim() : '';
        const compiler = typeof entryValue.compiler === 'string' ? entryValue.compiler.trim() : '';
        const provenanceSource = typeof entryValue.provenance_source === 'string'
            ? entryValue.provenance_source.trim() : '';
        if (!/^imami:[a-z0-9][a-z0-9-]*$/.test(sourceWorkId) || !canonicalSource || !compiler ||
            CANONICAL_SOURCE_TRADITIONS.get(canonicalSource) !== 'Imami' ||
            byWorkId.has(sourceWorkId)) {
            throw new Error(`invalid or duplicate Imami source-work identity ${sourceWorkId || '<blank>'}`);
        }
        const providerBookIds = entryValue.provider_book_ids;
        if (providerBacked && (!Array.isArray(providerBookIds) || providerBookIds.length === 0)) {
            throw new Error(`provider-backed Imami work lacks provider_book_ids: ${sourceWorkId}`);
        }
        if (!providerBacked && (providerBookIds !== undefined || !provenanceSource)) {
            throw new Error(`non-provider Imami work lacks exact provenance binding: ${sourceWorkId}`);
        }
        const work = { sourceWorkId, canonicalSource, provenanceSource, providerBacked };
        byWorkId.set(sourceWorkId, work);
        for (const providerBookIdValue of providerBacked ? (providerBookIds as unknown[]) : []) {
            const providerBookId = typeof providerBookIdValue === 'string'
                ? providerBookIdValue.trim() : '';
            if (!providerBookId || byProviderBookId.has(providerBookId)) {
                throw new Error(`blank or duplicate Imami provider_book_id ${providerBookId || '<blank>'}`);
            }
            byProviderBookId.set(providerBookId, work);
        }
    };
    for (const entry of registry.source_works) register(entry, true);
    for (const entry of registry.non_provider_source_works) register(entry, false);

    let imamiRows = 0;
    let headerChecked = false;
    const mismatches: string[] = [];
    for await (const row of readUnifiedCsv(unifiedPath)) {
        if (!headerChecked) {
            const actualSchema = Object.keys(row._raw);
            if (actualSchema.length !== datasetSchema.length ||
                actualSchema.some((column, index) => column !== datasetSchema[index])) {
                throw new Error('dataset_schema does not exactly match the published CSV header');
            }
            headerChecked = true;
        }
        if (row.tradition !== 'Imami') continue;
        imamiRows++;
        const providerBookId = (row._raw['provider_book_id'] ?? '').trim();
        const expected = providerBookId
            ? byProviderBookId.get(providerBookId)
            : byWorkId.get(row.source_work_id);
        const exact = Boolean(expected) &&
            expected?.sourceWorkId === row.source_work_id &&
            expected?.canonicalSource === row.source &&
            (providerBookId ? expected?.providerBacked === true : expected?.providerBacked === false) &&
            (providerBookId ? true : expected?.provenanceSource === row.provenance_source);
        if (!exact && mismatches.length < 10) {
            mismatches.push(
                `${row.record_id || row.dataset_row_id}: provider_book_id=${providerBookId || '<blank>'} ` +
                `source_work_id=${row.source_work_id || '<blank>'} source=${row.source}`,
            );
        }
    }
    if (!headerChecked || imamiRows !== expectedImamiRows || mismatches.length > 0) {
        throw new Error(
            `Imami source-work mapping is not exact: rows=${imamiRows}/${expectedImamiRows}` +
            (mismatches.length > 0 ? `; ${mismatches.join('; ')}` : ''),
        );
    }
}

/** Require the generator's explicit curation handoff before a release load. */
export async function preflightCurationManifest(
    manifestPath: string,
    report: FullregenPreflightReport,
    unifiedLogicalSha256: string,
    devAllowIncompleteData: boolean,
    handoffPaths?: CurationHandoffPaths,
): Promise<void> {
    let manifest: CurationManifest;
    try {
        manifest = JSON.parse(await fs.promises.readFile(manifestPath, 'utf8')) as CurationManifest;
    } catch (error) {
        if (!devAllowIncompleteData) {
            throw new Error(`[fullregen] Missing or invalid curation manifest: ${manifestPath}`, { cause: error });
        }
        console.warn(`[fullregen] DEV OVERRIDE: missing or invalid curation manifest ${manifestPath}`);
        return;
    }
    try {
        if (manifest.schema_version !== 2) throw new Error('schema_version must equal 2');
        if (!Array.isArray(manifest.dataset_schema) ||
            manifest.dataset_schema.some((column) => typeof column !== 'string') ||
            new Set(manifest.dataset_schema).size !== manifest.dataset_schema.length) {
            throw new Error('dataset_schema must contain unique string columns');
        }
        const datasetSchema = manifest.dataset_schema as string[];
        for (const requiredColumn of [
            'provider_book_id', 'source_work_id', 'source_display_label', 'record_id',
            'text_ar', 'text_en', 'translation_status', 'translation_review_status',
        ]) {
            if (!datasetSchema.includes(requiredColumn)) {
                throw new Error(`dataset_schema lacks ${requiredColumn}`);
            }
        }
        if (typeof manifest.candidate_content_sha256 !== 'string' ||
            !SHA256_HEX.test(manifest.candidate_content_sha256)) {
            throw new Error('candidate_content_sha256 is missing or malformed');
        }
        if (!isObject(manifest.release_blockers)) {
            throw new Error('release_blockers must be an object');
        }
        const blockerValues = Object.values(manifest.release_blockers);
        if (blockerValues.some((count) =>
            typeof count !== 'number' || !Number.isSafeInteger(count) || count !== 0)) {
            throw new Error('release_blockers must contain only zero integer counts');
        }
        if (!isObject(manifest.full_load_gates)) {
            throw new Error('full_load_gates must be an object');
        }
        for (const gateName of REQUIRED_FULL_LOAD_GATES) {
            const gate = manifest.full_load_gates[gateName];
            if (!isObject(gate) || gate.passed !== true) {
                throw new Error(`full_load_gates.${gateName}.passed must equal true`);
            }
        }
        for (const [gateName, gate] of Object.entries(manifest.full_load_gates)) {
            if (!isObject(gate) || gate.passed !== true) {
                throw new Error(`full_load_gates.${gateName}.passed must equal true`);
            }
        }
        if (manifest.ready_for_full_load !== true ||
            manifest.record_count !== report.totalRecords ||
            manifest.stable_record_id_count !== report.totalRecords) {
            throw new Error('ready flag or record/stable-ID counts do not match streamed preflight');
        }
        if (!isObject(manifest.tradition_counts)) {
            throw new Error('tradition_counts must be an object');
        }
        for (const [tradition, count] of Object.entries(report.perTraditionCounts)) {
            if (manifest.tradition_counts[tradition] !== count) {
                throw new Error(`tradition_counts.${tradition} does not match streamed preflight`);
            }
        }
        if (!handoffPaths) throw new Error('strict handoff paths are required');
        const published = manifest.published_dataset;
        if (!isObject(published) || published.logical_sha256 !== unifiedLogicalSha256 ||
            !isObject(published.csv) || !isObject(published.gzip)) {
            throw new Error('published_dataset logical content hash is not bound to the CSV');
        }
        const csvPathValue = published.csv.path;
        const gzipPathValue = published.gzip.path;
        if (typeof csvPathValue !== 'string' || typeof gzipPathValue !== 'string' ||
            published.csv.sha256 !== unifiedLogicalSha256 ||
            published.gzip.logical_sha256 !== unifiedLogicalSha256) {
            throw new Error('published CSV/GZIP content bindings are incomplete');
        }
        const manifestDir = path.dirname(manifestPath);
        const declaredCsvPath = path.resolve(manifestDir, csvPathValue);
        const declaredGzipPath = path.resolve(manifestDir, gzipPathValue);
        if (normalizedPath(declaredCsvPath) !== normalizedPath(handoffPaths.unifiedPath) ||
            normalizedPath(declaredGzipPath) !== normalizedPath(`${handoffPaths.unifiedPath}.gz`)) {
            throw new Error('published CSV/GZIP paths do not identify the selected input');
        }
        const csvStat = await fs.promises.stat(declaredCsvPath);
        const gzipStat = await fs.promises.stat(declaredGzipPath);
        if (published.csv.bytes !== csvStat.size || published.gzip.bytes !== gzipStat.size ||
            await sha256RawFile(declaredCsvPath) !== published.csv.sha256 ||
            typeof published.gzip.sha256 !== 'string' ||
            await sha256RawFile(declaredGzipPath) !== published.gzip.sha256 ||
            await sha256File(declaredGzipPath) !== unifiedLogicalSha256) {
            throw new Error('published CSV/GZIP physical or logical hash mismatch');
        }
        await validateManifestInputs(manifestPath, manifest.inputs, [
            handoffPaths.rawiPath,
            handoffPaths.imamiSourceWorkRegistryPath,
            handoffPaths.sourceRegistryPath,
        ]);
        await validateImamiSourceWorkMappings(
            handoffPaths.loadSnapshotPath ?? handoffPaths.unifiedPath,
            handoffPaths.imamiSourceWorkRegistryPath,
            datasetSchema,
            report.perTraditionCounts.Imami ?? 0,
        );
    } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        if (!devAllowIncompleteData) {
            throw new Error(`[fullregen] Curation manifest is not release-ready: ${detail}`, { cause: error });
        }
        console.warn(`[fullregen] DEV OVERRIDE: curation handoff validation failed: ${detail}`);
    }
}

/** Copy the hash-validated CSV to a read-only content-addressed load snapshot. */
async function withImmutableHadithSnapshot<T>(
    sourcePath: string,
    expectedLogicalSha256: string,
    work: (snapshotPath: string) => Promise<T>,
): Promise<T> {
    const tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'islamicapps-fullregen-'));
    const snapshotPath = path.join(tempDir, `${expectedLogicalSha256}.csv`);
    try {
        await fs.promises.copyFile(sourcePath, snapshotPath, fs.constants.COPYFILE_EXCL);
        if (await sha256File(snapshotPath) !== expectedLogicalSha256) {
            throw new Error('[fullregen] Unified CSV changed while creating the immutable load snapshot');
        }
        await fs.promises.chmod(snapshotPath, 0o444);
        return await work(snapshotPath);
    } finally {
        await fs.promises.chmod(snapshotPath, 0o600).catch(() => undefined);
        await fs.promises.rm(tempDir, { recursive: true, force: true });
    }
}

export async function runModeFullregen(args: CliArgs): Promise<void> {
    console.log('='.repeat(64));
    console.log('  Isnad/Narrator Graph — Full Regen');
    console.log('='.repeat(64));
    const bufferSize = validateFullregenBatchSize(args.batchSize);
    assertDevIncompleteFullregenTarget(args.devAllowIncompleteData);

    // Resolve and validate every input before the first graph mutation.
    const { hadithPath, rawiPath } = resolveDatasetPaths();
    console.log(`\n[fullregen] Hadith CSV: ${hadithPath}`);
    console.log(`[fullregen] Rawis CSV:  ${rawiPath}`);

    const [unifiedHash, rawisHash] = await Promise.all([
        sha256File(hadithPath),
        sha256File(rawiPath),
    ]);
    const contentHash = crypto
        .createHash('sha256')
        .update(`unified:${unifiedHash}\nrawis:${rawisHash}`)
        .digest('hex');
    console.log(`[fullregen] content_hash: ${contentHash}`);

    await withImmutableHadithSnapshot(hadithPath, unifiedHash, async (hadithSnapshotPath) => {

    console.log('\n[fullregen] Loading all_rawis.csv for read-only validation...');
    const rawis: Map<number, RawiRecord> = await readAllRawis(rawiPath);
    if (rawis.size === 0) throw new Error('[fullregen] all_rawis.csv contains no narrator records');
    preflightRawiDataset(rawis);
    console.log(`[fullregen] Loaded ${rawis.size} rawis.`);

    console.log('\n[fullregen] Read-only curation preflight...');
    const preflight = await preflightUnifiedDataset(
        hadithSnapshotPath,
        args.devAllowIncompleteData,
        rawis,
    );
    const {
        totalRecords,
        unknownRows,
        perTraditionCounts,
        perSourceCounts,
        csvSourceNames,
        sourceTraditions,
    } = preflight;
    if (args.devAllowIncompleteData) {
        console.warn(
            `[fullregen] DEV OVERRIDE active: derived_record_ids=${preflight.legacyRecordIdsDerived}, ` +
            `missing_source_record_ids=${preflight.missingSourceRecordIds}, ` +
            `missing_provenance_sources=${preflight.missingProvenanceSources}, ` +
            `missing_arabic=${preflight.missingArabic}, missing_english=${preflight.missingEnglish}, ` +
            `noncomplete_translation=${preflight.nonCompleteTranslations}, ` +
            `missing_translation_sources=${preflight.missingTranslationSources}, ` +
            `missing_translation_review_statuses=${preflight.missingTranslationReviewStatuses}, ` +
            `nonrelease_translation_review_statuses=${preflight.nonReleaseTranslationReviewStatuses}, ` +
            `missing_required_translation_models=${preflight.missingRequiredTranslationModels}, ` +
            `unknown_chain_refs=${preflight.missingNarratorReferences}, ` +
            `missing_chain_indx=${preflight.emptyChainRows}, ` +
            `unregistered_source_rows=${preflight.unregisteredSourceRows}, ` +
            `missing_imami_source_work_id=${preflight.missingImamiSourceWorkIds}, ` +
            `invalid_imami_source_work_id=${preflight.invalidImamiSourceWorkIds}`,
        );
    }

    await preflightCurationManifest(
        path.join(path.dirname(hadithPath), 'curation_manifest.json'),
        preflight,
        unifiedHash,
        args.devAllowIncompleteData,
        {
            unifiedPath: hadithPath,
            loadSnapshotPath: hadithSnapshotPath,
            rawiPath,
            imamiSourceWorkRegistryPath: path.join(
                path.dirname(hadithPath),
                'imami_source_work_registry.json',
            ),
            sourceRegistryPath: path.join(
                path.dirname(path.dirname(path.dirname(hadithPath))),
                'src', 'lib', 'constants', 'sources.ts',
            ),
        },
    );

    const measuredUnknownFraction = totalRecords > 0 ? unknownRows / totalRecords : 0;
    console.log(
        `[fullregen] Records: ${totalRecords} | ` +
        `Sunni=${perTraditionCounts.Sunni} Imami=${perTraditionCounts.Imami} ` +
        `Ibadi=${perTraditionCounts.Ibadi} Zaydi=${perTraditionCounts.Zaydi}`
    );
    console.log(`[fullregen] Truly unknown rows (no grading info): ${unknownRows} ` +
        `(fraction=${measuredUnknownFraction.toFixed(4)})`);

    // Unknown registries are permitted only because preflight established one
    // explicit row tradition for every source; no loader invents a Sunni default.
    const unregisteredSources = [...csvSourceNames].filter(
        (source) => !CANONICAL_SOURCE_TRADITIONS.has(source),
    );
    if (unregisteredSources.length > 0) {
        console.warn(
            `[fullregen] WARNING: Unregistered source(s) in unified CSV ` +
            `(using validated row traditions): ` +
            unregisteredSources.map((source) => `${source}=${sourceTraditions.get(source)}`).join(', '),
        );
    }

    // Cost acknowledgement is additive: it does not bypass any curation,
    // clean-target, or disposable-development guard above or below this call.
    assertRailwayProductionFullregenAcknowledgement(
        process.env.NEO4J_URL,
        args.devAllowIncompleteData,
    );
    if (await sha256File(hadithSnapshotPath) !== unifiedHash) {
        throw new Error('[fullregen] Immutable load snapshot hash changed before database acquisition');
    }
    await withFullregenLease(contentHash, async (lease) => {
    const graphIdentity = await preflightExistingGraphIdentity(
        args.devAllowIncompleteData,
        lease.ownerToken,
    );
    console.log(
        `[fullregen] Target graph: core_nodes=${graphIdentity.coreNodeCount}, ` +
        `core_relationships=${graphIdentity.coreRelationshipCount}, ` +
        `hadiths=${graphIdentity.totalHadiths}, record_id=${graphIdentity.hadithsWithRecordId}`,
    );

    console.log('\n[fullregen] Initializing Neo4j schema after preflight...');
    await lease.assertHeld();
    await initializeSchema();

    console.log('\n[fullregen] G-1: Migrating legacy scalar assessments...');
    await lease.assertHeld();
    const migReport = await migrateScalarAssessments();
    console.log(
        `[fullregen] G-1 migration: narrators=${migReport.narrators_migrated} hadiths=${migReport.hadiths_migrated} ` +
        `scalars_nulled=${migReport.scalars_nulled} errors=${migReport.errors.length}`,
    );
    if (migReport.errors.length > 0) {
        throw new Error(
            `[fullregen] G-1 scalar-assessment migration failed: ` +
            migReport.errors.slice(0, 5).join('; '),
        );
    }

    // Merge :DatasetVersion provenance node.
    await lease.assertHeld();
    const { id: dvId } = await mergeDatasetVersion({
        expectedRecordCount: totalRecords,
        perTraditionCounts,
        contentHash,
        measuredUnknownFraction,
        versionLabel: `unified-${contentHash.slice(0, 16)}`,
        activateImmediately: false,
        releaseEligible: !args.devAllowIncompleteData,
        nonReleaseReason: args.devAllowIncompleteData ? 'dev_allow_incomplete_data' : '',
        loadPurpose: args.devAllowIncompleteData ? 'dev_fullregen' : 'release_fullregen',
    });
    console.log(
        `\n[fullregen] Staging DatasetVersion id: ${dvId}` +
        (args.devAllowIncompleteData ? ' (non-release)' : ''),
    );

    // 8. FR-1.8: SchoolOfThought → ReligiousTradition migration.
    await lease.assertHeld();
    await migrateSchoolOfThought(dvId);

    // 9. Task 1: Bulk-merge :Narrator nodes from rawis ONCE before streaming loop.
    console.log('\n[fullregen] Bulk-merging :Narrator nodes from rawis...');
    await lease.assertHeld();
    const narratorResult = await bulkLoadNarrators(rawis, dvId);
    console.log(
        `[fullregen] Narrators: created=${narratorResult.created} ` +
        `matched=${narratorResult.matched} errors=${narratorResult.errors}`
    );
    if (narratorResult.errors > 0) {
        throw new Error(`[fullregen] Narrator base load failed for ${narratorResult.errors} row(s)`);
    }

    // 9b. Global chain-materialization wipe. A production target is empty by
    // contract; this cleanup exists only for loudly marked disposable dev runs.
    //
    // Why wipe both:
    //   - INCLUDES: prior runs may have written LONGER chains (taḥwīl merge,
    //     chain_indx=[hadith_no] garbage). MERGE preserves stale extras →
    //     chain becomes union(old, new). Wipe → clean re-load.
    //   - NARRATED_FROM: remove relationships not present in the curated input;
    //     the idempotent MERGE rebuild remains safe on resume.
    //   - INCLUDES_MENTION: remove unresolved mentions that curation has resolved.
    //
    // Chunked apoc-free delete to stay under the 30s per-tx timeout on
    // Railway. Count BEFORE delete (after DELETE the rel is gone).
    async function wipeRelType(
        relType: 'INCLUDES' | 'NARRATED_FROM' | 'INCLUDES_MENTION',
    ): Promise<void> {
        await lease.assertHeld();
        console.log(`\n[fullregen] Wiping :${relType} edges before re-load...`);
        const before = await runQuery<{ n: number }>(
            `MATCH ()-[r:${relType}]->() RETURN count(r) AS n`,
        );
        const beforeCount = before[0]?.n ?? 0;
        console.log(`[fullregen]   :${relType} edges before wipe: ${beforeCount.toLocaleString()}`);
        let totalDeleted = 0;
        while (true) {
            await lease.assertHeld();
            const deleted = await runWrite<{ n: number }>(
                `MATCH ()-[r:${relType}]->()
                 WITH r LIMIT 50000
                 WITH collect(r) AS rs
                 WITH rs, size(rs) AS n
                 FOREACH (x IN rs | DELETE x)
                 RETURN n AS n`,
            );
            const n = deleted[0]?.n ?? 0;
            totalDeleted += n;
            if (n === 0) break;
            console.log(`[fullregen]   wiped ${totalDeleted.toLocaleString()} / ${beforeCount.toLocaleString()}`);
        }
        console.log(`[fullregen] :${relType} wipe complete (${totalDeleted.toLocaleString()} edges deleted).`);
    }
    await wipeRelType('INCLUDES');
    await wipeRelType('NARRATED_FROM');
    await wipeRelType('INCLUDES_MENTION');

    // 10. Create JSONL logger.
    const logger = createRegenLogger('fullregen', dvId);
    const ctx: LoadContext = {
        dvId,
        mode: 'fullregen',
        log: logger.write.bind(logger),
    };

    // Main streaming load loop; see AGENTS.md for identity and retry invariants.
    console.log(
        `\n[fullregen] Streaming unified CSV ` +
        `(rows<=${bufferSize}, payload<=${MAX_BUFFER_PAYLOAD_BYTES / (1024 * 1024)} MiB)...`,
    );
    const sourceCache = new Map<string, Tradition>();
    let buffer: BufferedRow[] = [];
    let bufferPayloadBytes = 0;
    let rowNum = 0;
    let chainLoaded = 0;
    let assessmentLoaded = 0;
    let noExtantLoaded = 0;
    let mentionLoaded = 0;
    let errors = 0;

    const flushBuffer = async (): Promise<void> => {
        if (buffer.length === 0) return;
        await lease.assertHeld();
        const slice = buffer;
        buffer = [];
        bufferPayloadBytes = 0;
        try {
            await loadHadithsBatch(slice, ctx, sourceCache);
            await lease.assertHeld();
            const chainRes = await loadChainsBatch(slice, ctx);
            for (const keys of chainRes.chainKeysByRow.values()) chainLoaded += keys.length;
            await lease.assertHeld();
            const asmtRes = await loadAssessmentsBatch(slice, ctx);
            assessmentLoaded += asmtRes.real;
            noExtantLoaded += asmtRes.noExtant;
            await lease.assertHeld();
            mentionLoaded += await loadNameMentionsBatch(slice, chainRes.chainKeysByRow, ctx);
            await lease.assertHeld();
        } catch (err) {
            errors += slice.length;
            for (const it of slice) {
                logger.write({
                    action: 'batch_error',
                    record_id: it.hadithKey,
                    dataset_row_id: it.datasetRowId,
                    size: slice.length,
                    error: String(err),
                });
            }
            logger.close();
            throw new Error(
                `[fullregen] Batch load failed for ${slice.length} row(s); ` +
                'stopped without replaying already-committed phases. Re-run is idempotent.',
                { cause: err },
            );
        }
    };

    for await (const row of readUnifiedCsv(hadithSnapshotPath)) {
        rowNum++;
        // Per-row CPU work: entity resolution. No DB calls.
        let resolutions: NarratorResolutionResult[];
        if (row.chain_indx.length > 0) {
            // Tier-1: deterministic join from chain_indx.
            resolutions = buildTier1Resolution(row, rawis);
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
                const erResults = await resolveNarrators(
                    erRow,
                    rawis as unknown as Map<number, import('./entity-resolution').RawiRecord>,
                );
                resolutions = erResults.map((r) => adaptErResult(r));
            } catch (err) {
                errors++;
                logger.write({ action: 'er_error', row: rowNum, error: String(err) });
                logger.close();
                throw new Error(`[fullregen] Entity resolution failed on row ${rowNum}`, { cause: err });
            }
        }

        let bufferedRow: BufferedRow;
        try {
            bufferedRow = buildBufferedRow(
                prepareUnifiedRowForLoad(row, args.devAllowIncompleteData),
                resolutions,
            );
        } catch (err) {
            errors++;
            logger.write({ action: 'buffer_error', row: rowNum, error: String(err) });
            logger.close();
            throw new Error(`[fullregen] Buffer preparation failed on row ${rowNum}`, { cause: err });
        }

        const rowPayloadBytes = estimateRowPayloadBytes(row);
        if (rowPayloadBytes > MAX_BUFFER_PAYLOAD_BYTES) {
            logger.close();
            throw new Error(
                `[fullregen] Row ${rowNum} (${bufferedRow.hadithKey}) exceeds the ` +
                `${MAX_BUFFER_PAYLOAD_BYTES}-byte payload bound after successful preflight`,
            );
        }
        if (
            buffer.length > 0 &&
            bufferPayloadBytes + rowPayloadBytes > MAX_BUFFER_PAYLOAD_BYTES
        ) {
            await flushBuffer();
        }
        buffer.push(bufferedRow);
        bufferPayloadBytes += rowPayloadBytes;

        if (buffer.length >= bufferSize) {
            await flushBuffer();
            if (rowNum % 1000 === 0 || rowNum === bufferSize) {
                console.log(
                    `[fullregen] Progress: ${rowNum} rows | chains=${chainLoaded} ` +
                    `assessments=${assessmentLoaded} noExtant=${noExtantLoaded} ` +
                    `mentions=${mentionLoaded} errors=${errors}`,
                );
            }
        }
    }

    // Final flush for the tail.
    await flushBuffer();
    console.log(
        `[fullregen] Progress: ${rowNum} rows | chains=${chainLoaded} ` +
        `assessments=${assessmentLoaded} noExtant=${noExtantLoaded} ` +
        `mentions=${mentionLoaded} errors=${errors}  (final)`,
    );

    try {
        await verifyLoadedSnapshot(dvId, totalRecords, chainLoaded, rawis.size);
    } catch (err) {
        logger.write({ action: 'snapshot_verification_error', error: String(err) });
        logger.close();
        throw err;
    }
    console.log('[fullregen] Snapshot counts verified before DatasetVersion finalization.');

    // 12. G-6: Flag all [:NARRATED_FROM] transmission edges with temporal plausibility.
    console.log('\n[fullregen] G-6: Flagging transmission edges with temporal plausibility...');
    await lease.assertHeld();
    const temporalReport = await flagAllTransmissionEdges(rawis, dvId);
    console.log(
        `[fullregen] G-6: total=${temporalReport.total_edges_assessed} ` +
        `plausible=${temporalReport.plausible} impossible=${temporalReport.impossible} ` +
        `unknown=${temporalReport.unknown} errors=${temporalReport.errors.length}`
    );
    if (temporalReport.errors.length > 0) {
        logger.write({ action: 'temporal_error', errors: temporalReport.errors.slice(0, 100) });
        logger.close();
        throw new Error(
            `[fullregen] Temporal annotation failed for ${temporalReport.errors.length} edge(s); ` +
            'the staged DatasetVersion was not activated',
        );
    }

    // 13. Task 7: G-2 GIGO report — edge confidence strata.
    await printGigoReport();

    logger.close();

    // A disposable override is finalized with an explicit non-release marker;
    // only a strict release load may enter the active/complete lifecycle.
    if (await sha256File(hadithSnapshotPath) !== unifiedHash) {
        throw new Error('[fullregen] Immutable load snapshot hash changed before finalization');
    }
    if (args.devAllowIncompleteData) {
        await lease.assertHeld();
        await markDatasetVersionNonReleaseLoaded(
            dvId,
            'dev_fullregen',
            'dev_allow_incomplete_data',
        );
        console.warn(
            '[fullregen] DEV OVERRIDE: DatasetVersion remains inactive with ' +
            'load_status=non_release_loaded; this graph must not be published.',
        );
    } else {
        await lease.assertHeld();
        await activateDatasetVersion(dvId);
        console.log('[fullregen] DatasetVersion promoted; prior versions marked active=false.');
    }

    // 14. Summary.
    console.log('\n' + '='.repeat(64));
    console.log(args.devAllowIncompleteData
        ? '  Development Full Regen Finished (Non-Release)'
        : '  Full Regen Complete');
    console.log('='.repeat(64));
    console.log(`  DatasetVersion id:   ${dvId}`);
    console.log(`  Release state:       ${args.devAllowIncompleteData ? 'non_release_loaded' : 'active'}`);
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
    });
    });
}
