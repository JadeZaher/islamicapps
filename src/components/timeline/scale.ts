/** Linear Hijri-year scale for the timeline geometry: domain, tick years, and positions in percent. */
import type { YearRange } from '@/db/queries/timeline-contracts';

export interface YearScale {
  min: number;
  max: number;
  ticks: number[];
  /** Position of a year as a percentage of the track, clamped to [0, 100]. */
  at(year: number): number;
}

const TICK_STEPS = [5, 10, 25, 50, 100, 200, 250, 500];

/** Pads the known range so bars never touch the edges; a single year gets a window of at least `minimumSpan`. */
export function buildScale(range: YearRange, minimumSpan = 40, targetTicks = 6): YearScale {
  const width = Math.max(range.max - range.min, minimumSpan);
  const padding = Math.max(Math.round(width * 0.06), 3);
  const centre = (range.min + range.max) / 2;
  const min = Math.floor(Math.min(range.min, centre - width / 2) - padding);
  const max = Math.ceil(Math.max(range.max, centre + width / 2) + padding);
  const step = TICK_STEPS.find((candidate) => (max - min) / candidate <= targetTicks) ?? 1000;
  const ticks: number[] = [];
  for (let year = Math.ceil(min / step) * step; year <= max; year += step) if (year !== 0) ticks.push(year);
  const span = max - min || 1;
  return { min, max, ticks, at: (year: number) => Math.min(100, Math.max(0, ((year - min) / span) * 100)) };
}

/** Clamped [left, width] in percent for an interval; `end` null runs to the right edge. */
export function placeInterval(scale: YearScale, start: number, end: number | null): { left: number; width: number } {
  const left = scale.at(start);
  const right = end === null ? 100 : scale.at(end);
  return { left, width: Math.max(right - left, 0.4) };
}

export function isVisible(scale: YearScale, start: number, end: number | null): boolean {
  return start <= scale.max && (end === null || end >= scale.min);
}
