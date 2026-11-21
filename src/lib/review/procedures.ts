/**
 * The AI-review registry: every rule procedure and every specialist reviewer, with its evidence, measured accuracy,
 * failure modes, reader label and credits. Single source for /method, docs/review/ai-review.md and the coverage test.
 * See src/lib/review/AGENTS.md.
 */
import type { EnumValueReference } from '../glossary/terms';
import type { SourceCode } from '../sources/registry';
import type { ClaimKind } from './claim-key';

/** Where a procedure stands. Only `in_use` procedures produce labels readers see today. */
export type ProcedureStatus = 'in_use' | 'adopted_not_loaded' | 'in_progress' | 'planned';

/** The two kinds of AI review, never blurred: deterministic code, or a model working as a specialist reviewer. */
export type ReviewKind = 'rule' | 'specialist';

export const REVIEW_KIND_LABEL: Readonly<Record<ReviewKind, string>> = {
  rule: 'Checked by rule',
  specialist: 'AI specialist review',
};

export interface Measurement {
  /** What was measured, in one sentence with the numbers. */
  summary: string;
  /** Sample size and who read it. */
  sample: string;
  /** Repository path of the measurement. */
  where: string;
}

export interface RuleProcedure {
  kind: 'rule';
  /** Stable anchor on /method (`/method#<id>`) and the procedure id recorded on every AI-review record. */
  id: string;
  version: string;
  claimKind: ClaimKind;
  title: string;
  status: ProcedureStatus;
  /** The rule in plain words. */
  rule: string;
  evidence: readonly string[];
  /** Null when nothing has been measured; then `unmeasured` says so plainly. */
  measured: Measurement | null;
  unmeasured?: string;
  failureModes: readonly string[];
  /** What a reader sees next to the claim. */
  readerLabel: string;
  /** What the rule deliberately leaves out. */
  excluded?: readonly string[];
  sources: readonly SourceCode[];
  /** Code that implements the rule (its SHA-256 is recorded on each AI-review record). */
  code: readonly string[];
  /** Database enum values whose label this procedure explains. */
  covers: readonly EnumValueReference[];
  glossary: readonly string[];
}

export interface Specialist {
  kind: 'specialist';
  id: string;
  version: string;
  claimKinds: readonly ClaimKind[];
  title: string;
  status: 'prompt_written' | 'pilot_ready' | 'in_use';
  /** The question the specialist answers. */
  question: string;
  /** The saved system prompt: it is the documentation of what the reviewer was told. */
  prompt: string;
  packet: readonly string[];
  recommendedModel: string;
  modelReason: string;
  /** Models that must not review this claim kind, with why (independence from the producer). */
  notThisModel: readonly string[];
  measured: Measurement | null;
  unmeasured?: string;
}

export interface MethodSection {
  /** Anchor on /method; every "AI-reviewed" label of this kind links here. */
  id: string;
  title: string;
  claimKinds: readonly ClaimKind[];
  intro: string;
  procedures: readonly RuleProcedure[];
  specialistIds: readonly string[];
}

export const AI_REVIEW_MEANING =
  'AI-reviewed means a named, versioned check was run on this claim and passed: either a rule written as code, or a specialist AI reviewer that saw only the evidence packet. It never means a person has checked it. Human reviews are listed separately, each under the reviewer’s name.';

// ── Identity ───────────────────────────────────────────────────────────────────────────────────────────────────────

