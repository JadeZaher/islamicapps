/**
 * io.ts — Pure I/O helpers for the isnad-graph regen pipeline.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import, no top-level Cypher or network calls.
 * Exports:
 *   readUnifiedCsv(path)  → AsyncIterable<UnifiedRow>
 *   readAllRawis(path)    → Promise<Map<number, RawiRecord>>
 *   createRegenLogger(mode, dvId) → RegenLogger
 */

import fs from 'fs';
import path from 'path';
import readline from 'readline';
import zlib from 'zlib';
import { createHash } from 'crypto';
import type { Readable } from 'stream';

/** Resolve an explicit dataset path, falling back to its gzip sibling. */
export function resolveDatasetInputPath(filePath: string): string {
    if (fs.existsSync(filePath)) return filePath;
    if (!filePath.toLowerCase().endsWith('.gz')) {
        const gzPath = `${filePath}.gz`;
        if (fs.existsSync(gzPath)) return gzPath;
    }
    throw new Error(`[io] Dataset input not found: ${filePath} (or ${filePath}.gz)`);
}

/** True when a plain path or its gzip sibling can be read. */
export function datasetInputExists(filePath: string): boolean {
    if (fs.existsSync(filePath)) return true;
    return !filePath.toLowerCase().endsWith('.gz') && fs.existsSync(`${filePath}.gz`);
}

/** Open the logical, decompressed byte stream for a dataset input. */
function openDatasetStream(filePath: string): Readable {
    const resolvedPath = resolveDatasetInputPath(filePath);
    const source = fs.createReadStream(resolvedPath);
    return resolvedPath.toLowerCase().endsWith('.gz')
        ? source.pipe(zlib.createGunzip())
        : source;
}

/** SHA-256 the logical file contents without buffering the complete file. */
export async function sha256File(filePath: string): Promise<string> {
    const hash = createHash('sha256');
    for await (const chunk of openDatasetStream(filePath)) {
        hash.update(chunk);
    }
    return hash.digest('hex');
}

// ─── Shared types (canonical surface consumed by all regen modules) ──────────

export type Tradition = 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';

/** One row from all_hadiths_unified.csv */
export interface UnifiedRow {
    /** From CSV `id` column — the canonical dataset_row_id. */
    dataset_row_id: number | null;
    /** Durable cross-version identity; fullregen never keys nodes on row order. */
    record_id: string;
    /** Identifier owned by the upstream source, before unification. */
    source_record_id: string;
    /** From CSV `hadith_id` — source-specific original ID (may differ from dataset_row_id). */
    hadith_id: string;
    hadith_no: string;
    source: string;
    /** Durable work key when provider metadata distinguishes a shared label. */
    source_work_id: string;
    /** Provider-facing source label retained separately from canonical work name. */
    source_display_label: string;
    /** Canonical tradition string — already canonicalized by the reader. */
    tradition: Tradition;
    volume: string;
    chapter: string;
    chapter_no: string;
    category: string;
    text_ar: string;
    text_en: string;
    provenance_source: string;
    translation_status: string;
    translation_source: string;
    translation_model: string;
    translation_review_status: string;
    matn_ar: string;
    matn_en: string;
    /** Narrator names in sanad field (free text, not yet resolved). */
    sanad: string;
    sanad_confidence: string;
    /**
     * Parsed numeric chain indices, organized as branches.
     *   outer array = isnad branches (one per taḥwīl `ح` split, single-branch rows produce one branch)
     *   inner array = scholar_indx ints in chain order within that branch
     *
     * Empty when the CSV cell is empty / "[]". A flat legacy cell `"1,2,3"`
     * still produces `[[1, 2, 3]]` (one branch), preserving backwards
     * compatibility with pre-Phase-2 CSVs.
     */
    chain_indx: number[][];
    school: string;
    chain_type: string;
    attributed_to: string;
    narration_level: string;
    grade_value: string;
    grade_tradition: string;
    grade_source: string;
    gradings_full: string;
    url: string;
    page_ref: string;
    /** Raw row for any fields not explicitly mapped. */
    _raw: Record<string, string>;
}

/** One row from all_rawis.csv (narrator controlled vocabulary). */
export interface RawiRecord {
    scholar_indx: number;
    name: string;
    name_english: string;
    name_arabic: string;
    grade: string;
    bio: string;
    birth_date_hijri: number | null;
    birth_date_hijri_raw: string;
    birth_date_gregorian: number | null;
    birth_date_gregorian_raw: string;
    birth_date_source_text: string;
    birth_place: string;
    death_date_hijri: number | null;
    death_date_hijri_raw: string;
    death_date_gregorian: number | null;
    death_date_gregorian_raw: string;
    death_date_source_text: string;
    death_place: string;
    death_reason: string;
    teachers_inds: number[];
    students_inds: number[];
    geographic_region: string;
    tabaqah: string;
}

