import fs from 'fs';
import os from 'os';
import path from 'path';
import { randomUUID } from 'crypto';

// ─── Shared enums (mirrors comparative-actions.ts) ──────────────────────────

export type ParallelType =
    | 'CONDEMNATION'
    | 'CULTURAL_BLEED'
    | 'SHARED_SOURCE'
    | 'DIRECT_BORROWING'
    | 'APOLOGETIC'
    | 'DISPUTED';

export type IsraIliyyatStatus = 'MUWAFIQ' | 'MUKHALIF' | 'MASKUT_ANHU' | 'NONE';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type CandidateStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'COMMITTED';

// ─── Core candidate interface ────────────────────────────────────────────────

export interface ParallelCandidate {
    // Identity
    id: string; // UUID generated at discovery time

    // Source hadith (denormalised for review convenience)
    hadith_id: string;
    hadith_title: string;
    hadith_text_english: string;

    // LLM-suggested values
    suggested_tradition: string; // Free-form, e.g. "Zoroastrianism", "Yoruba"
    suggested_parallel_type: ParallelType;
    suggested_isra_iliyyat_status: IsraIliyyatStatus;
    suggested_confidence_level: ConfidenceLevel;
    suggested_source_text_title: string;
    suggested_source_text_canonical_reference: string; // e.g. "Avesta, Yasna 49.11"
    suggested_source_text_en: string;
    suggested_scholarly_analysis: string;
    suggested_motif_tags: string[];

    // API verification metadata
    api_source: string; // e.g. "sefaria" | "bible_api" | "llm_only"
    api_verified: boolean;

    // Reviewer override fields (set via Review UI)
    override_parallel_type?: ParallelType;
    override_isra_iliyyat_status?: IsraIliyyatStatus;
    override_confidence_level?: ConfidenceLevel;
    override_scholarly_analysis?: string;

    // Workflow state
    status: CandidateStatus;
    reviewer_notes?: string;
    generated_at: string; // ISO timestamp
    reviewed_at?: string;
    committed_at?: string;
}

// ─── Override shape used in review actions ───────────────────────────────────

export interface CandidateOverrides {
    override_parallel_type?: ParallelType;
    override_isra_iliyyat_status?: IsraIliyyatStatus;
    override_confidence_level?: ConfidenceLevel;
    override_scholarly_analysis?: string;
}

// ─── File I/O utilities ──────────────────────────────────────────────────────

export function loadCandidates(filePath: string): ParallelCandidate[] {
    if (!fs.existsSync(filePath)) {
        return [];
    }
    const raw = fs.readFileSync(filePath, 'utf8');
    try {
        return JSON.parse(raw) as ParallelCandidate[];
    } catch {
        throw new Error(`Failed to parse staging file at ${filePath}. File may be corrupted.`);
    }
}

export function saveCandidates(filePath: string, candidates: ParallelCandidate[]): void {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
    const tmpPath = path.join(os.tmpdir(), `parallel-candidates-${randomUUID()}.json`);
    fs.writeFileSync(tmpPath, JSON.stringify(candidates, null, 2), 'utf8');
    fs.renameSync(tmpPath, filePath);
}
