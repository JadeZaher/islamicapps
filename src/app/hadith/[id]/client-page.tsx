'use client';

import { useState } from 'react';
import { IsnadGraph } from './components/IsnadGraph';
import { GradingPanel } from './components/GradingPanel';
import { NarratorSidebar } from './components/NarratorSidebar';
import { getNarratorDetails } from '@/app/actions/graph-actions';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface HadithClientPageProps {
    hadith: any;
    nodes: any[];
    edges: any[];
    chainHealthScore: number;
}

export function HadithClientPage({
    hadith,
    nodes,
    edges,
    chainHealthScore,
}: HadithClientPageProps) {
    const [selectedNarrator, setSelectedNarrator] = useState<any>(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const handleNodeClick = async (node: any) => {
        const details = await getNarratorDetails(node.id);
        setSelectedNarrator(details);
        setIsSidebarOpen(true);
    };

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
        <div className="min-h-screen bg-slate-950 text-white p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-start justify-between mb-4">
                        <div>
                            <h1 className="text-3xl font-bold mb-2">
                                {hadith.title || <span className="text-slate-500 italic">null</span>}
                            </h1>
                            <p className="text-slate-400">
                                {hadith.primary_topic || <span className="text-slate-600 italic">null</span>}
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <Badge className={getGradeBadgeColor(hadith.display_grade)}>
                                {hadith.display_grade || <span className="text-slate-500">null</span>}
                            </Badge>
                            {hadith.transmission_type === 'MUTAWATIR' && (
                                <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                                    ⭐ Mutawatir
                                </Badge>
                            )}
                            {hadith.transmission_type && hadith.transmission_type !== 'MUTAWATIR' && (
                                <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                                    {hadith.transmission_type}
                                </Badge>
                            )}
                            {!hadith.transmission_type && (
                                <Badge className="bg-slate-500/20 text-slate-500 border-slate-500/30">
                                    null
                                </Badge>
                            )}
                        </div>
                    </div>
                </div>

                {/* Main Content: Graph + Sidebar */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                    {/* Graph Canvas */}
                    <div className="lg:col-span-2">
                        <Card className="bg-slate-900/50 border-slate-800 overflow-hidden">
                            <div className="p-4 border-b border-slate-800">
                                <h2 className="text-lg font-semibold">Isnad Chain Visualization</h2>
                                <p className="text-sm text-slate-400 mt-1">
                                    Click nodes to view narrator details
                                </p>
                            </div>
                            <div className="w-full h-[600px]">
                                <IsnadGraph
                                    nodes={nodes}
                                    edges={edges}
                                    onNodeClick={handleNodeClick}
                                />
                            </div>
                        </Card>
                    </div>

                    {/* Grading Panel */}
                    <div>
                        <Card className="bg-slate-900/50 border-slate-800 p-6">
                            <GradingPanel
                                autoCalculatedGrade={hadith.auto_calculated_grade}
                                displayGrade={hadith.display_grade}
                                transmissionType={hadith.transmission_type}
                                verdicts={hadith.verdicts || []}
                                chainHealthScore={chainHealthScore}
                            />
                        </Card>
                    </div>
                </div>

                {/* Matn Variations */}
                {hadith.variations && hadith.variations.length > 0 && (
                    <Card className="bg-slate-900/50 border-slate-800 p-6">
                        <h2 className="text-xl font-semibold mb-4">Text Variations (Matn)</h2>
                        <Tabs defaultValue="0" className="w-full">
                            <TabsList className="mb-4">
                                {hadith.variations.map((variation: any, index: number) => (
                                    <TabsTrigger key={index} value={index.toString()}>
                                        {variation.source_book}
                                    </TabsTrigger>
                                ))}
                            </TabsList>
                            {hadith.variations.map((variation: any, index: number) => (
                                <TabsContent key={index} value={index.toString()} className="space-y-4">
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">
                                            Arabic
                                        </h3>
                                        <p className="text-lg leading-loose font-arabic text-amber-100">
                                            {variation.text_arabic}
                                        </p>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">
                                            English Translation
                                        </h3>
                                        <p className="text-base leading-relaxed text-slate-300">
                                            {variation.text_english}
                                        </p>
                                    </div>
                                </TabsContent>
                            ))}
                        </Tabs>
                    </Card>
                )}
            </div>

            {/* Narrator Sidebar */}
            <NarratorSidebar
                narrator={selectedNarrator}
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
            />
        </div>
    );
}
