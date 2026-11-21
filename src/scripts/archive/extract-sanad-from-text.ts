/**
 * extract-sanad-from-text.ts
 *
 * For :Hadith nodes where `sanad` is empty but `text_ar` begins with a
 * classical isnad marker (e.g. "حدثنا" / "أخبرنا"), extract the isnad
 * portion of text_ar (everything before the matn) and write it to
 * `h.sanad`, plus provenance properties:
 *
 *   h.sanad_extraction_method = 'regex_v1'
 *   h.sanad_extracted_at      = datetime()
 *
 * Idempotent: only writes when sanad is currently NULL or empty. Never
 * overwrites a sanad value that was loaded from the source CSV.
 *
 * Why this exists
 * ---------------
 * The v2 unified CSV has dedicated `sanad` and `matn_ar` columns, but the
 * upstream extractor only populated them for some rows. For ~30% of
 * Sahih Bukhari, ~48% of Sunan an-Nasa'i, and similar shares of Muslim,
 * Ibn Majah, Abi Dawud, and Tirmidhi, the sanad column is empty even
 * though the full isnad is plainly visible inside `text_ar`. This script
 * recovers those rows without touching the original CSV.
 *
 * Approach (intentionally conservative)
 * -------------------------------------
 * 1. Require text_ar to start with an isnad opener
 *    (حدثنا | أخبرنا | حدثني | أخبرني | أنبأنا | نا | ثنا).
 * 2. Find the earliest matn-onset marker: a Prophet mention, an "X said"
 *    that begins direct speech, or a quotation-mark opener after a verb
 *    of report.
 * 3. The slice [0..matn_onset) is the sanad text; trim trailing punctuation.
 * 4. Only persist when the extracted sanad is at least 20 chars AND less
 *    than 70% of the total text_ar length (to avoid pathological splits).
 *
 * Run modes
 * ---------
 *   npx tsx src/scripts/extract-sanad-from-text.ts --dry-run [--limit=20] [--source="Sahih Bukhari"]
 *   npx tsx src/scripts/extract-sanad-from-text.ts                  # writes to DB
 *
 * The --dry-run mode prints extracted samples without touching the DB.
 */

import 'dotenv/config';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

// ─── Regex patterns ──────────────────────────────────────────────────────────

/** Hadith text must begin with one of these to qualify as having an isnad. */
const ISNAD_START = /^\s*(?:حدثنا|أخبرنا|حدثني|أخبرني|أنبأنا|نا\s|ثنا\s)/;

/**
 * Markers that indicate the matn (narrative content) is beginning.
 *
 * High-precision set: ONLY the Prophet-mention and reported-speech-opener
 * patterns. We deliberately exclude bare "أنه قال" / "أنها قالت" because
 * those false-positive into mid-matn cases (a Companion is reported to have
 * said something inside the matn body) and false-negative when a chain has
 * "X أخبره عن Y" structures that look identical to matn-onset.
 *
 * Net effect: ~20-30% extraction rate on Bukhari/Sunan rows, but the rows
 * that DO extract are clean. A Phase-2 LLM-assisted extractor is planned
 * for the remaining ~70% (which include Companion-narration patterns,
 * mursal/maqtū' chains, and abbreviated continuation isnads).
 */
