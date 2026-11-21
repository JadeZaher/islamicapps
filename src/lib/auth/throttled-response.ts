/** The answer to a blocked sign-in: browser form posts land on the sign-in page's throttled state, other callers get 429. */
import { NextResponse, type NextRequest } from 'next/server';

export const SIGN_IN_RETRY_AFTER_SECONDS = 15 * 60;

export function throttledSignInResponse(request: NextRequest): NextResponse {
  const wantsPage = request.headers.get('accept')?.includes('text/html') ?? false;
  const response = wantsPage
    ? NextResponse.redirect(new URL('/sign-in?error=throttled', request.url), 303)
    : new NextResponse('Too many sign-in attempts. Try again later.', {
        status: 429,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
  response.headers.set('Retry-After', String(SIGN_IN_RETRY_AFTER_SECONDS));
  return response;
}
