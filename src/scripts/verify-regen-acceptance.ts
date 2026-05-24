/**
 * verify-regen-acceptance.ts
 *
 * One-shot post-regen acceptance check for
 * neo4j_isnad_graph_regen_20260516 / ultrapilot-passoff-v2.md.
 *
 * Runs every Cypher assertion from spec §"Acceptance criteria":
 *   - Node-count table (8 labels)
 *   - Relationship-count table (9 types)
 *   - Guardrails G-1, G-2, G-4, G-5, G-6 (G-3 is a stdout disclaimer line,
 *     checked separately by greping the fullregen log)
 *   - Tradition canonicalization
 *   - Per-tradition row counts
 *   - DatasetVersion provenance
 *
 * Each assertion records PASS / FAIL / INFO with the actual value, expected
 * value, and tolerance where applicable. Final summary prints PASS=N FAIL=N
 * and exits with code 0 (all pass) or 1 (any FAIL).
 *
 * Read-only — does not write or modify the graph.
 */

import 'dotenv/config';
import { runQuery, closeDriver } from '../lib/db/neo4j';

type Status = 'PASS' | 'FAIL' | 'INFO';

interface Check {
    id: string;
    label: string;
    status: Status;
    expected: string;
    actual: string | number;
    note?: string;
}

const checks: Check[] = [];

function record(c: Check): void {
    checks.push(c);
    const tag = c.status === 'PASS' ? '[PASS]' : c.status === 'FAIL' ? '[FAIL]' : '[INFO]';
    const noteStr = c.note ? ` — ${c.note}` : '';
    console.log(`${tag} ${c.id.padEnd(34)} expected=${c.expected.padEnd(28)} actual=${c.actual}${noteStr}`);
}

async function scalar<T = number>(cypher: string, params: Record<string, unknown> = {}, field = 'n'): Promise<T> {
    const rows = await runQuery<Record<string, T>>(cypher, params);
    return (rows[0]?.[field] ?? (0 as unknown as T));
}

async function rangeCheck(id: string, label: string, cypher: string, lo: number, hi: number): Promise<void> {
    try {
        const v = Number(await scalar<number>(cypher));
        record({
            id,
            label,
            status: v >= lo && v <= hi ? 'PASS' : 'FAIL',
            expected: `${lo}–${hi}`,
            actual: v,
        });
    } catch (err) {
        record({ id, label, status: 'FAIL', expected: `${lo}–${hi}`, actual: 'ERROR', note: String(err) });
    }
}

async function minCheck(id: string, label: string, cypher: string, min: number): Promise<void> {
    try {
        const v = Number(await scalar<number>(cypher));
        record({
            id,
            label,
            status: v >= min ? 'PASS' : 'FAIL',
            expected: `>= ${min}`,
            actual: v,
        });
    } catch (err) {
        record({ id, label, status: 'FAIL', expected: `>= ${min}`, actual: 'ERROR', note: String(err) });
    }
}

async function exactCheck(id: string, label: string, cypher: string, want: number): Promise<void> {
    try {
        const v = Number(await scalar<number>(cypher));
        record({
            id,
            label,
            status: v === want ? 'PASS' : 'FAIL',
            expected: String(want),
            actual: v,
        });
    } catch (err) {
        record({ id, label, status: 'FAIL', expected: String(want), actual: 'ERROR', note: String(err) });
    }
}

async function infoCheck(id: string, label: string, cypher: string): Promise<void> {
    try {
        const v = Number(await scalar<number>(cypher));
        record({ id, label, status: 'INFO', expected: '—', actual: v });
    } catch (err) {
        record({ id, label, status: 'INFO', expected: '—', actual: 'ERROR', note: String(err) });
    }
}

