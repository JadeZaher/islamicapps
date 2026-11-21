/**
 * dataset-version.ts — DatasetVersion provenance node management.
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Workstream C
 *
 * Pure module: no side effects on import.
 * Exports:
 *   mergeDatasetVersion(opts) → Promise<{ id: string }>
 *   linkHadithToDatasetVersion(hadithKey, keyProp, dvId) → Promise<void>
 *   withFullregenLease(contentHash, work) → serialized writer scope
 *
 * FR-0.2 / FR-0.3 / tasks 0.10, 0.11
 *
 * Every regen run creates or merges a :DatasetVersion node that pins:
 *   - expected_record_count (99,283 for the current canonical release, or a future total)
 *   - per-tradition sub-counts
 *   - content_hash (sha256 of input CSVs)
 *   - measured_unknown_fraction (was going NULL in legacy — this fixes it)
 *   - active/load_status lifecycle (full loads stage, then promote atomically)
 *
 * INGESTED_IN edges from :Hadith to :DatasetVersion are written by
 * linkHadithToDatasetVersion(), called from loadHadith.
 */

import { randomUUID } from 'crypto';
import { runQuery, runWrite } from '../../../lib/db/neo4j';

// ─── Public types ─────────────────────────────────────────────────────────────

export interface MergeDatasetVersionOpts {
    /** Total expected CSV records (canonical ground truth). */
    expectedRecordCount: number;
    /** Per-tradition record counts, e.g. { Sunni: 64356, Imami: 33225, ... } */
    perTraditionCounts: Record<string, number>;
    /** sha256 hex of the input CSV(s). */
    contentHash: string;
    /** Fraction of rows where attribution is unknown/unresolved (0–1). */
    measuredUnknownFraction?: number;
    /** Optional human-readable label for this version. */
    versionLabel?: string;
    /** Keep false while a full snapshot is still loading. Defaults to true. */
    activateImmediately?: boolean;
    /** False for disposable/incomplete loads that must never become active. */
    releaseEligible?: boolean;
    /** Stable machine-readable reason when releaseEligible is false. */
    nonReleaseReason?: string;
    /** Immutable purpose within the release/non-release lifecycle class. */
    loadPurpose?: DatasetVersionLoadPurpose;
}

export type DatasetVersionReleaseClass = 'release' | 'non_release';
export type DatasetVersionLoadPurpose = 'release_fullregen' | 'dev_fullregen' | 'legacy_diff';

export interface DatasetVersionLifecycleSnapshot {
    release_class?: unknown;
    release_eligible?: unknown;
    non_release?: unknown;
    load_status?: unknown;
    active?: unknown;
    load_purpose?: unknown;
    non_release_reason?: unknown;
}

interface ExistingDatasetVersionRow extends DatasetVersionLifecycleSnapshot {
    id: string;
}

/** Infer one immutable lifecycle class; contradictory or legacy-ambiguous state is rejected. */
export function inferDatasetVersionReleaseClass(
    snapshot: DatasetVersionLifecycleSnapshot,
): DatasetVersionReleaseClass | null {
    const signals = new Set<DatasetVersionReleaseClass>();
    if (snapshot.release_class === 'release' || snapshot.release_class === 'non_release') {
        signals.add(snapshot.release_class);
    }
    if (typeof snapshot.release_eligible === 'boolean') {
        signals.add(snapshot.release_eligible ? 'release' : 'non_release');
    }
    if (typeof snapshot.non_release === 'boolean') {
        signals.add(snapshot.non_release ? 'non_release' : 'release');
    }
    const loadStatus = typeof snapshot.load_status === 'string' ? snapshot.load_status : '';
    if (loadStatus.startsWith('non_release_')) signals.add('non_release');
    if (loadStatus === 'complete' || snapshot.active === true) signals.add('release');
    return signals.size === 1 ? [...signals][0] : null;
}

