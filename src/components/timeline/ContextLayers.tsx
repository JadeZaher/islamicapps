'use client';

import { useState } from 'react';
import type {
  EventEntry,
  ExternalTraditionParallelEntry,
  NarratorAffiliationEntry,
  NarratorResidenceEntry,
  PlaceSnapshotEntry,
  TimelineAudience,
  TimelineContextLayer,
} from '@/db/queries/timeline-contracts';
import { formatRange } from '@/db/queries/timeline-rules';
import { CitationLink } from './CitationLink';
import styles from './timeline.module.css';

export interface ContextLayersProps {
  audience: TimelineAudience;
  events: EventEntry[];
  residences?: NarratorResidenceEntry[];
  affiliations?: NarratorAffiliationEntry[];
  placeSnapshots?: PlaceSnapshotEntry[];
  parallels?: ExternalTraditionParallelEntry[];
  initialLayers?: TimelineContextLayer[];
}

export const CONTEXT_LAYERS: Array<{ id: TimelineContextLayer; label: string }> = [
  { id: 'political', label: 'Political' },
  { id: 'places', label: 'Places & Demographics' },
  { id: 'tech', label: 'Tech & Writing' },
  { id: 'parallels', label: "Parallels & Isra'iliyyat" },
  { id: 'social_gender_norms', label: 'Social & Gender Norms' },
  { id: 'myths_literature_art', label: 'Myths, Poetry & Art' },
  { id: 'food_agriculture_ecology', label: 'Food & Agriculture' },
  { id: 'economic_tensions', label: 'Economic Tensions' },
];

const POLITICAL_TRACK_CATEGORIES = new Set(['political', 'world_event', 'legal_theological', 'intellectual_movement']);
const DEMOGRAPHIC_TRACK_CATEGORIES = new Set(['demographic_shift', 'trade_pilgrimage']);
const MYTHS_PARALLELS_SOURCES = new Set([
  'ancient_near_eastern_myth',
  'arabian_folklore',
  'greco_roman',
  'poetry_adab',
  'pre_islamic_poetry',
]);

export function filterPoliticalEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => {
    if (event.track_category) return POLITICAL_TRACK_CATEGORIES.has(event.track_category);
    const cat = (event.category ?? '').toLowerCase();
    return cat === '' || cat.includes('politic') || cat.includes('battle') || cat.includes('fitna') || cat.includes('caliph') || cat.includes('world');
  });
}

export function filterTechEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => {
    if (event.track_category) return event.track_category === 'technological';
    const cat = (event.category ?? '').toLowerCase();
    return cat.includes('tech') || cat.includes('writing') || cat.includes('paper') || cat.includes('tadwin');
  });
}

export function filterDemographicEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => Boolean(event.track_category && DEMOGRAPHIC_TRACK_CATEGORIES.has(event.track_category)));
}

export function filterSocialGenderEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => event.track_category === 'social_gender_norms');
}

export function filterMythsLiteratureArtEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => event.track_category === 'myths_literature_art');
}

export function filterFoodAgricultureEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => event.track_category === 'food_agriculture_ecology');
}

export function filterEconomicTensionsEvents(events: EventEntry[]): EventEntry[] {
  return events.filter((event) => event.track_category === 'economic_tensions');
}

/** Formats Hijri years cleanly, adding approximate CE/BCE context for negative (pre-Hijri) years. */
export function formatContextYear(year: number): string {
  if (year === 0) return '0 (not a Hijri year)';
  if (year > 0) return `${year} AH`;
  const approxGregorian = Math.round(622 + year * 0.970224);
  const gregorianLabel = approxGregorian <= 0 ? `c. ${1 - approxGregorian} BCE` : `c. ${approxGregorian} CE`;
  return `${-year} BH (${gregorianLabel})`;
}

export function formatContextYearSpan(min: number | null, max: number | null): string {
  if (min !== null && max !== null) {
    if (min === max) return formatContextYear(min);
    if (min < 0 || max < 0) return `${formatContextYear(min)} – ${formatContextYear(max)}`;
    return formatRange({ min, max });
  }
  if (min !== null) return formatContextYear(min);
  if (max !== null) return formatContextYear(max);
  return 'Date unrecorded';
}

export function formatContextInterval(interval: Pick<EventEntry, 'start' | 'end'>): string {
  if (interval.end === null) return `from ${formatContextYear(interval.start)}`;
  return formatContextYearSpan(interval.start, interval.end);
}

