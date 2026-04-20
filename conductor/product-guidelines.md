# Product Guidelines

## Design Philosophy

**Scholarly dignity over mass-market aesthetics.** The visual design should communicate seriousness, depth, and respect for the subject matter. Think reference library, not social app.

## Brand Voice & Tone

- **Precise**: Use correct Islamic terminology (isnad, matn, tabaqah, rijal, etc.) without dumbing it down — link to explanations instead
- **Neutral on contested matters**: Present scholarly positions without editorializing; show *that* scholars disagree and *why*, not which side is "correct"
- **Accessible but not patronizing**: Write for a serious Muslim who may not have formal seminary training, not for a PhD, and not for someone who needs everything explained from scratch
- **No clickbait, no sensationalism**: Especially important given the sensitivity of comparative religion topics

## UI/UX Standards

- **Dark theme**: Deep slate/purple gradient — scholarly, low-eyestrain for long reading sessions
- **Arabic text**: Always render Arabic in `font-arabic` class, right-to-left, at readable size. Never truncate Arabic text.
- **Color semantics** (consistent throughout):
  - Green: authentic / SAHIH / THIQA / trustworthy
  - Amber/Yellow: caution / HASAN / cultural crossover
  - Orange: weak / DAIF
  - Red: fabricated / MAWDU / KADHAB / condemnation parallels
  - Purple: primary UI accent, navigation
  - Sky blue: Christianity tradition
  - Amber: Judaism tradition
  - Orange: Zoroastrianism tradition
- **Graph visualizations**: Use @xyflow/react for structured isnad chains; react-force-graph-2d for network exploration
- **No external map libraries**: Use structured tables/text for geographic data — avoids dependency bloat

## Content Guidelines

- **Isra'iliyyat / comparative parallels**: Always present with scholarly framing. Never imply a hadith is "fake" because it has a parallel — note that Muwafiq parallels are acceptable to narrate per classical scholars.
- **Narrator criticism**: Source all reliability verdicts. The dual grading system (auto-calculated + scholar verdict) must be transparent about its reasoning.
- **Citations**: All commentary must cite source work and author. No unsourced editorial content.

## Technical Standards

- Next.js App Router patterns only (no Pages Router)
- Server Actions for all mutations — no separate REST/GraphQL layer
- All Neo4j queries in dedicated action files (`*-actions.ts`)
- Shared UI components in `src/components/`
- No test suite required at this stage — prioritize feature completeness
- Manual commits only — developer controls git history
