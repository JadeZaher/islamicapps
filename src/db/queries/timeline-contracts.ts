/**
 * Read contracts for the time-and-place layer (narrator and chain timelines). Types only, safe for client
 * components. See src/db/queries/AGENTS.md §Time and place.
 */

/** Who may see what: `public` shows only published, cited data; `review` shows every live row with its basis. */
export type TimelineAudience = 'public' | 'review';

/** Where a datum comes from and whether it has been reviewed; each value has one fixed reader-facing label. */
export type DatumBasis =
  | 'lexicon_uncited'
  | 'bio_uncited'
  | 'bio_cited'
  | 'seed_unverified'
  | 'curated_unreviewed'
  | 'reviewed_unpublished'
  | 'reviewed_cited';

/** Inclusive Hijri year range; a point year has min === max. Years before the Hijra are negative (53 BH = -53). */
export interface YearRange {
  min: number;
  max: number;
}

export interface DateClaim {
  event: 'birth' | 'death';
  range: YearRange;
  basis: DatumBasis;
  /** The value exactly as the source row holds it, e.g. "-53" or "0". */
  as_recorded: string;
  /** False when the recorded value cannot be a Hijri year (there is no year 0); such a claim is listed, never drawn. */
  usable: boolean;
}

/** Lifespan as ranges. `birth`/`death` span every usable claim, so competing reports widen the range. */
export interface Lifespan {
  birth: YearRange | null;
  death: YearRange | null;
  claims: DateClaim[];
  /** True when usable claims for the same event do not agree. */
  competing: boolean;
}

/** Broad generation classes in time order; `rank` is the position on that scale. */
export type GenerationClass =
  | 'prophet'
  | 'companion'
  | 'follower'
  | 'follower_of_followers'
  | 'third_century'
  | 'fourth_century_or_later';

export interface GenerationClaim {
  class: GenerationClass;
  rank: number;
  /** Finer numbered generation as the source writes it (the lexicon's "[6th generation]"), when present. */
  number: number | null;
  as_recorded: string;
  basis: DatumBasis;
}

export interface PlaceClaim {
  place: string;
  relation: 'born' | 'died' | 'resided' | 'region';
  basis: DatumBasis;
  location_id: string | null;
}

export interface TimelineInterval {
  id: string;
  name: string;
  name_arabic: string | null;
  /** Outer bounds: earliest start, latest end; `end` null means the period continues. */
  start: number;
  end: number | null;
  /** Present only when a boundary is disputed: the inner bounds and the note that says so. */
  start_latest: number | null;
  end_earliest: number | null;
  boundary_note: string | null;
  basis: DatumBasis;
}

export interface TimelineCitation {
  id: string | null;
  work_title: string | null;
  work_title_ar: string | null;
  author: string | null;
  edition: string | null;
  volume: string | null;
  page: string | null;
  locator: string | null;
  url: string | null;
  review_state: string | null;
}

export interface TimelineTemporalAssertion {
  id: string;
  predicate: string;
  year_min: number | null;
  year_max: number | null;
  statement_en: string | null;
  stated_ar: string | null;
  review_state: string;
  citation: TimelineCitation | null;
}

export interface EpochEntry extends TimelineInterval {
  kind: 'epoch';
  parent_id: string | null;
  tradition_context: string | null;
  alternate_names: Array<{ name: string; name_arabic?: string; used_by: string }>;
  overview: string | null;
  citation?: TimelineCitation | null;
  temporal_assertions?: TimelineTemporalAssertion[];
}

export interface EventEntry extends TimelineInterval {
  kind: 'event';
  category: string | null;
  location_name: string | null;
  location_id: string | null;
  description: string | null;
  significance?: string | null;
  track_id?: string | null;
  track_slug?: string | null;
  track_category?: TimelineTrackCategory | null;
  citation?: TimelineCitation | null;
  temporal_assertions?: TimelineTemporalAssertion[];
}

export type TimelineTrackCategory =
  | 'political'
  | 'world_event'
  | 'technological'
  | 'intellectual_movement'
  | 'demographic_shift'
  | 'legal_theological'
  | 'trade_pilgrimage';

export type TimelineContextLayer = 'political' | 'places' | 'tech' | 'parallels';

export interface TimelineTrackEntry {
  id: string;
  slug: string;
  title: string;
  category: TimelineTrackCategory;
  scope: 'global' | 'regional' | 'city';
  description: string | null;
}

export interface PlaceSnapshotEntry {
  id: string;
  location_id: string;
  location_name: string | null;
  year_min: number | null;
  year_max: number | null;
  precision: string | null;
  polity_or_ruler: string | null;
  dominant_schools: string[];
  religious_communities: Record<string, unknown>;
  languages: string[];
  ethnographic_notes: string | null;
  review_state: string;
  citation: TimelineCitation | null;
}

