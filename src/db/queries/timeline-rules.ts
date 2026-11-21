/**
 * Pure rules of the time-and-place layer: basis labels, Hijri formatting, generation parsing, lifespan ranges,
 * life-relation (interval overlap) and the chronological-gap rule. No database access; safe for client
 * components and unit tests. See src/db/queries/AGENTS.md §Time and place.
 */
import type {
  ChainTransmitter,
  ChronologicalGap,
  DateClaim,
  DatumBasis,
  GenerationClaim,
  GenerationClass,
  LifeRelation,
  Lifespan,
  PlaceClaim,
  TimelineInterval,
  YearRange,
} from './timeline-contracts';

const BASIS_LABELS: Record<DatumBasis, string> = {
  lexicon_uncited: 'narrator lexicon, not yet cited',
  bio_uncited: 'hand-written biography, not yet cited',
  bio_cited: 'curated biography, cited',
  seed_unverified: 'seed, unverified',
  curated_unreviewed: 'curator entry, not yet reviewed',
  reviewed_unpublished: 'reviewed, not yet published',
  reviewed_cited: 'reviewed and cited',
};

export function basisLabel(basis: DatumBasis): string {
  return BASIS_LABELS[basis];
}

/** Hijri year for display: negative years are "BH" (before the Hijra). 0 is not a Hijri year and says so. */
export function formatHijri(year: number): string {
  if (year === 0) return '0 (not a Hijri year)';
  return year < 0 ? `${-year} BH` : `${year} AH`;
}

/** "93 AH", "93–94 AH", "1 BH – 1 AH". */
export function formatRange(range: YearRange): string {
  if (range.min === range.max) return formatHijri(range.min);
  if (range.min > 0 || range.max < 0) {
    const era = range.max < 0 ? 'BH' : 'AH';
    const low = range.max < 0 ? -range.max : range.min;
    const high = range.max < 0 ? -range.min : range.max;
    return `${low}–${high} ${era}`;
  }
  return `${formatHijri(range.min)} – ${formatHijri(range.max)}`;
}

/** Outer interval bounds, "from 132 AH", "41–132 AH". */
export function formatInterval(interval: Pick<TimelineInterval, 'start' | 'end'>): string {
  if (interval.end === null) return `from ${formatHijri(interval.start)}`;
  return formatRange({ min: interval.start, max: interval.end });
}

const GENERATION_RANK: Record<GenerationClass, number> = {
  prophet: 0,
  companion: 1,
  follower: 2,
  follower_of_followers: 3,
  third_century: 4,
  fourth_century_or_later: 5,
};

const GENERATION_LABELS: Record<GenerationClass, string> = {
  prophet: 'the Prophet',
  companion: 'a Companion',
  follower: 'a Follower',
  follower_of_followers: 'a Follower of the Followers',
  third_century: 'a third-century transmitter',
  fourth_century_or_later: 'a fourth-century or later transmitter',
};

export function generationLabel(claim: Pick<GenerationClaim, 'class' | 'number'>): string {
  const base = GENERATION_LABELS[claim.class];
  return claim.number === null ? base : `${base} (generation ${claim.number} in the lexicon's numbering)`;
}

function generationClaim(generationClass: GenerationClass, number: number | null, asRecorded: string, basis: DatumBasis): GenerationClaim {
  return { class: generationClass, rank: GENERATION_RANK[generationClass], number, as_recorded: asRecorded, basis };
}

/**
 * Reads the narrator lexicon's generation marker (`lexicon_grade_label`, e.g. "Follower(Tabi') [6th generation]").
 * The marker is a generation class, never a verdict. "Prophet's Relative" names no generation and gives null.
 */
export function parseLexiconGeneration(label: string | null | undefined, basis: DatumBasis): GenerationClaim | null {
  const text = (label ?? '').trim();
  if (!text) return null;
  const numbered = /\[(\d{1,2})(?:st|nd|rd|th) generation\]/i.exec(text);
  const number = numbered ? Number(numbered[1]) : null;
  const prefixes: Array<[RegExp, GenerationClass]> = [
    [/^Rasool Allah/i, 'prophet'],
    [/^Comp\./i, 'companion'],
    [/^Follower/i, 'follower'],
    [/^Succ\./i, 'follower_of_followers'],
    [/^3rd Century AH/i, 'third_century'],
    [/^(?:[4-9]|1\d)th Century AH/i, 'fourth_century_or_later'],
  ];
  const match = prefixes.find(([pattern]) => pattern.test(text));
  return match ? generationClaim(match[1], number, text, basis) : null;
}

