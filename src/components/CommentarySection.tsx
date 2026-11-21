'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';

interface Commentary {
    id: string;
    author: string;
    text: string;
    source_work: string;
    reference?: string;
    type: 'HADITH_COMMENTARY' | 'NARRATOR_BIOGRAPHY' | 'CHAIN_ANALYSIS' | 'OTHER';
}

interface CommentarySectionProps {
    commentaries: Commentary[];
    /** Kept for call-site compatibility; the public view is read-only. */
    narratorId?: string;
}

const COMMENTARY_TYPE_LABELS = {
    HADITH_COMMENTARY: 'Hadith Commentary',
    NARRATOR_BIOGRAPHY: 'Narrator Biography',
    CHAIN_ANALYSIS: 'Chain Analysis',
    OTHER: 'Other',
};

const COMMENTARY_TYPE_COLORS = {
    HADITH_COMMENTARY: {
        bg: 'bg-blue-500/20',
        border: 'border-blue-500/40',
        text: 'text-blue-300',
    },
    NARRATOR_BIOGRAPHY: {
        bg: 'bg-teal-500/20',
        border: 'border-teal-500/40',
        text: 'text-teal-300',
    },
    CHAIN_ANALYSIS: {
        bg: 'bg-orange-500/20',
        border: 'border-orange-500/40',
        text: 'text-orange-300',
    },
    OTHER: {
        bg: 'bg-gray-500/20',
        border: 'border-gray-500/40',
        text: 'text-gray-300',
    },
};

export function CommentarySection({ commentaries }: CommentarySectionProps) {
    const [filterType, setFilterType] = useState<string>('ALL');

    // Group commentaries by source work
    const groupedCommentaries = commentaries.reduce(
        (acc, commentary) => {
            const source = commentary.source_work || 'Unknown Source';
            if (!acc[source]) {
                acc[source] = [];
            }
            acc[source].push(commentary);
            return acc;
        },
        {} as Record<string, Commentary[]>
    );

    // Filter commentaries
    const filteredCommentaries =
        filterType === 'ALL'
            ? commentaries
            : commentaries.filter((c) => c.type === filterType);

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-white">Scholarly Commentaries</h2>
                <p className="text-white/60 text-sm mt-1" aria-live="polite">
                    {filteredCommentaries.length} {filteredCommentaries.length === 1 ? 'commentary' : 'commentaries'}
                </p>
            </div>

            {/* Filter Tabs */}
            {commentaries.length > 0 && (
                <div className="flex flex-wrap gap-2 pb-4 border-b border-white/10">
                    <button
                        type="button"
                        aria-pressed={filterType === 'ALL'}
                        onClick={() => setFilterType('ALL')}
                        className={`px-4 py-2 rounded-lg border transition-all ${
                            filterType === 'ALL'
                                ? 'bg-cyan-700 border-cyan-600 text-white'
                                : 'bg-white/5 border-white/20 text-white/70 hover:bg-white/10'
                        }`}
                    >
                        All ({commentaries.length})
                    </button>
                    {Object.entries(COMMENTARY_TYPE_LABELS).map(([type, label]) => {
                        const count = commentaries.filter((c) => c.type === type).length;
                        return count > 0 ? (
                            <button
                                type="button"
                                key={type}
                                aria-pressed={filterType === type}
                                onClick={() => setFilterType(type)}
                                className={`px-4 py-2 rounded-lg border transition-all ${
                                    filterType === type
                                        ? 'bg-cyan-700 border-cyan-600 text-white'
                                        : 'bg-white/5 border-white/20 text-white/70 hover:bg-white/10'
                                }`}
                            >
                                {label} ({count})
                            </button>
                        ) : null;
                    })}
                </div>
            )}

            {/* Commentaries Display */}
            {filteredCommentaries.length > 0 ? (
                <div className="space-y-4">
                    {Object.entries(groupedCommentaries).map(([source, sourceCommentaries]) => {
                        const filtered = filterType === 'ALL'
                            ? sourceCommentaries
                            : sourceCommentaries.filter((c) => c.type === filterType);

                        if (filtered.length === 0) return null;

                        return (
                            <div key={source} className="space-y-3">
                                <h3 className="text-lg font-semibold text-cyan-300 px-1">{source}</h3>
                                <div className="space-y-3">
                                    {filtered.map((commentary) => {
                                        const typeColors =
                                            COMMENTARY_TYPE_COLORS[commentary.type];

                                        return (
                                            <Card
                                                key={commentary.id}
                                                className="bg-white/5 border-white/10 hover:border-white/20 transition-all"
                                            >
                                                <CardContent className="pt-6">
                                                    <div className="space-y-3">
                                                        {/* Header */}
                                                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                                            <div>
                                                                <h4 className="font-semibold text-white">
                                                                    {commentary.author}
                                                                </h4>
                                                                {commentary.reference && (
                                                                    <p className="text-sm text-white/60 mt-1">
                                                                        {commentary.reference}
                                                                    </p>
                                                                )}
                                                            </div>
                                                            <div
                                                                className={`inline-flex px-3 py-1 rounded-md border text-xs font-semibold
                                                                    ${typeColors.bg} ${typeColors.border} ${typeColors.text}`}
                                                            >
                                                                {COMMENTARY_TYPE_LABELS[commentary.type]}
                                                            </div>
                                                        </div>

                                                        {/* Commentary Text */}
                                                        <p className="text-white/80 leading-relaxed text-sm">
                                                            {commentary.text}
                                                        </p>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <Card className="bg-white/5 border-white/10">
                    <CardContent className="py-12">
                        <div className="text-center">
                            <p className="text-white/60">
                                {filterType === 'ALL'
                                    ? 'No commentaries available yet.'
                                    : `No ${COMMENTARY_TYPE_LABELS[filterType as keyof typeof COMMENTARY_TYPE_LABELS]} commentaries found.`}
                            </p>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