const MATN_MARKERS: RegExp[] = [
    // Prophet-mentions (the most reliable boundary — these are the most
    // common matn openers across the Sunni canon)
    /(?:أنّ|أن|قال|قالت|سمعت)\s+(?:النبيّ|النبي|رسولَ?\s+اللهِ?|رسول\s+اللَّه|الرسول)/,
    // Quoted speech opener right after a verb of report. The « / " quote
    // chars in Arabic hadith texts almost always wrap a matn body.
    /(?:قال|قالت|قلت)\s*[:،]?\s*[«""؟"‏]?\s*[«""]/,
    // Whitespace then opening Arabic quotation mark (some texts use the
    // ornamental ‏"‏ form widely)
    /\s‏"‏/,
];

// ─── Extractor ───────────────────────────────────────────────────────────────

export interface ExtractionResult {
    sanad: string | null;
    /** Why extraction failed (or 'ok' on success). */
    reason: 'ok' | 'no_isnad_marker' | 'no_matn_marker' | 'too_short' | 'too_long';
    /** Index where the matn was detected to start (for debugging). */
    matn_onset?: number;
}

export function extractSanad(text_ar: string): ExtractionResult {
    if (!text_ar || !ISNAD_START.test(text_ar)) {
        return { sanad: null, reason: 'no_isnad_marker' };
    }
    let earliest = -1;
    for (const re of MATN_MARKERS) {
        const m = re.exec(text_ar);
        if (m && (earliest === -1 || m.index < earliest)) {
            earliest = m.index;
        }
    }
    if (earliest === -1) {
        return { sanad: null, reason: 'no_matn_marker' };
    }
    let sanad = text_ar.slice(0, earliest).trim();
    // Strip trailing comma/punctuation
    sanad = sanad.replace(/[،,\s]+$/, '');
    if (sanad.length < 20) {
        return { sanad: null, reason: 'too_short', matn_onset: earliest };
    }
    if (sanad.length > text_ar.length * 0.7) {
        // Suspicious — matn was probably misdetected somewhere deep in
        // text_ar that isn't the real matn boundary. Bail out.
        return { sanad: null, reason: 'too_long', matn_onset: earliest };
    }
    return { sanad, reason: 'ok', matn_onset: earliest };
}

// ─── Main ────────────────────────────────────────────────────────────────────

interface CliArgs {
    dryRun: boolean;
    limit: number | null;
    source: string | null;
}

function parseArgs(argv: string[]): CliArgs {
    const args: CliArgs = { dryRun: false, limit: null, source: null };
    for (const a of argv) {
        if (a === '--dry-run') args.dryRun = true;
        else if (a.startsWith('--limit=')) args.limit = parseInt(a.slice('--limit='.length), 10);
        else if (a.startsWith('--source=')) args.source = a.slice('--source='.length);
    }
    return args;
}

async function fetchCandidates(opts: { source: string | null; limit: number | null }) {
    const where = `(h.sanad IS NULL OR h.sanad = '')
                   AND h.text_ar IS NOT NULL AND h.text_ar <> ''
                   AND NOT coalesce(h.tombstoned, false)`;
    const sourceFilter = opts.source ? ` AND h.source = $source` : '';
    const limit = opts.limit ? ` LIMIT ${Math.max(1, Math.floor(opts.limit))}` : '';
    const cypher = `
        MATCH (h:Hadith)
        WHERE ${where}${sourceFilter}
        RETURN h.id AS id, h.source AS source, h.hadith_no AS hadith_no, h.text_ar AS text_ar
        ${limit}
    `;
    return runQuery<{ id: string; source: string; hadith_no: string; text_ar: string }>(
        cypher,
        opts.source ? { source: opts.source } : {},
    );
}

async function main(): Promise<void> {
    const args = parseArgs(process.argv.slice(2));
    console.log('[extract-sanad] mode=' + (args.dryRun ? 'DRY-RUN' : 'WRITE'),
        '  limit=' + (args.limit ?? 'none'),
        '  source=' + (args.source ?? 'all'));

    const candidates = await fetchCandidates({ source: args.source, limit: args.limit });
    console.log(`[extract-sanad] ${candidates.length} candidate rows (empty sanad, non-empty text_ar)`);

    const stats = {
        scanned: 0,
        ok: 0,
        no_isnad_marker: 0,
        no_matn_marker: 0,
        too_short: 0,
        too_long: 0,
        written: 0,
        errors: 0,
    };

    const samples: Array<{ id: string; source: string; hadith_no: string; sanad: string; full_text_excerpt: string }> = [];

    for (const row of candidates) {
        stats.scanned++;
        const result = extractSanad(row.text_ar);
        stats[result.reason]++;
        if (result.reason === 'ok' && result.sanad) {
            if (args.dryRun && samples.length < 15) {
                samples.push({
                    id: row.id,
                    source: row.source,
                    hadith_no: row.hadith_no,
                    sanad: result.sanad,
                    full_text_excerpt: row.text_ar.slice(0, 250),
                });
            }
            if (!args.dryRun) {
                try {
                    await runWrite(
                        `MATCH (h:Hadith {id: $id})
                         WHERE h.sanad IS NULL OR h.sanad = ''
                         SET h.sanad = $sanad,
                             h.sanad_extraction_method = 'regex_v1',
                             h.sanad_extracted_at = datetime()`,
                        { id: row.id, sanad: result.sanad },
                    );
                    stats.written++;
                } catch (err) {
                    stats.errors++;
                    if (stats.errors < 5) console.error(`[extract-sanad] write error for ${row.id}: ${err}`);
                }
            }
        }
        if (stats.scanned % 500 === 0) {
            console.log(`[extract-sanad] progress: scanned=${stats.scanned} ok=${stats.ok} no_isnad=${stats.no_isnad_marker} no_matn=${stats.no_matn_marker} written=${stats.written}`);
        }
    }

    console.log('\n' + '='.repeat(70));
    console.log('  extract-sanad-from-text — results');
    console.log('='.repeat(70));
    console.log(`  scanned:           ${stats.scanned}`);
    console.log(`  ok (extractable):  ${stats.ok}   (${pct(stats.ok, stats.scanned)})`);
    console.log(`  no isnad marker:   ${stats.no_isnad_marker}`);
    console.log(`  no matn marker:    ${stats.no_matn_marker}`);
    console.log(`  too short:         ${stats.too_short}`);
    console.log(`  too long:          ${stats.too_long}`);
    console.log(`  written to DB:     ${stats.written}`);
    console.log(`  errors:            ${stats.errors}`);

    if (args.dryRun && samples.length > 0) {
        console.log('\n  --- DRY-RUN samples ---');
        for (const s of samples) {
            console.log(`\n  ${s.source} #${s.hadith_no || '?'}  (id=${s.id})`);
            console.log(`    text_ar (250 chars): ${s.full_text_excerpt}`);
            console.log(`    extracted sanad:     ${s.sanad}`);
        }
    }

    await closeDriver();
    if (stats.errors > 0) process.exitCode = 1;
}

function pct(n: number, d: number): string {
    if (d === 0) return '0.0%';
    return ((100 * n) / d).toFixed(1) + '%';
}

main().catch(async (err) => {
    console.error('[extract-sanad] fatal:', err);
    try { await closeDriver(); } catch {}
    process.exitCode = 1;
});
