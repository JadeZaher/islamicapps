import Link from 'next/link';

import { RouteMessage, primaryActionClass } from '@/components/RouteState';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <RouteMessage title="Page not found" description="This address does not match any page in the archive.">
      <Button asChild className={primaryActionClass}>
        <Link href="/hadith">Browse hadith</Link>
      </Button>
    </RouteMessage>
  );
}
