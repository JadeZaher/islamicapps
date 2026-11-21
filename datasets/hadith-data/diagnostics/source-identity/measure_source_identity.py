#!/usr/bin/env python3
"""Measure what the hadith-kg / Riwayat sidecars add to chain identity, and how the three sources agree.

Reads the reconciled sidecars (external_report_crosswalk, external_mention_claims, *_narrators,
external_narrator_lexicon_links, hadith_kg_quran_citations), the loaded projection (mentions and today's candidates)
and the corpus, all read-only. Writes measurements, the Imami 60-mention sample and the 150-row review worksheet
into this directory. See README.md. Usage (repo root):
    python -B datasets/hadith-data/diagnostics/source-identity/measure_source_identity.py
"""

import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
RECONCILED = Path(__file__).resolve().parents[2] / "reconciled"
sys.path.insert(0, str(RECONCILED))
import external_source_io as xio  # noqa: E402
import external_source_logic as logic  # noqa: E402

common = xio.common
OUT = common.output_directory("source-identity")
SEED = "source-identity-v1"
K6_BASES = ("source_index", "source_index_confirmed_by_text")
TRADITIONS = ("Sunni", "Imami", "Ibadi", "Zaydi")
WORKSHEET_QUOTAS = (   # (tradition, dataset, confirmed, rows); 150 in total
    ("Sunni", "hadith_kg", True, 20), ("Sunni", "hadith_kg", False, 15),
    ("Sunni", "riwayat", True, 15), ("Sunni", "riwayat", False, 10),
    ("Imami", "riwayat", True, 30), ("Imami", "riwayat", False, 25),
    ("Ibadi", "hadith_kg", None, 8), ("Ibadi", "riwayat", None, 7),
    ("Zaydi", "hadith_kg", None, 10), ("Zaydi", "riwayat", None, 10),
)


def pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


def stable_sample(claims, size, salt):
    """The `size` claims with the smallest SHA-256(salt, mention id): reproducible, and unaffected by changes to
    unrelated rows (a rebuild that adds or drops other claims leaves an existing pick in the sample)."""
    def rank(claim):
        return hashlib.sha256(f"{SEED}|{salt}|{claim['mention_id']}|{claim['dataset']}".encode()).hexdigest()
    return sorted(sorted(claims, key=rank)[:size], key=lambda c: c["mention_id"])


