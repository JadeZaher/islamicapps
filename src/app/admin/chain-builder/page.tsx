'use client';

import { searchNarrators, createChain, validateChainOrder, getAllHadiths } from '@/app/actions/graph-actions';
import { NarratorCard } from '@/components/NarratorCard';
import { useState, useEffect } from 'react';

export default function ChainBuilderPage() {
    const [step, setStep] = useState(1);
    const [selectedHadith, setSelectedHadith] = useState<any>(null);
    const [hadithList, setHadithList] = useState<any[]>([]);
    const [selectedChain, setSelectedChain] = useState<any[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [narratorResults, setNarratorResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [validationError, setValidationError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Load hadiths on mount
    useEffect(() => {
        getAllHadiths().then(setHadithList);
    }, []);

    // Search narrators with debounce
    useEffect(() => {
        const timer = setTimeout(async () => {
            if (searchTerm.trim()) {
                setIsSearching(true);
                const results = await searchNarrators(searchTerm);
                setNarratorResults(results);
                setIsSearching(false);
            } else {
                setNarratorResults([]);
            }
        }, 300);

        return () => clearTimeout(timer);
    }, [searchTerm]);

    const addNarratorToChain = async (narrator: any) => {
        const newChain = [...selectedChain, narrator];
        setSelectedChain(newChain);

        // Validate chain order
        const narratorIds = newChain.map((n) => n.id);
        const validation = await validateChainOrder(narratorIds);

        if (!validation.valid) {
            setValidationError(validation.error || 'Invalid chain order');
        } else {
            setValidationError(null);
        }

        setSearchTerm('');
        setNarratorResults([]);
    };

    const removeNarratorFromChain = async (index: number) => {
        const newChain = selectedChain.filter((_, i) => i !== index);
        setSelectedChain(newChain);

        if (newChain.length > 1) {
            const narratorIds = newChain.map((n) => n.id);
            const validation = await validateChainOrder(narratorIds);
            setValidationError(validation.valid ? null : validation.error || 'Invalid chain order');
        } else {
            setValidationError(null);
        }
    };

    const handleSaveChain = async () => {
        if (!selectedHadith || selectedChain.length < 2) {
            alert('Please select a hadith and add at least 2 narrators to the chain');
            return;
        }

        setIsSaving(true);
        try {
            // For now, we'll create a simple variation if one doesn't exist
            // In a full implementation, you'd select an existing variation or create one
            const variationId = 'temp-variation-id'; // This should be selected or created
            const narratorIds = selectedChain.map((n) => n.id);

            await createChain(selectedHadith.id, variationId, narratorIds);

            setSuccessMessage('Chain created successfully!');
            setTimeout(() => {
                setStep(1);
                setSelectedHadith(null);
                setSelectedChain([]);
                setSuccessMessage(null);
            }, 2000);
        } catch (error) {
            alert('Error creating chain: ' + (error instanceof Error ? error.message : 'Unknown error'));
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-12 px-4">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-white mb-2">Chain Builder</h1>
                    <p className="text-white/70">Create new transmission chains for hadiths</p>
                </div>

                {/* Progress Steps */}
                <div className="mb-8 bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
                    <div className="flex items-center justify-between">
                        {[
                            { num: 1, label: 'Select Hadith' },
                            { num: 2, label: 'Build Chain' },
                            { num: 3, label: 'Review & Save' },
                        ].map((s, idx) => (
                            <div key={s.num} className="flex items-center flex-1">
                                <div
                                    className={`flex items-center justify-center w-12 h-12 rounded-full border-2 font-bold transition-all ${step >= s.num
                                            ? 'bg-purple-600 border-purple-400 text-white'
                                            : 'bg-white/5 border-white/20 text-white/40'
                                        }`}
                                >
                                    {s.num}
                                </div>
                                <div className="ml-3">
                                    <p
                                        className={`font-semibold ${step >= s.num ? 'text-white' : 'text-white/40'}`}
                                    >
                                        {s.label}
                                    </p>
                                </div>
                                {idx < 2 && (
                                    <div
                                        className={`flex-1 h-1 mx-4 rounded ${step > s.num ? 'bg-purple-600' : 'bg-white/10'}`}
                                    />
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Success Message */}
                {successMessage && (
                    <div className="mb-6 p-4 bg-green-500/20 border border-green-500/40 rounded-lg">
                        <p className="text-green-200 text-center font-semibold">✓ {successMessage}</p>
                    </div>
                )}

                {/* Step 1: Select Hadith */}
                {step === 1 && (
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                        <h2 className="text-2xl font-bold text-white mb-6">Select a Hadith</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {hadithList.map((hadith) => (
                                <button
                                    key={hadith.id}
                                    onClick={() => {
                                        setSelectedHadith(hadith);
                                        setStep(2);
                                    }}
                                    className="text-left p-6 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/50 
                                        rounded-xl transition-all duration-300 group"
                                >
                                    <h3 className="text-xl font-semibold text-white group-hover:text-purple-300 transition-colors mb-2">
                                        {hadith.title}
                                    </h3>
                                    <p className="text-sm text-white/60">{hadith.primary_topic}</p>
                                </button>
                            ))}
                        </div>

                        {hadithList.length === 0 && (
                            <div className="text-center py-12">
                                <div className="text-4xl mb-4">📚</div>
                                <p className="text-white/60">No hadiths available. Please add hadiths first.</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Step 2: Build Chain */}
                {step === 2 && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Search Narrators */}
                        <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                            <h2 className="text-2xl font-bold text-white mb-6">Search Narrators</h2>
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Search by name..."
                                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white 
                                    placeholder-white/40 focus:outline-none focus:border-purple-500 mb-4"
                            />

                            {isSearching && (
                                <div className="text-center py-8">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500 mx-auto"></div>
                                </div>
                            )}

                            <div className="space-y-3 max-h-96 overflow-y-auto">
                                {narratorResults.map((narrator) => (
                                    <div key={narrator.id}>
                                        <NarratorCard
                                            narrator={narrator}
                                            onClick={() => addNarratorToChain(narrator)}
                                        />
                                    </div>
                                ))}
                            </div>

                            {!isSearching && searchTerm && narratorResults.length === 0 && (
                                <div className="text-center py-8">
                                    <p className="text-white/60">No narrators found</p>
                                </div>
                            )}
                        </div>

                        {/* Current Chain */}
                        <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-2xl font-bold text-white">Chain Preview</h2>
                                <button
                                    onClick={() => setStep(1)}
                                    className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
                                >
                                    ← Change Hadith
                                </button>
                            </div>

                            {selectedHadith && (
                                <div className="mb-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                                    <p className="text-sm text-purple-200 mb-1">Selected Hadith:</p>
                                    <p className="text-white font-semibold">{selectedHadith.title}</p>
                                </div>
                            )}

                            {validationError && (
                                <div className="mb-4 p-4 bg-red-500/20 border border-red-500/40 rounded-lg">
                                    <p className="text-red-200 text-sm">⚠️ {validationError}</p>
                                </div>
                            )}

                            <div className="space-y-4">
                                {selectedChain.map((narrator, index) => (
                                    <div key={index} className="relative">
                                        <div className="absolute -left-4 top-6 w-8 h-8 bg-purple-600 rounded-full 
                                            flex items-center justify-center text-white font-bold text-sm z-10">
                                            {index + 1}
                                        </div>
                                        <div className="ml-6 p-4 bg-white/10 border border-white/20 rounded-lg group hover:border-purple-500/50 transition-all">
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <p className="font-semibold text-white">{narrator.name_english}</p>
                                                    <p className="text-sm text-white/60">{narrator.tabaqah}</p>
                                                </div>
                                                <button
                                                    onClick={() => removeNarratorFromChain(index)}
                                                    className="text-red-400 hover:text-red-300 transition-colors"
                                                >
                                                    ✕
                                                </button>
                                            </div>
                                        </div>
                                        {index < selectedChain.length - 1 && (
                                            <div className="ml-10 h-6 w-0.5 bg-purple-500/30"></div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {selectedChain.length === 0 && (
                                <div className="text-center py-12">
                                    <div className="text-4xl mb-4">⛓️</div>
                                    <p className="text-white/60">Add narrators to build your chain</p>
                                </div>
                            )}

                            {selectedChain.length >= 2 && !validationError && (
                                <button
                                    onClick={() => setStep(3)}
                                    className="w-full mt-6 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white 
                                        rounded-lg transition-colors font-semibold"
                                >
                                    Continue to Review →
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* Step 3: Review & Save */}
                {step === 3 && (
                    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
                        <h2 className="text-2xl font-bold text-white mb-6">Review Chain</h2>

                        <div className="mb-6 p-6 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                            <p className="text-sm text-purple-200 mb-2">Hadith:</p>
                            <p className="text-xl text-white font-semibold mb-1">{selectedHadith?.title}</p>
                            <p className="text-white/60">{selectedHadith?.primary_topic}</p>
                        </div>

                        <div className="mb-8">
                            <p className="text-white/80 mb-4">
                                Transmission Chain ({selectedChain.length} narrators):
                            </p>
                            <div className="space-y-2">
                                {selectedChain.map((narrator, index) => (
                                    <div key={index} className="flex items-center gap-4 p-4 bg-white/5 rounded-lg">
                                        <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center 
                                            text-white font-bold text-sm">
                                            {index + 1}
                                        </div>
                                        <div>
                                            <p className="text-white font-semibold">{narrator.name_english}</p>
                                            <p className="text-sm text-white/60">
                                                {narrator.tabaqah} • {narrator.reliability}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => setStep(2)}
                                className="flex-1 px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-lg 
                                    transition-colors font-semibold"
                            >
                                ← Back to Edit
                            </button>
                            <button
                                onClick={handleSaveChain}
                                disabled={isSaving}
                                className={`flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg 
                                    transition-colors font-semibold ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
                            >
                                {isSaving ? 'Saving...' : 'Save Chain ✓'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