const TABAQAH_CLASSES: Record<string, GenerationClass> = {
  PROPHET: 'prophet',
  SAHABA: 'companion',
  TABIUN: 'follower',
  ATBA_TABIUN: 'follower_of_followers',
  ATBA_ATBA: 'third_century',
  LATER_SCHOLAR: 'fourth_century_or_later',
};

/** A curated `tabaqah_class` value as a generation claim. */
export function generationFromTabaqahClass(value: string | null | undefined, basis: DatumBasis): GenerationClaim | null {
  const generationClass = value ? TABAQAH_CLASSES[value] : undefined;
  return generationClass ? generationClaim(generationClass, null, value!, basis) : null;
}

/** A recorded year as a claim; 0 is kept and listed but marked unusable (the Hijri count has no year 0). */
export function yearClaim(event: 'birth' | 'death', year: number | null | undefined, basis: DatumBasis): DateClaim | null {
  if (year === null || year === undefined || !Number.isFinite(year)) return null;
  return { event, range: { min: year, max: year }, basis, as_recorded: String(year), usable: year !== 0 };
}

function spanOf(claims: DateClaim[]): YearRange | null {
  if (claims.length === 0) return null;
  return { min: Math.min(...claims.map((claim) => claim.range.min)), max: Math.max(...claims.map((claim) => claim.range.max)) };
}

function claimsDisagree(claims: DateClaim[]): boolean {
  return new Set(claims.map((claim) => `${claim.range.min}:${claim.range.max}`)).size > 1;
}

/** Combines claims into ranges: competing reports widen the range and set `competing`; nothing is resolved. */
export function buildLifespan(claims: Array<DateClaim | null>): Lifespan {
  const present = claims.filter((claim): claim is DateClaim => claim !== null);
  const births = present.filter((claim) => claim.event === 'birth' && claim.usable);
  const deaths = present.filter((claim) => claim.event === 'death' && claim.usable);
  return {
    birth: spanOf(births),
    death: spanOf(deaths),
    claims: present,
    competing: claimsDisagree(births) || claimsDisagree(deaths),
  };
}

/**
 * How an interval relates to a life, on the most permissive bounds (earliest birth, latest death):
 * both bounds known: overlap with the lifetime; only death known: the interval contains the death year(s);
 * only birth known: it contains the birth year(s); nothing known: null. An unknown bound never widens a life.
 */
export function relationToLife(lifespan: Pick<Lifespan, 'birth' | 'death'>, interval: Pick<TimelineInterval, 'start' | 'end'>): LifeRelation | null {
  const intervalEnd = interval.end ?? Number.POSITIVE_INFINITY;
  const { birth, death } = lifespan;
  if (birth && death) {
    return intervalEnd >= birth.min && interval.start <= death.max ? 'during_lifetime' : null;
  }
  if (death) return interval.start <= death.max && intervalEnd >= death.min ? 'at_death' : null;
  if (birth) return interval.start <= birth.max && intervalEnd >= birth.min ? 'at_birth' : null;
  return null;
}

/** Lexicon place cells as written; "NA" and blanks are absence, not a place. */
export function lexiconPlace(value: string | null | undefined, relation: PlaceClaim['relation']): PlaceClaim | null {
  const text = (value ?? '').trim();
  if (!text || /^(na|n\/a|unknown)$/i.test(text)) return null;
  return { place: text, relation, basis: 'lexicon_uncited', location_id: null };
}

/** Basis of a curated history row (event or epoch) from its review state. */
export function historyBasis(row: { verification_status: string; publication_ready: boolean }): DatumBasis {
  if (row.verification_status === 'unverified_seed') return 'seed_unverified';
  if (row.verification_status === 'human_verified' || row.verification_status === 'source_verified') {
    return row.publication_ready ? 'reviewed_cited' : 'reviewed_unpublished';
  }
  return 'curated_unreviewed';
}

