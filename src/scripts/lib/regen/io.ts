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

// ─── Shared types (canonical surface consumed by all regen modules) ──────────

export type Tradition = 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';

/** One row from all_hadiths_unified.csv */
export interface UnifiedRow {
    /** From CSV `id` column — the canonical dataset_row_id. */
    dataset_row_id: number | null;
    /** From CSV `hadith_id` — source-specific original ID (may differ from dataset_row_id). */
    hadith_id: string;
    hadith_no: string;
    source: string;
    /** Canonical tradition string — already canonicalized by the reader. */
    tradition: Tradition;
    volume: string;
    chapter: string;
    chapter_no: string;
    category: string;
    text_ar: string;
    text_en: string;
    matn_ar: string;
    matn_en: string;
    /** Narrator names in sanad field (free text, not yet resolved). */
    sanad: string;
    sanad_confidence: string;
    /** Parsed numeric chain indices — may be empty. */
    chain_indx: number[];
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
    death_date_hijri: number | null;
    death_date_gregorian: number | null;
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
    return TRADITION_MAP[key] ?? 'Sunni';
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
            this.headers = this.parseCSVLine(line);
            this.isFirstLine = false;
            return null;
        }
        const values = this.parseCSVLine(line);
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

function splitCSVRecords(content: string): string[] {
    const rows: string[] = [];
    let currentRow = '';
    let insideQuotes = false;
    for (let i = 0; i < content.length; i++) {
        const char = content[i];
        if (char === '"') insideQuotes = !insideQuotes;
        if ((char === '\n' || char === '\r') && !insideQuotes) {
            if (char === '\r' && content[i + 1] === '\n') i++;
            if (currentRow.trim()) rows.push(currentRow);
            currentRow = '';
        } else {
            currentRow += char;
        }
    }
    if (currentRow.trim()) rows.push(currentRow);
    return rows;
}

function parseIndices(s: string): number[] {
    if (!s) return [];
    // Handle JSON-array form "[1,2,3]" as well as bare "1,2,3".
    const stripped = s.trim().replace(/^\[|\]$/g, '');
    if (!stripped) return [];
    return stripped
        .split(',')
        .map((t) => parseInt(t.trim(), 10))
        .filter((n) => !isNaN(n));
}

function parseIntOrNull(s: string | undefined): number | null {
    const v = parseInt((s ?? '').trim(), 10);
    return isNaN(v) ? null : v;
}

/** Map a raw CSV row to a typed UnifiedRow with tradition canonicalized. */
function mapUnifiedRow(raw: CSVRow): UnifiedRow {
    // Helper: read a string column, trimming whitespace (handles trailing-space source names etc.)
    const s = (key: string): string => (raw[key] ?? '').trim();
    return {
        dataset_row_id: parseIntOrNull(raw['id']),        // CSV column is `id`, not `dataset_row_id`
        hadith_id: s('hadith_id'),
        hadith_no: s('hadith_no'),
        source: s('source'),
        tradition: canonicalizeTradition(s('tradition')),
        volume: s('volume'),
        chapter: s('chapter'),
        chapter_no: s('chapter_no'),
        category: s('category'),
        text_ar: s('text_ar'),
        text_en: s('text_en'),                            // CSV column is `text_en`, not `text_english`
        matn_ar: s('matn_ar'),
        matn_en: s('matn_en'),
        sanad: s('sanad'),
        sanad_confidence: s('sanad_confidence'),
        chain_indx: parseIndices(s('chain_indx')),
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
    const content = fs.readFileSync(filePath, 'utf8');
    const rawRows = splitCSVRecords(content);
    const parser = new CSVParser();
    for (const rawRow of rawRows) {
        let row: CSVRow | null = null;
        try {
            row = parser.parseRow(rawRow);
        } catch (err) {
            console.error('[io] CSV parse error, skipping row:', err);
        }
        if (row) yield mapUnifiedRow(row);
    }
}

// ─── Public: readAllRawis ─────────────────────────────────────────────────────

function mapRawiRecord(raw: CSVRow): RawiRecord {
    const scholar_indx = parseIntOrNull(raw['scholar_indx']);
    if (scholar_indx === null) {
        throw new Error(`[io] Invalid scholar_indx in rawis row: ${JSON.stringify(raw)}`);
    }
    return {
        scholar_indx,
        name: raw['name'] ?? '',
        name_english: raw['name_english'] ?? raw['name'] ?? '',
        name_arabic: raw['name_arabic'] ?? '',
        grade: raw['grade'] ?? '',
        bio: raw['bio'] ?? '',
        death_date_hijri: parseIntOrNull(raw['death_date_hijri']),
        death_date_gregorian: parseIntOrNull(raw['death_date_gregorian']),
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
    const content = fs.readFileSync(filePath, 'utf8');
    const rawRows = splitCSVRecords(content);
    const parser = new CSVParser();
    const out = new Map<number, RawiRecord>();
    for (const rawRow of rawRows) {
        let row: CSVRow | null = null;
        try {
            row = parser.parseRow(rawRow);
        } catch (err) {
            console.error('[io] rawis CSV parse error, skipping row:', err);
        }
        if (row) {
            try {
                const rawi = mapRawiRecord(row);
                out.set(rawi.scholar_indx, rawi);
            } catch (err) {
                console.warn('[io] Skipping malformed rawis row:', err);
            }
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
    const content = fs.readFileSync(filePath, 'utf8');
    for (const line of content.split('\n')) {
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
