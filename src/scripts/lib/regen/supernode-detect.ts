/**
 * supernode-detect.ts — Identify supernode hotspots before they bottleneck writes.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream H (perf, supernode-aware)
 *
 * Background — why this exists
 * ----------------------------
 * Hadith isnads converge on a handful of Companion-narrators (Abu Hurayrah,
 * Anas ibn Malik, etc.). When a batched UNWIND issues many MERGEs targeting
 * the same narrator within one transaction, each MERGE has to scan that
 * narrator's accumulating edge set. Past a few hundred edges, per-MERGE cost
 * grows non-trivially and the whole transaction blows the per-tx wall-clock.
 *
 * On a v2.2 run over Sunan Ibn Majah (rows ~31k-35k), every K=100 batch
 * tripped the runWrite 30s ceiling, all on the same supernode contention.
 * Retry-with-split recovers correctness but throughput tanks.
 *
 * This module is **read-only**. It surfaces three pre-load reports the
 * fullregen mode can log at startup and the operator can use to size batches:
 *
 *   1. csvNarratorFrequency(csvPath)           — offline CSV scan, no DB.
 *   2. liveNarratorDegree(label, edgeType, k)  — live DB query for current top-k.
 *   3. predictSupernodes(csvFreq, threshold)   — narrators expected to exceed
 *                                                a contention threshold under
 *                                                full load.
 *
 * No writes. No mutation. Pure reporting.
 */

import fs from 'fs';
import { runQuery } from '../../../lib/db/neo4j';

// ─── CSV-side: narrator frequency from chain_indx ────────────────────────────

export interface NarratorFrequencyEntry {
    scholar_indx: number;
    chain_appearances: number;
    /** Distinct source collections this narrator appears in (small int). */
    distinct_sources: number;
    /** Sources contributing the most appearances. */
    top_sources: Array<{ source: string; n: number }>;
}

/**
 * Scan the unified CSV's `chain_indx` column and aggregate narrator
 * appearances by scholar_indx. No DB calls. Returns the frequency table
 * sorted by appearance count descending.
 *
 * For 99,283 rows × avg chain length 5, this scans ~500k slots in ~5 seconds.
 */
export function csvNarratorFrequency(csvPath: string): NarratorFrequencyEntry[] {
    // Lightweight CSV parser: only reads `chain_indx` and `source` columns,
    // skipping the multi-MB Arabic text. Avoids re-using the regen io.ts
    // parser to keep this module independent.
    const content = fs.readFileSync(csvPath, 'utf8');
    const lines = splitCSVRecords(content);
    if (lines.length === 0) return [];
    const headers = parseCSVLine(lines[0]);
    const chainIdx = headers.indexOf('chain_indx');
    const sourceIdx = headers.indexOf('source');
    if (chainIdx === -1) {
        throw new Error(`[supernode-detect] CSV missing chain_indx column: ${csvPath}`);
    }

    interface Acc {
        count: number;
        bySource: Map<string, number>;
    }
    const tally = new Map<number, Acc>();

    for (let i = 1; i < lines.length; i++) {
        const fields = parseCSVLine(lines[i]);
        const rawChain = (fields[chainIdx] ?? '').trim();
        if (!rawChain) continue;
        const source = sourceIdx === -1 ? '' : (fields[sourceIdx] ?? '').trim();
        const indices = rawChain
            .replace(/^\[|\]$/g, '')
            .split(',')
            .map((s) => parseInt(s.trim(), 10))
            .filter((n) => Number.isFinite(n));
        for (const idx of indices) {
            let acc = tally.get(idx);
            if (!acc) {
                acc = { count: 0, bySource: new Map() };
                tally.set(idx, acc);
            }
            acc.count++;
            if (source) acc.bySource.set(source, (acc.bySource.get(source) ?? 0) + 1);
        }
    }

    const out: NarratorFrequencyEntry[] = [];
    for (const [scholar_indx, acc] of tally.entries()) {
        const top_sources = [...acc.bySource.entries()]
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([source, n]) => ({ source, n }));
        out.push({
            scholar_indx,
            chain_appearances: acc.count,
            distinct_sources: acc.bySource.size,
            top_sources,
        });
    }
    out.sort((a, b) => b.chain_appearances - a.chain_appearances);
    return out;
}

/**
 * Filter a frequency table down to predicted-supernode entries. Threshold is
 * the number of chain appearances above which MERGE contention is expected
 * to start degrading per-tx throughput.
 *
 * Empirical from v2.2 runs: contention noticeable above ~500 appearances;
 * severe above ~2000.
 */
export function predictSupernodes(
    freq: NarratorFrequencyEntry[],
    threshold = 500,
): NarratorFrequencyEntry[] {
    return freq.filter((e) => e.chain_appearances >= threshold);
}

// ─── Live DB: actual degree per node ─────────────────────────────────────────

export interface LiveDegreeEntry {
    scholar_indx: number | null;
    name: string | null;
    in_degree: number;
    out_degree: number;
}

/**
 * Top-k narrators by total degree (in + out) of the given relationship type.
 * Defaults to INCLUDES (Chain → Narrator). Cheap read-only query.
 */