async function main(): Promise<void> {
    console.log('=' .repeat(72));
    console.log('  v2 fullregen — acceptance criteria gauntlet');
    console.log('=' .repeat(72));

    // ── Node counts ─────────────────────────────────────────────────────────
    console.log('\n--- Node counts ---');
    await rangeCheck('nodes.hadith',         ':Hadith count',
        'MATCH (h:Hadith) WHERE NOT coalesce(h.tombstoned, false) RETURN count(h) AS n', 99_233, 99_333);
    await rangeCheck('nodes.narrator',       ':Narrator count',
        'MATCH (n:Narrator) WHERE NOT coalesce(n.tombstoned, false) RETURN count(n) AS n', 24_316, 24_336);
    await minCheck('nodes.chain',            ':Chain count (>= hadith)',
        'MATCH (c:Chain) WHERE NOT coalesce(c.tombstoned, false) RETURN count(c) AS n', 99_283);
    await minCheck('nodes.assessment',       ':Assessment count',
        'MATCH (a:Assessment) RETURN count(a) AS n', 44_817);
    await minCheck('nodes.namemention',      ':NameMention count',
        'MATCH (m:NameMention) RETURN count(m) AS n', 5_000);
    await exactCheck('nodes.dv.active',      'Active :DatasetVersion = 1',
        'MATCH (dv:DatasetVersion {active: true}) RETURN count(dv) AS n', 1);
    await exactCheck('nodes.tradition',      ':ReligiousTradition = 4',
        'MATCH (rt:ReligiousTradition) RETURN count(rt) AS n', 4);
    await exactCheck('nodes.source',         ':Source = 32',
        'MATCH (s:Source) WHERE NOT coalesce(s.tombstoned, false) RETURN count(s) AS n', 32);

    // ── Relationship counts ─────────────────────────────────────────────────
    console.log('\n--- Relationship counts ---');
    await minCheck('rels.has_chain',         '(:Hadith)-[:HAS_CHAIN]->(:Chain)',
        'MATCH ()-[r:HAS_CHAIN]->() RETURN count(r) AS n', 99_283);
    await minCheck('rels.includes',          '(:Chain)-[:INCLUDES]->(:Narrator)',
        'MATCH ()-[r:INCLUDES]->() RETURN count(r) AS n', 100_000);
    await minCheck('rels.includes_mention',  '(:Chain)-[:INCLUDES_MENTION]->(:NameMention)',
        'MATCH ()-[r:INCLUDES_MENTION]->() RETURN count(r) AS n', 1_000);
    await minCheck('rels.narrated_from',     '(:Narrator)-[:NARRATED_FROM]->(:Narrator)',
        'MATCH ()-[r:NARRATED_FROM]->() RETURN count(r) AS n', 10_000);
    await exactCheck('rels.from_tradition',  '(:Hadith)-[:FROM_TRADITION]->(:ReligiousTradition)',
        'MATCH (h:Hadith)-[r:FROM_TRADITION]->() WHERE NOT coalesce(h.tombstoned, false) RETURN count(r) AS n', 99_283);
    await minCheck('rels.ingested_in',       '(:Hadith)-[:INGESTED_IN]->(:DatasetVersion)',
        'MATCH ()-[r:INGESTED_IN]->() RETURN count(r) AS n', 99_283);
    await minCheck('rels.from_source',       '(:Hadith)-[:FROM_SOURCE]->(:Source)',
        'MATCH ()-[r:FROM_SOURCE]->() RETURN count(r) AS n', 99_283);
    await minCheck('rels.has_assessment',    '(:Hadith)-[:HAS_ASSESSMENT]->(:Assessment)',
        'MATCH ()-[r:HAS_ASSESSMENT]->() RETURN count(r) AS n', 44_817);
    await minCheck('rels.under_scheme',      '(:Assessment)-[:UNDER_SCHEME]->(:GradeScheme)',
        'MATCH ()-[r:UNDER_SCHEME]->() RETURN count(r) AS n', 44_817);

    // ── Guardrails ──────────────────────────────────────────────────────────
    console.log('\n--- Guardrails ---');
    await exactCheck('G-1.scalar_grade',     'G-1: no scalar grade/reliability on identity nodes',
        `MATCH (n) WHERE (n:Narrator OR n:Hadith) AND
           (n.reliability IS NOT NULL OR n.grade IS NOT NULL) RETURN count(n) AS n`, 0);
    await exactCheck('G-2.narrated_from_props', 'G-2: every NARRATED_FROM has confidence + extraction_method',
        `MATCH ()-[r:NARRATED_FROM]->()
         WHERE r.confidence IS NULL OR r.extraction_method IS NULL
         RETURN count(r) AS n`, 0);
    await exactCheck('G-4.edge_source',      'G-4: every transmission/inclusion edge has source',
        `MATCH ()-[r:INCLUDES|NARRATED_FROM|INCLUDES_MENTION|HAS_CHAIN|FROM_TRADITION]->()
         WHERE r.source IS NULL RETURN count(r) AS n`, 0);
    await exactCheck('G-5.same_as_reviewed', 'G-5: zero :SAME_AS without reviewed_by',
        `MATCH ()-[r:SAME_AS]->() WHERE r.reviewed_by IS NULL RETURN count(r) AS n`, 0);
    await exactCheck('G-6.temporal_plausibility', 'G-6: every NARRATED_FROM has temporal_plausibility',
        `MATCH ()-[r:NARRATED_FROM]->() WHERE r.temporal_plausibility IS NULL RETURN count(r) AS n`, 0);

    // ── Tradition canonicalization ──────────────────────────────────────────
    console.log('\n--- Tradition canonicalization ---');
    await exactCheck('tradition.canon',      'No "Shia Imami" / "Shia Zaydi" on identity nodes',
        `MATCH (n) WHERE (n:Hadith OR n:Narrator)
           AND n.tradition IN ['Shia Imami', 'Shia Zaydi']
         RETURN count(n) AS n`, 0);

    // ── Per-tradition row counts ────────────────────────────────────────────
    console.log('\n--- Per-tradition hadith counts (expected: Sunni 64356, Imami 33225, Ibadi 1004, Zaydi 698) ---');
    try {
        const rows = await runQuery<{ t: string; n: number }>(
            `MATCH (h:Hadith) WHERE NOT coalesce(h.tombstoned, false)
             RETURN h.tradition AS t, count(h) AS n ORDER BY n DESC`
        );
        const expected: Record<string, number> = { Sunni: 64356, Imami: 33225, Ibadi: 1004, Zaydi: 698 };
        for (const row of rows) {
            const t = String(row.t);
            const n = Number(row.n);
            const want = expected[t];
            if (want === undefined) {
                record({ id: `tradition.${t}`, label: `Tradition "${t}" hadith count`, status: 'INFO', expected: '—', actual: n });
            } else {
                const ok = Math.abs(n - want) <= 50;
                record({
                    id: `tradition.${t}`, label: `Tradition "${t}" hadith count`,
                    status: ok ? 'PASS' : 'FAIL', expected: `${want} ± 50`, actual: n,
                });
            }
        }
    } catch (err) {
        record({ id: 'tradition.counts', label: 'per-tradition counts', status: 'FAIL', expected: '4 rows', actual: 'ERROR', note: String(err) });
    }

    // ── DatasetVersion provenance ───────────────────────────────────────────
    console.log('\n--- DatasetVersion provenance ---');
    try {
        const rows = await runQuery<{
            id: string;
            expected_record_count: number;
            measured_unknown_fraction: number | null;
            content_hash: string | null;
            created_at: string | null;
        }>(`MATCH (dv:DatasetVersion {active: true})
            RETURN dv.id AS id,
                   dv.expected_record_count AS expected_record_count,
                   dv.measured_unknown_fraction AS measured_unknown_fraction,
                   dv.content_hash AS content_hash,
                   dv.created_at AS created_at`);
        if (rows.length === 0) {
            record({ id: 'dv.exists', label: 'active DatasetVersion present', status: 'FAIL', expected: '1 row', actual: 0 });
        } else {
            const dv = rows[0];
            const expRec = Number(dv.expected_record_count ?? 0);
            const muf = dv.measured_unknown_fraction === null ? NaN : Number(dv.measured_unknown_fraction);
            record({
                id: 'dv.id', label: 'DatasetVersion.id', status: 'INFO',
                expected: 'uuid', actual: String(dv.id),
            });
            record({
                id: 'dv.expected_record_count', label: 'expected_record_count = 99283',
                status: expRec === 99283 ? 'PASS' : 'FAIL', expected: '99283', actual: expRec,
            });
            record({
                id: 'dv.measured_unknown_fraction', label: 'measured_unknown_fraction ≈ 0.70',
                status: (!isNaN(muf) && muf >= 0.5 && muf <= 0.85) ? 'PASS' : 'FAIL',
                expected: '0.50–0.85', actual: isNaN(muf) ? 'null' : muf.toFixed(4),
            });
            record({
                id: 'dv.content_hash', label: 'content_hash present',
                status: dv.content_hash ? 'PASS' : 'FAIL',
                expected: 'sha256 hex', actual: dv.content_hash ? `${String(dv.content_hash).slice(0, 12)}…` : 'null',
            });
            record({
                id: 'dv.created_at', label: 'created_at present',
                status: dv.created_at ? 'PASS' : 'FAIL',
                expected: 'iso datetime', actual: dv.created_at ? String(dv.created_at) : 'null',
            });
        }
    } catch (err) {
        record({ id: 'dv.query', label: 'DatasetVersion query', status: 'FAIL', expected: 'rows', actual: 'ERROR', note: String(err) });
    }

    // ── Summary ─────────────────────────────────────────────────────────────
    const passed = checks.filter(c => c.status === 'PASS').length;
    const failed = checks.filter(c => c.status === 'FAIL').length;
    const info   = checks.filter(c => c.status === 'INFO').length;
    console.log('\n' + '=' .repeat(72));
    console.log(`  Results: PASS=${passed} FAIL=${failed} INFO=${info}`);
    console.log('=' .repeat(72));

    if (failed > 0) {
        console.log('\nFAIL details:');
        for (const c of checks) {
            if (c.status === 'FAIL') {
                console.log(`  - ${c.id}: ${c.label}`);
                console.log(`    expected=${c.expected} actual=${c.actual}${c.note ? ` (${c.note})` : ''}`);
            }
        }
    }

    await closeDriver();
    if (failed > 0) process.exitCode = 1;
}

main().catch(async (err) => {
    console.error('[verify-regen-acceptance] fatal:', err);
    try { await closeDriver(); } catch {}
    process.exitCode = 1;
});
