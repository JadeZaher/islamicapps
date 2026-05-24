/**
 * audit-graph.ts — generic read-only Neo4j diagnostic.
 * =====================================================
 *
 * One CLI surface for every "what's in the graph?" question. Sectioned so it
 * stays useful as the schema evolves; each section is a small named function
 * with a docstring describing what it checks and why.
 *
 * Usage:
 *   npm run db:audit                              # run every section
 *   npm run db:audit -- --section=schools,text   # comma-list to run a subset
 *   npm run db:audit -- --list                    # list available sections
 *   npm run db:audit -- --json                    # emit JSONL instead of tables
 *
 * This is read-only. It writes nothing to Neo4j.
 *
 * Replaces `_audit_gaps.ts` (the throwaway used to build the
 * neo4j_isnad_graph_regen_20260516 track spec).
 */
import { loadEnv } from './lib/env';
import { runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ── CLI parsing ────────────────────────────────────────────────────────────

const argv = process.argv.slice(2);
const flag = (name: string): string | undefined => {
    const eq = argv.find((a) => a.startsWith(`--${name}=`));
    if (eq) return eq.slice(name.length + 3);
    const bare = argv.find((a) => a === `--${name}`);
    return bare ? '' : undefined;
};
const wantsList = flag('list') !== undefined;
const asJson = flag('json') !== undefined;
const requested = (flag('section') ?? '').split(',').map((s) => s.trim()).filter(Boolean);

// ── Section infrastructure ────────────────────────────────────────────────

type Section = {
    name: string;
    description: string;
    run: () => Promise<void>;
};

async function emit(title: string, rows: Record<string, unknown>[]) {
    if (asJson) {
        for (const r of rows) console.log(JSON.stringify({ section: title, ...r }));
        return;
    }
    console.log(`\n=== ${title} ===`);
    for (const r of rows) console.log(' ', JSON.stringify(r));
}

const sections: Section[] = [
    // ── nodes ───────────────────────────────────────────────────────────
    {
        name: 'nodes',
        description: 'Node counts by label (overall graph shape).',
        run: async () => {
            const rows = await runQuery<{ label: string; count: number | string }>(
                `CALL db.labels() YIELD label
                 CALL { WITH label MATCH (n) WHERE label IN labels(n) RETURN count(n) AS count }
                 RETURN label, count ORDER BY count DESC`,
            );
            await emit('NODE COUNTS BY LABEL', rows);
        },
    },

    // ── rels ────────────────────────────────────────────────────────────
    {
        name: 'rels',
        description: 'Relationship counts by type.',
        run: async () => {
            const rows = await runQuery<{ rel: string; count: number | string }>(
                `CALL db.relationshipTypes() YIELD relationshipType AS rel
                 CALL { WITH rel MATCH ()-[r]->() WHERE type(r) = rel RETURN count(r) AS count }
                 RETURN rel, count ORDER BY count DESC`,
            );
            await emit('RELATIONSHIP COUNTS BY TYPE', rows);
        },
    },

    // ── schools ─────────────────────────────────────────────────────────
    {
        name: 'schools',
        description:
            'SchoolOfThought usage. Flags the known mislabel: traditions ' +
            '("Sunni"/"Shia Imami"/...) being held as SchoolOfThought nodes ' +
            'alongside the actual madhhabs (Hanafi/Maliki/...).',
        run: async () => {
            const rows = await runQuery(
                `MATCH (s:SchoolOfThought)
                 OPTIONAL MATCH (s)<-[:IN_SCHOOL]-(h:Hadith)
                 WITH s.name AS school, count(h) AS hadiths,
                      CASE WHEN s.name IN ['Sunni','Shia Imami','Shia Zaydi','Ibadi','Imami','Zaydi']
                           THEN 'MISLABELED_TRADITION' ELSE 'ok' END AS flag
                 RETURN school, hadiths, flag ORDER BY hadiths DESC`,
            );
            await emit('SCHOOL-OF-THOUGHT USAGE', rows);
        },
    },

    // ── text ────────────────────────────────────────────────────────────
    {
        name: 'text',
        description:
            'Hadith text quality: empty, very-short, or contaminated text. ' +
            'Catches OCR breakage and LLM refusal leakage.',
        run: async () => {
            const lengths = await runQuery(
                `MATCH (h:Hadith)
                 WITH CASE WHEN h.text_arabic IS NULL OR h.text_arabic = '' THEN 'empty'
                           WHEN size(h.text_arabic) < 30 THEN 'very_short_<30'
                           WHEN size(h.text_arabic) < 100 THEN 'short_<100'
                           ELSE 'normal' END AS bucket
                 RETURN bucket, count(*) AS n ORDER BY n DESC`,
            );
            await emit('text_arabic LENGTH BUCKETS', lengths);

            const missingEn = await runQuery(
                `MATCH (h:Hadith) WHERE h.text_english IS NULL OR h.text_english = ''
                 RETURN h.tradition AS tradition, count(*) AS n ORDER BY n DESC`,
            );
            await emit('HADITHS MISSING text_english', missingEn);

            const contaminated = await runQuery(
                `MATCH (h:Hadith)
                 WHERE h.text_english =~ '(?i).*(no Arabic text was provided|Final Decision:|Applying the rules|I cannot generate a translation|no specific Arabic text|the prompt is incomplete).*'
                 RETURN count(h) AS contaminated_english`,
            );
            await emit('ENGLISH REFUSAL/LEAK CONTAMINATION', contaminated);
        },
    },

    // ── narrators ──────────────────────────────────────────────────────
    {
        name: 'narrators',
        description: 'Narrator tradition coverage and identity-shape distribution.',
        run: async () => {
            const trad = await runQuery(
                `MATCH (n:Narrator)
                 RETURN coalesce(n.tradition,'NULL') AS tradition, count(*) AS n
                 ORDER BY n DESC`,
            );
            await emit('NARRATOR TRADITION COVERAGE', trad);
        },
    },

    // ── sources ────────────────────────────────────────────────────────
    {
        name: 'sources',
        description: 'Source registry: per-source hadith counts and Source.tradition coverage.',
        run: async () => {
            const rows = await runQuery(
                `MATCH (s:Source)
                 OPTIONAL MATCH (s)<-[:FROM_SOURCE]-(h:Hadith)
                 RETURN s.name AS source,
                        coalesce(s.tradition,'NULL') AS source_tradition,
                        count(h) AS hadiths
                 ORDER BY hadiths DESC LIMIT 100`,
            );
            await emit('SOURCES (top 100 by hadith count)', rows);
        },
    },

    // ── provenance ─────────────────────────────────────────────────────
    {
        name: 'provenance',
        description:
            'DatasetVersion history + legacy hadiths not linked to any ' +
            ':DatasetVersion (the INGESTED_IN backfill gap).',
        run: async () => {
            const dv = await runQuery(
                `MATCH (dv:DatasetVersion)
                 RETURN dv.id AS id,
                        dv.expected_record_count AS expected,
                        dv.measured_unknown_fraction AS unknown_frac,
                        dv.created_at AS created
                 ORDER BY dv.created_at DESC LIMIT 10`,
            );
            await emit('DATASET VERSION HISTORY', dv);

            const legacy = await runQuery(
                `MATCH (h:Hadith) WHERE NOT (h)-[:INGESTED_IN]->(:DatasetVersion)
                 RETURN coalesce(h.tradition,'NULL') AS tradition,
                        count(*) AS legacy_hadiths_not_in_any_version
                 ORDER BY legacy_hadiths_not_in_any_version DESC`,
            );
            await emit('LEGACY HADITHS WITHOUT :DatasetVersion LINK', legacy);
        },
    },

    // ── chains ─────────────────────────────────────────────────────────
    {
        name: 'chains',
        description: 'Chain coverage: hadiths without chains and chain-length distribution.',
        run: async () => {
            const noChain = await runQuery(
                `MATCH (h:Hadith)
                 WHERE NOT (h)-[:HAS_VARIATION]->(:MatnVariation)
                    OR NOT (h)-[:HAS_VARIATION]->(:MatnVariation)-[:TRANSMITTED_VIA]->(:Chain)
                 RETURN count(DISTINCT h) AS hadiths_missing_chain`,
            );
            await emit('HADITHS WITH NO CHAIN', noChain);

            const lens = await runQuery(
                `MATCH (c:Chain)-[:INCLUDES]->(n:Narrator)
                 WITH c, count(n) AS len
                 WITH CASE WHEN len = 0 THEN '0' WHEN len <= 2 THEN '1-2'
                           WHEN len <= 4 THEN '3-4' WHEN len <= 6 THEN '5-6'
                           WHEN len <= 9 THEN '7-9' ELSE '10+' END AS bucket
                 RETURN bucket, count(*) AS chains ORDER BY chains DESC`,
            );
            await emit('CHAIN LENGTH DISTRIBUTION', lens);
        },
    },

    // ── ids ────────────────────────────────────────────────────────────
    {
        name: 'ids',
        description:
            'Hadith id shape (uuid vs business-key) per tradition. ' +
            'Surfaces the legacy uuid-bug damage that --fullregen will clean.',
        run: async () => {
            const rows = await runQuery(
                `MATCH (h:Hadith)
                 WITH CASE WHEN h.id =~ '[0-9a-f-]{36}' THEN 'uuid' ELSE 'biz_key' END AS shape,
                      h.tradition AS tradition
                 RETURN shape, tradition, count(*) AS n ORDER BY n DESC`,
            );
            await emit('HADITH ID SHAPE BY TRADITION', rows);
        },
    },

    // ── translation ────────────────────────────────────────────────────
    {
        name: 'translation',
        description:
            'English-translation coverage per source — input to the ' +
            'append-translation regen mode that fills only the missing.',
        run: async () => {
            const rows = await runQuery(
                `MATCH (h:Hadith)-[:FROM_SOURCE]->(s:Source)
                 WITH s.name AS source, count(h) AS total,
                      sum(CASE WHEN h.text_english IS NOT NULL AND h.text_english <> '' THEN 1 ELSE 0 END) AS translated
                 RETURN source, total, translated,
                        total - translated AS missing,
                        CASE WHEN total > 0 THEN toFloat(translated) / total ELSE 0.0 END AS coverage
                 ORDER BY missing DESC LIMIT 50`,
            );
            await emit('ENGLISH TRANSLATION COVERAGE BY SOURCE', rows);
        },
    },

    // ── constraints ────────────────────────────────────────────────────
    {
        name: 'constraints',
        description: 'Schema constraints currently present (for npm run db:init coverage).',
        run: async () => {
            const rows = await runQuery(
                `SHOW CONSTRAINTS YIELD name, labelsOrTypes, properties, type
                 RETURN name, labelsOrTypes, properties, type ORDER BY name`,
            );
            await emit('SCHEMA CONSTRAINTS', rows);
        },
    },
];

// ── runner ────────────────────────────────────────────────────────────────

(async () => {
    if (wantsList) {
        console.log('Available sections:');
        for (const s of sections) console.log(`  ${s.name.padEnd(14)} ${s.description}`);
        return;
    }

    const toRun = requested.length
        ? sections.filter((s) => requested.includes(s.name))
        : sections;
    if (requested.length && toRun.length !== requested.length) {
        const unknown = requested.filter((r) => !sections.find((s) => s.name === r));
        console.error(`Unknown section(s): ${unknown.join(', ')}`);
        console.error('Run with --list to see available sections.');
        process.exitCode = 2;
        return;
    }

    try {
        for (const s of toRun) await s.run();
    } finally {
        await closeDriver();
    }
})();
