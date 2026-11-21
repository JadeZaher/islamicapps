import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Layering rules (data-architecture.md section 3.2): all SQL lives in src/db/queries.
const DATABASE_IMPORTS = {
  paths: [
    { name: "drizzle-orm", message: "No SQL outside src/db/queries: call a query function instead (section 3.2 rule 1)." },
    { name: "postgres", message: "Only src/db/client.ts creates a database client (section 3.2 rule 1)." },
    { name: "@/db/client", message: "Import a query function from @/db/queries/* instead (section 3.2 rule 1)." },
  ],
  patterns: [
    { group: ["drizzle-orm/*"], message: "No SQL outside src/db/queries (section 3.2 rule 1)." },
    { group: ["@/db/schema", "@/db/schema/*"], message: "The schema is read only by src/db/queries (section 3.2 rule 1)." },
    { group: ["**/db/client", "**/db/schema", "**/db/schema/*"], message: "Use @/db/queries/* (section 3.2 rule 1)." },
  ],
};

// Base-table (reviewer-mode) reads live in *-review.ts and may serve only curator surfaces (section 3.2 rule 9).
const REVIEW_QUERIES = {
  group: ["@/db/queries/*-review", "**/db/queries/*-review"],
  message: "Public pages read public views only; *-review queries are for /admin and curation actions (section 3.2 rule 9).",
};

const NO_SQL_TEMPLATE = {
  selector: "TaggedTemplateExpression[tag.name='sql']",
  message: "No SQL outside src/db/queries (section 3.2 rule 1).",
};

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/app/**/*.{ts,tsx}", "src/components/**/*.{ts,tsx}"],
    ignores: ["src/app/admin/**", "src/app/actions/curation/**", "src/app/api/export/**"],
    rules: {
      "no-restricted-imports": ["error", { ...DATABASE_IMPORTS, patterns: [...DATABASE_IMPORTS.patterns, REVIEW_QUERIES] }],
      "no-restricted-syntax": ["error", NO_SQL_TEMPLATE],
    },
  },
  {
    files: ["src/app/admin/**/*.{ts,tsx}", "src/app/actions/curation/**/*.{ts,tsx}", "src/app/api/export/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", DATABASE_IMPORTS],
      "no-restricted-syntax": ["error", NO_SQL_TEMPLATE],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    ".pytest_cache/**",
    "src/scripts/archive/**",
    "datasets/hadith-data/archive/**",
  ]),
]);

export default eslintConfig;
