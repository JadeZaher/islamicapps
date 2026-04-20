'use client';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { AlertCircle, Star } from 'lucide-react';

interface GradingPanelProps {
    autoCalculatedGrade: string;
    displayGrade: string;
    transmissionType: string;
    chainHealthScore?: number;
}

export function GradingPanel({
    autoCalculatedGrade,
    displayGrade,
    transmissionType,
    chainHealthScore = 0,
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

    return (
        <div className="space-y-6">
            <div>
                <div className="flex items-center gap-2 mb-4">
                    <AlertCircle className="w-5 h-5 text-slate-400" />
                    <h3 className="text-lg font-semibold text-white">Auto-Analysis</h3>
                </div>

                <Card className="p-4 bg-slate-900/30 border-slate-700">
                    <div className="space-y-4">
                        {/* Display Grade */}
                        <div>
                            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                                Display Grade
                            </p>
                            <Badge className={getGradeBadgeColor(displayGrade)}>
                                {displayGrade || <span className="text-slate-400 italic">null</span>}
                            </Badge>
                        </div>

                        {/* Auto Grade */}
                        <div>
                            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                                Calculated Grade
                            </p>
                            <Badge className={getGradeBadgeColor(autoCalculatedGrade)}>
                                {autoCalculatedGrade || <span className="text-slate-400 italic">null</span>}
                            </Badge>
                        </div>

                        {/* Transmission Type */}
                        <div>
                            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">
                                Transmission Type
                            </p>
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="bg-slate-700/50 text-slate-300">
                                    {transmissionType || <span className="text-slate-400 italic">null</span>}
                                </Badge>
                                {transmissionType === 'MUTAWATIR' && (
                                    <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                                )}
                            </div>
                        </div>

                        {/* Chain Health Score */}
                        <div>
                            <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">
                                Chain Health Score
                            </p>
                            <div className="flex items-center gap-3">
                                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-emerald-500 transition-all"
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
                            <strong>Note:</strong> Auto-analysis is based on chain narrator reliability.
                            Algorithmic analysis cannot detect subtle defects like hidden
                            narrator biases or temporal impossibilities.
                        </p>
                    </div>
                </Card>
            </div>
        </div>
    );
}
