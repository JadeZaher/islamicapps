'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useState, useEffect, useCallback, useTransition } from 'react';
import { Button } from '@/components/ui/button';

export interface FilterOption {
    label: string;
    value: string;
}

export interface FilterConfig {
    /** URL param name, e.g. "grade" */
    key: string;
    /** Display label, e.g. "Grade" */
    label: string;
    /** Available options. First option is usually "All" with value "" */
    options: FilterOption[];
}

interface SearchFilterBarProps {
    /** Placeholder for the search input */
    searchPlaceholder?: string;
    /** Show the search input. Default true. */
    showSearch?: boolean;
    /** Filter configurations */
    filters?: FilterConfig[];
    /** Total results count to display */
    totalResults?: number;
}

export function SearchFilterBar({
    searchPlaceholder = 'Search...',
    showSearch = true,
    filters = [],
    totalResults,
}: SearchFilterBarProps) {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isPending, startTransition] = useTransition();

    const currentSearch = searchParams.get('q') || '';
    const [searchInput, setSearchInput] = useState(currentSearch);

    // Sync input when URL changes externally
    useEffect(() => {
        setSearchInput(searchParams.get('q') || '');
    }, [searchParams]);

    const updateParams = useCallback((updates: Record<string, string>) => {
        const params = new URLSearchParams(searchParams.toString());
        for (const [key, value] of Object.entries(updates)) {
            if (value) {
                params.set(key, value);
            } else {
                params.delete(key);
            }
        }
        // Reset to page 1 on any filter/search change
        params.delete('page');
        startTransition(() => {
            router.push(`?${params.toString()}`);
        });
    }, [router, searchParams, startTransition]);

    // Debounced search
    useEffect(() => {
        const timer = setTimeout(() => {
            if (searchInput !== currentSearch) {
                updateParams({ q: searchInput });
            }
        }, 400);
        return () => clearTimeout(timer);
    }, [searchInput, currentSearch, updateParams]);

    const handleFilterChange = (key: string, value: string) => {
        updateParams({ [key]: value });
    };

    const hasActiveFilters = filters.some(f => searchParams.get(f.key)) || currentSearch;

    const clearAll = () => {
        const params = new URLSearchParams();
        startTransition(() => {
            router.push(`?${params.toString()}`);
        });
        setSearchInput('');
    };

    return (
        <div className="space-y-3 mb-6">
            <div className="flex flex-wrap items-center gap-3">
                {showSearch && (
                    <div className="relative flex-1 min-w-[200px] max-w-md">
                        <input
                            type="text"
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            placeholder={searchPlaceholder}
                            className="w-full px-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder:text-slate-400 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/25 text-sm"
                        />
                        {isPending && (
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                        )}
                    </div>
                )}

                {filters.map((filter) => (
                    <select
                        key={filter.key}
                        value={searchParams.get(filter.key) || ''}
                        onChange={(e) => handleFilterChange(filter.key, e.target.value)}
                        className="px-3 py-2.5 bg-slate-800/50 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500/50 cursor-pointer"
                    >
                        {filter.options.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                ))}

                {hasActiveFilters && (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={clearAll}
                        className="border-slate-600 text-slate-400 hover:text-white hover:bg-slate-800"
                    >
                        Clear filters
                    </Button>
                )}
            </div>

            {totalResults !== undefined && (
                <p className="text-xs text-slate-400">
                    {totalResults.toLocaleString()} result{totalResults !== 1 ? 's' : ''}
                    {isPending && ' (updating...)'}
                </p>
            )}
        </div>
    );
}
