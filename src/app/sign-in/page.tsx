import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { authEnabled } from '@/lib/auth/switches';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = { title: 'Curator sign-in', robots: { index: false, follow: false } };

interface PageProps {
  searchParams: Promise<{ error?: string; next?: string }>;
}


/** Inline message per failure; `throttled` is the state after repeated failures (the route may answer 429 directly). */
function errorMessage(error: string | undefined): string | null {
  if (!error) return null;
  if (error === 'throttled') return 'Too many attempts. Wait fifteen minutes, then try again.';
  return 'That name and passphrase did not match.';
}

/** Named-curator sign-in. A plain form posting to the sign-in route, so it works without JavaScript. */
export default async function SignInPage({ searchParams }: PageProps) {
  if (!authEnabled()) notFound();
  const { error, next } = await searchParams;
  const message = errorMessage(error);
  return (
    <main className="wrap pb-12 pt-12">
      <div className="max-w-sm">
      <h1 className="type-h1 border-b-2 border-rule-strong pb-5">Curator sign-in</h1>
      <form method="post" action="/api/auth/sign-in" className="mt-8 space-y-5">
        <input type="hidden" name="next" value={next ?? '/admin'} />
        <div className="space-y-2">
          <Label htmlFor="name" className="text-ink">
            Name
          </Label>
          <Input
            id="name"
            name="name"
            autoComplete="username"
            required
            aria-invalid={message ? true : undefined}
            aria-describedby={message ? 'sign-in-error' : undefined}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="passphrase" className="text-ink">
            Passphrase
          </Label>
          <Input
            id="passphrase"
            name="passphrase"
            type="password"
            autoComplete="current-password"
            required
            aria-invalid={message ? true : undefined}
            aria-describedby={message ? 'sign-in-error' : undefined}
          />
        </div>
        {message && (
          <p id="sign-in-error" role="alert" className="text-sm text-danger">
            {message}
          </p>
        )}
        <Button type="submit" className="w-full">
          Sign in
        </Button>
      </form>
      </div>
    </main>
  );
}
