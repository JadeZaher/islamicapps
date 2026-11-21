'use client';

import { useEffect, useRef, useState } from 'react';
import { Archive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { describeActionError } from './actionError';

interface ConfirmDeleteProps {
    /** Singular noun used in labels, e.g. "event". */
    itemName: string;
    /** Consequence shown before the user confirms. */
    consequence: string;
    /** Retires the item; throw to surface a failure. */
    onConfirm: () => Promise<void>;
}

/** Two-step inline retire (nothing is erased): trigger button, then a consequence message with Retire / Cancel. */
export function ConfirmDelete({ itemName, consequence, onConfirm }: ConfirmDeleteProps) {
    const [isConfirming, setIsConfirming] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const cancelButtonRef = useRef<HTMLButtonElement>(null);
    const triggerButtonRef = useRef<HTMLButtonElement>(null);

    useEffect(() => {
        if (isConfirming) cancelButtonRef.current?.focus();
    }, [isConfirming]);

    const cancel = () => {
        setIsConfirming(false);
        setErrorMessage(null);
        requestAnimationFrame(() => triggerButtonRef.current?.focus());
    };

    const confirm = async () => {
        setIsDeleting(true);
        setErrorMessage(null);
        try {
            await onConfirm();
            setIsConfirming(false);
        } catch (error) {
            setErrorMessage(describeActionError(error, `Could not retire this ${itemName}. Try again.`));
        } finally {
            setIsDeleting(false);
        }
    };

    if (!isConfirming) {
        return (
            <Button
                ref={triggerButtonRef}
                size="sm"
                variant="outline"
                onClick={() => setIsConfirming(true)}
                aria-label={`Retire ${itemName}`}
                className="border-danger text-danger hover:bg-transparent"
            >
                <Archive className="w-4 h-4" aria-hidden="true" />
            </Button>
        );
    }

    return (
        <div
            role="alertdialog"
            aria-label={`Confirm retiring ${itemName}`}
            onKeyDown={(event) => {
                if (event.key === 'Escape' && !isDeleting) cancel();
            }}
            className="max-w-xs border border-danger bg-transparent p-3 text-sm"
        >
            <p className="text-danger">{consequence}</p>
            {errorMessage && (
                <p role="alert" className="mt-2 text-danger">{errorMessage}</p>
            )}
            <div className="mt-3 flex justify-end gap-2">
                <Button
                    ref={cancelButtonRef}
                    size="sm"
                    variant="outline"
                    onClick={cancel}
                    disabled={isDeleting}
                    className="border-rule text-ink"
                >
                    Cancel
                </Button>
                <Button
                    size="sm"
                    onClick={confirm}
                    disabled={isDeleting}
                    className="bg-danger text-paper border-danger hover:bg-ink hover:border-ink"
                >
                    {isDeleting ? 'Retiring...' : `Retire ${itemName}`}
                </Button>
            </div>
        </div>
    );
}
