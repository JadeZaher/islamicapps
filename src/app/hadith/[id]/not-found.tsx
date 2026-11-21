import Link from 'next/link';

import { RouteMessage, primaryActionClass } from '@/components/RouteState';
import { Button } from '@/components/ui/button';

export default function HadithNotFound() {
  return (
    <RouteMessage title="Hadith not found" description="No hadith in the archive has this identifier.">
      <Button asChild className={primaryActionClass}>
        <Link href="/hadith">Browse hadith</Link>
      </Button>
    </RouteMessage>
  );
}
