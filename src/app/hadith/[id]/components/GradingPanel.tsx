'use client';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, Award, Star } from 'lucide-react';

interface ScholarVerdict {
    id: string;
    grade: string;
    reasoning: string;
    confidence_level: string;
    date_assessed: string;
    scholar: {
        name: string;
        era: string;
        school: string;
    };
}

interface GradingPanelProps {
    autoCalculatedGrade: string;
    displayGrade: string;
    transmissionType: string;
    verdicts: ScholarVerdict[];
    chainHealthScore?: number;
    onAddVerdict?: () => void;
}

export function GradingPanel({
    autoCalculatedGrade,
    displayGrade,
    transmissionType,
    verdicts,
    chainHealthScore = 0,
    onAddVerdict,
}: GradingPanelProps) {
    const getGradeBadgeColor = (grade: string) => {
        switch (grade) {
            case 'SAHIH':
                return 'bg-green-500/20 text-green-400 border-green-500/30';
            case 'HASAN':
                return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
            case 'DAIF':
                return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
            case 'MAWDU':
                return 'bg-red-500/20 text-red-400 border-red-500/30';
            default:
                return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    const getConfidenceBadgeColor = (level: string) => {
        switch (level) {
            case 'HIGH':
                return 'bg-emerald-500/20 text-emerald-400';
            case 'MEDIUM':
                return 'bg-yellow-500/20 text-yellow-400';
            case 'LOW':
                return 'bg-rose-500/20 text-rose-400';
            default:
                return 'bg-gray-500/20 text-gray-400';
        }
    };

    return (
        <div className="space-y-6">
            {/* Scholar Verdicts Section (Primary) */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Award className="w-5 h-5 text-amber-400" />
                        Scholar Verdicts
                    </h3>
                    {onAddVerdict && (
                        <Button onClick={onAddVerdict} variant="outline" size="sm">
                            Add Verdict
                        </Button>
                    )}
                </div>

                {verdicts.length > 0 ? (
                    <div className="space-y-3">
                        {verdicts.map((verdict) => (
                            <Card key={verdict.id} className="p-4 bg-slate-900/50 border-slate-700">
                                <div className="flex items-start justify-between mb-2">
                                    <div>
                                        <p className="font-semibold text-white">{verdict.scholar.name}</p>
                                        <p className="text-sm text-slate-400">
                                            {verdict.scholar.school} • {verdict.scholar.era}
                                        </p>
                                    </div>
                                    <Badge className={getGradeBadgeColor(verdict.grade)}>
                                        {verdict.grade}
                                    </Badge>
                                </div>
                                <p className="text-sm text-slate-300 leading-relaxed mb-3">
                                    {verdict.reasoning}
                                </p>
                                <div className="flex items-center gap-3 text-xs text-slate-400">
                                    <Badge variant="secondary" className={getConfidenceBadgeColor(verdict.confidence_level)}>
                                        {verdict.confidence_level} Confidence
                                    </Badge>
                                    <span>{verdict.date_assessed}</span>
                                </div>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <Card className="p-6 bg-slate-900/30 border-slate-800 border-dashed">
                        <p className="text-slate-400 text-center text-sm">
                            No scholar verdicts yet. Auto-calculated grade is being used.
                        </p>
                    </Card>
                )}
            </div>

            {/* Divider */}
            <div className="border-t border-slate-800" />

            {/* Auto-Analysis Section (Secondary) */}
            <div>
                <div className="flex items-center gap-2 mb-4">
                    <AlertCircle className="w-5 h-5 text-slate-400" />
                    <h3 className="text-lg font-semibold text-white">Auto-Analysis</h3>
                </div>

                <Card className="p-4 bg-slate-900/30 border-slate-700">
                    <div className="space-y-4">
                        {/* Auto Grade */}
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">
                                Calculated Grade
                            </p>
                            <Badge className={getGradeBadgeColor(autoCalculatedGrade)}>
                                {autoCalculatedGrade || <span className="text-slate-500 italic">null</span>}
                            </Badge>
                        </div>

                        {/* Transmission Type */}
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">
                                Transmission Type
                            </p>
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300">
                                    {transmissionType || <span className="text-slate-500 italic">null</span>}
                                </Badge>
                                {transmissionType === 'MUTAWATIR' && (
                                    <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                                )}
                            </div>
                        </div>

                        {/* Chain Health Score */}
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide mb-2">
                                Chain Health Score
                            </p>
                            <div className="flex items-center gap-3">
                                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-emerald-500 to-green-400 transition-all"
                                        style={{ width: `${chainHealthScore}%` }}
                                    />
                                </div>
                                <span className="text-sm font-semibold text-white w-12 text-right">
                                    {chainHealthScore}%
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Disclaimer */}
                    <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                        <p className="text-xs text-amber-200/80 leading-relaxed">
                            <strong>Note:</strong> Auto-analysis is supplementary. Refer to scholar verdicts for
                            authoritative grading. Algorithmic analysis cannot detect subtle defects like hidden
                            narrator biases or temporal impossibilities.
                        </p>
                    </div>
                </Card>
            </div>
        </div>
    );
}
