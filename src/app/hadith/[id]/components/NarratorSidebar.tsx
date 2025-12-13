'use client';

import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { X, MapPin, Calendar } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface NarratorDetails {
    id: string;
    name_arabic: string;
    name_english: string;
    reliability: string;
    tabaqah: string;
    bio: string;
    birth_year_hijri?: number;
    death_year_hijri?: number;
    geographic_region?: string;
    other_hadiths: Array<{
        id: string;
        title: string;
    }>;
}

interface NarratorSidebarProps {
    narrator: NarratorDetails | null;
    isOpen: boolean;
    onClose: () => void;
}

export function NarratorSidebar({ narrator, isOpen, onClose }: NarratorSidebarProps) {
    const router = useRouter();

    if (!isOpen || !narrator) return null;

    const getReliabilityColor = (reliability: string) => {
        switch (reliability) {
            case 'THIQA':
                return 'bg-green-500/20 text-green-400 border-green-500/30';
            case 'SADUQ':
                return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
            case 'DAIF':
                return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
            case 'KADHAB':
                return 'bg-red-500/20 text-red-400 border-red-500/30';
            case 'MAJHUL':
                return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
            default:
                return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                onClick={onClose}
            />

            {/* Sidebar */}
            <div className="fixed right-0 top-0 h-full w-full md:w-96 bg-slate-900 border-l border-slate-700 z-50 overflow-y-auto">
                <div className="p-6">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-6">
                        <div>
                            <h2 className="text-xl font-bold text-white mb-1">
                                {narrator.name_english}
                            </h2>
                            <p className="text-lg text-amber-400 font-arabic">
                                {narrator.name_arabic}
                            </p>
                        </div>
                        <Button
                            onClick={onClose}
                            variant="ghost"
                            size="icon"
                            className="text-slate-400 hover:text-white"
                        >
                            <X className="w-5 h-5" />
                        </Button>
                    </div>

                    {/* Reliability Badge */}
                    <div className="mb-6">
                        <Badge className={getReliabilityColor(narrator.reliability)}>
                            {narrator.reliability}
                        </Badge>
                        <Badge variant="secondary" className="ml-2 bg-slate-700/50 text-slate-300">
                            {narrator.tabaqah?.replace('_', ' ')}
                        </Badge>
                    </div>

                    {/* Dates and Location */}
                    <div className="space-y-3 mb-6">
                        {(narrator.birth_year_hijri || narrator.death_year_hijri) && (
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <Calendar className="w-4 h-4" />
                                <span>
                                    {narrator.birth_year_hijri && `${narrator.birth_year_hijri} - `}
                                    {narrator.death_year_hijri && `${narrator.death_year_hijri} AH`}
                                </span>
                            </div>
                        )}
                        {narrator.geographic_region && (
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <MapPin className="w-4 h-4" />
                                <span>{narrator.geographic_region}</span>
                            </div>
                        )}
                    </div>

                    {/* Biography */}
                    <div className="mb-6">
                        <h3 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">
                            Biography
                        </h3>
                        <p className="text-sm text-slate-300 leading-relaxed">
                            {narrator.bio}
                        </p>
                    </div>

                    {/* Other Hadiths */}
                    {narrator.other_hadiths && narrator.other_hadiths.length > 0 && (
                        <div>
                            <h3 className="text-sm font-semibold text-white uppercase tracking-wide mb-3">
                                Other Hadiths Narrated ({narrator.other_hadiths.length})
                            </h3>
                            <div className="space-y-2">
                                {narrator.other_hadiths.map((hadith) => (
                                    <Card
                                        key={hadith.id}
                                        className="p-3 bg-slate-800/50 border-slate-700 hover:bg-slate-800 transition-colors cursor-pointer"
                                        onClick={() => {
                                            router.push(`/hadith/${hadith.id}`);
                                            onClose();
                                        }}
                                    >
                                        <p className="text-sm text-white">{hadith.title}</p>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
