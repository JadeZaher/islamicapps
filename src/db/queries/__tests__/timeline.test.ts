/**
 * Time-and-place flows against the fixture schema with real rows: the history seed through the query layer, the
 * pending epochs migration, narrator timelines, and the chain-family timeline with its chronological gaps.
 * Real extra rows (fixtures/timeline.json) are copied from the development database (`generated_from` names it).
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/timeline.test.ts
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import type { Sql } from 'postgres';
import { FIXTURE_VERSION_ID, prepareFixtureDatabase, type FixtureDatabase } from './fixture-database';
import { flow, runFlows } from './harness';
import { eventSeedRows, seedHistory, stableSeedId } from '../../../scripts/db/seed-history';
import { updateHistoricalEvent } from '../history';
import { getChainFamilyTimeline, getNarratorTimeline } from '../timeline';
import type { ReadVisibility } from '../visibility';
import { createSessionToken } from '../../../lib/auth/session';
import { visibilityForSessionToken } from '../../../lib/auth/visibility';

const UMAR = 'narrator:rawi:3';
const MUHAMMAD_IBN_IBRAHIM = 'narrator:rawi:11213';
const HUSAYN_BIN_MUHAMMAD = 'narrator:rawi:39284';
const SUFYAN_IBN_UYAYNA = 'narrator:rawi:20005';
const BUKHARI_813 = 'hadith:k6:813';
const BUKHARI_1 = 'hadith:k6:1';
const CURATOR = 'curator:fixture-historian';

type Rows = Array<Record<string, unknown>>;
interface TimelineFixture {
  narrators: Rows;
  lexicon_profiles: Rows;
  hadiths: Rows;
  chains: Rows;
  mentions: Rows;
  narrator_bios: Rows;
}

let fixture: FixtureDatabase;
/** Curator visibility minted the only supported way: a verified session under private preview. */
let curator: ReadVisibility;

/** Inserts real rows generically: every non-generated column, fixture bookkeeping, no book/chapter links. */
async function insertRows(sql: Sql, table: string, rows: Rows, overrides: Record<string, unknown> = {}): Promise<void> {
  if (rows.length === 0) return;
  const columns = (await sql<{ column_name: string }[]>`
    select column_name from information_schema.columns
    where table_schema = ${fixture.schema} and table_name = ${table} and is_generated = 'NEVER'`).map((row) => row.column_name);
  const prepared = rows.map((row) => {
    const copy: Record<string, unknown> = { ...row, ...overrides };
    for (const key of ['first_seen_dataset_version_id', 'changed_in_dataset_version_id']) if (key in copy) copy[key] = FIXTURE_VERSION_ID;
    return copy;
  });
  const list = sql.unsafe(columns.map((column) => `"${column}"`).join(', '));
  await sql`insert into ${sql(table)} (${list})
            select ${list} from jsonb_populate_recordset(null::${sql(table)}, ${sql.json(prepared as never)})
            on conflict do nothing`;
}

async function setUp(): Promise<void> {
  fixture = await prepareFixtureDatabase(process.env.TIMELINE_FIXTURE_SCHEMA || 'timeline_fixture');
  const pending = readFileSync(path.resolve(__dirname, '../../ops/pending/epochs.pending.sql'), 'utf8');
  for (const statement of pending.split('--> statement-breakpoint').map((part) => part.trim()).filter(Boolean)) {
    await fixture.sql.unsafe(statement);
  }
  const extra = JSON.parse(readFileSync(path.join(__dirname, 'fixtures/timeline.json'), 'utf8')) as TimelineFixture;
  await insertRows(fixture.sql, 'narrators', extra.narrators);
  await insertRows(fixture.sql, 'narrator_lexicon_profiles', extra.lexicon_profiles);
  await insertRows(fixture.sql, 'hadiths', extra.hadiths, { book_id: null, chapter_id: null });
  await insertRows(fixture.sql, 'chains', extra.chains);
  await insertRows(fixture.sql, 'chain_mentions', extra.mentions, { decision_id: null });
  await insertRows(fixture.sql, 'narrator_bios', extra.narrator_bios);

  const secret = 'timeline-fixture-session-secret-0123456789abcdef';
  process.env.ADMIN_SESSION_SECRET = secret;
  process.env.CURATOR_PASSPHRASES = JSON.stringify({ 'fixture-historian': 'scrypt$unused' });
  const token = await createSessionToken('fixture-historian', secret);
  curator = await visibilityForSessionToken(token, { ...process.env, PRIVATE_PREVIEW: '1' });
  assert.equal(curator, 'curator');
}

