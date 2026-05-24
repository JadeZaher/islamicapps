/**
 * Prop types for the HadithClientPage component.
 *
 * These types mirror the actual data shapes produced by:
 *   - getHadithById() -> HadithNode
 *   - getFullChainGraph() -> { nodes: GraphNode[], edges: GraphEdge[] }
 *   - getParallelsForHadith() -> ParallelRecord[]
 *   - chain health score calculation in page.tsx -> number
 */

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
}

/** A node in the isnad graph returned by getFullChainGraph() */
export interface GraphNode {
    id: string;
    label?: string;
    reliability?: string;
    tabaqah?: string;
    name_english?: string;
    name_arabic?: string;
    [key: string]: unknown;
}

/** An edge in the isnad graph returned by getFullChainGraph() */
export interface GraphEdge {
    source: string;
    target: string;
    type?: string;
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
    /** Percentage (0-100) of THIQA narrators in the chain. 0 when chain is empty. */
    chainHealthScore: number;
    /** Whether the chain traces back to the Prophet (via Sahabi or explicit mention). */
    tracesToProphet: boolean;
}
