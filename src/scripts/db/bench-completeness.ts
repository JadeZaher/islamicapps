/**
 * Read-only mathematical completeness benchmark across the corpus, narrators/biographies,
 * timeline/citations, and referential/accounting invariants.
 *
 * Usage:
 *   npx tsx --conditions=react-server src/scripts/db/bench-completeness.ts --database development
 *   npx tsx --conditions=react-server src/scripts/db/bench-completeness.ts --database production
 *   npx tsx --conditions=react-server src/scripts/db/bench-completeness.ts --database production --json
 */
import { config as loadEnvironment } from 'dotenv';
import postgres from 'postgres';
import { connectionOptions } from '../../db/connection-options';
import { resolveTargetDatabase, type TargetName } from '../../db/target-database';

export interface BenchArgs {
  database: TargetName;
  json: boolean;
  minTranslationPct: number | null;
}

export interface CollectionCompletenessRow {
  collectionId: string;
  slug: string;
  name: string;
  sortKey: number;
  totalLiveHadiths: number;
  publicHadiths: number;
  translations: {
    total: number;
    sourceProvided: number;
    machineUnreviewed: number;
    humanVerified: number;
    sourceVerified: number;
    unknownProvenance: number;
    missing: number;
    coveragePct: number;
    missingPct: number;
  };
  chains: {
    totalLiveChains: number;
    hadithsWithChain: number;
    coveragePct: number;
    checkedByRule: number;
    uncertain: number;
    readByModel: number;
    aiReviewed: number;
    agentVerified: number;
    verifiedByReviewer: number;
    otherOrNull: number;
  };
  assessments: {
    totalLiveAssessments: number;
    hadithsWithAssessment: number;
    coveragePct: number;
  };
}

export interface NarratorCompletenessSummary {
  totalLiveNarrators: number;
  byAuthority: Record<string, number>;
  bios: {
    total: number;
    published: number;
    verified: number;
    proposed: number;
    coveragePct: number;
  };
  lifespans: {
    total: number;
    coveragePct: number;
  };
  assessments: {
    total: number;
    distinctNarrators: number;
    published: number;
    verified: number;
    proposed: number;
    coveragePct: number;
  };
  events: {
    total: number;
    distinctNarrators: number;
    distinctEvents: number;
    coveragePct: number;
  };
}

export interface ContactGridSummary {
  timelineTracks: number;
  historicalEventsWithTrack: number;
  placeSnapshots: {
    total: number;
    distinctLocations: number;
    byReviewState: Record<string, number>;
  };
  narratorResidences: {
    total: number;
    distinctNarrators: number;
    distinctLocations: number;
    byReviewState: Record<string, number>;
  };
  narratorAffiliations: {
    total: number;
    distinctNarrators: number;
    byReviewState: Record<string, number>;
  };
  externalTraditionParallels: {
    total: number;
    distinctHadiths: number;
    byReviewState: Record<string, number>;
  };
}

export interface TimelineCitationsSummary {
  epochs: {
    total: number;
    cited: number;
    publishedFlag: number;
    publishedView: number;
  };
  historicalEvents: {
    total: number;
    cited: number;
    publishedFlag: number;
    publishedView: number;
  };
  temporalAssertions: {
    total: number;
    byReviewState: Record<string, number>;
  };
  locations: {
    total: number;
    withCoordinates: number;
    cited: number;
  };
  citations: {
    total: number;
    history: number;
    rijal: number;
    other: number;
    byReviewState: Record<string, number>;
  };
  bibliographicWorks: number;
  editions: number;
  contactGrid?: ContactGridSummary;
}

export interface OrphanCheckCounts {
  hadithsCollection: number;
  translationsHadith: number;
  chainsHadith: number;
  hadithAssessmentsHadith: number;
  narratorBiosNarrator: number;
  narratorAssessmentsNarrator: number;
  narratorEventsNarrator: number;
  narratorEventsEvent: number;
  temporalAssertionsCitation: number;
  citationsWork: number;
  editionsWork: number;
}

export interface InvariantResult {
  name: string;
  passed: boolean;
  expected: string;
  actual: string;
  detail?: string;
}

export interface CompletenessReport {
  database: TargetName;
  generatedAt: string;
  totals: {
    collections: number;
    totalLiveHadiths: number;
    totalPublicHadiths: number;
    totalTranslatedHadiths: number;
    totalMissingTranslationHadiths: number;
    translationCoveragePct: number;
    totalHadithsWithChain: number;
    chainCoveragePct: number;
    totalHadithsWithAssessment: number;
    assessmentCoveragePct: number;
  };
  collections: CollectionCompletenessRow[];
  narrators: NarratorCompletenessSummary;
  timelineAndCitations: TimelineCitationsSummary;
  invariants: InvariantResult[];
  allPassed: boolean;
}

export function pct(numerator: number, denominator: number): number {
  if (denominator <= 0) return 0;
  return Math.round((numerator / denominator) * 10000) / 100;
}

