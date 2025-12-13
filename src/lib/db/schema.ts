import { runWrite } from './neo4j';

/**
 * Initializes Neo4j database schema with constraints and indexes
 * Simplified version for Neo4j 3.5/4.x compatibility
 */
export async function initializeSchema(): Promise<void> {
    console.log('Creating schema one query at a time...\n');

    // Create constraints individually (most compatible approach)
    try {
        await runWrite(`CREATE CONSTRAINT ON (n:Narrator) ASSERT n.id IS UNIQUE`);
        console.log('  ✅ Narrator constraint');
    } catch (e: any) {
        if (!e.message?.includes('already exists')) throw e;
        console.log('  ℹ️  Narrator constraint already exists');
    }

    try {
        await runWrite(`CREATE CONSTRAINT ON (h:Hadith) ASSERT h.id IS UNIQUE`);
        console.log('  ✅ Hadith constraint');
    } catch (e: any) {
        if (!e.message?.includes('already exists')) throw e;
        console.log('  ℹ️  Hadith constraint already exists');
    }

    try {
        await runWrite(`CREATE CONSTRAINT ON (m:MatnVariation) ASSERT m.id IS UNIQUE`);
        console.log('  ✅ MatnVariation constraint');
    } catch (e: any) {
        if (!e.message?.includes('already exists')) throw e;
        console.log('  ℹ️  MatnVariation constraint already exists');
    }

    try {
        await runWrite(`CREATE CONSTRAINT ON (c:Chain) ASSERT c.id IS UNIQUE`);
        console.log('  ✅ Chain constraint');
    } catch (e: any) {
        if (!e.message?.includes('already exists')) throw e;
        console.log('  ℹ️  Chain constraint already exists');
    }

    try {
        await runWrite(`CREATE CONSTRAINT ON (s:Scholar) ASSERT s.id IS UNIQUE`);
        console.log('  ✅ Scholar constraint');
    } catch (e: any) {
        if (!e.message?.includes('already exists')) throw e;
        console.log('  ℹ️  Scholar constraint already exists');
    }

    try {
        await runWrite(`CREATE CONSTRAINT ON (v:ScholarVerdict) ASSERT v.id IS UNIQUE`);
        console.log('  ✅ ScholarVerdict constraint');
    } catch (e: any) {
        if (!e.message?.includes('already exists')) throw e;
        console.log('  ℹ️  ScholarVerdict constraint already exists');
    }

    // Create indexes (more lenient, won't error if exists)
    console.log('\nCreating indexes...');
    try {
        await runWrite(`CREATE INDEX ON :Narrator(reliability)`);
        console.log('  ✅ Narrator reliability index');
    } catch (e: any) {
        console.log('  ℹ️  Narrator reliability index already exists');
    }

    try {
        await runWrite(`CREATE INDEX ON :Narrator(tabaqah)`);
        console.log('  ✅ Narrator tabaqah index');
    } catch (e: any) {
        console.log('  ℹ️  Narrator tabaqah index already exists');
    }

    try {
        await runWrite(`CREATE INDEX ON :Hadith(display_grade)`);
        console.log('  ✅ Hadith display_grade index');
    } catch (e: any) {
        console.log('  ℹ️  Hadith display_grade index already exists');
    }

    try {
        await runWrite(`CREATE INDEX ON :Hadith(transmission_type)`);
        console.log('  ✅ Hadith transmission_type index');
    } catch (e: any) {
        console.log('  ℹ️  Hadith transmission_type index already exists');
    }

    try {
        await runWrite(`CREATE INDEX ON :Scholar(authority_rank)`);
        console.log('  ✅ Scholar authority_rank index');
    } catch (e: any) {
        console.log('  ℹ️  Scholar authority_rank index already exists');
    }

    console.log('\n✅ Neo4j schema initialized successfully');
}

/**
 * Clears all data from the database (use with caution!)
 */
export async function clearDatabase(): Promise<void> {
    await runWrite('MATCH (n) DETACH DELETE n');
    console.log('🗑️  Database cleared');
}
