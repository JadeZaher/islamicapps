/**
 * Barrel for the schema (50 tables: the 40 launch tables, chain_mention_candidates, the three report-correspondence
 * tables and the six chain-fix tables of 0019). drizzle.config.ts and the client read this file.
 */
export * from './enums';
export * from './operations';
export * from './corpus';
export * from './narrators';
export * from './evidence';
export * from './chain-fixes';
export * from './isnad';
export * from './assessments';
export * from './history';
export * from './commentary';
export * from './comparative';
export * from './correspondence';
