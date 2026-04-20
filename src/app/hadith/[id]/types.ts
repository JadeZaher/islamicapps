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
    source_book: string;
    text_english: string | null;
    text_arabic: string | null;
}

export interface HadithNode {
    id: string;
    title: string | null;
    primary_topic: string | null;
    display_grade: string | null;
    auto_calculated_grade: string | null;
    transmission_type: string | null;
    text_english: string | null;
    text_arabic: string | null;
    isnad_arabic: string | null;
    chain_text_arabic: string | null;
    chapter: string | null;
    hadith_no: string | null;
    source: string | null;
    variations: MatnVariation[];
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
}
