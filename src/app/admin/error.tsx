'use client';

import { RouteError } from '@/components/RouteState';

export default function AdminError(props: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteError {...props} backHref="/admin" backLabel="Admin home" />;
}
