/** Turns a rejected server action into one inline sentence: zod issues and curation refusals pass through, masked production errors fall back. */
export function describeActionError(error: unknown, fallback: string): string {
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