/** Fail before writes when a content hash is already owned by another lifecycle class. */
export function assertDatasetVersionLifecycleClass(
    snapshot: DatasetVersionLifecycleSnapshot,
    requestedClass: DatasetVersionReleaseClass,
): void {
    const existingClass = inferDatasetVersionReleaseClass(snapshot);
    if (existingClass === null) {
        throw new Error(
            '[dataset-version] Existing content hash has ambiguous or contradictory lifecycle class',
        );
    }
    if (existingClass !== requestedClass) {
        throw new Error(
            `[dataset-version] Existing content hash is ${existingClass}; ` +
            `refusing ${requestedClass} reuse`,
        );
    }
}

/** Infer legacy purpose markers without permitting cross-purpose reuse. */
export function inferDatasetVersionLoadPurpose(
    snapshot: DatasetVersionLifecycleSnapshot,
): DatasetVersionLoadPurpose | null {
    const signals = new Set<DatasetVersionLoadPurpose>();
    if (
        snapshot.load_purpose === 'release_fullregen' ||
        snapshot.load_purpose === 'dev_fullregen' ||
        snapshot.load_purpose === 'legacy_diff'
    ) signals.add(snapshot.load_purpose);
    const reason = snapshot.non_release_reason === null || snapshot.non_release_reason === undefined
        ? ''
        : String(snapshot.non_release_reason).trim();
    if (reason === 'dev_allow_incomplete_data') signals.add('dev_fullregen');
    else if (reason === 'legacy_diff_mode') signals.add('legacy_diff');
    else if (reason !== '') return null;
    if (inferDatasetVersionReleaseClass(snapshot) === 'release') signals.add('release_fullregen');
    return signals.size === 1 ? [...signals][0] : null;
}

/** Reject content-hash reuse across immutable lifecycle class or load purpose. */
export function assertDatasetVersionLifecycleIdentity(
    snapshot: DatasetVersionLifecycleSnapshot,
    requestedClass: DatasetVersionReleaseClass,
    requestedPurpose: DatasetVersionLoadPurpose,
): void {
    assertDatasetVersionLifecycleClass(snapshot, requestedClass);
    const explicitPurpose = snapshot.load_purpose === 'release_fullregen' ||
        snapshot.load_purpose === 'dev_fullregen' ||
        snapshot.load_purpose === 'legacy_diff'
        ? snapshot.load_purpose
        : null;
    if (explicitPurpose !== null && explicitPurpose !== requestedPurpose) {
        throw new Error(
            `[dataset-version] Existing content hash purpose is ${explicitPurpose}; ` +
            `refusing ${requestedPurpose} reuse`,
        );
    }
    const existingPurpose = inferDatasetVersionLoadPurpose(snapshot);
    if (existingPurpose !== null && existingPurpose !== requestedPurpose) {
        throw new Error(
            `[dataset-version] Existing content hash purpose is ${existingPurpose}; ` +
            `refusing ${requestedPurpose} reuse`,
        );
    }
    const expectedReason = requestedPurpose === 'dev_fullregen'
        ? 'dev_allow_incomplete_data'
        : requestedPurpose === 'legacy_diff'
            ? 'legacy_diff_mode'
            : '';
    const existingReason = snapshot.non_release_reason === null ||
        snapshot.non_release_reason === undefined
        ? ''
        : String(snapshot.non_release_reason).trim();
    if (existingReason !== '' && existingReason !== expectedReason) {
        throw new Error(
            `[dataset-version] Existing content hash reason is ${existingReason}; ` +
            `expected ${expectedReason || '<blank>'} for ${requestedPurpose}`,
        );
    }
    if (existingPurpose === null) {
        throw new Error('[dataset-version] Existing content hash has ambiguous load purpose');
    }
}

function snapshotToken(value: unknown): string {
    return value === null || value === undefined ? '<null>' : String(value);
}

export const FULLREGEN_LEASE_NAME = 'global-fullregen';
const FULLREGEN_LEASE_TTL_SECONDS = 600;
const FULLREGEN_LEASE_HEARTBEAT_MS = 60_000;

export interface FullregenLeaseHandle {
    ownerToken: string;
    assertHeld(): Promise<void>;
}