const IDENTITY: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'identity-source-index-confirmed-by-text',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'Source index confirmed by the Arabic text',
    status: 'in_use',
    rule:
      'The six-books source ships its own narrator index for each chain. The identity stands when the source names this person at this position, the name written in the Arabic agrees with that person’s recorded name position by position (or every source id aligns across the branches), and no other candidate names someone else. A kunya-only match never counts against it.',
    evidence: [
      'The report’s Arabic text and its extracted chain, bound by the text’s SHA-256',
      'The source’s narrator index for the report (K6 chain_indx), read from the original file',
      'The narrator lexicon’s recorded names for each indexed person',
    ],
    measured: {
      summary:
        'Where this rule and hadith-kg (an independent compilation) both identify a name and both are confirmed by the text, they pair the same way for 19,855 of 20,972 mentions (94.7 %). A separate reading found about one in twenty wrong where two people share a name.',
      sample:
        'Agreement: 20,972 co-claimed Sunni mentions, measured by code (a floor, not a precision). The one-in-twenty reading: one reader; sample size not recorded in the repository.',
      where: 'datasets/hadith-data/diagnostics/source-identity/README.md; src/db/AGENTS.md §Standing identity',
    },
    failureModes: [
      'Shared opening tokens let a wrong index pass (قيس بن أبي غرزة confirmed as قيس بن أبي حازم through قيس بن أبي)',
      'Bare isms shared by several men (سفيان, خالد) when the source commits to one of them',
      'Duplicate lexicon rows for one man look like two people',
    ],
    readerLabel: 'AI-reviewed (checked by rule): the source’s index and the text agree',
    excluded: ['Placeholder lexicon rows (single word, kunya only, no Arabic name, unidentified shaykh) are never a target'],
    sources: ['K6I', 'MSD', 'SUN'],
    code: ['datasets/hadith-data/reconciled/build_k6_source_index_sidecar.py', 'datasets/hadith-data/pg_export/export_postgres.py'],
    covers: ['mention_candidate_basis.source_index_confirmed_by_text'],
    glossary: ['confirmed-by-source-and-text', 'basis', 'source-index'],
  },
  {
    kind: 'rule',
    id: 'identity-source-index',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'Source index without full confirmation',
    status: 'in_use',
    rule:
      'The source’s index names a person at a position the Arabic corroborates, but the report as a whole does not agree position by position. The claim is shown as the source’s, not as AI-reviewed.',
    evidence: ['The source’s narrator index', 'The aligned positions of the Arabic chain'],
    measured: {
      summary: 'Across all co-claimed Sunni mentions, the source index and hadith-kg pair the same way for 90,295 of 96,331 (93.7 %).',
      sample: '96,331 mentions, measured by code; agreement between two sources, not a precision.',
      where: 'datasets/hadith-data/diagnostics/source-identity/README.md',
    },
    failureModes: ['A position shift in a report where the source counts names differently from the text'],
    readerLabel: 'Source index (the source’s claim; not AI-reviewed)',
    sources: ['K6I'],
    code: ['datasets/hadith-data/pg_export/export_postgres.py'],
    covers: ['mention_candidate_basis.source_index'],
    glossary: ['source-index'],
  },
  {
    kind: 'rule',
    id: 'identity-name-match',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'Name match against the narrator lexicon',
    status: 'in_use',
    rule:
      'In Sunni reports only, the name as written matches exactly one lexicon entry, letter for letter or after five fixed spelling folds. A name shared by several entries never matches. The match is a candidate, never AI-reviewed.',
    evidence: ['The name as written', 'The lexicon’s names after the same folds'],
    measured: null,
    unmeasured: 'No precision has been measured for name matches. They are shown only as candidates for that reason.',
    failureModes: ['Two people with one recorded name where the lexicon holds only one of them'],
    readerLabel: 'Matched by name (a candidate; not AI-reviewed)',
    excluded: ['Imami, Ibadi and Zaydi reports get no name candidate (owner decision: sanads stay within their tradition)'],
    sources: ['MSD'],
    code: ['datasets/hadith-data/regen_unified_csvs.py'],
    covers: ['mention_candidate_basis.name_exact', 'mention_candidate_basis.name_spelling_fold'],
    glossary: ['matched-by-name'],
  },
  {
    kind: 'rule',
    id: 'identity-kunya-only',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'Kunya-only match (a label)',
    status: 'in_use',
    rule:
      'The only match is on a kunya. It is shown as a labelled note, never contests another identity, and is left out of every analysis.',
    evidence: ['The name as written', 'Lexicon entries that are a kunya alone'],
    measured: null,
    unmeasured: 'Not measured; by owner decision it is a label, not an identification.',
    failureModes: ['Many narrators share one kunya'],
    readerLabel: 'Matched by kunya only (a label)',
    sources: ['MSD'],
    code: ['datasets/hadith-data/regen_unified_csvs.py'],
    covers: ['mention_candidate_basis.name_kunya_only'],
    glossary: ['matched-by-kunya-only', 'kunya'],
  },
  {
    kind: 'rule',
    id: 'identity-imam-kunya-convention',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'The Imams’ conventional kunyas in Imami chains',
    status: 'adopted_not_loaded',
    rule:
      'In an Imami chain, a name that is exactly one of the listed kunyas, optionally with a listed qualifier, followed by the honorific marker, names that Imam. A kunya several Imams share, with no qualifier, gives a labelled candidate for each, never AI-reviewed. Any other words after the kunya mean it is not an Imam.',
    evidence: ['The name as written with its marker', 'The convention table (reviewable data, not a scholarly claim)'],
    measured: null,
    unmeasured: 'Not yet measured. The specialist pilot includes a sample of these mentions.',
    failureModes: ['A non-Imam narrator with the same kunya and a marker added by a copyist'],
    readerLabel: 'AI-reviewed (checked by rule): the Imams’ conventional kunya',
    excluded: ['Sunni, Ibadi and Zaydi chains'],
    sources: ['THQ', 'SWI'],
    code: ['datasets/hadith-data/pg_export/imam_kunya.py', 'datasets/hadith-data/pg_export/imam_kunya_conventions.json'],
    covers: ['mention_candidate_basis.imam_kunya_convention', 'mention_candidate_basis.imam_kunya_candidate'],
    glossary: ['kunya', 'imam-report'],
  },
  {
    kind: 'rule',
    id: 'identity-two-sources-agree',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'Two independent sources agree',
    status: 'adopted_not_loaded',
    rule:
      'The six-books source index and hadith-kg, compiled independently, name the same person at the same name-consistent position. Riwayat agreeing with hadith-kg does not count: its Sunni ids are hadith-kg’s own annotation.',
    evidence: ['Both sources’ claims at the position', 'The lexicon link between their two narrator records'],
    measured: {
      summary: 'At mentions both sources claim, the pairing is mutual for 93.7 % (90,295 of 96,331).',
      sample: '96,331 Sunni mentions, measured by code (a floor).',
      where: 'datasets/hadith-data/diagnostics/source-identity/README.md',
    },
    failureModes: ['Both sources inherit one upstream error'],
    readerLabel: 'AI-reviewed (checked by rule): two sources agree',
    sources: ['K6I', 'HKG'],
    code: ['datasets/hadith-data/reconciled/build_external_identity_sidecars.py'],
    covers: [],
    glossary: ['basis'],
  },
  {
    kind: 'rule',
    id: 'identity-external-source-claims',
    version: '2026.11.21',
    claimKind: 'identity',
    title: 'hadith-kg and Riwayat identifications',
    status: 'in_progress',
    rule:
      'A dataset’s narrator id is that dataset’s claim, carried onto our chain only at positions the Arabic corroborates. Riwayat’s automatic linking never counts toward AI-reviewed.',
    evidence: ['The dataset’s chain for the matched report', 'Our chain’s aligned positions', 'The dataset’s own names'],
    measured: {
      summary: 'Imami mentions read against the Arabic: 51 plainly right, 8 plausible, 1 wrong.',
      sample: '60 mentions, one reader (a machine reading, not a reviewer decision).',
      where: 'datasets/hadith-data/diagnostics/source-identity/imami_sample_60_judgement.csv',
    },
    failureModes: ['Thaqalayn labels identify a written label more often than a person (أحمد بن محمد)', 'Riwayat position shifts'],
    readerLabel: 'Source claim (hadith-kg or Riwayat; not AI-reviewed until loaded under this rule)',
    sources: ['HKG', 'RWY', 'THQ'],
    code: ['datasets/hadith-data/reconciled/external_source_logic.py'],
    covers: [
      'mention_candidate_basis.source_hadith_kg',
      'mention_candidate_basis.source_hadith_kg_confirmed_by_text',
      'mention_candidate_basis.source_riwayat',
      'mention_candidate_basis.source_riwayat_confirmed_by_text',
    ],
    glossary: ['source-index'],
  },
];

