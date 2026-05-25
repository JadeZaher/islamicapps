'use server';

import { runQuery, runWrite, runTransaction } from '@/lib/db/neo4j';
import { randomUUID } from 'crypto';
import { type PaginationParams, type PaginatedResult, toSkipLimit, paginate } from '@/lib/pagination';

// ============ TYPES ============

export type ParallelType =
    | 'CONDEMNATION'
    | 'CULTURAL_BLEED'
    | 'SHARED_SOURCE'
    | 'DIRECT_BORROWING'
    | 'APOLOGETIC'
    | 'DISPUTED';

export type IsraIliyyatStatus = 'MUWAFIQ' | 'MUKHALIF' | 'MASKUT_ANHU' | 'NONE';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type MotifCategory =
    | 'ESCHATOLOGY'
    | 'CREATION'
    | 'PROPHETIC_STORIES'
    | 'LEGAL'
    | 'WISDOM'
    | 'PERSIAN_INFLUENCE'
    | 'COSMOLOGY';

export interface ReligiousTraditionData {
    name: string;
    name_arabic?: string;
    description?: string;
    geographic_heartlands?: string[];
}

export interface SourceTextData {
    title: string;
    title_original?: string;
    tradition_name: string;
    author?: string;
    approximate_date_ce?: string;
    canonical_reference?: string;
    description?: string;
}

export interface CrossCulturalParallelData {
    hadith_id: string;
    source_text_id: string;
    tradition_id: string;
    parallel_type: ParallelType;
    isra_iliyyat_status?: IsraIliyyatStatus;
    confidence_level?: ConfidenceLevel;
    hadith_excerpt_en?: string;
    source_text_original?: string;
    source_text_en?: string;
    scholarly_analysis?: string;
    motif_tag_ids?: string[];
}

export interface MotifTagData {
    name: string;
    category: MotifCategory;
    description?: string;
}

// ============ RELIGIOUS TRADITIONS ============

export async function createReligiousTradition(data: ReligiousTraditionData): Promise<string> {
    const id = randomUUID();
    await runWrite(`
        CREATE (t:ReligiousTradition {
            id: $id,
            name: $name,
            name_arabic: $name_arabic,
            description: $description,
            geographic_heartlands: $geographic_heartlands,
            created_at: datetime()
        })
    `, {
        id,
        name: data.name,
        name_arabic: data.name_arabic || null,
        description: data.description || null,
        geographic_heartlands: data.geographic_heartlands || [],
    });
    return id;
}

export async function getAllTraditions() {
    const result = await runQuery(`
        MATCH (t:ReligiousTradition)
        OPTIONAL MATCH (s:SourceText)-[:BELONGS_TO]->(t)
        OPTIONAL MATCH (n:Narrator)-[:TRANSMITTER_OF_TRADITION]->(t)
        RETURN t, count(DISTINCT s) as source_count, count(DISTINCT n) as narrator_count
        ORDER BY t.name
    `);
    return result.map((r) => ({
        ...r.t.properties,
        source_count: r.source_count,
        narrator_count: r.narrator_count,
    }));
}

export async function deleteTradition(traditionId: string): Promise<void> {
    await runWrite(`MATCH (t:ReligiousTradition {id: $traditionId}) DETACH DELETE t`, { traditionId });
}

export async function updateTradition(traditionId: string, data: Partial<ReligiousTraditionData>): Promise<void> {
    const updateData = {
        ...data,
        geographic_heartlands: data.geographic_heartlands || undefined,
    };
    const setClause = Object.keys(updateData)
        .filter((k) => updateData[k as keyof typeof updateData] !== undefined)
        .map((k) => `t.${k} = $${k}`)
        .join(', ');
    if (!setClause) return;
    await runWrite(`MATCH (t:ReligiousTradition {id: $traditionId}) SET ${setClause}`, { traditionId, ...updateData });
}

// ============ SOURCE TEXTS ============

export async function createSourceText(data: SourceTextData): Promise<string> {
    const id = randomUUID();
    await runWrite(`
        CREATE (s:SourceText {
            id: $id,
            title: $title,
            title_original: $title_original,
            tradition_name: $tradition_name,
            author: $author,
            approximate_date_ce: $approximate_date_ce,
            canonical_reference: $canonical_reference,
            description: $description,
            created_at: datetime()
        })
    `, {
        id,
        title: data.title,
        title_original: data.title_original || null,
        tradition_name: data.tradition_name,
        author: data.author || null,
        approximate_date_ce: data.approximate_date_ce || null,
        canonical_reference: data.canonical_reference || null,
        description: data.description || null,
    });
    return id;
}

