---
type: reference
updated: 2026-11-21
---

# Testing

The project's real test suite as one sequence. Every database step uses the **development** database from
`.env.local` (`DATABASE_URL`); the fixture-based suites build private schemas inside it and refuse production. Run
from the repository root. Steps 1 to 4 need no build; 6 and 7 need step 5.

```
# 1. Types
npx tsc --noEmit

# 2. Query-layer flows on the fixture schema (real rows from the 2026-11-21 bundle)
npx tsx --conditions=react-server src/db/queries/__tests__/flows.test.ts
npx tsx --conditions=react-server src/db/queries/__tests__/browse-flows.test.ts

# 3. Glossary integrity
npx tsx src/lib/glossary/__tests__/glossary.test.ts

# 4. Catalog verification of the development database
npm run db:verify

# 5. Production build
npx next build

# 6. HTTP gate: proxy, sign-in, actions with AUTH_ENABLED=1 (next start on port 3917)
npx tsx --conditions=react-server src/db/queries/__tests__/http-gate.test.ts

# 7. Switches over HTTP: auth off, private preview, crawl policy, start-up refusals, SITE_URL as the only origin
#    under forged Host headers (ports 3927 to 3930)
npx tsx --conditions=react-server src/db/queries/__tests__/switches-http.test.ts

# 8. Python suites (standard library unittest; -I keeps the interpreter isolated). Discovery does not descend into
#    folders without __init__.py, so each folder is named (test counts as of 2026-11-21).
python -I datasets/hadith-data/pg_export/test_export_postgres.py
python -I -m unittest discover -s datasets/hadith-data/__tests__ -p "test_*.py"                        # 182
python -m pytest -q datasets/hadith-data/__tests__/fixtures/__tests__                                  # 36; these import pytest, which -I hides
python -I -m unittest discover -s datasets/hadith-data/diagnostics -p "test_*.py"                      # 10
python -I -m unittest discover -s datasets/hadith-data/diagnostics/biography-recovery -p "test_*.py"   # 5
python -I -m unittest discover -s datasets/hadith-data/diagnostics/biography-verification -p "test_*.py"  # 9
python -I -m unittest discover -s datasets/hadith-data/diagnostics/report-correspondence -p "test_*.py"   # 14
```

Not in the sequence: `src/db/load/__tests__/load-flow.test.ts` (needs a full projection on disk; run
`npx tsx --test src/db/load/__tests__/load-flow.test.ts` after a projection build) and the archived Neo4j-era
`src/scripts/__tests__/regen-*.test.ts` (`npm run test:regen`), which test the outgoing graph pipeline.

## Proposed `package.json` scripts

Not added (shared file; the session lead edits it at a join):

```json
"test:types": "tsc --noEmit",
"test:flows": "tsx --conditions=react-server src/db/queries/__tests__/flows.test.ts && tsx --conditions=react-server src/db/queries/__tests__/browse-flows.test.ts",
"test:glossary": "tsx src/lib/glossary/__tests__/glossary.test.ts",
"test:http": "tsx --conditions=react-server src/db/queries/__tests__/http-gate.test.ts && tsx --conditions=react-server src/db/queries/__tests__/switches-http.test.ts",
"test:python": "python -I datasets/hadith-data/pg_export/test_export_postgres.py && python -I -m unittest discover -s datasets/hadith-data/__tests__ -p test_*.py && python -m pytest -q datasets/hadith-data/__tests__/fixtures/__tests__ && python -I -m unittest discover -s datasets/hadith-data/diagnostics -p test_*.py && python -I -m unittest discover -s datasets/hadith-data/diagnostics/biography-recovery -p test_*.py && python -I -m unittest discover -s datasets/hadith-data/diagnostics/biography-verification -p test_*.py && python -I -m unittest discover -s datasets/hadith-data/diagnostics/report-correspondence -p test_*.py",
"test": "npm run test:types && npm run test:flows && npm run test:glossary && npm run db:verify && next build && npm run test:http && npm run test:python"
```
