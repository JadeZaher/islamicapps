#!/usr/bin/env tsx
/**
 * build-credits.ts — generate datasets/CREDITS.md from front-matter
 *
 * Reads every file under datasets/sources/ and datasets/strategies/
 * (excluding _TEMPLATE.md and README.md), parses the YAML front-matter,
 * and renders a canonical credits page. The generated file is the single
 * thing we link from the app footer, the GitHub README, and any external
 * publication that cites the project.
 *
 * Re-run after editing any source or strategy file:
 *   npm run build:credits
 *
 * The script intentionally hand-rolls a minimal YAML reader rather than
 * pulling in a dependency. The front-matter schema is small and stable;
 * see datasets/sources/_TEMPLATE.md and datasets/strategies/_TEMPLATE.md
 * for the full key list.
 */

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join, basename } from "node:path";

const REPO_ROOT = join(__dirname, "..", "..");
const SOURCES_DIR = join(REPO_ROOT, "datasets", "sources");
const STRATEGIES_DIR = join(REPO_ROOT, "datasets", "strategies");
const OUTPUT_PATH = join(REPO_ROOT, "datasets", "CREDITS.md");

type FrontMatter = Record<string, unknown>;

interface RegistryEntry {
  slug: string;
  path: string;
  fm: FrontMatter;
}

// ─── front-matter extraction ─────────────────────────────────────────────

function extractFrontMatter(raw: string): FrontMatter {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) {
    throw new Error("missing YAML front-matter block");
  }
  return parseYaml(match[1]);
}

/**
 * Minimal YAML reader covering the subset used by source/strategy files:
 *   - scalar keys: `key: value`
 *   - list keys:   `key:` followed by `  - item` lines
 *   - block scalars: `key: |` followed by indented continuation lines
 *   - comments (`#` to end of line) and blank lines ignored
 *   - quoted strings are unquoted; everything else is stored as-is
 *
 * Deliberately strict: throws on anything it doesn't recognize so a
 * malformed front-matter fails the build loudly rather than silently
 * producing wrong credits.
 */
function parseYaml(body: string): FrontMatter {
  const lines = body.split(/\r?\n/);
  const out: FrontMatter = {};
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.replace(/\s+#.*$/, "").trimEnd();

    if (trimmed === "" || /^\s*#/.test(line)) {
      i++;
      continue;
    }

    const scalarMatch = trimmed.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!scalarMatch) {
      throw new Error(`unparseable YAML line: ${JSON.stringify(line)}`);
    }
    const key = scalarMatch[1];
    const rest = scalarMatch[2];

    if (rest === "") {
      const collected: string[] = [];
      i++;
      while (i < lines.length && /^\s{2,}-\s/.test(lines[i])) {
        collected.push(lines[i].replace(/^\s{2,}-\s*/, "").trim());
        i++;
      }
      out[key] = collected;
      continue;
    }

    if (rest === "|" || rest === ">") {
      const collected: string[] = [];
      i++;
      while (i < lines.length && (lines[i].startsWith("  ") || lines[i] === "")) {
        collected.push(lines[i].replace(/^ {2}/, ""));
        i++;
      }
      out[key] = collected.join("\n").trim();
      continue;
    }

    out[key] = unquote(rest);
    i++;
  }

  return out;
}

function unquote(s: string): string {
  const t = s.trim();
  if (
    (t.startsWith('"') && t.endsWith('"')) ||
    (t.startsWith("'") && t.endsWith("'"))
  ) {
    return t.slice(1, -1);
  }
  return t;
}

// ─── registry loading ────────────────────────────────────────────────────

function loadRegistry(dir: string): RegistryEntry[] {
  const entries: RegistryEntry[] = [];
  for (const fname of readdirSync(dir)) {
    if (!fname.endsWith(".md")) continue;
    if (fname === "_TEMPLATE.md" || fname === "README.md") continue;

    const path = join(dir, fname);
    const raw = readFileSync(path, "utf8");
    let fm: FrontMatter;
    try {
      fm = extractFrontMatter(raw);
    } catch (err) {
      throw new Error(`${path}: ${(err as Error).message}`);
    }

    const slug = basename(fname, ".md");
    const fmId = fm.id;
    if (typeof fmId !== "string" || fmId !== slug) {
      throw new Error(
        `${path}: front-matter id (${String(fmId)}) must equal filename slug (${slug})`,
      );
    }

    entries.push({ slug, path, fm });
  }
  entries.sort((a, b) => a.slug.localeCompare(b.slug));
  return entries;
}

