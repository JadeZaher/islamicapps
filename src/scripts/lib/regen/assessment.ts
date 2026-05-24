/**
 * assessment.ts — Tradition-scoped :Assessment node management.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   loadAssessment(opts)                → Promise<void>
 *   migrateScalarAssessments()          → Promise<MigrationReport>
 *   parseGradingsFull(str, tradition)   → GradingEntry[]
 *   loadGradingsFull(opts)              → Promise<{ written: number; skipped: number }>
 *
 * Invariant G-1 (ABSOLUTE): NEVER write `reliability`, `grade`, or any scalar
 * verdict on a :Narrator or :Hadith node. All verdicts live on tradition-scoped
 * :Assessment nodes linked by:
 *   (:Hadith|:Narrator)-[:HAS_ASSESSMENT]->(:Assessment)-[:UNDER_SCHEME]->(:ReligiousTradition)
 *
 * Grade schemes follow scholarly norms per tradition:
 *   Sunni:  sahih / hasan / da'if / mawdu' / etc. (7-tier)
 *   Imami:  sahih / hasan / muwaththaq / da'if (4-tier Mamaqani/Hillī)
 *   Zaydi:  musnid / mursal / maqtu' (3-tier)
 *   Ibadi:  sahih / da'if (2-tier Rabi)
 *
 * Phase-0 finding: 24,347 legacy scalar-assessment nodes exist on :Narrator
 * and :Hadith. migrateScalarAssessments() migrates them into :Assessment nodes
 * then nulls out the scalar properties (node not deleted — NFR-2).
 *
 * When a tradition has no extant evaluation, a placeholder :Assessment with
 * grade='no_extant_evaluation' is written to make coverage explicit.
 *
 * Performance note: :Assessment nodes are MERGEd on `pipeline_key` which is
 * currently unindexed (index lives in schema.ts — not added here). For large
 * fan-outs (e.g. gradings_full with 14,902 rows × N scholars), the lack of an
 * index will cause full label scans per MERGE. Add a constraint/index on
 * Assessment.pipeline_key in schema.ts if write throughput degrades.
 */

import { randomUUID } from 'crypto';
import { runWrite, runQuery } from '../../../lib/db/neo4j';
import type { Tradition } from './io';

// ─── Types ────────────────────────────────────────────────────────────────────

export type GradeScheme = 'sunni_7tier' | 'imami_4tier' | 'zaydi_3tier' | 'ibadi_2tier' | 'unspecified';

export interface LoadAssessmentOpts {
    /** The node receiving the assessment: 'Hadith' or 'Narrator'. */
    targetLabel: 'Hadith' | 'Narrator';
    /** Business key property of the target node. */
    targetKeyProp: 'dataset_row_id' | 'pipeline_key' | 'scholar_indx';
    /** Business key value. */
    targetKeyValue: string | number;
    /** Tradition name (canonicalized). */
    tradition: string;
    /** Grade string (e.g. 'sahih', 'da\'if', 'no_extant_evaluation'). */
    grade: string;
    /** Source of the grade (e.g. 'rijal_csv', 'hadith_csv', 'manual'). */
    gradeSource: string;
    /** Which grade scheme applies. */
    gradeScheme: GradeScheme;
}

export interface MigrationReport {
    narrators_migrated: number;
    hadiths_migrated: number;
    scalars_nulled: number;
    errors: string[];
}

// ─── Grade scheme lookup ──────────────────────────────────────────────────────

const TRADITION_SCHEME_MAP: Record<string, GradeScheme> = {
    Sunni: 'sunni_7tier',
    Imami: 'imami_4tier',
    Zaydi: 'zaydi_3tier',
    Ibadi: 'ibadi_2tier',
};

export function schemeForTradition(tradition: string): GradeScheme {
    return TRADITION_SCHEME_MAP[tradition] ?? 'unspecified';
}

// ─── Merge ReligiousTradition node ────────────────────────────────────────────

async function mergeReligiousTradition(tradition: string): Promise<void> {
    const cypher = `
        MERGE (rt:ReligiousTradition { name: $name })
        ON CREATE SET
            rt.id = $id,
            rt.created_at = datetime()
    `;
    await runWrite(cypher, { name: tradition, id: randomUUID() });
}

// ─── loadAssessment ───────────────────────────────────────────────────────────