/** Context passed to loadHadith, loadChain, assessment, etc. */
export interface LoadContext {
    /** Active DatasetVersion.id (uuid string). */
    dvId: string;
    /** Mode of the current run. */
    mode: 'test' | 'fullregen' | 'diff' | 'enrich';
    /** Append a JSONL log line. */
    log: RegenLogger['write'];
}

/** JSONL logger handle. */
export interface RegenLogger {
    write(entry: Record<string, unknown>): void;
    close(): void;
}

// ─── Tradition canonicalization ───────────────────────────────────────────────

const TRADITION_MAP: Record<string, Tradition> = {
    'sunni': 'Sunni',
    'imami': 'Imami',
    'shia imami': 'Imami',
    'shia_imami': 'Imami',
    'twelver': 'Imami',
    'zaydi': 'Zaydi',
    'shia zaydi': 'Zaydi',
    'shia_zaydi': 'Zaydi',
    'ibadi': 'Ibadi',
};

export function canonicalizeTradition(raw: string): Tradition {
    const key = raw.toLowerCase().trim();
    const tradition = TRADITION_MAP[key];
    if (!tradition) {
        throw new Error(`[io] unsupported tradition: ${raw.trim() || '<blank>'}`);
    }
    return tradition;
}

export function isSupportedTradition(raw: string): boolean {
    return Object.prototype.hasOwnProperty.call(TRADITION_MAP, raw.toLowerCase().trim());
}

// ─── CSV parser (multiline-quoted-field aware) ────────────────────────────────
//
// Ported from import-datasets.ts / regen-isnad-graph.ts — the canonical
// multiline-aware parser that counts 69,368 records vs wc -l's ~78,952.

type CSVRow = Record<string, string>;

class CSVParser {
    private headers: string[] = [];
    private isFirstLine = true;

    parseRow(line: string): CSVRow | null {
        if (this.isFirstLine) {
            this.headers = this.parseCSVLine(line.replace(/^\uFEFF/, ''));
            if (
                this.headers.length === 0 ||
                this.headers.some((header) => header.length === 0) ||
                new Set(this.headers).size !== this.headers.length
            ) {
                throw new Error('[io] CSV header is empty or contains duplicate column names');
            }
            this.isFirstLine = false;
            return null;
        }
        const values = this.parseCSVLine(line);
        if (values.length !== this.headers.length) {
            throw new Error(`[io] CSV column mismatch: expected ${this.headers.length}, received ${values.length}`);
        }
        const row: CSVRow = {};
        this.headers.forEach((header, idx) => {
            row[header] = values[idx] ?? '';
        });
        return row;
    }

    private parseCSVLine(line: string): string[] {
        const result: string[] = [];
        let current = '';
        let insideQuotes = false;
        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            const nextChar = line[i + 1];
            if (char === '"') {
                if (insideQuotes && nextChar === '"') {
                    current += '"';
                    i++;
                } else {
                    insideQuotes = !insideQuotes;
                }
            } else if (char === ',' && !insideQuotes) {
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        result.push(current.trim());
        return result;
    }
}

/** Yield complete RFC-4180-style records while retaining only one record. */
async function* readCSVRecords(filePath: string): AsyncIterable<string> {
    const stream = openDatasetStream(filePath);
    stream.setEncoding('utf8');
    let currentRow = '';
    let insideQuotes = false;
    let previousDelimiterWasCr = false;

    for await (const chunk of stream) {
        const text = String(chunk);
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            if (char === '"') {
                insideQuotes = !insideQuotes;
                currentRow += char;
                previousDelimiterWasCr = false;
                continue;
            }

            if (!insideQuotes && (char === '\n' || char === '\r')) {
                if (char === '\n' && previousDelimiterWasCr) {
                    previousDelimiterWasCr = false;
                    continue;
                }
                if (currentRow.trim()) yield currentRow;
                currentRow = '';
                previousDelimiterWasCr = char === '\r';
                continue;
            }

            previousDelimiterWasCr = false;
            currentRow += char;
        }
    }

    if (insideQuotes) {
        throw new Error(`[io] Unterminated quoted CSV record in ${resolveDatasetInputPath(filePath)}`);
    }
    if (currentRow.trim()) yield currentRow;
}

export function parseIndices(s: string): number[] {
    if (!s) return [];
    // Handle JSON-array form "[1,2,3]" as well as bare "1,2,3".
    const stripped = s.trim().replace(/^\[|\]$/g, '');
    if (!stripped) return [];
    return stripped
        .split(',')
        .map((token) => token.trim())
        .filter((token) => /^\d+$/.test(token))
        .map((token) => Number(token))
        .filter((value) => Number.isSafeInteger(value) && value > 0);
}

