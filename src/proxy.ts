/** Request gate (section 10.1): curator session on /admin and export, sign-in throttling, read rate limit, headers. */
import { NextResponse, type NextRequest } from 'next/server';
import { clientIp, consumeRead, isSignInBlocked } from '@/lib/auth/throttle';
import { throttledSignInResponse } from '@/lib/auth/throttled-response';
import { SESSION_COOKIE_NAME, verifyCuratorToken } from '@/lib/auth/session';

const SIGN_IN_ROUTE = '/api/auth/sign-in';
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

function tooManyRequests(retryAfterSeconds: number): NextResponse {
  return withSecurityHeaders(
    new NextResponse('Too many requests. Try again later.', {
      status: 429,
      headers: { 'Retry-After': String(retryAfterSeconds), 'Content-Type': 'text/plain; charset=utf-8' },
    }),
    true,
  );
}

export async function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const ip = clientIp(request.headers);
  const method = request.method.toUpperCase();

  // Early answer for a blocked address; the sign-in route reserves the attempt itself (browsers land on /sign-in?error=throttled).
  if (pathname === SIGN_IN_ROUTE && method === 'POST' && isSignInBlocked(ip)) {
    return withSecurityHeaders(throttledSignInResponse(request), true);
  }

  const session = await verifyCuratorToken(request.cookies.get(SESSION_COOKIE_NAME)?.value);
  const admin = isAdminPath(pathname);

  if ((admin || pathname.startsWith('/api/export')) && !session) {
    if (admin && (method === 'GET' || method === 'HEAD')) {
      const signIn = new URL('/sign-in', request.url);
      signIn.searchParams.set('next', pathname + request.nextUrl.search);
      return withSecurityHeaders(NextResponse.redirect(signIn, 303), true);
    }
    // POSTs to /admin (server actions from admin pages) and export requests are refused outright.
    return withSecurityHeaders(new NextResponse('Sign in as a curator.', { status: 401 }), true);
  }

  // Anonymous read rate limit: server-action POSTs and search page requests (30 a minute per IP).
  const isActionPost = method === 'POST' && request.headers.has('next-action');
  const isSearch = (method === 'GET' || method === 'HEAD') && SEARCH_PAGES.has(pathname) && searchParams.has('q');
  if (!session && (isActionPost || isSearch) && !consumeRead(ip)) return tooManyRequests(60);

  return withSecurityHeaders(NextResponse.next(), admin || pathname === '/sign-in');
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