export async function linkSourceTextToTradition(sourceTextId: string, traditionId: string): Promise<void> {
    await runWrite(`
        MATCH (s:SourceText {id: $sourceTextId})
        MATCH (t:ReligiousTradition {id: $traditionId})
        MERGE (s)-[:BELONGS_TO]->(t)
    `, { sourceTextId, traditionId });
}

export async function getAllSourceTexts(filters?: { tradition_name?: string }) {
    let query = `
        MATCH (s:SourceText)
        OPTIONAL MATCH (s)-[:BELONGS_TO]->(t:ReligiousTradition)
    `;
    const params: Record<string, any> = {};
    if (filters?.tradition_name) {
        query += ` WHERE s.tradition_name = $tradition_name`;
        params.tradition_name = filters.tradition_name;
    }
    query += ` RETURN s, t ORDER BY s.tradition_name, s.title`;
    const result = await runQuery(query, params);
    return result.map((r) => ({
        ...r.s.properties,
        tradition: r.t?.properties || null,
    }));
}

export async function deleteSourceText(sourceTextId: string): Promise<void> {
    await runWrite(`MATCH (s:SourceText {id: $sourceTextId}) DETACH DELETE s`, { sourceTextId });
}

export async function updateSourceText(sourceTextId: string, data: Partial<SourceTextData>): Promise<void> {
    const setClause = Object.keys(data).map((k) => `s.${k} = $${k}`).join(', ');
    if (!setClause) return;
    await runWrite(`MATCH (s:SourceText {id: $sourceTextId}) SET ${setClause}`, { sourceTextId, ...data });
}

// ============ MOTIF TAGS ============

export async function createMotifTag(data: MotifTagData): Promise<string> {
    const id = randomUUID();
    await runWrite(`
        CREATE (m:MotifTag {
            id: $id,
            name: $name,
            category: $category,
            description: $description,
            created_at: datetime()
        })
    `, {
        id,
        name: data.name,
        category: data.category,
        description: data.description || null,
    });
    return id;
}

export async function getAllMotifTags(category?: MotifCategory) {
    let query = 'MATCH (m:MotifTag)';
    const params: Record<string, any> = {};
    if (category) {
        query += ' WHERE m.category = $category';
        params.category = category;
    }
    query += ' RETURN m ORDER BY m.category, m.name';
    const result = await runQuery(query, params);
    return result.map((r) => r.m.properties);
}

export async function deleteMotifTag(tagId: string): Promise<void> {
    await runWrite(`MATCH (m:MotifTag {id: $tagId}) DETACH DELETE m`, { tagId });
}

export async function tagHadith(hadithId: string, motifTagId: string): Promise<void> {
    await runWrite(`
        MATCH (h:Hadith {id: $hadithId})
        MATCH (m:MotifTag {id: $motifTagId})
        MERGE (h)-[:TAGGED_WITH]->(m)
    `, { hadithId, motifTagId });
}

export async function untagHadith(hadithId: string, motifTagId: string): Promise<void> {
    await runWrite(`
        MATCH (h:Hadith {id: $hadithId})-[r:TAGGED_WITH]->(m:MotifTag {id: $motifTagId})
        DELETE r
    `, { hadithId, motifTagId });
}

export async function tagParallel(parallelId: string, motifTagId: string): Promise<void> {
    await runWrite(`
        MATCH (p:CrossCulturalParallel {id: $parallelId})
        MATCH (m:MotifTag {id: $motifTagId})
        MERGE (p)-[:TAGGED_WITH]->(m)
    `, { parallelId, motifTagId });
}

// ============ CROSS-CULTURAL PARALLELS ============

