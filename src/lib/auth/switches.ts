/**
 * Deployment switches, resolved in one place: AUTH_ENABLED (curator sign-in and admin) and PRIVATE_PREVIEW.
 * Edge-safe (no server-only); used by src/proxy.ts, route handlers, requireCurator and server components.
 * See src/lib/auth/AGENTS.md §Switches.
 */
import { configuredCuratorNames, sessionSecret } from './session';

/** PRIVATE_PREVIEW=1 only; anything else leaves the site public. */
export function privatePreviewEnabled(environment: Readonly<Record<string, string | undefined>> = process.env): boolean {
  return environment.PRIVATE_PREVIEW === '1';
}

/** Curator auth is on with AUTH_ENABLED=1, and always under private preview (which needs a session). Default off. */
export function authEnabled(environment: Readonly<Record<string, string | undefined>> = process.env): boolean {
  return environment.AUTH_ENABLED === '1' || privatePreviewEnabled(environment);
}

/** Why private preview cannot run safely, or null. Fail closed: the server refuses to start and the proxy answers 503. */
export function previewConfigurationProblem(environment: Readonly<Record<string, string | undefined>> = process.env): string | null {
  if (!privatePreviewEnabled(environment)) return null;
  if (!sessionSecret(environment)) return 'PRIVATE_PREVIEW=1 needs ADMIN_SESSION_SECRET (at least 32 characters).';
  if (configuredCuratorNames(environment).size === 0) return 'PRIVATE_PREVIEW=1 needs at least one curator in CURATOR_PASSPHRASES.';
  return null;
}

/** The curator surfaces that do not exist while auth is off: they answer 404. */
export function isAuthSurface(pathname: string): boolean {
  return (
    pathname === '/sign-in' ||
    pathname === '/admin' ||
    pathname.startsWith('/admin/') ||
    pathname.startsWith('/api/auth/') ||
    pathname === '/api/export' ||
    pathname.startsWith('/api/export/')
  );
}

/** Paths reachable without a session under private preview: sign-in, sign-out, health, robots. */
const PREVIEW_OPEN_PATHS = new Set(['/sign-in', '/api/auth/sign-in', '/api/auth/sign-out', '/api/health', '/robots.txt']);
/** Top-level files from public/ (static assets); `_next/*` and favicon never reach the proxy (matcher). */
const PUBLIC_ASSET = /^\/[A-Za-z0-9._-]+\.(?:svg|png|ico|webmanifest)$/;

export function isPreviewOpenPath(pathname: string): boolean {
  return PREVIEW_OPEN_PATHS.has(pathname) || PUBLIC_ASSET.test(pathname);
}

/**
 * A safe post-sign-in target: a same-site path. Admin paths always; under private preview any site path, since
 * every page needs the session. Rejects scheme-relative (`//`), backslash and whitespace tricks.
 */
export function safeReturnPath(next: string | undefined, preview = privatePreviewEnabled()): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || /[\s\\]/.test(next)) return '/admin';
  if (/^\/admin(\/|\?|$)/.test(next)) return next;
  return preview ? next : '/admin';
}
