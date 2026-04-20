/**
 * pipeline.ts
 *
 * Core pipeline logic: for a single hadith, loop through all configured faith
 * traditions, call you.com Research API once per tradition, parse the
 * structured response, and commit any discovered parallel directly to Neo4j.
 *
 * This module is the single source of truth used by both:
 *   - The batch script (src/scripts/find-parallels.ts)
 *   - The Next.js API endpoint (src/app/api/comparative/research/route.ts)
 */

import {
    FAITHS,
    getFaithsByIds,
    buildResearchQuery,
    type FaithConfig,
    type HadithInput,
} from './faith-prompts';
import {
    callYouResearch,
    parseStructuredAssessment,
    embedSourceCitations,
    type ResearchEffort,
} from './you-research-client';
import { commitParallelToNeo4j, type CommitResult } from './neo4j-commit';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HadithRecord extends HadithInput {
    id: string;
}

export interface FaithResult {
    faith_id: string;
    faith_name: string;
    parallel_exists: 'YES' | 'PARTIAL' | 'NO';
    parallel_type: string;
    confidence: string;
    source_reference: string;
    source_title: string;
    isra_status: string;
    motif_tags: string[];
    commit?: CommitResult;       // set if parallel was committed to Neo4j
    skipped?: boolean;           // true if parallel_exists === 'NO'
    error?: string;
}

export interface PipelineOptions {
    /** you.com API key */
    youApiKey: string;
    /** Traditions to process. Defaults to all FAITHS. */
    faithIds?: string[];
    /** you.com research_effort level */
    effort?: ResearchEffort;
    /** Milliseconds to wait between each you.com API call */
    delayMs?: number;
    /** If true, print progress to stdout */
    verbose?: boolean;
}

export interface PipelineResult {
    hadith_id: string;
    hadith_title: string;
    faiths_processed: number;
    parallels_found: number;
    parallels_created: number;
    parallels_updated: number;
    errors: number;
    results: FaithResult[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
}

function log(verbose: boolean, msg: string) {
    if (verbose) process.stdout.write(msg);
}

// ─── Core: process one hadith across all faiths ───────────────────────────────

export async function processHadith(
    hadith: HadithRecord,
    opts: PipelineOptions
): Promise<PipelineResult> {
    const {
        youApiKey,
        faithIds,
        effort = 'standard',
        delayMs = 1500,
        verbose = false,
    } = opts;

    const faithConfigs: FaithConfig[] =
        faithIds && faithIds.length > 0 ? getFaithsByIds(faithIds) : FAITHS;

    const results: FaithResult[] = [];
    let parallelsFound = 0;
    let parallelsCreated = 0;
    let parallelsUpdated = 0;
    let errors = 0;

    for (let i = 0; i < faithConfigs.length; i++) {
        const faith = faithConfigs[i];

        log(verbose, `  [${i + 1}/${faithConfigs.length}] ${faith.name}... `);

        try {
            const query = buildResearchQuery(faith, hadith);
            const truncated =
                query.length > 39_000 ? query.slice(0, 39_000) + '\n\n[truncated]' : query;

            const response = await callYouResearch(truncated, youApiKey, effort);
            const assessment = parseStructuredAssessment(response.content);

            if (assessment.parallel_exists === 'NO') {
                log(verbose, 'no parallel\n');
                results.push({
                    faith_id: faith.id,
                    faith_name: faith.name,
                    parallel_exists: 'NO',
                    parallel_type: 'NONE',
                    confidence: 'LOW',
                    source_reference: '',
                    source_title: '',
                    isra_status: 'NONE',
                    motif_tags: [],
                    skipped: true,
                });
            } else {
                parallelsFound++;

                const enrichedAnalysis = embedSourceCitations(
                    response.content,
                    response.sources
                );

                const commit = await commitParallelToNeo4j({
                    hadith_id: hadith.id,
                    hadith_text_en: hadith.text_english,
                    tradition_name: faith.name,
                    parallel_type: assessment.parallel_type,
                    isra_status: assessment.isra_status,
                    confidence: assessment.confidence,
                    source_title: assessment.source_title,
                    source_reference:
                        assessment.source_reference || `${faith.id}_${hadith.id}`,
                    source_quote: assessment.source_quote,
                    scholarly_analysis: enrichedAnalysis,
                    motif_tags: assessment.motif_tags,
                });

                if (commit.created) parallelsCreated++;
                else parallelsUpdated++;

                log(
                    verbose,
                    `${assessment.parallel_exists} [${assessment.confidence}] ${assessment.source_reference}\n`
                );

                results.push({
                    faith_id: faith.id,
                    faith_name: faith.name,
                    parallel_exists: assessment.parallel_exists,
                    parallel_type: assessment.parallel_type,
                    confidence: assessment.confidence,
                    source_reference: assessment.source_reference,
                    source_title: assessment.source_title,
                    isra_status: assessment.isra_status,
                    motif_tags: assessment.motif_tags,
                    commit,
                });
            }
        } catch (err) {
            const message = (err as Error).message;
            log(verbose, `ERROR: ${message}\n`);
            errors++;
            results.push({
                faith_id: faith.id,
                faith_name: faith.name,
                parallel_exists: 'NO',
                parallel_type: 'NONE',
                confidence: 'LOW',
                source_reference: '',
                source_title: '',
                isra_status: 'NONE',
                motif_tags: [],
                error: message,
            });
        }

        // Delay between calls (skip after last faith)
        if (i < faithConfigs.length - 1) {
            await sleep(delayMs);
        }
    }

    return {
        hadith_id: hadith.id,
        hadith_title: hadith.title,
        faiths_processed: faithConfigs.length,
        parallels_found: parallelsFound,
        parallels_created: parallelsCreated,
        parallels_updated: parallelsUpdated,
        errors,
        results,
    };
}
