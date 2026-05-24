# Neo4j GDS Setup & Initial Analytics — Implementation Plan

## Phase 1: GDS Library Installation & Configuration (3 tasks)

### Task 1.1: Install Neo4j GDS plugin
- Determine Neo4j version (query `CALL dbms.components()`)
- Download matching GDS plugin jar
- Configure neo4j.conf to load GDS
- Restart Neo4j and verify: `RETURN gds.version()`

### Task 1.2: Create graph projections
- Script: `src/scripts/gds-project-graphs.ts`
- Project 1: Full narrator network (all HEARD_FROM)
- Project 2: Sunni-only subgraph (narrators connected to Sunni hadiths)
- Project 3: Shia-only subgraph
- Project 4: Zaydi-only subgraph

### Task 1.3: Validate projections
- Check node/edge counts per projection
- Verify no projection errors

## Phase 2: Centrality Analysis (3 tasks)

### Task 2.1: Run PageRank
```cypher
CALL gds.pageRank.write('narrator-full', {
  writeProperty: 'pagerank_score',
  maxIterations: 20,
  dampingFactor: 0.85
})
```
- Store on Narrator.pagerank_score

### Task 2.2: Run Betweenness Centrality
```cypher
CALL gds.betweenness.write('narrator-full', {
  writeProperty: 'betweenness_score'
})
```
- Store on Narrator.betweenness_score

### Task 2.3: Run Degree Centrality
- Compute in_degree and out_degree for HEARD_FROM
- Store as Narrator.heard_from_in_degree, Narrator.heard_from_out_degree
- Create indexes on all new properties

## Phase 3: Community Detection (3 tasks)

### Task 3.1: Run Louvain on full graph
```cypher
CALL gds.louvain.write('narrator-full', {
  writeProperty: 'community_id'
})
```

### Task 3.2: Analyze community composition
- For each community: count narrators, list top-5 by PageRank
- Cross-reference with geographic_region (once enriched)
- Cross-reference with tradition
- Output: community profile report

### Task 3.3: Run per-tradition community detection
- Separate Louvain on Sunni/Shia subgraphs
- Compare: do the same communities appear? Where do they diverge?

## Phase 4: Path Analysis & Chain Validation (3 tasks)

### Task 4.1: Temporal continuity check
- Script: `src/scripts/gds-chain-validation.ts`
- For each HEARD_FROM edge: check if student.death_year < teacher.death_year
- Flag impossible links
- Report: count by source, count by tradition

### Task 4.2: Chain completeness analysis
- For each Chain node: verify all INCLUDES narrators form a connected path via HEARD_FROM
- Detect broken chains (narrator A in chain but no HEARD_FROM to next)

### Task 4.3: Chain length distribution
- Histogram of chain lengths by source collection
- Identify unusually short or long chains

## Phase 5: Common Link Theory Computational Test (2 tasks)

### Task 5.1: Compute common link scores
- Score = betweenness_score / tabaqah (or betweenness normalized by generation)
- High score = narrator who is a convergence point for many chains relative to their generation
- These are Juynboll's "common links"

### Task 5.2: Generate common link report
- Top 50 narrators by common link score
- For each: name, tabaqah, tradition, number of chains passing through, betweenness
- Cross-reference with known common links from hadith scholarship literature

## Phase 6: Cross-Tradition Comparative Analytics (2 tasks)

### Task 6.1: Shared narrator analysis
- Find narrators who appear in chains from multiple traditions
- How many narrators are shared between Sunni and Shia chains?
- What are their PageRank scores in each tradition's subgraph?

### Task 6.2: Tradition divergence mapping
- Find narrators who are highly central in one tradition but absent from another
- Map the "point of divergence" in chains between traditions

## Phase 7: Results Storage & Visualization (2 tasks)

### Task 7.1: Create analytics summary endpoint
- Server action: `src/app/actions/analytics-actions.ts`
- Queries: top narrators by centrality, community profiles, chain stats

### Task 7.2: Add analytics dashboard page
- Page: `/analytics` or `/admin/analytics`
- Show: centrality leaders, community graph, chain validation results
- Use existing react-force-graph-2d for network visualization