/**
 * Parse the chain_indx CSV cell into branches.
 *
 * Format (FR-2.2, Phase 2 of uniform_isnad_extraction_20260609):
 *   - Single branch (legacy):   "1,2,3"        -> [[1, 2, 3]]
 *   - Multi-branch (taḥwīl ح):  "1,2,3|4,5,6"  -> [[1, 2, 3], [4, 5, 6]]
 *   - Empty cell:               ""             -> []
 *   - JSON-array legacy form:   "[1,2,3]"      -> [[1, 2, 3]]
 *   - Invalid/non-positive token: rejected as a curation error
 *   - Empty inner branch:       rejected as a curation error
 *
 * Branches are separated by `|`, narrators within a branch by `,`.
 * `teachers_inds` and `students_inds` continue to use the flat `parseIndices`
 * — they never use the `|` delimiter.
 *
 * @returns Array of branches; each branch is an array of scholar_indx ints
 *          in chain order. Empty array when the cell is empty.
 */
export function parseChainIndices(s: string): number[][] {
    if (!s) return [];
    // Strip optional JSON-array wrapping at the outer level only
    // (legacy "[1,2,3]" form). The pipe delimiter is never wrapped.
    const trimmed = s.trim().replace(/^\[|\]$/g, '');
    if (!trimmed) return [];
    return trimmed.split('|').map((branch, branchIdx) => {
        const tokens = branch.split(',').map((token) => token.trim());
        if (tokens.some((token) => token.length === 0)) {
            throw new Error(`[io] Empty chain_indx token in branch ${branchIdx}: ${s}`);
        }
        return tokens.map((token) => {
            if (!/^\d+$/.test(token)) {
                throw new Error(`[io] Invalid chain_indx token "${token}": ${s}`);
            }
            const value = Number(token);
            if (!Number.isSafeInteger(value) || value <= 0) {
                throw new Error(`[io] Invalid chain_indx value "${token}": ${s}`);
            }
            return value;
        });
    });
}

function parseExactSafeIntegerOrNull(s: string | undefined): number | null {
    const token = (s ?? '').trim();
    if (!/^[+-]?\d+$/.test(token)) return null;
    const value = Number(token);
    return Number.isSafeInteger(value) ? value : null;
}

/** Preserve the sign encoded by a source's “BH” (Before Hijra) date text. */
function parseHijriYear(
    rawYear: string | undefined,
    ...dateContext: Array<string | undefined>
): number | null {
    const year = parseExactSafeIntegerOrNull(rawYear);
    if (year === null) return null;
    const isBeforeHijra = [rawYear, ...dateContext].some(
        (value) => /\bBH\b/i.test(value ?? ''),
    );
    return isBeforeHijra ? -Math.abs(year) : year;
}

/** Map a raw CSV row to a typed UnifiedRow with tradition canonicalized. */
function mapUnifiedRow(raw: CSVRow): UnifiedRow {
    // Helper: read a string column, trimming whitespace (handles trailing-space source names etc.)
    const s = (key: string): string => (raw[key] ?? '').trim();
    return {
        dataset_row_id: parseExactSafeIntegerOrNull(raw['id']), // CSV column is `id`, not `dataset_row_id`
        record_id: s('record_id'),
        source_record_id: s('source_record_id'),
        hadith_id: s('hadith_id'),
        hadith_no: s('hadith_no'),
        source: s('source'),
        source_work_id: s('source_work_id'),
        source_display_label: s('source_display_label'),
        tradition: canonicalizeTradition(s('tradition')),
        volume: s('volume'),
        chapter: s('chapter'),
        chapter_no: s('chapter_no'),
        category: s('category'),
        text_ar: s('text_ar'),
        text_en: s('text_en'),                            // CSV column is `text_en`, not `text_english`
        provenance_source: s('provenance_source'),
        translation_status: s('translation_status'),
        translation_source: s('translation_source'),
        translation_model: s('translation_model'),
        translation_review_status: s('translation_review_status'),
        matn_ar: s('matn_ar'),
        matn_en: s('matn_en'),
        sanad: s('sanad'),
        sanad_confidence: s('sanad_confidence'),
        chain_indx: parseChainIndices(s('chain_indx')),
        school: s('school'),
        chain_type: s('chain_type'),
        attributed_to: s('attributed_to'),
        narration_level: s('narration_level'),
        grade_value: s('grade_value'),                    // CSV column is `grade_value`, not `grade`
        grade_tradition: s('grade_tradition'),
        grade_source: s('grade_source'),
        gradings_full: s('gradings_full'),
        url: s('url'),
        page_ref: s('page_ref'),
        _raw: raw,
    };
}

// ─── Public: readUnifiedCsv ───────────────────────────────────────────────────

/**
 * Yield every data record from the unified CSV as a typed UnifiedRow.
 * Uses the multiline-aware parser — Arabic text_ar contains embedded newlines
 * that naive line-splitting would corrupt. Tradition strings are canonicalized.
 */
