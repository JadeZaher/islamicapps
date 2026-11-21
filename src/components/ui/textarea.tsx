import * as React from "react"

import { cn } from "@/lib/utils"

/** Multi-line field; same rules as Input (DESIGN.md §Filters and forms). */
function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex field-sizing-content min-h-16 w-full rounded-none border border-control bg-surface px-3 py-2 text-base text-ink placeholder:text-ink-muted transition-colors duration-[var(--motion-fast)] focus-visible:border-focus focus-visible:outline-offset-0 aria-invalid:border-danger aria-invalid:shadow-[inset_0_-2px_0_var(--color-danger)] disabled:cursor-not-allowed disabled:border-rule disabled:text-ink-muted",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