export function parseBenchArgs(argv: readonly string[]): BenchArgs {
  const idx = argv.indexOf('--database');
  const requested =
    idx >= 0
      ? argv[idx + 1]
      : argv.find((v) => v.startsWith('--database='))?.slice('--database='.length);
  const database = (requested ?? 'development') as TargetName;
  if (database !== 'development' && database !== 'production') {
    throw new Error(`--database must be development or production, not "${database}".`);
  }

  const json = argv.includes('--json');

  const minIdx = argv.indexOf('--min-translation-pct');
  const minRaw =
    minIdx >= 0
      ? argv[minIdx + 1]
      : argv.find((v) => v.startsWith('--min-translation-pct='))?.slice('--min-translation-pct='.length);
  let minTranslationPct: number | null = null;
  if (minRaw !== undefined) {
    const parsed = Number(minRaw);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) {
      throw new Error(`--min-translation-pct must be a number between 0 and 100, not "${minRaw}".`);
    }
    minTranslationPct = parsed;
  }

  return { database, json, minTranslationPct };
}

export function resolveReadOnlyConnection(database: TargetName): { name: TargetName; url: string } {
  loadEnvironment({ path: '.env.local', quiet: true });
  if (database === 'production') {
    const url = process.env.DATABASE_URL_PRODUCTION?.trim();
    if (!url) throw new Error('DATABASE_URL_PRODUCTION is not set.');
    return { name: 'production', url };
  }
  return resolveTargetDatabase(['--database', 'development'], { required: true });
}

export function evaluateInvariants(params: {
  collections: readonly CollectionCompletenessRow[];
  totalLiveHadithsDirect: number;
  totalPublicHadithsDirect: number;
  narrators: NarratorCompletenessSummary;
  timelineAndCitations: TimelineCitationsSummary;
  orphans: OrphanCheckCounts;
  minTranslationPct?: number | null;
}): InvariantResult[] {
  const results: InvariantResult[] = [];

  const sumLiveHadiths = params.collections.reduce((acc, c) => acc + c.totalLiveHadiths, 0);
  results.push({
    name: 'per_collection_hadith_sum',
    passed: sumLiveHadiths === params.totalLiveHadithsDirect,
    expected: String(params.totalLiveHadithsDirect),
    actual: String(sumLiveHadiths),
  });

  const sumPublicHadiths = params.collections.reduce((acc, c) => acc + c.publicHadiths, 0);
  results.push({
    name: 'per_collection_public_hadith_sum',
    passed: sumPublicHadiths === params.totalPublicHadithsDirect,
    expected: String(params.totalPublicHadithsDirect),
    actual: String(sumPublicHadiths),
  });

  const badTranslationPartitions = params.collections.filter((c) => {
    const countMatch = c.translations.total + c.translations.missing === c.totalLiveHadiths;
    const stateSum =
      c.translations.sourceProvided +
      c.translations.machineUnreviewed +
      c.translations.humanVerified +
      c.translations.sourceVerified +
      c.translations.unknownProvenance;
    const pctSum = Math.round((c.translations.coveragePct + c.translations.missingPct) * 100) / 100;
    const pctOk = c.totalLiveHadiths === 0 ? pctSum === 0 : Math.abs(pctSum - 100) <= 0.02;
    return !countMatch || stateSum !== c.translations.total || !pctOk;
  });
  results.push({
    name: 'translation_coverage_partition',
    passed: badTranslationPartitions.length === 0,
    expected: '0 mismatched collections',
    actual: `${badTranslationPartitions.length} mismatched collections`,
    detail: badTranslationPartitions.map((c) => c.slug).join(', ') || undefined,
  });

  const sumNarratorsByAuthority = Object.values(params.narrators.byAuthority).reduce((a, b) => a + b, 0);
  results.push({
    name: 'narrator_authority_sum',
    passed: sumNarratorsByAuthority === params.narrators.totalLiveNarrators,
    expected: String(params.narrators.totalLiveNarrators),
    actual: String(sumNarratorsByAuthority),
  });

  const sumTemporalByState = Object.values(params.timelineAndCitations.temporalAssertions.byReviewState).reduce(
    (a, b) => a + b,
    0,
  );
  results.push({
    name: 'temporal_assertions_review_state_sum',
    passed: sumTemporalByState === params.timelineAndCitations.temporalAssertions.total,
    expected: String(params.timelineAndCitations.temporalAssertions.total),
    actual: String(sumTemporalByState),
  });

  const sumCitationsPartition =
    params.timelineAndCitations.citations.history +
    params.timelineAndCitations.citations.rijal +
    params.timelineAndCitations.citations.other;
  results.push({
    name: 'citations_lane_partition',
    passed: sumCitationsPartition === params.timelineAndCitations.citations.total,
    expected: String(params.timelineAndCitations.citations.total),
    actual: String(sumCitationsPartition),
  });

  const totalOrphans = Object.values(params.orphans).reduce((a, b) => a + b, 0);
  const nonZeroOrphans = Object.entries(params.orphans)
    .filter(([, count]) => count > 0)
    .map(([k, v]) => `${k}=${v}`);
  results.push({
    name: 'zero_orphaned_fks',
    passed: totalOrphans === 0,
    expected: '0',
    actual: String(totalOrphans),
    detail: nonZeroOrphans.length > 0 ? nonZeroOrphans.join(', ') : undefined,
  });

  if (params.minTranslationPct !== null && params.minTranslationPct !== undefined) {
    const totalTranslated = params.collections.reduce((acc, c) => acc + c.translations.total, 0);
    const globalPct = pct(totalTranslated, sumLiveHadiths);
    results.push({
      name: 'min_translation_pct_threshold',
      passed: globalPct >= params.minTranslationPct,
      expected: `>= ${params.minTranslationPct}%`,
      actual: `${globalPct}%`,
    });
  }

  return results;
}

