import Link from 'next/link';

import { ArabicText } from '@/components/ArabicText';
import { SourceCredit } from '@/components/archive/SourceCredit';
import { NameBasisMark, NAME_LATIN_BASIS_LABEL } from '@/components/marks';
import type { NarratorLinkCandidate, NarratorSourceRecord } from '@/db/queries/narrator-sources';
import { sourceForNarratorAuthority } from '@/lib/sources/registry';

const SOURCE_TITLE: Record<string, string> = {
  hadith_kg: 'Record in hadith-kg',
  riwayat: 'Record in the Riwayat corpus',
  imam_register: 'Record in the Imam register',
};

/** Why an id names a label rather than a person, in words (narrator_source_profiles.label_reason). */
const LABEL_REASON: Record<string, string> = {
  name_held_by_several_ids: 'the same name is held by several of its ids, so it is a name several men share',
  nasab_only_label: 'it is a family name alone (ibn …), which several men share',
  'riwayat_flag:merged_names_suspect': 'the source itself flags this record as merging different names',
  'riwayat_flag:compound_source_name': 'the source itself flags this record as a compound of names',
  'riwayat_flag:junk_name': 'the source itself flags this name as malformed',
  'placeholder:kunya_only_name': 'it is a kunya alone, which several men share',
  'placeholder:bare_single_token_name': 'it is a single word',
  'placeholder:collective_or_anonymous_name': 'it names a group or an unnamed person',
  'placeholder:relational_name': 'it names a relation (his father, his grandfather)',
};

/** Field names as the source writes them, in words; anything else is shown with its own key. */
const FIELD: Record<string, string> = {
  tabaqa: 'Generation (tabaqa)',
  tabaka: 'Generation (tabaqa)',
  death_year: 'Death year',
  death_year_raw: 'Death year (as written)',
  birth_year: 'Birth year',
  birth_year_raw: 'Birth year (as written)',
  city: 'City',
  death_city: 'Died in',
  death_place: 'Died in',
  residence: 'Residence',
  nasab: 'Nasab',
  tribe_nisba: 'Tribe or nisba',
  family: 'Family',
  profession: 'Profession',
  age: 'Age',
  is_stub: 'Stub record',
  riwaya_qty: 'Reports in the source',
  n_sources: 'Sources the record draws on',
  popular_name_ar: 'Popular name',
  known_as: 'Known as',
  ordinal: 'Imam',
  kunyas: 'Kunyas in the register',
  tradition_label: 'Tradition label (the source’s)',
};

/** Riwayat's name-form sources (its crosswalk namespaces), in words. */
const FORM_SOURCE: Record<string, string> = {
  thq: 'Thaqalayn',
  sh: 'SemanticHadith',
  itq: 'Itqan',
  kg: 'hadith-kg',
  chains_new: 'Riwayat, from a chain',
  mids: 'Muslim Scholars Database',
};

