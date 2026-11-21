/**
 * Compatibility surface for callers that formerly selected a CREATE fast path.
 * See AGENTS.md for the retry/idempotency invariant.
 */

export {
    buildBufferedRow,
    loadHadithsBatch,
    loadChainsBatch as loadChainsBatchFresh,
    loadAssessmentsBatch,
    loadNameMentionsBatch,
    type BufferedRow,
    type ChainsBatchResult,
    type AssessmentsBatchResult,
} from './batch-loaders';
