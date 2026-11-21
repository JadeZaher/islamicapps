import { GradeBadge } from '@/components/badges';

interface GradingPanelProps {
    /** Grade as recorded on the source row; shown attributed to the source, never as the archive's verdict. */
    displayGrade?: string | null;
    transmissionType?: string | null;
}

/** Inline grade and transmission labels the source row records. Computed grades and scores are never shown. */
export function GradingPanel({ displayGrade, transmissionType }: GradingPanelProps) {
    if (!displayGrade && !transmissionType) return null;
    return (
        <>
            {displayGrade && (
                <span className="inline-flex items-center gap-1.5" title="Grade as recorded in the source collection">
                    <span className="text-xs text-slate-500">Source grade</span>
                    <GradeBadge grade={displayGrade} />
                </span>
            )}
            {transmissionType && (
                <span className="rounded border border-slate-700 px-2 py-0.5 text-xs text-slate-300">
                    {transmissionType.toLowerCase()}
                </span>
            )}
        </>
    );
}