export async function createCrossParallel(data: CrossCulturalParallelData): Promise<string> {
    const id = randomUUID();

    const queries: Array<{ query: string; params?: Record<string, any> }> = [
        {
            query: `
                CREATE (p:CrossCulturalParallel {
                    id: $id,
                    parallel_type: $parallel_type,
                    isra_iliyyat_status: $isra_iliyyat_status,
                    confidence_level: $confidence_level,
                    hadith_excerpt_en: $hadith_excerpt_en,
                    source_text_original: $source_text_original,
                    source_text_en: $source_text_en,
                    scholarly_analysis: $scholarly_analysis,
                    created_at: datetime()
                })
            `,
            params: {
                id,
                parallel_type: data.parallel_type,
                isra_iliyyat_status: data.isra_iliyyat_status || 'NONE',
                confidence_level: data.confidence_level || 'MEDIUM',
                hadith_excerpt_en: data.hadith_excerpt_en || null,
                source_text_original: data.source_text_original || null,
                source_text_en: data.source_text_en || null,
                scholarly_analysis: data.scholarly_analysis || null,
            },
        },
        {
            query: `
                MATCH (h:Hadith {id: $hadithId})
                MATCH (p:CrossCulturalParallel {id: $id})
                CREATE (h)-[:HAS_PARALLEL]->(p)
            `,
            params: { hadithId: data.hadith_id, id },
        },
        {
            query: `
                MATCH (s:SourceText {id: $sourceTextId})
                MATCH (p:CrossCulturalParallel {id: $id})
                CREATE (p)-[:PARALLELS]->(s)
            `,
            params: { sourceTextId: data.source_text_id, id },
        },
        {
            query: `
                MATCH (t:ReligiousTradition {id: $traditionId})
                MATCH (p:CrossCulturalParallel {id: $id})
                CREATE (p)-[:FROM_TRADITION]->(t)
            `,
            params: { traditionId: data.tradition_id, id },
        },
    ];

    await runTransaction(queries);

    // Add motif tags if provided
    if (data.motif_tag_ids && data.motif_tag_ids.length > 0) {
        for (const tagId of data.motif_tag_ids) {
            await tagParallel(id, tagId);
        }
    }

    return id;
}

export async function getParallelsForHadith(hadithId: string) {
    const result = await runQuery(`
        MATCH (h:Hadith {id: $hadithId})-[:HAS_PARALLEL]->(p:CrossCulturalParallel)
        MATCH (p)-[:PARALLELS]->(s:SourceText)
        MATCH (p)-[:FROM_TRADITION]->(t:ReligiousTradition)
        OPTIONAL MATCH (p)-[:TAGGED_WITH]->(m:MotifTag)
        RETURN p, s, t, collect(DISTINCT m) as tags
        ORDER BY p.created_at
    `, { hadithId });

    return result.map((r) => ({
        ...r.p.properties,
        source_text: r.s.properties,
        tradition: r.t.properties,
        motif_tags: r.tags.map((t: any) => t.properties),
    }));
}

export async function deleteParallel(parallelId: string): Promise<void> {
    await runWrite(`MATCH (p:CrossCulturalParallel {id: $parallelId}) DETACH DELETE p`, { parallelId });
}

export async function updateParallel(parallelId: string, data: Partial<Omit<CrossCulturalParallelData, 'hadith_id' | 'source_text_id' | 'tradition_id' | 'motif_tag_ids'>>): Promise<void> {
    const setClause = Object.keys(data).map((k) => `p.${k} = $${k}`).join(', ');
    if (!setClause) return;
    await runWrite(`MATCH (p:CrossCulturalParallel {id: $parallelId}) SET ${setClause}`, { parallelId, ...data });
}

// ============ NARRATOR ↔ TRADITION ============

export async function linkNarratorToTradition(narratorId: string, traditionId: string): Promise<void> {
    await runWrite(`
        MATCH (n:Narrator {id: $narratorId})
        MATCH (t:ReligiousTradition {id: $traditionId})
        MERGE (n)-[:TRANSMITTER_OF_TRADITION]->(t)
    `, { narratorId, traditionId });
}

export async function unlinkNarratorFromTradition(narratorId: string, traditionId: string): Promise<void> {
    await runWrite(`
        MATCH (n:Narrator {id: $narratorId})-[r:TRANSMITTER_OF_TRADITION]->(t:ReligiousTradition {id: $traditionId})
        DELETE r
    `, { narratorId, traditionId });
}

export async function getTraditionConnectionsForNarrator(narratorId: string) {
    const traditions = await runQuery(`
        MATCH (n:Narrator {id: $narratorId})-[:TRANSMITTER_OF_TRADITION]->(t:ReligiousTradition)
        RETURN t
        ORDER BY t.name
    `, { narratorId });

    const parallels = await runQuery(`
        MATCH (n:Narrator {id: $narratorId})<-[:INCLUDES]-(c:Chain)<-[:HAS_CHAIN]-(h:Hadith)
        MATCH (h)-[:HAS_PARALLEL]->(p:CrossCulturalParallel)-[:FROM_TRADITION]->(t:ReligiousTradition)
        MATCH (p)-[:PARALLELS]->(s:SourceText)
        RETURN DISTINCT h {.id, .chapter, .category, .display_grade} as hadith,
               p {.id, .parallel_type, .isra_iliyyat_status} as parallel,
               t {.id, .name} as tradition,
               s {.title, .canonical_reference} as source_text
        ORDER BY h.chapter, h.category
        LIMIT 50
    `, { narratorId });

    return {
        traditions: traditions.map((r) => r.t.properties),
        hadiths_with_parallels: parallels,
    };
}

