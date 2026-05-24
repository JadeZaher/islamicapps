# Neo4j GDS Setup & Initial Graph Analytics

## Problem

The graph has 24,347 narrators connected by 77,696 HEARD_FROM edges — a rich network ready for graph analytics. But the Neo4j GDS library is not installed, and no analytics have been run. This data represents one of the most complete cross-tradition isnad networks ever assembled in a graph database.

## Goal

Install Neo4j GDS and run the first wave of graph analytics to:
1. Compute narrator authority scores (PageRank, Betweenness Centrality)
2. Discover transmission school clusters (Community Detection)
3. Validate chain temporal continuity (Path Analysis)
4. Computationally test the Common Link Theory (Schacht/Juynboll)
5. Compare graph structures across traditions (Sunni, Shia, Zaydi, Ibadi)

Store all computed scores as node properties for downstream use in the vector embedding pipeline and UI.

## Key Analytics

### Centrality
- **PageRank** on HEARD_FROM graph -> `narrator.pagerank_score`
- **Betweenness Centrality** -> `narrator.betweenness_score`
- **Degree Centrality** -> `narrator.in_degree`, `narrator.out_degree`

### Community Detection
- **Louvain** on HEARD_FROM graph -> `narrator.community_id`
- Cross-reference communities with geographic_region and tradition
- Identify: Medinan, Kufan, Basran, Syrian, Egyptian transmission schools

### Path Analysis
- Chain continuity check: student.death_year < teacher.death_year = impossible link
- Detect breaks (inqita'), hidden chains (mu'an'an), and elevated chains (ali)

### Common Link Theory Test
- Narrators with anomalously high betweenness relative to their tabaqah
- These "common links" are where multiple chains converge
- Compare against Juynboll's published common link findings

## Constraints

- GDS library must be compatible with current Neo4j version
- All graph projections should be named and documented
- Analytics scripts must be re-runnable (overwrite previous scores)
- Heavy computations may need to run against local Neo4j, not Railway proxy

## Success Criteria

- GDS library installed and verified
- PageRank, Betweenness, Community ID stored on all 24,347 narrators
- At least 5 distinct communities identified
- Chain validation report: count of temporally impossible links
- Common link candidates list: top 50 narrators by betweenness/tabaqah ratio
