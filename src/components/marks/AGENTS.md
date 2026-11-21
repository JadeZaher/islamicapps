# Marks

Flat geometric SVG primitives of the design system. The rules (shapes, sizes, meanings, when a mark may stand
without text) live in `DESIGN.md` at the repository root, §Marks; change the drawing and that section together.

- Every mark draws in `currentColor`, has no shadow, gradient or rounded corner, and carries a default
  accessible title. Pass `decorative` only when visible text beside it says the same thing.
- A mark never replaces its words in running UI: tradition marks sit before the tradition name, basis marks
  before the basis label. Only diagram legends pair a mark with its words once and then use the mark alone.
- Marks are fixed glyphs and are not mirrored in right-to-left text. `ArrowIcon` is physical; swap direction at
  the call site for "back"/"next" in RTL.
- `IDENTITY_BASIS_LABEL` is the single copy of the basis wording; `IsnadChain.tsx` imports it.
- `TRADITION_DASH` is the single set of tradition line patterns; the family view's `labels.ts` derives from it.
- `ProductMark` is the header wordmark (proposed in DESIGN.md §Site header).