function LinkCandidates({ title, links }: { title: string; links: NarratorLinkCandidate[] }) {
  if (links.length === 0) return null;
  return (
    <div className="mt-6">
      <h3 className="type-small font-semibold text-ink">{title}</h3>
      <ul className="mt-1 space-y-1 type-small">
        {links.map((link) => (
          <li key={link.narrator_id}>
            <Link href={`/narrator/${encodeURIComponent(link.narrator_id)}`} className="link-row text-ink">
              {link.name}
            </Link>
            {link.name_ar && !link.name.includes(link.name_ar) && (
              <bdi lang="ar" dir="rtl" className="ms-2 font-arabic text-[1.0625rem] text-ink-muted">
                {link.name_ar}
              </bdi>
            )}
            <span className="text-ink-muted"> · candidate ({link.basis.replaceAll('_', ' ')}), not reviewed</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * What an external source (or the Imam register) records about this narrator, as that source gives it, credited, with a
 * plain notice when the source's id names a label rather than an established person. Verdict-like fields are never
 * shown (G-1). See src/db/AGENTS.md §External identity.
 */
export function SourceRecord({ record }: { record: NarratorSourceRecord }) {
  const code = sourceForNarratorAuthority(record.authority);
  const labelReason = record.label_reason ? LABEL_REASON[record.label_reason] ?? record.label_reason : null;
  return (
    <section aria-labelledby="source-record-heading" className="mb-12 max-w-[var(--measure-wide)]" data-source-record={record.authority}>
      <h2 id="source-record-heading" className="section-rule type-label mb-3">
        {SOURCE_TITLE[record.authority] ?? 'Source record'}
      </h2>
      {labelReason && (
        <p className="mb-4 border-s-2 border-ink ps-3 type-small text-ink" data-label-notice>
          This id names a label as written in chains, not an established person: {labelReason}. Reports listed here may
          concern different men.
        </p>
      )}
      <dl className="grid grid-cols-[10rem_minmax(0,1fr)] gap-x-4 gap-y-2 type-small">
        <dt className="text-ink-muted">Name as the source gives it</dt>
        <dd className="min-w-0">
          {record.name_ar && <ArabicText as="span" variant="inline" className="block text-ink">{record.name_ar}</ArabicText>}
          {record.name_latin && (
            <span className="block text-ink">
              {record.name_latin}
              {record.name_latin_basis && record.authority !== 'imam_register' && (
                <span className="ms-2 inline-flex items-center gap-1 text-xs text-ink-muted">
                  <NameBasisMark basis={record.name_latin_basis} decorative />
                  {NAME_LATIN_BASIS_LABEL[record.name_latin_basis]}
                </span>
              )}
            </span>
          )}
        </dd>
        <dt className="text-ink-muted">Id in the source</dt>
        <dd className="font-mono text-ink">{record.source_key}</dd>
        {record.assertions.map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-ink-muted">{FIELD[key] ?? key.replaceAll('_', ' ')}</dt>
            <dd className="min-w-0 text-ink [overflow-wrap:anywhere]" dir="auto">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 type-small text-ink-muted">
        As the source records it, not checked here. {record.asserted_by}.
      </p>

      {record.name_forms.length > 0 && (
        <div className="mt-6">
          <h3 className="type-small font-semibold text-ink">Name forms the source lists</h3>
          <ul className="mt-1 space-y-1 type-small">
            {record.name_forms.map((form, index) => (
              <li key={`${form.form}-${index}`} className="flex flex-wrap items-baseline gap-x-2">
                <ArabicText as="span" variant="inline" className="text-ink">{form.form}</ArabicText>
                <span className="text-ink-muted">{form.type} · {FORM_SOURCE[form.source] ?? form.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {record.external_ids.length > 0 && (
        <div className="mt-6">
          <h3 className="type-small font-semibold text-ink">Ids in other datasets (the source’s crosswalk)</h3>
          <p className="mt-1 type-small text-ink-muted">
            {record.external_ids.map((item, index) => (
              <span key={`${item.namespace}:${item.external_id}`}>
                {index > 0 && ', '}
                {FORM_SOURCE[item.namespace] ?? item.namespace}{' '}
                {item.narrator_id ? (
                  <Link href={`/narrator/${encodeURIComponent(item.narrator_id)}`} className="link-row font-mono">
                    {item.external_id}
                  </Link>
                ) : (
                  <span className="font-mono">{item.external_id}</span>
                )}
              </span>
            ))}
          </p>
        </div>
      )}

      <LinkCandidates title="Possibly the same person in the narrator lexicon" links={record.link_candidates} />

      <SourceCredit code={code} role="Narrator record" detail={record.licence} className="mt-6" />
      {record.authority === 'riwayat' && record.name_source === 'thq' && (
        <SourceCredit code="THQ" role="Name" detail="Thaqalayn's narrator label, re-keyed to this edition" />
      )}
    </section>
  );
}

/** On a lexicon narrator's page: external records a link candidate proposes as the same person. */
export function ExternalCandidates({ links }: { links: NarratorLinkCandidate[] }) {
  if (links.length === 0) return null;
  return (
    <section aria-labelledby="external-records-heading" className="mb-12 max-w-[var(--measure-wide)]">
      <h2 id="external-records-heading" className="section-rule type-label mb-3">
        Records in other sources
      </h2>
      <LinkCandidates title="Possibly the same person (machine-proposed, not reviewed)" links={links} />
      {[...new Set(links.map((link) => sourceForNarratorAuthority(link.authority)))].map((code) => (
        <SourceCredit key={code} code={code} role="Narrator record" className="mt-2" />
      ))}
    </section>
  );
}