flow('seed: the history seed loads locations, events and eras as unverified seed rows, audited', async () => {
  const outcome = await seedHistory();
  assert.deepEqual(
    [outcome.locations.created.length, outcome.events.created.length, outcome.epochs?.created.length],
    [32, 54, 38],
  );
  const [states] = await fixture.sql<{ statuses: string[]; published: number; linked: number; audits: number }[]>`
    select array(select distinct verification_status::text from historical_events) as statuses,
           (select count(*)::int from historical_events where publication_ready) as published,
           (select count(*)::int from historical_events where location_id is not null) as linked,
           (select count(*)::int from curation_audit where actor = 'system:seed' and action = 'seed_create') as audits`;
  assert.deepEqual(states.statuses, ['unverified_seed']);
  assert.equal(states.published, 0);
  // The two "Egypt" events have no seeded location of that name: loaded without a link, never guessed.
  assert.equal(states.linked, 52);
  assert.deepEqual(eventSeedRows().unlinked.map((row) => row.location_name), ['Egypt', 'Egypt']);
  assert.equal(states.audits, 32 + 54 + 38);
});

flow('seed: re-running changes nothing, refreshes a drifted seed row, and never overwrites a reviewed event', async () => {
  const again = await seedHistory();
  assert.deepEqual([again.locations.created.length, again.events.created.length, again.events.refreshed.length], [0, 0, 0]);
  assert.equal(again.events.unchanged.length, 54);

  const badr = stableSeedId('historical-event', 'Battle of Badr', 2);
  const uhud = stableSeedId('historical-event', 'Battle of Uhud', 3);
  await updateHistoricalEvent(CURATOR, badr, {
    title: 'Battle of Badr (reviewed wording)',
    verification_status: 'human_verified',
    citation_source: 'Ibn Hisham, al-Sira al-Nabawiyya',
    citation_locator: 'vol. 1, p. 606',
  });
  await fixture.sql`update historical_events set description = 'drifted' where id = ${uhud}`;

  const third = await seedHistory();
  assert.deepEqual(third.events.keptCurated, [{ id: badr, reason: 'reviewed (human_verified)' }]);
  assert.deepEqual(third.events.refreshed, [uhud]);
  const [rows] = await fixture.sql<{ badr_title: string; badr_status: string; uhud_description: string }[]>`
    select (select title from historical_events where id = ${badr}) as badr_title,
           (select verification_status::text from historical_events where id = ${badr}) as badr_status,
           (select description from historical_events where id = ${uhud}) as uhud_description`;
  assert.equal(rows.badr_title, 'Battle of Badr (reviewed wording)');
  assert.equal(rows.badr_status, 'human_verified');
  assert.notEqual(rows.uhud_description, 'drifted');
});

flow('narrator with known dates: the eras and events of the recorded lifetime, and nothing outside it', async () => {
  const umar = await getNarratorTimeline(UMAR, curator);
  assert.deepEqual([umar.lifespan.birth, umar.lifespan.death], [{ min: -41, max: -41 }, { min: 23, max: 23 }]);
  assert.ok(umar.lifespan.claims.every((claim) => claim.basis === 'lexicon_uncited'));
  const eras = new Map(umar.epochs.map((item) => [item.entry.id, item.relation]));
  for (const id of ['epoch:prophetic-mission', 'epoch:prophetic-mission-makkah', 'epoch:first-four-caliphs', 'epoch:caliphate-umar', 'epoch:imami-imamate-ali']) {
    assert.equal(eras.get(id), 'during_lifetime', id);
  }
  for (const id of ['epoch:umayyad', 'epoch:caliphate-ali', 'epoch:abbasid']) assert.ok(!eras.has(id), id);
  const events = umar.events.map((item) => item.entry.name);
  assert.ok(events.includes('The Hijra (Migration to Medina)') && events.includes('Umar becomes Caliph'));
  assert.ok(!events.includes('Assassination of Uthman'), 'an event after the recorded death is not lived through');
  assert.ok(!events.includes('Birth of Prophet Muhammad'), 'the corrected 53 BH is before the recorded birth (41 BH)');
  assert.ok(umar.epochs.every((item) => item.entry.basis === 'seed_unverified'));
  assert.deepEqual(umar.generation.map((claim) => [claim.class, claim.number]), [['companion', 1]]);
});

