'use client';

interface TabaqahTimelineProps {
    currentTabaqah: 'PROPHET' | 'SAHABA' | 'TABI_UN' | 'TABI_TABI_IN';
}

const TABAQAH_LEVELS = [
    { key: 'PROPHET', label: 'Prophet Muhammad ﷺ', era: 'Generation 0' },
    { key: 'SAHABA', label: 'Companions (Sahaba)', era: 'Generation 1' },
    { key: 'TABI_UN', label: "Successors (Tabi'un)", era: 'Generation 2' },
    { key: 'TABI_TABI_IN', label: "Successors' Successors", era: 'Generation 3' },
] as const;

export function TabaqahTimeline({ currentTabaqah }: TabaqahTimelineProps) {
    const currentIndex = TABAQAH_LEVELS.findIndex((t) => t.key === currentTabaqah);

    return (
        <div className="w-full max-w-4xl">
            <h3 className="text-lg font-semibold text-white/80 mb-6">Generation (Tabaqah)</h3>
            <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-purple-500/50 via-purple-400/30 to-purple-500/50" />

                {/* Timeline items */}
                <div className="space-y-6">
                    {TABAQAH_LEVELS.map((level, index) => {
                        const isCurrent = level.key === currentTabaqah;
                        const isPast = index < currentIndex;

                        return (
                            <div key={level.key} className="relative flex items-start gap-6">
                                {/* Node */}
                                <div
                                    className={`relative z-10 w-16 h-16 rounded-full border-4 flex items-center justify-center
                                        transition-all duration-300 ${isCurrent
                                            ? 'bg-purple-500 border-purple-300 shadow-lg shadow-purple-500/50 scale-110'
                                            : isPast
                                                ? 'bg-purple-500/30 border-purple-500/50'
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
                                                ? 'bg-purple-500/20 border-purple-400/50 shadow-lg'
                                                : 'bg-white/5 border-white/10'
                                            }`}
                                    >
                                        <h4
                                            className={`text-lg font-semibold ${isCurrent ? 'text-purple-200' : 'text-white/70'}`}
                                        >
                                            {level.label}
                                        </h4>
                                        <p className={`text-sm mt-1 ${isCurrent ? 'text-purple-300/80' : 'text-white/50'}`}>
                                            {level.era}
                                        </p>
                                        {isCurrent && (
                                            <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-purple-600/40 rounded-full">
                                                <div className="w-2 h-2 rounded-full bg-purple-300 animate-pulse" />
                                                <span className="text-xs text-purple-200 font-medium">Current Level</span>
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