function basesOf(claims: DateClaim[], event: 'birth' | 'death'): string {
  const labels = [...new Set(claims.filter((claim) => claim.event === event && claim.usable).map((claim) => basisLabel(claim.basis)))];
  return labels.join('; ');
}

function displayName(transmitter: ChainTransmitter): string {
  return transmitter.name_en || transmitter.name_ar || transmitter.surface_ar;
}

/** Transmitters whose dates and generation may be compared: a verified link or one agreed candidate. */
export function isComparable(transmitter: ChainTransmitter): boolean {
  return transmitter.identity === 'verified' || transmitter.identity === 'single_candidate';
}

/**
 * The chronological-gap rule, for each pair of consecutive positions (teacher, then the student who heard from them):
 * (1) lifespans as recorded do not overlap: one's earliest recorded birth is after the other's latest recorded death;
 * (2) generations as recorded are not adjacent: the broad classes (Prophet, Companion, Follower, Follower of the
 * Followers, third century, fourth century or later) differ by more than one step, either way.
 * Only identified transmitters are compared, and only known bounds are used. Information, never a ruling.
 * `earliestFirst` is one chain's transmitters ordered teacher before student.
 */
export function chronologicalGaps(earliestFirst: ChainTransmitter[]): ChronologicalGap[] {
  const gaps: ChronologicalGap[] = [];
  for (let index = 0; index + 1 < earliestFirst.length; index++) {
    const teacher = earliestFirst[index];
    const student = earliestFirst[index + 1];
    if (teacher.position !== student.position + 1) continue;
    if (!isComparable(teacher) || !isComparable(student)) continue;
    const positions = { student_position: student.position, teacher_position: teacher.position };

    const studentBorn = student.lifespan.birth;
    const teacherDied = teacher.lifespan.death;
    const teacherBorn = teacher.lifespan.birth;
    const studentDied = student.lifespan.death;
    if (studentBorn && teacherDied && studentBorn.min > teacherDied.max) {
      gaps.push({
        kind: 'lifespans_do_not_overlap',
        ...positions,
        statement:
          `Lifespans as recorded do not overlap: ${displayName(student)} is recorded as born ${formatRange(studentBorn)} ` +
          `(${basesOf(student.lifespan.claims, 'birth')}), after ${displayName(teacher)}'s recorded death ${formatRange(teacherDied)} ` +
          `(${basesOf(teacher.lifespan.claims, 'death')}).`,
      });
    } else if (teacherBorn && studentDied && teacherBorn.min > studentDied.max) {
      gaps.push({
        kind: 'lifespans_do_not_overlap',
        ...positions,
        statement:
          `Lifespans as recorded do not overlap: ${displayName(teacher)} is recorded as born ${formatRange(teacherBorn)} ` +
          `(${basesOf(teacher.lifespan.claims, 'birth')}), after ${displayName(student)}'s recorded death ${formatRange(studentDied)} ` +
          `(${basesOf(student.lifespan.claims, 'death')}).`,
      });
    }

    const teacherGeneration = teacher.generation[0];
    const studentGeneration = student.generation[0];
    if (teacherGeneration && studentGeneration && Math.abs(studentGeneration.rank - teacherGeneration.rank) > 1) {
      gaps.push({
        kind: 'generations_not_adjacent',
        ...positions,
        statement:
          `Generations as recorded are not adjacent: ${displayName(student)} is recorded as ${GENERATION_LABELS[studentGeneration.class]} ` +
          `(${basisLabel(studentGeneration.basis)}), ${displayName(teacher)} as ${GENERATION_LABELS[teacherGeneration.class]} ` +
          `(${basisLabel(teacherGeneration.basis)}).`,
      });
    }
  }
  return gaps;
}

/** Smallest range holding every drawable year of the given lifespans; null when none is known. */
export function spanOfLifespans(lifespans: Array<Pick<Lifespan, 'birth' | 'death'>>): YearRange | null {
  const years = lifespans.flatMap((lifespan) => [lifespan.birth?.min, lifespan.birth?.max, lifespan.death?.min, lifespan.death?.max]);
  const known = years.filter((year): year is number => typeof year === 'number');
  return known.length === 0 ? null : { min: Math.min(...known), max: Math.max(...known) };
}
