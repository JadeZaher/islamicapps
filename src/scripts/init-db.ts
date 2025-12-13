// Database initialization script
// Simplified: Skip schema constraints (causing syntax errors) and seed data directly
import { seedDatabase } from '../lib/db/seed';
import { closeDriver } from '../lib/db/neo4j';

async function main() {
    try {
        console.log('🚀 Initializing Neo4j database (seeding data)...\n');

        // Skip schema initialization due to syntax errors
        console.log('⏭️  Skipping schema constraints (will seed data directly)\n');

        // Seed data
        console.log('Step 1: Seeding database with Hadith of Jibril...');
        await seedDatabase();

        console.log('\n✅ Database initialization complete!');
        console.log('\n📋 Next steps:');
        console.log('1. Start the dev server: npm run dev');
        console.log('2. Navigate to http://localhost:3000/admin to manage data');
    } catch (error) {
        console.error('❌ Error during setup:', error);
        process.exit(1);
    } finally {
        await closeDriver();
    }
}

main();
