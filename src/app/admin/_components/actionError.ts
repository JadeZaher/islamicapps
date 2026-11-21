import type { ActionResult } from '@/app/actions/curation/result';

/** An expected refusal returned by a curation action (validation, publish gate, not found, load in progress, not signed in). */
export class ActionRefusal extends Error {
    constructor(
        message: string,
        readonly fieldErrors?: Record<string, string[]>,
    ) {
        super(message);
        this.name = 'ActionRefusal';
    }
}

/** Awaits a curation action's result: returns `data`, or throws an ActionRefusal carrying the real message (survives production masking). */
export async function unwrapAction<T>(pending: Promise<ActionResult<T>>): Promise<T> {
    const result = await pending;
    if (!result.ok) throw new ActionRefusal(result.message, result.fieldErrors);
    return result.data;
}

/** Turns a failed action into one inline sentence: refusals show their real message; only unexpected (masked) failures use the fallback. */
export function describeActionError(error: unknown, fallback: string): string {
    if (error instanceof ActionRefusal) return error.message;
    const raw = error instanceof Error ? error.message : '';
    if (!raw) return fallback;
    try {
        const issues: unknown = JSON.parse(raw);
        if (Array.isArray(issues)) {
            const messages = issues
                .map((issue) => {
                    const { message, path } = issue as { message?: string; path?: unknown[] };
                    if (!message) return null;
                    const field = Array.isArray(path) && path.length > 0 ? String(path[path.length - 1]).replace(/_/g, ' ') : '';
                    return field ? `${field}: ${message}` : message;
                })
                .filter((message): message is string => Boolean(message));
            if (messages.length > 0) return messages.join(' ');
        }
    } catch {
        // Not JSON: a plain message.
    }
    // Next masks thrown server-action errors in production behind a generic digest message.
    if (/Server Components render|digest/i.test(raw)) return fallback;
    return raw;
}
