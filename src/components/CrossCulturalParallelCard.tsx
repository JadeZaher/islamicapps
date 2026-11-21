import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import { Card, CardContent } from '@/components/ui/card';
import { TraditionBadge, ParallelTypeBadge, IsraIliyyatBadge } from '@/components/TraditionBadge';

interface MotifTag {
    id: string;
    name: string;
    category: string;
}

interface CrossCulturalParallelCardProps {
    parallel: {
        id: string;
        parallel_type: string;
        isra_iliyyat_status: string;
        confidence_level: string;
        hadith_excerpt_en?: string | null;
        source_text_original?: string | null;
        source_text_en?: string | null;
        scholarly_analysis?: string | null;
        provenance?: string | null;
        reviewed?: boolean | null;
    };
    tradition: {
        id: string;
        name: string;
    };
    sourceText: {
        id: string;
        title: string;
        canonical_reference?: string | null;
        tradition_name?: string | null;
    };
    hadith?: {
        id: string;
        title: string;
        display_grade?: string;
    };
    motifTags?: MotifTag[];
    showHadithLink?: boolean;
}

const CONFIDENCE_COLORS: Record<string, string> = {
    HIGH: 'text-accent',
    MEDIUM: 'text-ink-muted',
    LOW: 'text-danger',
};

const MOTIF_CATEGORY_COLORS: Record<string, string> = {
    ESCHATOLOGY: 'bg-transparent text-danger',
    CREATION: 'bg-sunken text-accent',
    PROPHETIC_STORIES: 'bg-sunken text-ink-muted',
    LEGAL: 'bg-sunken text-ink-muted',
    WISDOM: 'bg-accent-wash text-accent',
    PERSIAN_INFLUENCE: 'bg-sunken text-ink-muted',
    COSMOLOGY: 'bg-sunken text-ink-muted',
};

/** True when the record is flagged as machine-proposed (provenance field) or explicitly unreviewed. */
export function isMachineProposed(parallel: { provenance?: string | null; reviewed?: boolean | null; origin?: string | null }): boolean {
    return parallel.provenance === 'machine' || parallel.origin === 'ai_research' || parallel.reviewed === false;
}

export function MachineProposedBadge() {
    return (
        <span className="inline-block px-2 py-0.5 type-label">
            Machine-proposed · unreviewed
        </span>
    );
}

export function CrossCulturalParallelCard({
    parallel,
    tradition,
    sourceText,
    hadith,
    motifTags = [],
    showHadithLink = false,
}: CrossCulturalParallelCardProps) {
    return (
        <Card className="pb-4">
            <CardContent className="pt-5 space-y-4">
                {/* Header badges */}
                <div className="flex flex-wrap gap-2 items-center">
                    <TraditionBadge tradition={tradition.name} />
                    <ParallelTypeBadge type={parallel.parallel_type} />
                    <IsraIliyyatBadge status={parallel.isra_iliyyat_status} />
                    {isMachineProposed(parallel) && <MachineProposedBadge />}
                    {parallel.confidence_level && (
                        <span
                            className={`text-xs font-medium ${CONFIDENCE_COLORS[parallel.confidence_level] ?? 'text-ink-muted'}`}
                        >
                            {parallel.confidence_level} confidence
                        </span>
                    )}
                </div>

                {/* Source reference */}
                <div className="text-xs text-ink-muted">
                    <span className="font-semibold text-ink">{sourceText.title}</span>
                    {sourceText.canonical_reference && (
                        <span> · {sourceText.canonical_reference}</span>
                    )}
                </div>

                {/* Side-by-side text comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Hadith excerpt */}
                    {parallel.hadith_excerpt_en && (
                        <div className="p-4 bg-sunken border border-rule">
                            <p className="text-xs font-semibold text-accent uppercase tracking-wide mb-2">
                                Hadith Text
                            </p>
                            <p className="text-sm text-ink-muted leading-relaxed whitespace-pre-line">
                                {parallel.hadith_excerpt_en}
                            </p>
                        </div>
                    )}

                    {/* Source text from other tradition */}
                    {(parallel.source_text_en || parallel.source_text_original) && (
                        <div className="p-4 bg-sunken border border-rule overflow-hidden">
                            <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2 wrap-break-word">
                                {tradition.name} Source
                            </p>
                            {parallel.source_text_original && (
                                <p dir="auto" className="text-sm text-ink-muted/80 leading-relaxed mb-2 font-serif whitespace-pre-line text-start">
                                    {parallel.source_text_original}
                                </p>
                            )}
                            {parallel.source_text_en && parallel.source_text_original && (
                                <hr className="border-rule my-2" />
                            )}
                            {parallel.source_text_en && (
                                <p className="text-sm text-ink-muted leading-relaxed italic whitespace-pre-line">
                                    {parallel.source_text_en}
                                </p>
                            )}
                        </div>
                    )}
                </div>

                {/* Scholarly analysis */}
                {parallel.scholarly_analysis && (
                    <div className="p-3 bg-sunken border border-rule">
                        <p className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-1">
                            Scholarly Analysis
                        </p>
                        <div className="text-sm text-ink leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-2 prose-headings:text-ink prose-strong:text-ink prose-a:text-accent">
                            <ReactMarkdown>{parallel.scholarly_analysis}</ReactMarkdown>
                        </div>
                    </div>
                )}

                {/* Motif tags */}
                {motifTags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                        {motifTags.map((tag) => (
                            <span
                                key={tag.id}
                                className={`text-xs px-2 py-0.5  ${MOTIF_CATEGORY_COLORS[tag.category] ?? 'bg-sunken text-ink-muted'}`}
                            >
                                {tag.name}
                            </span>
                        ))}
                    </div>
                )}

                {/* Link to hadith */}
                {showHadithLink && hadith && (
                    <div className="pt-2 border-t border-rule">
                        <Link
                            href={`/hadith/${hadith.id}`}
                            className="text-sm text-accent hover:text-accent transition-colors"
                        >
                            → {hadith.title}
                            {hadith.display_grade && (
                                <span className="ml-2 text-xs text-ink-muted">({hadith.display_grade})</span>
                            )}
                        </Link>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
