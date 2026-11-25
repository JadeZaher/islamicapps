/** Reader wording for the chain structure gate (0017), model readings (0019), unified Agent Review (0023) and the compiler head (0019; src/db/AGENTS.md). */
import type { ChainAiMark, ChainCompiler, ChainCorrectionMark, ChainDisposition, ChainFixLabel, ChainNode, ChainSaying, ChainVariantRemark } from '@/db/queries/contracts';

/** Verification-process anchor on /method linked from every chain review indicator tooltip. */
export const CHAIN_VERIFICATION_METHOD_HREF = '/method#chain-tiers';

/** Why a chain's structure is uncertain (0017; codes from `pg_export/chain_structure.py`), in plain words. */
export const CHAIN_STRUCTURE_REASON_LABEL: Record<string, string> = {
  duplicated_link: 'one person seems to be stored as two neighbouring names',
  joined_names: 'one position holds two names joined by «و»',
  ghayr_wahid_half: 'half of «غير واحد» is stored as a name',
  short_beside_long: 'this route is much shorter than another route of the report',
  repeated_name: 'the same name stands twice in the chain',
  text_between_links: 'the text names more between two stored names than the chain holds',
  text_names_more_after: 'the text names a further transmitter after the last stored name',
  not_a_name: 'a stored name contains words that are not a name',
  unaccounted_route_marker: 'the text marks more routes («ح», «جميعا», «كلهم») than were stored',
  crossed_routes: "two of al-Kulayni's routes appear joined in one chain",
  many_routes: 'the report has three or more routes, which the rules read wrong too often',
  sibling_skips_link: 'two routes of this report differ by one name in the middle, so one of them lost or added a name',
  work_not_checked: 'chains in this work were read wrong too often to rely on',
};

/** The plain line under an uncertain chain: shown as stored, kept out of teacher and student lists, and why. */
export function structureNote(node: Pick<ChainNode, 'chain_structure_status' | 'chain_structure_reasons'>): string | null {
  if (node.chain_structure_status !== 'uncertain') return null;
  const reasons = (node.chain_structure_reasons ?? []).map((code) => CHAIN_STRUCTURE_REASON_LABEL[code] ?? code);
  return [
    "The reading of this chain's routes has not been checked; it is not used for teacher and student lists.",
    reasons.length > 0 ? `Why: ${reasons.join('; ')}.` : null,
  ].filter(Boolean).join(' ');
}

const day = (value: string) => value.slice(0, 10);
const COUNT_WORDS = ['no', 'one', 'two', 'three', 'four', 'five'];
/** "two models": the independent reader runs that agree (owner wording, 2026-11-22). */
const readers = (runs: number) => `${COUNT_WORDS[runs] ?? runs} model${runs === 1 ? '' : 's'}`;

/** The tier line of a reading read by agreeing models: "Read by two models (claude-haiku-5-5), 2026-11-22". */
export const readByModelsLine = (fix: Pick<ChainFixLabel, 'models' | 'runs' | 'decided_at'>) =>
  `Read by ${readers(fix.runs)} (${[...new Set(fix.models)].join(', ')}), ${day(fix.decided_at)}`;

export interface ReviewProvenanceStamp {
  role: 'Reader' | 'Agent review' | 'Historical AI review (superseded)' | 'Human verification';
  models: string[];
  date: string | null;
  promptVersion: string | null;
  promptPath: string | null;
  promptSha256: string | null;
  runId: string | null;
  specialistId: string | null;
  superseded: boolean;
}

export type ChainReviewTierKind = 'verified_by_person' | 'agent_verified' | 'agent_reviewed' | 'disputed' | 'read_by_two_models';

export interface ChainReviewIndicatorMeta {
  text: string;
  tier: ChainReviewTierKind;
  tierLabel: string;
  /** True when a legacy `ai_*` record is displayed under Agent Review or superseded by an explicit `agent_*` mark. */
  supersededAiReview: boolean;
  supersededNote: string | null;
  witness: { witness: string; locator: string; method: string; matched_at: string } | null;
  stamps: ReviewProvenanceStamp[];
  methodHref: string;
  methodLinkLabel: string;
}

const cleanText = (value: string | null | undefined): string | null => {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
};

const promptNameFromPath = (promptPath: string | null): string | null => {
  if (!promptPath) return null;
  const parts = promptPath.split('/');
  return parts[parts.length - 1] || promptPath;
};

