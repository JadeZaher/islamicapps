'use client';

import { RouteError } from '@/components/RouteState';

/** Root route error boundary; never prints error.message (it can carry query text). */
export default function RootError(props: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteError {...props} />;
}
