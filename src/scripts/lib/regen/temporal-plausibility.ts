/**
 * temporal-plausibility.ts — Contemporaneity guardrail for transmission edges.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C — task 2.5 (partial)
 *
 * Pure module: no side effects on import.
 * Exports:
 *   assessTemporalPlausibility(studentIndx, teacherIndx, rawis) → PlausibilityResult
 *   flagTransmissionEdge(studentIndx, teacherIndx, result, dvId) → Promise<void>
 *   flagAllTransmissionEdges(rawis, dvId) → Promise<TemporalReport>
 *
 * Using all_rawis birth/death bounds, flag [:NARRATED_FROM] edges whose
 * narrator lifetimes cannot overlap.
 *
 * Rule (conservative — avoids false positives):
 *   If the student was born after the teacher died, or the teacher was born
 *   after the student died, the edge is marked 'impossible'. If both overlap
 *   comparisons can be evaluated and pass, it is 'plausible'; otherwise it is
 *   'unknown'. Plausible means chronologically possible, not historically proven.
 *
 * NEVER deletes edges — sets temporal_plausibility property only (NFR-2).
 * Tombstone is not triggered for temporal implausibility — the edge remains
 * but is visually flagged and filtered in downstream analytics.
 *
 * G-6: temporal-plausibility flags MUST be present after a full regen.
 */

import { runWrite, runQuery } from '../../../lib/db/neo4j';
import type { RawiRecord } from './io';

// ─── Types ────────────────────────────────────────────────────────────────────

export type TemporalPlausibility = 'plausible' | 'impossible' | 'unknown';

export interface PlausibilityResult {
    plausibility: TemporalPlausibility;
    reason: string;
    teacher_death_hijri: number | null;
    student_death_hijri: number | null;
}

export interface TemporalReport {
    total_edges_assessed: number;
    plausible: number;
    impossible: number;
    unknown: number;
    errors: string[];
}

// ─── Bounded annotation batches ───────────────────────────────────────────────

const TEMPORAL_WRITE_BATCH_SIZE = 1_000;

// ─── assessTemporalPlausibility ───────────────────────────────────────────────

/**
 * Assess whether a transmission edge (student narrated FROM teacher) is
 * temporally plausible given Hijri birth/death bounds from all_rawis.
 *
 * This is a pure JS function — no DB I/O — so it can be called on every edge
 * before the write phase (fast batch screening).
 */
export function assessTemporalPlausibility(
    studentRecord: RawiRecord | undefined,
    teacherRecord: RawiRecord | undefined
): PlausibilityResult {
    const teacherDeath = teacherRecord?.death_date_hijri ?? null;
    const studentDeath = studentRecord?.death_date_hijri ?? null;
    const teacherBirth = teacherRecord?.birth_date_hijri ?? null;
    const studentBirth = studentRecord?.birth_date_hijri ?? null;

    if (studentBirth !== null && teacherDeath !== null && studentBirth > teacherDeath) {
        return {
            plausibility: 'impossible',
            reason: `Student birth ${studentBirth} AH is after teacher death ${teacherDeath} AH`,
            teacher_death_hijri: teacherDeath,
            student_death_hijri: studentDeath,
        };
    }
    if (teacherBirth !== null && studentDeath !== null && teacherBirth > studentDeath) {
        return {
            plausibility: 'impossible',
            reason: `Teacher birth ${teacherBirth} AH is after student death ${studentDeath} AH`,
            teacher_death_hijri: teacherDeath,
            student_death_hijri: studentDeath,
        };
    }
    if (
        studentBirth !== null && teacherDeath !== null &&
        teacherBirth !== null && studentDeath !== null
    ) {
        return {
            plausibility: 'plausible',
            reason: `Lifetimes overlap: student ${studentBirth}–${studentDeath} AH, teacher ${teacherBirth}–${teacherDeath} AH`,
            teacher_death_hijri: teacherDeath,
            student_death_hijri: studentDeath,
        };
    }
    return {
        plausibility: 'unknown',
        reason: 'Insufficient birth/death bounds to establish lifetime overlap',
        teacher_death_hijri: teacherDeath,
        student_death_hijri: studentDeath,
    };
}

// ─── flagTransmissionEdge ─────────────────────────────────────────────────────

/**
 * Write temporal_plausibility + reason onto a [:NARRATED_FROM] edge.
 * NEVER deletes the edge — only stamps the property.
 */
export async function flagTransmissionEdge(
    studentScholarIndx: number,
    teacherScholarIndx: number,
    result: PlausibilityResult,
    dvId: string
): Promise<void> {
    const cypher = `
        MATCH (student:Narrator { scholar_indx: $studentIndx })-[r:NARRATED_FROM]->(teacher:Narrator { scholar_indx: $teacherIndx })
        SET
            r.temporal_plausibility = $plausibility,
            r.temporal_reason = $reason,
            r.temporal_assessed_at = datetime(),
            r.temporal_dvId = $dvId
    `;
    await runWrite(cypher, {
        studentIndx: studentScholarIndx,
        teacherIndx: teacherScholarIndx,
        plausibility: result.plausibility,
        reason: result.reason,
        dvId,
    });
}