export interface NarratorResidenceEntry {
  id: string;
  narrator_id: string;
  narrator_name?: string | null;
  location_id: string;
  location_name: string | null;
  year_min: number | null;
  year_max: number | null;
  precision: string | null;
  role: string;
  review_state: string;
  citation: TimelineCitation | null;
}

export interface NarratorAffiliationEntry {
  id: string;
  narrator_id: string;
  narrator_name?: string | null;
  kind: string;
  label: string;
  note: string | null;
  review_state: string;
  citation: TimelineCitation | null;
}

export interface ExternalTraditionParallelEntry {
  id: string;
  hadith_id: string;
  tradition_source: string;
  relation_type: string;
  source_work: string;
  locator: string | null;
  note: string | null;
  review_state: string;
  citation: TimelineCitation | null;
}

export interface NarratorEventEntry {
  id: string;
  event_id: string;
  role: string;
  stated_ar: string | null;
  event: EventEntry;
  citation: TimelineCitation | null;
}

/** How an era or event relates to what is known of a life. Never inferred from an unknown bound. */
export type LifeRelation = 'during_lifetime' | 'at_death' | 'at_birth';

export interface RelatedInterval<T extends TimelineInterval> {
  entry: T;
  relation: LifeRelation;
}

export interface NarratorTimeline {
  narrator_id: string;
  audience: TimelineAudience;
  lifespan: Lifespan;
  generation: GenerationClaim[];
  places: PlaceClaim[];
  epochs: Array<RelatedInterval<EpochEntry>>;
  events: Array<RelatedInterval<EventEntry>>;
  /** Direct narrator-to-event links (`narrator_events`), distinct from contextual lifespan overlap. */
  narrator_events: NarratorEventEntry[];
  /** Multi-axis timeline tracks and cultural-contact grid (0025). */
  tracks?: TimelineTrackEntry[];
  residences?: NarratorResidenceEntry[];
  affiliations?: NarratorAffiliationEntry[];
  place_snapshots?: PlaceSnapshotEntry[];
  parallels?: ExternalTraditionParallelEntry[];
  timelines_grid_available?: boolean;
  /** False when the epochs table is not yet in this database (pending migration). */
  epochs_available: boolean;
}

/** How the person at a chain position is known. Dates are drawn only for `verified` and `single_candidate`. */
export type ChainIdentity = 'verified' | 'single_candidate' | 'candidates_differ' | 'unidentified';

export interface ChainTransmitter {
  mention_id: string;
  position: number;
  surface_ar: string;
  identity: ChainIdentity;
  /** Basis labels of the identity (e.g. "matched by name"); empty for a verified link. */
  identity_bases: string[];
  narrator_id: string | null;
  name_en: string | null;
  name_ar: string | null;
  /** Other narrators the candidates name when they differ. */
  candidate_names: Array<{ narrator_id: string; name: string }>;
  lifespan: Lifespan;
  generation: GenerationClaim[];
  places: PlaceClaim[];
}

export type ChronologicalGapKind = 'lifespans_do_not_overlap' | 'generations_not_adjacent';

/** Information for the reader, never a verdict on the chain. */
export interface ChronologicalGap {
  kind: ChronologicalGapKind;
  /** The transmitter nearer the compiler (heard from `teacher_position`). */
  student_position: number;
  teacher_position: number;
  /** Reader-facing sentence with the basis of each date or generation. */
  statement: string;
}

export interface ChainTimeline {
  chain_id: string;
  hadith_id: string;
  branch: number;
  /** Earliest transmitter first (the reverse of the isnad as written). */
  transmitters: ChainTransmitter[];
  /** Span of all drawable years in the chain, or null when none is known. */
  span: YearRange | null;
  gaps: ChronologicalGap[];
}

export interface ChainFamilyTimeline {
  audience: TimelineAudience;
  hadith_ids: string[];
  /** Tradition of each report, for the tradition lane of epochs. */
  traditions: Record<string, string | null>;
  source_works: Record<string, string | null>;
  chains: ChainTimeline[];
  /** One axis for every chain. */
  span: YearRange | null;
  epochs: EpochEntry[];
  events: EventEntry[];
  /** Multi-axis timeline tracks and cultural-contact grid (0025). */
  tracks?: TimelineTrackEntry[];
  residences?: NarratorResidenceEntry[];
  affiliations?: NarratorAffiliationEntry[];
  place_snapshots?: PlaceSnapshotEntry[];
  parallels?: ExternalTraditionParallelEntry[];
  timelines_grid_available?: boolean;
  epochs_available: boolean;
}
