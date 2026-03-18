import { runWrite } from './neo4j';

/**
 * Initializes Neo4j database schema with constraints and indexes
 * Includes original nodes + new HistoricalEvent, Location, Commentary nodes
 */
export async function initializeSchema(): Promise<void> {
    console.log('Creating schema one query at a time...\n');

    const constraints = [
        { label: 'Narrator', prop: 'id' },
        { label: 'Narrator', prop: 'scholar_indx' },
        { label: 'Hadith', prop: 'id' },
        { label: 'MatnVariation', prop: 'id' },
        { label: 'Chain', prop: 'id' },
        { label: 'Scholar', prop: 'id' },
        { label: 'ScholarVerdict', prop: 'id' },
        { label: 'HistoricalEvent', prop: 'id' },
        { label: 'Location', prop: 'id' },
        { label: 'Commentary', prop: 'id' },
        { label: 'Source', prop: 'id' },
    ];

    for (const { label, prop } of constraints) {
        // Use constraint name to avoid duplicates
        const constraintName = `${label.toLowerCase()}_${prop}_unique`;
        try {
            // Neo4j 5+ syntax: FOR / REQUIRE instead of ON / ASSERT
            await runWrite(`CREATE CONSTRAINT ${constraintName} IF NOT EXISTS FOR (n:${label}) REQUIRE n.${prop} IS UNIQUE`);
            console.log(`  ✅ ${label}.${prop} constraint`);
        } catch (e: any) {
            if (e.message?.includes('already exists') || e.message?.includes('equivalent')) {
                console.log(`  ℹ️  ${label}.${prop} constraint already exists`);
            } else {
                console.warn(`  ⚠️  ${label}.${prop}: ${e.message}`);
            }
        }
    }

    console.log('\nCreating indexes...');

    const indexes = [
        { label: 'Narrator', prop: 'reliability' },
        { label: 'Narrator', prop: 'tabaqah' },
        { label: 'Narrator', prop: 'name_english' },
        { label: 'Narrator', prop: 'name_arabic' },
        { label: 'Narrator', prop: 'geographic_region' },
        { label: 'Narrator', prop: 'death_year_hijri' },
        { label: 'Hadith', prop: 'display_grade' },
        { label: 'Hadith', prop: 'transmission_type' },
        { label: 'Hadith', prop: 'source' },
        { label: 'Hadith', prop: 'hadith_no' },
        { label: 'Scholar', prop: 'authority_rank' },
        { label: 'HistoricalEvent', prop: 'year_hijri' },
        { label: 'HistoricalEvent', prop: 'category' },
        { label: 'Location', prop: 'name' },
        { label: 'Commentary', prop: 'source_work' },
    ];

    for (const { label, prop } of indexes) {
        const indexName = `${label.toLowerCase()}_${prop}_idx`;
        try {
            // Neo4j 5+ syntax: FOR (n:Label) ON (n.prop)
            await runWrite(`CREATE INDEX ${indexName} IF NOT EXISTS FOR (n:${label}) ON (n.${prop})`);
            console.log(`  ✅ ${label}.${prop} index`);
        } catch (e: any) {
            if (e.message?.includes('already exists') || e.message?.includes('equivalent')) {
                console.log(`  ℹ️  ${label}.${prop} index already exists`);
            } else {
                console.warn(`  ⚠️  ${label}.${prop}: ${e.message}`);
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
    let deleted = 1;
    while (deleted > 0) {
        const result = await runWrite(`
            MATCH (n)
            WITH n LIMIT 10000
            DETACH DELETE n
            RETURN count(*) as deleted
        `);
        deleted = result[0]?.deleted || 0;
        if (deleted > 0) console.log(`  🗑️  Deleted ${deleted} nodes...`);
    }
    console.log('🗑️  Database cleared');
}
