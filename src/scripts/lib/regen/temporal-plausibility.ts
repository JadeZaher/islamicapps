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
 * Using all_rawis.death_date_hijri, flag [:NARRATED_FROM] edges where the
 * TEACHER's recorded death precedes the STUDENT's floruit (= death year, used
 * as a proxy since floruit is rarely recorded).
 *
 * Rule (conservative — avoids false positives):
 *   If both teacher and student have known death years, and
 *   teacher.death < student.death − 15  (a generation gap heuristic),
 *   the edge is marked 'impossible'.
 *   If either death year is missing, the edge is marked 'unknown'.
 *   Otherwise 'plausible'.
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

// ─── Generation gap heuristic ─────────────────────────────────────────────────

/**
 * Minimum hijri year gap between student's death and teacher's death for the
 * transmission to be considered plausible. A traditional generation is ~25–30 AH
 * years; we use 15 to be conservative and avoid false positives (hadith chains
 * sometimes span shorter distances due to precocious learners or long lives).
 */
const MIN_GENERATION_GAP_AH = 15;

// ─── assessTemporalPlausibility ───────────────────────────────────────────────

/**
 * Assess whether a transmission edge (student narrated FROM teacher) is
 * temporally plausible given the Hijri death dates from all_rawis.
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

    if (teacherDeath === null || studentDeath === null) {
        return {
            plausibility: 'unknown',
            reason:
                teacherDeath === null && studentDeath === null
                    ? 'Both death dates unknown'
                    : teacherDeath === null
                    ? 'Teacher death date unknown'
                    : 'Student death date unknown',
            teacher_death_hijri: teacherDeath,
            student_death_hijri: studentDeath,
        };
    }

    // Teacher must die BEFORE the student (teacher is further in the past).
    // If teacher died AFTER the student (or within MIN_GENERATION_GAP), flag impossible.
    // Heuristic: teacher.death + MIN_GENERATION_GAP_AH should be <= student.death
    if (teacherDeath + MIN_GENERATION_GAP_AH > studentDeath) {
        return {
            plausibility: 'impossible',
            reason: `Teacher death ${teacherDeath} AH is not at least ${MIN_GENERATION_GAP_AH} years before student death ${studentDeath} AH`,
            teacher_death_hijri: teacherDeath,
            student_death_hijri: studentDeath,
        };
    }

    return {
        plausibility: 'plausible',
        reason: `Teacher (d.${teacherDeath} AH) → Student (d.${studentDeath} AH) gap = ${studentDeath - teacherDeath} AH`,
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

// ─── flagAllTransmissionEdges ─────────────────────────────────────────────────

/**
 * Assess and flag ALL [:NARRATED_FROM] edges in the graph using the rawis map.
 * Should be called once after a full regen run, not per-row.
 *
 * Uses batch Cypher to read all edges, then writes plausibility in JS batches.
 */
export async function flagAllTransmissionEdges(
    rawis: Map<number, RawiRecord>,
    dvId: string
): Promise<TemporalReport> {
    const report: TemporalReport = {
        total_edges_assessed: 0,
        plausible: 0,
        impossible: 0,
        unknown: 0,
        errors: [],
    };

    // Read all NARRATED_FROM edges that haven't been temporally assessed yet.
    const edges = await runQuery<{
        studentIndx: number;
        teacherIndx: number;
    }>(`
        MATCH (student:Narrator)-[r:NARRATED_FROM]->(teacher:Narrator)
        WHERE r.temporal_plausibility IS NULL
        RETURN student.scholar_indx AS studentIndx, teacher.scholar_indx AS teacherIndx
    `);

    for (const edge of edges) {
        try {
            const studentRecord = rawis.get(edge.studentIndx);
            const teacherRecord = rawis.get(edge.teacherIndx);

            const result = assessTemporalPlausibility(studentRecord, teacherRecord);
            await flagTransmissionEdge(edge.studentIndx, edge.teacherIndx, result, dvId);

            report.total_edges_assessed++;
            report[result.plausibility]++;
        } catch (err) {
            report.errors.push(`Edge ${edge.studentIndx}→${edge.teacherIndx}: ${err}`);
        }
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
    const report: TemporalReport = {
        total_edges_assessed: 0,
        plausible: 0,
        impossible: 0,
        unknown: 0,
        errors: [],
    };

    const edges = await runQuery<{
        studentIndx: number;
        teacherIndx: number;
    }>(`
        MATCH (student:Narrator)-[r:NARRATED_FROM]->(teacher:Narrator)
        RETURN student.scholar_indx AS studentIndx, teacher.scholar_indx AS teacherIndx
    `);

    for (const edge of edges) {
        try {
            const studentRecord = rawis.get(edge.studentIndx);
            const teacherRecord = rawis.get(edge.teacherIndx);
            const result = assessTemporalPlausibility(studentRecord, teacherRecord);
            await flagTransmissionEdge(edge.studentIndx, edge.teacherIndx, result, dvId);
            report.total_edges_assessed++;
            report[result.plausibility]++;
        } catch (err) {
            report.errors.push(`Edge ${edge.studentIndx}→${edge.teacherIndx}: ${err}`);
        }
    }

    return report;
}
