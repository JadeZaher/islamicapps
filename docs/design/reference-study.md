---
type: evidence
updated: 2026-11-21
---

# Reference study: Neos and Taawun

Evidence behind `DESIGN.md`. Measured on 2026-11-21 with headless Chrome 157 through Playwright, using computed styles
(not impressions), at 1440 x 900 and 390 x 844, with `prefers-color-scheme` set to light and to dark. Read-only:
no form was submitted and nothing was signed into.

Pages read: Neos `/`, `/practices`, `/about`, `/communities/<id>`; Taawun `/`, `/account` (the form was only rendered).
Two Neos loads failed on network time-outs and were retried; no measurement depends on a single load.

Note on italics: in some captures Neos `/about` and the Taawun navigation render oblique. `font-style` is
`normal` everywhere; those pages load no web font, so Chrome substituted a locally installed Inter face. Not a design
choice and not recorded as one.

## Facts

| | Neos (neos.primusneo.com) | Taawun (taawun-production.up.railway.app) |
| --- | --- | --- |
| Themes | Light and dark, follows the system (`html.light` / `html.dark`, `data-theme`, `color-scheme`) | Dark only; identical under both schemes |
| Latin faces | Inter 400–900 (Google Fonts) everywhere; JetBrains Mono 400–600 for kickers and footer links; Georgia for long prose on `/practices` | Home: Iowan Old Style (system serif, not loaded) for headings, Inter (system, not loaded) for body, SFMono for kickers. `/account`: Fraunces + IBM Plex Sans/Mono. The two pages do not agree |
| Display | 60px / 60 / 900 / -2.4px (1440); 36px / 40 / 900 at 390; `/about` 115px / 0.84 / 900 / -0.07em UPPERCASE | 94px / 0.93 / 500 / -0.05em serif with one italic accent word; 58.5px at 390 |
| Headings | h2 24 / 32 / 900 / -0.035em; h3 20 / 28 / 900 | h2 62 / 63 / 500; h3 21–24 / 1.2 / 500 serif |
| Body | 16 / 24 and 18 / 28–29 regular | 16 / 25.6 and 20 / 32 regular |
| Labels | 12 / 16 / 700 / +0.12em UPPERCASE (Inter) and 12 / 16 / 500 / +0.14em UPPERCASE (mono) | 11 / 15 / 600 / +0.13em UPPERCASE mono |
| Paper (light) | `#F2EDE3` (hsl 40 36.6% 92%) | (none) |
| Surface (light) | `#FFFDF8` cards | (none) |
| Ink (light) | `#15130F` | (none) |
| Muted (light) | `#5E584E` | (none) |
| Rule (light) | `#C8BEAF` 1px; ink `#15130F` 2px on cards; control border `#6C655A` 2px | (none) |
| Dark ground | `#000000`; cards `#0A0A0A` | `#08110F` ink-green; `#101A17` soft |
| Dark text | `#F7F2E8`; muted `#AAA49A` | `#F2EAD8` parchment; `#CEC3AA` dim |
| Dark rules | `#2D2D2D` 1px; `#F7F2E8` 2px on cards | `rgba(242,234,216,0.18)` 1px (99 uses on the home page) |
| Accent | One: cobalt `#1739D6` (light) / `#82A7FF` (dark) for links and focus only | Emerald `#63B89B` / `#1D604F` for the primary button and kickers; gold `#E0B75B` for focus and display italics; rust `#D66832` reserved |
| States | success `#146B43`, warning `#855600`, destructive `#A42B24` (light) | (not observed) |
| Grid | max 1152px (72rem), gutter 20px at 390 and 32px at 1440, prose 672px (42rem) / 68ch; `/about` 12 x 120px columns | content 1224px, copy 780px, three 292–400px columns, gap 12px |
| Spacing | `--section-gap` clamp(2.5rem, 5vw, 4.5rem); `--panel-padding` clamp(1.25rem, 2.25vw, 2.25rem); 4px multiples | sections 110–130px block padding; 10/12/14/18/24px steps |
| Radii | 2px on buttons, inputs and links-as-buttons; 0 elsewhere | 0 on buttons and cards; 2px on inputs |
| Shadows | none (every `--shadow-*` token is `none`) | `0 28px 100px rgba(0,0,0,.35)` on panels; gold glow |
| Gradients | none | linear and radial on every card and section |
| Buttons | primary ink fill, paper text, 2px ink border, 14/20/700, 8 x 16px, 44px tall; secondary transparent, 2px border | primary emerald `#1D604F` fill, 1px `#63B89B` border, 16/700, 11 x 18px, 50px tall; secondary translucent with hairline |
| Links | underlined, ink for navigation, cobalt in prose | no underline; parchment-dim navigation at 13px |
| Inputs | 2px `#6C655A` border, paper fill, 44px, 8 x 12px | 1px translucent border, 2px radius, 44.5px |
| Focus | 2px cobalt outline, offset 2px | 3px gold outline, offset 4px |
| Iconography | Lucide, 16px, 2px round-cap strokes (arrow, monitor, check) | none as SVG; CSS-drawn marks |
| Geometric motif | none | girih star lattice: `repeating-linear-gradient` at plus and minus 45 degrees on a 92px cell, a conic-gradient halo, a 1520 x 980 canvas; logo = two 34 x 10 bordered rectangles crossed at 90 degrees in gold |
| Motion | 150ms `cubic-bezier(0.4,0,0.2,1)` on colour/border; `active:translate-y-px`; reduced-motion rules present | 1.8s / 0.52s `cubic-bezier(0.34,0.08,0.22,1)` decorative drift, with a "Motion" toggle (`aria-pressed`) and reduced-motion rules |
| Skip link | yes | yes |

## Where they agree

Warm off-white or parchment on near-black, one dominant accent, square or near-square corners, uppercase tracked
labels (12px, about +0.1em) set apart from sentence-case body, a 42–49rem prose measure, 44px controls, a visible
offset focus ring, a skip link, reduced-motion handling, and Inter as the sans.

## Where they differ, and what DESIGN.md follows

| Question | Neos | Taawun | Followed |
| --- | --- | --- | --- |
| Hierarchy carrier | heavy grotesque weight (900) | serif display at large sizes | Neos: weight, not a second family. Arabic is the second voice |
| Surfaces | flat fills, no shadows | gradients, glows, translucent panels | Neos (the owner's "ultra-flat") |
| Themes | light and dark | dark only | Neos: both, following the system |
| Accent | cobalt, links and focus only | emerald and gold | One accent, as both intend; hue from the product (emerald, already this app's accent), role from Neos (links, primary action, focus) |
| Radius | 2px controls | 0 buttons, 2px inputs | 0 everywhere |
| Rules | 2px ink frames on cards | hairlines everywhere | Taawun's hairlines between rows; Neos's ink rule only to open a section. No framed cards |
| Geometry | none | Islamic lattice as atmosphere | Geometry as information only (tradition marks, nodes), never as decoration |
| Motion | 150ms state changes | slow ambient drift | Neos, shorter (120–180ms) |
