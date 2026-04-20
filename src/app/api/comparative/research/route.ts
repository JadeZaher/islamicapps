/**
 * POST /api/comparative/research
 *
 * Runs the comparative parallel pipeline for one or more hadiths.
 * For each hadith it loops through all configured faith traditions, calls
 * you.com Research API, and commits discovered parallels directly to Neo4j.
 *
 * Two modes:
 *
 * 1. Single hadith (from admin UI):
 *    { hadith_id: "..." }
 *
 * 2. Batch (from pipeline invoker — page through with offset):
 *    { batch_size: 5, offset: 0, faiths?: [...] }
 *
 * Optional shared params:
 *    faiths?:       string[]  — tradition IDs; defaults to all 15
 *    effort_level?: string    — lite|standard|deep|exhaustive (default: standard)
 *    delay_ms?:     number    — ms between API calls (default: 1500)
 *
 * Response:
 *    { results, total_created, total_updated, total_errors, next_offset? }
 */

import { NextRequest, NextResponse } from 'next/server';
import { runQuery } from '@/lib/db/neo4j';
import { processHadith, type HadithRecord } from '@/lib/comparative/pipeline';
import type { ResearchEffort } from '@/lib/comparative/you-research-client';

export async function POST(req: NextRequest): Promise<NextResponse> {
    const apiKey = process.env.YOU_API_KEY;
    if (!apiKey) {
        return NextResponse.json(
            { error: 'YOU_API_KEY is not configured on the server.' },
            { status: 500 }
        );
    }

    let body: {
        hadith_id?: string;
        batch_size?: number;
        offset?: number;
        faiths?: string[];
        effort_level?: ResearchEffort;
        delay_ms?: number;
    };

    try {
        body = await req.json();
    } catch {
        return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
    }

    const effortLevel = body.effort_level ?? 'standard';
    const delayMs = body.delay_ms ?? 1500;
    const faithIds = body.faiths ?? [];

    // ── Resolve hadiths to process ────────────────────────────────────────────

    let hadiths: HadithRecord[];

    if (body.hadith_id) {
        // Single hadith mode
        const rows = await runQuery<{
            id: string;
            title: string;
            text_english: string;
            primary_topic: string;
        }>(
            `MATCH (h:Hadith {id: $id})
             WHERE h.text_english IS NOT NULL
             RETURN h.id AS id, h.title AS title, h.text_english AS text_english,
                    h.primary_topic AS primary_topic`,
            { id: body.hadith_id }
        );

        if (!rows.length) {
            return NextResponse.json(
                { error: `Hadith "${body.hadith_id}" not found.` },
                { status: 404 }
            );
        }
        hadiths = rows;
    } else {
        // Batch mode
        const batchSize = Math.min(body.batch_size ?? 5, 20); // cap at 20
        const offset = body.offset ?? 0;

        hadiths = await runQuery<HadithRecord>(
            `MATCH (h:Hadith)
             WHERE h.text_english IS NOT NULL AND h.text_english <> ''
             RETURN h.id AS id, h.title AS title, h.text_english AS text_english,
                    h.primary_topic AS primary_topic
             ORDER BY h.created_at
             SKIP $offset LIMIT $batchSize`,
            { offset, batchSize }
        );

        if (!hadiths.length) {
            return NextResponse.json({
                results: [],
                total_created: 0,
                total_updated: 0,
                total_errors: 0,
                message: 'No hadiths found at this offset.',
            });
        }
    }

    // ── Run pipeline for each hadith ─────────────────────────────────────────

    const allResults = [];
    let totalCreated = 0;
    let totalUpdated = 0;
    let totalErrors = 0;

    for (const hadith of hadiths) {
        const result = await processHadith(hadith, {
            youApiKey: apiKey,
            faithIds,
            effort: effortLevel,
            delayMs,
            verbose: false,
        });

        allResults.push(result);
        totalCreated += result.parallels_created;
        totalUpdated += result.parallels_updated;
        totalErrors += result.errors;
    }

    // ── Compute next offset for pagination ────────────────────────────────────

    const nextOffset =
        !body.hadith_id && hadiths.length === (body.batch_size ?? 5)
            ? (body.offset ?? 0) + hadiths.length
            : null;

    return NextResponse.json({
        results: allResults,
        total_created: totalCreated,
        total_updated: totalUpdated,
        total_errors: totalErrors,
        hadiths_processed: hadiths.length,
        ...(nextOffset !== null && { next_offset: nextOffset }),
    });
}
