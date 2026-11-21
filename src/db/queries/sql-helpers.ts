/** Shared query helpers: paging, LIKE escaping, read retry, tradition aliases. See src/db/queries/AGENTS.md. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { db } from '@/db/client';

export type HadithTraditionCode = 'Sunni' | 'Imami' | 'Zaydi' | 'Ibadi';

export const HADITH_TRADITION_CODES: readonly HadithTraditionCode[] = ['Sunni', 'Imami', 'Zaydi', 'Ibadi'];

export const DEFAULT_PAGE_SIZE = 25;
export const MAX_PAGE_SIZE = 100;
/** Public pages page with limit/offset up to this page (section 7.3). */
export const MAX_PUBLIC_PAGE = 200;
/** Searches count up to COUNT_CAP + 1 rows and report "1,000+" beyond (section 7.3). */
export const COUNT_CAP = 1000;

export interface Paginated<T> {
  items: T[];
  /** Exact total, or COUNT_CAP when `totalCapped` is true. */
  total: number;
  totalCapped: boolean;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface PageRequest {
  page?: number;
  pageSize?: number;
}

export interface PageWindow {
  page: number;
  pageSize: number;
  limit: number;
  offset: number;
}

/** Clamps a page request to [1, maxPage] and pageSize to [1, MAX_PAGE_SIZE]. */
export function clampPage(request: PageRequest | undefined, maxPage = MAX_PUBLIC_PAGE): PageWindow {
  const pageSize = Math.min(MAX_PAGE_SIZE, Math.max(1, Math.floor(request?.pageSize ?? DEFAULT_PAGE_SIZE)));
  const page = Math.min(maxPage, Math.max(1, Math.floor(request?.page ?? 1) || 1));
  return { page, pageSize, limit: pageSize, offset: (page - 1) * pageSize };
}

/** Builds a Paginated result; a count of COUNT_CAP + 1 or more is reported as capped. */
export function paginated<T>(items: T[], countedRows: number, window: PageWindow, capped = false): Paginated<T> {
  const totalCapped = capped && countedRows > COUNT_CAP;
  const total = totalCapped ? COUNT_CAP : countedRows;
  return {
    items,
    total,
    totalCapped,
    page: window.page,
    pageSize: window.pageSize,
    totalPages: Math.max(1, Math.ceil(total / window.pageSize)),
  };
}

/** Escapes LIKE wildcards so user input matches literally (escape character is backslash). */
export function escapeLike(term: string): string {
  return term.replace(/[\\%_]/g, (character) => `\\${character}`);
}

/** `%term%` pattern with wildcards escaped. */
export function containsPattern(term: string): string {
  return `%${escapeLike(term)}%`;
}

/** Integer or null; never NaN. */
export function toInt(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
}

/** ISO string or null for a Date or a JSON timestamp string. */
export function toIso(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return value.toISOString();
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

const TRADITION_ALIASES: Record<string, HadithTraditionCode> = {
  sunni: 'Sunni',
  imami: 'Imami',
  'shia imami': 'Imami',
  shia: 'Imami',
  zaydi: 'Zaydi',
  'shia zaydi': 'Zaydi',
  ibadi: 'Ibadi',
};

/**
 * Maps a tradition filter to one enum value (section 7.3, rule 8).
 * Returns undefined for "no filter" (empty input) and null for an unknown value (empty result).
 */
export function resolveTraditionCode(value: string | null | undefined): HadithTraditionCode | null | undefined {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) return undefined;
  return TRADITION_ALIASES[normalized] ?? null;
}

const RETRYABLE_CODES = new Set(['ECONNREFUSED', 'ECONNRESET', '57P01', '57P03', 'CONNECTION_CLOSED', 'CONNECTION_ENDED']);
const RETRY_DELAYS_MS = [250, 1000];

function isRetryable(error: unknown): boolean {
  const code = (error as { code?: unknown } | null)?.code;
  const causeCode = (error as { cause?: { code?: unknown } } | null)?.cause?.code;
  return RETRYABLE_CODES.has(String(code)) || RETRYABLE_CODES.has(String(causeCode));
}

/** Retries a read twice on connection loss (250 ms, then 1 s). Writes never retry (section 2.6, rule 10). */
export async function withReadRetry<T>(read: () => Promise<T>): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await read();
    } catch (error) {
      if (attempt >= RETRY_DELAYS_MS.length || !isRetryable(error)) throw error;
      await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[attempt]));
    }
  }
}

/** Runs one raw statement and returns its rows as plain objects. */
export async function rows<Row extends Record<string, unknown>>(query: SQL): Promise<Row[]> {
  const result = await db.execute<Row>(query);
  return Array.from(result) as unknown as Row[];
}

/** Runs a read statement that returns exactly one row, with read retry. */
export async function oneRow<Row extends Record<string, unknown>>(query: SQL): Promise<Row | undefined> {
  return withReadRetry(async () => (await rows<Row>(query))[0]);
}

/** `and`-joins SQL fragments; `true` when empty. */
export function andAll(conditions: Array<SQL | undefined | false>): SQL {
  const present = conditions.filter((condition): condition is SQL => Boolean(condition));
  if (present.length === 0) return sql`true`;
  return sql.join(present, sql` and `);
}

/** Cleans a free-text search term: trims, collapses whitespace, caps length. */
export function cleanTerm(term: string | null | undefined, maxLength = 200): string {
  return (term ?? '').replace(/\s+/g, ' ').trim().slice(0, maxLength);
}

/** True when the string contains an Arabic letter. */
export function hasArabic(term: string): boolean {
  return /[؀-ۿ]/.test(term);
}