export async function runCompletenessBenchmark(args: BenchArgs): Promise<CompletenessReport> {
  const target = resolveReadOnlyConnection(args.database);
  const sqlClient = postgres(target.url, connectionOptions(target.url, 4));

  try {
    const [
      collectionRows,
      directTotalsRows,
      narratorAuthorityRows,
      narratorBioRows,
      narratorLifespanRows,
      narratorAssessmentRows,
      narratorEventRows,
      epochRows,
      historicalEventRows,
      temporalAssertionRows,
      locationRows,
      citationRows,
      citationStateRows,
      bibWorkRows,
      editionRows,
      orphanRows,
    ] = await Promise.all([
      // 1. Per-collection completeness
      sqlClient`
        with live_hadiths as (
          select id, collection_id
          from hadiths
          where retired_at is null
        ),
        pub_hadiths as (
          select collection_id, count(*)::int as cnt
          from public_hadiths
          group by collection_id
        ),
        en_trans as (
          select
            h.collection_id,
            count(*)::int as total_trans,
            count(*) filter (where t.state = 'source_provided')::int as source_provided,
            count(*) filter (where t.state = 'machine_unreviewed')::int as machine_unreviewed,
            count(*) filter (where t.state = 'human_verified')::int as human_verified,
            count(*) filter (where t.state = 'source_verified')::int as source_verified,
            count(*) filter (where t.state = 'unknown_provenance')::int as unknown_provenance
          from translations t
          join live_hadiths h on h.id = t.hadith_id
          where t.retired_at is null and t.language = 'en'
          group by h.collection_id
        ),
        chain_stats as (
          select
            h.collection_id,
            count(*)::int as total_chains,
            count(distinct ch.hadith_id)::int as hadiths_with_chain,
            count(*) filter (where ch.structure_status = 'checked_by_rule')::int as checked_by_rule,
            count(*) filter (where ch.structure_status = 'uncertain')::int as uncertain,
            count(*) filter (where ch.structure_status = 'read_by_model')::int as read_by_model,
            count(*) filter (where ch.structure_status = 'ai_reviewed')::int as ai_reviewed,
            count(*) filter (where ch.structure_status = 'agent_verified')::int as agent_verified,
            count(*) filter (where ch.structure_status = 'verified_by_reviewer')::int as verified_by_reviewer,
            count(*) filter (
              where ch.structure_status is null
                 or ch.structure_status not in (
                   'checked_by_rule',
                   'uncertain',
                   'read_by_model',
                   'ai_reviewed',
                   'agent_verified',
                   'verified_by_reviewer'
                 )
            )::int as other_or_null
          from chains ch
          join live_hadiths h on h.id = ch.hadith_id
          where ch.retired_at is null
          group by h.collection_id
        ),
        assess_stats as (
          select
            h.collection_id,
            count(*)::int as total_assessments,
            count(distinct a.hadith_id)::int as hadiths_with_assessment
          from hadith_assessments a
          join live_hadiths h on h.id = a.hadith_id
          where a.retired_at is null
          group by h.collection_id
        ),
        hadith_counts as (
          select collection_id, count(*)::int as total_live
          from live_hadiths
          group by collection_id
        )
        select
          c.id as collection_id,
          c.slug,
          c.name,
          c.sort_key,
          coalesce(hc.total_live, 0)::int as total_live_hadiths,
          coalesce(ph.cnt, 0)::int as public_hadiths,
          coalesce(et.total_trans, 0)::int as total_trans,
          coalesce(et.source_provided, 0)::int as source_provided,
          coalesce(et.machine_unreviewed, 0)::int as machine_unreviewed,
          coalesce(et.human_verified, 0)::int as human_verified,
          coalesce(et.source_verified, 0)::int as source_verified,
          coalesce(et.unknown_provenance, 0)::int as unknown_provenance,
          coalesce(cs.total_chains, 0)::int as total_chains,
          coalesce(cs.hadiths_with_chain, 0)::int as hadiths_with_chain,
          coalesce(cs.checked_by_rule, 0)::int as checked_by_rule,
          coalesce(cs.uncertain, 0)::int as uncertain,
          coalesce(cs.read_by_model, 0)::int as read_by_model,
          coalesce(cs.ai_reviewed, 0)::int as ai_reviewed,
          coalesce(cs.agent_verified, 0)::int as agent_verified,
          coalesce(cs.verified_by_reviewer, 0)::int as verified_by_reviewer,
          coalesce(cs.other_or_null, 0)::int as other_or_null,
          coalesce(asst.total_assessments, 0)::int as total_assessments,
          coalesce(asst.hadiths_with_assessment, 0)::int as hadiths_with_assessment
        from collections c
        left join hadith_counts hc on hc.collection_id = c.id
        left join pub_hadiths ph on ph.collection_id = c.id
        left join en_trans et on et.collection_id = c.id
        left join chain_stats cs on cs.collection_id = c.id
        left join assess_stats asst on asst.collection_id = c.id
        where c.retired_at is null
        order by c.sort_key asc, c.slug asc
      `,

      // 2. Direct totals for invariants
      sqlClient`
        select
          (select count(*)::int from hadiths where retired_at is null) as total_live_hadiths,
          (select count(*)::int from public_hadiths) as total_public_hadiths,
          (select count(*)::int from narrators where retired_at is null) as total_live_narrators
      `,

      // 3. Narrators by authority
      sqlClient`
        select authority::text as authority, count(*)::int as cnt
        from narrators
        where retired_at is null
        group by authority
        order by cnt desc, authority asc
      `,

      // 4. Narrator bios
      sqlClient`
        select
          count(*)::int as total,
          count(*) filter (where status = 'published')::int as published,
          count(*) filter (where status = 'verified')::int as verified,
          count(*) filter (where status = 'proposed')::int as proposed
        from narrator_bios
        where retired_at is null
      `,

      // 5. Narrator lifespans
      sqlClient`
        select count(*)::int as total from narrator_lifespans
      `,

      // 6. Narrator assessments
      sqlClient`
        select
          count(*)::int as total,
          count(distinct narrator_id)::int as distinct_narrators,
          count(*) filter (where status = 'published')::int as published,
          count(*) filter (where status = 'verified')::int as verified,
          count(*) filter (where status = 'proposed')::int as proposed
        from narrator_assessments
        where retired_at is null
      `,

      // 7. Narrator events
      sqlClient`
        select
          count(*)::int as total,
          count(distinct narrator_id)::int as distinct_narrators,
          count(distinct event_id)::int as distinct_events
        from narrator_events
        where retired_at is null
      `,

      // 8. Epochs
      sqlClient`
        select
          (select count(*)::int from epochs where retired_at is null) as total,
          (select count(*)::int from epochs where retired_at is null and citation_id is not null) as cited,
          (select count(*)::int from epochs where retired_at is null and publication_ready = true) as published_flag,
          (select count(*)::int from published_epochs) as published_view
      `,

      // 9. Historical events
      sqlClient`
        select
          (select count(*)::int from historical_events where retired_at is null) as total,
          (
            select count(*)::int
            from historical_events
            where retired_at is null
              and (citation_id is not null or nullif(trim(citation_source), '') is not null)
          ) as cited,
          (select count(*)::int from historical_events where retired_at is null and publication_ready = true) as published_flag,
          (select count(*)::int from published_historical_events) as published_view
      `,

      // 10. Temporal assertions by review_state
      sqlClient`
        select review_state::text as review_state, count(*)::int as cnt
        from temporal_assertions
        where retired_at is null
        group by review_state
        order by cnt desc, review_state asc
      `,

      // 11. Locations
      sqlClient`
        select
          count(*)::int as total,
          count(*) filter (where latitude is not null and longitude is not null)::int as with_coordinates,
          count(*) filter (where cardinality(cited_in_citation_ids) > 0)::int as cited
        from locations
        where retired_at is null
      `,

      // 12. Citations lane breakdown (history vs rijal vs other)
      sqlClient`
        select
          count(*)::int as total,
          count(*) filter (
            where id like 'cit:rijal:%'
               or id like 'cit:rij:%'
               or coalesce(source_file, '') ilike '%rijal%'
          )::int as rijal,
          count(*) filter (
            where not (id like 'cit:rijal:%' or id like 'cit:rij:%' or coalesce(source_file, '') ilike '%rijal%')
              and (
                id like 'cit:hist:%'
                or id like 'cit:history:%'
                or coalesce(source_file, '') ilike '%history%'
                or id in (select citation_id from temporal_assertions where retired_at is null)
                or id in (select citation_id from epochs where retired_at is null and citation_id is not null)
                or id in (select citation_id from historical_events where retired_at is null and citation_id is not null)
              )
          )::int as history
        from citations
        where retired_at is null
      `,

      // 13. Citations by review_state
      sqlClient`
        select review_state::text as review_state, count(*)::int as cnt
        from citations
        where retired_at is null
        group by review_state
        order by cnt desc, review_state asc
      `,

      // 14. Bibliographic works
      sqlClient`
        select count(*)::int as total from bibliographic_works where retired_at is null
      `,

      // 15. Editions
      sqlClient`
        select count(*)::int as total from editions where retired_at is null
      `,

      // 16. Orphaned FK checks (live rows referencing missing or retired parents)
      sqlClient`
        select
          (select count(*)::int from hadiths h left join collections c on c.id = h.collection_id where h.retired_at is null and c.id is null) as hadiths_collection,
          (select count(*)::int from translations t left join hadiths h on h.id = t.hadith_id where t.retired_at is null and h.id is null) as translations_hadith,
          (select count(*)::int from chains ch left join hadiths h on h.id = ch.hadith_id where ch.retired_at is null and h.id is null) as chains_hadith,
          (select count(*)::int from hadith_assessments a left join hadiths h on h.id = a.hadith_id where a.retired_at is null and h.id is null) as hadith_assessments_hadith,
          (select count(*)::int from narrator_bios b left join narrators n on n.id = b.narrator_id where b.retired_at is null and n.id is null) as narrator_bios_narrator,
          (select count(*)::int from narrator_assessments a left join narrators n on n.id = a.narrator_id where a.retired_at is null and n.id is null) as narrator_assessments_narrator,
          (select count(*)::int from narrator_events ne left join narrators n on n.id = ne.narrator_id where ne.retired_at is null and n.id is null) as narrator_events_narrator,
          (select count(*)::int from narrator_events ne left join historical_events e on e.id = ne.event_id where ne.retired_at is null and e.id is null) as narrator_events_event,
          (select count(*)::int from temporal_assertions ta left join citations c on c.id = ta.citation_id where ta.retired_at is null and c.id is null) as temporal_assertions_citation,
          (select count(*)::int from citations c left join bibliographic_works w on w.id = c.work_id where c.retired_at is null and w.id is null) as citations_work,
          (select count(*)::int from editions e left join bibliographic_works w on w.id = e.work_id where e.retired_at is null and w.id is null) as editions_work
      `,
    ]);

    const collections: CollectionCompletenessRow[] = collectionRows.map((r) => {
      const totalLive = Number(r.total_live_hadiths);
      const totalTrans = Number(r.total_trans);
      const missingTrans = totalLive - totalTrans;
      const hadithsWithChain = Number(r.hadiths_with_chain);
      const hadithsWithAssessment = Number(r.hadiths_with_assessment);
      return {
        collectionId: String(r.collection_id),
        slug: String(r.slug),
        name: String(r.name),
        sortKey: Number(r.sort_key),
        totalLiveHadiths: totalLive,
        publicHadiths: Number(r.public_hadiths),
        translations: {
          total: totalTrans,
          sourceProvided: Number(r.source_provided),
          machineUnreviewed: Number(r.machine_unreviewed),
          humanVerified: Number(r.human_verified),
          sourceVerified: Number(r.source_verified),
          unknownProvenance: Number(r.unknown_provenance),
          missing: missingTrans,
          coveragePct: pct(totalTrans, totalLive),
          missingPct: pct(missingTrans, totalLive),
        },
        chains: {
          totalLiveChains: Number(r.total_chains),
          hadithsWithChain,
          coveragePct: pct(hadithsWithChain, totalLive),
          checkedByRule: Number(r.checked_by_rule),
          uncertain: Number(r.uncertain),
          readByModel: Number(r.read_by_model),
          aiReviewed: Number(r.ai_reviewed),
          agentVerified: Number(r.agent_verified),
          verifiedByReviewer: Number(r.verified_by_reviewer),
          otherOrNull: Number(r.other_or_null),
        },
        assessments: {
          totalLiveAssessments: Number(r.total_assessments),
          hadithsWithAssessment,
          coveragePct: pct(hadithsWithAssessment, totalLive),
        },
      };
    });

    const directTotals = directTotalsRows[0] ?? {
      total_live_hadiths: 0,
      total_public_hadiths: 0,
      total_live_narrators: 0,
    };
    const totalLiveHadithsDirect = Number(directTotals.total_live_hadiths);
    const totalPublicHadithsDirect = Number(directTotals.total_public_hadiths);
    const totalLiveNarrators = Number(directTotals.total_live_narrators);

    const byAuthority: Record<string, number> = {};
    for (const r of narratorAuthorityRows) {
      byAuthority[String(r.authority)] = Number(r.cnt);
    }

    const bioRow = narratorBioRows[0] ?? { total: 0, published: 0, verified: 0, proposed: 0 };
    const lifespanTotal = Number(narratorLifespanRows[0]?.total ?? 0);
    const narrAssessRow = narratorAssessmentRows[0] ?? {
      total: 0,
      distinct_narrators: 0,
      published: 0,
      verified: 0,
      proposed: 0,
    };
    const narrEventRow = narratorEventRows[0] ?? { total: 0, distinct_narrators: 0, distinct_events: 0 };

    const narrators: NarratorCompletenessSummary = {
      totalLiveNarrators,
      byAuthority,
      bios: {
        total: Number(bioRow.total),
        published: Number(bioRow.published),
        verified: Number(bioRow.verified),
        proposed: Number(bioRow.proposed),
        coveragePct: pct(Number(bioRow.total), totalLiveNarrators),
      },
      lifespans: {
        total: lifespanTotal,
        coveragePct: pct(lifespanTotal, totalLiveNarrators),
      },
      assessments: {
        total: Number(narrAssessRow.total),
        distinctNarrators: Number(narrAssessRow.distinct_narrators),
        published: Number(narrAssessRow.published),
        verified: Number(narrAssessRow.verified),
        proposed: Number(narrAssessRow.proposed),
        coveragePct: pct(Number(narrAssessRow.distinct_narrators), totalLiveNarrators),
      },
      events: {
        total: Number(narrEventRow.total),
        distinctNarrators: Number(narrEventRow.distinct_narrators),
        distinctEvents: Number(narrEventRow.distinct_events),
        coveragePct: pct(Number(narrEventRow.distinct_narrators), totalLiveNarrators),
      },
    };

    const epRow = epochRows[0] ?? { total: 0, cited: 0, published_flag: 0, published_view: 0 };
    const heRow = historicalEventRows[0] ?? { total: 0, cited: 0, published_flag: 0, published_view: 0 };
    const temporalByState: Record<string, number> = {};
    let temporalTotal = 0;
    for (const r of temporalAssertionRows) {
      const cnt = Number(r.cnt);
      temporalByState[String(r.review_state)] = cnt;
      temporalTotal += cnt;
    }

    const locRow = locationRows[0] ?? { total: 0, with_coordinates: 0, cited: 0 };
    const citRow = citationRows[0] ?? { total: 0, rijal: 0, history: 0 };
    const citTotal = Number(citRow.total);
    const citRijal = Number(citRow.rijal);
    const citHistory = Number(citRow.history);
    const citOther = citTotal - citRijal - citHistory;
    const citByState: Record<string, number> = {};
    for (const r of citationStateRows) {
      citByState[String(r.review_state)] = Number(r.cnt);
    }

    const timelineAndCitations: TimelineCitationsSummary = {
      epochs: {
        total: Number(epRow.total),
        cited: Number(epRow.cited),
        publishedFlag: Number(epRow.published_flag),
        publishedView: Number(epRow.published_view),
      },
      historicalEvents: {
        total: Number(heRow.total),
        cited: Number(heRow.cited),
        publishedFlag: Number(heRow.published_flag),
        publishedView: Number(heRow.published_view),
      },
      temporalAssertions: {
        total: temporalTotal,
        byReviewState: temporalByState,
      },
      locations: {
        total: Number(locRow.total),
        withCoordinates: Number(locRow.with_coordinates),
        cited: Number(locRow.cited),
      },
      citations: {
        total: citTotal,
        history: citHistory,
        rijal: citRijal,
        other: citOther,
        byReviewState: citByState,
      },
      bibliographicWorks: Number(bibWorkRows[0]?.total ?? 0),
      editions: Number(editionRows[0]?.total ?? 0),
    };

    // Optional 0025 timelines & contact-grid coverage (safe when 0025 is not yet applied)
    const [gridExistsRow] = await sqlClient`
      select to_regclass('public.timeline_tracks') is not null as has_grid
    `;
    if (gridExistsRow?.has_grid) {
      const [
        tracksCountRows,
        eventsWithTrackRows,
        psRows,
        psStateRows,
        nrRows,
        nrStateRows,
        naRows,
        naStateRows,
        etpRows,
        etpStateRows,
      ] = await Promise.all([
        sqlClient`select count(*)::int as total from timeline_tracks where retired_at is null`,
        sqlClient`select count(*)::int as total from historical_events where retired_at is null and track_id is not null`,
        sqlClient`
          select count(*)::int as total, count(distinct location_id)::int as distinct_locations
          from place_snapshots where retired_at is null
        `,
        sqlClient`
          select review_state::text as review_state, count(*)::int as cnt
          from place_snapshots where retired_at is null
          group by review_state order by cnt desc, review_state asc
        `,
        sqlClient`
          select
            count(*)::int as total,
            count(distinct narrator_id)::int as distinct_narrators,
            count(distinct location_id)::int as distinct_locations
          from narrator_residences where retired_at is null
        `,
        sqlClient`
          select review_state::text as review_state, count(*)::int as cnt
          from narrator_residences where retired_at is null
          group by review_state order by cnt desc, review_state asc
        `,
        sqlClient`
          select count(*)::int as total, count(distinct narrator_id)::int as distinct_narrators
          from narrator_affiliations where retired_at is null
        `,
        sqlClient`
          select review_state::text as review_state, count(*)::int as cnt
          from narrator_affiliations where retired_at is null
          group by review_state order by cnt desc, review_state asc
        `,
        sqlClient`
          select count(*)::int as total, count(distinct hadith_id)::int as distinct_hadiths
          from external_tradition_parallels where retired_at is null
        `,
        sqlClient`
          select review_state::text as review_state, count(*)::int as cnt
          from external_tradition_parallels where retired_at is null
          group by review_state order by cnt desc, review_state asc
        `,
      ]);

      const toStateMap = (rows: readonly Record<string, unknown>[]): Record<string, number> => {
        const out: Record<string, number> = {};
        for (const r of rows) out[String(r.review_state)] = Number(r.cnt);
        return out;
      };

      timelineAndCitations.contactGrid = {
        timelineTracks: Number(tracksCountRows[0]?.total ?? 0),
        historicalEventsWithTrack: Number(eventsWithTrackRows[0]?.total ?? 0),
        placeSnapshots: {
          total: Number(psRows[0]?.total ?? 0),
          distinctLocations: Number(psRows[0]?.distinct_locations ?? 0),
          byReviewState: toStateMap(psStateRows),
        },
        narratorResidences: {
          total: Number(nrRows[0]?.total ?? 0),
          distinctNarrators: Number(nrRows[0]?.distinct_narrators ?? 0),
          distinctLocations: Number(nrRows[0]?.distinct_locations ?? 0),
          byReviewState: toStateMap(nrStateRows),
        },
        narratorAffiliations: {
          total: Number(naRows[0]?.total ?? 0),
          distinctNarrators: Number(naRows[0]?.distinct_narrators ?? 0),
          byReviewState: toStateMap(naStateRows),
        },
        externalTraditionParallels: {
          total: Number(etpRows[0]?.total ?? 0),
          distinctHadiths: Number(etpRows[0]?.distinct_hadiths ?? 0),
          byReviewState: toStateMap(etpStateRows),
        },
      };
    }

    const orph = orphanRows[0] ?? {};
    const orphans: OrphanCheckCounts = {
      hadithsCollection: Number(orph.hadiths_collection ?? 0),
      translationsHadith: Number(orph.translations_hadith ?? 0),
      chainsHadith: Number(orph.chains_hadith ?? 0),
      hadithAssessmentsHadith: Number(orph.hadith_assessments_hadith ?? 0),
      narratorBiosNarrator: Number(orph.narrator_bios_narrator ?? 0),
      narratorAssessmentsNarrator: Number(orph.narrator_assessments_narrator ?? 0),
      narratorEventsNarrator: Number(orph.narrator_events_narrator ?? 0),
      narratorEventsEvent: Number(orph.narrator_events_event ?? 0),
      temporalAssertionsCitation: Number(orph.temporal_assertions_citation ?? 0),
      citationsWork: Number(orph.citations_work ?? 0),
      editionsWork: Number(orph.editions_work ?? 0),
    };

    const invariants = evaluateInvariants({
      collections,
      totalLiveHadithsDirect,
      totalPublicHadithsDirect,
      narrators,
      timelineAndCitations,
      orphans,
      minTranslationPct: args.minTranslationPct,
    });

    const totalTranslatedHadiths = collections.reduce((acc, c) => acc + c.translations.total, 0);
    const totalMissingTranslationHadiths = collections.reduce((acc, c) => acc + c.translations.missing, 0);
    const totalHadithsWithChain = collections.reduce((acc, c) => acc + c.chains.hadithsWithChain, 0);
    const totalHadithsWithAssessment = collections.reduce((acc, c) => acc + c.assessments.hadithsWithAssessment, 0);

    return {
      database: args.database,
      generatedAt: new Date().toISOString(),
      totals: {
        collections: collections.length,
        totalLiveHadiths: totalLiveHadithsDirect,
        totalPublicHadiths: totalPublicHadithsDirect,
        totalTranslatedHadiths,
        totalMissingTranslationHadiths,
        translationCoveragePct: pct(totalTranslatedHadiths, totalLiveHadithsDirect),
        totalHadithsWithChain,
        chainCoveragePct: pct(totalHadithsWithChain, totalLiveHadithsDirect),
        totalHadithsWithAssessment,
        assessmentCoveragePct: pct(totalHadithsWithAssessment, totalLiveHadithsDirect),
      },
      collections,
      narrators,
      timelineAndCitations,
      invariants,
      allPassed: invariants.every((inv) => inv.passed),
    };
  } finally {
    await sqlClient.end({ timeout: 5 });
  }
}

