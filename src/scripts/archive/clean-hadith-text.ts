// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * clean-hadith-text.ts
 * ====================
 * Cleans hadith texts in Neo4j for vector embedding readiness.
 *
 * Phases:
 *   1. Flag AI refusal artifacts in English translations
 *   2. Clean OCR numeric artifacts in Arabic text
 *   3. Flag very short Arabic texts for embedding skip
 *   4. Create normalized Arabic text for all hadiths
 *
 * Usage: npx tsx src/scripts/clean-hadith-text.ts
 */

import neo4j from 'neo4j-driver';
import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── Summary counters ────────────────────────────────────────────────────────

const summary = {
    refusalsFlagged: 0,
    ocrTextsCleaned: 0,
    shortTextsFlagged: 0,
    textsNormalized: 0,
};

// ─── Phase 1: Flag AI Refusal Artifacts ──────────────────────────────────────

async function phase1FlagRefusals(): Promise<void> {
    console.log('\n========================================');
    console.log('  Phase 1: Flag AI Refusal Artifacts');
    console.log('========================================');

    const result = await runWrite<{ flagged: number }>(
        `MATCH (h:Hadith)
         WHERE h.text_english IS NOT NULL
           AND (h.text_english CONTAINS 'I cannot'
             OR h.text_english CONTAINS "I can't"
             OR h.text_english CONTAINS "I'm unable"
             OR h.text_english CONTAINS 'I cannot create'
             OR h.text_english CONTAINS 'I cannot fulfill'
             OR h.text_english CONTAINS 'I cannot translate')
         SET h.text_english_needs_retranslation = true
         RETURN count(h) AS flagged`
    );

    summary.refusalsFlagged = Number(result[0]?.flagged ?? 0);
    console.log(`  Flagged ${summary.refusalsFlagged} hadiths with AI refusal artifacts`);
}

// ─── Phase 2: Clean OCR Numeric Artifacts in Arabic Text ─────────────────────

function cleanArabicOCR(text: string): string {
    // Remove footnote markers like (1), (2), etc.
    let cleaned = text.replace(/\(\s*\d+\s*\)/g, '');
    // Remove Arabic-numeral footnote markers like (١), (٢), etc.
    cleaned = cleaned.replace(/\(\s*[٠-٩]+\s*\)/g, '');
    // Remove reversed Arabic footnote markers like )١(
    cleaned = cleaned.replace(/\)\s*[٠-٩]+\s*\(/g, '');
    // Remove standalone 3+ digit sequences (likely page numbers)
    cleaned = cleaned.replace(/(?<!\S)\d{3,}(?!\S)/g, '');
    // Remove standalone 3+ Arabic digit sequences
    cleaned = cleaned.replace(/(?<!\S)[٠-٩]{3,}(?!\S)/g, '');
    // Remove stray single/double Latin chars (but preserve actual Arabic text)
    cleaned = cleaned.replace(/(?<![a-zA-Z])[a-zA-Z]{1,2}(?![a-zA-Z])/g, '');
    // Collapse multiple spaces
    cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();
    return cleaned;
}

async function phase2CleanOCR(): Promise<void> {
    console.log('\n========================================');
    console.log('  Phase 2: Clean OCR Artifacts in Arabic');
    console.log('========================================');

    const BATCH_SIZE = 500;
    let totalCleaned = 0;
    let offset = 0;

    while (true) {
        // Fetch a batch of hadiths with numeric sequences in Arabic text
        const batch = await runQuery<{ id: string; text: string }>(
            `MATCH (h:Hadith)
             WHERE h.text_arabic IS NOT NULL
               AND h.text_arabic =~ '.*[0-9]{3,}.*'
               AND h.text_arabic_raw IS NULL
             RETURN h.id AS id, h.text_arabic AS text
             SKIP $offset LIMIT $limit`,
            { offset: neo4j.int(offset), limit: neo4j.int(BATCH_SIZE) }
        );

        if (batch.length === 0) break;

        // Clean in JS and prepare batch updates
        const updates: { id: string; raw: string; cleaned: string }[] = [];
        for (const row of batch) {
            const cleaned = cleanArabicOCR(row.text);
            if (cleaned !== row.text) {
                updates.push({ id: row.id, raw: row.text, cleaned });
            }
        }

        if (updates.length > 0) {
            await runWrite(
                `UNWIND $updates AS u
                 MATCH (h:Hadith {id: u.id})
                 SET h.text_arabic_raw = u.raw,
                     h.text_arabic = u.cleaned`,
                { updates }
            );
            totalCleaned += updates.length;
            console.log(`  Batch at offset ${offset}: cleaned ${updates.length}/${batch.length}`);
        } else {
            console.log(`  Batch at offset ${offset}: 0/${batch.length} needed cleaning`);
        }

        // If batch was smaller than limit, we're done
        if (batch.length < BATCH_SIZE) break;
        offset += BATCH_SIZE;
    }

    // Also handle hadiths that already had text_arabic_raw backed up (re-run safe)
    // Query those that still have numeric sequences but already have a backup
    const alreadyBacked = await runQuery<{ id: string; text: string }>(
        `MATCH (h:Hadith)
         WHERE h.text_arabic IS NOT NULL
           AND h.text_arabic =~ '.*[0-9]{3,}.*'
           AND h.text_arabic_raw IS NOT NULL
         RETURN h.id AS id, h.text_arabic AS text`
    );

    if (alreadyBacked.length > 0) {
        const updates: { id: string; cleaned: string }[] = [];
        for (const row of alreadyBacked) {
            const cleaned = cleanArabicOCR(row.text);
            if (cleaned !== row.text) {
                updates.push({ id: row.id, cleaned });
            }
        }

        if (updates.length > 0) {
            // Process in batches
            for (let i = 0; i < updates.length; i += BATCH_SIZE) {
                const chunk = updates.slice(i, i + BATCH_SIZE);
                await runWrite(
                    `UNWIND $updates AS u
                     MATCH (h:Hadith {id: u.id})
                     SET h.text_arabic = u.cleaned`,
                    { updates: chunk }
                );
            }
            totalCleaned += updates.length;
            console.log(`  Re-cleaned ${updates.length} previously backed-up hadiths`);
        }
    }

    summary.ocrTextsCleaned = totalCleaned;
    console.log(`  Total OCR texts cleaned: ${totalCleaned}`);
}

