import { runWrite } from './neo4j';
import { randomUUID } from 'crypto';

/**
 * Simplified seed - creates minimal test data
 */
export async function seedDatabase(): Promise<void> {
    console.log('🌱 Starting simplified seed...\n');

    try {
        // Create Prophet node
        const prophetId = randomUUID();
        console.log('Creating Prophet node...');
        await runWrite(`
      CREATE (p:Narrator {
        id: $id,
        name_arabic: 'محمد صلى الله عليه وسلم',
        name_english: 'Prophet Muhammad ﷺ',
        reliability: 'THIQA',
        tabaqah: 'PROPHET',
        bio: 'The final messenger of Allah',
        is_prophet: true
      })
    `, { id: prophetId });
        console.log('✅ Prophet node created');

        //Create a simple narrator
        const narratorId = randomUUID();
        console.log('Creating narrator node...');
        await runWrite(`
      CREATE (n:Narrator {
        id: $id,
        name_arabic: 'عمر بن الخطاب',
        name_english: 'Umar ibn al-Khattab',
        reliability: 'THIQA',
        tabaqah: 'SAHABA',
        bio: 'The second Caliph of Islam',
        death_year_hijri: 23
      })
    `, { id: narratorId });
        console.log('✅ Narrator node created');

        // Create Hadith
        const hadithId = randomUUID();
        console.log('Creating Hadith node...');
        await runWrite(`
      CREATE (h:Hadith {
        id: $id,
        title: 'Hadith of Jibril',
        primary_topic: 'Pillars of Islam',
        auto_calculated_grade: 'SAHIH',
        display_grade: 'SAHIH',
        transmission_type: 'MASHHUR'
      })
    `, { id: hadithId });
        console.log('✅ Hadith node created');

        // Create Scholar
        const scholarId = randomUUID();
        console.log('Creating Scholar node...');
        await runWrite(`
      CREATE (s:Scholar {
        id: $id,
        name: 'Ibn Hajar al-Asqalani',
        era: 'Medieval',
        school: 'Shafii',
        authority_rank: 10
      })
    `, { id: scholarId });
        console.log('✅ Scholar node created');

        console.log('\n✅ Seed completed!');
        console.log(`📌 Hadith ID: ${hadithId}`);
        console.log(`📌 Prophet ID: ${prophetId}\n`);

    } catch (error) {
        console.error('❌ Seed failed:', error);
        throw error;
    }
}
