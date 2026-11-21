import { GradeBadge } from '@/components/badges';
import { TraditionBadge } from '@/components/TraditionBadge';
import type { HadithAssessmentGroup } from '../types';
import { GradingCredit } from './family/SourceCredits';

const KIND_LABELS: Record<string, string> = {
    cited_ruling: 'Ruling',
    compiler_criterion: "Compiler's criterion",
    compiler_statement: "Compiler's statement",
};

/** Grades per tradition, each attributed to its grader and citation; side by side, none overriding another. */
export function Assessments({ groups, hadithId }: { groups: HadithAssessmentGroup[]; hadithId: string }) {
    if (groups.length === 0) return null;
    return (
        <ul>
            {groups.map((group) => (
                <li key={group.tradition} className="grid gap-2 border-b border-rule py-3 first:pt-0 last:border-b-0 sm:grid-cols-[8rem_1fr] sm:gap-6">
                    <div>
                        <TraditionBadge tradition={group.tradition} />
                    </div>
                    {group.assessments.length === 0 ? (
                        <p className="type-small text-ink-muted">No assessment recorded</p>
                    ) : (
                        <ul className="space-y-3">
                            {group.assessments.map((assessment, index) => (
                                <li key={index} className="type-small">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <GradeBadge grade={assessment.grade_canonical ?? assessment.grade_raw} />
                                        <span className="text-ink" dir="auto">{assessment.grade_raw}</span>
                                    </div>
                                    <p className="mt-1 text-ink-muted">
                                        {KIND_LABELS[assessment.kind] ?? assessment.kind}
                                        {assessment.grader ? ` · ${assessment.grader}` : ' · grader not recorded'}
                                        {assessment.citation_raw && (
                                            <> · <span dir="auto">{assessment.citation_raw}</span></>
                                        )}
                                    </p>
                                </li>
                            ))}
                            <li>
                                <GradingCredit hadithId={hadithId} className="!text-xs !leading-4" />
                            </li>
                        </ul>
                    )}
                </li>
            ))}
        </ul>
    );
}
