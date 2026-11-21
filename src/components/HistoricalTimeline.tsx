'use client';

import { useState } from 'react';

export interface HistoricalTimelineEvent {
    id: string;
    title: string;
    description: string;
    year_hijri: number;
    year_gregorian?: number;
    start_year_hijri?: number;
    start_year_gregorian?: number;
    end_year_hijri?: number;
    end_year_gregorian?: number;
    category?: string;
    citation_source?: string;
    citation_locator?: string;
    citation_url?: string;
    citation_retrieved_at?: string;
}

interface HistoricalTimelineProps {
    events: HistoricalTimelineEvent[];
    narratorBirthYear?: number;
    narratorDeathYear?: number;
    onEventSelect?: (eventId: string) => void;
    selectedEventId?: string | null;
}

interface CategoryStyle {
    bg: string;
    border: string;
    dot: string;
    label: string;
}

const CATEGORY_COLORS: Record<string, CategoryStyle> = {
    PROPHETIC_ERA: {
        bg: 'bg-violet-500/20',
        border: 'border-violet-500/40',
        dot: 'bg-violet-500',
        label: 'Prophetic era',
    },
    RASHIDUN: {
        bg: 'bg-amber-500/20',
        border: 'border-amber-500/40',
        dot: 'bg-amber-500',
        label: 'Rashidun',
    },
    UMAYYAD: {
        bg: 'bg-orange-500/20',
        border: 'border-orange-500/40',
        dot: 'bg-orange-500',
        label: 'Umayyad',
    },
    ABBASID: {
        bg: 'bg-purple-500/20',
        border: 'border-purple-500/40',
        dot: 'bg-purple-500',
        label: 'Abbasid',
    },
    SCHOLARLY: {
        bg: 'bg-blue-500/20',
        border: 'border-blue-500/40',
        dot: 'bg-blue-500',
        label: 'Scholarly',
    },
    MILITARY: {
        bg: 'bg-rose-500/20',
        border: 'border-rose-500/40',
        dot: 'bg-rose-500',
        label: 'Military',
    },
    POLITICAL: {
        bg: 'bg-red-500/20',
        border: 'border-red-500/40',
        dot: 'bg-red-500',
        label: 'Political',
    },
    SCIENTIFIC: {
        bg: 'bg-blue-500/20',
        border: 'border-blue-500/40',
        dot: 'bg-blue-500',
        label: 'Scientific',
    },
    CULTURAL: {
        bg: 'bg-teal-500/20',
        border: 'border-teal-500/40',
        dot: 'bg-teal-500',
        label: 'Cultural',
    },
    RELIGIOUS: {
        bg: 'bg-green-500/20',
        border: 'border-green-500/40',
        dot: 'bg-green-500',
        label: 'Religious',
    },
    SOCIAL: {
        bg: 'bg-cyan-500/20',
        border: 'border-cyan-500/40',
        dot: 'bg-cyan-500',
        label: 'Social',
    },
    OTHER: {
        bg: 'bg-gray-500/20',
        border: 'border-gray-500/40',
        dot: 'bg-gray-500',
        label: 'Other',
    },
};

function getCategoryStyle(category?: string): CategoryStyle {
    const known = category ? CATEGORY_COLORS[category] : undefined;
    if (known) return known;
    const normalizedLabel = category?.trim().replaceAll('_', ' ').toLowerCase() ?? '';
    return {
        ...CATEGORY_COLORS.OTHER,
        label: normalizedLabel
            ? normalizedLabel.replace(/^./, (character) => character.toUpperCase())
            : CATEGORY_COLORS.OTHER.label,
    };
}

function safeExternalUrl(value?: string): string | undefined {
    if (!value) return undefined;
    try {
        const parsed = new URL(value);
        return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : undefined;
    } catch {
        return undefined;
    }
}

