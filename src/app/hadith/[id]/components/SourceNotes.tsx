import { ArabicText } from '@/components/ArabicText';
import { SourceCredit } from '@/components/archive/SourceCredit';
import type { SourceNote, SourceNoteKind } from '@/db/queries/contracts';

/** Who wrote each kind of note the OpenITI edition prints beside a report (src/db/AGENTS.md §OpenITI extraction fields). */
const KIND_LABEL: Record<SourceNoteKind, string> = {
  compiler_comment: "Compiler's remark",
  arranger_note: "Arranger's note",
  editor_footnote: "Editor's footnote",
  note: 'Note in the source edition',
};

/**
 * The notes the source edition prints with a report, labelled by author and credited once to OpenITI. Always its own
 * block below the text: a note is never part of the report, so it is never merged into the Arabic above.
 */
export function SourceNotes({ notes }: { notes: SourceNote[] }) {
  return (
    <div>
      <ul className="space-y-4">
        {notes.map((note, index) => (
          <li key={index}>
            <p className="mb-1 type-small text-ink-muted">{KIND_LABEL[note.kind]}</p>
            <ArabicText as="p" variant="reading" className="whitespace-pre-line text-ink">
              {note.text_ar}
            </ArabicText>
          </li>
        ))}
      </ul>
      <SourceCredit code="OITI" role="Notes" className="mt-3" />
    </div>
  );
}