export function formatCompletenessReport(report: CompletenessReport): string {
  const lines: string[] = [];
  lines.push(`=== COMPLETENESS BENCHMARK (${report.database}) @ ${report.generatedAt} ===`);
  lines.push(
    `Corpus: ${report.totals.collections} collections | ${report.totals.totalLiveHadiths.toLocaleString()} live hadiths | ${report.totals.totalPublicHadiths.toLocaleString()} public | EN ${report.totals.translationCoveragePct}% | Chains ${report.totals.chainCoveragePct}% | Assessments ${report.totals.assessmentCoveragePct}%`,
  );
  lines.push('');

  lines.push('--- 1. PER-COLLECTION COMPLETENESS ---');
  lines.push(
    '| # | Collection | Live | Public | EN % | SrcProv | MachUnrev | Missing | Chain % | Rule | Uncert | Model | AIRev | AgtVer | HumVer | Assess % |',
  );
  lines.push(
    '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
  );
  for (const c of report.collections) {
    lines.push(
      `| ${c.sortKey} | ${c.slug} | ${c.totalLiveHadiths} | ${c.publicHadiths} | ${c.translations.coveragePct.toFixed(1)}% | ${c.translations.sourceProvided} | ${c.translations.machineUnreviewed} | ${c.translations.missing} | ${c.chains.coveragePct.toFixed(1)}% | ${c.chains.checkedByRule} | ${c.chains.uncertain} | ${c.chains.readByModel} | ${c.chains.aiReviewed} | ${c.chains.agentVerified} | ${c.chains.verifiedByReviewer} | ${c.assessments.coveragePct.toFixed(1)}% |`,
    );
  }
  lines.push('');

  lines.push('--- 2. BIOGRAPHIES & NARRATORS ---');
  const authSummary = Object.entries(report.narrators.byAuthority)
    .map(([k, v]) => `${k}=${v.toLocaleString()}`)
    .join(', ');
  lines.push(`Total live narrators: ${report.narrators.totalLiveNarrators.toLocaleString()} (${authSummary})`);
  lines.push(
    `narrator_bios: ${report.narrators.bios.total.toLocaleString()} (${report.narrators.bios.coveragePct}%) — published=${report.narrators.bios.published}, verified=${report.narrators.bios.verified}, proposed=${report.narrators.bios.proposed}`,
  );
  lines.push(
    `narrator_lifespans: ${report.narrators.lifespans.total.toLocaleString()} (${report.narrators.lifespans.coveragePct}%)`,
  );
  lines.push(
    `narrator_assessments: ${report.narrators.assessments.total.toLocaleString()} rows across ${report.narrators.assessments.distinctNarrators.toLocaleString()} narrators (${report.narrators.assessments.coveragePct}%) — published=${report.narrators.assessments.published}, verified=${report.narrators.assessments.verified}, proposed=${report.narrators.assessments.proposed}`,
  );
  lines.push(
    `narrator_events: ${report.narrators.events.total.toLocaleString()} links across ${report.narrators.events.distinctNarrators.toLocaleString()} narrators (${report.narrators.events.coveragePct}%) and ${report.narrators.events.distinctEvents.toLocaleString()} events`,
  );
  lines.push('');

  lines.push('--- 3. TIMELINE & CITATIONS ---');
  const tc = report.timelineAndCitations;
  lines.push(
    `epochs: total=${tc.epochs.total}, cited=${tc.epochs.cited}, published_flag=${tc.epochs.publishedFlag}, published_view=${tc.epochs.publishedView}`,
  );
  lines.push(
    `historical_events: total=${tc.historicalEvents.total}, cited=${tc.historicalEvents.cited}, published_flag=${tc.historicalEvents.publishedFlag}, published_view=${tc.historicalEvents.publishedView}`,
  );
  const taSummary = Object.entries(tc.temporalAssertions.byReviewState)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ');
  lines.push(`temporal_assertions: total=${tc.temporalAssertions.total} (${taSummary || 'none'})`);
  lines.push(
    `locations: total=${tc.locations.total}, with_coordinates=${tc.locations.withCoordinates}, cited=${tc.locations.cited}`,
  );
  const citStateSummary = Object.entries(tc.citations.byReviewState)
    .map(([k, v]) => `${k}=${v.toLocaleString()}`)
    .join(', ');
  lines.push(
    `citations: total=${tc.citations.total.toLocaleString()} (history=${tc.citations.history.toLocaleString()}, rijal=${tc.citations.rijal.toLocaleString()}, other=${tc.citations.other.toLocaleString()}) [${citStateSummary || 'none'}]`,
  );
  lines.push(`bibliographic_works: ${tc.bibliographicWorks.toLocaleString()} | editions: ${tc.editions.toLocaleString()}`);
  if (tc.contactGrid) {
    const cg = tc.contactGrid;
    const fmtStates = (m: Record<string, number>) =>
      Object.entries(m)
        .map(([k, v]) => `${k}=${v}`)
        .join(', ') || 'none';
    lines.push(
      `timeline_tracks: ${cg.timelineTracks} | historical_events with track_id: ${cg.historicalEventsWithTrack}/${tc.historicalEvents.total}`,
    );
    lines.push(
      `place_snapshots: total=${cg.placeSnapshots.total}, distinct_locations=${cg.placeSnapshots.distinctLocations} [${fmtStates(cg.placeSnapshots.byReviewState)}]`,
    );
    lines.push(
      `narrator_residences: total=${cg.narratorResidences.total}, narrators=${cg.narratorResidences.distinctNarrators}, locations=${cg.narratorResidences.distinctLocations} [${fmtStates(cg.narratorResidences.byReviewState)}]`,
    );
    lines.push(
      `narrator_affiliations: total=${cg.narratorAffiliations.total}, narrators=${cg.narratorAffiliations.distinctNarrators} [${fmtStates(cg.narratorAffiliations.byReviewState)}]`,
    );
    lines.push(
      `external_tradition_parallels: total=${cg.externalTraditionParallels.total}, hadiths=${cg.externalTraditionParallels.distinctHadiths} [${fmtStates(cg.externalTraditionParallels.byReviewState)}]`,
    );
  }
  lines.push('');

  lines.push('--- 4. MATHEMATICAL INVARIANTS ---');
  for (const inv of report.invariants) {
    const status = inv.passed ? 'PASS' : 'FAIL';
    const extra = inv.detail ? ` (${inv.detail})` : '';
    lines.push(`[${status}] ${inv.name}: expected=${inv.expected}, actual=${inv.actual}${extra}`);
  }
  lines.push(`OVERALL: ${report.allPassed ? 'PASS' : 'FAIL'}`);
  return lines.join('\n');
}

export async function main(argv: readonly string[]): Promise<number> {
  const args = parseBenchArgs(argv);
  const report = await runCompletenessBenchmark(args);
  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(formatCompletenessReport(report));
  }
  return report.allPassed ? 0 : 1;
}

if (/bench-completeness\.ts$/.test(process.argv[1] ?? '')) {
  main(process.argv.slice(2))
    .then((code) => process.exit(code))
    .catch((error) => {
      console.error(error instanceof Error ? error.message : error);
      process.exit(1);
    });
}
