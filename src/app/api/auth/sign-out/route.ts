/** Curator sign-out: clears the session cookie. */
import { NextResponse, type NextRequest } from 'next/server';
import { SESSION_COOKIE_NAME } from '@/lib/auth/session';
import { siteUrlFor } from '@/lib/site-origin';
import { authEnabled } from '@/lib/auth/switches';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  if (!authEnabled()) return new NextResponse('Not found', { status: 404 });
  const response = NextResponse.redirect(siteUrlFor('/', request), 303);
  response.cookies.set(SESSION_COOKIE_NAME, '', { httpOnly: true, secure: true, sameSite: 'strict', path: '/', maxAge: 0 });
  return response;
}
