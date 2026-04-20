# TypeScript Styleguide

## General

- Use `interface` for object shapes; `type` for unions/intersections/aliases
- Prefer explicit return types on exported functions
- Use `const` by default; `let` only when reassignment is needed
- No `var`

## Next.js Patterns

```typescript
// Server component (default — no directive needed)
export default async function Page({ params }: { params: { id: string } }) { ... }

// Client component
'use client';
export function ClientComponent() { ... }

// Server action
'use server';
export async function myAction(data: MyType): Promise<string> { ... }
```

## Neo4j Queries

Always use parameterized queries:

```typescript
// CORRECT
const result = await runQuery(`MATCH (n:Narrator {id: $id}) RETURN n`, { id });

// WRONG — never do this
const result = await runQuery(`MATCH (n:Narrator {id: '${id}'}) RETURN n`);
```

Map results explicitly:

```typescript
const result = await runQuery<{ n: { properties: NarratorProps } }>(`...`);
return result.map((r) => r.n.properties);
```

## Naming Conventions

| Pattern | Convention | Example |
|---|---|---|
| Components | PascalCase | `NarratorCard`, `TraditionBadge` |
| Server actions | camelCase verb | `createNarrator`, `getParallelsForHadith` |
| Types/Interfaces | PascalCase | `NarratorData`, `ParallelType` |
| Constants | SCREAMING_SNAKE | `PARALLEL_TYPES`, `MOTIF_CATEGORIES` |
| Files | kebab-case or camelCase | `graph-actions.ts`, `client-page.tsx` |

## Component Structure

```typescript
// Props interface first
interface MyComponentProps {
  data: MyData;
  onAction?: () => void;
}

// Component declaration
export function MyComponent({ data, onAction }: MyComponentProps) {
  // hooks first
  const [state, setState] = useState(...);

  // handlers
  const handleClick = () => { ... };

  // render
  return (...);
}
```

## Imports Order

1. React and Next.js
2. Third-party libraries
3. Internal actions (`@/app/actions/`)
4. Internal components (`@/components/`)
5. Types (inline or from same file)

## Error Handling

- Server actions: throw errors, let Next.js propagate
- Parallel fetches: use `.catch(() => fallback)` to avoid one failure killing the page
- Never swallow errors silently — at minimum `console.error`
