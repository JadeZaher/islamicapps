/**
 * Prop types for the HadithClientPage component.
 *
 * Data now comes from the Postgres query layer (src/db/queries): getPublicHadith, getChainGraph,
 * getPublicParallelsForHadith. page.tsx adapts those contracts to the legacy keys below; the section 9.4
 * fields (`assessments`, the mention-keyed node fields) are carried alongside so the client can switch to them.
 */
import type { ChainNode, HadithAssessmentGroup } from '@/db/queries/contracts';

export type { ChainNode, HadithAssessmentGroup };

export interface MatnVariation {
    source_book?: string;
    text_english: string | null;
    text_arabic: string | null;
    /** Discriminator: 'hadith_node' when synthesized from the parent :Hadith node,
     *  otherwise absent (legacy :MatnVariation child). */
    source?: string;
    id?: string;
}

export interface HadithNode {
    id: string;
    /** v1 alias derived from chapter/category by getHadithById. */
    title: string | null;
    /** v1 alias derived from category by getHadithById. */
    primary_topic: string | null;
    display_grade: string | null;
    auto_calculated_grade: string | null;
    transmission_type: string | null;
    /** v1 alias of text_en. */
    text_english: string | null;
    /** v1 alias of text_ar. */
    text_arabic: string | null;
    /** Mirrored from sanad (v2 canonical field). */
    isnad_arabic: string | null;
    /** Mirrored from sanad (v2 canonical field). */
    chain_text_arabic: string | null;
    chapter: string | null;
    hadith_no: string | null;
    source: string | null;
    variations: MatnVariation[];
    // ─── v2 canonical fields ────────────────────────────────────────────────
    /** v2: canonical English text. */
    text_en?: string | null;
    /** v2: canonical Arabic text. */
    text_ar?: string | null;
    /** v2: Arabic matn (narrative portion, post-isnad). */
    matn_ar?: string | null;
    /** v2: English matn (narrative portion, post-isnad). */
    matn_en?: string | null;
    /** v2: isnad text (the chain of transmitters, free-text Arabic). */
    sanad?: string | null;
    /** v2: collection category (replaces v1 primary_topic). */
    category?: string | null;
    /** v2: volume number/label within the source. */
    volume?: string | null;
    /** v2: chapter number/label. */
    chapter_no?: string | null;
    /** v2: source-specific original hadith id (may differ from internal id). */
    hadith_id?: string | null;
    /** v2: madhab (Hanafi/Maliki/Shafi'i/Hanbali/...). */
    school?: string | null;
    /** v2: chain type (marfu'/mawquf/maqtu'/etc.). */
    chain_type?: string | null;
    /** v2: who the hadith is attributed to. */
    attributed_to?: string | null;
    /** v2: narration_level / sanad_confidence labels. */
    narration_level?: string | null;
    sanad_confidence?: string | null;
    /** v2: tradition (Sunni|Imami|Zaydi|Ibadi). */
    tradition?: string | null;
    /**
     * Section 9.4: grades per tradition, replacing display_grade / auto_calculated_grade / transmission_type
     * (always null now). An empty group means "no assessment recorded" for that tradition.
     */
    assessments?: HadithAssessmentGroup[];
}

/**
 * A chain position. `id` is the narrator ID only when `is_link`; otherwise it is the mention ID (`node_id`) and
 * `name_arabic` carries the surface as written, which must render without a narrator link (section 9.4).
 */
export interface GraphNode extends Omit<Partial<ChainNode>, 'position' | 'chain_id'> {
    id: string;
    label?: string;
    reliability?: string | null;
    tabaqah?: string;
    name_english?: string;
    name_arabic?: string;
    chain_id?: string;
    chain_index?: number | null;
    position?: number | null;
    chain_position?: number | null;
    chain_schema?: 'v2' | 'legacy';
    [key: string]: unknown;
}

/** An edge in the isnad graph returned by getFullChainGraph() */
export interface GraphEdge {
    source: string;
    target: string;
    type?: string;
    chain_id?: string;
    chain_index?: number | null;
    source_position?: number | null;
    target_position?: number | null;
    chain_schema?: 'v2' | 'legacy';
    [key: string]: unknown;
}

/** The tradition object nested inside a ParallelRecord */
export interface TraditionRef {
    id: string;
    name: string;
}

/** The source-text object nested inside a ParallelRecord */
export interface SourceTextRef {
    id: string;
    title: string;
    canonical_reference?: string | null;
    tradition_name?: string | null;
}

/** A motif tag nested inside a ParallelRecord */
export interface MotifTag {
    id: string;
    name: string;
    category: string;
}

/**
 * Shape returned by getParallelsForHadith() — each element is the spread of
 * CrossCulturalParallel node properties plus the joined tradition, source_text
 * and motif_tags.
 */
export interface ParallelRecord {
    id: string;
    parallel_type: string;
    isra_iliyyat_status: string;
    confidence_level: string;
    hadith_excerpt_en?: string | null;
    source_text_original?: string | null;
    source_text_en?: string | null;
    scholarly_analysis?: string | null;
    /** Joined ReligiousTradition node */
    tradition: TraditionRef;
    /** Joined SourceText node */
    source_text: SourceTextRef;
    /** Joined MotifTag nodes */
    motif_tags: MotifTag[];
    [key: string]: unknown;
}

export interface HadithClientPageProps {
    hadith: HadithNode;
    nodes: GraphNode[];
    edges: GraphEdge[];
    parallels: ParallelRecord[];
}
