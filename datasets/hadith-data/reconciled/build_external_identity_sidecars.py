#!/usr/bin/env python3
"""External narrator registries, lexicon links, per-mention source claims and Qur'an quotation spans.

Reads the report crosswalk (build_external_report_crosswalk.py), the loaded projection's mentions and K6 candidates
(read only), the rawi lexicon and both external SQLite files (read only). Aligns each matched report's external
narrator list with our chain(s) using the K6 `classify`/`align` unchanged, through a name-only stand-in registry
(external_source_logic.ExternalNames). Writes, here: hadith_kg_narrators, riwayat_narrators,
external_narrator_lexicon_links, external_mention_claims, hadith_kg_quran_citations (+ manifest).
Never imports a computed verdict or grade (hadith-kg `sanads.hukum`/`matn`, Riwayat edge/flag heuristics).
Usage (repo root): python -B datasets/hadith-data/reconciled/build_external_identity_sidecars.py
"""

import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_source_io as xio  # noqa: E402
import external_source_logic as logic  # noqa: E402

io_, common, rc = xio.io_, xio.common, xio.rc
sys.path.insert(0, str(io_.RECONCILE_DIR))
from measure_source_index_agreement import classify  # noqa: E402
sys.path.insert(0, str(common.HADITH_DATA_DIR / "pg_export"))
from export_postgres import align_source_index  # noqa: E402
sys.path.insert(0, str(common.DIAGNOSTICS_DIR / "biography-verification"))
import rijal_sources as rs  # noqa: E402
from verify_lexicon_against_rijal import _raw_years  # noqa: E402

KG, RIW = logic.DATASET_HADITH_KG, logic.DATASET_RIWAYAT
KG_ZAYDI_BOOK, KG_IBADI_BOOK = 55, 56
RIWAYAT_ZAYDI_BOOK, RIWAYAT_IBADI_BOOK = "مسند زيد", "مسند الربيع بن حبيب"
RIWAYAT_FORM_TYPES = ("full", "popular", "kunya", "laqab", "variant", "nasab_nisba")   # never `observed` chain surfaces
RIWAYAT_KEY_TYPES = ("full", "popular")
MIN_QUOTE_LETTERS = 10
K6_BASES = ("source_index", "source_index_confirmed_by_text")
NOT_IMPORTED = {
    "hadith_kg": ["sanads.hukum (a computed sentence on the isnad)", "sanads.matn / hadiths.matn (hukm labels)",
                  "sanads.max_rank (computed from narrator ranks)", "aqwal (critic statements; separate curation)",
                  "meaning_groups / embeddings"],
    "riwayat": ["guess_narrator_id (weak candidates)", "narrator_edge / suspect flags (computed)",
                "isnad_node floruit ranges (computed)", "claude_label_* (model labels) except as the id_method "
                "provenance of an asserted id"],
}


def kg_id(rawi_id) -> str:
    return f"{logic.ID_PREFIX[KG]}{rawi_id}"


def riw_id(narrator_id) -> str:
    return f"{logic.ID_PREFIX[RIW]}{narrator_id}"


def load_crosswalk() -> dict:
    """{record_id: {dataset: crosswalk row}} for used (unique) matches."""
    used = defaultdict(dict)
    for row in xio.read_jsonl_gz(io_.RECONCILED_DIR / xio.CROSSWALK):
        if row["used"]:
            used[row["record_id"]][row["dataset"]] = row
    return used


# Mentions a continuation repeats from an earlier report (pg_export chain_builder): they copy that mention's claims, so
# no external claim is aligned onto them.
INHERITED_MENTIONS: set = set()


def load_mentions(hadith_ids: set) -> dict:
    """{hadith_id: [[(mention_id, surface_ar), ...] per branch]} from the loaded projection, branches in order."""
    grouped = defaultdict(lambda: defaultdict(list))
    for row in xio.iter_projection("chain_mentions.csv"):
        if row.get("inherited_from_mention_id"):
            INHERITED_MENTIONS.add(row["id"])
        if row["hadith_id"] in hadith_ids:
            branch = int(row["chain_id"].rsplit(":", 1)[1])
            grouped[row["hadith_id"]][branch].append((int(row["position"]), row["id"], row["surface_ar"]))
    out = {}
    for hadith_id, branches in grouped.items():
        if sorted(branches) != list(range(len(branches))):
            raise SystemExit(f"{hadith_id}: projection branches not contiguous")
        out[hadith_id] = []
        for index in range(len(branches)):
            items = sorted(branches[index])
            if [p for p, _, _ in items] != list(range(len(items))):
                raise SystemExit(f"{hadith_id}: projection positions not contiguous")
            out[hadith_id].append([(mention_id, surface) for _, mention_id, surface in items])
    return out