export function HistoricalTimeline({
    events,
    narratorBirthYear,
    narratorDeathYear,
    onEventSelect,
    selectedEventId,
}: HistoricalTimelineProps) {
    const [expandedEventId, setExpandedEventId] = useState<string | null>(selectedEventId || null);
    const hasBirthYear = narratorBirthYear !== undefined;
    const hasDeathYear = narratorDeathYear !== undefined;

    // Sort events by year
    const sortedEvents = [...events].sort((a, b) => a.year_hijri - b.year_hijri);

    // Calculate the year range
    const allYears = [
        ...sortedEvents.map((e) => e.year_hijri),
        ...(narratorBirthYear !== undefined ? [narratorBirthYear] : []),
        ...(narratorDeathYear !== undefined ? [narratorDeathYear] : []),
    ];

    const minYear = Math.min(...allYears);
    const maxYear = Math.max(...allYears);
    const yearRange = maxYear - minYear || 1;

    const getEventPosition = (year: number) => {
        return ((year - minYear) / yearRange) * 100;
    };

    const isEventInNarratorLifetime = (event: HistoricalTimelineEvent) => {
        const eventStart = event.start_year_hijri ?? event.year_hijri;
        const eventEnd = event.end_year_hijri ?? eventStart;
        const afterBirth = narratorBirthYear === undefined || eventEnd >= narratorBirthYear;
        const beforeDeath = narratorDeathYear === undefined || eventStart <= narratorDeathYear;
        return afterBirth && beforeDeath;
    };

    return (
        <div className="w-full space-y-6">
            {/* Legend */}
            <div className="flex flex-wrap gap-4 pb-4 border-b border-white/10">
                {Object.entries(CATEGORY_COLORS).map(([key, colors]) => (
                    <div key={key} className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${colors.dot}`} />
                        <span className="text-sm text-white/70">{colors.label}</span>
                    </div>
                ))}
                {(hasBirthYear || hasDeathYear) && (
                    <>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full border-2 border-yellow-500 bg-transparent" />
                            <span className="text-sm text-white/70">Life Period</span>
                        </div>
                    </>
                )}
            </div>

            {/* Timeline */}
            <div className="relative">
                {/* Horizontal timeline line */}
                <div className="absolute top-16 left-0 right-0 h-1 bg-white/10" />

                {/* Life period indicators */}
                {narratorBirthYear !== undefined && narratorDeathYear !== undefined && (
                    <div className="absolute inset-0 w-full pointer-events-none">
                        {/* Life period background */}
                        <div
                            className="absolute top-0 bottom-0 bg-yellow-500/5 border-l-2 border-r-2 border-yellow-500/40"
                            style={{
                                left: `calc(${getEventPosition(narratorBirthYear)}% - 20px)`,
                                right: `calc(${100 - getEventPosition(narratorDeathYear)}% - 20px)`,
                            }}
                        />

                        {/* Birth marker */}
                        <div
                            className="absolute top-8 -translate-x-1/2 z-10"
                            style={{ left: `${getEventPosition(narratorBirthYear)}%` }}
                        >
                            <div className="relative">
                                <div className="w-6 h-6 rounded-full border-3 border-yellow-500 bg-yellow-500/20 flex items-center justify-center">
                                    <div className="w-2 h-2 rounded-full bg-yellow-500" />
                                </div>
                                <div className="mt-2 text-center">
                                    <div className="text-xs font-semibold text-yellow-300 whitespace-nowrap">
                                        Born
                                    </div>
                                    <div className="text-xs text-yellow-300/70">{narratorBirthYear} AH</div>
                                </div>
                            </div>
                        </div>

                        {/* Death marker */}
                        <div
                            className="absolute top-8 -translate-x-1/2 z-10"
                            style={{ left: `${getEventPosition(narratorDeathYear)}%` }}
                        >
                            <div className="relative">
                                <div className="w-6 h-6 rounded-full border-3 border-red-500 bg-red-500/20 flex items-center justify-center">
                                    <div className="w-2 h-2 rounded-full bg-red-500" />
                                </div>
                                <div className="mt-2 text-center">
                                    <div className="text-xs font-semibold text-red-300 whitespace-nowrap">
                                        Died
                                    </div>
                                    <div className="text-xs text-red-300/70">{narratorDeathYear} AH</div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Events */}
                <div className="pt-32 pb-8 space-y-6">
                    {sortedEvents.map((event) => {
                        const colors = getCategoryStyle(event.category);
                        const isInLifetime = isEventInNarratorLifetime(event);
                        const isExpanded = expandedEventId === event.id;
                        const citationUrl = safeExternalUrl(event.citation_url);
                        const hasCitation = Boolean(
                            event.citation_source || event.citation_locator || citationUrl || event.citation_retrieved_at,
                        );

                        return (
                            <div
                                key={event.id}
                                className="relative"
                                style={{ marginLeft: `${getEventPosition(event.year_hijri)}%` }}
                            >
                                {/* Dot and connector */}
                                <div className="absolute -left-6 top-4 w-12 h-12 flex items-center justify-center">
                                    <div
                                        className={`w-4 h-4 rounded-full border-2 ${colors.dot} border-white/30
                                            ${isInLifetime ? 'ring-2 ring-yellow-500/50' : ''} transition-all`}
                                    />
                                </div>

                                {/* Event card */}
                                <button
                                    onClick={() => {
                                        setExpandedEventId(isExpanded ? null : event.id);
                                        onEventSelect?.(event.id);
                                    }}
                                    className={`w-96 text-left p-4 rounded-lg border transition-all duration-300 cursor-pointer
                                        ${isExpanded
                                        ? `${colors.bg} ${colors.border} border-2`
                                        : `bg-white/5 border-white/10 hover:${colors.bg} hover:${colors.border}`
                                    }`}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold
                                                    ${colors.bg} ${colors.border} border`}>
                                                    {colors.label}
                                                </span>
                                                {isInLifetime && (
                                                    <span className="text-xs font-semibold text-yellow-300 bg-yellow-500/20 px-2 py-1 rounded border border-yellow-500/30">
                                                        During Lifetime
                                                    </span>
                                                )}
                                            </div>
                                            <h4 className="font-semibold text-white text-sm group-hover:text-cyan-300">
                                                {event.title}
                                            </h4>
                                        </div>
                                        <div className="flex flex-col items-end gap-1">
                                            <span className="text-sm font-bold text-white/80">
                                                {event.year_hijri} AH
                                            </span>
                                            {event.year_gregorian !== undefined && (
                                                <span className="text-xs text-white/60">
                                                    {event.year_gregorian} CE
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Expanded content */}
                                    {isExpanded && (
                                        <div className="mt-4 pt-4 border-t border-white/20 space-y-2">
                                            <p className="text-sm text-white/80 leading-relaxed">
                                                {event.description}
                                            </p>
                                        </div>
                                    )}
                                </button>
                                {isExpanded && hasCitation && (
                                    <div className="mt-2 w-96 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-xs text-white/60">
                                        <p>
                                            <span className="font-semibold text-white/75">Citation:</span>{' '}
                                            {event.citation_source || 'Source not named'}
                                            {event.citation_locator && ` · ${event.citation_locator}`}
                                        </p>
                                        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                                            {citationUrl && (
                                                <a
                                                    href={citationUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    referrerPolicy="no-referrer"
                                                    className="text-cyan-300 underline underline-offset-2 hover:text-cyan-200"
                                                >
                                                    Open source
                                                </a>
                                            )}
                                            {event.citation_retrieved_at && (
                                                <span>Retrieved {event.citation_retrieved_at}</span>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {sortedEvents.length === 0 && (
                <div className="text-center py-12">
                    <p className="text-white/60">No historical events recorded for this period.</p>
                </div>
            )}
        </div>
    );
}
