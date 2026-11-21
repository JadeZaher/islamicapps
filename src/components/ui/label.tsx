"use client"

import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"

import { cn } from "@/lib/utils"

/** Field label above its control: 14px, 600 (DESIGN.md §Filters and forms). */
function Label({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      className={cn(
        "flex items-center gap-2 text-sm leading-5 font-semibold text-ink select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:text-ink-muted peer-disabled:cursor-not-allowed peer-disabled:text-ink-muted",
        className
      )}
      {...props}
    />
  )
}

export { Label }
