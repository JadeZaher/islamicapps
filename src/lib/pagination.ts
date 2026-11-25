/**
 * Shared pagination types and helpers.
 */

export interface PaginationParams {
    page?: number;
    pageSize?: number;
}

export interface PaginatedResult<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

export const DEFAULT_PAGE_SIZE = 25;

/** Parse a `?page=` search param into a positive integer (NaN, 0, negatives and junk become 1). */
export function parsePageParam(value: string | undefined): number {
    const parsed = Math.floor(Number(value));
    return Number.isFinite(parsed) && parsed >= 1 ? parsed : 1;
}

/** Build a PaginatedResult from items + total count. */
export function paginate<T>(items: T[], total: number, page: number, pageSize: number): PaginatedResult<T> {
    return {
        items,
        total,
        page,
        pageSize,
        totalPages: Math.ceil(total / pageSize),
    };
}
