import neo4j, { Driver, Session } from 'neo4j-driver';

let driver: Driver | null = null;

export function getDriver(): Driver {
    if (!driver) {
        const uri = process.env.NEO4J_URL || 'switchyard.proxy.rlwy.net:52091';
        const username = process.env.NEO4J_USERNAME || 'neo4j';
        const password = process.env.NEO4J_PASSWORD || 'qa67yaimttxev1lzgfqxeybsryh0wlnf';

        // Railway proxy uses bolt:// protocol with custom port
        let fullUri: string;
        if (uri.startsWith('bolt://') || uri.startsWith('neo4j://') || uri.startsWith('neo4j+s://')) {
            fullUri = uri;
        } else {
            // If URI contains port, use it as-is with bolt://
            fullUri = uri.includes(':') ? `bolt://${uri}` : `bolt://${uri}:7687`;
        }

        console.log('🔌 Connecting to Neo4j:', fullUri.replace(password, '***'));

        driver = neo4j.driver(fullUri, neo4j.auth.basic(username, password), {
            maxConnectionPoolSize: 50,
            connectionAcquisitionTimeout: 2 * 60 * 1000, // 2 minutes
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
        return result.records.map((record) => record.toObject() as T);
    } finally {
        await session.close();
    }
}

export async function runWrite<T = any>(
    query: string,
    params: Record<string, any> = {}
): Promise<T[]> {
    const driver = getDriver();
    const session: Session = driver.session();
    try {
        const result = await session.executeWrite((tx) => tx.run(query, params));
        return result.records.map((record) => record.toObject() as T);
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
