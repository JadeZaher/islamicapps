import * as React from "react"

import { cn } from "@/lib/utils"

/** Text input per DESIGN.md §Filters and forms: 40px, 1px control border on surface, square; focus turns the border accent. */
function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-10 w-full min-w-0 rounded-none border border-control bg-surface px-3 py-2 text-base text-ink placeholder:text-ink-muted transition-colors duration-[var(--motion-fast)] file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:cursor-not-allowed disabled:border-rule disabled:text-ink-muted",
        "focus-visible:border-focus focus-visible:outline-offset-0",
        "aria-invalid:border-danger aria-invalid:shadow-[inset_0_-2px_0_var(--color-danger)]",
        className
      )}
      {...props}
    />
  )
}

export { Input }
