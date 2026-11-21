import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** Buttons per DESIGN.md §Buttons and links: primary (accent fill), secondary (ink border), quiet (underlined text). Square, flat, 40px. */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-none border text-sm font-semibold leading-none no-underline transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)] disabled:cursor-not-allowed disabled:border-rule disabled:bg-transparent disabled:text-ink-muted [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 aria-invalid:border-danger",
  {
    variants: {
      variant: {
        default: "border-accent bg-accent text-on-accent hover:border-ink hover:bg-ink hover:text-paper",
        destructive: "border-danger bg-transparent text-danger hover:bg-danger hover:text-paper",
        outline: "border-ink bg-transparent text-ink hover:bg-ink hover:text-paper",
        secondary: "border-ink bg-transparent text-ink hover:bg-ink hover:text-paper",
        ghost: "border-transparent bg-transparent text-ink hover:bg-sunken",
        link: "border-transparent bg-transparent px-0 text-ink underline decoration-rule decoration-1 underline-offset-[0.2em] hover:decoration-accent",
      },
      size: {
        default: "h-10 px-4 has-[>svg]:px-3",
        sm: "h-10 gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-11 px-6 has-[>svg]:px-4",
        icon: "size-10",
        "icon-sm": "size-10",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