/**
 * Write a tradition-scoped :Assessment node and connect it to the target node.
 *
 * Assessment nodes are keyed on (targetId, tradition) — one per target per tradition.
 * If a grade already exists, it is updated (not duplicated).
 *
 * Does NOT write grade/reliability to the target node — only to :Assessment.
 */
export async function loadAssessment(opts: LoadAssessmentOpts): Promise<void> {
    const { targetLabel, targetKeyProp, targetKeyValue, tradition, grade, gradeSource, gradeScheme } = opts;

    // Ensure the ReligiousTradition node exists.
    await mergeReligiousTradition(tradition);

    // Build a stable Assessment key: <targetKeyProp>:<targetKeyValue>::<tradition>
    const assessmentKey = `${targetKeyProp}:${targetKeyValue}::${tradition}`;

    const cypher = `
        MATCH (target:${targetLabel} { ${targetKeyProp}: $targetKeyValue })
        MATCH (rt:ReligiousTradition { name: $tradition })
        MERGE (a:Assessment { pipeline_key: $assessmentKey })
        ON CREATE SET
            a.id = $assessmentId,
            a.created_at = datetime(),
            a.grade = $grade,
            a.grade_source = $gradeSource,
            a.grade_scheme = $gradeScheme,
            a.tradition = $tradition
        ON MATCH SET
            a.updated_at = datetime(),
            a.grade = $grade,
            a.grade_source = $gradeSource,
            a.grade_scheme = $gradeScheme
        MERGE (target)-[:HAS_ASSESSMENT]->(a)
        MERGE (a)-[:UNDER_SCHEME]->(rt)
    `;

    await runWrite(cypher, {
        targetKeyValue,
        tradition,
        assessmentKey,
        assessmentId: randomUUID(),
        grade,
        gradeSource,
        gradeScheme,
    });
}

// ─── loadNoExtantEvaluation ───────────────────────────────────────────────────

/**
 * Write an explicit 'no_extant_evaluation' placeholder :Assessment for a
 * tradition that has no verdict for this target. Makes coverage gaps explicit
 * rather than invisible (prevents silent nulls in grade analytics).
 */
export async function loadNoExtantEvaluation(
    targetLabel: 'Hadith' | 'Narrator',
    targetKeyProp: 'dataset_row_id' | 'pipeline_key' | 'scholar_indx',
    targetKeyValue: string | number,
    tradition: string
): Promise<void> {
    await loadAssessment({
        targetLabel,
        targetKeyProp,
        targetKeyValue,
        tradition,
        grade: 'no_extant_evaluation',
        gradeSource: 'system_placeholder',
        gradeScheme: schemeForTradition(tradition),
    });
}

// ─── migrateScalarAssessments ─────────────────────────────────────────────────

/**
 * Migration helper: migrate existing scalar `reliability` / `grade` properties
 * on :Narrator and :Hadith nodes into tradition-scoped :Assessment nodes,
 * then SET those scalar properties to null on the source nodes.
 *
 * Called from mode-fullregen.ts (workstream E) at the start of a full regen run.
 *
 * Phase-0 finding: 24,347 :Narrator nodes and ~N :Hadith nodes have legacy
 * scalar assessments. These are all treated as 'unspecified' tradition since
 * the original importer collapsed multi-tradition grades into one field.
 *
 * The scalar properties are nulled (not the nodes — NFR-2).
 */