// ─── rendering ───────────────────────────────────────────────────────────

function str(v: unknown, fallback = "—"): string {
  if (typeof v === "string" && v.trim() !== "") return v;
  if (Array.isArray(v) && v.length > 0) return v.join(", ");
  return fallback;
}

function renderSource(e: RegistryEntry): string {
  const fm = e.fm;
  return [
    `### ${str(fm.name)}`,
    "",
    `- **Kind:** ${str(fm.kind)}`,
    `- **URL:** ${str(fm.url)}`,
    `- **License:** ${str(fm.license)}${fm.license_url ? ` ([text](${fm.license_url}))` : ""}`,
    `- **Traditions:** ${str(fm.traditions)}`,
    `- **Retrieved:** ${str(fm.retrieved)}`,
    `- **In-repo:** ${str(fm.paths)}`,
    `- **Details:** [\`datasets/sources/${e.slug}.md\`](./sources/${e.slug}.md)`,
    "",
    "```bibtex",
    str(fm.bibtex, "% no BibTeX entry provided"),
    "```",
    "",
  ].join("\n");
}

function renderStrategy(e: RegistryEntry): string {
  const fm = e.fm;
  return [
    `### ${str(fm.name)}`,
    "",
    `- **Status:** ${str(fm.status)}`,
    `- **Applies to:** ${str(fm.applies_to_traditions)}`,
    `- **Consumes sources:** ${str(fm.consumes_sources)}`,
    `- **Introduced:** ${str(fm.introduced)} · **Last reviewed:** ${str(fm.last_reviewed)}`,
    `- **Implementation:** ${str(fm.paths)}`,
    "",
    `**Problem.** ${str(fm.problem_domain)}`,
    "",
    `**Evaluation.** ${str(fm.evaluation_method, "—")} → ${str(fm.evaluation_results, "—")}`,
    "",
    `**Details:** [\`datasets/strategies/${e.slug}.md\`](./strategies/${e.slug}.md)`,
    "",
    fm.bibtex
      ? ["```bibtex", String(fm.bibtex), "```", ""].join("\n")
      : "",
  ].join("\n");
}

function render(sources: RegistryEntry[], strategies: RegistryEntry[]): string {
  const today = new Date().toISOString().slice(0, 10);
  return [
    "# Credits",
    "",
    "_This file is generated by `npm run build:credits` from the front-matter of every file under [`datasets/sources/`](./sources/) and [`datasets/strategies/`](./strategies/). **Do not hand-edit.** Edit the source files and re-run the generator._",
    "",
    `_Last built: ${today}_`,
    "",
    "## How to cite this project",
    "",
    "If you publish work that uses Shura wa Istehsan data, please cite **both** the project and any individual upstream source you rely on. The per-source BibTeX entries below are the citations to lift directly.",
    "",
    "---",
    "",
    `## Data sources (${sources.length})`,
    "",
    ...sources.map(renderSource),
    "---",
    "",
    `## Strategies & methodologies (${strategies.length})`,
    "",
    ...strategies.map(renderStrategy),
    "---",
    "",
    "## Acknowledgements",
    "",
    "Shura wa Istehsan stands on the work of generations of Muslim scholars across every tradition — Sunnī, Shīʿī, Zaydī, Ibāḍī, and beyond — and on the modern digital-humanities projects that have made classical texts machine-readable. The sources listed above are the proximate causes; the deeper debt is owed to the long chain of transmitters whose names this project is, in part, about preserving.",
    "",
  ].join("\n");
}

// ─── main ────────────────────────────────────────────────────────────────

function main(): void {
  const sources = loadRegistry(SOURCES_DIR);
  const strategies = loadRegistry(STRATEGIES_DIR);

  if (sources.length === 0) {
    console.warn("warning: no source files found under datasets/sources/");
  }
  if (strategies.length === 0) {
    console.warn("warning: no strategy files found under datasets/strategies/");
  }

  const output = render(sources, strategies);
  writeFileSync(OUTPUT_PATH, output, "utf8");
  console.log(
    `wrote ${OUTPUT_PATH} (${sources.length} sources, ${strategies.length} strategies)`,
  );
}

main();
