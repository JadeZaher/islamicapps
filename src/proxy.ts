/**
 * Request gate (section 10.1): auth switch, private preview, curator session on /admin and export, sign-in
 * throttling, read rate limit, report addresses, headers. See src/lib/auth/AGENTS.md §Switches.
 */
import { NextResponse, type NextRequest } from 'next/server';
import { canonicalForLegacyPath, internalHadithPath, parseHadithPath } from '@/lib/hadith-address';
import { clientIp, consumeRead, isSignInBlocked } from '@/lib/auth/throttle';
import { throttledSignInResponse } from '@/lib/auth/throttled-response';
import { SESSION_COOKIE_NAME, verifyCuratorToken } from '@/lib/auth/session';
import {
  authEnabled,
  isAuthSurface,
  isPreviewOpenPath,
  previewConfigurationProblem,
  privatePreviewEnabled,
} from '@/lib/auth/switches';

const SIGN_IN_ROUTE = '/api/auth/sign-in';
/** Marks a request this proxy rewrote to the internal report route; Next runs the proxy again on it. */
const REWRITTEN_HEADER = 'x-archive-report-rewrite';
const SEARCH_PAGES = new Set(['/hadith', '/narrator']);

function isAdminPath(pathname: string): boolean {
  return pathname === '/admin' || pathname.startsWith('/admin/');
}

function withSecurityHeaders(response: NextResponse, noIndex: boolean): NextResponse {
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  if (noIndex) response.headers.set('X-Robots-Tag', 'noindex, nofollow');
  return response;
}

function plain(body: string, status: number, extra: Record<string, string> = {}): NextResponse {
  return new NextResponse(body, { status, headers: { 'Content-Type': 'text/plain; charset=utf-8', ...extra } });
}

export async function proxy(request: NextRequest) {
  const { pathname, searchParams, search } = request.nextUrl;
  const ip = clientIp(request.headers);
  const method = request.method.toUpperCase();
  const preview = privatePreviewEnabled();
  const auth = authEnabled();

  // Fail closed: private preview without a working sign-in would otherwise lock everyone out or worse.
  if (preview && previewConfigurationProblem()) return withSecurityHeaders(plain('Service unavailable.', 503), true);

  // With auth off the curator surfaces do not exist, and the session code is never reached.
  if (!auth && isAuthSurface(pathname)) return withSecurityHeaders(plain('Not found.', 404), true);

  // Legacy report address (/hadith/<percent-encoded id>) -> the canonical path, permanently.
  // Not for our own rewrite: its internal path has the legacy shape, so redirecting it would loop.
  const canonical = request.headers.has(REWRITTEN_HEADER) ? null : canonicalForLegacyPath(pathname);
  if (canonical && (method === 'GET' || method === 'HEAD')) {
    return withSecurityHeaders(NextResponse.redirect(new URL(canonical + search, request.url), 308), preview);
  }

  // Early answer for a blocked address; the sign-in route reserves the attempt itself (browsers land on /sign-in?error=throttled).
  if (auth && pathname === SIGN_IN_ROUTE && method === 'POST' && isSignInBlocked(ip)) {
    return withSecurityHeaders(throttledSignInResponse(request), true);
  }

  const session = auth ? await verifyCuratorToken(request.cookies.get(SESSION_COOKIE_NAME)?.value) : null;
  const admin = isAdminPath(pathname);

  // Private preview: nothing is published; every route but sign-in, health, robots and assets needs a curator.
  const previewGated = preview && !isPreviewOpenPath(pathname);
  if ((admin || pathname.startsWith('/api/export') || previewGated) && !session) {
    if ((admin || previewGated) && (method === 'GET' || method === 'HEAD')) {
      const signIn = new URL('/sign-in', request.url);
      signIn.searchParams.set('next', pathname + search);
      return withSecurityHeaders(NextResponse.redirect(signIn, 303), true);
    }
    // POSTs (server actions) and export requests are refused outright.
    return withSecurityHeaders(plain('Sign in as a curator.', 401), true);
  }

  // Anonymous read rate limit: server-action POSTs and search page requests (30 a minute per IP).
  const isActionPost = method === 'POST' && request.headers.has('next-action');
  const isSearch = (method === 'GET' || method === 'HEAD') && SEARCH_PAGES.has(pathname) && searchParams.has('q');
  if (!session && (isActionPost || isSearch) && !consumeRead(ip)) {
    return withSecurityHeaders(plain('Too many requests. Try again later.', 429, { 'Retry-After': '60' }), true);
  }

  const noIndex = preview || admin || pathname === '/sign-in';
  // Canonical report address (/hadith/k6/10008) -> the [id] route, served without a redirect.
  const report = parseHadithPath(pathname);
  if (report) {
    const headers = new Headers(request.headers);
    headers.set(REWRITTEN_HEADER, '1');
    return withSecurityHeaders(
      NextResponse.rewrite(new URL(internalHadithPath(report) + search, request.url), { request: { headers } }),
      noIndex,
    );
  }
  return withSecurityHeaders(NextResponse.next(), noIndex);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
