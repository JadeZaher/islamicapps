/**
 * neo4j-commit.ts
 *
 * MERGE helpers that write a discovered parallel directly into the Neo4j schema.
 * Idempotent — safe to call multiple times for the same (hadith, tradition, canonical_ref).
 */

import { runWrite } from '@/lib/db/neo4j';
import { randomUUID } from 'crypto';
import type { ParsedParallelType, ParsedIsraStatus, ParsedConfidence } from './you-research-client';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CommitInput {
    hadith_id: string;
    hadith_text_en: string;        // actual English hadith text for the excerpt
    tradition_name: string;        // e.g. "Zoroastrianism"
    parallel_type: ParsedParallelType;
    isra_status: ParsedIsraStatus;
    confidence: ParsedConfidence;
    source_title: string;
    source_reference: string;      // canonical ref — also used as idempotency key
    source_quote: string;          // English passage text
    scholarly_analysis: string;    // full you.com response markdown
    motif_tags: string[];
}

export interface CommitResult {
    parallel_id: string;
    source_id: string;
    tradition_id: string;
    created: boolean;              // false = already existed (idempotent re-run)
}

// ─── Category inference for MotifTag nodes ────────────────────────────────────

type MotifCategory =
    | 'ESCHATOLOGY'
    | 'CREATION'
    | 'PROPHETIC_STORIES'
    | 'LEGAL'
    | 'WISDOM'
    | 'PERSIAN_INFLUENCE'
    | 'COSMOLOGY';

function inferMotifCategory(tagName: string): MotifCategory {
    const t = tagName.toLowerCase();
    if (/eschatol|afterlife|judgment|resurrection|day of|hell|heaven|paradise|barzakh|chinvat/.test(t))
        return 'ESCHATOLOGY';
    if (/creat|genesis|origin|primordial|adam|garden|fall/.test(t))
        return 'CREATION';
    if (/prophet|legend|miracle|story|narrative|moses|noah|sulayman|solomon|david|elijah|enoch/.test(t))
        return 'PROPHETIC_STORIES';
    if (/legal|law|halakha|fiqh|ritual|purity|dietary|marriage|contract/.test(t))
        return 'LEGAL';
    if (/wisdom|proverb|counsel|ethics|virtue|moral/.test(t))
        return 'WISDOM';
    if (/persian|iran|zoroastr|avesta|pahlavi|sassanid/.test(t))
        return 'PERSIAN_INFLUENCE';
    if (/cosm|universe|heavens|earth|sphere|angel|jinn|celestial/.test(t))
        return 'COSMOLOGY';
    return 'WISDOM';
}

// ─── MERGE helpers ────────────────────────────────────────────────────────────

async function mergeTradition(name: string): Promise<string> {
    const rows = await runWrite<{ id: string }>(
        `MERGE (t:ReligiousTradition {name: $name})
         ON CREATE SET t.id = $id, t.created_at = datetime()
         RETURN t.id AS id`,
        { name, id: randomUUID() }
    );
    return rows[0].id;
}

async function mergeSourceText(
    traditionName: string,
    title: string,
    canonicalRef: string,
    textEn: string
): Promise<string> {
    const rows = await runWrite<{ id: string }>(
        `MERGE (s:SourceText {canonical_reference: $canonicalRef})
         ON CREATE SET
           s.id = $id,
           s.title = $title,
           s.tradition_name = $traditionName,
           s.description = $textEn,
           s.created_at = datetime()
         ON MATCH SET
           s.title = $title,
           s.tradition_name = $traditionName
         RETURN s.id AS id`,
        {
            canonicalRef,
            id: randomUUID(),
            title: title || canonicalRef,
            traditionName,
            textEn,
        }
    );
    return rows[0].id;
}

async function mergeMotifTag(tagName: string): Promise<string> {
    const category = inferMotifCategory(tagName);
    const rows = await runWrite<{ id: string }>(
        `MERGE (m:MotifTag {name: $name})
         ON CREATE SET m.id = $id, m.category = $category, m.created_at = datetime()
         RETURN m.id AS id`,
        { name: tagName, id: randomUUID(), category }
    );
    return rows[0].id;
}

// ─── Main commit ──────────────────────────────────────────────────────────────