/** Serialize full-regeneration writers through one database-owned reservation. */
export async function withFullregenLease<T>(
    contentHash: string,
    work: (lease: FullregenLeaseHandle) => Promise<T>,
): Promise<T> {
    await runWrite(`
        CREATE CONSTRAINT fullregen_lease_name_unique IF NOT EXISTS
        FOR (lease:FullregenLease) REQUIRE lease.name IS UNIQUE
    `);

    const ownerToken = randomUUID();
    const acquired = await runWrite<{ owner_token: string }>(`
        MERGE (lease:FullregenLease { name: $leaseName })
        ON CREATE SET
            lease.owner_token = $ownerToken,
            lease.created_at = datetime(),
            lease.expires_at = datetime() + duration({ seconds: $ttlSeconds })
        WITH lease
        WHERE lease.owner_token = $ownerToken
           OR lease.owner_token IS NULL
        SET lease.owner_token = $ownerToken,
            lease.content_hash = $contentHash,
            lease.acquired_at = datetime(),
            lease.heartbeat_at = datetime(),
            lease.expires_at = datetime() + duration({ seconds: $ttlSeconds }),
            lease.released_at = null
        RETURN lease.owner_token AS owner_token
    `, {
        leaseName: FULLREGEN_LEASE_NAME,
        ownerToken,
        contentHash,
        ttlSeconds: FULLREGEN_LEASE_TTL_SECONDS,
    });
    if (acquired.length !== 1 || acquired[0]?.owner_token !== ownerToken) {
        throw new Error(
            '[fullregen] An active or abandoned full-regeneration lease exists; ' +
            'refusing writes until an audited manual cleanup releases it',
        );
    }

    let heartbeatFailure: Error | null = null;
    let heartbeatInFlight: Promise<void> | null = null;
    const renew = async (): Promise<void> => {
        const rows = await runWrite<{ owner_token: string }>(`
            MATCH (lease:FullregenLease { name: $leaseName, owner_token: $ownerToken })
            WHERE lease.expires_at > datetime()
            SET lease.heartbeat_at = datetime(),
                lease.expires_at = datetime() + duration({ seconds: $ttlSeconds })
            RETURN lease.owner_token AS owner_token
        `, {
            leaseName: FULLREGEN_LEASE_NAME,
            ownerToken,
            ttlSeconds: FULLREGEN_LEASE_TTL_SECONDS,
        });
        if (rows.length !== 1 || rows[0]?.owner_token !== ownerToken) {
            throw new Error('[fullregen] Full-regeneration database lease was lost');
        }
    };
    const timer = setInterval(() => {
        if (heartbeatInFlight || heartbeatFailure) return;
        heartbeatInFlight = renew()
            .catch((error: unknown) => {
                heartbeatFailure = error instanceof Error ? error : new Error(String(error));
            })
            .finally(() => {
                heartbeatInFlight = null;
            });
    }, FULLREGEN_LEASE_HEARTBEAT_MS);
    timer.unref();

    const lease: FullregenLeaseHandle = {
        ownerToken,
        async assertHeld(): Promise<void> {
            if (heartbeatFailure) {
                throw new Error(
                    '[fullregen] Full-regeneration lease heartbeat failed; stopping before more writes',
                    { cause: heartbeatFailure },
                );
            }
            const rows = await runQuery<{ owner_token: string }>(`
                MATCH (lease:FullregenLease { name: $leaseName, owner_token: $ownerToken })
                WHERE lease.expires_at > datetime()
                RETURN lease.owner_token AS owner_token
            `, { leaseName: FULLREGEN_LEASE_NAME, ownerToken });
            if (rows.length !== 1 || rows[0]?.owner_token !== ownerToken) {
                throw new Error(
                    '[fullregen] Full-regeneration lease ownership or heartbeat expiry check failed',
                );
            }
        },
    };

    let workFailed = false;
    try {
        const result = await work(lease);
        await lease.assertHeld();
        return result;
    } catch (error) {
        workFailed = true;
        throw error;
    } finally {
        clearInterval(timer);
        await heartbeatInFlight;
        try {
            const released = await runWrite<{ owner_token: null }>(`
                MATCH (lease:FullregenLease { name: $leaseName, owner_token: $ownerToken })
                SET lease.owner_token = null,
                    lease.content_hash = null,
                    lease.released_at = datetime(),
                    lease.expires_at = datetime() - duration({ seconds: 1 })
                RETURN lease.owner_token AS owner_token
            `, { leaseName: FULLREGEN_LEASE_NAME, ownerToken });
            if (released.length !== 1) {
                throw new Error('[fullregen] Full-regeneration lease release lost ownership');
            }
        } catch (releaseError) {
            if (!workFailed) throw releaseError;
            console.error('[fullregen] Failed to release database lease after load failure:', releaseError);
        }
    }
}