def main() -> None:
    started = time.time()
    rng = random.Random(SEED)
    regen = common.load_regen()

    # Our reports: tradition and work by record_id.
    report = {}
    for row in xio.iter_corpus():
        report[row["record_id"]] = (row["tradition"], row["source_work_id"] or row["source"])
    xio.progress(started, f"corpus: {len(report)} reports")

    # Projection: every mention, and today's candidates.
    mention_report, mention_surface = {}, {}
    branches = defaultdict(lambda: defaultdict(dict))
    for row in xio.iter_projection("chain_mentions.csv"):
        record_id = row["hadith_id"].removeprefix("hadith:")
        mention_report[row["id"]] = record_id
        mention_surface[row["id"]] = row["surface_ar"]
        branches[record_id][int(row["chain_id"].rsplit(":", 1)[1])][int(row["position"])] = row["id"]
    today_any, k6 = set(), defaultdict(set)
    k6_confirmed = set()
    for row in xio.iter_projection("chain_mention_candidates.csv"):
        today_any.add(row["mention_id"])
        if row["basis"] in K6_BASES:
            k6[row["mention_id"]].add(row["narrator_id"].removeprefix("narrator:rawi:"))
            if row["basis"] == "source_index_confirmed_by_text":
                k6_confirmed.add(row["mention_id"])
    xio.progress(started, f"projection: {len(mention_report)} mentions, {len(today_any)} with a candidate today")

    # Sidecars.
    claims = defaultdict(list)
    for row in xio.read_jsonl_gz(RECONCILED / "external_mention_claims.jsonl.gz"):
        claims[row["mention_id"]].append(row)
    links = {row["external_narrator_id"]: row for row in xio.read_jsonl_gz(
        RECONCILED / "external_narrator_lexicon_links.jsonl.gz")}
    riwayat_registry = {}
    for row in xio.read_jsonl_gz(RECONCILED / "riwayat_narrators.jsonl.gz"):
        riwayat_registry[row["external_narrator_id"]] = row
    kg_registry = {row["external_narrator_id"]: row for row in xio.read_jsonl_gz(RECONCILED / "hadith_kg_narrators.jsonl.gz")}
    lexicon_name = {}
    with open(common.REGISTRY_PATH, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            lexicon_name[row["scholar_indx"].strip()] = regen._extract_arabic_name(row["name"])
    xio.progress(started, f"sidecars: {sum(len(v) for v in claims.values())} claims on {len(claims)} mentions")

    def confirmed(claim):
        return claim["basis"].endswith("_confirmed_by_text")

    # --- gains on today's unidentified mentions ----------------------------------------------------------------------
    gains = {"by_tradition": defaultdict(Counter), "by_work": defaultdict(Counter),
             "by_tradition_agreement_class": defaultdict(Counter)}
    for mention_id, record_id in mention_report.items():
        tradition, work = report[record_id]
        bucket = "identified_today" if mention_id in today_any else "unidentified_today"
        mine = claims.get(mention_id, [])
        datasets = {c["dataset"] for c in mine}
        outcome = ("no_external_claim" if not mine else
                   "external_confirmed_by_text" if any(confirmed(c) for c in mine) else "external_unconfirmed_only")
        for key, counter_key in (("by_tradition", tradition), ("by_work", f"{tradition}|{work}")):
            gains[key][counter_key][f"{bucket}"] += 1
            gains[key][counter_key][f"{bucket}:{outcome}"] += 1
            for dataset in sorted(datasets):
                dataset_confirmed = any(confirmed(c) for c in mine if c["dataset"] == dataset)
                gains[key][counter_key][f"{bucket}:{dataset}:{'confirmed' if dataset_confirmed else 'unconfirmed'}"] += 1
            if len(datasets) == 2:
                gains[key][counter_key][f"{bucket}:both_datasets"] += 1
        for claim in mine:
            gains["by_tradition_agreement_class"][tradition][
                f"{bucket}:{claim['dataset']}:{claim['report_agreement_class']}"] += 1
    gains_out = {key: {k: dict(sorted(v.items())) for k, v in sorted(value.items())} for key, value in gains.items()}
    summary_gain = {}
    for tradition in TRADITIONS:
        counts = gains["by_tradition"][tradition]
        unidentified = counts["unidentified_today"]
        gained = unidentified - counts["unidentified_today:no_external_claim"]
        summary_gain[tradition] = {
            "mentions": counts["identified_today"] + unidentified, "unidentified_today": unidentified,
            "gain_any_source_claim": gained, "gain_percent": pct(gained, unidentified),
            "gain_confirmed_by_text": counts["unidentified_today:external_confirmed_by_text"],
            "gain_unconfirmed_only": counts["unidentified_today:external_unconfirmed_only"]}

    # Riwayat id origin on gained Imami mentions (who asserted the id).
    origin = Counter()
    for mention_id, mine in claims.items():
        for claim in mine:
            if claim["dataset"] == "riwayat":
                origin[f"{claim['tradition']}:{claim['external_id_origin']}:{'confirmed' if confirmed(claim) else 'unconfirmed'}"] += 1

    # --- reports with every name carrying a source claim ------------------------------------------------------------
    complete = defaultdict(Counter)
    for record_id, by_branch in branches.items():
        tradition, _ = report[record_id]
        ids = [m for branch in by_branch.values() for m in branch.values()]
        complete[tradition]["reports_with_chain"] += 1
        source_any = all((m in k6) or claims.get(m) for m in ids)
        source_confirmed = all((m in k6_confirmed) or any(confirmed(c) for c in claims.get(m, [])) for m in ids)
        external_any = all(claims.get(m) for m in ids)
        today = all(m in k6 for m in ids)
        complete[tradition]["every_name_has_k6_claim_today"] += today
        complete[tradition]["every_name_has_a_source_claim_k6_or_external"] += source_any
        complete[tradition]["every_name_has_a_confirmed_source_claim"] += source_confirmed
        complete[tradition]["every_name_has_an_external_claim"] += external_any

    # --- three-way agreement on Sunni mentions -----------------------------------------------------------------------
    def dominant(pairs):
        """{key: (partner, count, total)} for the most frequent partner of each key."""
        grouped = defaultdict(Counter)
        for key, partner in pairs:
            grouped[key][partner] += 1
        return {key: (*counter.most_common(1)[0], sum(counter.values())) for key, counter in grouped.items()}

    agreement = {}
    examples = {}
    riw_to_kg = {eid: {f"hadith-kg:rawi:{x}" for x in row["crosswalk"].get("kg", [])}
                 for eid, row in riwayat_registry.items() if row["crosswalk"].get("kg")}
    for dataset in ("hadith_kg", "riwayat"):
        pairs = []
        rows = []
        for mention_id, mine in claims.items():
            if mention_id not in k6:
                continue
            for claim in mine:
                if claim["dataset"] != dataset or claim["tradition"] != "Sunni":
                    continue
                for scholar in sorted(k6[mention_id]):
                    pairs.append((claim["external_narrator_id"], scholar))
                    rows.append((mention_id, claim, scholar))
        by_external = dominant(pairs)
        by_lexicon = dominant([(s, e) for e, s in pairs])
        counts = Counter()
        disagreements = []
        for mention_id, claim, scholar in rows:
            external_id = claim["external_narrator_id"]
            mutual = by_external[external_id][0] == scholar and by_lexicon[scholar][0] == external_id
            both_confirmed = confirmed(claim) and mention_id in k6_confirmed
            counts["co_claimed_mentions"] += 1
            counts["mutual_dominant_pairing" if mutual else "not_mutual_dominant_pairing"] += 1
            if both_confirmed:
                counts["both_confirmed_by_text"] += 1
                counts["both_confirmed:" + ("mutual" if mutual else "not_mutual")] += 1
            link = links.get(external_id)
            if link and link["basis"] in (logic.LINK_YEAR, logic.LINK_BOTH):
                counts["via_year_link:" + ("same_narrator" if link["scholar_indx"] == scholar else "different_narrator")] += 1
            elif link:
                counts["via_k6_or_crosswalk_link_circular_excluded"] += 1
            else:
                counts["external_narrator_not_linked"] += 1
            if not mutual:
                disagreements.append({
                    "mention_id": mention_id, "surface_ar": claim["surface_ar"],
                    "k6_scholar_indx": scholar, "k6_lexicon_name": lexicon_name.get(scholar),
                    "external_narrator_id": external_id, "external_name": claim["external_narrator_name"],
                    "external_usual_lexicon_partner": by_external[external_id][0],
                    "external_usual_partner_name": lexicon_name.get(by_external[external_id][0]),
                    "external_basis": claim["basis"], "k6_confirmed": mention_id in k6_confirmed})
        distinct = Counter()
        for external_id, (_, top, total) in by_external.items():
            distinct["external_ids"] += 1
            distinct["external_ids_always_same_lexicon_id" if top == total else "external_ids_with_several_lexicon_ids"] += 1
        counts["mutual_percent"] = pct(counts["mutual_dominant_pairing"], counts["co_claimed_mentions"])
        counts["both_confirmed_mutual_percent"] = pct(counts["both_confirmed:mutual"], counts["both_confirmed_by_text"])
        year_total = counts["via_year_link:same_narrator"] + counts["via_year_link:different_narrator"]
        counts["via_year_link_same_percent"] = pct(counts["via_year_link:same_narrator"], year_total)
        agreement[f"k6_vs_{dataset}"] = {**dict(counts), **dict(distinct)}
        examples[f"k6_vs_{dataset}"] = stable_sample(
            [{**row, "dataset": dataset} for row in disagreements], 12, f"examples-{dataset}")

    # hadith-kg vs Riwayat at the same mention, through Riwayat's own kg crosswalk.
    cross = Counter()
    cross_examples = []
    for mention_id, mine in claims.items():
        by_dataset = defaultdict(list)
        for claim in mine:
            by_dataset[claim["dataset"]].append(claim)
        if not (by_dataset["hadith_kg"] and by_dataset["riwayat"]):
            continue
        for claim_r in by_dataset["riwayat"]:
            for claim_k in by_dataset["hadith_kg"]:
                key = f"{claim_r['tradition']}:"
                bridge = riw_to_kg.get(claim_r["external_narrator_id"])
                if not bridge:
                    cross[key + "riwayat_narrator_has_no_kg_crosswalk"] += 1
                elif claim_k["external_narrator_id"] in bridge:
                    cross[key + "same_narrator_by_riwayat_crosswalk"] += 1
                else:
                    cross[key + "different_narrator"] += 1
                    cross_examples.append({
                        "mention_id": mention_id, "dataset": "both", "surface_ar": claim_r["surface_ar"],
                        "riwayat": [claim_r["external_narrator_id"], claim_r["external_narrator_name"],
                                    claim_r["external_id_method"]],
                        "hadith_kg": [claim_k["external_narrator_id"], claim_k["external_narrator_name"]]})
                cross[key + "riwayat_id_origin:" + claim_r["external_id_origin"]] += 1
    agreement["hadith_kg_vs_riwayat"] = dict(sorted(cross.items()))
    examples["hadith_kg_vs_riwayat"] = stable_sample(cross_examples, 10, "examples-kg-vs-riwayat")

    # --- Riwayat Shi'i registry profile ------------------------------------------------------------------------------
    profile = Counter()
    key_owners = defaultdict(list)
    tokens_hist = Counter()
    imami_ids = []
    for external_id, row in riwayat_registry.items():
        context = row["tradition_context_mentions"]
        in_imami = context.get("Imami", 0) > 0
        if row["tradition_label"] == "shia":
            profile["labelled_shia"] += 1
        if not in_imami:
            continue
        imami_ids.append(external_id)
        profile["narrators_in_shii_chains"] += 1
        profile[f"label:{row['tradition_label']}"] += 1
        profile[f"name_source:{row['name_source']}"] += 1
        assertions = row["dataset_assertions"]
        for field in ("death_year", "birth_year", "tabaqa", "city", "death_city", "madhhab", "tribe_nisba", "family"):
            if field in assertions:
                profile[f"has:{field}"] += 1
        if any(f in assertions for f in ("death_year", "birth_year", "tabaqa", "city", "death_city", "madhhab")):
            profile["has_any_biographical_field"] += 1
        if row["crosswalk"].get("thq"):
            profile["has_thaqalayn_id"] += 1
        if row["crosswalk"].get("kg"):
            profile["has_hadith_kg_id"] += 1
        if row["crosswalk"].get("itq"):
            profile["has_itqan_id"] += 1
        if len(row["crosswalk"].get("thq", [])) > 1:
            profile["several_thaqalayn_ids"] += 1
        profile[f"placeholder:{row['name_placeholder_reason'] or 'person_like_name'}"] += 1
        name = row["name_ar"] or ""
        if name.strip().startswith("ـ"):
            profile["name_starts_with_tatweel_artefact"] += 1
        if "(" in name or "عليه السلام" in regen.narrator_normalize(name):
            profile["name_carries_blessing_or_parenthesis"] += 1
        key = regen.strip_blessing_formulas(regen.narrator_fold_normalize(name))
        tokens = key.split()
        tokens_hist[min(len(tokens), 6)] += 1
        if "بن" in tokens or "بنت" in tokens:
            profile["name_has_nasab"] += 1
        if tokens and tokens[0] in logic.KUNYA_HEADS:
            profile["name_starts_with_kunya"] += 1
        if key:
            key_owners[key].append(external_id)
        if row["claims_in_our_mentions"]:
            profile["claimed_in_our_mentions"] += 1
        if row["lexicon_link"]:
            profile["linked_to_lexicon"] += 1
        if row["flags"]:
            profile["with_quality_flag"] += 1
    duplicate_keys = {k: v for k, v in key_owners.items() if len(v) > 1}
    profile["names_shared_by_several_ids_keys"] = len(duplicate_keys)
    profile["names_shared_by_several_ids_narrators"] = sum(len(v) for v in duplicate_keys.values())
    duplicate_examples = [{"name_key": k, "narrators": [(e, riwayat_registry[e]["name_ar"],
                                                         riwayat_registry[e]["crosswalk"].get("thq"),
                                                         riwayat_registry[e]["tradition_context_mentions"].get("Imami"))
                                                        for e in v]}
                          for k, v in sorted(duplicate_keys.items(), key=lambda kv: -len(kv[1]))[:12]]
    mention_weight = Counter()
    for external_id in imami_ids:
        mention_weight[riwayat_registry[external_id]["name_placeholder_reason"] or "person_like_name"] += \
            riwayat_registry[external_id]["tradition_context_mentions"].get("Imami", 0)

    # --- Imami 60-mention sample -------------------------------------------------------------------------------------
    imami_claims = [c for mine in claims.values() for c in mine
                    if c["tradition"] == "Imami" and c["dataset"] == "riwayat"]
    sample = stable_sample(imami_claims, 60, "imami-sample")

    def context(mention_id):
        record_id = mention_report[mention_id]
        parts = mention_id.rsplit(":", 2)
        branch, position = int(parts[1]), int(parts[2])
        chain = branches[record_id][branch]
        student = mention_surface.get(chain.get(position - 1)) if position > 0 else ""
        teacher = mention_surface.get(chain.get(position + 1)) or ""
        return student or "", teacher

    sample_rows = []
    for claim in sample:
        student, teacher = context(claim["mention_id"])
        registry_row = riwayat_registry.get(claim["external_narrator_id"], {})
        sample_rows.append({
            "mention_id": claim["mention_id"], "work": claim["source_work_id"],
            "student_surface": student, "surface_ar": claim["surface_ar"], "teacher_surface": teacher,
            "riwayat_narrator_id": claim["external_narrator_id"], "riwayat_name": claim["external_narrator_name"],
            "riwayat_other_forms": " | ".join(sorted({f["form"] for f in registry_row.get("name_forms", [])})[:6]),
            "riwayat_surface_in_their_text": claim.get("external_surface"),
            "id_method": claim["external_id_method"], "id_origin": claim["external_id_origin"],
            "basis": claim["basis"], "agreement_detail": claim["agreement_detail"],
            "narrator_imami_mentions": registry_row.get("tradition_context_mentions", {}).get("Imami"),
        })
    write_csv("imami_sample_60.csv", sample_rows)
    judged = OUT / "imami_sample_60_judgement.csv"
    judgement_summary = {"file_present": judged.exists()}
    if judged.exists():
        with open(judged, encoding="utf-8", newline="") as handle:
            verdicts = {row["mention_id"]: row for row in csv.DictReader(handle)}
        by = Counter()
        for row in sample_rows:
            verdict = verdicts.get(row["mention_id"])
            if verdict is None or verdict["riwayat_narrator_id"] != row["riwayat_narrator_id"]:
                by["sample_row_without_current_judgement"] += 1
                continue
            by[f"judgement:{verdict['judgement']}"] += 1
            by[f"by_origin:{row['id_origin']}:{verdict['judgement']}"] += 1
            by[f"by_basis:{row['basis']}:{verdict['judgement']}"] += 1
        judgement_summary.update(dict(sorted(by.items())))

    # --- 150-row review worksheet ------------------------------------------------------------------------------------
    pools = defaultdict(list)
    for mine in claims.values():
        for claim in mine:
            pools[(claim["tradition"], claim["dataset"], confirmed(claim))].append(claim)
    worksheet = []
    def pool_of(tradition, dataset, is_confirmed):
        if is_confirmed is None:
            return pools[(tradition, dataset, True)] + pools[(tradition, dataset, False)]
        return pools[(tradition, dataset, is_confirmed)]

    # A stratum smaller than its quota (Zaydi has 8 + 6 claims) gives its shortfall to the Imami unconfirmed stratum.
    shortfall = sum(max(0, quota - len(pool_of(t, d, c))) for t, d, c, quota in WORKSHEET_QUOTAS)
    for tradition, dataset, is_confirmed, quota in WORKSHEET_QUOTAS:
        if (tradition, dataset, is_confirmed) == ("Imami", "riwayat", False):
            quota += shortfall
        pool = pool_of(tradition, dataset, is_confirmed)
        stratum_name = f"{tradition}|{dataset}|{is_confirmed}"
        for claim in stable_sample(pool, quota, stratum_name):
            student, teacher = context(claim["mention_id"])
            stratum = f"{tradition}|{dataset}|" + ("any" if is_confirmed is None else
                                                    "confirmed" if is_confirmed else "unconfirmed")
            worksheet.append({
                "stratum": stratum, "mention_id": claim["mention_id"], "record_id": claim["record_id"],
                "tradition": tradition, "work": claim["source_work_id"],
                "student_surface": student, "surface_ar": claim["surface_ar"], "teacher_surface": teacher,
                "dataset": dataset, "external_narrator_id": claim["external_narrator_id"],
                "external_name": claim["external_narrator_name"], "basis": claim["basis"],
                "agreement_detail": claim["agreement_detail"], "external_id_method": claim.get("external_id_method"),
                "lexicon_scholar_indx": claim["lexicon_scholar_indx"],
                "lexicon_name": lexicon_name.get(claim["lexicon_scholar_indx"] or ""),
                "k6_scholar_indx": "|".join(sorted(k6.get(claim["mention_id"], ()))),
                "reviewer_judgement": "", "reviewer_note": "", "reviewer": "", "reviewed_on": ""})
    write_csv("review_worksheet_150.csv", worksheet)

    # --- Qur'an coverage ---------------------------------------------------------------------------------------------
    quran, reports_with_quran, seen = Counter(), Counter(), set()
    for row in xio.read_jsonl_gz(RECONCILED / "hadith_kg_quran_citations.jsonl.gz"):
        quran[f"spans:{row['tradition']}|{row['source_work_id']}"] += 1
        if row["record_id"] not in seen:
            seen.add(row["record_id"])
            reports_with_quran[row["tradition"]] += 1
    identity_manifest = json.loads((RECONCILED / "external_identity_sidecars.manifest.json").read_text(encoding="utf-8"))

    result = {
        "header": common.header_object("source-identity", "python -B datasets/hadith-data/diagnostics/source-identity/"
                                       "measure_source_identity.py", common.input_fingerprints(
            RECONCILED / "external_report_crosswalk.jsonl.gz", RECONCILED / "external_mention_claims.jsonl.gz",
            RECONCILED / "external_narrator_lexicon_links.jsonl.gz", RECONCILED / "riwayat_narrators.jsonl.gz",
            RECONCILED / "hadith_kg_narrators.jsonl.gz", RECONCILED / "hadith_kg_quran_citations.jsonl.gz",
            xio.PROJECTION / "chain_mentions.csv", xio.PROJECTION / "chain_mention_candidates.csv", xio.CORPUS)),
        "licence": xio.LICENCE,
        "gain_summary": summary_gain,
        "gains": gains_out,
        "riwayat_id_origin_of_claims": dict(sorted(origin.items())),
        "reports_every_name_with_source_claim": {k: dict(v) for k, v in sorted(complete.items())},
        "agreement": agreement,
        "agreement_examples": examples,
        "imami_sample_60_judgement": judgement_summary,
        "riwayat_imami_registry_profile": {**dict(sorted(profile.items())),
                                           "name_token_count_histogram": dict(sorted(tokens_hist.items())),
                                           "imami_mentions_by_name_kind": dict(mention_weight),
                                           "duplicate_name_examples": duplicate_examples},
        "hadith_kg_registry": {"narrators": len(kg_registry),
                               "linked_to_lexicon": sum(1 for r in kg_registry.values() if r["lexicon_link"]),
                               "claimed_in_our_mentions": sum(1 for r in kg_registry.values() if r["claims_in_our_mentions"])},
        "lexicon_links_by_basis": dict(Counter(f"{'hadith_kg' if e.startswith('hadith-kg') else 'riwayat'}:{r['basis']}"
                                               for e, r in links.items())),
        "quran": {"build": identity_manifest["quran"], "reports_with_relocated_span": dict(reports_with_quran),
                  "spans_by_work": {k.removeprefix('spans:'): v for k, v in sorted(quran.items()) if k.startswith("spans:")}},
        "runtime_seconds": round(time.time() - started, 1),
    }
    common.write_json(OUT, "source_identity_measurements.json", result)
    print(json.dumps({"gain": summary_gain, "complete": result["reports_every_name_with_source_claim"],
                      "agreement": agreement}, ensure_ascii=False, indent=1))


def write_csv(name, rows):
    handle, _ = common.open_output(OUT, name)
    with handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
