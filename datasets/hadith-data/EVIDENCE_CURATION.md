# Citation-bound biography and history curation

`evidence_curation.schema.json` defines the only accepted shape for
`evidence_curation.json`. The checked-in bundle intentionally contains no
claims. The companion manifest is a derived summary and remains non-ready until
scholarly review supplies citation-bound records; editing its counts or ready
boolean cannot satisfy the publication gate.

Each claim must name a stable assertion ID, subject ID, exact citation ID, and
`human_verified` or `source_verified` review state. A citation records the
bibliographic work and edition plus an authentic locator; volume and page are
preserved separately when the edition provides them. A stable URL is useful but
does not replace an edition locator.

Citation IDs must be unique. Assertion IDs are unique across all claim arrays,
every `citation_id` must resolve inside the same bundle, and a non-null
`supersedes_assertion_id` must resolve to another assertion. Regeneration loads
the schema and derives all manifest counts from the bundle before it can pass.

For dates, use `year_min`/`year_max`, `precision`, and `uncertainty`. Leave
both years null for a cited unknown date. Never turn a relative, disputed, or
approximate statement into an exact year. Competing assertions remain separate
and link via `supersedes_assertion_id` only after review.

Source-author assertions must use the durable `source_work_id`, not an Arabic
or Romanized display label. This preserves the separate Mufid/Saduq *Al-Amali*
and Tusi/Nu'mani *Kitab al-Ghayba* works. Provider metadata can establish which
work a row came from but does not itself make a compiler biography, date, or
edition citation publication-ready.

Historical seed nodes are deliberately not evidence. Do not promote or edit a
seed through this workflow unless a cited event/epoch assertion has been added
and independently reviewed. The graph read path remains fail-closed while the
manifest is non-ready.