flow('only a death year, or only a generation: no era or event is claimed beyond what is recorded', async () => {
  const deathOnly = await getNarratorTimeline(MUHAMMAD_IBN_IBRAHIM, curator);
  assert.equal(deathOnly.lifespan.birth, null);
  assert.deepEqual(deathOnly.lifespan.death, { min: 120, max: 120 });
  assert.deepEqual(deathOnly.events, [], 'no event contains the year 120; earlier events are not "lived through"');
  assert.deepEqual(
    deathOnly.epochs.map((item) => [item.entry.id, item.relation]).sort(),
    [
      ['epoch:imami-imamate-sadiq', 'at_death'],
      ['epoch:imami-presence-of-the-imams', 'at_death'],
      ['epoch:umayyad', 'at_death'],
      ['epoch:umayyad-marwanid', 'at_death'],
    ],
  );

  const generationOnly = await getNarratorTimeline(HUSAYN_BIN_MUHAMMAD, curator);
  assert.deepEqual([generationOnly.lifespan.birth, generationOnly.lifespan.death], [null, null]);
  assert.deepEqual(generationOnly.generation.map((claim) => claim.class), ['third_century']);
  assert.deepEqual([generationOnly.epochs.length, generationOnly.events.length], [0, 0]);
});

flow('public reader: no lexicon date and no unreviewed era or event is shown', async () => {
  const umar = await getNarratorTimeline(UMAR, 'public');
  assert.deepEqual([umar.lifespan.claims.length, umar.generation.length, umar.places.length], [0, 0, 0]);
  assert.deepEqual([umar.epochs.length, umar.events.length], [0, 0]);
});

flow('chain: a non-overlap between consecutive transmitters is reported with the basis of each date', async () => {
  const family = await getChainFamilyTimeline([BUKHARI_813], curator);
  assert.equal(family.chains.length, 1);
  const [chain] = family.chains;
  assert.deepEqual(chain.transmitters.map((transmitter) => transmitter.position), [4, 3, 2, 1, 0], 'earliest transmitter first');
  const lifespanGaps = chain.gaps.filter((gap) => gap.kind === 'lifespans_do_not_overlap');
  assert.equal(lifespanGaps.length, 1);
  assert.deepEqual([lifespanGaps[0].teacher_position, lifespanGaps[0].student_position], [1, 0]);
  assert.match(lifespanGaps[0].statement, /^Lifespans as recorded do not overlap: Qutayba/);
  assert.match(lifespanGaps[0].statement, /born 150 AH \(narrator lexicon, not yet cited\)/);
  assert.match(lifespanGaps[0].statement, /death 106 AH \(narrator lexicon, not yet cited\)/);
  assert.ok(chain.gaps.every((gap) => !/weak|broken|da.?if|invalid/i.test(gap.statement)), 'a gap is information, not a ruling');
  assert.ok(family.span && family.epochs.length > 0);
});

flow('chain family: competing death years stay competing, on one axis with the other report', async () => {
  const family = await getChainFamilyTimeline([BUKHARI_1, BUKHARI_813], curator);
  assert.deepEqual([...new Set(family.chains.map((chain) => chain.hadith_id))], [BUKHARI_1, BUKHARI_813]);
  const sufyan = family.chains[0].transmitters.find((transmitter) => transmitter.narrator_id === SUFYAN_IBN_UYAYNA)!;
  assert.equal(sufyan.lifespan.competing, true);
  assert.deepEqual(sufyan.lifespan.death, { min: 196, max: 198 });
  assert.deepEqual(
    sufyan.lifespan.claims.filter((claim) => claim.event === 'death').map((claim) => [claim.range.min, claim.basis]),
    [[196, 'lexicon_uncited'], [198, 'bio_uncited']],
  );
  assert.ok(family.span!.min <= -41 && family.span!.max >= 219, 'one axis spans both reports');
});

async function main() {
  await setUp();
  await runFlows(async () => {
    const { getDatabase } = await import('../../client');
    await getDatabase().$client.end({ timeout: 5 });
    await fixture.sql.unsafe(`drop schema if exists ${fixture.schema} cascade`);
    await fixture.close();
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
