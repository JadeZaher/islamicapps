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
import { formatInterval, formatRange } from '@/db/queries/timeline-rules';
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
];

const POLITICAL_TRACK_CATEGORIES = new Set(['political', 'world_event', 'legal_theological', 'intellectual_movement']);
const DEMOGRAPHIC_TRACK_CATEGORIES = new Set(['demographic_shift', 'trade_pilgrimage']);

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

function formatYearSpan(min: number | null, max: number | null): string {
  if (min !== null && max !== null) return formatRange({ min, max });
  if (min !== null) return formatRange({ min, max: min });
  if (max !== null) return formatRange({ min: max, max });
  return 'Date unrecorded';
}

function formatRole(value: string): string {
  return value.replace(/_/g, ' ');
}

function formatCommunities(communities: Record<string, unknown>): string | null {
  const entries = Object.entries(communities).filter(([, v]) => v !== null && v !== undefined && String(v).trim() !== '');
  if (entries.length === 0) return null;
  return entries.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${String(v)}`).join('; ');
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

  const counts: Record<TimelineContextLayer, number> = {
    political: politicalEvents.length,
    places: residences.length + affiliations.length + placeSnapshots.length + demographicEvents.length,
    tech: techEvents.length,
    parallels: parallels.length,
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
            <ul className={styles.list}>
              {politicalEvents.map((event) => (
                <li key={event.id} className={styles.listItem}>
                  <span className={styles.listYear}>{formatInterval(event)}</span>
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
                    <span className={styles.listYear}>{formatYearSpan(item.year_min, item.year_max)}</span>
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
                  const communities = formatCommunities(snap.religious_communities);
                  return (
                    <li key={snap.id} className={styles.listItem}>
                      <span className={styles.listYear}>{formatYearSpan(snap.year_min, snap.year_max)}</span>
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
              <ul className={styles.list}>
                {demographicEvents.map((event) => (
                  <li key={event.id} className={styles.listItem}>
                    <span className={styles.listYear}>{formatInterval(event)}</span>
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
            <ul className={styles.list}>
              {techEvents.map((event) => (
                <li key={event.id} className={styles.listItem}>
                  <span className={styles.listYear}>{formatInterval(event)}</span>
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
    </div>
  );
}
