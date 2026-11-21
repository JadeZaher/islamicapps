/**
 * The site's public origin, edge-safe (no server-only import). In production it is `SITE_URL` and nothing else: request
 * headers never decide an absolute URL there (host-header injection). See src/lib/AGENTS.md §Site origin.
 */

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]', '::1']);

/** True for a loopback host, with or without a port. */
export function isLoopbackHost(host: string): boolean {
  const hostname = host.startsWith('[') ? host.slice(0, host.indexOf(']') + 1) : host.split(':')[0];
  return LOOPBACK_HOSTS.has(hostname.toLowerCase()) || /^127\.\d+\.\d+\.\d+$/.test(hostname);
}

/** Why a `SITE_URL` value is unusable, or null: it must be an absolute https origin (http only on a loopback host). */
export function siteUrlProblem(value: string | undefined): string | null {
  const trimmed = value?.trim();
  if (!trimmed) return 'SITE_URL is not set; production needs the public origin, e.g. https://example.org.';
  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return 'SITE_URL is not an absolute URL.';
  }
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && isLoopbackHost(url.host))) {
    return 'SITE_URL must use https (http is accepted only for a loopback host).';
  }
  if (url.username || url.password || url.search || url.hash || url.pathname.replace(/\/+$/, '') !== '') {
    return 'SITE_URL must be an origin only (scheme and host, optional port), with no path, query or credentials.';
  }
  return null;
}

/** The validated `SITE_URL` origin, or null when unset or invalid. */
export function configuredSiteOrigin(): string | null {
  const value = process.env.SITE_URL;
  return siteUrlProblem(value) ? null : new URL(value!.trim()).origin;
}

function isProduction(): boolean {
  return process.env.NODE_ENV === 'production';
}

/**
 * The public origin. Production: `SITE_URL`, or a thrown error (start-up already refused). Elsewhere: `SITE_URL` when
 * set, else the request's host only when it is a loopback host, else `http://localhost:3000`.
 */
export function siteOriginFor(requestHost: string | null, requestProtocol: string | null): string {
  const configured = configuredSiteOrigin();
  if (configured) return configured;
  if (isProduction()) throw new Error(siteUrlProblem(process.env.SITE_URL) ?? 'SITE_URL is invalid.');
  if (requestHost && isLoopbackHost(requestHost)) return `${requestProtocol === 'https' ? 'https' : 'http'}://${requestHost}`;
  return 'http://localhost:3000';
}

/** An absolute URL on this site for a redirect `Location` (production: always `SITE_URL`). */
export function siteUrlFor(path: string, request: { nextUrl: { host: string; protocol: string } }): URL {
  return new URL(path, siteOriginFor(request.nextUrl.host, request.nextUrl.protocol.replace(/:$/, '')));
}