export async function migrateScalarAssessments(): Promise<MigrationReport> {
    const errors: string[] = [];
    let narrators_migrated = 0;
    let hadiths_migrated = 0;
    let scalars_nulled = 0;

    // ── Migrate Narrator.reliability ─────────────────────────────────────────
    try {
        const narratorResult = await runQuery<{
            id: string;
            scholar_indx: number;
            reliability: string;
        }>(`
            MATCH (n:Narrator)
            WHERE n.reliability IS NOT NULL AND NOT n.tombstoned = true
            RETURN n.id AS id, n.scholar_indx AS scholar_indx, n.reliability AS reliability
        `);

        for (const row of narratorResult) {
            try {
                // Write Assessment node for unspecified tradition (legacy collapse).
                const assessmentKey = `scholar_indx:${row.scholar_indx}::unspecified_legacy`;
                await runWrite(`
                    MATCH (n:Narrator { scholar_indx: $scholarIndx })
                    MERGE (a:Assessment { pipeline_key: $assessmentKey })
                    ON CREATE SET
                        a.id = $assessmentId,
                        a.created_at = datetime(),
                        a.grade = $grade,
                        a.grade_source = 'legacy_scalar_migration',
                        a.grade_scheme = 'unspecified',
                        a.tradition = 'unspecified_legacy',
                        a.migrated_from = 'Narrator.reliability'
                    MERGE (n)-[:HAS_ASSESSMENT]->(a)
                `, {
                    scholarIndx: row.scholar_indx,
                    assessmentKey,
                    assessmentId: randomUUID(),
                    grade: row.reliability,
                });

                // Null the scalar on the Narrator node.
                await runWrite(`
                    MATCH (n:Narrator { id: $nodeId })
                    REMOVE n.reliability
                `, { nodeId: row.id });

                narrators_migrated++;
                scalars_nulled++;
            } catch (err) {
                errors.push(`Narrator ${row.scholar_indx}: ${err}`);
            }
        }
    } catch (err) {
        errors.push(`Narrator migration query failed: ${err}`);
    }

    // ── Migrate Hadith.grade (scalar) ─────────────────────────────────────────
    try {
        const hadithResult = await runQuery<{
            id: string;
            pipeline_key: string;
            dataset_row_id: number | null;
            grade: string;
            tradition: string;
        }>(`
            MATCH (h:Hadith)
            WHERE h.grade IS NOT NULL AND NOT h.tombstoned = true
            RETURN h.id AS id, h.pipeline_key AS pipeline_key,
                   h.dataset_row_id AS dataset_row_id,
                   h.grade AS grade, h.tradition AS tradition
        `);

        for (const row of hadithResult) {
            try {
                const tradition = row.tradition ?? 'unspecified_legacy';
                const targetKeyProp = row.dataset_row_id !== null ? 'dataset_row_id' : 'pipeline_key';
                const targetKeyValue = row.dataset_row_id !== null ? row.dataset_row_id : row.pipeline_key;
                const assessmentKey = `${targetKeyProp}:${targetKeyValue}::${tradition}_legacy`;

                await runWrite(`
                    MATCH (h:Hadith { id: $nodeId })
                    MERGE (a:Assessment { pipeline_key: $assessmentKey })
                    ON CREATE SET
                        a.id = $assessmentId,
                        a.created_at = datetime(),
                        a.grade = $grade,
                        a.grade_source = 'legacy_scalar_migration',
                        a.grade_scheme = $gradeScheme,
                        a.tradition = $tradition,
                        a.migrated_from = 'Hadith.grade'
                    MERGE (h)-[:HAS_ASSESSMENT]->(a)
                `, {
                    nodeId: row.id,
                    assessmentKey,
                    assessmentId: randomUUID(),
                    grade: row.grade,
                    gradeScheme: schemeForTradition(tradition),
                    tradition,
                });

                // Null the scalar grade on the Hadith node.
                await runWrite(`
                    MATCH (h:Hadith { id: $nodeId })
                    REMOVE h.grade
                `, { nodeId: row.id });

                hadiths_migrated++;
                scalars_nulled++;
            } catch (err) {
                errors.push(`Hadith ${row.id}: ${err}`);
            }
        }
    } catch (err) {
        errors.push(`Hadith migration query failed: ${err}`);
    }

    return { narrators_migrated, hadiths_migrated, scalars_nulled, errors };
}

// ─── GradingEntry ─────────────────────────────────────────────────────────────

/**
 * A single scholar grading parsed from the pipe-separated `gradings_full` field.
 *
 * Example input segment:
 *   "Allamah Baqir al-Majlisi:  صحيح     (Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25))"
 * Parsed as:
 *   { scholar: "Allamah Baqir al-Majlisi", grade: "صحيح",
 *     citation: "Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25)", tradition: <default> }
 */
export interface GradingEntry {
    /** e.g. "Allamah Baqir al-Majlisi" */
    scholar: string;
    /** e.g. "صحيح" — may be Arabic or Latin */
    grade: string;
    /** e.g. "Mirʾāt al-ʿUqūl fī Sharḥ Akhbār Āl al-Rasūl (1/25)" */
    citation: string;
    /** Tradition from the source dataset (passed in as defaultTradition). */
    tradition: Tradition;
}

// ─── parseGradingsFull ────────────────────────────────────────────────────────

