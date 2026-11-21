'use client';

import { RouteError } from '@/components/RouteState';

export default function NarratorError(props: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteError {...props} title="This narrator is temporarily unavailable" backHref="/narrator" backLabel="All narrators" />;
}