def load_k6_claims() -> dict:
    """{mention_id: {scholar_indx}} for today's K6 source-index candidates in the projection."""
    claims = defaultdict(set)
    for row in xio.iter_projection("chain_mention_candidates.csv"):
        if row["basis"] in K6_BASES:
            claims[row["mention_id"]].add(row["narrator_id"].removeprefix("narrator:rawi:"))
    return claims


def fetch_kg_chain(connection, hadith_id: str) -> list:
    """[(external id, sanad id, pos, None)] for every sanad of a hadith-kg report, the author (pos 0) dropped."""
    items = []
    for (sanad_id,) in connection.execute("select id from sanads where hadith_id = ? order by id", (int(hadith_id),)):
        for pos, rawi_id in connection.execute(
                "select pos, rawi_id from sanad_rawis where sanad_id = ? and pos > 0 order by pos", (sanad_id,)):
            items.append((kg_id(rawi_id), sanad_id, pos, None))
    return items


def fetch_riwayat_chain(connection, hadith_id: str) -> list:
    """[(external id or an unidentified placeholder, chain_no, pos, mention detail)] in chain and position order."""
    items = []
    for chain_no, pos, surface, narrator_id, method, confidence in connection.execute(
            "select chain_no, pos, surface, narrator_id, id_method, id_confidence from chain_mention "
            "where hadith_id = ? order by chain_no, pos", (hadith_id,)):
        identity = riw_id(narrator_id) if narrator_id else f"riwayat-unidentified:{hadith_id}:{chain_no}:{pos}"
        items.append((identity, chain_no, pos, {"surface": surface, "id_method": method,
                                                "id_confidence": confidence}))
    return items


def kg_narrators(connection) -> dict:
    columns = ("id", "name", "nickname", "rank_no", "rank", "tabaka", "is_bukhari", "is_muslim", "has_ikhtilat",
               "has_tadlis", "riwaya_qty", "birth_year", "birth_year_raw", "death_year", "death_year_raw", "age_raw",
               "profession", "nasab", "iqama", "death_place", "is_stub")
    return {row[0]: dict(zip(columns, row)) for row in connection.execute(f"select {', '.join(columns)} from rawis")}


def kg_context(connection) -> dict:
    """{rawi_id: Counter(tradition context -> chain positions)} over every hadith-kg chain (author excluded).

    Sequential scans aggregated here: a SQL join does millions of random reads into the text-bearing tables."""
    label = {KG_ZAYDI_BOOK: "Zaydi", KG_IBADI_BOOK: "Ibadi"}
    hadith_context = {hadith_id: label.get(book_id, "Sunni")
                      for hadith_id, book_id in connection.execute("select id, book_id from hadiths")}
    sanad_context = {sanad_id: hadith_context[hadith_id]
                     for sanad_id, hadith_id in connection.execute("select id, hadith_id from sanads")}
    del hadith_context
    context = defaultdict(Counter)
    for sanad_id, rawi_id in connection.execute("select sanad_id, rawi_id from sanad_rawis where pos > 0"):
        context[rawi_id][sanad_context[sanad_id]] += 1
    return context


def riwayat_context(connection) -> dict:
    """{narrator_id: Counter(tradition context -> asserted mentions)}; Musnad Zayd and Musnad al-Rabi' re-attributed."""
    hadith_context = {}
    for hadith_id, tradition, book in connection.execute("select id, tradition, book from hadith"):
        hadith_context[hadith_id] = ("Imami" if tradition == "shia" else "Zaydi" if book == RIWAYAT_ZAYDI_BOOK
                                     else "Ibadi" if book == RIWAYAT_IBADI_BOOK else "Sunni")
    context = defaultdict(Counter)
    for hadith_id, narrator_id in connection.execute(
            "select hadith_id, narrator_id from chain_mention where narrator_id is not null"):
        context[narrator_id][hadith_context[hadith_id]] += 1
    return context