interface TransmissionEdge {
    relationshipId: string;
    studentIndx: number;
    teacherIndx: number;
}

interface TemporalUpdate extends TransmissionEdge, PlausibilityResult {}

async function flagTransmissionEdgesBatched(
    edges: TransmissionEdge[],
    rawis: Map<number, RawiRecord>,
    dvId: string,
): Promise<TemporalReport> {
    const report: TemporalReport = {
        total_edges_assessed: 0,
        plausible: 0,
        impossible: 0,
        unknown: 0,
        errors: [],
    };

    for (let offset = 0; offset < edges.length; offset += TEMPORAL_WRITE_BATCH_SIZE) {
        const edgeBatch = edges.slice(offset, offset + TEMPORAL_WRITE_BATCH_SIZE);
        const updates: TemporalUpdate[] = edgeBatch.map((edge) => ({
            ...edge,
            ...assessTemporalPlausibility(
                rawis.get(edge.studentIndx),
                rawis.get(edge.teacherIndx),
            ),
        }));

        try {
            const rows = await runWrite<{ updated: number }>(`
                UNWIND $updates AS update
                MATCH (student:Narrator { scholar_indx: update.studentIndx })
                    -[r:NARRATED_FROM]->
                    (teacher:Narrator { scholar_indx: update.teacherIndx })
                WHERE elementId(r) = update.relationshipId
                SET r.temporal_plausibility = update.plausibility,
                    r.temporal_reason = update.reason,
                    r.temporal_assessed_at = datetime(),
                    r.temporal_dvId = $dvId
                RETURN count(r) AS updated
            `, { updates, dvId });
            const updated = rows[0]?.updated ?? 0;
            if (updated !== updates.length) {
                report.errors.push(
                    `Temporal batch ${offset}-${offset + updates.length - 1}: ` +
                    `matched ${updated}/${updates.length} relationships`,
                );
                continue;
            }
            report.total_edges_assessed += updated;
            for (const update of updates) report[update.plausibility]++;
        } catch (err) {
            report.errors.push(
                `Temporal batch ${offset}-${offset + updates.length - 1}: ${String(err)}`,
            );
        }
    }

    return report;
}

function mergeTemporalReport(target: TemporalReport, addition: TemporalReport): void {
    target.total_edges_assessed += addition.total_edges_assessed;
    target.plausible += addition.plausible;
    target.impossible += addition.impossible;
    target.unknown += addition.unknown;
    target.errors.push(...addition.errors);
}

function emptyTemporalReport(): TemporalReport {
    return { total_edges_assessed: 0, plausible: 0, impossible: 0, unknown: 0, errors: [] };
}

// ─── flagAllTransmissionEdges ─────────────────────────────────────────────────

/**
 * Assess and flag ALL [:NARRATED_FROM] edges in the graph using the rawis map.
 * Should be called once after a full regen run, not per-row.
 *
 * Reads and writes bounded batches until no unassessed edge remains.
 */
export async function flagAllTransmissionEdges(
    rawis: Map<number, RawiRecord>,
    dvId: string
): Promise<TemporalReport> {
    const report = emptyTemporalReport();
    while (true) {
        const edges = await runQuery<TransmissionEdge>(`
            MATCH (student:Narrator)-[r:NARRATED_FROM]->(teacher:Narrator)
            WHERE r.temporal_plausibility IS NULL
            RETURN elementId(r) AS relationshipId,
                   student.scholar_indx AS studentIndx,
                   teacher.scholar_indx AS teacherIndx
            LIMIT $limit
        `, { limit: TEMPORAL_WRITE_BATCH_SIZE });
        if (edges.length === 0) break;
        const batchReport = await flagTransmissionEdgesBatched(edges, rawis, dvId);
        mergeTemporalReport(report, batchReport);
        if (batchReport.errors.length > 0) break;
    }
    return report;
}

// ─── re-assess already-flagged edges ─────────────────────────────────────────

/**
 * Re-assess ALL [:NARRATED_FROM] edges (including previously flagged ones).
 * Use this when rawis data is updated with new death dates.
 */
export async function reflagAllTransmissionEdges(
    rawis: Map<number, RawiRecord>,
    dvId: string
): Promise<TemporalReport> {
    const report = emptyTemporalReport();
    let cursor = '';
    while (true) {
        const edges = await runQuery<TransmissionEdge>(`
            MATCH (student:Narrator)-[r:NARRATED_FROM]->(teacher:Narrator)
            WHERE $cursor = '' OR elementId(r) > $cursor
            RETURN elementId(r) AS relationshipId,
                   student.scholar_indx AS studentIndx,
                   teacher.scholar_indx AS teacherIndx
            ORDER BY relationshipId
            LIMIT $limit
        `, { cursor, limit: TEMPORAL_WRITE_BATCH_SIZE });
        if (edges.length === 0) break;
        const batchReport = await flagTransmissionEdgesBatched(edges, rawis, dvId);
        mergeTemporalReport(report, batchReport);
        if (batchReport.errors.length > 0) break;
        cursor = edges[edges.length - 1].relationshipId;
    }
    return report;
}
