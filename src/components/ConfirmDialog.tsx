'use client';

import { cloneElement, useId, useRef, useState, type MouseEvent, type ReactElement } from 'react';

import { Button } from '@/components/ui/button';

interface ConfirmDialogProps {
  /** Clickable element (usually a Button) that opens the dialog. */
  trigger: ReactElement<{ onClick?: (event: MouseEvent) => void }>;
  title: string;
  description?: string;
  confirmLabel?: string;
  /** Destructive styling on the confirm button; defaults to true. */
  destructive?: boolean;
  /** May be async; the dialog closes on success and shows an inline error on failure. */
  onConfirm: () => void | Promise<void>;
}

/** Modal confirmation on the native <dialog> element: focus trap, Esc and backdrop dismissal included. */
export function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel = 'Delete',
  destructive = true,
  onConfirm,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [isPending, setIsPending] = useState(false);
  const [failed, setFailed] = useState(false);

  const open = () => {
    setFailed(false);
    dialogRef.current?.showModal();
  };
  const close = () => dialogRef.current?.close();

  const confirm = async () => {
    setIsPending(true);
    setFailed(false);
    try {
      await onConfirm();
      close();
    } catch {
      setFailed(true);
    } finally {
      setIsPending(false);
    }
  };

  return (
    <>
      {cloneElement(trigger, {
        onClick: (event: MouseEvent) => {
          trigger.props.onClick?.(event);
          open();
        },
      })}
      <dialog
        ref={dialogRef}
        aria-labelledby={titleId}
        onCancel={(event) => {
          if (isPending) event.preventDefault();
        }}
        onClick={(event) => {
          if (event.target === dialogRef.current && !isPending) close();
        }}
        className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-0 text-slate-100 backdrop:bg-black/60"
      >
        <div className="space-y-4 p-6">
          <h2 id={titleId} className="text-base font-semibold">
            {title}
          </h2>
          {description && <p className="text-sm text-slate-400">{description}</p>}
          {failed && (
            <p role="alert" className="text-sm text-red-400">
              Couldn&apos;t complete that. Try again.
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={close} disabled={isPending} autoFocus>
              Cancel
            </Button>
            <Button
              type="button"
              variant={destructive ? 'destructive' : 'default'}
              onClick={confirm}
              disabled={isPending}
            >
              {isPending ? 'Working...' : confirmLabel}
            </Button>
          </div>
        </div>
      </dialog>
    </>
  );
}