// ─── Attribution disclaimer (G-3) ────────────────────────────────────────────

const ATTRIBUTION_DISCLAIMER =
    'Graph metrics reflect kathrat al-riwāya (volume of transmission), NOT ʿadāla/ḍabṭ ' +
    'or any authenticity ḥukm. Algorithmic output is never a scholarly verdict.';

// ─── mergeDatasetVersion ──────────────────────────────────────────────────────

/**
 * Idempotently MERGE a :DatasetVersion node keyed on contentHash.
 * If a node with this hash already exists, it is matched (not duplicated).
 * Returns the node's stable id.
 *
 * Idempotency: keyed on contentHash so the same dataset file always maps to
 * the same version node. A different CSV produces a new DatasetVersion.
 * Fullregen passes activateImmediately=false and calls activateDatasetVersion
 * only after its fail-closed load and annotation phases complete.
 */
export async function mergeDatasetVersion(
    opts: MergeDatasetVersionOpts
): Promise<{ id: string }> {
    const {
        expectedRecordCount,
        perTraditionCounts,
        contentHash,
        measuredUnknownFraction = 0,
        versionLabel = '',
        activateImmediately = true,
        releaseEligible = true,
        nonReleaseReason = '',
        loadPurpose = releaseEligible ? 'release_fullregen' : undefined,
    } = opts;

    if (activateImmediately && !releaseEligible) {
        throw new Error('[dataset-version] A non-release DatasetVersion cannot activate immediately');
    }
    const releaseClass: DatasetVersionReleaseClass = releaseEligible ? 'release' : 'non_release';
    if (!loadPurpose) {
        throw new Error('[dataset-version] Non-release DatasetVersion requires an explicit loadPurpose');
    }
    if (
        (releaseEligible && loadPurpose !== 'release_fullregen') ||
        (!releaseEligible && loadPurpose === 'release_fullregen')
    ) {
        throw new Error(
            `[dataset-version] loadPurpose=${loadPurpose} is incompatible with ${releaseClass}`,
        );
    }
    const expectedReason = loadPurpose === 'dev_fullregen'
        ? 'dev_allow_incomplete_data'
        : loadPurpose === 'legacy_diff'
            ? 'legacy_diff_mode'
            : '';
    if (nonReleaseReason !== expectedReason) {
        throw new Error(
            `[dataset-version] nonReleaseReason=${nonReleaseReason || '<blank>'} ` +
            `is incompatible with loadPurpose=${loadPurpose}`,
        );
    }
    const activateNow = activateImmediately && releaseEligible;
    const loadStatus = releaseEligible
        ? (activateNow ? 'complete' : 'loading')
        : 'non_release_loading';

    const newId = randomUUID();
    const now = new Date().toISOString();

    // Build per-tradition props (flattened into top-level node properties).
    const traditionProps: Record<string, unknown> = {};
    for (const [tradition, count] of Object.entries(perTraditionCounts)) {
        // e.g. subcount_sunni, subcount_imami — lowercase, safe property names
        const key = `subcount_${tradition.toLowerCase().replace(/[^a-z]/g, '_')}`;
        traditionProps[key] = count;
    }

    const params: Record<string, unknown> = {
        contentHash,
        id: newId,
        expectedRecordCount,
        measuredUnknownFraction,
        disclaimer: ATTRIBUTION_DISCLAIMER,
        versionLabel: versionLabel || `regen-${now.slice(0, 10)}`,
        activateNow,
        loadStatus,
        releaseClass,
        loadPurpose,
        releaseEligible,
        nonReleaseReason,
        perTraditionJson: JSON.stringify(perTraditionCounts),
    };

    const existingRows = await runQuery<ExistingDatasetVersionRow>(`
        MATCH (dv:DatasetVersion { content_hash: $contentHash })
        RETURN dv.id AS id,
               dv.release_class AS release_class,
               dv.release_eligible AS release_eligible,
               dv.non_release AS non_release,
               dv.load_status AS load_status,
               dv.active AS active,
               dv.load_purpose AS load_purpose,
               dv.non_release_reason AS non_release_reason
    `, { contentHash });
    if (existingRows.length > 1) {
        throw new Error(`[dataset-version] Duplicate DatasetVersion content hash ${contentHash}`);
    }

    let rows: Array<{ id: string }>;
    const existing = existingRows[0];
    if (existing) {
        assertDatasetVersionLifecycleIdentity(existing, releaseClass, loadPurpose);
        rows = await runWrite<{ id: string }>(`
            MATCH (dv:DatasetVersion { id: $existingId, content_hash: $contentHash })
            WHERE coalesce(toString(dv.release_class), '<null>') = $observedReleaseClass
              AND coalesce(toString(dv.release_eligible), '<null>') = $observedReleaseEligible
              AND coalesce(toString(dv.non_release), '<null>') = $observedNonRelease
              AND coalesce(toString(dv.load_status), '<null>') = $observedLoadStatus
              AND coalesce(toString(dv.active), '<null>') = $observedActive
              AND coalesce(toString(dv.load_purpose), '<null>') = $observedLoadPurpose
              AND coalesce(toString(dv.non_release_reason), '<null>') = $observedNonReleaseReason
            SET dv.updated_at = datetime(),
                dv.measured_unknown_fraction = $measuredUnknownFraction,
                dv.active = CASE
                    WHEN $activateNow THEN true
                    WHEN $releaseClass = 'non_release' THEN false
                    ELSE coalesce(dv.active, false)
                END,
                dv.load_status = $loadStatus,
                dv.release_class = coalesce(dv.release_class, $releaseClass),
                dv.load_purpose = coalesce(dv.load_purpose, $loadPurpose),
                dv.release_eligible = coalesce(dv.release_eligible, $releaseEligible),
                dv.non_release = coalesce(dv.non_release, NOT $releaseEligible),
                dv.non_release_reason = CASE
                    WHEN $releaseClass = 'release' THEN null
                    ELSE $nonReleaseReason
                END
            RETURN dv.id AS id
        `, {
            ...params,
            existingId: existing.id,
            observedReleaseClass: snapshotToken(existing.release_class),
            observedReleaseEligible: snapshotToken(existing.release_eligible),
            observedNonRelease: snapshotToken(existing.non_release),
            observedLoadStatus: snapshotToken(existing.load_status),
            observedActive: snapshotToken(existing.active),
            observedLoadPurpose: snapshotToken(existing.load_purpose),
            observedNonReleaseReason: snapshotToken(existing.non_release_reason),
        });
        if (rows.length === 0) {
            throw new Error(
                '[dataset-version] DatasetVersion lifecycle changed concurrently; no update applied',
            );
        }
    } else {
        rows = await runWrite<{ id: string }>(`
            CREATE (dv:DatasetVersion {
                content_hash: $contentHash,
                id: $id,
                release_class: $releaseClass,
                load_purpose: $loadPurpose,
                release_eligible: $releaseEligible,
                non_release: NOT $releaseEligible,
                active: $activateNow,
                load_status: $loadStatus,
                expected_record_count: $expectedRecordCount,
                measured_unknown_fraction: $measuredUnknownFraction,
                attribution_disclaimer: $disclaimer,
                version_label: $versionLabel,
                _per_tradition: $perTraditionJson,
                created_at: datetime()
            })
            SET dv.non_release_reason = CASE
                WHEN $releaseEligible THEN null ELSE $nonReleaseReason
            END
            RETURN dv.id AS id
        `, params);
    }
    if (!rows.length) {
        throw new Error('[dataset-version] mergeDatasetVersion returned no rows');
    }

    const dvId = rows[0].id;

    // Also write per-tradition flattened sub-count properties directly onto node.
    // Doing this in a second pass keeps the MERGE clause above clean.
    if (Object.keys(traditionProps).length > 0) {
        const setParts = Object.keys(traditionProps)
            .map((k) => `dv.${k} = $${k}`)
            .join(', ');
        const setCypher = `
            MATCH (dv:DatasetVersion { id: $dvId })
            SET ${setParts}
        `;
        await runWrite(setCypher, { dvId, ...traditionProps });
    }

    return { id: dvId };
}