/** Formats optional prompt provenance fields (`version · file · sha256:prefix`), falling back cleanly when unrecorded. */
export function formatPromptStamp(stamp: Pick<ReviewProvenanceStamp, 'promptVersion' | 'promptPath' | 'promptSha256'>): string {
  const version = cleanText(stamp.promptVersion);
  const pathName = promptNameFromPath(cleanText(stamp.promptPath));
  const sha = cleanText(stamp.promptSha256);
  const parts = [
    version ? (version.startsWith('v') ? version : `v${version}`) : null,
    pathName,
    sha ? `sha256:${sha.slice(0, 12)}` : null,
  ].filter((part): part is string => Boolean(part));
  return parts.length > 0 ? parts.join(' · ') : 'Not recorded';
}

function stampFromMark(
  mark: ChainAiMark,
  role: ReviewProvenanceStamp['role'],
  superseded: boolean,
): ReviewProvenanceStamp {
  return {
    role,
    models: cleanText(mark.model_id) ? [mark.model_id.trim()] : [],
    date: cleanText(mark.at) ? day(mark.at) : null,
    promptVersion: cleanText(mark.prompt_version),
    promptPath: cleanText(mark.prompt_path),
    promptSha256: cleanText(mark.prompt_sha256),
    runId: cleanText(mark.run_id),
    specialistId: cleanText(mark.specialist_id),
    superseded,
  };
}

function stampFromCorrection(
  correction: ChainCorrectionMark,
  role: ReviewProvenanceStamp['role'],
  superseded: boolean,
): ReviewProvenanceStamp {
  return {
    role,
    models: [...new Set(correction.models.map((model) => model.trim()).filter(Boolean))],
    date: cleanText(correction.at) ? day(correction.at) : null,
    promptVersion: cleanText(correction.prompt_version),
    promptPath: cleanText(correction.prompt_path),
    promptSha256: cleanText(correction.prompt_sha256),
    runId: correction.runs.length > 0 ? correction.runs.join(', ') : null,
    specialistId: cleanText(correction.specialist_id),
    superseded,
  };
}

function readerStamp(fix: Pick<ChainFixLabel, 'models' | 'decided_at' | 'prompt_version' | 'prompt_path' | 'prompt_sha256'>): ReviewProvenanceStamp {
  return {
    role: 'Reader',
    models: [...new Set(fix.models.map((model) => model.trim()).filter(Boolean))],
    date: cleanText(fix.decided_at) ? day(fix.decided_at) : null,
    promptVersion: cleanText(fix.prompt_version),
    promptPath: cleanText(fix.prompt_path),
    promptSha256: cleanText(fix.prompt_sha256),
    runId: null,
    specialistId: 'chain-reader',
    superseded: false,
  };
}

function resolveReviewMarks(fix: ChainFixLabel) {
  const hasExplicitAgent = Boolean(fix.agent_review || fix.agent_corrected || fix.agent_disputed);
  const hasLegacyAi = Boolean(fix.ai_review || fix.ai_corrected || fix.ai_disputed);

  // Agent review supersedes AI review in all states (confirmation, correction, dispute).
  const activeCorrected = fix.agent_corrected ?? (!hasExplicitAgent ? fix.ai_corrected ?? null : null);
  const activeDisputed = fix.agent_disputed ?? (!fix.agent_review && !fix.agent_corrected ? fix.ai_disputed ?? null : null);
  const activeReview = fix.agent_review ?? (!fix.agent_disputed ? fix.ai_review ?? null : null);

  return { hasExplicitAgent, hasLegacyAi, activeCorrected, activeDisputed, activeReview };
}

