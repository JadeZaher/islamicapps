# src/lib — pure helpers shared by pages, the proxy and the query layer

Only the sections below are documented here; other subfolders carry their own `AGENTS.md` (`auth/`, `glossary/`).

## Report addresses (`hadith-address.ts`)

Public URL of a report: the stable ID without its `hadith:` prefix, one path segment per ID part, each
percent-encoded: `hadith:k6:10008` → `/hadith/k6/10008`, `hadith:openiti:ibadi:rabi_0001|1|` →
`/hadith/openiti/ibadi/rabi_0001%7C1%7C`.

- **Why the ID and not work slug + number.** Numbers are not unique within a work in this data (al-Kafi numbers restart
  per chapter; Musnad Ahmad has 3,601 distinct numbers over 23,529 reports; Musnad al-Shafi'i has none). The stable ID
  is the loader's immutable key (datasets/hadith-data/AGENTS.md, Durable identity), so the address never moves when
  numbering is corrected.
- **Arity per namespace** (`k6`, `thaqalayn`, `pure-canon`: 1 part; `openiti`: 2) makes parsing unambiguous, so
  sub-routes such as `/hadith/k6/10008/chains` work.
- **The `[id]` route is unchanged.** `src/proxy.ts` rewrites the canonical path to the internal one-segment form and
  308-redirects the old `/hadith/<percent-encoded id>` form to the canonical path. Build links with `hadithPath(id)`.

## Report numbering (`citation/reference.ts`)

Each provider is referred to in its own scheme: K6 `Book n, Hadith m` (sunnah.com numbers; `0` means unnumbered);
Thaqalayn `Volume v, Book c, Chapter k, Hadith h` from the provider URL, because the loaded `hadith_no` of every
Thaqalayn row is the chapter number (`shia-hadith/build_csv.py` maps `hadith_no` from `chapterInCategoryId`);
OpenITI `No. n (vol. v, p. p)`; Pure Canon `No. n`, or the record key when the copy has no number.
`citation/cite.ts` builds the plain-text citation (work, reference, archive, dataset version, address, access date,
source references).

## Sources (`sources/registry.ts`, `sources/report-credit.ts`)

One typed registry of every source with a stable short code (`THQ`, `OITI`, `SUN`, `NMC`, `MSD`, `K6I`, `RIJ`, `HKG`,
`RWY`, `SWI`, `AMR`, `GST`), the anchor of its record on `/sources`, what it supplies, licence, the wording its licence or
`docs/rights/rights-register.md` requires (quoted verbatim, placeholders as written), link and retrieval date; plus
per-work credits (author, translator, OpenITI URI) from the register's tables. Surfaces show a short reference (code
and name linking to the record, licence name) via `SourceCredit`; the full wording lives on the record. CC BY 4.0 and
CC BY-NC-SA 4.0 allow attribution "by providing a URI or hyperlink to a resource that includes the required
information", which is what the record is. Helpers: `sourceForDatabaseSlug`, `sourceCodeForHadithId`,
`sourceForIdentityBasis` (name bases → `MSD`, source-index bases → `K6I`, reviewer → `SWI`), `sourceForGrading`.
`browse-flows.test.ts` fails if a loaded or registered work, or a `datasets/sources/*.md` card, lacks a record.

## Site origin (`site-origin.ts`, `site-url.ts`)

Every absolute URL the site emits (citation address, canonical link, robots sitemap line, sitemap, redirect `Location`
in `src/proxy.ts`, the sign-in and sign-out routes and the throttled sign-in answer) goes through `siteOriginFor` /
`siteUrlFor` (edge-safe) or `siteOrigin()` (server components).

- **Production uses `SITE_URL` only.** Request headers (`Host`, `X-Forwarded-Host`, `X-Forwarded-Proto`) never decide an
  absolute URL there: a client could otherwise plant its own host in canonical links, citations, cached pages and
  redirects (host-header injection, cache poisoning; security review 2026-11-21). `src/instrumentation.ts` refuses to
  start in production when `SITE_URL` is missing, not absolute, not https (http only for a loopback host, so local
  `next start` tests run), or carries a path, query or credentials (`siteUrlProblem`).
- **Development and tests** use `SITE_URL` when set, else the request host only if it is a loopback host, else
  `http://localhost:3000`.
- **Internal rewrites** clone `request.nextUrl` (`internalRewriteUrl` in the proxy), so a rewrite can never target
  another origin.
- Tested over HTTP in `switches-http.test.ts` ("site origin"): forged `Host` and `X-Forwarded-Host` leave the cite
  block, canonical link and a 308 `Location` on `SITE_URL`, and production without `SITE_URL` exits 1.