export async function* readUnifiedCsv(filePath: string): AsyncIterable<UnifiedRow> {
    const parser = new CSVParser();
    for await (const rawRow of readCSVRecords(filePath)) {
        const row = parser.parseRow(rawRow);
        if (row) yield mapUnifiedRow(row);
    }
}

// ─── Public: readAllRawis ─────────────────────────────────────────────────────

function mapRawiRecord(raw: CSVRow): RawiRecord {
    const scholarToken = (raw['scholar_indx'] ?? '').trim();
    const scholar_indx = Number(scholarToken);
    if (!/^\d+$/.test(scholarToken) || !Number.isSafeInteger(scholar_indx) || scholar_indx <= 0) {
        throw new Error(`[io] Invalid scholar_indx in rawis row: ${JSON.stringify(raw)}`);
    }
    return {
        scholar_indx,
        name: raw['name'] ?? '',
        name_english: raw['name_english'] ?? '',
        name_arabic: raw['name_arabic'] ?? '',
        grade: raw['grade'] ?? '',
        bio: raw['bio'] ?? '',
        birth_date_hijri: parseHijriYear(
            raw['birth_date_hijri'],
            raw['birth_date'],
            raw['birth_date_place'],
        ),
        birth_date_hijri_raw: (raw['birth_date_hijri'] ?? '').trim(),
        birth_date_gregorian: parseExactSafeIntegerOrNull(raw['birth_date_gregorian']),
        birth_date_gregorian_raw: (raw['birth_date_gregorian'] ?? '').trim(),
        birth_date_source_text: (raw['birth_date'] ?? '').trim(),
        birth_place: raw['birth_place'] ?? '',
        death_date_hijri: parseHijriYear(
            raw['death_date_hijri'],
            raw['death_date'],
            raw['death_date_place'],
        ),
        death_date_hijri_raw: (raw['death_date_hijri'] ?? '').trim(),
        death_date_gregorian: parseExactSafeIntegerOrNull(raw['death_date_gregorian']),
        death_date_gregorian_raw: (raw['death_date_gregorian'] ?? '').trim(),
        death_date_source_text: (raw['death_date'] ?? '').trim(),
        death_place: raw['death_place'] ?? '',
        death_reason: raw['death_reason'] ?? '',
        teachers_inds: parseIndices(raw['teachers_inds'] ?? ''),
        students_inds: parseIndices(raw['students_inds'] ?? ''),
        geographic_region: raw['geographic_region'] ?? '',
        tabaqah: raw['tabaqah'] ?? '',
    };
}

/**
 * Load all_rawis.csv into an in-memory Map keyed by scholar_indx.
 * The file is small (~24k rows) and is used as a lookup table by all loaders.
 */
export async function readAllRawis(filePath: string): Promise<Map<number, RawiRecord>> {
    const parser = new CSVParser();
    const out = new Map<number, RawiRecord>();
    for await (const rawRow of readCSVRecords(filePath)) {
        const row = parser.parseRow(rawRow);
        if (row) {
            const rawi = mapRawiRecord(row);
            if (out.has(rawi.scholar_indx)) {
                throw new Error(`[io] Duplicate scholar_indx in rawis input: ${rawi.scholar_indx}`);
            }
            out.set(rawi.scholar_indx, rawi);
        }
    }
    return out;
}

// ─── JSONL reader ─────────────────────────────────────────────────────────────

/**
 * Stream a JSONL file line-by-line, yielding parsed objects.
 * Skips blank lines and lines that fail to parse (with a warning).
 */
export async function* readJsonl<T = Record<string, unknown>>(filePath: string): AsyncIterable<T> {
    const input = openDatasetStream(filePath);
    input.setEncoding('utf8');
    const lines = readline.createInterface({ input, crlfDelay: Infinity });
    for await (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
            yield JSON.parse(trimmed) as T;
        } catch (err) {
            console.warn('[io] JSONL parse error, skipping line:', err);
        }
    }
}

// ─── JSONL logger ─────────────────────────────────────────────────────────────

/**
 * Create a JSONL logger that writes to logs/regen-<mode>-<dvId>.jsonl.
 * The logs/ directory is created if it doesn't exist.
 */
export function createRegenLogger(mode: string, dvId: string): RegenLogger {
    const logDir = path.join(process.cwd(), 'logs');
    if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
    }
    const logPath = path.join(logDir, `regen-${mode}-${dvId}.jsonl`);
    const stream = fs.createWriteStream(logPath, { flags: 'a', encoding: 'utf8' });

    return {
        write(entry: Record<string, unknown>): void {
            stream.write(JSON.stringify({ ...entry, _ts: new Date().toISOString() }) + '\n');
        },
        close(): void {
            stream.end();
        },
    };
}
