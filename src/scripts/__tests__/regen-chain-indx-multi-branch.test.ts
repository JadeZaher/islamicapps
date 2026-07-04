/**
 * regen-chain-indx-multi-branch.test.ts — Phase 3 multi-branch chain_indx tests
 * ==============================================================================
 *
 * Track: uniform_isnad_extraction_20260609, Phase 3.
 * Spec refs: FR-2.2 (CSV format compatibility), tasks T-3.1 .. T-3.5.
 *
 * Covers the TypeScript read-path migration from flat `number[]` chain_indx
 * to per-branch `number[][]` chain_indx (taḥwīl-aware):
 *
 *   io.ts                  — parseChainIndices  (flat + multi-branch + edge cases)
 *   load-chain.ts          — buildTier1Resolution (per-branch emission)
 *   entity-resolution.ts   — resolveNarrators Tier-1 path (per-branch emission,
 *                            audit-flag preservation for missing scholar_indx)
 *
 * Test groups:
 *   T1 — parseChainIndices unit tests (no Neo4j)
 *   T2 — buildTier1Resolution unit tests (no Neo4j)
 *   T3 — resolveNarrators Tier-1 path unit tests (no Neo4j)
 *
 * Run: tsx src/scripts/__tests__/regen-chain-indx-multi-branch.test.ts
 */

import { parseChainIndices, parseIndices } from '../lib/regen/io';
import type { UnifiedRow } from '../lib/regen/io';
import { buildTier1Resolution } from '../lib/regen/load-chain';
import { resolveNarrators } from '../lib/regen/entity-resolution';
import type { RawiRecord as ErRawiRecord } from '../lib/regen/entity-resolution';

// ─── Harness ─────────────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const failures: string[] = [];

function check(name: string, cond: boolean, detail = ''): void {
    if (cond) {
        passed++;
        console.log(`  PASS ${name}`);
    } else {
        failed++;
        failures.push(`${name}${detail ? ` — ${detail}` : ''}`);
        console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
    }
}

