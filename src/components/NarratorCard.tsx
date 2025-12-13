'use client';

import Link from 'next/link';
import { ReliabilityBadge } from './ReliabilityBadge';

interface NarratorCardProps {
    narrator: {
        id: string;
        name_arabic: string;
        name_english: string;
        reliability: 'THIQA' | 'SADUQ' | 'DAIF' | 'MAJHUL' | 'KADHAB';
        tabaqah: string;
        death_year_hijri?: number;
    };
    onClick?: () => void;
}

export function NarratorCard({ narrator, onClick }: NarratorCardProps) {
    const content = (
        <div
            className="group relative bg-white/5 backdrop-blur-lg rounded-xl p-6 border border-white/10 
                hover:bg-white/10 hover:border-purple-500/50 transition-all duration-300 cursor-pointer
                hover:shadow-xl hover:shadow-purple-500/20 hover:-translate-y-1"
            onClick={onClick}
        >
            <div className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                        <h3 className="text-xl font-bold text-white group-hover:text-purple-300 transition-colors">
                            {narrator.name_english}
                        </h3>
                        <p className="text-lg text-purple-200/80 font-arabic mt-1">
                            {narrator.name_arabic}
                        </p>
                    </div>
                    {narrator.death_year_hijri && (
                        <div className="flex flex-col items-end">
                            <span className="text-sm text-white/60">Died</span>
                            <span className="text-lg font-semibold text-purple-300">
                                {narrator.death_year_hijri} AH
                            </span>
                        </div>
                    )}
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <ReliabilityBadge reliability={narrator.reliability} />
                    <div className="px-3 py-1 rounded-md bg-purple-500/20 border border-purple-500/30">
                        <span className="text-sm text-purple-200">{narrator.tabaqah}</span>
                    </div>
                </div>
            </div>

            {/* Hover indicator */}
            <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-purple-400">→</span>
            </div>
        </div>
    );

    if (onClick) {
        return content;
    }

    return <Link href={`/narrator/${narrator.id}`}>{content}</Link>;
}
