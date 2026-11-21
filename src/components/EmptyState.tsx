import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title: string;
  description?: string;
  /** One recovery action, e.g. a Button or Link. */
  action?: ReactNode;
  className?: string;
}

/** Empty state (DESIGN.md §Empty, loading and error states): hairline above, a 20px title, one reason, one action. Flush left, no panel. */
export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div role="status" className={cn('flex flex-col items-start gap-2 border-t border-rule pt-3', className)}>
      <p className="type-h3 text-ink">{title}</p>
      {description && <p className="max-w-[var(--measure-reading)] type-small text-ink-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