// ── Correspondence ─────────────────────────────────────────────────────────────────────────────────────────────────

const CORRESPONDENCE: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'correspondence-textual-overlap',
    version: 'report-correspondence-v1',
    claimKind: 'correspondence',
    title: 'Shared wording between two report texts',
    status: 'in_use',
    rule:
      'With the chains set aside, two texts share enough five-letter sequences to be shown as tellings of one report: same wording at 80 % shared, variant wording at 40 % or more, or a passage covering 70 % or more of the shorter text. Texts under eight words are not compared.',
    evidence: ['Both report texts, each bound by its SHA-256', 'The matn of each, isolated from its chain'],
    measured: {
      summary:
        'Pairs read as plainly the same report: same wording 24 of 24; variant wording at 40 % or more 45 of 48; shared passage at 70 % or more 35 of 40. Recall against exact scoring: 77 % overall, 100 % for same wording.',
      sample: '150 pairs read by the job’s author (one reader, not a reviewer); recall on 450 reports scored exactly.',
      where: 'datasets/hadith-data/diagnostics/report-correspondence/README.md §Precision, §Recall',
    },
    failureModes: [
      'A shared formula carries the overlap: the shahada, the tahlil, a Qur’an verse, the frame ثلاثة لا يكلمهم الله with different triads',
      'The same ruling attributed to different speakers',
      'Short sayings are missed (under eight words)',
    ],
    readerLabel: 'AI-reviewed (checked by rule): shared wording',
    sources: ['SWI'],
    code: [
      'datasets/hadith-data/diagnostics/report-correspondence/correspondence_logic.py',
      'datasets/hadith-data/diagnostics/report-correspondence/matn_isolation.py',
    ],
    covers: [
      'report_correspondence_basis.textual_overlap',
      'report_correspondence_class.same_wording',
      'report_correspondence_class.same_report_variant_wording',
      'report_correspondence_class.partial_overlap',
    ],
    glossary: ['report-correspondence', 'same-wording', 'variant-wording', 'shared-passage'],
  },
  {
    kind: 'rule',
    id: 'correspondence-textual-overlap-v2',
    version: 'report-correspondence-v2',
    claimKind: 'correspondence',
    title: 'Shared wording after removing formulas (second version)',
    status: 'in_progress',
    rule:
      'As the first version, after cutting compiler remarks and setting aside formula spans and Qur’an quotations; short sayings match only when nearly identical, and a short saying quoted inside a longer report is its own class.',
    evidence: ['Both report texts', 'A formula inventory built from the whole corpus', 'The Qur’an text (Tanzil)'],
    measured: null,
    unmeasured: 'In progress; no precision reading yet.',
    failureModes: ['Not yet known'],
    readerLabel: 'AI-reviewed (checked by rule): shared wording',
    sources: ['SWI'],
    code: ['datasets/hadith-data/diagnostics/report-correspondence-v2/correspondence_logic_v2.py'],
    covers: [],
    glossary: ['report-correspondence', 'shared-formula-only'],
  },
];

