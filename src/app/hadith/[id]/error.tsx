'use client';

import { RouteError } from '@/components/RouteState';

export default function HadithError(props: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteError {...props} title="This hadith is temporarily unavailable" backHref="/hadith" backLabel="All hadith" />;
}
