/** How public chains stand, by tier, overall and per tradition, computed live (src/db/AGENTS.md §AI review tier). */
import 'server-only';
import { sql } from 'drizzle-orm';
import { rows } from './sql-helpers';

/** The tiers in the order /method shows them; "no chain by reading" counts reports (their chains are retired), the rest count chains. */
export const CHAIN_TIERS = [
  'rule_uncertain',
  'rule_checked',
  'read_by_two_models',
  'ai_reviewed',
  'agent_verified',
  'verified_by_person',
  'no_chain_by_reading',
] as const;
export type ChainTier = (typeof CHAIN_TIERS)[number];

export interface ChainTierCoverage {
  /** tradition code -> tier -> count; `all` is every tradition together. */
  counts: Record<string, Record<ChainTier, number>>;
  traditions: string[];
}

const emptyRow = (): Record<ChainTier, number> => Object.fromEntries(CHAIN_TIERS.map((tier) => [tier, 0])) as Record<ChainTier, number>;

/**
 * One tier per live public chain: a person's confirmation; else, read by model, "agent verified" (AI reviewed and a matched witness),
 * "AI reviewed" (confirmed or its correction, not disputed) or "read by two models"; else the structure gate's status. Disputed readings
 * stay in "read by two models". Reports whose applied reading found no chain are counted once each.
 */
export async function getChainTierCoverage(): Promise<ChainTierCoverage> {
  const found = await rows<{ tradition: string; tier: ChainTier; n: number }>(sql`
    select t.code::text as tradition, x.tier, count(*)::int as n
    from (
      select h.tradition_id,
             case when c.structure_status = 'verified_by_reviewer' then 'verified_by_person'
                  when c.structure_status = 'read_by_model' and fl.ai_review is not null and fl.ai_disputed is null and fl.witness_match is not null then 'agent_verified'
                  when c.structure_status = 'read_by_model' and (fl.ai_review is not null or fl.ai_corrected is not null) and fl.ai_disputed is null then 'ai_reviewed'
                  when c.structure_status = 'read_by_model' then 'read_by_two_models'
                  when c.structure_status = 'uncertain' then 'rule_uncertain'
                  else 'rule_checked' end as tier
      from chains c
      join public_hadiths h on h.id = c.hadith_id
      left join public_chain_fix_labels fl on fl.chain_id = c.id
      where c.retired_at is null
      union all
      select h.tradition_id, 'no_chain_by_reading'
      from public_chain_fix_dispositions d join public_hadiths h on h.id = d.hadith_id
    ) x
    join traditions t on t.id = x.tradition_id
    group by 1, 2`);
  const counts: Record<string, Record<ChainTier, number>> = { all: emptyRow() };
  for (const row of found) {
    const tradition = row.tradition.toLowerCase();
    counts[tradition] ??= emptyRow();
    counts[tradition][row.tier] += row.n;
    counts.all[row.tier] += row.n;
  }
  return { counts, traditions: Object.keys(counts).filter((key) => key !== 'all').sort() };
}
