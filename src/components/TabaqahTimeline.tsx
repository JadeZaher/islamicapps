'use client';

interface TabaqahTimelineProps {
    /** Tabaqah key; anything outside TABAQAH_LEVELS (or empty) renders as "not recorded". */
    currentTabaqah?: string | null;
}

const TABAQAH_LEVELS = [
    { key: 'PROPHET', label: 'Prophet Muhammad ﷺ', era: 'Generation 0' },
    { key: 'SAHABA', label: 'Companions (Sahaba)', era: 'Generation 1' },
    { key: 'TABI_UN', label: "Successors (Tabi'un)", era: 'Generation 2' },
    { key: 'TABI_TABI_IN', label: "Successors' Successors", era: 'Generation 3' },
    { key: 'LATER_SCHOLAR', label: 'Later scholars', era: 'Generation 4 and later' },
] as const;

export function TabaqahTimeline({ currentTabaqah }: TabaqahTimelineProps) {
    const currentIndex = TABAQAH_LEVELS.findIndex((t) => t.key === currentTabaqah);
    const isRecognised = currentIndex !== -1;

    return (
        <div className="w-full max-w-4xl">
            <h3 className="text-lg font-semibold text-white/80 mb-6">Generation (Tabaqah)</h3>
            {!isRecognised && (
                <p role="status" className="mb-4 text-sm text-white/60">
                    {currentTabaqah ? `Recorded as ${currentTabaqah.replaceAll('_', ' ').toLowerCase()}` : 'Generation not recorded'}
                </p>
            )}
            <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-cyan-500/30" />

                {/* Timeline items */}
                <div className="space-y-6" aria-label="Generation levels" role="list">
                    {TABAQAH_LEVELS.map((level, index) => {
                        const isCurrent = level.key === currentTabaqah;
                        const isPast = index < currentIndex;

                        return (
                            <div key={level.key} role="listitem" aria-current={isCurrent ? 'step' : undefined} className="relative flex items-start gap-6">
                                {/* Node */}
                                <div
                                    className={`relative z-10 w-16 h-16 rounded-full border-4 flex items-center justify-center
                                        transition-all duration-300 ${isCurrent
                                            ? 'bg-cyan-600 border-cyan-300 shadow-lg shadow-cyan-500/50 scale-110'
                                            : isPast
                                                ? 'bg-cyan-500/30 border-cyan-500/50'
                                                : 'bg-white/5 border-white/20'
                                        }`}
                                >
                                    <span
                                        className={`text-2xl font-bold ${isCurrent ? 'text-white' : 'text-white/60'}`}
                                    >
                                        {index}
                                    </span>
                                </div>

                                {/* Content */}
                                <div className="flex-1 pt-2">
                                    <div
                                        className={`p-4 rounded-lg border backdrop-blur-sm transition-all duration-300 ${isCurrent
                                                ? 'bg-cyan-500/15 border-cyan-400/50 shadow-lg'
                                                : 'bg-white/5 border-white/10'
                                            }`}
                                    >
                                        <h4
                                            className={`text-lg font-semibold ${isCurrent ? 'text-cyan-200' : 'text-white/70'}`}
                                        >
                                            {level.label}
                                        </h4>
                                        <p className={`text-sm mt-1 ${isCurrent ? 'text-cyan-300/80' : 'text-white/60'}`}>
                                            {level.era}
                                        </p>
                                        {isCurrent && (
                                            <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-cyan-700/40 rounded-full">
                                                <div className="w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
                                                <span className="text-xs text-cyan-200 font-medium">Current Level</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
