import { loadEnv } from '../lib/env';

loadEnv();

export const DISPOSABLE_NEO4J_TEST_ACK =
  'I_ACKNOWLEDGE_THIS_IS_A_DISPOSABLE_NEO4J_TEST_DATABASE';

export interface LiveNeo4jTestGate {
  enabled: boolean;
  reason: string;
  uri?: string;
}

function endpointHost(uri: string): string {
  try {
    const normalized = /^[a-z][a-z0-9+.-]*:\/\//i.test(uri) ? uri : `bolt://${uri}`;
    return new URL(normalized).hostname.toLowerCase();
  } catch {
    return '';
  }
}

function isRailwayHost(host: string): boolean {
  return /(^|\.)(?:railway\.app|railway\.internal|rlwy\.net)$/.test(host) ||
    host.includes('railway') || host.includes('rlwy');
}

function normalizedEndpoint(uri: string): string {
  try {
    const normalized = /^[a-z][a-z0-9+.-]*:\/\//i.test(uri) ? uri : `bolt://${uri}`;
    const parsed = new URL(normalized);
    return `${parsed.hostname.toLowerCase()}:${parsed.port || '7687'}`;
  } catch {
    return uri.trim().replace(/\/+$/, '').toLowerCase();
  }
}

/** Configure the shared driver only from explicit test-only environment variables. */
export function configureLiveNeo4jTest(options: { writes?: boolean } = {}): LiveNeo4jTestGate {
  if (process.env.RUN_LIVE_NEO4J_TESTS !== '1') {
    return { enabled: false, reason: 'set RUN_LIVE_NEO4J_TESTS=1 to opt in' };
  }

  const uri = process.env.NEO4J_TEST_URI?.trim() ?? '';
  const username = process.env.NEO4J_TEST_USERNAME?.trim() ?? '';
  const password = process.env.NEO4J_TEST_PASSWORD ?? '';
  if (!uri) {
    return { enabled: false, reason: 'NEO4J_TEST_URI is required; production NEO4J_URL is never used as fallback' };
  }
  if (!username || !password) {
    return { enabled: false, reason: 'NEO4J_TEST_USERNAME and NEO4J_TEST_PASSWORD are required' };
  }

  const host = endpointHost(uri);
  if (!host) return { enabled: false, reason: 'NEO4J_TEST_URI is invalid' };
  if (isRailwayHost(host)) {
    return { enabled: false, reason: `live tests refuse Railway target ${host}` };
  }
  const configuredAppEndpoint = process.env.NEO4J_URL?.trim() ?? '';
  if (
    configuredAppEndpoint &&
    normalizedEndpoint(configuredAppEndpoint) === normalizedEndpoint(uri)
  ) {
    return { enabled: false, reason: 'live tests refuse the application NEO4J_URL endpoint' };
  }

  if (options.writes) {
    if (process.env.NEO4J_TEST_TARGET_MARKER !== 'DISPOSABLE_TEST_ONLY') {
      return { enabled: false, reason: 'set NEO4J_TEST_TARGET_MARKER=DISPOSABLE_TEST_ONLY for write tests' };
    }
    if (process.env.NEO4J_TEST_DISPOSABLE_ACK !== DISPOSABLE_NEO4J_TEST_ACK) {
      return { enabled: false, reason: `set NEO4J_TEST_DISPOSABLE_ACK=${DISPOSABLE_NEO4J_TEST_ACK}` };
    }
  }

  process.env.NEO4J_URL = uri;
  process.env.NEO4J_USERNAME = username;
  process.env.NEO4J_PASSWORD = password;
  return { enabled: true, reason: 'explicit test target configured', uri };
}