// ── Translation ────────────────────────────────────────────────────────────────────────────────────────────────────

const TRANSLATION: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'translation-machine-qa-screen',
    version: 'screen-v2',
    claimKind: 'translation',
    title: 'Machine translation with a quality screen',
    status: 'in_use',
    rule:
      'The pinned model translates the Arabic only; the output is kept only if it passes the screen: not blank, not a refusal or placeholder, no Arabic letters left, at least 80 % Latin letters, a plausible length against the Arabic, no repetition loop, and a normal finish.',
    evidence: ['The Arabic text, bound by its SHA-256', 'The model’s output and the provider’s run record'],
    measured: {
      summary:
        '7 of 58 outputs read against their Arabic had a meaning-level error (12 %, about one in eight), in line with the first pilot’s one in seven; four of the seven read a common noun as a proper name.',
      sample: '58 outputs drawn at random by work and length, one reader (the lane’s agent); not a reviewed measurement.',
      where: 'datasets/hadith-data/diagnostics/translation-run-2/README.md §Reading of 58 outputs',
    },
    failureModes: ['A changed meaning in fluent English (a gift rendered as an oath)', 'A speaker dropped or added', 'Name spellings drift between rows'],
    readerLabel: 'Unreviewed machine translation (model named); the screen checks form, not meaning',
    excluded: ['Source-provided English is the source’s own and is credited to its translator; it is not AI-reviewed'],
    sources: ['SWI'],
    code: ['datasets/hadith-data/generate_hy_mt2_candidates.py', 'datasets/hadith-data/translation_model.json'],
    covers: ['translation_state.machine_unreviewed'],
    glossary: ['machine-proposed', 'unreviewed'],
  },
];

// ── Gradings ───────────────────────────────────────────────────────────────────────────────────────────────────────

