"""Cut a small, referentially closed slice of real rows out of a canonical projection (loader flow test input).

Usage: python slice_projection.py --projection <dir> --output <new dir> [--per-tradition 6] [--omit-hadith <id>]
       [--change-hadith <id>]   (appends a marker to that hadith's category, so the loader sees one changed row)
The slice keeps the source projection's bundle binding, so the loader's manifest checks run unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import export_postgres as ep  # noqa: E402


def read_table(directory: Path, table: str) -> tuple[list[str], list[dict[str, str | None]]]:
    with (directory / "canonical" / f"{table}.csv").open("rt", encoding="utf-8", newline="") as handle:
        # The 3.12 reader cannot tell quoted "" from NULL: blank is NULL except the one known-empty column,
        # and the mention contexts are recomputed from neighbours in build_slice.
        reader = csv.reader(handle)
        header = next(reader)
        rows = []
        for values in reader:
            row = {name: (value if value != "" else None) for name, value in zip(header, values)}
            if table == "chain_mentions" and row["surface_normalized"] is None:
                row["surface_normalized"] = ep.Verbatim("")
            rows.append(row)
        return header, rows


def build_slice(projection: Path, output: Path, per_tradition: int, omit_hadith: str | None,
                change_hadith: str | None = None) -> dict:
    source_manifest = json.loads((projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    tables = {item["table"]: read_table(projection, item["table"]) for item in source_manifest["files"]}

    hadiths = tables["hadiths"][1]
    chains_by_hadith: dict[str, list[dict]] = defaultdict(list)
    for chain in tables["chains"][1]:
        chains_by_hadith[chain["hadith_id"]].append(chain)
    mentions_by_chain: dict[str, list[dict]] = defaultdict(list)
    for mention in tables["chain_mentions"][1]:
        mentions_by_chain[mention["chain_id"]].append(mention)
    with_translation = {row["hadith_id"] for row in tables["translations"][1]}
    with_assessment = {row["hadith_id"] for row in tables["hadith_assessments"][1]}
    with_verified_link = {row["hadith_id"] for row in tables["chain_mentions"][1] if row["narrator_id"]}
    candidates_by_mention: dict[str, list[dict]] = defaultdict(list)
    for candidate in tables["chain_mention_candidates"][1]:
        candidates_by_mention[candidate["mention_id"]].append(candidate)
    with_disagreement = {rows[0]["hadith_id"] for rows in candidates_by_mention.values()
                         if len({row["narrator_id"] for row in rows}) > 1}
    with_kunya_only = {row["hadith_id"] for row in tables["chain_mention_candidates"][1]
                       if row["basis"] == "name_kunya_only"}
    # One cross-tradition correspondence pair, both reports with chains, so the slice exercises the pair tables.
    cross_pair = next((row for row in sorted(tables["report_correspondence_candidates"][1], key=lambda r: r["id"])
                       if row["scope"] == "cross_tradition" and row["hadith_id_a"] in chains_by_hadith
                       and row["hadith_id_b"] in chains_by_hadith), None)

    chosen: set[str] = set()
    for tradition in ("tradition:sunni", "tradition:imami", "tradition:zaydi", "tradition:ibadi"):
        pool = sorted(row["id"] for row in hadiths if row["tradition_id"] == tradition)
        for predicate in (chains_by_hadith.__contains__, with_translation.__contains__, with_assessment.__contains__,
                          with_verified_link.__contains__, with_disagreement.__contains__,
                          with_kunya_only.__contains__):
            chosen.update([hadith_id for hadith_id in pool if predicate(hadith_id)][:per_tradition])
    if cross_pair is not None:
        centre = {row["hadith_id"]: row["star_centre_hadith_id"]
                  for row in tables["report_correspondence_cluster_members"][1]}
        for hadith_id in (cross_pair["hadith_id_a"], cross_pair["hadith_id_b"]):
            chosen.update((hadith_id, centre[hadith_id]))
    if omit_hadith is not None:
        if omit_hadith not in chosen:
            raise SystemExit(f"--omit-hadith {omit_hadith} is not in the slice")
        chosen.discard(omit_hadith)

    keep: dict[str, list[dict]] = {}
    keep["hadiths"] = [row for row in hadiths if row["id"] in chosen]
    keep["chains"] = [row for row in tables["chains"][1] if row["hadith_id"] in chosen]
    chain_ids = {row["id"] for row in keep["chains"]}
    keep["chain_mentions"] = [row for row in tables["chain_mentions"][1] if row["chain_id"] in chain_ids]
    for chain_id in chain_ids:
        ordered = sorted(mentions_by_chain[chain_id], key=lambda row: int(row["position"]))
        for index, row in enumerate(ordered):
            row["teacher_context_normalized"] = ordered[index + 1]["surface_normalized"] if index + 1 < len(ordered) else None
            row["student_context_normalized"] = ordered[index - 1]["surface_normalized"] if index > 0 else None
    keep["chain_mention_candidates"] = [row for row in tables["chain_mention_candidates"][1]
                                        if row["hadith_id"] in chosen]
    keep["translations"] = [row for row in tables["translations"][1] if row["hadith_id"] in chosen]
    keep["hadith_assessments"] = [row for row in tables["hadith_assessments"][1] if row["hadith_id"] in chosen]
    keep["report_correspondence_cluster_members"] = [
        row for row in tables["report_correspondence_cluster_members"][1]
        if row["hadith_id"] in chosen and row["star_centre_hadith_id"] in chosen]
    members = {row["hadith_id"] for row in keep["report_correspondence_cluster_members"]}
    keep["report_correspondence_candidates"] = [
        row for row in tables["report_correspondence_candidates"][1]
        if row["hadith_id_a"] in members and row["hadith_id_b"] in members]
    if change_hadith is not None:
        [changed] = [row for row in keep["hadiths"] if row["id"] == change_hadith]
        changed["category"] = f"{changed['category'] or ''} [changed by slice]".strip()
        changed["category_folded"] = changed["category"].lower()
    # Narrators, collections and structure are closed over the FULL slice (including any omitted hadith), so
    # omitting one hadith retires only that hadith and its dependents.
    full_chosen = chosen | ({omit_hadith} if omit_hadith else set())
    full_chains = {row["id"] for row in tables["chains"][1] if row["hadith_id"] in full_chosen}
    narrator_ids = {row["narrator_id"] for row in tables["chain_mentions"][1]
                    if row["chain_id"] in full_chains and row["narrator_id"]}
    narrator_ids |= {row["narrator_id"] for row in tables["chain_mention_candidates"][1]
                     if row["hadith_id"] in full_chosen}
    full_hadiths = [row for row in hadiths if row["id"] in full_chosen]
    collection_ids = {row["collection_id"] for row in full_hadiths}
    chapter_ids = {row["chapter_id"] for row in full_hadiths if row["chapter_id"]}
    keep["chapters"] = [row for row in tables["chapters"][1] if row["id"] in chapter_ids]
    book_ids = {row["book_id"] for row in full_hadiths if row["book_id"]} | {
        row["book_id"] for row in keep["chapters"] if row["book_id"]}
    keep["books"] = [row for row in tables["books"][1] if row["id"] in book_ids]
    keep["collections"] = [row for row in tables["collections"][1] if row["id"] in collection_ids]
    source_ids = {row["source_id"] for row in keep["collections"]}
    keep["sources"] = [row for row in tables["sources"][1] if row["id"] in source_ids]
    keep["traditions"] = list(tables["traditions"][1])
    keep["narrators"] = [row for row in tables["narrators"][1] if row["id"] in narrator_ids]
    keep["narrator_lexicon_profiles"] = [row for row in tables["narrator_lexicon_profiles"][1]
                                         if row["narrator_id"] in narrator_ids]
    keep["narrator_aliases"] = [row for row in tables["narrator_aliases"][1] if row["narrator_id"] in narrator_ids]
    keep["narrator_teachers"] = [row for row in tables["narrator_teachers"][1]
                                 if row["student_id"] in narrator_ids and row["teacher_id"] in narrator_ids]
    # External identity tables (0010), when the projection has them: closed over the slice's narrators.
    if "narrator_source_profiles" in tables:
        keep["narrator_source_profiles"] = [row for row in tables["narrator_source_profiles"][1]
                                            if row["narrator_id"] in narrator_ids]
        keep["narrator_external_ids"] = [row for row in tables["narrator_external_ids"][1]
                                         if row["narrator_id"] in narrator_ids]
        keep["narrator_link_candidates"] = [row for row in tables["narrator_link_candidates"][1]
                                            if row["external_narrator_id"] in narrator_ids
                                            and row["rawi_narrator_id"] in narrator_ids]
    for table in ("bibliographic_works", "editions", "citations"):
        keep[table] = []

    writer = ep.TableWriter(output, "canonical", None)
    for table in sorted(tables):
        header = tables[table][0]
        key_width = 2 if table in ("narrator_teachers", "report_correspondence_cluster_members") else 1
        writer.write(table, header, [[row[name] for name in header] for row in keep[table]], key_width=key_width)
    manifest = {**source_manifest, "files": writer.files,
                "counts": {"slice_of": source_manifest["content_sha256"], "omitted_hadith": omit_hadith,
                           "changed_hadith": change_hadith},
                "content_sha256": ep.graph_content_hash(writer.files, [])}
    (output / "canonical" / "manifest.json").write_bytes(ep.deterministic_json_bytes(manifest))

    longest = max(keep["chains"], key=lambda row: (int(row["length"]), row["id"]))
    ordered = sorted(mentions_by_chain[longest["id"]], key=lambda row: int(row["position"]))
    expectations = {
        "content_sha256": manifest["content_sha256"],
        "rows": {item["table"]: item["row_count"] for item in writer.files},
        "hadiths_by_tradition": {t: sum(1 for row in keep["hadiths"] if row["tradition_id"] == t)
                                 for t in sorted({row["tradition_id"] for row in keep["hadiths"]})},
        "chain": {"id": longest["id"], "surfaces": [row["surface_ar"] for row in ordered]},
        "omitted_hadith": omit_hadith,
        "changed_hadith": change_hadith,
        "correspondence_pair": cross_pair["id"] if cross_pair else None,
        "hadith_ids": sorted(chosen),
        "hadiths_with_chains": sorted(hadith_id for hadith_id in chosen if hadith_id in chains_by_hadith),
    }
    (output / "expectations.json").write_text(json.dumps(expectations, ensure_ascii=False, indent=2), encoding="utf-8")
    return expectations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--per-tradition", type=int, default=6)
    parser.add_argument("--omit-hadith")
    parser.add_argument("--change-hadith")
    args = parser.parse_args()
    expectations = build_slice(args.projection, args.output, args.per_tradition, args.omit_hadith, args.change_hadith)
    print(json.dumps({"content_sha256": expectations["content_sha256"], "rows": expectations["rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
