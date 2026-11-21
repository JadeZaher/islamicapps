'use client';

import { RouteError } from '@/components/RouteState';

export default function AdminComparativeError(props: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteError {...props} title="Comparative studies are temporarily unavailable" backHref="/admin" backLabel="Admin home" />;
}
