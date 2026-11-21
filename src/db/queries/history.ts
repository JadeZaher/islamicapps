/** Historical events: admin list and CRUD, and the public lifetime-overlap read (sections 5.9, 8). */
import 'server-only';
import { sql } from 'drizzle-orm';
import { historicalEvents } from '@/db/schema';
import type { HistoricalEventRecord, Paginated } from './contracts';
import type { EventCategory, EventVerification } from './enums';
import { mapHistoricalEvent } from './mappers';
import { andAll, clampPage, oneRow, paginated, rows, withReadRetry, type PageRequest } from './sql-helpers';
import { allowlistedPatch, audit, curationWrite, lockLiveRow, newId, txRows } from './write';

export interface HistoricalEventInput {
  title: string;
  title_arabic?: string | null;
  description?: string | null;
  significance?: string | null;
  start_year_hijri?: number | null;
  end_year_hijri?: number | null;
  start_year_gregorian?: number | null;
  end_year_gregorian?: number | null;
  category?: EventCategory | null;
  location_name?: string | null;
  verification_status?: EventVerification;
  publication_ready?: boolean;
  citation_source?: string | null;
  citation_locator?: string | null;
  citation_url?: string | null;
  citation_retrieved_at?: Date | null;
}

export type HistoricalEventPatch = Partial<HistoricalEventInput>;

/** Update allowlist: contract key to column property (rule 5). */
const EVENT_COLUMNS = {
  title: 'title',
  title_arabic: 'titleArabic',
  description: 'description',
  significance: 'significance',
  start_year_hijri: 'startYearHijri',
  end_year_hijri: 'endYearHijri',
  start_year_gregorian: 'startYearGregorian',
  end_year_gregorian: 'endYearGregorian',
  category: 'category',
  location_name: 'locationName',
  verification_status: 'verificationStatus',
  publication_ready: 'publicationReady',
  citation_source: 'citationSource',
  citation_locator: 'citationLocator',
  citation_url: 'citationUrl',
  citation_retrieved_at: 'citationRetrievedAt',
} as const;

/** Admin list of live events, oldest first. `category` is already canonical; null means "matches nothing". */
export async function listHistoricalEvents(
  filters: { category?: EventCategory | null; yearRange?: [number, number] } = {},
  request?: PageRequest,
): Promise<Paginated<HistoricalEventRecord>> {
  const window = clampPage(request, Number.MAX_SAFE_INTEGER);
  if (filters.category === null) return paginated([], 0, window);
  const where = andAll([
    sql`e.retired_at is null`,
    filters.category ? sql`e.category = ${filters.category}` : undefined,
    filters.yearRange
      ? sql`coalesce(e.end_year_hijri, e.start_year_hijri) >= ${filters.yearRange[0]} and e.start_year_hijri <= ${filters.yearRange[1]}`
      : undefined,
  ]);
  const row = await oneRow<{ total: number; items: Record<string, unknown>[] }>(sql`
    select (select count(*)::int from historical_events e where ${where}) as total,
           coalesce((select json_agg(to_jsonb(x) order by x.start_year_hijri nulls last, x.id)
                     from (select e.* from historical_events e where ${where}
                           order by e.start_year_hijri nulls last, e.id
                           limit ${window.limit} offset ${window.offset}) x), '[]'::json) as items
  `);
  return paginated((row?.items ?? []).map(mapHistoricalEvent), row?.total ?? 0, window);
}

/**
 * Published events overlapping the narrator's lifespan range (`narrator_lifespans` x `published_historical_events`).
 * Fails closed: a narrator with no lifespan bound gets no events.
 */
export async function getHistoricalEventsForNarrator(narratorId: string): Promise<HistoricalEventRecord[]> {
  const found = await withReadRetry(() =>
    rows<Record<string, unknown>>(sql`
      select e.*
      from narrator_lifespans l
      join published_historical_events e
        on (l.birth_min is null or e.event_end >= l.birth_min)
       and (l.death_max is null or e.event_start <= l.death_max)
      where l.narrator_id = ${narratorId}
      order by e.event_start, e.id
    `),
  );
  return found.map(mapHistoricalEvent);
}

export async function createHistoricalEvent(actor: string, input: HistoricalEventInput): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [created] = await tx
      .insert(historicalEvents)
      .values({
        id,
        title: input.title,
        titleArabic: input.title_arabic ?? null,
        description: input.description ?? null,
        significance: input.significance ?? null,
        startYearHijri: input.start_year_hijri ?? null,
        endYearHijri: input.end_year_hijri ?? null,
        startYearGregorian: input.start_year_gregorian ?? null,
        endYearGregorian: input.end_year_gregorian ?? null,
        category: input.category ?? null,
        locationName: input.location_name ?? null,
        // New records are unverified and not publishable until reviewed (src/app/actions/AGENTS.md).
        verificationStatus: input.verification_status ?? 'unverified',
        publicationReady: input.publication_ready ?? false,
        citationSource: input.citation_source ?? null,
        citationLocator: input.citation_locator ?? null,
        citationUrl: input.citation_url ?? null,
        citationRetrievedAt: input.citation_retrieved_at ?? null,
        origin: 'manual',
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    await audit(tx, { actor, action: 'create', entityType: 'historical_event', entityId: id, after: created });
    return id;
  });
}

export async function updateHistoricalEvent(actor: string, id: string, patch: HistoricalEventPatch): Promise<void> {
  const set = allowlistedPatch(patch, EVENT_COLUMNS);
  if (Object.keys(set).length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'historical_events', id, 'Historical event');
    const [after] = await tx
      .update(historicalEvents)
      .set({ ...(set as Partial<typeof historicalEvents.$inferInsert>), updatedAt: new Date(), updatedBy: actor })
      .where(sql`${historicalEvents.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: 'update', entityType: 'historical_event', entityId: id, before, after });
  });
}

/** Retires the event and its live narrator links; nothing is deleted. */
export async function retireHistoricalEvent(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'historical_events', id, 'Historical event');
    await txRows(tx, sql`update historical_events set retired_at = now(), retired_by = ${actor}, updated_at = now(),
                          updated_by = ${actor} where id = ${id}`);
    const links = await txRows(tx, sql`update narrator_events set retired_at = now(), retired_by = ${actor}
                                       where event_id = ${id} and retired_at is null returning id`);
    await audit(tx, { actor, action: 'retire', entityType: 'historical_event', entityId: id, before, after: { retired_links: links.length } });
  });
}