const GRADING: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'grading-attribution',
    version: '2026.11.21',
    claimKind: 'grading',
    title: 'Grading attributed to a named scholar',
    status: 'in_use',
    rule:
      'A grade is shown only as one scholar’s ruling within one tradition, in the scholar’s words, with the work, volume and page the source records. Entries that are not rulings (“he did not include it”, “he was silent on it”, back-references) are excluded. No grade is computed, mapped to another scale or combined.',
    evidence: ['The grading entry as the source records it', 'The grader’s name and the cited work and locator'],
    measured: {
      summary: 'Every one of 16,835 Imami grading entries parsed into grader, term and locator (0 failures); 1,813 non-rulings excluded.',
      sample: 'All entries, by code. The attribution itself has not been checked against the cited works.',
      where: 'datasets/hadith-data/diagnostics/grading/README.md; datasets/hadith-data/diagnostics/grading-recovery/README.md',
    },
    failureModes: ['A ruling about a different chain of the same report', 'Spelling variants of one term counted as different terms'],
    readerLabel: 'Attributed ruling (as the source records it); AI-reviewed means the attribution was parsed, not that the ruling was checked in the work',
    sources: ['THQ'],
    code: ['datasets/hadith-data/diagnostics/grading-recovery/build_hadith_assessment_rows.py'],
    covers: ['assessment_kind.cited_ruling'],
    glossary: ['assessment', 'imami-grading'],
  },
  {
    kind: 'rule',
    id: 'grading-compiler-statement',
    version: '2026.11.21',
    claimKind: 'grading',
    title: 'A compiler’s own statement in the text',
    status: 'in_progress',
    rule:
      'A grade term that follows the compiler’s own speaker phrase (قال أبو عيسى in al-Tirmidhi) is quoted with its exact character span in the Arabic. Statements where another authority is quoted, or no grade term appears, are held back.',
    evidence: ['The Arabic text with the statement’s character span'],
    measured: null,
    unmeasured: 'Not measured; 2,707 statements found and 785 held back, every one awaiting review.',
    failureModes: ['A quoted authority mistaken for the compiler'],
    readerLabel: 'Compiler’s statement (quoted from the text)',
    sources: ['SUN'],
    code: ['datasets/hadith-data/diagnostics/extract_tirmidhi_compiler_statements.py'],
    covers: ['assessment_kind.compiler_statement'],
    glossary: ['compiler-statement'],
  },
  {
    kind: 'rule',
    id: 'grading-compiler-criterion',
    version: '2026.11.21',
    claimKind: 'grading',
    title: 'A collection’s criterion, not a grade',
    status: 'in_progress',
    rule: 'A report in a collection whose compiler set a standard for the whole work is linked to that standard, never given a grade of its own.',
    evidence: ['The work the report belongs to'],
    measured: null,
    unmeasured: 'Nothing to measure: membership in the work decides it. The criterion text itself still needs a citation.',
    failureModes: ['None in the link; the criterion’s wording needs a cited source'],
    readerLabel: 'The collection’s criterion (not a grade of this report)',
    sources: ['SWI'],
    code: ['datasets/hadith-data/diagnostics/grading-recovery/build_hadith_assessment_rows.py'],
    covers: ['assessment_kind.compiler_criterion'],
    glossary: ['compiler-criterion'],
  },
  {
    kind: 'rule',
    id: 'grading-collection-label-excluded',
    version: '2026.11.21',
    claimKind: 'grading',
    title: 'Collection-wide labels are never grades',
    status: 'in_use',
    rule: 'A label an upstream dataset put on every row of a collection (ثابت on all 29,915 rows of four works) is kept for the record and never shown as a grade.',
    evidence: ['The label’s distribution across the dataset'],
    measured: {
      summary: 'The label has one value on all 100,217 upstream rows, including both Sahihs, so it carries no per-report information.',
      sample: 'All rows, by code.',
      where: 'datasets/hadith-data/diagnostics/grading/README.md (J6c)',
    },
    failureModes: ['None'],
    readerLabel: 'Not shown as a grade',
    sources: ['NMC'],
    code: ['datasets/hadith-data/diagnostics/audit_pure_canon_ruling_label.py'],
    covers: ['assessment_kind.collection_label'],
    glossary: ['collection-label', 'thabit'],
  },
];

// ── Biography and rijal ────────────────────────────────────────────────────────────────────────────────────────────

const BIOGRAPHY: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'biography-lexicon-not-yet-cited',
    version: '2026.11.21',
    claimKind: 'biography',
    title: 'Narrator lexicon values, compared with Taqrib',
    status: 'in_use',
    rule:
      'Dates, places and generations from the narrator lexicon are shown labelled “narrator lexicon, not yet cited”. Where the lexicon row links to an entry of Ibn Hajar’s Taqrib al-Tahdhib, the two are compared; the 61 values that conflict are held back until reviewed.',
    evidence: ['The lexicon row', 'The linked Taqrib entry’s verbatim passage, entry number and page'],
    measured: {
      summary:
        'Death years agree or are consistent with Taqrib for 1,588 of 1,663 linked narrators that both date (95.5 %); generation 5,128 of 5,194 (98.7 %); places 3,195 agree, 20 differ. The lexicon was very likely compiled from Taqrib-family works, so agreement mostly confirms faithful copying.',
      sample: 'All 5,404 Taqrib-linked lexicon rows, by code.',
      where: 'datasets/hadith-data/diagnostics/biography-verification/README.md',
    },
    failureModes: ['Digit slips in the lexicon', 'Typos in the digital Taqrib (ست عسرة for ست عشرة)', 'Century omitted by Ibn Hajar and read by his rule'],
    readerLabel: 'Narrator lexicon, not yet cited',
    sources: ['MSD', 'RIJ'],
    code: ['datasets/hadith-data/diagnostics/biography-verification/verify_lexicon_against_rijal.py'],
    covers: ['evidence_review_state.lexicon_unverified'],
    glossary: ['unreviewed', 'rijal'],
  },
  {
    kind: 'rule',
    id: 'biography-cited-rijal-passage',
    version: '2026.11.21',
    claimKind: 'biography',
    title: 'A value cited to a rijal passage',
    status: 'in_progress',
    rule:
      'A biographical value is cited when it is read from a verbatim passage of a named rijal work, with the author, edition, entry number and page, and attributed to that author within that author’s tradition. Several authors’ values are kept side by side, never merged.',
    evidence: ['The verbatim passage with entry and page', 'The edition as its file header names it'],
    measured: null,
    unmeasured: 'A 100-row spot-check worksheet is drawn but not yet read.',
    failureModes: ['A link to the wrong entry where two men share a name'],
    readerLabel: 'Cited: <author>, <work>, entry <n>, vol. <v> p. <p>',
    sources: ['RIJ'],
    code: ['datasets/hadith-data/diagnostics/biography-verification/rijal_parsing.py', 'datasets/hadith-data/rijal/rijal_extract.py'],
    covers: ['evidence_review_state.candidate_only', 'evidence_review_state.source_verified'],
    glossary: ['citation', 'rijal'],
  },
];

