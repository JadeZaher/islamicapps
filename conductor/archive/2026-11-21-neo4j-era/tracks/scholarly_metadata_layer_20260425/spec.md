# Scholarly Metadata Layer

## Problem

The graph schema defines nodes for scholarly opinions (Scholar, ScholarVerdict, Commentary, Practice) but the audit found them nearly empty:

| Node Type | Count | Expected |
|---|---|---|
| Scholar | 1 | 50+ major scholars |
| ScholarVerdict | 0 | Thousands (scholar + hadith + ruling) |
| Commentary | 0 | Hundreds (sharh references) |
| Practice | 0 | Dozens (fiqh rulings derived from hadiths) |
| SchoolOfThought | 9 | Good baseline |

Without scholarly verdicts, the graph can compute structural properties (centrality, community) but cannot represent the scholarly dimension — which scholars graded which hadiths and why.

## Goal

Populate the scholarly metadata layer to enable:
1. **Multi-scholar grading views**: See how different scholars graded the same hadith
2. **Scholar authority weighting**: Weight grades by scholar reputation
3. **Temporal scholarly opinion tracking**: How grades changed over centuries
4. **AI-assisted grading**: Use ScholarVerdict data as training signal

## Scope

Phase 1 focuses on the Shia Imami corpus (33K hadiths) because it already has detailed Arabic grades from al-Khoei's Mu'jam al-Ahadith. This data is already in display_grade but not structured as ScholarVerdict nodes.

Phase 2 extends to Sunni corpus using publicly available grading databases.

## Constraints

- Scholar nodes must have: name_arabic, name_english, death_year_hijri, tradition, authority_rank
- ScholarVerdict links Scholar -> Hadith with ruling + source_work + reasoning
- Must preserve scholarly attribution (which scholar said what)
- Do not fabricate or infer scholarly opinions

## Success Criteria

- 10+ Scholar nodes (major hadith scholars across traditions)
- ScholarVerdict nodes for at least the Shia corpus (33K hadiths from al-Khoei)
- Commentary nodes linking to at least 5 major sharh works
- Practice nodes linking common fiqh derivations to supporting hadiths
