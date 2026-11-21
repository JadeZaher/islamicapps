/**
 * Phase-0 import of hand-written narrator biographies and verdicts (design section 5.7): `insert ... on conflict do
 * nothing`, so a re-run, a later phase or a curator's edit is never overwritten. Rows start `proposed`; publishing
 * needs a citation (check constraints). Every insert is audited.
 */
import 'server-only';
import { sql } from 'drizzle-orm';
import { audit, curationWrite, txRows } from './write';

export interface SeedBiography {
  narrator_id: string;
  is_prophet: boolean;
  tabaqah_class: string;
  name_en_clean: string | null;
  name_ar_clean: string | null;
  kunya: string | null;
  nasab: string | null;
  nisba: string | null;
  geographic_region: string | null;
  death_year_hijri: number | null;
  death_year_gregorian: number | null;
  bio_summary: string | null;
}

export interface SeedVerdict {
  id: string;
  narrator_id: string;
  tradition_id: string;
  verdict: string;
  tadil_text: string | null;
  jarh_text: string | null;
  is_companion: boolean | null;
  disagreement: boolean;
  critic_quote_count: number | null;
}

export interface BiographySeedOutcome {
  biosCreated: string[];
  biosExisting: string[];
  verdictsCreated: string[];
  verdictsExisting: string[];
  missingNarrators: string[];
}

export const PHASE_0_PROVENANCE = 'manual_phase_0';

export async function seedNarratorBiographies(actor: string, bios: SeedBiography[], verdicts: SeedVerdict[]): Promise<BiographySeedOutcome> {
  const outcome: BiographySeedOutcome = { biosCreated: [], biosExisting: [], verdictsCreated: [], verdictsExisting: [], missingNarrators: [] };
  await curationWrite(actor, async (tx) => {
    const wanted = [...new Set([...bios.map((bio) => bio.narrator_id), ...verdicts.map((verdict) => verdict.narrator_id)])];
    const live = new Set(
      (await txRows<{ id: string }>(tx, sql`select id from narrators where retired_at is null
                                            and id in (select jsonb_array_elements_text(${JSON.stringify(wanted)}::jsonb))`)).map((row) => row.id),
    );
    outcome.missingNarrators = wanted.filter((id) => !live.has(id));

    for (const bio of bios.filter((row) => live.has(row.narrator_id))) {
      const [created] = await txRows<{ image: Record<string, unknown> }>(tx, sql`
        insert into narrator_bios (narrator_id, is_prophet, tabaqah_class, name_en_clean, name_ar_clean, kunya, nasab, nisba,
                                   geographic_region, death_year_hijri, death_year_gregorian, bio_summary, provenance, status,
                                   created_by, updated_by)
        values (${bio.narrator_id}, ${bio.is_prophet}, ${bio.tabaqah_class}, ${bio.name_en_clean}, ${bio.name_ar_clean}, ${bio.kunya},
                ${bio.nasab}, ${bio.nisba}, ${bio.geographic_region}, ${bio.death_year_hijri}, ${bio.death_year_gregorian},
                ${bio.bio_summary}, ${PHASE_0_PROVENANCE}, 'proposed', ${actor}, ${actor})
        on conflict (narrator_id) do nothing
        returning to_jsonb(narrator_bios) as image`);
      if (created) {
        await audit(tx, { actor, action: 'seed_create', entityType: 'narrator_bio', entityId: bio.narrator_id, after: created.image });
        outcome.biosCreated.push(bio.narrator_id);
      } else {
        outcome.biosExisting.push(bio.narrator_id);
      }
    }

    for (const verdict of verdicts.filter((row) => live.has(row.narrator_id))) {
      const [created] = await txRows<{ image: Record<string, unknown> }>(tx, sql`
        insert into narrator_assessments (id, narrator_id, tradition_id, kind, verdict, tadil_text, jarh_text, is_companion,
                                          disagreement, critic_quote_count, provenance, status, created_by, updated_by)
        values (${verdict.id}, ${verdict.narrator_id}, ${verdict.tradition_id}, 'consensus_summary', ${verdict.verdict},
                ${verdict.tadil_text}, ${verdict.jarh_text}, ${verdict.is_companion}, ${verdict.disagreement},
                ${verdict.critic_quote_count}, ${PHASE_0_PROVENANCE}, 'proposed', ${actor}, ${actor})
        on conflict (id) do nothing
        returning to_jsonb(narrator_assessments) as image`);
      if (created) {
        await audit(tx, { actor, action: 'seed_create', entityType: 'narrator_assessment', entityId: verdict.id, after: created.image });
        outcome.verdictsCreated.push(verdict.id);
      } else {
        outcome.verdictsExisting.push(verdict.id);
      }
    }
  });
  return outcome;
}