// ── History, Qur'an, numbering ─────────────────────────────────────────────────────────────────────────────────────

const HISTORY: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'history-cited-passage',
    version: '2026.11.21',
    claimKind: 'history',
    title: 'An event or era date stated by a cited passage',
    status: 'in_progress',
    rule:
      'A date is shown as AI-reviewed only when its citation is complete (book, author, printed edition, volume and page or entry, the exact Arabic passage, its position in the digital file and the file’s SHA-256) and the passage itself states the year, or the year heading it sits under in an annal does. An age, a duration, a reckoning such as the Year of the Elephant, or a missing century keeps the citation but not the label. When books differ, each date is its own cited claim; none is chosen. No language model is used.',
    evidence: ['The cited passage from a chronicle or rijal work (Khalifa b. Khayyat, al-Tabari and others, from OpenITI) with its locator and file hash'],
    measured: {
      summary:
        '182 date claims, all cited: 163 pass, 19 fail (15 century not written, 4 not stated as a year). 171 citations re-read from their spans with 0 failures. Of the 54 seeded events, 29 are supported by a cited passage, 2 are contradicted by it.',
      sample: 'Every claim, by code. Not yet read by a person.',
      where: 'datasets/hadith-data/history/README.md §Results',
    },
    failureModes: ['A date stated for a different event in the same year', 'A narrator’s presence reported only as “it is said”'],
    readerLabel: 'AI-reviewed (checked by rule), source cited',
    sources: ['OITI', 'SWI'],
    code: ['datasets/hadith-data/history/history_text.py', 'datasets/hadith-data/history/validate_citations.py'],
    covers: ['event_verification.unverified', 'event_verification.unverified_seed', 'event_verification.source_verified'],
    glossary: ['unverified-seed', 'era'],
  },
];

const QURAN: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'quran-citation-letter-match',
    version: '2026.11.21',
    claimKind: 'quran_citation',
    title: 'Qur’an quotation found by exact letter match',
    status: 'in_progress',
    rule:
      'A span of the report is a Qur’an quotation when its letters, after folding spelling differences between the Uthmani and plain scripts, match a verse exactly; the span is recorded by character offsets in the stored text and bound by its hash. Short common phrases and formulas are kept apart from citations.',
    evidence: ['The report text', 'The Tanzil Qur’an text, Simple Clean and Uthmani'],
    measured: {
      summary:
        'Spans classed as citations were real quotations in 51 of 54 read (94 %). Of hadith-kg’s own quotations that can be located, 1,206 of 1,262 (95.6 %) are found whole.',
      sample: '80 matches read by one reader (not a scholar); recall measured by code against hadith-kg on Sunni reports.',
      where: 'datasets/hadith-data/quran/README.md §Reading of 80 matches, §Validation',
    },
    failureModes: ['A common phrase that also occurs in the Qur’an', 'Short cued quotations of four words'],
    readerLabel: 'Qur’an citation (checked by rule)',
    sources: ['SWI', 'HKG'],
    code: ['datasets/hadith-data/quran/quran_logic.py'],
    covers: [],
    glossary: ['citation'],
  },
];

const NUMBERING: readonly RuleProcedure[] = [
  {
    kind: 'rule',
    id: 'numbering-source-scheme',
    version: '2026.11.21',
    claimKind: 'numbering',
    title: 'Report numbers in each source’s own scheme',
    status: 'in_progress',
    rule:
      'Each report is referred to in its provider’s own numbering; a number cell that is a marker, a grade word or empty is not read as a number, and every irregularity is flagged rather than repaired.',
    evidence: ['The provider’s number cell and URL'],
    measured: null,
    unmeasured: 'Not measured.',
    failureModes: ['Numbering that restarts per chapter (al-Kafi)'],
    readerLabel: 'Number as the source gives it',
    sources: ['SUN', 'THQ', 'OITI', 'NMC'],
    code: ['datasets/hadith-data/reconciled/structure/structure_logic.py', 'src/lib/citation/reference.ts'],
    covers: [],
    glossary: ['source-work', 'edition'],
  },
];