function collectChainStamps(fix: ChainFixLabel, status: ChainNode['chain_structure_status']): {
  stamps: ReviewProvenanceStamp[];
  supersededAiReview: boolean;
  supersededNote: string | null;
} {
  const { hasExplicitAgent, hasLegacyAi, activeCorrected, activeDisputed, activeReview } = resolveReviewMarks(fix);
  const stamps: ReviewProvenanceStamp[] = [];

  if (status === 'verified_by_reviewer' && fix.human_confirmations.length > 0) {
    for (const confirmation of fix.human_confirmations) {
      stamps.push({
        role: 'Human verification',
        models: [confirmation.reviewer],
        date: day(confirmation.reviewed_at),
        promptVersion: null,
        promptPath: null,
        promptSha256: null,
        runId: null,
        specialistId: null,
        superseded: false,
      });
    }
  }

  if (activeCorrected) {
    const fromLegacy = !fix.agent_corrected && activeCorrected === fix.ai_corrected;
    stamps.push(stampFromCorrection(activeCorrected, fromLegacy ? 'Historical AI review (superseded)' : 'Agent review', fromLegacy));
  } else if (activeDisputed) {
    const fromLegacy = !fix.agent_disputed && activeDisputed === fix.ai_disputed;
    stamps.push(stampFromMark(activeDisputed, fromLegacy ? 'Historical AI review (superseded)' : 'Agent review', fromLegacy));
  } else if (activeReview) {
    const fromLegacy = !fix.agent_review && activeReview === fix.ai_review;
    stamps.push(stampFromMark(activeReview, fromLegacy ? 'Historical AI review (superseded)' : 'Agent review', fromLegacy));
  }

  // If an explicit Agent review superseded an earlier legacy AI review/dispute/correction, preserve the legacy provenance too.
  if (hasExplicitAgent && hasLegacyAi) {
    if (fix.ai_review) stamps.push(stampFromMark(fix.ai_review, 'Historical AI review (superseded)', true));
    if (fix.ai_disputed) stamps.push(stampFromMark(fix.ai_disputed, 'Historical AI review (superseded)', true));
    if (fix.ai_corrected) stamps.push(stampFromCorrection(fix.ai_corrected, 'Historical AI review (superseded)', true));
  }

  stamps.push(readerStamp(fix));

  const supersededNote = hasExplicitAgent && hasLegacyAi
    ? 'Agent review supersedes the prior standalone AI review; both original prompt and model stamps are recorded below.'
    : hasLegacyAi
      ? 'Legacy AI-reviewed record unified under Agent Review; original prompt and model are stamped below.'
      : null;

  return { stamps, supersededAiReview: hasLegacyAi, supersededNote };
}

/**
 * Full indicator text, tier classification, stamped prompt/model provenance, and /method verification link
 * under the unified Agent Review model. "Verified" (capitalized) names a person only.
 */
export function chainFixReviewMeta(
  fix: ChainFixLabel | null | undefined,
  status: ChainNode['chain_structure_status'],
): ChainReviewIndicatorMeta | null {
  if (!fix) return null;
  const models = [...new Set(fix.models)].join(', ');
  const { activeCorrected, activeDisputed, activeReview } = resolveReviewMarks(fix);
  const { stamps, supersededAiReview, supersededNote } = collectChainStamps(fix, status);

  let text: string;
  let tier: ChainReviewTierKind;
  let tierLabel: string;

  if (status === 'verified_by_reviewer' && fix.human_confirmations.length > 0) {
    text = fix.human_confirmations.map((confirmation) => `Verified by ${confirmation.reviewer}, ${day(confirmation.reviewed_at)}`).join('; ');
    tier = 'verified_by_person';
    tierLabel = 'Verified by a person';
  } else if (fix.effect === 'annotate') {
    text = `A model reader read the same routes (${models}, ${day(fix.decided_at)})`;
    tier = 'read_by_two_models';
    tierLabel = 'Read by model';
  } else if (activeCorrected) {
    text = `Corrected by Agent review (${activeCorrected.models.join(', ')}, ${activeCorrected.runs.length} runs), ${day(activeCorrected.at)}`;
    tier = 'agent_reviewed';
    tierLabel = 'Agent reviewed (correction)';
  } else if (activeDisputed) {
    text = `${readByModelsLine(fix)}; Disputed by Agent review; awaiting second review`;
    tier = 'disputed';
    tierLabel = 'Disputed by Agent review';
  } else if (activeReview && fix.witness_match) {
    text = `Agent verified: ${COUNT_WORDS[fix.runs] ?? fix.runs} readers agree, reviewed by ${activeReview.model_id}, text matched to ${fix.witness_match.witness}`;
    tier = 'agent_verified';
    tierLabel = 'Agent verified';
  } else if (activeReview) {
    text = `${readByModelsLine(fix)}; Agent reviewed (${activeReview.model_id}), ${day(activeReview.at)}`;
    tier = 'agent_reviewed';
    tierLabel = 'Agent reviewed';
  } else {
    text = readByModelsLine(fix);
    tier = 'read_by_two_models';
    tierLabel = 'Read by two models';
  }

  return {
    text,
    tier,
    tierLabel,
    supersededAiReview,
    supersededNote,
    witness: fix.witness_match ?? null,
    stamps,
    methodHref: CHAIN_VERIFICATION_METHOD_HREF,
    methodLinkLabel: 'Verification process & chain tiers',
  };
}

