/** Fixed pg advisory-lock keys. The same literals appear in drizzle/core/0004_functions.sql. See src/db/AGENTS.md §Locks. */

/** Held by the migrator and the bulk loader so a migration and a load never overlap (sections 2.6, 4.3). */
export const DATA_WRITE_LOCK_KEY = 4_741_100_001;

/** Held by refresh_network() for its own transaction: one network refresh at a time (section 4.1). */
export const NETWORK_REFRESH_LOCK_KEY = 4_741_100_002;
