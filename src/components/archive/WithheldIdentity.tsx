/** A machine-reviewed identity the chronology guard withheld; its candidate stays listed with this reason (src/db/AGENTS.md §Chain chronology guard). */
export function WithheldIdentity({ reason }: { reason: string }) {
  return (
    <p className="text-ink-muted" data-identity-withheld>
      Identity withheld. {reason.charAt(0).toUpperCase()}
      {reason.slice(1)}.
    </p>
  );
}
