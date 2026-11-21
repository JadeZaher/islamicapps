/**
 * Barrel for the schema (44 tables: the 40 launch tables, chain_mention_candidates, and the three report-correspondence
 * tables). drizzle.config.ts and the client read this file.
 */
export * from './enums';
export * from './operations';
export * from './corpus';
export * from './narrators';
export * from './evidence';
export * from './isnad';
export * from './assessments';
export * from './history';
export * from './commentary';
export * from './comparative';
export * from './correspondence';
