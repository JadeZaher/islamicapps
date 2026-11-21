#!/usr/bin/env python3
"""Measure what al-Najashi, al-Tusi (Rijal, Fihrist) and the Riwayat corpus offer for an Imami narrator authority.

Measurement only: no authority, registry or identity is built. A headword-key match is a candidate, never an
identification. Usage (repo root):
python -B datasets/hadith-data/diagnostics/biography-verification/measure_imami_authority_inputs.py
"""

import json
import pathlib
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rijal_parsing as rp  # noqa: E402
import rijal_sources as rs  # noqa: E402

common = rs.common
OUT = common.output_directory(rs.JOB)
IMAMI_WORKS = ("najashi_rijal", "tusi_rijal", "tusi_fihrist")
# Imami rijal assessment vocabulary (folded); counted as words in the entry, attributed to the work's author.
TERMS = {
    "thiqa": r"ثقة", "thiqa_thiqa": r"ثقة ثقة", "daif": r"ضعيف", "ayn": r"عين", "wajh": r"وجه", "jalil": r"جليل",
    "ghali": r"غال|الغلو|غلو", "waqifi": r"واقفي|واقف|الواقفة", "fathi": r"فطحي|الفطحية", "ammi": r"عامي",
    "mamduh": r"ممدوح", "majhul": r"مجهول",
}
_TERM_RE = {name: re.compile(r"(?<![ء-ي])(?:" + pattern + r")(?![ء-ي])") for name, pattern in TERMS.items()}
_PREFIX = re.compile(r"^\s*(?:\[\s*\d+\s*\]\s*)?(?:\d+\s*)?(?:-\s*)?")  # Fihrist: '[1] 1 - name'


def entries_with_keys(work: str):
    document = rs.read_document(work)
    # Top-level chapters only ('### |'): in Tusi's Rijal these name the Imam a narrator transmitted from;
    # '### ||' are letter sub-chapters.
    sections = [(m.start(), rs.display_text(m.group(1))) for m in re.finditer(r"^### \|(?!\|)\s*(.*)$", document, flags=re.M)]
    section_index = 0
    for entry in rs.read_entries(work):
        while section_index + 1 < len(sections) and sections[section_index + 1][0] < entry["raw_start"]:
            section_index += 1
        section = sections[section_index][1] if sections and sections[section_index][0] < entry["raw_start"] else None
        text = _PREFIX.sub("", entry["text"])
        folded = rp.fold_for_phrases(text)
        head = re.split(r"[،,.:]", folded, maxsplit=1)[0]
        key = rs.name_key(" ".join(rp.headword_tokens(head)))
        yield entry, folded, key, section


def main() -> None:
    summary = {"works": {}}
    key_owners = defaultdict(set)
    key_entries = Counter()
    for work in IMAMI_WORKS:
        stats = Counter()
        terms = Counter()
        keys = Counter()
        sections = Counter()
        for entry, folded, key, section in entries_with_keys(work):
            stats["entries"] += 1
            if key:
                keys[key] += 1
                key_owners[key].add(work)
                key_entries[key] += 1
            for name, pattern in _TERM_RE.items():
                if pattern.search(folded):
                    terms[name] += 1
            deaths = rp.parse_year_statements(folded, "death", None, use_taqrib_century=False)
            if deaths:
                stats["entries_with_death_clause"] += 1
            if any(d["year_min"] is not None or d["year_max"] is not None for d in deaths):
                stats["entries_with_full_death_year"] += 1
            if section and work == "tusi_rijal":
                sections[section[:80]] += 1
        summary["works"][work] = {
            "entries": stats["entries"], "entries_with_death_clause": stats["entries_with_death_clause"],
            "entries_with_full_death_year": stats["entries_with_full_death_year"],
            "distinct_headword_keys": len(keys), "keys_unique_within_work": sum(1 for v in keys.values() if v == 1),
            "entries_sharing_a_key_within_work": sum(v for v in keys.values() if v > 1),
            "entries_with_term": dict(terms),
            "critic": rs.WORKS[work]["critic"],
        }
        if work == "tusi_rijal":
            summary["works"][work]["entries_by_section_imam"] = dict(sections.most_common(20))
    summary["key_overlap_across_works"] = dict(Counter(len(owners) for owners in key_owners.values()))

    # Riwayat Shi'i narrators
    connection = sqlite3.connect(pathlib.Path(rs.RIWAYAT).as_uri() + "?mode=ro&immutable=1", uri=True)
    q = lambda sql, *a: connection.execute(sql, a).fetchall()  # noqa: E731
    mention_counts = dict(q("""select m.narrator_id, count(*) from chain_mention m join hadith h on h.id = m.hadith_id
                               where h.tradition = 'shia' and m.narrator_id is not null group by 1"""))
    totals = q("""select count(*), count(m.narrator_id) from chain_mention m join hadith h on h.id = m.hadith_id
                  where h.tradition = 'shia'""")[0]
    method = dict(q("""select m.id_method, count(*) from chain_mention m join hadith h on h.id = m.hadith_id
                       where h.tradition = 'shia' group by 1 order by 2 desc limit 12"""))
    info = {row[0]: row[1:] for row in q("select id, std_name, tradition, death_year, tabaqa from narrator")}
    sources = defaultdict(set)
    for narrator_id, source in q("select narrator_id, source from narrator_source_id"):
        sources[narrator_id].add(source)
    forms = defaultdict(set)
    for narrator_id, form in q("select narrator_id, form from narrator_name where type in ('full','popular')"):
        if narrator_id in mention_counts:
            forms[narrator_id].add(form)
    counts = Counter()
    weighted = Counter()
    for narrator_id, mentions in mention_counts.items():
        std_name, tradition, death_year, tabaqa = info.get(narrator_id, (None, None, None, None))
        counts[f"tradition:{tradition}"] += 1
        counts["with_death_year"] += death_year is not None
        counts["with_tabaqa"] += tabaqa is not None
        for source in sources.get(narrator_id, ()):
            counts[f"crosswalk:{source}"] += 1
        keys = {rs.name_key(f) for f in forms.get(narrator_id, set()) | {std_name or ""}} - {""}
        entry_total = sum(key_entries.get(key, 0) for key in keys)
        status = ("one_rijal_entry" if entry_total == 1 else
                  "several_rijal_entries" if entry_total > 1 else "no_rijal_headword")
        counts[status] += 1
        weighted[status] += mentions
    summary["riwayat_shia"] = {
        "chain_mentions_in_shia_hadith": totals[0], "with_asserted_id": totals[1],
        "id_method_top": method, "distinct_asserted_narrators": len(mention_counts),
        "narrator_counts": dict(counts), "mentions_by_rijal_headword_match": dict(weighted),
        "note": "a headword-key match means the name equals an entry heading in Najashi/Tusi; homonyms are common "
                "(see chain-reconciliation Q5), so this is coverage of candidates, not identification",
    }
    connection.close()
    inputs = common.input_fingerprints(*(rs.WORKS[w]["path"] for w in IMAMI_WORKS), rs.RIWAYAT)
    summary["header"] = common.header_object(rs.JOB, "python -B datasets/hadith-data/diagnostics/biography-verification/"
                                                     "measure_imami_authority_inputs.py", inputs)
    summary["licence"] = "OpenITI texts CC BY-NC-SA 4.0; Riwayat CC0 (own layer)"
    common.write_json(OUT, "imami_authority_inputs.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "header"}, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