/**
 * The lines under a chain a model reader read (docs/review/chain-fix-pipeline.md §States; tiers in src/db/AGENTS.md §AI review tier).
 * "Verified" names a person only. Unified under Agent Review (superseding standalone AI review).
 */
export function chainFixNote(fix: ChainFixLabel | null | undefined, status: ChainNode['chain_structure_status']): string | null {
  return chainFixReviewMeta(fix, status)?.text ?? null;
}

/** Indicator metadata and provenance stamps for a report whose applied model reading found no isnad in the text (0021). */
export function noChainReviewMeta(disposition: ChainDisposition | null | undefined): ChainReviewIndicatorMeta | null {
  if (!disposition) return null;
  const activeReview = disposition.agent_review ?? disposition.ai_review ?? null;
  const hasExplicitAgent = Boolean(disposition.agent_review);
  const hasLegacyAi = Boolean(disposition.ai_review);
  const stamps: ReviewProvenanceStamp[] = [];

  if (activeReview) {
    const fromLegacy = !hasExplicitAgent && activeReview === disposition.ai_review;
    stamps.push(stampFromMark(activeReview, fromLegacy ? 'Historical AI review (superseded)' : 'Agent review', fromLegacy));
  }
  if (hasExplicitAgent && hasLegacyAi && disposition.ai_review) {
    stamps.push(stampFromMark(disposition.ai_review, 'Historical AI review (superseded)', true));
  }
  stamps.push(readerStamp(disposition));

  const review = activeReview ? `; Agent reviewed (${activeReview.model_id}), ${day(activeReview.at)}` : '';
  return {
    text: `No chain is written in this report (${readByModelsLine(disposition).replace(/^Read/, 'read')}${review}).`,
    tier: activeReview ? 'agent_reviewed' : 'read_by_two_models',
    tierLabel: activeReview ? 'Agent reviewed (no chain)' : 'Read by two models (no chain)',
    supersededAiReview: hasLegacyAi,
    supersededNote: hasExplicitAgent && hasLegacyAi
      ? 'Agent review supersedes the prior standalone AI review; both original prompt and model stamps are recorded below.'
      : hasLegacyAi
        ? 'Legacy AI-reviewed record unified under Agent Review; original prompt and model are stamped below.'
        : null,
    witness: null,
    stamps,
    methodHref: CHAIN_VERIFICATION_METHOD_HREF,
    methodLinkLabel: 'Verification process & chain tiers',
  };
}

/** The line for a report whose applied model reading found no isnad in the text (0021): instead of stored junk names. */
export function noChainNote(disposition: ChainDisposition | null | undefined): string | null {
  return noChainReviewMeta(disposition)?.text ?? null;
}

/** The heading of a route of a two-saying report: "Chain of the first saying" (a second route of the same saying is numbered). */
export function sayingHeading(saying: ChainSaying, routeOfSaying: number, routesOfSaying: number): string {
  return routesOfSaying > 1 ? `${saying.label}, route ${routeOfSaying}` : saying.label;
}

/** The plain label of the compiler heading a chain: derived from the work, never written in the text. */
export function compilerNote(compiler: ChainCompiler): string {
  return compiler.link === 'direct'
    ? 'Compiler of the work; not written in the text'
    : 'Compiler of the work; not written in the text, and this chain does not start from his own teacher, so no teacher link is drawn';
}

/** The variant remarks of the model reading a report's chains share (one fix per report), or none. */
export function variantRemarksOf(nodes: Pick<ChainNode, 'chain_fix'>[]): ChainVariantRemark[] {
  return nodes.find((node) => node.chain_fix?.variant_remarks?.length)?.chain_fix?.variant_remarks ?? [];
}

/** The lead of a variant remark's line; the Arabic sentence and the names follow it (never drawn as a chain, never a route). */
export const VARIANT_REMARK_LEAD = 'The report mentions another version:';

/** The names a remark lists, in the order the sentence gives them; alternatives of one level joined by «/». */
export function variantRemarkNames(remark: ChainVariantRemark): string {
  return remark.surfaces.map((level) => level.join(' / ')).join('، ');
}

/** A remark only one of the two readers noted is said so: a weaker claim than one both made. */
export function variantRemarkCaveat(remark: ChainVariantRemark): string | null {
  return remark.passes.length < 2 ? 'noted by one of the two readers' : null;
}
