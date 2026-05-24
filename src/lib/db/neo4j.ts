import neo4j, { Driver, Session, Integer, DateTime, isInt, isDateTime, isDate } from 'neo4j-driver';

/**
 * Recursively convert Neo4j types (Integer, DateTime, Node, Relationship, etc.)
 * to plain JS values safe for React Client Components.
 *
 * Neo4j Node/Relationship objects have class prototypes that Next.js rejects.
 * We preserve the `.properties` wrapper structure (action files use it) but
 * rebuild it as a plain object.
 */
function toPlainValue(value: unknown): unknown {
    if (value === null || value === undefined) return value;
    if (isInt(value)) {
        const int = value as Integer;
        return int.inSafeRange() ? int.toNumber() : int.toString();
    }
    if (isDateTime(value)) return (value as DateTime).toString();
    if (isDate(value)) return (value as unknown as { toString(): string }).toString();
    if (Array.isArray(value)) return value.map(toPlainValue);
    if (typeof value === 'object') {
        const obj = value as Record<string, unknown>;
        // Neo4j Node/Relationship: rebuild as plain object with serialized .properties
        if ('properties' in obj && typeof obj.properties === 'object' && obj.properties !== null) {
            const plain: Record<string, unknown> = {};
            // Copy non-properties fields (labels, identity, etc.) as plain values
            for (const [k, v] of Object.entries(obj)) {
                if (k === 'properties') {
                    plain.properties = toPlainObject(v as Record<string, unknown>);
                } else {
                    plain[k] = toPlainValue(v);
                }
            }
            return plain;
        }
        return toPlainObject(obj);
    }
    return value;
}

function toPlainObject(obj: Record<string, unknown>): Record<string, unknown> {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(obj)) {
        out[k] = toPlainValue(v);
    }
    return out;
}

let driver: Driver | null = null;

export function getDriver(): Driver {
    if (!driver) {
        const uri = process.env.NEO4J_URL;
        const username = process.env.NEO4J_USERNAME;
        const password = process.env.NEO4J_PASSWORD;
        if (!uri || !username || !password) {
            throw new Error('Missing required environment variables: NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD');
        }

        // Railway proxy uses bolt:// protocol with custom port
        let fullUri: string;
        if (uri.startsWith('bolt://') || uri.startsWith('neo4j://') || uri.startsWith('neo4j+s://')) {
            fullUri = uri;
        } else {
            // If URI contains port, use it as-is with bolt://
            fullUri = uri.includes(':') ? `bolt://${uri}` : `bolt://${uri}:7687`;
        }

        if (process.env.NODE_ENV === 'development') {
            console.log('🔌 Connecting to Neo4j:', fullUri.replace(password, '***'));
        }

        driver = neo4j.driver(fullUri, neo4j.auth.basic(username, password), {
            maxConnectionPoolSize: 50,
            connectionAcquisitionTimeout: 10_000, // 10 seconds
            connectionTimeout: 10_000, // 10 seconds
        });
    }
    return driver;
}

export async function closeDriver(): Promise<void> {
    if (driver) {
        await driver.close();
        driver = null;
    }
}

export async function runQuery<T = any>(
    query: string,
    params: Record<string, any> = {}
): Promise<T[]> {
    const driver = getDriver();
    const session: Session = driver.session();
    try {
        const result = await session.run(query, params);
        return result.records.map((record) => JSON.parse(JSON.stringify(toPlainValue(record.toObject()))) as T);
    } finally {
        await session.close();
    }
}

// 30s per-tx timeout so a stuck connection surfaces as a TransientError
// instead of hanging the whole script. Long-running batches should be
// chunked at the caller.
const WRITE_TX_TIMEOUT_MS = 30_000;

export async function runWrite<T = any>(
    query: string,
    params: Record<string, any> = {}
): Promise<T[]> {
    const driver = getDriver();
    const session: Session = driver.session();
    try {
        const result = await session.executeWrite(
            (tx) => tx.run(query, params),
            { timeout: WRITE_TX_TIMEOUT_MS },
        );
        return result.records.map((record) => JSON.parse(JSON.stringify(toPlainValue(record.toObject()))) as T);
    } finally {
        await session.close();
    }
}

// Helper to execute multiple queries in a transaction
export async function runTransaction(
    queries: Array<{ query: string; params?: Record<string, any> }>
): Promise<void> {
    const driver = getDriver();
    const session: Session = driver.session();
    try {
        await session.executeWrite(async (tx) => {
            for (const { query, params = {} } of queries) {
                await tx.run(query, params);
            }
        });
    } finally {
        await session.close();
    }
}