// ── Specialists ────────────────────────────────────────────────────────────────────────────────────────────────────

export const SPECIALISTS: readonly Specialist[] = [
  {
    kind: 'specialist',
    id: 'isnad-identity',
    version: '1.0.0',
    claimKinds: ['identity'],
    title: 'Isnad identity reviewer',
    status: 'pilot_ready',
    question: 'Is this name, at this position of this chain, this person?',
    prompt: 'reviews/ai/prompts/isnad-identity.md',
    packet: ['The Arabic text and the chain as written', 'The target position with its neighbours', 'Candidates in a neutral order, each with who asserts it', 'Rijal passages with locators where linked', 'Glossary definitions'],
    recommendedModel: 'claude-opus-5-5',
    modelReason: 'Rijal reasoning over classical Arabic; Fable 5.2 only for contested names and the Imams’ kunyas.',
    notThisModel: ['Any model that produced the candidate (Riwayat’s automatic linking used Claude labels: review those with a non-Claude model or flag the overlap)'],
    measured: null,
    unmeasured: 'Pilot not yet run.',
  },
  {
    kind: 'specialist',
    id: 'correspondence',
    version: '1.0.0',
    claimKinds: ['correspondence'],
    title: 'Report correspondence reviewer',
    status: 'pilot_ready',
    question: 'Are these two texts tellings of the same report, a shared passage, a shared formula or verse, the same ruling from another speaker, or unrelated?',
    prompt: 'reviews/ai/prompts/correspondence.md',
    packet: ['Both texts in full, labelled A and B in a neutral order', 'Their locators, for citing only', 'Glossary definitions'],
    recommendedModel: 'claude-opus-5-5',
    modelReason: 'Close reading of classical Arabic wording; volume is handled by sampling, not a weaker model.',
    notThisModel: [],
    measured: null,
    unmeasured: 'Pilot not yet run.',
  },
  {
    kind: 'specialist',
    id: 'translation',
    version: '1.0.0',
    claimKinds: ['translation'],
    title: 'Translation reviewer',
    status: 'prompt_written',
    question: 'Does the English say what the Arabic says? List every meaning error.',
    prompt: 'reviews/ai/prompts/translation.md',
    packet: ['The Arabic text', 'The English to review', 'The transliteration note and glossary terms'],
    recommendedModel: 'claude-opus-5-5',
    modelReason: 'Independent of the translators; strong on classical Arabic.',
    notThisModel: ['tencent/hy-mt2-30b-a3b (the pinned translator)', 'google/gemini-2.5-flash for its own candidates'],
    measured: null,
    unmeasured: 'Not yet run.',
  },
  {
    kind: 'specialist',
    id: 'grading-attribution',
    version: '1.0.0',
    claimKinds: ['grading', 'narrator_verdict'],
    title: 'Grading attribution reviewer',
    status: 'prompt_written',
    question: 'Does the passage state this ruling, by this scholar, about this report or narrator?',
    prompt: 'reviews/ai/prompts/grading-attribution.md',
    packet: ['The report or narrator', 'The claimed ruling, grader and locator', 'The cited passage verbatim'],
    recommendedModel: 'claude-opus-5-5',
    modelReason: 'Attribution errors are consequential; the passages are short, so cost is low.',
    notThisModel: [],
    measured: null,
    unmeasured: 'Not yet run.',
  },
  {
    kind: 'specialist',
    id: 'history-claim',
    version: '1.0.0',
    claimKinds: ['history'],
    title: 'History claim reviewer',
    status: 'prompt_written',
    question: 'Does the cited passage state this date, place or event?',
    prompt: 'reviews/ai/prompts/history-claim.md',
    packet: ['The claim', 'The cited passages with locators', 'The Hijri calendar note'],
    recommendedModel: 'claude-fable-5-2',
    modelReason: 'Few items (92) and chronicle Arabic is hard; the strongest model costs little here.',
    notThisModel: [],
    measured: null,
    unmeasured: 'Not yet run.',
  },
  {
    kind: 'specialist',
    id: 'rijal-link',
    version: '1.0.0',
    claimKinds: ['rijal_link', 'biography'],
    title: 'Rijal link reviewer',
    status: 'prompt_written',
    question: 'Is this rijal entry about this narrator?',
    prompt: 'reviews/ai/prompts/rijal-link.md',
    packet: ['The narrator’s recorded names, teachers and students', 'The rijal entry verbatim with its locator', 'Other entries with the same headword'],
    recommendedModel: 'claude-opus-5-5',
    modelReason: 'Homonym resolution in rijal works.',
    notThisModel: [],
    measured: null,
    unmeasured: 'Not yet run.',
  },
];

