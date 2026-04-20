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
        hadith_excerpt_en?: string;
        source_text_original?: string;
        source_text_en?: string;
        scholarly_analysis?: string;
    };
    tradition: {
        id: string;
        name: string;
    };
    sourceText: {
        id: string;
        title: string;
        canonical_reference?: string;
        tradition_name?: string;
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
    HIGH: 'text-green-400',
    MEDIUM: 'text-yellow-400',
    LOW: 'text-red-400',
};

const MOTIF_CATEGORY_COLORS: Record<string, string> = {
    ESCHATOLOGY: 'bg-red-500/10 text-red-300',
    CREATION: 'bg-green-500/10 text-green-300',
    PROPHETIC_STORIES: 'bg-blue-500/10 text-blue-300',
    LEGAL: 'bg-orange-500/10 text-orange-300',
    WISDOM: 'bg-teal-500/10 text-teal-300',
    PERSIAN_INFLUENCE: 'bg-amber-500/10 text-amber-300',
    COSMOLOGY: 'bg-indigo-500/10 text-indigo-300',
};

export function CrossCulturalParallelCard({
    parallel,
    tradition,
    sourceText,
    hadith,
    motifTags = [],
    showHadithLink = false,
}: CrossCulturalParallelCardProps) {
    return (
        <Card className="bg-white/5 border-white/10">
            <CardContent className="pt-5 space-y-4">
                {/* Header badges */}
                <div className="flex flex-wrap gap-2 items-center">
                    <TraditionBadge tradition={tradition.name} />
                    <ParallelTypeBadge type={parallel.parallel_type} />
                    <IsraIliyyatBadge status={parallel.isra_iliyyat_status} />
                    {parallel.confidence_level && (
                        <span
                            className={`text-xs font-medium ${CONFIDENCE_COLORS[parallel.confidence_level] ?? 'text-slate-400'}`}
                        >
                            {parallel.confidence_level} confidence
                        </span>
                    )}
                </div>

                {/* Source reference */}
                <div className="text-xs text-slate-400">
                    <span className="font-semibold text-slate-300">{sourceText.title}</span>
                    {sourceText.canonical_reference && (
                        <span> · {sourceText.canonical_reference}</span>
                    )}
                </div>

                {/* Side-by-side text comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Hadith excerpt */}
                    {parallel.hadith_excerpt_en && (
                        <div className="p-4 bg-slate-800/50 border border-slate-600/30 rounded-lg">
                            <p className="text-xs font-semibold text-cyan-300 uppercase tracking-wide mb-2">
                                Hadith Text
                            </p>
                            <p className="text-sm text-white/80 leading-relaxed whitespace-pre-line">
                                {parallel.hadith_excerpt_en}
                            </p>
                        </div>
                    )}

                    {/* Source text from other tradition */}
                    {(parallel.source_text_en || parallel.source_text_original) && (
                        <div className="p-4 bg-amber-900/20 border border-amber-500/20 rounded-lg overflow-hidden">
                            <p className="text-xs font-semibold text-amber-300 uppercase tracking-wide mb-2 wrap-break-word">
                                {tradition.name} Source
                            </p>
                            {parallel.source_text_original && (
                                <p className="text-sm text-amber-100/80 leading-relaxed mb-2 font-serif whitespace-pre-line">
                                    {parallel.source_text_original}
                                </p>
                            )}
                            {parallel.source_text_en && parallel.source_text_original && (
                                <hr className="border-amber-500/20 my-2" />
                            )}
                            {parallel.source_text_en && (
                                <p className="text-sm text-white/70 leading-relaxed italic whitespace-pre-line">
                                    {parallel.source_text_en}
                                </p>
                            )}
                        </div>
                    )}
                </div>

                {/* Scholarly analysis */}
                {parallel.scholarly_analysis && (
                    <div className="p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg">
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                            Scholarly Analysis
                        </p>
                        <div className="text-sm text-slate-300 leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-2 prose-headings:text-slate-200 prose-strong:text-white prose-a:text-cyan-400">
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
                                className={`text-xs px-2 py-0.5 rounded ${MOTIF_CATEGORY_COLORS[tag.category] ?? 'bg-slate-700/40 text-slate-400'}`}
                            >
                                {tag.name}
                            </span>
                        ))}
                    </div>
                )}

                {/* Link to hadith */}
                {showHadithLink && hadith && (
                    <div className="pt-2 border-t border-white/10">
                        <Link
                            href={`/hadith/${hadith.id}`}
                            className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                            → {hadith.title}
                            {hadith.display_grade && (
                                <span className="ml-2 text-xs text-slate-400">({hadith.display_grade})</span>
                            )}
                        </Link>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
