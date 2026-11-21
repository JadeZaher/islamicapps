/** Public report addresses: `hadith:k6:10008` <-> `/hadith/k6/10008`. See src/lib/AGENTS.md §Report addresses. */

const ID_PREFIX = 'hadith:';
const ROUTE_PREFIX = '/hadith/';

/** Path segments after the namespace, per stable-ID namespace (datasets/hadith-data/AGENTS.md, Durable identity). */
const NAMESPACE_ARITY: Record<string, number> = {
  k6: 1,
  thaqalayn: 1,
  'pure-canon': 1,
  openiti: 2,
};

function splitKnownId(id: string): string[] | null {
  if (!id.startsWith(ID_PREFIX)) return null;
  const parts = id.slice(ID_PREFIX.length).split(':');
  const arity = NAMESPACE_ARITY[parts[0]];
  if (arity === undefined || parts.length !== arity + 1 || parts.some((part) => part === '')) return null;
  return parts;
}

/** The canonical public path of a report; unknown ID shapes fall back to one percent-encoded segment. */
export function hadithPath(id: string): string {
  const parts = splitKnownId(id);
  if (!parts) return `${ROUTE_PREFIX}${encodeURIComponent(id)}`;
  return ROUTE_PREFIX + parts.map(encodeURIComponent).join('/');
}

function decodeSegment(segment: string): string | null {
  try {
    return decodeURIComponent(segment);
  } catch {
    return null;
  }
}

/** Segments of `pathname` under /hadith/, still encoded; null outside it. */
function routeSegments(pathname: string): string[] | null {
  if (!pathname.startsWith(ROUTE_PREFIX)) return null;
  const segments = pathname.slice(ROUTE_PREFIX.length).split('/');
  return segments[0] ? segments : null;
}

export interface ParsedHadithPath {
  id: string;
  /** Anything after the report's own segments, e.g. `/chains`; empty for the report page. */
  rest: string;
}

/** Parses a canonical path (`/hadith/k6/10008[/sub]`) into the report ID; null for any other shape. */
export function parseHadithPath(pathname: string): ParsedHadithPath | null {
  const segments = routeSegments(pathname);
  if (!segments) return null;
  const namespace = decodeSegment(segments[0]);
  const arity = namespace === null ? undefined : NAMESPACE_ARITY[namespace];
  if (arity === undefined || segments.length < arity + 1) return null;
  const local = segments.slice(1, arity + 1).map(decodeSegment);
  if (local.some((part) => part === null || part === '' || part.includes(':') || part.includes('/'))) return null;
  const rest = segments.slice(arity + 1);
  return { id: `${ID_PREFIX}${namespace}:${local.join(':')}`, rest: rest.length ? `/${rest.join('/')}` : '' };
}

/** The canonical path for a legacy `/hadith/<percent-encoded id>[/sub]` address, or null when it is not one. */
export function canonicalForLegacyPath(pathname: string): string | null {
  const segments = routeSegments(pathname);
  if (!segments) return null;
  const id = decodeSegment(segments[0]);
  if (!id || !splitKnownId(id)) return null;
  const rest = segments.slice(1);
  return hadithPath(id) + (rest.length ? `/${rest.join('/')}` : '');
}

/** The internal route path the app serves a report from (one encoded `[id]` segment). */
export function internalHadithPath({ id, rest }: ParsedHadithPath): string {
  return `${ROUTE_PREFIX}${encodeURIComponent(id)}${rest}`;
}
