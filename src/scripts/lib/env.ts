/**
 * Environment variable helpers for pipeline scripts.
 * Call loadEnv() at the top of each script before accessing any env vars.
 */
import dotenv from 'dotenv';
import path from 'path';

let loaded = false;

export function loadEnv(): void {
    if (loaded) return;
    // Try .env.local first (Next.js convention), then .env as fallback
    dotenv.config({ path: path.join(process.cwd(), '.env.local') });
    dotenv.config({ path: path.join(process.cwd(), '.env') });
    loaded = true;
}

export function getRequiredEnv(key: string): string {
    const value = process.env[key];
    if (!value) {
        throw new Error(
            `Missing required environment variable: ${key}\n` +
            `Add it to .env.local in the project root and try again.`
        );
    }
    return value;
}

export function getOptionalEnv(key: string): string | undefined {
    return process.env[key] || undefined;
}