/** Atomically promote one successfully loaded version and deactivate its peers. */
export async function activateDatasetVersion(dvId: string): Promise<void> {
    const rows = await runWrite<{ id: string }>(`
        MATCH (target:DatasetVersion { id: $dvId })
        WHERE target.release_class = 'release'
          AND target.load_purpose = 'release_fullregen'
          AND coalesce(target.release_eligible, true) = true
          AND coalesce(target.non_release, false) = false
        WITH target
        MATCH (dv:DatasetVersion)
        SET dv.active = (dv.id = target.id),
            dv.updated_at = datetime()
        SET target.load_status = 'complete',
            target.completed_at = datetime()
        RETURN target.id AS id
    `, { dvId });
    if (rows.length === 0) {
        throw new Error(
            `[dataset-version] Cannot activate missing or non-release DatasetVersion ${dvId}`,
        );
    }
}

/** Finalize a disposable load without ever making it active or release-complete. */
export async function markDatasetVersionNonReleaseLoaded(
    dvId: string,
    purpose: Exclude<DatasetVersionLoadPurpose, 'release_fullregen'>,
    reason: string,
): Promise<void> {
    const rows = await runWrite<{ id: string }>(`
        MATCH (dv:DatasetVersion { id: $dvId })
        WHERE dv.release_class = 'non_release'
          AND dv.load_purpose = $purpose
          AND dv.release_eligible = false
          AND dv.non_release = true
        SET dv.active = false,
            dv.non_release_reason = coalesce(dv.non_release_reason, $reason),
            dv.load_status = 'non_release_loaded',
            dv.non_release_loaded_at = datetime(),
            dv.updated_at = datetime()
        RETURN dv.id AS id
    `, { dvId, purpose, reason });
    if (rows.length === 0) {
        throw new Error(
            `[dataset-version] Cannot finalize missing or release-class DatasetVersion ${dvId}`,
        );
    }
}

