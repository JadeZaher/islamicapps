import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

interface EmptyStateProps {
  title: string;
  description?: string;
  /** One recovery action, e.g. a Button or Link. */
  action?: ReactNode;
  className?: string;
}

/** Single empty-state style: dashed panel, short title, optional action. */
export function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        'flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-700 px-6 py-12 text-center',
        className,
      )}
    >
      <p className="font-medium text-slate-200">{title}</p>
      {description && <p className="max-w-md text-sm text-slate-400">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
