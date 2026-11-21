/** Locations: admin list and CRUD (section 9.1). Coordinates use `??`, so 0 is a real value (rule 7). */
import 'server-only';
import { sql } from 'drizzle-orm';
import { locations } from '@/db/schema';
import type { LocationRecord, Paginated } from './contracts';
import { mapLocation } from './mappers';
import { clampPage, cleanTerm, containsPattern, oneRow, paginated, type PageRequest } from './sql-helpers';
import { allowlistedPatch, audit, CurationError, curationWrite, lockLiveRow, newId, txRows } from './write';

export interface LocationInput {
  name: string;
  name_arabic?: string | null;
  modern_country?: string | null;
  region?: string | null;
  description?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export type LocationPatch = Partial<LocationInput>;

const LOCATION_COLUMNS = {
  name: 'name',
  name_arabic: 'nameArabic',
  modern_country: 'modernCountry',
  region: 'region',
  description: 'description',
  latitude: 'latitude',
  longitude: 'longitude',
} as const;

/** Live locations by name, optionally filtered by a name substring. */
export async function listLocations(term?: string, request?: PageRequest): Promise<Paginated<LocationRecord>> {
  const window = clampPage(request, Number.MAX_SAFE_INTEGER);
  const cleaned = cleanTerm(term, 100);
  const where = cleaned
    ? sql`l.retired_at is null and (l.name ilike ${containsPattern(cleaned)} or l.name_arabic ilike ${containsPattern(cleaned)})`
    : sql`l.retired_at is null`;
  const row = await oneRow<{ total: number; items: Record<string, unknown>[] }>(sql`
    select (select count(*)::int from locations l where ${where}) as total,
           coalesce((select json_agg(to_jsonb(x) order by x.name, x.id)
                     from (select l.* from locations l where ${where} order by l.name, l.id
                           limit ${window.limit} offset ${window.offset}) x), '[]'::json) as items
  `);
  return paginated((row?.items ?? []).map(mapLocation), row?.total ?? 0, window);
}

export async function createLocation(actor: string, input: LocationInput): Promise<string> {
  const id = newId();
  return curationWrite(actor, async (tx) => {
    const [created] = await tx
      .insert(locations)
      .values({
        id,
        name: input.name,
        nameArabic: input.name_arabic ?? null,
        modernCountry: input.modern_country ?? null,
        region: input.region ?? null,
        description: input.description ?? null,
        latitude: input.latitude ?? null,
        longitude: input.longitude ?? null,
        origin: 'manual',
        createdBy: actor,
        updatedBy: actor,
      })
      .returning();
    await audit(tx, { actor, action: 'create', entityType: 'location', entityId: id, after: created });
    return id;
  });
}

export async function updateLocation(actor: string, id: string, patch: LocationPatch): Promise<void> {
  const set = allowlistedPatch(patch, LOCATION_COLUMNS);
  if (Object.keys(set).length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'locations', id, 'Location');
    const [after] = await tx
      .update(locations)
      .set({ ...(set as Partial<typeof locations.$inferInsert>), updatedAt: new Date(), updatedBy: actor })
      .where(sql`${locations.id} = ${id}`)
      .returning();
    await audit(tx, { actor, action: 'update', entityType: 'location', entityId: id, before, after });
  });
}

/** Retires a location and its live links; refused while a live event names it (soft delete never fires the FK). */
export async function retireLocation(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'locations', id, 'Location');
    const [referenced] = await txRows(tx, sql`select 1 from historical_events where location_id = ${id} and retired_at is null limit 1`);
    if (referenced) throw new CurationError('refused', 'A live historical event refers to this location.');
    await txRows(tx, sql`update locations set retired_at = now(), retired_by = ${actor}, updated_at = now(),
                          updated_by = ${actor} where id = ${id}`);
    const narratorLinks = await txRows(tx, sql`update narrator_locations set retired_at = now(), retired_by = ${actor}
                                                where location_id = ${id} and retired_at is null returning id`);
    const traditionLinks = await txRows(tx, sql`update location_religious_traditions set retired_at = now(), retired_by = ${actor}
                                                 where location_id = ${id} and retired_at is null returning id`);
    await audit(tx, {
      actor,
      action: 'retire',
      entityType: 'location',
      entityId: id,
      before,
      after: { retired_links: narratorLinks.length + traditionLinks.length },
    });
  });
}
