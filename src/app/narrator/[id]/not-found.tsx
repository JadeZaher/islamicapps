import Link from 'next/link';

import { RouteMessage, primaryActionClass } from '@/components/RouteState';
import { Button } from '@/components/ui/button';

export default function NarratorNotFound() {
  return (
    <RouteMessage title="Narrator not found" description="No narrator in the archive has this identifier.">
      <Button asChild className={primaryActionClass}>
        <Link href="/narrator">Browse narrators</Link>
      </Button>
    </RouteMessage>
  );
}