export async function commitParallelToNeo4j(input: CommitInput): Promise<CommitResult> {
    // Idempotency key: identifies this specific (hadith, tradition, source) triple
    const pipelineKey = `${input.hadith_id}::${input.tradition_name.toUpperCase()}::${input.source_reference}`;

    // 1. Merge tradition node
    const traditionId = await mergeTradition(input.tradition_name);

    // 2. Merge source text node
    const sourceId = await mergeSourceText(
        input.tradition_name,
        input.source_title,
        input.source_reference,
        input.source_quote
    );

    // 3. Link source text → tradition
    await runWrite(
        `MATCH (s:SourceText {id: $sourceId})
         MATCH (t:ReligiousTradition {id: $traditionId})
         MERGE (s)-[:BELONGS_TO]->(t)`,
        { sourceId, traditionId }
    );

    // 4. Merge CrossCulturalParallel node (idempotent on pipeline_key)
    const parallelId = randomUUID();
    const rows = await runWrite<{ id: string; created: boolean }>(
        `MERGE (p:CrossCulturalParallel {pipeline_key: $pipelineKey})
         ON CREATE SET
           p.id = $id,
           p.pipeline_key = $pipelineKey,
           p.parallel_type = $parallelType,
           p.isra_iliyyat_status = $israStatus,
           p.confidence_level = $confidence,
           p.hadith_excerpt_en = $hadithExcerpt,
           p.source_text_original = $sourceRef,
           p.source_text_en = $sourceQuote,
           p.scholarly_analysis = $analysis,
           p.created_at = datetime()
         ON MATCH SET
           p.parallel_type = $parallelType,
           p.isra_iliyyat_status = $israStatus,
           p.confidence_level = $confidence,
           p.hadith_excerpt_en = $hadithExcerpt,
           p.source_text_original = $sourceRef,
           p.source_text_en = $sourceQuote,
           p.scholarly_analysis = $analysis,
           p.updated_at = datetime()
         RETURN p.id AS id, (p.created_at = p.updated_at OR p.updated_at IS NULL) AS created`,
        {
            pipelineKey,
            id: parallelId,
            parallelType: input.parallel_type,
            israStatus: input.isra_status,
            confidence: input.confidence,
            hadithExcerpt: input.hadith_text_en,
            sourceRef: input.source_reference,
            sourceQuote: input.source_quote,
            analysis: input.scholarly_analysis,
        }
    );

    const committedId = rows[0]?.id ?? parallelId;
    const wasCreated = rows[0]?.created ?? true;

    // 5. Link Hadith → CrossCulturalParallel
    await runWrite(
        `MATCH (h:Hadith {id: $hadithId})
         MATCH (p:CrossCulturalParallel {pipeline_key: $pipelineKey})
         MERGE (h)-[:HAS_PARALLEL]->(p)`,
        { hadithId: input.hadith_id, pipelineKey }
    );

    // 6. Link CrossCulturalParallel → SourceText
    await runWrite(
        `MATCH (p:CrossCulturalParallel {pipeline_key: $pipelineKey})
         MATCH (s:SourceText {id: $sourceId})
         MERGE (p)-[:PARALLELS]->(s)`,
        { pipelineKey, sourceId }
    );

    // 7. Link CrossCulturalParallel → ReligiousTradition
    await runWrite(
        `MATCH (p:CrossCulturalParallel {pipeline_key: $pipelineKey})
         MATCH (t:ReligiousTradition {id: $traditionId})
         MERGE (p)-[:FROM_TRADITION]->(t)`,
        { pipelineKey, traditionId }
    );

    // 8. Merge and link motif tags
    for (const tag of input.motif_tags) {
        if (!tag.trim()) continue;
        const tagId = await mergeMotifTag(tag.trim());
        await runWrite(
            `MATCH (p:CrossCulturalParallel {pipeline_key: $pipelineKey})
             MATCH (m:MotifTag {id: $tagId})
             MERGE (p)-[:TAGGED_WITH]->(m)`,
            { pipelineKey, tagId }
        );
    }

    return {
        parallel_id: committedId,
        source_id: sourceId,
        tradition_id: traditionId,
        created: wasCreated,
    };
}
