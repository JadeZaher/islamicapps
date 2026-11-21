'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useState, useEffect, useCallback, useId, useTransition } from 'react';
import { Button } from '@/components/ui/button';
import { SearchIcon } from '@/components/marks';

export interface FilterOption {
    label: string;
    value: string;
    /** Exact URL/database values represented by this canonical option. */
    aliases?: readonly string[];
}

export interface FilterConfig {
    /** URL param name, e.g. "grade" */
    key: string;
    /** Display label, e.g. "Grade" */
    label: string;
    /** Available options. First option is usually "All" with value "" */
    options: FilterOption[];
    /** Read-only URL aliases that should be normalized on the next filter change. */
    legacyKeys?: string[];
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
    const searchId = useId();

    const currentSearch = searchParams.get('q') || '';
    const [searchDraft, setSearchDraft] = useState({ source: currentSearch, value: currentSearch });
    const searchInput = searchDraft.source === currentSearch ? searchDraft.value : currentSearch;

    const updateParams = useCallback((updates: Record<string, string>, removeKeys: string[] = []) => {
        const params = new URLSearchParams(searchParams.toString());
        for (const [key, value] of Object.entries(updates)) {
            if (value) {
                params.set(key, value);
            } else {
                params.delete(key);
            }
        }
        removeKeys.forEach((key) => params.delete(key));
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

    const handleFilterChange = (filter: FilterConfig, value: string) => {
        updateParams({ [filter.key]: value }, filter.legacyKeys);
    };

    const getFilterValue = (filter: FilterConfig): string => {
        const rawValue = searchParams.get(filter.key) ||
            filter.legacyKeys?.map((key) => searchParams.get(key)).find(Boolean) || '';
        const matchingOption = filter.options.find((option) =>
            option.value === rawValue || option.aliases?.includes(rawValue),
        );
        return matchingOption?.value ?? rawValue;
    };

    const hasActiveFilters = filters.some((filter) => Boolean(getFilterValue(filter))) || Boolean(currentSearch);

    const clearAll = () => {
        const params = new URLSearchParams(searchParams.toString());
        params.delete('q');
        params.delete('page');
        filters.forEach((filter) => {
            params.delete(filter.key);
            filter.legacyKeys?.forEach((key) => params.delete(key));
        });
        startTransition(() => {
            router.push(`?${params.toString()}`);
        });
        setSearchDraft({ source: currentSearch, value: '' });
    };

    return (
        <section className="mb-8 space-y-3" aria-label="Search and filters" aria-busy={isPending}>
            <div className="flex flex-wrap items-end gap-4">
                {showSearch && (
                    <div className="flex-1 min-w-[200px] max-w-md">
                        <label htmlFor={searchId} className="mb-2 block text-sm font-semibold text-ink">
                            Search
                        </label>
                        <div className="relative">
                            <SearchIcon decorative className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-ink-muted" />
                            <input
                                id={searchId}
                                type="search"
                                dir="auto"
                                value={searchInput}
                                onChange={(e) => setSearchDraft({ source: currentSearch, value: e.target.value })}
                                placeholder={searchPlaceholder}
                                className="h-10 w-full border border-control bg-surface ps-9 pe-3 text-base text-ink placeholder:text-ink-muted focus-visible:border-focus focus-visible:outline-offset-0"
                            />
                            {isPending && (
                                <span className="absolute end-px top-1/2 -translate-y-1/2 bg-surface px-3 type-label" role="status">Updating</span>
                            )}
                        </div>
                    </div>
                )}

                {filters.map((filter) => (
                    <div key={filter.key} className="min-w-44">
                        <label htmlFor={`${searchId}-${filter.key}`} className="mb-2 block text-sm font-semibold text-ink">
                            {filter.label}
                        </label>
                        <select
                            id={`${searchId}-${filter.key}`}
                            value={getFilterValue(filter)}
                            onChange={(e) => handleFilterChange(filter, e.target.value)}
                            className="h-10 w-full cursor-pointer border border-control bg-surface px-3 text-base text-ink focus-visible:border-focus focus-visible:outline-offset-0"
                        >
                            {filter.options.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                </option>
                            ))}
                        </select>
                    </div>
                ))}

                {hasActiveFilters && (
                    <Button variant="link" onClick={clearAll}>
                        Clear filters
                    </Button>
                )}
            </div>

            {totalResults !== undefined && (
                <p className="text-sm tabular-nums text-ink-muted" aria-live="polite" aria-atomic="true">
                    {totalResults.toLocaleString()} result{totalResults !== 1 ? 's' : ''}
                </p>
            )}
        </section>
    );
}
