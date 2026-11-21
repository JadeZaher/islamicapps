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
                className="border-red-600/30 text-red-400 hover:bg-red-500/10"
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
            className="max-w-xs rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm"
        >
            <p className="text-red-200">{consequence}</p>
            {errorMessage && (
                <p role="alert" className="mt-2 text-red-300">{errorMessage}</p>
            )}
            <div className="mt-3 flex justify-end gap-2">
                <Button
                    ref={cancelButtonRef}
                    size="sm"
                    variant="outline"
                    onClick={cancel}
                    disabled={isDeleting}
                    className="border-slate-600 text-slate-300"
                >
                    Cancel
                </Button>
                <Button
                    size="sm"
                    onClick={confirm}
                    disabled={isDeleting}
                    className="bg-red-600 text-white hover:bg-red-700"
                >
                    {isDeleting ? 'Retiring...' : `Retire ${itemName}`}
                </Button>
            </div>
        </div>
    );
}
