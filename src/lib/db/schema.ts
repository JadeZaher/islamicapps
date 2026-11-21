import { runQuery, runWrite } from './neo4j';

export interface HadithRecordIdCoverage {
    totalHadiths: number;
    canonicalRecordIds: number;
    duplicateRecordIdGroups: number;
}

/** Positional uniqueness is removable only on an empty or fully migrated graph. */
export function canRetireHadithDatasetRowIdConstraint(
    coverage: HadithRecordIdCoverage,
): boolean {
    return coverage.duplicateRecordIdGroups === 0 && (
        coverage.totalHadiths === 0 ||
        coverage.canonicalRecordIds === coverage.totalHadiths
    );
}

async function inspectHadithRecordIdCoverage(): Promise<HadithRecordIdCoverage> {
    const [coverageRows, duplicateRows] = await Promise.all([
        runQuery<{ total: number; canonical: number }>(`
            MATCH (h:Hadith)
            RETURN count(h) AS total,
                   count(CASE WHEN h.record_id IS NOT NULL
                                   AND h.record_id = toString(h.record_id)
                                   AND h.record_id = trim(toString(h.record_id))
                                   AND h.record_id <> ''
                              THEN 1 END) AS canonical
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
    ]);
    return {
        totalHadiths: coverageRows[0]?.total ?? 0,
        canonicalRecordIds: coverageRows[0]?.canonical ?? 0,
        duplicateRecordIdGroups: duplicateRows[0]?.groups ?? 0,
    };
}

function errorMessage(error: unknown): string {
    return error instanceof Error ? error.message : String(error);
}

/**
 * Initializes Neo4j database schema with constraints and indexes
 * Includes original nodes + new HistoricalEvent, Location, Commentary nodes
 */
export async function initializeSchema(): Promise<void> {
    console.log('Creating schema one query at a time...\n');

    const constraints = [
        { label: 'Narrator', prop: 'id' },
        // narrator_scholar_indx_unique — stable business key; narrators MERGE on this, never on UUID (FR-0.1)
        { label: 'Narrator', prop: 'scholar_indx' },
        { label: 'Hadith', prop: 'id' },
        { label: 'Hadith', prop: 'record_id' },
        { label: 'MatnVariation', prop: 'id' },
        { label: 'Chain', prop: 'id' },
        { label: 'Chain', prop: 'pipeline_key' },
        { label: 'Scholar', prop: 'id' },
        { label: 'Scholar', prop: 'pipeline_key' },
        { label: 'ScholarVerdict', prop: 'id' },
        { label: 'ScholarVerdict', prop: 'pipeline_key' },
        { label: 'HistoricalEvent', prop: 'id' },
        { label: 'Epoch', prop: 'id' },
        { label: 'Person', prop: 'id' },
        { label: 'BibliographicWork', prop: 'id' },
        { label: 'Edition', prop: 'id' },
        { label: 'Citation', prop: 'id' },
        { label: 'BiographicalAssertion', prop: 'id' },
        { label: 'TemporalAssertion', prop: 'id' },
        { label: 'Location', prop: 'id' },
        { label: 'Commentary', prop: 'id' },
        { label: 'Commentary', prop: 'pipeline_key' },
        { label: 'Source', prop: 'id' },
        { label: 'Source', prop: 'name' },
        // Comparative studies nodes
        { label: 'ReligiousTradition', prop: 'id' },
        { label: 'ReligiousTradition', prop: 'name' },
        { label: 'SourceText', prop: 'id' },
        { label: 'CrossCulturalParallel', prop: 'id' },
        { label: 'CrossCulturalParallel', prop: 'pipeline_key' },
        { label: 'MotifTag', prop: 'id' },
        { label: 'MotifTag', prop: 'name' },
        // Scholarship-layer nodes
        // TODO FR-1.8: SchoolOfThought already has id+name unique constraints. The 4 tradition-pseudo-schools
        // (Sunni / Shia Imami / Ibadi / Shia Zaydi) must be tombstoned and their IN_SCHOOL edges migrated
        // to (:Hadith)-[:FROM_TRADITION]->(:ReligiousTradition). This is application-level logic (requires
        // Cypher mutation in regen-isnad-graph.ts task 1.8), not a schema-only change. The existing
        // uniqueness on SchoolOfThought.id / SchoolOfThought.name is already correct and sufficient for
        // the tradition-scoped representation once the pseudo-schools are tombstoned.
        { label: 'SchoolOfThought', prop: 'id' },
        { label: 'SchoolOfThought', prop: 'name' },
        { label: 'Practice', prop: 'id' },
        { label: 'Practice', prop: 'name' },
        // Reified isnad/narrator graph nodes (FR-1.1..1.4)
        { label: 'NameMention', prop: 'id' },
        { label: 'NameMention', prop: 'pipeline_key' },
        { label: 'Assessment', prop: 'id' },
        { label: 'Assessment', prop: 'pipeline_key' },
        { label: 'DatasetVersion', prop: 'id' },
        { label: 'DatasetVersion', prop: 'content_hash' },
    ];

    for (const { label, prop } of constraints) {
        // Use constraint name to avoid duplicates
        const constraintName = `${label.toLowerCase()}_${prop}_unique`;
        try {
            // Neo4j 5+ syntax: FOR / REQUIRE instead of ON / ASSERT
            await runWrite(`CREATE CONSTRAINT ${constraintName} IF NOT EXISTS FOR (n:${label}) REQUIRE n.${prop} IS UNIQUE`);
            console.log(`  ✅ ${label}.${prop} constraint`);
        } catch (e: unknown) {
            const message = errorMessage(e);
            if (message.includes('already exists') || message.includes('equivalent')) {
                console.log(`  ℹ️  ${label}.${prop} constraint already exists`);
            } else {
                throw new Error(`Failed to establish required ${label}.${prop} constraint`, { cause: e });
            }
        }
    }

    // A uniqueness constraint permits nulls, so its successful creation alone
    // does not prove that a populated legacy graph has migrated record_id.
    const hadithCoverage = await inspectHadithRecordIdCoverage();
    if (canRetireHadithDatasetRowIdConstraint(hadithCoverage)) {
        await runWrite('DROP CONSTRAINT hadith_dataset_row_id_unique IF EXISTS');
        console.log('  ✅ retired Hadith.dataset_row_id positional uniqueness');
    } else {
        console.warn(
            '  ⚠️  retained Hadith.dataset_row_id uniqueness: ' +
            `canonical record_id coverage=${hadithCoverage.canonicalRecordIds}/` +
            `${hadithCoverage.totalHadiths}, duplicate groups=` +
            `${hadithCoverage.duplicateRecordIdGroups}`,
        );
    }

    console.log('\nCreating indexes...');

    const indexes = [
        { label: 'Narrator', prop: 'reliability' },
        { label: 'Narrator', prop: 'tabaqah' },
        { label: 'Narrator', prop: 'name_english' },
        { label: 'Narrator', prop: 'name_arabic' },
        { label: 'Narrator', prop: 'geographic_region' },
        { label: 'Narrator', prop: 'birth_date_hijri' },
        { label: 'Narrator', prop: 'death_date_hijri' },
        { label: 'Hadith', prop: 'display_grade' },
        { label: 'Hadith', prop: 'transmission_type' },
        { label: 'Hadith', prop: 'source' },
        { label: 'Hadith', prop: 'source_work_id' },
        { label: 'Hadith', prop: 'hadith_no' },
        { label: 'Hadith', prop: 'dataset_row_id' },
        { label: 'Scholar', prop: 'authority_rank' },
        { label: 'Scholar', prop: 'name_english' },
        { label: 'Scholar', prop: 'death_year_hijri' },
        { label: 'ScholarVerdict', prop: 'ruling' },
        { label: 'HistoricalEvent', prop: 'year_hijri' },
        { label: 'HistoricalEvent', prop: 'start_year_hijri' },
        { label: 'HistoricalEvent', prop: 'end_year_hijri' },
        { label: 'HistoricalEvent', prop: 'category' },
        { label: 'Epoch', prop: 'start_year_hijri' },
        { label: 'Epoch', prop: 'end_year_hijri' },
        { label: 'Citation', prop: 'edition_id' },
        { label: 'Citation', prop: 'locator' },
        { label: 'Edition', prop: 'work_id' },
        { label: 'BiographicalAssertion', prop: 'person_id' },
        { label: 'BiographicalAssertion', prop: 'predicate' },
        { label: 'BiographicalAssertion', prop: 'review_status' },
        { label: 'TemporalAssertion', prop: 'subject_id' },
        { label: 'TemporalAssertion', prop: 'review_status' },
        { label: 'Location', prop: 'name' },
        { label: 'Source', prop: 'source_work_id' },
        { label: 'Commentary', prop: 'source_work' },
        // Comparative studies indexes
        { label: 'CrossCulturalParallel', prop: 'parallel_type' },
        { label: 'CrossCulturalParallel', prop: 'isra_iliyyat_status' },
        { label: 'CrossCulturalParallel', prop: 'confidence_level' },
        { label: 'SourceText', prop: 'tradition_name' },
        { label: 'SourceText', prop: 'canonical_reference' },
        { label: 'MotifTag', prop: 'category' },
        // Scholarship-layer indexes
        { label: 'SchoolOfThought', prop: 'category' },
        { label: 'Practice', prop: 'category' },
        // Reified isnad/narrator graph indexes (FR-1.1..1.4)
        // NameMention — high-cardinality lookups for resolution matching
        { label: 'NameMention', prop: 'surface_form' },
        { label: 'NameMention', prop: 'normalized_form' },
        { label: 'NameMention', prop: 'position' },
        // Assessment — tradition-scoped grade lookups (G-1 guardrail: grades live here, not on Narrator/Hadith)
        { label: 'Assessment', prop: 'grade' },
        { label: 'Assessment', prop: 'grade_source' },
        { label: 'Assessment', prop: 'grade_scheme' },
        // DatasetVersion — provenance chain lookups
        { label: 'DatasetVersion', prop: 'content_hash' },
        { label: 'DatasetVersion', prop: 'created_at' },
    ];

    for (const { label, prop } of indexes) {
        const indexName = `${label.toLowerCase()}_${prop}_idx`;
        try {
            // Neo4j 5+ syntax: FOR (n:Label) ON (n.prop)
            await runWrite(`CREATE INDEX ${indexName} IF NOT EXISTS FOR (n:${label}) ON (n.${prop})`);
            console.log(`  ✅ ${label}.${prop} index`);
        } catch (e: unknown) {
            const message = errorMessage(e);
            if (message.includes('already exists') || message.includes('equivalent')) {
                console.log(`  ℹ️  ${label}.${prop} index already exists`);
            } else {
                console.warn(`  ⚠️  ${label}.${prop}: ${message}`);
            }
        }
    }

    console.log('\n✅ Neo4j schema initialized successfully');
}

/**
 * Clears all data from the database (use with caution!)
 */
export async function clearDatabase(): Promise<void> {
    // Delete in batches to avoid memory issues with large datasets
    // let deleted = 1;
    // while (deleted > 0) {
    //     const result = await runWrite(`
    //         MATCH (n)
    //         WITH n LIMIT 10000
    //         DETACH DELETE n
    //         RETURN count(*) as deleted
    //     `);
    //     deleted = result[0]?.deleted || 0;
    //     if (deleted > 0) console.log(`  🗑️  Deleted ${deleted} nodes...`);
    // }
    // console.log('🗑️  Database cleared');
}