def riwayat_forms(connection, narrator_ids=None) -> dict:
    """{narrator_id: [(form, type, source)]} for the non-observed name types, optionally for some narrators only."""
    marks = ",".join("?" * len(RIWAYAT_FORM_TYPES))
    forms = defaultdict(list)
    if narrator_ids is None:
        rows = connection.execute(f"select narrator_id, form, type, source from narrator_name where type in ({marks}) "
                                  "order by narrator_id, type, source, form", RIWAYAT_FORM_TYPES)
    else:
        ids = sorted(narrator_ids)
        rows = []
        for start in range(0, len(ids), 500):
            chunk = ids[start:start + 500]
            rows.extend(connection.execute(
                f"select narrator_id, form, type, source from narrator_name where type in ({marks}) and narrator_id "
                f"in ({','.join('?' * len(chunk))}) order by narrator_id, type, source, form",
                (*RIWAYAT_FORM_TYPES, *chunk)))
    for narrator_id, form, form_type, source in rows:
        forms[narrator_id].append((form, form_type, source))
    return forms


def main() -> None:
    started = time.time()
    random.seed("external-identity-sidecars-v1")
    canon = rc.Canon()
    regen = canon.regen
    xio.progress(started, "canonical normalizer, extractor and lexicon loaded")
    crosswalk = load_crosswalk()
    hadith_ids = {f"hadith:{record_id}" for record_id in crosswalk}
    mentions = load_mentions(hadith_ids)
    k6_claims = load_k6_claims()
    xio.progress(started, f"crosswalk reports {len(crosswalk)}, with mentions {len(mentions)}, K6 mentions {len(k6_claims)}")

    kg_conn, riw_conn = xio.connect(xio.HADITH_KG), xio.connect(xio.RIWAYAT)
    kg_people = kg_narrators(kg_conn)
    riw_people = {}
    riw_columns = ("id", "std_name", "std_name_source", "tradition", "death_year", "birth_year", "tabaqa", "city",
                   "death_city", "madhhab", "tribe_nisba", "family", "n_sources")
    for row in riw_conn.execute(f"select {', '.join(riw_columns)} from narrator order by id"):
        riw_people[row[0]] = dict(zip(riw_columns, row))
    xio.progress(started, f"narrators: hadith-kg {len(kg_people)}, Riwayat {len(riw_people)}")

    # --- external chains of matched reports ------------------------------------------------------------------------
    chains = {}
    for number, record_id in enumerate(sorted(crosswalk)):
        for dataset, row in crosswalk[record_id].items():
            fetch = fetch_kg_chain if dataset == KG else fetch_riwayat_chain
            chains[(record_id, dataset)] = fetch(kg_conn if dataset == KG else riw_conn, row["external_report_id"])
        if number % 10000 == 0:
            xio.progress(started, f"external chains fetched for {number} reports")
    needed_riw = {item[0].removeprefix(logic.ID_PREFIX[RIW]) for (record, dataset), items in chains.items()
                  if dataset == RIW for item in items if item[0].startswith(logic.ID_PREFIX[RIW])}
    chain_forms = riwayat_forms(riw_conn, needed_riw)

    def best_name(external_id: str) -> str:
        if external_id.startswith(logic.ID_PREFIX[KG]):
            person = kg_people.get(int(external_id.removeprefix(logic.ID_PREFIX[KG])))
            return (person or {}).get("name") or ""
        person = riw_people.get(external_id.removeprefix(logic.ID_PREFIX[RIW]))
        return (person or {}).get("std_name") or ""

    forms_by_id = {}
    for rawi_id, person in kg_people.items():
        forms_by_id[kg_id(rawi_id)] = [person["name"] or "", person["nickname"] or ""]
    for narrator_id in needed_riw:
        person = riw_people.get(narrator_id, {})
        forms_by_id[riw_id(narrator_id)] = [person.get("std_name") or ""] + [f for f, _, _ in chain_forms[narrator_id]]
    for external_id in list(forms_by_id):
        forms_by_id[external_id] += [regen.strip_blessing_formulas(regen.narrator_fold_normalize(f))
                                     for f in forms_by_id[external_id]]
    names = logic.ExternalNames(canon.comparison_key, forms_by_id)
    placeholder_cache = {}

    def placeholder(external_id: str) -> str:
        if external_id not in placeholder_cache:
            reason = logic.external_name_placeholder(rs.name_key(best_name(external_id)))
            if not reason and external_id.startswith(logic.ID_PREFIX[KG]):
                person = kg_people.get(int(external_id.removeprefix(logic.ID_PREFIX[KG])))
                if person is None or person["is_stub"]:
                    reason = logic.KG_STUB
            placeholder_cache[external_id] = reason
        return placeholder_cache[external_id]

    xio.progress(started, f"name stand-in registry: {len(names.registry)} external ids")

    # --- alignment and per-mention claims --------------------------------------------------------------------------
    claims = []          # compact tuples, expanded at write time
    report_info = {}
    stats = defaultdict(Counter)
    for number, (record_id, dataset) in enumerate(sorted(chains)):
        row = crosswalk[record_id][dataset]
        hadith_id = f"hadith:{record_id}"
        branches_with_ids = mentions.get(hadith_id, [])
        branches = [[surface for _, surface in branch] for branch in branches_with_ids]
        items = chains[(record_id, dataset)]
        ids = [item[0] for item in items]
        label, tiers, pairs = classify(names, ids, branches)
        report_info[(record_id, dataset)] = {"class": label, "row": row, "external_length": len(ids),
                                             "our_branch_lengths": [len(b) for b in branches]}
        stats["report_class"][f"{dataset}:{row['tradition']}:{label}"] += 1
        if not pairs:
            continue
        sidecar_like = {"record_id": record_id, "text_branches": branches,
                        "aligned_positions": [{"source_position": i, "branch": b, "branch_position": j}
                                              for i, b, j, _ in pairs]}
        mapping = align_source_index(sidecar_like, branches)
        tier_at = {(b, j): tier for _, b, j, tier in pairs}
        for (b, j), (i, shared) in sorted(mapping.items()):
            external_id = ids[i]
            reason = placeholder(external_id)
            if reason in logic.DROPPED_PLACEHOLDERS:
                stats["claims_dropped_placeholder"][f"{dataset}:{row['tradition']}:{reason}"] += 1
                continue
            basis = logic.mention_basis(dataset, label, reason)
            mention_id = branches_with_ids[b][j][0]
            if mention_id in INHERITED_MENTIONS:
                stats["claims_skipped_inherited_mention"][f"{dataset}:{row['tradition']}"] += 1
                continue
            claims.append((mention_id, dataset, record_id, b, j, i, external_id, tier_at.get((b, j)), shared, basis,
                           reason))
            stats["claims_by_basis"][f"{dataset}:{row['tradition']}:{basis}"] += 1
        if number % 10000 == 0:
            xio.progress(started, f"aligned {number} report/dataset pairs; claims {len(claims)}")

    # --- K6 co-occurrence (evidence for lexicon links) -------------------------------------------------------------
    pair_count, external_total, lexicon_total = Counter(), Counter(), Counter()
    for mention_id, dataset, *_rest in claims:
        external_id = _rest[4]
        for scholar in k6_claims.get(mention_id, ()):
            pair_count[(external_id, scholar)] += 1
            external_total[external_id] += 1
            lexicon_total[(dataset, scholar)] += 1

    # --- lexicon links -----------------------------------------------------------------------------------------------
    lexicon = rs.load_lexicon()
    lexicon_years = defaultdict(list)
    for scholar, rows in rs.load_lexicon_candidates().items():
        for item in rows:
            if (item["predicate"] == "death_year" and item.get("calendar") == "hijri"
                    and item.get("precision") != "zero_placeholder_suspected"
                    and (item.get("year_min") is not None or item.get("year_max") is not None)):
                lexicon_years[scholar].append((item["year_min"], item["year_max"]))
    lexicon_by_key = defaultdict(set)
    lexicon_name = {}
    for entry in lexicon:
        lexicon_name[entry["scholar_indx"]] = entry["arabic_name"]
        if entry["key"] and not entry["placeholder_reason"]:
            lexicon_by_key[entry["key"]].add(entry["scholar_indx"])
    xio.progress(started, "lexicon keys and years loaded")

    contexts = {KG: {kg_id(k): v for k, v in kg_context(kg_conn).items()},
                RIW: {riw_id(k): v for k, v in riwayat_context(riw_conn).items()}}
    xio.progress(started, "tradition contexts aggregated")
    keys_by_external = {}
    for rawi_id, person in kg_people.items():
        keys_by_external[kg_id(rawi_id)] = {rs.name_key(person["name"] or ""), rs.name_key(person["nickname"] or "")}
    all_riw_key_forms = defaultdict(set)
    for narrator_id, form in riw_conn.execute(
            "select narrator_id, form from narrator_name where type in (?, ?)", RIWAYAT_KEY_TYPES):
        all_riw_key_forms[narrator_id].add(form)
    for narrator_id, person in riw_people.items():
        keys_by_external[riw_id(narrator_id)] = {rs.name_key(f) for f in all_riw_key_forms.get(narrator_id, set())
                                                 | {person["std_name"] or ""}}
    del all_riw_key_forms
    external_by_key = {KG: defaultdict(set), RIW: defaultdict(set)}
    for external_id, keys in keys_by_external.items():
        dataset = KG if external_id.startswith(logic.ID_PREFIX[KG]) else RIW
        keys.discard("")
        for key in keys:
            external_by_key[dataset][key].add(external_id)

    def external_years(external_id: str):
        if external_id.startswith(logic.ID_PREFIX[KG]):
            parsed = _raw_years(kg_people[int(external_id.removeprefix(logic.ID_PREFIX[KG]))]["death_year_raw"])
            return (parsed["year_min"], parsed["year_max"]) if parsed and parsed["year_min"] is not None else None
        year = riw_people[external_id.removeprefix(logic.ID_PREFIX[RIW])]["death_year"]
        return (year, year) if year is not None else None

    links, link_evidence = {}, {}
    proposals = defaultdict(list)
    for external_id, keys in sorted(keys_by_external.items()):
        dataset = KG if external_id.startswith(logic.ID_PREFIX[KG]) else RIW
        if placeholder(external_id):        # placeholder names and hadith-kg stubs never link
            continue
        matched = set()
        for key in keys:
            if len(external_by_key[dataset][key]) == 1 and logic.external_name_placeholder(key) == "":
                matched |= lexicon_by_key.get(key, set())
        candidates = set()
        for key in keys:
            owners = lexicon_by_key.get(key, set())
            if owners and len(owners) == 1 and len(external_by_key[dataset][key]) == 1:
                candidates |= owners
            elif owners:
                candidates.add(None)            # a key shared on our side poisons the match
        name_unique = len(candidates) == 1 and None not in candidates
        if not matched and not candidates:
            continue
        scholar = next(iter(candidates)) if name_unique else None
        context = contexts[dataset].get(external_id, Counter())
        sunni_context = context.get("Sunni", 0) > 0
        ext_years = external_years(external_id)
        lex_years = lexicon_years.get(scholar, []) if scholar else []
        year_agrees = bool(ext_years and any(logic.years_overlap(a, b, *ext_years) for a, b in lex_years))
        year_conflicts = bool(ext_years and lex_years and not year_agrees)
        shared = pair_count.get((external_id, scholar), 0) if scholar else 0
        k6 = bool(scholar) and logic.k6_agrees(shared, external_total[external_id], lexicon_total[(dataset, scholar)])
        basis = logic.link_decision(name_unique, sunni_context, year_agrees, k6, year_conflicts)
        stats["link_outcome"][f"{dataset}:{basis or ('no_link:not_unique' if not name_unique else 'no_link:no_sunni_context' if not sunni_context else 'no_link:year_conflict' if year_conflicts else 'no_link:no_corroboration')}"] += 1
        if basis:
            proposals[(dataset, scholar)].append(external_id)
            link_evidence[external_id] = {
                "scholar_indx": scholar, "basis": basis, "lexicon_arabic_name": lexicon_name.get(scholar),
                "external_name": best_name(external_id), "external_death_years": ext_years,
                "lexicon_death_years": sorted(lex_years, key=lambda y: (y[0] or 0, y[1] or 0)),
                "k6_shared_mentions": shared, "k6_external_comentions": external_total[external_id],
                "k6_lexicon_comentions": lexicon_total[(dataset, scholar)], "tradition_context": dict(context)}
    for (dataset, scholar), external_ids in proposals.items():
        if len(external_ids) == 1:
            links[external_ids[0]] = link_evidence[external_ids[0]]
        else:
            stats["link_outcome"][f"{dataset}:no_link:lexicon_row_claimed_by_several_externals"] += len(external_ids)

    # Riwayat narrators whose explicit kg crosswalk points at a linked hadith-kg narrator.
    riw_crosswalk = defaultdict(lambda: defaultdict(list))
    for narrator_id, source, source_id in riw_conn.execute(
            "select narrator_id, source, source_id from narrator_source_id order by narrator_id, source, source_id"):
        riw_crosswalk[narrator_id][source].append(source_id)
    kg_to_riw = defaultdict(list)
    for narrator_id, sources in riw_crosswalk.items():
        for source_id in sources.get("kg", ()):
            kg_to_riw[source_id].append(narrator_id)
    linked_scholars = {(RIW, link["scholar_indx"]) for eid, link in links.items() if eid.startswith(logic.ID_PREFIX[RIW])}
    via = defaultdict(list)
    for narrator_id, sources in riw_crosswalk.items():
        external_id = riw_id(narrator_id)
        kg_ids = sources.get("kg", [])
        if len(kg_ids) != 1 or kg_id(kg_ids[0]) not in links:
            continue
        target = links[kg_id(kg_ids[0])]
        if external_id in links:
            stats["crosswalk_check"]["direct_link_equals_crosswalk" if links[external_id]["scholar_indx"]
                                     == target["scholar_indx"] else "direct_link_differs_from_crosswalk"] += 1
            continue
        if contexts[RIW].get(external_id, Counter()).get("Sunni", 0) == 0:
            continue
        via[target["scholar_indx"]].append((external_id, kg_ids[0], target))
    for scholar, entries in via.items():
        if len(entries) == 1 and (RIW, scholar) not in linked_scholars:
            external_id, source_id, target = entries[0]
            links[external_id] = {**{k: target[k] for k in ("scholar_indx", "lexicon_arabic_name", "lexicon_death_years")},
                                  "basis": logic.LINK_CROSSWALK, "external_name": best_name(external_id),
                                  "via_hadith_kg": kg_id(source_id), "via_basis": target["basis"],
                                  "tradition_context": dict(contexts[RIW].get(external_id, Counter()))}
        else:
            stats["link_outcome"]["riwayat:no_link:crosswalk_target_shared"] += len(entries)
    for external_id, link in links.items():
        stats["links_by_basis"][f"{'hadith_kg' if external_id.startswith(logic.ID_PREFIX[KG]) else 'riwayat'}:{link['basis']}"] += 1
    xio.progress(started, f"lexicon links: {dict(stats['links_by_basis'])}")

    # --- write: links, mention claims ------------------------------------------------------------------------------
    link_rows = [{"external_narrator_id": eid, **link, "review_state": "unreviewed",
                  "meaning": "candidate link between an external narrator and a lexicon row; not an identification"}
                 for eid, link in sorted(links.items())]
    outputs = {"links": io_.write_jsonl_gz("external_narrator_lexicon_links.jsonl.gz", link_rows)}

    def claim_rows():
        for (mention_id, dataset, record_id, b, j, i, external_id, tier, shared, basis, reason) in sorted(
                claims, key=lambda c: (c[0], c[1])):
            info = report_info[(record_id, dataset)]
            row = info["row"]
            item = chains[(record_id, dataset)][i]
            detail = item[3] or {}
            link = links.get(external_id)
            out = {
                "mention_id": mention_id, "hadith_id": f"hadith:{record_id}", "record_id": record_id,
                "tradition": row["tradition"], "source_work_id": row["source_work_id"],
                "branch": b, "position": j, "surface_ar": mentions[f"hadith:{record_id}"][b][j][1],
                "dataset": dataset, "basis": basis,
                "external_report_id": row["external_report_id"], "report_match_class": row["match_class"],
                "external_chain": item[1], "external_position": item[2], "external_list_index": i,
                "external_narrator_id": external_id, "external_narrator_name": best_name(external_id),
                "external_name_flag": reason or None,
                "report_agreement_class": info["class"], "name_tier": tier, "shared_trunk": shared,
                "agreement_detail": info["class"] + (f":{tier}" if tier else "") + (":shared_trunk" if shared else ""),
                "lexicon_scholar_indx": link["scholar_indx"] if link else None,
                "lexicon_link_basis": link["basis"] if link else None,
                "review_state": "unreviewed",
            }
            if dataset == RIW:
                out.update({"external_surface": detail.get("surface"), "external_id_method": detail.get("id_method"),
                            "external_id_confidence": detail.get("id_confidence"),
                            "external_id_origin": logic.riwayat_id_origin(detail.get("id_method") or "")})
            yield out

    outputs["claims"] = io_.write_jsonl_gz("external_mention_claims.jsonl.gz", claim_rows())
    xio.progress(started, f"claims written: {outputs['claims']['rows']}")

    # --- registries --------------------------------------------------------------------------------------------------
    riw_flags = defaultdict(list)
    for narrator_id, flag in riw_conn.execute("select narrator_id, flag from narrator_flag order by narrator_id, flag"):
        riw_flags[narrator_id].append(flag)
    claimed_mentions = Counter(c[6] for c in claims)

    def kg_registry():
        for rawi_id in sorted(kg_people):
            person = kg_people[rawi_id]
            external_id = kg_id(rawi_id)
            assertions = {k: person[k] for k in ("rank", "rank_no", "tabaka", "birth_year_raw", "death_year_raw",
                                                 "age_raw", "iqama", "death_place", "nasab", "profession",
                                                 "is_bukhari", "is_muslim", "has_tadlis", "has_ikhtilat",
                                                 "riwaya_qty", "is_stub") if person[k] not in (None, "")}
            yield {"external_narrator_id": external_id, "dataset": KG, "rawi_id": rawi_id,
                   "name_ar": person["name"], "popular_name_ar": person["nickname"],
                   "dataset_assertions": assertions, "asserted_by": "hadith-kg (verbatim; not verified here)",
                   "tradition_context_chain_positions": dict(contexts[KG].get(external_id, Counter())),
                   "riwayat_narrators_crosswalked_here": sorted(kg_to_riw.get(str(rawi_id), [])),
                   "name_placeholder_reason": placeholder(external_id) or None,
                   "claims_in_our_mentions": claimed_mentions.get(external_id, 0),
                   "lexicon_link": ({k: links[external_id][k] for k in ("scholar_indx", "basis")}
                                    if external_id in links else None),
                   "review_state": "unreviewed"}

    outputs["hadith_kg_narrators"] = io_.write_jsonl_gz("hadith_kg_narrators.jsonl.gz", kg_registry())
    all_forms = riwayat_forms(riw_conn)
    observed = Counter(dict(riw_conn.execute(
        "select narrator_id, count(*) from narrator_name where type = 'observed' group by narrator_id").fetchall()))

    def riw_registry():
        for narrator_id in sorted(riw_people):
            person = riw_people[narrator_id]
            external_id = riw_id(narrator_id)
            assertions = {k: person[k] for k in ("death_year", "birth_year", "tabaqa", "city", "death_city", "madhhab",
                                                 "tribe_nisba", "family", "n_sources") if person[k] not in (None, "")}
            yield {"external_narrator_id": external_id, "dataset": RIW, "narrator_id": narrator_id,
                   "name_ar": person["std_name"], "name_source": person["std_name_source"],
                   "tradition_label": person["tradition"], "dataset_assertions": assertions,
                   "asserted_by": "Riwayat corpus (verbatim; not verified here)",
                   "name_forms": [{"form": f, "type": t, "source": s} for f, t, s in all_forms.get(narrator_id, [])],
                   "observed_chain_forms": observed.get(narrator_id, 0),
                   "crosswalk": {k: v for k, v in sorted(riw_crosswalk.get(narrator_id, {}).items())},
                   "flags": riw_flags.get(narrator_id, []),
                   "tradition_context_mentions": dict(contexts[RIW].get(external_id, Counter())),
                   "name_placeholder_reason": placeholder(external_id) or None,
                   "claims_in_our_mentions": claimed_mentions.get(external_id, 0),
                   "lexicon_link": ({k: links[external_id][k] for k in ("scholar_indx", "basis")}
                                    if external_id in links else None),
                   "review_state": "unreviewed"}

    outputs["riwayat_narrators"] = io_.write_jsonl_gz("riwayat_narrators.jsonl.gz", riw_registry())
    del all_forms
    xio.progress(started, "registries written")

    # --- Qur'an quotation spans (hadith-kg) ------------------------------------------------------------------------
    kg_reports = {record_id: datasets[KG] for record_id, datasets in crosswalk.items() if KG in datasets}
    texts = {}
    for row in xio.iter_corpus():
        if row["record_id"] in kg_reports:
            texts[row["record_id"]] = row["text_ar"] or ""
    char_cache = {}

    def normalize_char(char):
        if char not in char_cache:
            char_cache[char] = regen.narrator_normalize(char)
        return char_cache[char]

    quran_rows, quran_stats = [], Counter()
    for record_id in sorted(kg_reports):
        row = kg_reports[record_id]
        spans = kg_conn.execute("select seq, start, end from hadith_ayas where hadith_id = ? order by seq",
                                (int(row["external_report_id"]),)).fetchall()
        if not spans:
            continue
        nass = kg_conn.execute("select nass from hadiths where id = ?", (int(row["external_report_id"]),)).fetchone()[0]
        text = texts[record_id]
        letters, origins, starts, ends = logic.letters_with_origins(text, normalize_char)
        whole, _ = logic.skeleton_words(regen.narrator_normalize(text))
        if letters != whole:
            quran_stats["not_relocated:per_character_normalization_differs"] += len(spans)
            continue
        for seq, start, end in spans:
            quote, references = logic.parse_quran_span(nass[start:end])
            needle, _ = logic.skeleton_words(regen.narrator_normalize(quote))
            quran_stats["spans_in_matched_reports"] += 1
            quran_stats[f"by_match_class:{row['match_class']}:spans"] += 1
            if len(needle) < MIN_QUOTE_LETTERS:
                quran_stats[f"not_relocated:quote_under_{MIN_QUOTE_LETTERS}_letters"] += 1
                continue
            hit = logic.relocate_unique(needle, letters, starts, ends)
            if hit is None:
                outcome = "repeated_in_our_text" if needle in letters else "absent_from_our_text"
                quran_stats["not_relocated:" + outcome] += 1
                quran_stats[f"by_match_class:{row['match_class']}:not_relocated:{outcome}"] += 1
                continue
            begin, finish = logic.original_span(text, origins, hit, len(needle))
            quran_stats["relocated"] += 1
            quran_stats[f"by_match_class:{row['match_class']}:relocated"] += 1
            quran_stats["relocated_with_reference" if references else "relocated_without_reference"] += 1
            if any(ref["sura_number"] is None for ref in references):
                quran_stats["reference_sura_name_unrecognised"] += 1
            quran_rows.append({
                "record_id": record_id, "hadith_id": f"hadith:{record_id}", "tradition": row["tradition"],
                "source_work_id": row["source_work_id"], "arabic_sha256": row["arabic_sha256"],
                "start": begin, "end": finish, "quote_ar": text[begin:finish],
                "quote_sha256": io_.sha256_text(text[begin:finish]),
                "references": references, "reference_count": len(references),
                "basis": "source_hadith_kg", "external_report_id": row["external_report_id"],
                "external_seq": seq, "external_span": [start, end],
                "external_arabic_sha256": row["external_arabic_sha256"],
                "offsets": "Unicode code points of our text_ar, [start, end)", "review_state": "unreviewed"})
    outputs["quran"] = io_.write_jsonl_gz("hadith_kg_quran_citations.jsonl.gz", quran_rows)
    kg_conn.close()
    riw_conn.close()

    here = Path(__file__).resolve()
    io_.write_manifest("external_identity_sidecars.manifest.json", {
        "artifact": "external_identity_sidecars", "status": "sidecar_unreviewed_not_a_release_input",
        "meaning": "External narrator registries (each dataset's own description), candidate lexicon links, per-mention "
                   "source claims keyed by our mention id, and hadith-kg Qur'an quotation spans re-located in our "
                   "text. A source id is that source's claim; nothing here is verified.",
        "command": "python -B datasets/hadith-data/reconciled/build_external_identity_sidecars.py",
        "licence": xio.LICENCE,
        "inputs_sha256": {
            **common.input_fingerprints(io_.RECONCILED_DIR / xio.CROSSWALK, xio.CORPUS, xio.HADITH_KG, xio.RIWAYAT,
                                        common.REGISTRY_PATH, rs.LEXICON_CANDIDATES,
                                        xio.PROJECTION / "chain_mentions.csv",
                                        xio.PROJECTION / "chain_mention_candidates.csv",
                                        xio.PROJECTION / "manifest.json")},
        "code_sha256": io_.code_fingerprints(
            here, io_.RECONCILED_DIR / "external_source_logic.py", io_.RECONCILED_DIR / "external_source_io.py",
            io_.RECONCILED_DIR / "sidecar_io.py", io_.RECONCILE_DIR / "reconcile_common.py",
            io_.RECONCILE_DIR / "measure_source_index_agreement.py",
            common.HADITH_DATA_DIR / "pg_export" / "export_postgres.py",
            common.DIAGNOSTICS_DIR / "biography-verification" / "rijal_sources.py",
            common.DIAGNOSTICS_DIR / "name_invariant.py",
            common.HADITH_DATA_DIR / "regen_unified_csvs.py", common.HADITH_DATA_DIR / "extract_isnad_unified.py"),
        "not_imported": NOT_IMPORTED,
        "outputs": outputs,
        "counts": {k: dict(sorted(v.items())) for k, v in sorted(stats.items())},
        "quran": dict(sorted(quran_stats.items())),
    })
    xio.progress(started, json.dumps({k: v["rows"] for k, v in outputs.items()}))


if __name__ == "__main__":
    main()
