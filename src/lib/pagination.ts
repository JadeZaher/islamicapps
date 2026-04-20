/**
 * Shared pagination types and helpers for Neo4j queries.
 */

import neo4j from 'neo4j-driver';

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

/** Convert page/pageSize to Neo4j SKIP/LIMIT values (as Neo4j integers). */
export function toSkipLimit(params?: PaginationParams) {
    const page = Math.max(1, params?.page ?? 1);
    const pageSize = Math.min(100, Math.max(1, params?.pageSize ?? DEFAULT_PAGE_SIZE));
    return {
        skip: neo4j.int((page - 1) * pageSize),
        limit: neo4j.int(pageSize),
        page,
        pageSize,
    };
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
