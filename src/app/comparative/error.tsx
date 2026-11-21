'use client';

import { RouteError } from '@/components/RouteState';

export default function ComparativeError(props: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteError {...props} title="Comparative studies are temporarily unavailable" />;
}