export const METHOD_SECTIONS: readonly MethodSection[] = [
  {
    id: 'identity',
    title: 'Who a name in a chain refers to',
    claimKinds: ['identity'],
    intro: 'Every candidate identity for a name is kept with its basis. Where sources disagree, all are shown and none is preferred.',
    procedures: IDENTITY,
    specialistIds: ['isnad-identity'],
  },
  {
    id: 'correspondence',
    title: 'Tellings of the same report',
    claimKinds: ['correspondence'],
    intro: 'Reports are linked, never narrators or chains. A link is evidence that two texts correspond, not a ruling that they are one hadith.',
    procedures: CORRESPONDENCE,
    specialistIds: ['correspondence'],
  },
  {
    id: 'translation',
    title: 'English translations',
    claimKinds: ['translation'],
    intro: 'English supplied by a source is credited to its translator. English made here is a machine translation, labelled with the model.',
    procedures: TRANSLATION,
    specialistIds: ['translation'],
  },
  {
    id: 'grading',
    title: 'Gradings and verdicts',
    claimKinds: ['grading', 'narrator_verdict'],
    intro: 'A grade is always one scholar’s ruling within one tradition. The archive computes no grade.',
    procedures: GRADING,
    specialistIds: ['grading-attribution'],
  },
  {
    id: 'biography',
    title: 'Narrator dates, places and rijal entries',
    claimKinds: ['biography', 'rijal_link'],
    intro: 'Each rijal author’s entry is kept under that author and work; a narrator may have many.',
    procedures: BIOGRAPHY,
    specialistIds: ['rijal-link'],
  },
  {
    id: 'history',
    title: 'Events and eras',
    claimKinds: ['history'],
    intro: 'Nothing historical is published without a cited passage.',
    procedures: HISTORY,
    specialistIds: ['history-claim'],
  },
  {
    id: 'quran',
    title: 'Qur’an citations',
    claimKinds: ['quran_citation'],
    intro: 'Verse text and numbering come from the Tanzil Qur’an text.',
    procedures: QURAN,
    specialistIds: [],
  },
  {
    id: 'numbering',
    title: 'Report numbers and editions',
    claimKinds: ['numbering'],
    intro: 'Each provider is referred to in its own scheme.',
    procedures: NUMBERING,
    specialistIds: [],
  },
];

/**
 * Review-bearing enum values that are deliberately not an AI review, each with its reason.
 * Every other value of the enums in REVIEW_BEARING_ENUMS must be covered by a procedure (checked by the test).
 */
export const NOT_AI_REVIEWED: Readonly<Record<EnumValueReference, string>> = {
  'mention_candidate_basis.reviewer_decision': 'A person’s decision: shown as a human review, never as AI-reviewed.',
  'translation_state.human_verified': 'A person’s review of the English.',
  'translation_state.source_verified': 'Checked against a printed translation by a person; none are loaded.',
  'translation_state.source_provided': 'The source’s own English, credited to its translator; not reviewed here.',
  'translation_state.unknown_provenance': 'Never shown: it cannot be credited.',
  'evidence_review_state.source_provided': 'Supplied with the source data and credited to it.',
  'evidence_review_state.human_verified': 'A person’s review.',
  'event_verification.human_verified': 'A person’s review.',
};

/** The enums whose values say how a claim was checked. */
export const REVIEW_BEARING_ENUMS = [
  'mention_candidate_basis',
  'report_correspondence_basis',
  'report_correspondence_class',
  'translation_state',
  'assessment_kind',
  'evidence_review_state',
  'event_verification',
] as const;

export function allProcedures(): RuleProcedure[] {
  return METHOD_SECTIONS.flatMap((section) => section.procedures);
}

export function specialistById(id: string): Specialist | undefined {
  return SPECIALISTS.find((specialist) => specialist.id === id);
}

/** Link target for a reader-facing AI-review label. */
export function methodHref(id: string): string {
  return `/method#${id}`;
}

export const STATUS_LABEL: Readonly<Record<ProcedureStatus | Specialist['status'], string>> = {
  in_use: 'In use',
  adopted_not_loaded: 'Adopted, not yet loaded',
  in_progress: 'In progress',
  planned: 'Planned',
  prompt_written: 'Prompt written, not yet run',
  pilot_ready: 'Ready for its pilot',
};