// ============ LOCATION ↔ TRADITION ============

export async function linkLocationToTradition(locationId: string, traditionId: string): Promise<void> {
    await runWrite(`
        MATCH (l:Location {id: $locationId})
        MATCH (t:ReligiousTradition {id: $traditionId})
        MERGE (l)-[:HEARTLAND_OF]->(t)
    `, { locationId, traditionId });
}

// ============ SEARCH / QUERY ============

export async function searchParallels(filters?: {
    tradition_id?: string;
    parallel_type?: ParallelType;
    isra_iliyyat_status?: IsraIliyyatStatus;
    motif_category?: MotifCategory;
    confidence_level?: ConfidenceLevel;
}) {
    let query = `
        MATCH (h:Hadith)-[:HAS_PARALLEL]->(p:CrossCulturalParallel)
        MATCH (p)-[:PARALLELS]->(s:SourceText)
        MATCH (p)-[:FROM_TRADITION]->(t:ReligiousTradition)
        OPTIONAL MATCH (p)-[:TAGGED_WITH]->(mt:MotifTag)
    `;

    const conditions: string[] = [];
    const params: Record<string, any> = {};

    if (filters?.tradition_id) {
        conditions.push('t.id = $tradition_id');
        params.tradition_id = filters.tradition_id;
    }
    if (filters?.parallel_type) {
        conditions.push('p.parallel_type = $parallel_type');
        params.parallel_type = filters.parallel_type;
    }
    if (filters?.isra_iliyyat_status) {
        conditions.push('p.isra_iliyyat_status = $isra_iliyyat_status');
        params.isra_iliyyat_status = filters.isra_iliyyat_status;
    }
    if (filters?.confidence_level) {
        conditions.push('p.confidence_level = $confidence_level');
        params.confidence_level = filters.confidence_level;
    }
    if (filters?.motif_category) {
        conditions.push('mt.category = $motif_category');
        params.motif_category = filters.motif_category;
    }

    if (conditions.length > 0) {
        query += ' WHERE ' + conditions.join(' AND ');
    }

    query += `
        RETURN p, h {.id, .chapter, .category, .display_grade} as hadith,
               s, t, collect(DISTINCT mt) as tags
        ORDER BY t.name, p.parallel_type
        LIMIT 100
    `;

    const result = await runQuery(query, params);
    return result.map((r) => ({
        ...r.p.properties,
        hadith: r.hadith,
        source_text: r.s.properties,
        tradition: r.t.properties,
        motif_tags: r.tags.map((t: any) => t.properties),
    }));
}

export async function getAllParallels(pagination?: PaginationParams): Promise<PaginatedResult<any>> {
    const { skip, limit, page, pageSize } = toSkipLimit(pagination);
    const [countResult, result] = await Promise.all([
        runQuery<{ total: number }>(`
            MATCH (h:Hadith)-[:HAS_PARALLEL]->(p:CrossCulturalParallel)
            RETURN count(p) as total
        `),
        runQuery(`
            MATCH (h:Hadith)-[:HAS_PARALLEL]->(p:CrossCulturalParallel)
            MATCH (p)-[:PARALLELS]->(s:SourceText)
            MATCH (p)-[:FROM_TRADITION]->(t:ReligiousTradition)
            OPTIONAL MATCH (p)-[:TAGGED_WITH]->(mt:MotifTag)
            RETURN p, h {.id, .title, .display_grade} as hadith, s, t,
                   collect(DISTINCT mt) as tags
            ORDER BY p.created_at DESC
            SKIP $skip LIMIT $limit
        `, { skip, limit }),
    ]);
    return paginate(
        result.map((r) => ({
            ...r.p.properties,
            hadith: r.hadith,
            source_text: r.s.properties,
            tradition: r.t.properties,
            motif_tags: r.tags.map((t: any) => t.properties),
        })),
        countResult[0]?.total ?? 0, page, pageSize,
    );
}

export async function getComparativeStats() {
    const result = await runQuery(`
        MATCH (p:CrossCulturalParallel)-[:FROM_TRADITION]->(t:ReligiousTradition)
        RETURN t.name as tradition, p.parallel_type as type, count(*) as count
        ORDER BY tradition, type
    `);
    return result;
}
