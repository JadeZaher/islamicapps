'use client';

import { useState } from 'react';

interface HistoricalEvent {
    id: string;
    title: string;
    description: string;
    year_hijri: number;
    year_gregorian: number;
    category: 'POLITICAL' | 'SCIENTIFIC' | 'CULTURAL' | 'RELIGIOUS' | 'OTHER';
}

interface HistoricalTimelineProps {
    events: HistoricalEvent[];
    narratorBirthYear?: number;
    narratorDeathYear?: number;
    onEventSelect?: (eventId: string) => void;
    selectedEventId?: string | null;
}

const CATEGORY_COLORS = {
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
        bg: 'bg-purple-500/20',
        border: 'border-purple-500/40',
        dot: 'bg-purple-500',
        label: 'Cultural',
    },
    RELIGIOUS: {
        bg: 'bg-green-500/20',
        border: 'border-green-500/40',
        dot: 'bg-green-500',
        label: 'Religious',
    },
    OTHER: {
        bg: 'bg-gray-500/20',
        border: 'border-gray-500/40',
        dot: 'bg-gray-500',
        label: 'Other',
    },
};

export function HistoricalTimeline({
    events,
    narratorBirthYear,
    narratorDeathYear,
    onEventSelect,
    selectedEventId,
}: HistoricalTimelineProps) {
    const [expandedEventId, setExpandedEventId] = useState<string | null>(selectedEventId || null);

    // Sort events by year
    const sortedEvents = [...events].sort((a, b) => a.year_hijri - b.year_hijri);

    // Calculate the year range
    const allYears = [
        ...sortedEvents.map((e) => e.year_hijri),
        ...(narratorBirthYear ? [narratorBirthYear] : []),
        ...(narratorDeathYear ? [narratorDeathYear] : []),
    ];

    const minYear = Math.min(...allYears);
    const maxYear = Math.max(...allYears);
    const yearRange = maxYear - minYear || 1;

    const getEventPosition = (year: number) => {
        return ((year - minYear) / yearRange) * 100;
    };

    const isEventInNarratorLifetime = (eventYear: number) => {
        const afterBirth = !narratorBirthYear || eventYear >= narratorBirthYear;
        const beforeDeath = !narratorDeathYear || eventYear <= narratorDeathYear;
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
                {(narratorBirthYear || narratorDeathYear) && (
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
                <div className="absolute top-16 left-0 right-0 h-1 bg-gradient-to-r from-white/10 via-purple-500/30 to-white/10" />

                {/* Life period indicators */}
                {narratorBirthYear && narratorDeathYear && (
                    <div className="absolute top-0 bottom-0 pointer-events-none">
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
                    {sortedEvents.map((event, index) => {
                        const colors = CATEGORY_COLORS[event.category];
                        const isInLifetime = isEventInNarratorLifetime(event.year_hijri);
                        const isExpanded = expandedEventId === event.id;

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
                                            <h4 className="font-semibold text-white text-sm group-hover:text-purple-300">
                                                {event.title}
                                            </h4>
                                        </div>
                                        <div className="flex flex-col items-end gap-1">
                                            <span className="text-sm font-bold text-white/80">
                                                {event.year_hijri} AH
                                            </span>
                                            <span className="text-xs text-white/60">
                                                {event.year_gregorian} CE
                                            </span>
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