/**
 * Parse the pipe-separated multi-scholar `gradings_full` CSV column into
 * individual GradingEntry objects.
 *
 * Format: `<scholar>: <grade> (<citation>) | <scholar>: <grade> (<citation>) | ...`
 *
 * Trimming is aggressive — Arabic whitespace and Latin whitespace are both
 * handled by String.prototype.trim().
 *
 * @param gradingsFull    Raw cell value from the CSV.
 * @param defaultTradition  Tradition of the source hadith (used for all entries).
 */
export function parseGradingsFull(gradingsFull: string, defaultTradition: Tradition): GradingEntry[] {
    if (!gradingsFull || !gradingsFull.trim()) return [];

    const segments = gradingsFull.split(' | ');
    const entries: GradingEntry[] = [];

    for (const segment of segments) {
        const colonIdx = segment.indexOf(':');
        if (colonIdx === -1) {
            console.warn('[assessment] parseGradingsFull: skipping malformed segment (no colon):', segment.trim());
            continue;
        }

        const scholar = segment.slice(0, colonIdx).trim();
        const rest = segment.slice(colonIdx + 1).trim();

        // Extract trailing (...) as citation. Handle nested parens by finding
        // the LAST closing paren and scanning back to the matching open paren.
        let grade: string;
        let citation: string;

        const lastCloseParen = rest.lastIndexOf(')');
        if (lastCloseParen !== -1) {
            // Walk back to find the matching opening paren.
            let depth = 0;
            let openIdx = -1;
            for (let i = lastCloseParen; i >= 0; i--) {
                if (rest[i] === ')') depth++;
                else if (rest[i] === '(') {
                    depth--;
                    if (depth === 0) { openIdx = i; break; }
                }
            }
            if (openIdx !== -1) {
                grade = rest.slice(0, openIdx).trim();
                citation = rest.slice(openIdx + 1, lastCloseParen).trim();
            } else {
                // Unbalanced parens — treat whole rest as grade.
                grade = rest;
                citation = '';
            }
        } else {
            grade = rest;
            citation = '';
        }

        if (!scholar || !grade) {
            console.warn('[assessment] parseGradingsFull: skipping empty scholar/grade in segment:', segment.trim());
            continue;
        }

        entries.push({ scholar, grade, citation, tradition: defaultTradition });
    }

    return entries;
}

// ─── LoadGradingsFullOpts ─────────────────────────────────────────────────────

export interface LoadGradingsFullOpts {
    /** Label of the node receiving the assessments. */
    targetLabel: 'Hadith' | 'Narrator';
    /** Business key property on the target node. */
    targetKeyProp: 'dataset_row_id' | 'pipeline_key' | 'scholar_indx';
    /** Business key value. */
    targetKeyValue: string | number;
    /** Tradition of the source (applied to every parsed entry). */
    sourceTradition: Tradition;
    /** Raw pipe-separated gradings_full string from the CSV. */
    gradingsFull: string;
}

// ─── loadGradingsFull ─────────────────────────────────────────────────────────

/**
 * Parse `gradings_full` and fan-out into N per-scholar :Assessment nodes using
 * the existing `loadAssessment`.
 *
 * Each Assessment's `grade_source` encodes the scholar name + citation so that
 * downstream queries can filter by scholar (e.g. WHERE a.grade_source STARTS WITH
 * 'Allamah Baqir al-Majlisi').
 *
 * Returns { written, skipped } — skipped counts segments that failed to parse.
 */
export async function loadGradingsFull(opts: LoadGradingsFullOpts): Promise<{ written: number; skipped: number }> {
    const { targetLabel, targetKeyProp, targetKeyValue, sourceTradition, gradingsFull } = opts;

    const entries = parseGradingsFull(gradingsFull, sourceTradition);
    let written = 0;
    let skipped = 0;

    for (const entry of entries) {
        try {
            const gradeSource = entry.citation
                ? `${entry.scholar} (${entry.citation})`
                : entry.scholar;

            await loadAssessment({
                targetLabel,
                targetKeyProp,
                targetKeyValue,
                tradition: entry.tradition,
                grade: entry.grade,
                gradeSource,
                gradeScheme: schemeForTradition(entry.tradition),
            });
            written++;
        } catch (err) {
            console.warn(
                `[assessment] loadGradingsFull: failed to write Assessment for scholar="${entry.scholar}":`,
                err,
            );
            skipped++;
        }
    }

    return { written, skipped };
}