// ─── Phase 3: Flag Very Short Texts ─────────────────────────────────────────

async function phase3FlagShortTexts(): Promise<void> {
    console.log('\n========================================');
    console.log('  Phase 3: Flag Very Short Arabic Texts');
    console.log('========================================');

    const result = await runWrite<{ flagged: number }>(
        `MATCH (h:Hadith)
         WHERE h.text_arabic IS NOT NULL
           AND size(h.text_arabic) > 0
           AND size(h.text_arabic) < 20
         SET h.embedding_skip = true
         RETURN count(h) AS flagged`
    );

    summary.shortTextsFlagged = Number(result[0]?.flagged ?? 0);
    console.log(`  Flagged ${summary.shortTextsFlagged} very short texts for embedding skip`);
}

// ─── Phase 4: Create Normalized Arabic Text ──────────────────────────────────

function normalizeArabic(text: string): string {
    if (!text) return '';
    // Remove harakat (diacritics)
    let normalized = text.replace(/[\u064B-\u0652]/g, '');
    // Normalize alif variants
    normalized = normalized.replace(/[\u0623\u0625\u0622]/g, '\u0627');
    // Normalize ta marbuta to ha
    normalized = normalized.replace(/\u0629/g, '\u0647');
    // Normalize alif maqsura to ya
    normalized = normalized.replace(/\u0649/g, '\u064A');
    // Collapse whitespace
    normalized = normalized.replace(/\s+/g, ' ').trim();
    return normalized;
}

async function phase4NormalizeArabic(): Promise<void> {
    console.log('\n========================================');
    console.log('  Phase 4: Normalize Arabic Text');
    console.log('========================================');

    const BATCH_SIZE = 1000;
    let totalNormalized = 0;
    let offset = 0;

    while (true) {
        // Stream batch: query hadiths that need normalization
        const batch = await runQuery<{ id: string; text: string }>(
            `MATCH (h:Hadith)
             WHERE h.text_arabic IS NOT NULL
               AND size(h.text_arabic) > 0
               AND h.text_arabic_normalized IS NULL
             RETURN h.id AS id, h.text_arabic AS text
             LIMIT $limit`,
            { limit: neo4j.int(BATCH_SIZE) }
        );

        if (batch.length === 0) break;

        // Normalize in JS
        const updates: { id: string; normalized: string }[] = [];
        for (const row of batch) {
            const normalized = normalizeArabic(row.text);
            if (normalized.length > 0) {
                updates.push({ id: row.id, normalized });
            }
        }

        if (updates.length > 0) {
            await runWrite(
                `UNWIND $updates AS u
                 MATCH (h:Hadith {id: u.id})
                 SET h.text_arabic_normalized = u.normalized`,
                { updates }
            );
            totalNormalized += updates.length;
        }

        if (totalNormalized % 5000 === 0 || batch.length < BATCH_SIZE) {
            console.log(`  Normalized ${totalNormalized} texts so far...`);
        }

        if (batch.length < BATCH_SIZE) break;
    }

    summary.textsNormalized = totalNormalized;
    console.log(`  Total texts normalized: ${totalNormalized}`);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
    console.log('==============================================');
    console.log('  Hadith Text Cleanup for Embedding Readiness');
    console.log('==============================================');

    const start = Date.now();

    await phase1FlagRefusals();
    await phase2CleanOCR();
    await phase3FlagShortTexts();
    await phase4NormalizeArabic();

    const elapsed = ((Date.now() - start) / 1000).toFixed(1);

    console.log('\n========================================');
    console.log('  SUMMARY');
    console.log('========================================');
    console.log(`  AI refusals flagged:        ${summary.refusalsFlagged}`);
    console.log(`  OCR texts cleaned:          ${summary.ocrTextsCleaned}`);
    console.log(`  Short texts flagged (skip):  ${summary.shortTextsFlagged}`);
    console.log(`  Arabic texts normalized:     ${summary.textsNormalized}`);
    console.log(`  Elapsed: ${elapsed}s`);
    console.log('========================================\n');

    await closeDriver();
}

main().catch((err) => {
    console.error('Fatal error:', err);
    process.exit(1);
});
