// Verify seeded data
import neo4j from 'neo4j-driver';

async function verify() {
    const driver = neo4j.driver(
        'bolt://switchyard.proxy.rlwy.net:52091',
        neo4j.auth.basic('neo4j', 'qa67yaimttxev1lzgfqxeybsryh0wlnf')
    );

    try {
        const session = driver.session();

        // Count all nodes
        const countResult = await session.run('MATCH (n) RETURN count(n) as count, labels(n) as labels');
        console.log('📊 Database contents:');
        console.log(`Total nodes: ${countResult.records[0].get('count').toNumber()}\n`);

        // Get all node types
        const typesResult = await session.run('MATCH (n) RETURN DISTINCT labels(n) as labels, count(*) as count');
        console.log('Node types:');
        typesResult.records.forEach(record => {
            const labels = record.get('labels');
            const count = record.get('count').toNumber();
            console.log(`  • ${labels.join(', ')}: ${count}`);
        });

        // Get Hadith details
        console.log('\n📖 Hadiths in database:');
        const hadithResult = await session.run('MATCH (h:Hadith) RETURN h');
        hadithResult.records.forEach(record => {
            const hadith = record.get('h').properties;
            console.log(`  • "${hadith.title}" (ID: ${hadith.id})`);
            console.log(`    Grade: ${hadith.display_grade}`);
        });

        await session.close();
        await driver.close();

        console.log('\n✅ Database verification complete!');
    } catch (error) {
        console.error('❌ Verification failed:', error);
        process.exit(1);
    }
}

verify();
