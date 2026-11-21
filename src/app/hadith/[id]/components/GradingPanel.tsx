'use client';

import { Badge } from '@/components/ui/badge';
import { Star } from 'lucide-react';

interface GradingPanelProps {
    autoCalculatedGrade?: string | null;
    displayGrade?: string | null;
    transmissionType?: string | null;
    /** 0-100, or null when the chain carries no narrator verdicts to compute it from. */
    chainHealthScore?: number | null;
}

const GRADE_COLORS: Record<string, string> = {
    SAHIH: 'bg-green-500/20 text-green-400 border-green-500/30',
    HASAN: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    DAIF: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    MAWDU: 'bg-red-500/20 text-red-400 border-red-500/30',
};
const NEUTRAL_BADGE = 'bg-gray-500/20 text-gray-300 border-gray-500/30';

function Row({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">{label}</p>
            {children}
        </div>
    );
}

/** Renders only the rulings the data contains; returns null when there are none. */
export function GradingPanel({
    autoCalculatedGrade,
    displayGrade,
    transmissionType,
    chainHealthScore = null,
}: GradingPanelProps) {
    const hasScore = typeof chainHealthScore === 'number';
    if (!displayGrade && !autoCalculatedGrade && !transmissionType && !hasScore) return null;

    return (
        <section aria-labelledby="grading-heading" className="space-y-4">
            <h2 id="grading-heading" className="text-lg font-semibold text-white">Grading</h2>

            {displayGrade && (
                <Row label="Grade">
                    <Badge className={GRADE_COLORS[displayGrade] ?? NEUTRAL_BADGE}>{displayGrade}</Badge>
                </Row>
            )}

            {autoCalculatedGrade && (
                <Row label="Calculated grade">
                    <Badge className={GRADE_COLORS[autoCalculatedGrade] ?? NEUTRAL_BADGE}>{autoCalculatedGrade}</Badge>
                </Row>
            )}

            {transmissionType && (
                <Row label="Transmission">
                    <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="bg-slate-700/50 text-slate-300">
                            {transmissionType}
                        </Badge>
                        {transmissionType === 'MUTAWATIR' && (
                            <Star className="w-4 h-4 text-amber-400 fill-amber-400" aria-hidden="true" />
                        )}
                    </div>
                </Row>
            )}

            {hasScore && (
                <Row label="Narrators rated thiqa">
                    <div className="flex items-center gap-3">
                        <div
                            className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden"
                            role="meter"
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={chainHealthScore}
                            aria-label="Share of chain narrators rated thiqa"
                        >
                            <div className="h-full bg-emerald-500" style={{ width: `${chainHealthScore}%` }} />
                        </div>
                        <span className="text-sm font-semibold text-white w-12 text-right">{chainHealthScore}%</span>
                    </div>
                </Row>
            )}
        </section>
    );
}
