/**
 * you-research-client.ts
 *
 * Client for the you.com Research API.
 * POST https://api.you.com/v1/research
 *
 * Also handles parsing the structured assessment block from the markdown response.
 */

// ─── API types ────────────────────────────────────────────────────────────────

export type ResearchEffort = 'lite' | 'standard' | 'deep' | 'exhaustive';

export interface YouResearchSource {
    url: string;
    title?: string;
    snippets?: string[];
}

export interface YouResearchResponse {
    content: string;   // Markdown with numbered citations
    sources: YouResearchSource[];
}

// ─── Parsed structured assessment ────────────────────────────────────────────

export type ParallelExistsValue = 'YES' | 'PARTIAL' | 'NO';
export type ParsedParallelType =
    | 'CONDEMNATION'
    | 'CULTURAL_BLEED'
    | 'SHARED_SOURCE'
    | 'DIRECT_BORROWING'
    | 'APOLOGETIC'
    | 'DISPUTED'
    | 'NONE';
export type ParsedConfidence = 'HIGH' | 'MEDIUM' | 'LOW';
export type ParsedIsraStatus = 'MUWAFIQ' | 'MUKHALIF' | 'MASKUT_ANHU' | 'NONE';

export interface StructuredAssessment {
    parallel_exists: ParallelExistsValue;
    parallel_type: ParsedParallelType;
    confidence: ParsedConfidence;
    source_title: string;
    source_reference: string;
    source_quote: string;
    isra_status: ParsedIsraStatus;
    motif_tags: string[];
    /** True if the structured block was found and parsed; false if we had to use defaults */
    parsed: boolean;
}

// ─── API call ─────────────────────────────────────────────────────────────────

export async function callYouResearch(
    query: string,
    apiKey: string,
    effort: ResearchEffort = 'standard'
): Promise<YouResearchResponse> {
    const response = await fetch('https://api.you.com/v1/research', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey,
        },
        body: JSON.stringify({
            input: query,
            research_effort: effort,
        }),
    });

    if (!response.ok) {
        const body = await response.text().catch(() => '');
        throw new Error(`you.com Research API error ${response.status}: ${body}`);
    }

    const data = await response.json() as {
        output?: {
            content?: string;
            content_type?: string;
            sources?: YouResearchSource[];
        };
    };

    return {
        content: data.output?.content ?? '',
        sources: data.output?.sources ?? [],
    };
}

// ─── Response parser ──────────────────────────────────────────────────────────

const VALID_PARALLEL_TYPES = new Set([
    'CONDEMNATION',
    'CULTURAL_BLEED',
    'SHARED_SOURCE',
    'DIRECT_BORROWING',
    'APOLOGETIC',
    'DISPUTED',
    'NONE',
]);

const VALID_ISRA = new Set(['MUWAFIQ', 'MUKHALIF', 'MASKUT_ANHU', 'NONE']);

function extractField(block: string, key: string): string {
    // Matches "KEY: value" allowing value to span until the next KEY: line
    const pattern = new RegExp(`^${key}:\\s*(.+?)(?=\\n[A-Z_]+:|$)`, 'ms');
    const match = block.match(pattern);
    return match ? match[1].trim().replace(/^\[|\]$/g, '') : '';
}

export function parseStructuredAssessment(markdown: string): StructuredAssessment {
    const blockMatch = markdown.match(
        /---STRUCTURED ASSESSMENT---([\s\S]*?)---END ASSESSMENT---/
    );

    if (!blockMatch) {
        return defaultAssessment(false);
    }

    const block = blockMatch[1];

    const parallelExists = extractField(block, 'PARALLEL_EXISTS');
    const parallelType = extractField(block, 'PARALLEL_TYPE');
    const confidence = extractField(block, 'CONFIDENCE');
    const sourceTitle = extractField(block, 'PRIMARY_SOURCE_TITLE');
    const sourceRef = extractField(block, 'PRIMARY_SOURCE_REFERENCE');
    const sourceQuote = extractField(block, 'PRIMARY_SOURCE_QUOTE');
    const israStatus = extractField(block, 'ISRA_STATUS');
    const motifTagsRaw = extractField(block, 'MOTIF_TAGS');

    const motifTags = motifTagsRaw
        ? motifTagsRaw.split(',').map((t) => t.trim()).filter(Boolean)
        : [];

    return {
        parallel_exists: (['YES', 'PARTIAL', 'NO'].includes(parallelExists)
            ? parallelExists
            : 'NO') as ParallelExistsValue,
        parallel_type: (VALID_PARALLEL_TYPES.has(parallelType)
            ? parallelType
            : 'NONE') as ParsedParallelType,
        confidence: (['HIGH', 'MEDIUM', 'LOW'].includes(confidence)
            ? confidence
            : 'LOW') as ParsedConfidence,
        source_title: sourceTitle === 'N/A' ? '' : sourceTitle,
        source_reference: sourceRef === 'N/A' ? '' : sourceRef,
        source_quote: sourceQuote === 'N/A' ? '' : sourceQuote,
        isra_status: (VALID_ISRA.has(israStatus) ? israStatus : 'NONE') as ParsedIsraStatus,
        motif_tags: motifTags,
        parsed: true,
    };
}

// ─── Source embedding ────────────────────────────────────────────────────────

/**
 * Replaces [[N]] and [[N, M, ...]] citation markers in you.com markdown
 * with clickable markdown links to the source URLs, and appends a
 * numbered reference list at the bottom.
 *
 * Citations are 1-indexed: [[1]] → sources[0].
 */
export function embedSourceCitations(
    content: string,
    sources: YouResearchSource[]
): string {
    if (!sources.length) return content;

    // Strip the structured assessment block — we don't need it in the display text
    const displayContent = content
        .replace(/---STRUCTURED ASSESSMENT---[\s\S]*?---END ASSESSMENT---/, '')
        .trimEnd();

    // Track which source indices are actually referenced
    const referenced = new Set<number>();

    // Replace [[N]] and [[N, M, ...]] with inline markdown links
    const withLinks = displayContent.replace(
        /\[\[(\d+(?:\s*,\s*\d+)*)\]\]/g,
        (_match, nums: string) => {
            const indices = nums.split(',').map((s: string) => parseInt(s.trim(), 10));
            return indices
                .map((n) => {
                    const idx = n - 1; // 1-indexed → 0-indexed
                    const src = sources[idx];
                    if (!src) return `[${n}]`;
                    referenced.add(idx);
                    const title = src.title || src.url;
                    return `[${n}](${src.url} "${title.replace(/"/g, "'")}")`;
                })
                .join(' ');
        }
    );

    // Build a reference list of all cited sources
    const refEntries = Array.from(referenced)
        .sort((a, b) => a - b)
        .map((idx) => {
            const src = sources[idx];
            const title = src.title || src.url;
            return `${idx + 1}. [${title}](${src.url})`;
        });

    if (refEntries.length === 0) return withLinks;

    return `${withLinks}\n\n---\n\n**Sources**\n\n${refEntries.join('\n')}`;
}

function defaultAssessment(parsed: boolean): StructuredAssessment {
    return {
        parallel_exists: 'NO',
        parallel_type: 'NONE',
        confidence: 'LOW',
        source_title: '',
        source_reference: '',
        source_quote: '',
        isra_status: 'NONE',
        motif_tags: [],
        parsed,
    };
}