// ─── linkHadithToDatasetVersion ───────────────────────────────────────────────

/**
 * Write an idempotent [:INGESTED_IN] edge from a :Hadith to a :DatasetVersion.
 * Called by loadHadith for every ingested row.
 *
 * @param hadithKey   Value of the business key property on :Hadith
 * @param keyProp     'dataset_row_id' | 'pipeline_key'
 * @param dvId        DatasetVersion.id (uuid)
 */
export async function linkHadithToDatasetVersion(
    hadithKey: string | number,
    keyProp: 'dataset_row_id' | 'pipeline_key',
    dvId: string
): Promise<void> {
    const cypher = `
        MATCH (h:Hadith { ${keyProp}: $hadithKey })
        MATCH (dv:DatasetVersion { id: $dvId })
        MERGE (h)-[:INGESTED_IN]->(dv)
    `;
    await runWrite(cypher, { hadithKey, dvId });
}

// ─── deactivateOtherVersions ──────────────────────────────────────────────────

/**
 * Mark all DatasetVersion nodes except the given id as active=false.
 * Retained for incremental modes; fullregen uses activateDatasetVersion after loading.
 * Never deletes — tombstone semantics are in tombstone.ts.
 */
export async function deactivateOtherVersions(activeDvId: string): Promise<void> {
    const cypher = `
        MATCH (dv:DatasetVersion)
        WHERE dv.id <> $activeDvId
        SET dv.active = false, dv.updated_at = datetime()
    `;
    await runWrite(cypher, { activeDvId });
}
