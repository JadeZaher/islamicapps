interface TabaqahTimelineProps {
    /** Tabaqah key; anything outside TABAQAH_LEVELS (or empty) is shown as recorded, or "Unknown". */
    currentTabaqah?: string | null;
}

const TABAQAH_LEVELS = [
    { key: 'PROPHET', label: 'The Prophet' },
    { key: 'SAHABA', label: 'Companions (ṣaḥāba)' },
    { key: 'TABIUN', label: 'Successors (tābiʿūn)' },
    { key: 'ATBA_TABIUN', label: 'Successors of the Successors' },
    { key: 'ATBA_ATBA', label: 'Their successors' },
    { key: 'LATER_SCHOLAR', label: 'Later scholars' },
] as const;

/** Generation (ṭabaqa) as a six-step scale; only a recorded level is highlighted, unknown is said plainly. */
export function TabaqahTimeline({ currentTabaqah }: TabaqahTimelineProps) {
    const currentIndex = TABAQAH_LEVELS.findIndex((level) => level.key === currentTabaqah);
    if (currentIndex === -1) {
        return currentTabaqah?.trim()
            ? <span>{currentTabaqah.replaceAll('_', ' ').toLowerCase()}</span>
            : <span className="text-slate-500">Unknown</span>;
    }
    return (
        <span className="flex flex-col gap-2">
            <span>{TABAQAH_LEVELS[currentIndex].label}</span>
            <span className="flex gap-1" aria-hidden="true">
                {TABAQAH_LEVELS.map((level, index) => (
                    <span
                        key={level.key}
                        title={level.label}
                        className={`h-1 w-8 rounded-full ${index === currentIndex ? 'bg-emerald-400' : 'bg-slate-700'}`}
                    />
                ))}
            </span>
        </span>
    );
}