export async function liveNarratorDegree(
    edgeType: 'INCLUDES' | 'NARRATED_FROM' = 'INCLUDES',
    k = 20,
): Promise<LiveDegreeEntry[]> {
    // `degree` (not `size( (n)<-[...]-() )`) keeps the query O(k log N).
    const rows = await runQuery<LiveDegreeEntry>(
        `MATCH (n:Narrator)
         WITH n,
              COUNT { (n)<-[r:${edgeType}]-() } AS in_d,
              COUNT { (n)-[r:${edgeType}]->() } AS out_d
         WITH n, in_d, out_d, (in_d + out_d) AS total
         ORDER BY total DESC LIMIT $k
         RETURN n.scholar_indx AS scholar_indx, n.name AS name, in_d AS in_degree, out_d AS out_degree`,
        { k },
    );
    return rows;
}

// ─── Combined startup report ─────────────────────────────────────────────────

export interface SupernodeReport {
    total_distinct_narrators_in_csv: number;
    total_chain_positions_in_csv: number;
    threshold: number;
    predicted_supernodes: number;
    top_csv: NarratorFrequencyEntry[];
    top_live: LiveDegreeEntry[];
    /** Suggested K for batched loaders given the supernode load. */
    suggested_buffer_size: number;
}

export async function buildSupernodeReport(
    csvPath: string,
    opts: { threshold?: number; topN?: number; queryLive?: boolean } = {},
): Promise<SupernodeReport> {
    const threshold = opts.threshold ?? 500;
    const topN = opts.topN ?? 10;
    const freq = csvNarratorFrequency(csvPath);
    const totalSlots = freq.reduce((s, e) => s + e.chain_appearances, 0);
    const predicted = predictSupernodes(freq, threshold);

    let live: LiveDegreeEntry[] = [];
    if (opts.queryLive) {
        try {
            live = await liveNarratorDegree('INCLUDES', topN);
        } catch {
            live = [];
        }
    }

    // Heuristic: above 50 supernodes, K=100 will time out frequently. Drop K.
    // (Tunable; observed in v2.2 over Sunan Ibn Majah.)
    let suggested = 100;
    if (predicted.length > 50) suggested = 50;
    if (predicted.length > 100) suggested = 25;
    if (predicted.length > 200) suggested = 10;

    return {
        total_distinct_narrators_in_csv: freq.length,
        total_chain_positions_in_csv: totalSlots,
        threshold,
        predicted_supernodes: predicted.length,
        top_csv: freq.slice(0, topN),
        top_live: live,
        suggested_buffer_size: suggested,
    };
}

/** Print a human-readable report to stdout. Used at fullregen startup. */
export function printSupernodeReport(r: SupernodeReport): void {
    console.log('\n[supernode] Narrator chain-frequency report (read-only)');
    console.log(`[supernode]   distinct narrators in CSV chain_indx: ${r.total_distinct_narrators_in_csv}`);
    console.log(`[supernode]   total chain position slots:           ${r.total_chain_positions_in_csv}`);
    console.log(`[supernode]   threshold (appearances):              ${r.threshold}`);
    console.log(`[supernode]   predicted supernodes (>= threshold):  ${r.predicted_supernodes}`);
    console.log(`[supernode]   suggested batch K:                    ${r.suggested_buffer_size}`);
    console.log('[supernode]   Top CSV supernodes (scholar_indx, appearances, top source):');
    for (const e of r.top_csv) {
        const topSrc = e.top_sources[0] ? `${e.top_sources[0].source}:${e.top_sources[0].n}` : '—';
        console.log(`[supernode]     scholar_indx=${String(e.scholar_indx).padStart(6)} app=${String(e.chain_appearances).padStart(5)} top=${topSrc}`);
    }
    if (r.top_live.length > 0) {
        console.log('[supernode]   Top live-DB supernodes by INCLUDES degree:');
        for (const e of r.top_live) {
            const name = (e.name ?? '').slice(0, 40);
            console.log(
                `[supernode]     scholar_indx=${String(e.scholar_indx).padStart(6)} in=${String(e.in_degree).padStart(5)} out=${String(e.out_degree).padStart(5)}  name="${name}"`,
            );
        }
    }
}

// ─── Minimal CSV helpers (local, to avoid coupling to io.ts) ─────────────────

function parseCSVLine(line: string): string[] {
    const result: string[] = [];
    let current = '';
    let inside = false;
    for (let i = 0; i < line.length; i++) {
        const c = line[i];
        const n = line[i + 1];
        if (c === '"') {
            if (inside && n === '"') { current += '"'; i++; }
            else inside = !inside;
        } else if (c === ',' && !inside) {
            result.push(current);
            current = '';
        } else {
            current += c;
        }
    }
    result.push(current);
    return result;
}

function splitCSVRecords(content: string): string[] {
    const rows: string[] = [];
    let cur = '';
    let inside = false;
    for (let i = 0; i < content.length; i++) {
        const c = content[i];
        if (c === '"') inside = !inside;
        if ((c === '\n' || c === '\r') && !inside) {
            if (c === '\r' && content[i + 1] === '\n') i++;
            if (cur.trim()) rows.push(cur);
            cur = '';
        } else {
            cur += c;
        }
    }
    if (cur.trim()) rows.push(cur);
    return rows;
}