function formatRole(value: string): string {
  return value.replace(/_/g, ' ');
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean).join(', ');
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${formatValue(v)}`)
      .join(', ');
  }
  return String(value);
}

function formatStructuredRecord(record: Record<string, unknown> | null | undefined): string | null {
  if (!record || typeof record !== 'object') return null;
  const entries = Object.entries(record).filter(([, v]) => {
    if (v === null || v === undefined) return false;
    if (Array.isArray(v)) return v.length > 0;
    return String(v).trim() !== '';
  });
  if (entries.length === 0) return null;
  return entries.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${formatValue(v)}`).join('; ');
}

function EventList({ events }: { events: EventEntry[] }) {
  return (
    <ul className={styles.list}>
      {events.map((event) => (
        <li key={event.id} className={styles.listItem}>
          <span className={styles.listYear}>{formatContextInterval(event)}</span>
          <div>
            <span>{event.name}</span>
            {event.location_name && <span className={styles.basis}> · {event.location_name}</span>}
            {event.citation && (
              <>
                {' · '}
                <CitationLink citation={event.citation} />
              </>
            )}
            {event.description && <p className={styles.itemDetail}>{event.description}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ContextLayers({
  audience,
  events,
  residences = [],
  affiliations = [],
  placeSnapshots = [],
  parallels = [],
  initialLayers = [],
}: ContextLayersProps) {
  const [active, setActive] = useState<Set<TimelineContextLayer>>(() => new Set(initialLayers));

  const politicalEvents = filterPoliticalEvents(events);
  const techEvents = filterTechEvents(events);
  const demographicEvents = filterDemographicEvents(events);
  const socialGenderEvents = filterSocialGenderEvents(events);
  const mythsEvents = filterMythsLiteratureArtEvents(events);
  const foodEvents = filterFoodAgricultureEvents(events);
  const economicEvents = filterEconomicTensionsEvents(events);

  const socialNormSnapshots = placeSnapshots.filter((snap) => formatStructuredRecord(snap.social_norms) !== null);
  const materialCultureSnapshots = placeSnapshots.filter((snap) => formatStructuredRecord(snap.material_culture) !== null);
  const mythsParallels = parallels.filter((item) => MYTHS_PARALLELS_SOURCES.has(item.tradition_source));

  const counts: Record<TimelineContextLayer, number> = {
    political: politicalEvents.length,
    places: residences.length + affiliations.length + placeSnapshots.length + demographicEvents.length,
    tech: techEvents.length,
    parallels: parallels.length,
    social_gender_norms: socialGenderEvents.length + socialNormSnapshots.length,
    myths_literature_art: mythsEvents.length + mythsParallels.length,
    food_agriculture_ecology: foodEvents.length + materialCultureSnapshots.length,
    economic_tensions: economicEvents.length,
  };

  function toggleLayer(layer: TimelineContextLayer) {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(layer)) next.delete(layer);
      else next.add(layer);
      return next;
    });
  }

  return (
    <div className={styles.layerSection}>
      <div className={styles.layerHeader}>
        <h3 className={styles.layerTitle}>Context layers</h3>
        <div className={styles.layerBar} role="group" aria-label="Context layers">
          {CONTEXT_LAYERS.map(({ id, label }) => {
            const isOn = active.has(id);
            const count = counts[id];
            return (
              <button
                key={id}
                type="button"
                aria-pressed={isOn}
                onClick={() => toggleLayer(id)}
                className={isOn ? `${styles.layerToggle} ${styles.layerToggleActive}` : styles.layerToggle}
              >
                <span>{label}</span>
                {count > 0 && <span className={styles.layerCount}>{count}</span>}
              </button>
            );
          })}
        </div>
      </div>

      {active.has('political') && (
        <div className={styles.layerPanel} data-layer="political">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Political &amp; world context</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {politicalEvents.length === 0 ? (
            <p className={styles.note}>No political or world events{audience === 'public' ? ' reviewed and cited' : ''} on this span.</p>
          ) : (
            <EventList events={politicalEvents} />
          )}
        </div>
      )}

      {active.has('places') && (
        <div className={styles.layerPanel} data-layer="places">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Places, residences &amp; demographics</span>
          </div>

          {residences.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Residences &amp; mobility</span>
                <span className={styles.layerAttested}>Attested</span>
              </div>
              <ul className={styles.list}>
                {residences.map((item) => (
                  <li key={item.id} className={styles.listItem}>
                    <span className={styles.listYear}>{formatContextYearSpan(item.year_min, item.year_max)}</span>
                    <div>
                      <span>{item.location_name ?? item.location_id}</span>
                      <span className={styles.basis}> · {formatRole(item.role)}</span>
                      {item.narrator_name && <span className={styles.basis}> · {item.narrator_name}</span>}
                      {item.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                      {item.citation && (
                        <>
                          {' · '}
                          <CitationLink citation={item.citation} />
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {affiliations.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Affiliations</span>
                <span className={styles.layerAttested}>Attested</span>
              </div>
              <ul className={styles.list}>
                {affiliations.map((item) => (
                  <li key={item.id} className={styles.listItem}>
                    <span className={styles.listYear}>{formatRole(item.kind)}</span>
                    <div>
                      <span>{item.label}</span>
                      {item.narrator_name && <span className={styles.basis}> · {item.narrator_name}</span>}
                      {item.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                      {item.citation && (
                        <>
                          {' · '}
                          <CitationLink citation={item.citation} />
                        </>
                      )}
                      {item.note && <p className={styles.itemDetail}>{item.note}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {placeSnapshots.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Place snapshots</span>
                <span className={styles.layerContextual}>Contextual</span>
              </div>
              <ul className={styles.list}>
                {placeSnapshots.map((snap) => {
                  const communities = formatStructuredRecord(snap.religious_communities);
                  const socialNorms = formatStructuredRecord(snap.social_norms);
                  const materialCulture = formatStructuredRecord(snap.material_culture);
                  return (
                    <li key={snap.id} className={styles.listItem}>
                      <span className={styles.listYear}>{formatContextYearSpan(snap.year_min, snap.year_max)}</span>
                      <div>
                        <span>{snap.location_name ?? snap.location_id}</span>
                        {snap.polity_or_ruler && <span className={styles.basis}> · {snap.polity_or_ruler}</span>}
                        {snap.dominant_schools.length > 0 && (
                          <span className={styles.basis}> · Schools: {snap.dominant_schools.join(', ')}</span>
                        )}
                        {snap.languages.length > 0 && (
                          <span className={styles.basis}> · Languages: {snap.languages.join(', ')}</span>
                        )}
                        {snap.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                        {snap.citation && (
                          <>
                            {' · '}
                            <CitationLink citation={snap.citation} />
                          </>
                        )}
                        {communities && <p className={styles.itemDetail}>Communities: {communities}</p>}
                        {socialNorms && <p className={styles.itemDetail}>Social norms: {socialNorms}</p>}
                        {materialCulture && <p className={styles.itemDetail}>Material culture: {materialCulture}</p>}
                        {snap.ethnographic_notes && <p className={styles.itemDetail}>{snap.ethnographic_notes}</p>}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {demographicEvents.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Demographic &amp; trade shifts</span>
                <span className={styles.layerContextual}>Contextual</span>
              </div>
              <EventList events={demographicEvents} />
            </div>
          )}

          {counts.places === 0 && (
            <p className={styles.note}>No residences, affiliations, or place snapshots{audience === 'public' ? ' reviewed and cited' : ''} for this span.</p>
          )}
        </div>
      )}

      {active.has('tech') && (
        <div className={styles.layerPanel} data-layer="tech">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Tech &amp; writing</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {techEvents.length === 0 ? (
            <p className={styles.note}>No writing or technological milestones{audience === 'public' ? ' reviewed and cited' : ''} on this span.</p>
          ) : (
            <EventList events={techEvents} />
          )}
        </div>
      )}

      {active.has('parallels') && (
        <div className={styles.layerPanel} data-layer="parallels">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Parallels &amp; Isra&apos;iliyyat</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {parallels.length === 0 ? (
            <p className={styles.note}>No cited external-tradition parallels{audience === 'public' ? ' reviewed and cited' : ''}.</p>
          ) : (
            <ul className={styles.list}>
              {parallels.map((item) => (
                <li key={item.id} className={styles.listItem}>
                  <span className={styles.listYear}>{formatRole(item.tradition_source)}</span>
                  <div>
                    <span>{item.source_work}</span>
                    {item.locator && <span className={styles.basis}> · {item.locator}</span>}
                    <span className={styles.basis}> · {formatRole(item.relation_type)}</span>
                    {item.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                    {item.citation && (
                      <>
                        {' · '}
                        <CitationLink citation={item.citation} />
                      </>
                    )}
                    {item.note && <p className={styles.itemDetail}>{item.note}</p>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {active.has('social_gender_norms') && (
        <div className={styles.layerPanel} data-layer="social_gender_norms">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Social &amp; gender norms</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {socialGenderEvents.length > 0 && <EventList events={socialGenderEvents} />}
          {socialNormSnapshots.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Place social norms</span>
                <span className={styles.layerContextual}>Contextual</span>
              </div>
              <ul className={styles.list}>
                {socialNormSnapshots.map((snap) => (
                  <li key={snap.id} className={styles.listItem}>
                    <span className={styles.listYear}>{formatContextYearSpan(snap.year_min, snap.year_max)}</span>
                    <div>
                      <span>{snap.location_name ?? snap.location_id}</span>
                      {snap.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                      {snap.citation && (
                        <>
                          {' · '}
                          <CitationLink citation={snap.citation} />
                        </>
                      )}
                      <p className={styles.itemDetail}>{formatStructuredRecord(snap.social_norms)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {counts.social_gender_norms === 0 && (
            <p className={styles.note}>No social or gender norms entries{audience === 'public' ? ' reviewed and cited' : ''} on this span.</p>
          )}
        </div>
      )}

      {active.has('myths_literature_art') && (
        <div className={styles.layerPanel} data-layer="myths_literature_art">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Myths, poetry &amp; art</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {mythsEvents.length > 0 && <EventList events={mythsEvents} />}
          {mythsParallels.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Literary &amp; mythological parallels</span>
                <span className={styles.layerContextual}>Contextual</span>
              </div>
              <ul className={styles.list}>
                {mythsParallels.map((item) => (
                  <li key={item.id} className={styles.listItem}>
                    <span className={styles.listYear}>{formatRole(item.tradition_source)}</span>
                    <div>
                      <span>{item.source_work}</span>
                      {item.locator && <span className={styles.basis}> · {item.locator}</span>}
                      <span className={styles.basis}> · {formatRole(item.relation_type)}</span>
                      {item.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                      {item.citation && (
                        <>
                          {' · '}
                          <CitationLink citation={item.citation} />
                        </>
                      )}
                      {item.note && <p className={styles.itemDetail}>{item.note}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {counts.myths_literature_art === 0 && (
            <p className={styles.note}>No myths, poetry, or art entries{audience === 'public' ? ' reviewed and cited' : ''} on this span.</p>
          )}
        </div>
      )}

      {active.has('food_agriculture_ecology') && (
        <div className={styles.layerPanel} data-layer="food_agriculture_ecology">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Food, agriculture &amp; ecology</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {foodEvents.length > 0 && <EventList events={foodEvents} />}
          {materialCultureSnapshots.length > 0 && (
            <div className={styles.layerSubgroup}>
              <div className={styles.layerPanelHeader}>
                <span className={styles.layerSubheading}>Material culture &amp; diet</span>
                <span className={styles.layerContextual}>Contextual</span>
              </div>
              <ul className={styles.list}>
                {materialCultureSnapshots.map((snap) => (
                  <li key={snap.id} className={styles.listItem}>
                    <span className={styles.listYear}>{formatContextYearSpan(snap.year_min, snap.year_max)}</span>
                    <div>
                      <span>{snap.location_name ?? snap.location_id}</span>
                      {snap.review_state === 'candidate_only' && <span className={styles.candidateTag}>candidate</span>}
                      {snap.citation && (
                        <>
                          {' · '}
                          <CitationLink citation={snap.citation} />
                        </>
                      )}
                      <p className={styles.itemDetail}>{formatStructuredRecord(snap.material_culture)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {counts.food_agriculture_ecology === 0 && (
            <p className={styles.note}>No food, agriculture, or ecology entries{audience === 'public' ? ' reviewed and cited' : ''} on this span.</p>
          )}
        </div>
      )}

      {active.has('economic_tensions') && (
        <div className={styles.layerPanel} data-layer="economic_tensions">
          <div className={styles.layerPanelHeader}>
            <span className={styles.layerPanelTitle}>Economic tensions &amp; material life</span>
            <span className={styles.layerContextual}>Contextual</span>
          </div>
          {economicEvents.length === 0 ? (
            <p className={styles.note}>No economic or material-life entries{audience === 'public' ? ' reviewed and cited' : ''} on this span.</p>
          ) : (
            <EventList events={economicEvents} />
          )}
        </div>
      )}
    </div>
  );
}