function eq<T>(name: string, actual: T, expected: T): void {
    check(name, JSON.stringify(actual) === JSON.stringify(expected),
        `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

// ─── Fixtures ────────────────────────────────────────────────────────────────

/** Minimal UnifiedRow for buildTier1Resolution tests — only chain_indx matters. */
function makeRow(chainIndx: number[][]): UnifiedRow {
    return {
        dataset_row_id: 1,
        hadith_id: 'h1',
        hadith_no: '1',
        source: 'test',
        tradition: 'Sunni',
        volume: '',
        chapter: '',
        chapter_no: '',
        category: '',
        text_ar: '',
        text_en: '',
        matn_ar: '',
        matn_en: '',
        sanad: '',
        sanad_confidence: '',
        chain_indx: chainIndx,
        school: '',
        chain_type: '',
        attributed_to: '',
        narration_level: '',
        grade_value: '',
        grade_tradition: '',
        grade_source: '',
        gradings_full: '',
        url: '',
        page_ref: '',
        _raw: {},
    };
}

/** Build a tiny Map<scholar_indx, RawiRecord> for entity-resolution tests. */
function makeRawisMap(ids: number[]): Map<number, ErRawiRecord> {
    const m = new Map<number, ErRawiRecord>();
    for (const id of ids) {
        m.set(id, {
            scholar_indx: id,
            name: `Rawi ${id}`,
            grade: 'sahih',
            death_date_hijri: 100 + id,
        });
    }
    return m;
}

/** Minimal entity-resolution UnifiedRow stub (different shape — chain_indx is string). */
function makeErRow(chainIndxStr: string, sanad = ''): {
    dataset_row_id?: number;
    source?: string;
    hadith_no?: string;
    tradition?: string;
    sanad?: string;
    chain_indx?: string;
} {
    return {
        dataset_row_id: 1,
        source: 'test',
        hadith_no: '1',
        tradition: 'Sunni',
        sanad,
        chain_indx: chainIndxStr,
    };
}

// ─── T1: parseChainIndices unit tests ────────────────────────────────────────

function testT1_parseChainIndices(): void {
    console.log('\n[T1] parseChainIndices (io.ts) — multi-branch parser');

    eq('T1.1: empty string → []',
        parseChainIndices(''), []);

    eq('T1.2: single branch "1,2,3" → [[1,2,3]] (backwards compat)',
        parseChainIndices('1,2,3'), [[1, 2, 3]]);

    eq('T1.3: two branches "1,2,3|4,5,6" → [[1,2,3],[4,5,6]]',
        parseChainIndices('1,2,3|4,5,6'), [[1, 2, 3], [4, 5, 6]]);

    eq('T1.4: three single-id branches "1|2|3" → [[1],[2],[3]]',
        parseChainIndices('1|2|3'), [[1], [2], [3]]);

    eq('T1.5: whitespace tolerance " 1, 2 | 3, 4 " → [[1,2],[3,4]]',
        parseChainIndices(' 1, 2 | 3, 4 '), [[1, 2], [3, 4]]);

    eq('T1.6: empty middle branch "1,2||3,4" → [[1,2],[3,4]] (empty dropped)',
        parseChainIndices('1,2||3,4'), [[1, 2], [3, 4]]);

    eq('T1.7: invalid token "1,abc,3" → [[1,3]] (NaN dropped silently)',
        parseChainIndices('1,abc,3'), [[1, 3]]);

    eq('T1.8: legacy JSON-array form "[1,2,3]" → [[1,2,3]]',
        parseChainIndices('[1,2,3]'), [[1, 2, 3]]);

    eq('T1.9: leading/trailing pipe "|1,2|" → [[1,2]] (empty branches dropped)',
        parseChainIndices('|1,2|'), [[1, 2]]);

    // Sanity: parseIndices (flat helper, for teachers/students) MUST stay flat.
    eq('T1.10: parseIndices (flat) on "1,2,3" → [1,2,3] (unchanged)',
        parseIndices('1,2,3'), [1, 2, 3]);
    eq('T1.11: parseIndices (flat) on "" → [] (unchanged)',
        parseIndices(''), []);
}

// ─── T2: buildTier1Resolution unit tests ─────────────────────────────────────

function testT2_buildTier1Resolution(): void {
    console.log('\n[T2] buildTier1Resolution (load-chain.ts) — per-branch emission');

    // T2.1: empty chain_indx → no results.
    const emptyResults = buildTier1Resolution(makeRow([]));
    eq('T2.1: empty chain_indx → []', emptyResults.length, 0);

    // T2.2: single-branch row → exactly one NarratorResolutionResult, chain_index=0.
    const singleBranch = buildTier1Resolution(makeRow([[1, 2, 3]]));
    check('T2.2a: single branch emits exactly one result',
        singleBranch.length === 1,
        `expected 1, got ${singleBranch.length}`);
    eq('T2.2b: single-branch result chain_index === 0',
        singleBranch[0]?.chain_index, 0);
    eq('T2.2c: single-branch resolved.length === 3',
        singleBranch[0]?.resolved.length, 3);
    eq('T2.2d: single-branch scholar_indx values preserved',
        singleBranch[0]?.resolved.map(r => r.scholar_indx), [1, 2, 3]);
    eq('T2.2e: single-branch positions are 0,1,2',
        singleBranch[0]?.resolved.map(r => r.position), [0, 1, 2]);
    eq('T2.2f: single-branch method === chain_indx_join',
        singleBranch[0]?.method, 'chain_indx_join');

    // T2.3: two-branch row → two NarratorResolutionResults, chain_index = 0, 1.
    const twoBranch = buildTier1Resolution(makeRow([[1, 2], [3, 4, 5]]));
    check('T2.3a: two branches emit exactly two results',
        twoBranch.length === 2,
        `expected 2, got ${twoBranch.length}`);
    eq('T2.3b: branch 0 chain_index === 0', twoBranch[0]?.chain_index, 0);
    eq('T2.3c: branch 1 chain_index === 1', twoBranch[1]?.chain_index, 1);
    eq('T2.3d: branch 0 resolved scholar_indx',
        twoBranch[0]?.resolved.map(r => r.scholar_indx), [1, 2]);
    eq('T2.3e: branch 1 resolved scholar_indx',
        twoBranch[1]?.resolved.map(r => r.scholar_indx), [3, 4, 5]);

    // T2.4: position-in-branch (NOT global running) — narrator at branch 1 pos 0
    // must have position 0, NOT 2 (= length of branch 0).
    eq('T2.4a: branch 1 first narrator position === 0 (per-branch, not global)',
        twoBranch[1]?.resolved[0]?.position, 0);
    eq('T2.4b: branch 1 last narrator position === 2 (in-branch index)',
        twoBranch[1]?.resolved[2]?.position, 2);

    // T2.5: each ResolvedNarrator carries method='chain_indx_join' and confidence=1.0.
    check('T2.5a: branch 0 narrators all confidence=1.0',
        twoBranch[0]?.resolved.every(r => r.confidence === 1.0) ?? false);
    check('T2.5b: branch 0 narrators all method=chain_indx_join',
        twoBranch[0]?.resolved.every(r => r.method === 'chain_indx_join') ?? false);

    // T2.6: each branch result has empty mentions[] (Tier-1 never emits mentions).
    eq('T2.6a: branch 0 mentions empty', twoBranch[0]?.mentions.length, 0);
    eq('T2.6b: branch 1 mentions empty', twoBranch[1]?.mentions.length, 0);
}

// ─── T3: entity-resolution Tier-1 path tests ─────────────────────────────────

async function testT3_resolveNarratorsTier1(): Promise<void> {
    console.log('\n[T3] resolveNarrators Tier-1 path (entity-resolution.ts) — multi-branch');

    // Rawis fixture: scholars 1,2,3,4,5,6 exist; 99999 does NOT (audit-flag case).
    const rawis = makeRawisMap([1, 2, 3, 4, 5, 6]);

    // T3.1: single-branch chain_indx "1,2,3" → one result, method=chain_indx_join, 3 resolved.
    const single = await resolveNarrators(makeErRow('1,2,3'), rawis);
    check('T3.1a: single-branch chain_indx → exactly one result',
        single.length === 1,
        `expected 1, got ${single.length}`);
    eq('T3.1b: single-branch method === chain_indx_join',
        single[0]?.method, 'chain_indx_join');
    eq('T3.1c: single-branch resolved.length === 3',
        single[0]?.resolved.length, 3);
    eq('T3.1d: single-branch chain_index === 0',
        single[0]?.chain_index, 0);
    eq('T3.1e: single-branch scholar_indx values',
        single[0]?.resolved.map(r => r.scholar_indx), [1, 2, 3]);

    // T3.2: multi-branch chain_indx "1,2,3|4,5,6" → two results, method=chain_indx_join.
    const multi = await resolveNarrators(makeErRow('1,2,3|4,5,6'), rawis);
    check('T3.2a: multi-branch chain_indx → exactly two results',
        multi.length === 2,
        `expected 2, got ${multi.length}`);
    eq('T3.2b: multi-branch result 0 method === chain_indx_join',
        multi[0]?.method, 'chain_indx_join');
    eq('T3.2c: multi-branch result 0 chain_index === 0',
        multi[0]?.chain_index, 0);
    eq('T3.2d: multi-branch result 1 chain_index === 1',
        multi[1]?.chain_index, 1);
    eq('T3.2e: branch 0 resolved count === 3', multi[0]?.resolved.length, 3);
    eq('T3.2f: branch 1 resolved count === 3', multi[1]?.resolved.length, 3);
    eq('T3.2g: branch 0 scholar_indx values',
        multi[0]?.resolved.map(r => r.scholar_indx), [1, 2, 3]);
    eq('T3.2h: branch 1 scholar_indx values',
        multi[1]?.resolved.map(r => r.scholar_indx), [4, 5, 6]);

    // T3.3: audit-flag preservation — scholar 99999 has no rawi → produces a
    // NameMention with surface_form '[chain_indx:99999]'. Branch 1 has both
    // valid (1,2) and invalid (99999) → branch 1 carries 2 resolved + 1 mention.
    const mixed = await resolveNarrators(makeErRow('1,2|3,99999'), rawis);
    check('T3.3a: mixed-validity multi-branch → two results',
        mixed.length === 2,
        `expected 2, got ${mixed.length}`);
    eq('T3.3b: branch 0 resolved count === 2', mixed[0]?.resolved.length, 2);
    eq('T3.3c: branch 0 mentions count === 0', mixed[0]?.mentions.length, 0);
    eq('T3.3d: branch 1 resolved count === 1', mixed[1]?.resolved.length, 1);
    eq('T3.3e: branch 1 mentions count === 1', mixed[1]?.mentions.length, 1);

    const auditMention = mixed[1]?.mentions[0];
    eq('T3.3f: branch 1 audit-flag surface_form === [chain_indx:99999]',
        auditMention?.surface_form, '[chain_indx:99999]');
    eq('T3.3g: branch 1 audit-flag normalized_form === [chain_indx:99999]',
        auditMention?.normalized_form, '[chain_indx:99999]');

    // T3.4: empty chain_indx + empty sanad → Tier-2/3 fall-through, returns
    // exactly one result (Tier-2 single-result contract). Method becomes
    // 'lexicon_exact' for empty sanad.
    const empty = await resolveNarrators(makeErRow('', ''), rawis);
    check('T3.4a: empty chain_indx + empty sanad → exactly one result',
        empty.length === 1,
        `expected 1, got ${empty.length}`);
    eq('T3.4b: empty path resolved count === 0', empty[0]?.resolved.length, 0);
    eq('T3.4c: empty path chain_index === 0', empty[0]?.chain_index, 0);
}

// ─── Smoke: round-trip parity ────────────────────────────────────────────────

function testSmoke_roundTrip(): void {
    console.log('\n[Smoke] parseChainIndices round-trip (manual proofs)');
    const a = parseChainIndices('1,2,3');
    const b = parseChainIndices('1,2,3|4,5,6');
    const c = parseChainIndices('');
    check('Smoke 1: "1,2,3" round-trip == [[1,2,3]]',
        JSON.stringify(a) === '[[1,2,3]]', JSON.stringify(a));
    check('Smoke 2: "1,2,3|4,5,6" round-trip == [[1,2,3],[4,5,6]]',
        JSON.stringify(b) === '[[1,2,3],[4,5,6]]', JSON.stringify(b));
    check('Smoke 3: "" round-trip == []',
        JSON.stringify(c) === '[]', JSON.stringify(c));
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
    console.log('=== regen-chain-indx-multi-branch.test.ts ===');
    console.log('Track: uniform_isnad_extraction_20260609, Phase 3 (FR-2.2)\n');

    testT1_parseChainIndices();
    testT2_buildTier1Resolution();
    await testT3_resolveNarratorsTier1();
    testSmoke_roundTrip();

    console.log(`\n=== Summary ===`);
    console.log(`  passed:  ${passed}`);
    console.log(`  failed:  ${failed}`);
    if (failures.length > 0) {
        console.log('\nFailures:');
        for (const f of failures) console.log(`  - ${f}`);
    }

    // JSON summary on the last stdout line for verifier parsing.
    console.log(JSON.stringify({ passed, failed, skipped: 0 }));

    if (failed > 0) process.exit(1);
}

void main();
