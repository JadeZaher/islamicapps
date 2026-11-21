"""Part B: biography and date content in every other local asset, with what joins to narrator ids.

Writes candidate files plus local_asset_inventory.json inside diagnostics/biography-recovery/ only.
Name joins are review candidates (exact normalized Arabic equality), never identity assertions.
"""

import ast
import collections
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import diagnostic_common as common  # noqa: E402

JOB = "biography-recovery"
HADITH = common.HADITH_DATA_DIR
LEXICON = common.REGISTRY_PATH
SEED_TS = common.PROJECT_DIR / "src" / "scripts" / "seed-narrator-bios-phase0.ts"
IBADI_RAWIS = common.DATASETS_DIR / "archive" / "loose-files-20260610" / "musnad_rawis.csv"
OPENITI_FILES = [
    ("openiti-sources/rabi/jamic_sahih_ibadiyya.txt", "Ibadi"),
    ("openiti-sources/zayd/musnad_zaydiyya_052.mARkdown", "Zaydi"),
    ("openiti-sources/zayd/musnad_zaydiyya_056.txt", "Zaydi"),
    ("openiti-sources/zayd/musnad_shia_811.txt", "Zaydi"),
]
PARSED = [("ibadi-hadith/parsed_hadiths.json", "Ibadi"), ("zaydi-hadith/parsed_hadiths.json", "Zaydi"),
          ("rida-hadith/parsed_hadiths.json", "Imami")]
PURE_CANON = HADITH / "archive" / "sheikahmad-pure-canon" / "pure_canon.jsonl"
STATUS = {"review_state": "unreviewed_local_candidate", "source_status": "source_status_unknown", "citation_id": None}
DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
HONORIFIC = re.compile(r"رضي الله عن(?:ه|ها|هم|هما)|\(ع\)|عليه السلام")


def normalize_arabic(text):
    text = unicodedata.normalize("NFKC", text or "")
    text = HONORIFIC.sub(" ", DIACRITICS.sub("", text))
    text = re.sub("[إأآٱ]", "ا", text).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[^ء-ي ]", " ", text).split() and " ".join(re.sub(r"[^ء-ي ]", " ", text).split())


def lexicon_arabic_index():
    index = collections.defaultdict(list)
    with LEXICON.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        arabic = re.findall(r"[؀-ۿ][؀-ۿ\s]*", row["name"])
        if arabic:
            key = normalize_arabic(max(arabic, key=len))
            if key:
                index[key].append(row["scholar_indx"])
    return {row["scholar_indx"]: row for row in rows}, index


def join_by_name(arabic, index):
    key = normalize_arabic(arabic)
    hits = index.get(key, [])
    status = "no_exact_match" if not hits else "unique_exact_match" if len(hits) == 1 else "ambiguous_exact_match"
    return {"normalized_arabic": key, "join_status": status, "candidate_scholar_indx": hits[:5]}


def seed_candidates(lexicon):
    text = SEED_TS.read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(r"scholar_indx:\s*\d+", text)]
    out = []
    for i, start in enumerate(starts):
        block = text[start: starts[i + 1] if i + 1 < len(starts) else len(text)]
        line = text.count("\n", 0, start) + 1

        def field(name, quoted=True):
            m = re.search(rf"\b{name}:\s*" + (r"'((?:[^'\\]|\\.)*)'" if quoted else r"([\w.]+)"), block)
            return m.group(1).replace("\\'", "'") if m else None
        index = re.match(r"scholar_indx:\s*(\d+)", block).group(1)
        lex = lexicon.get(index, {})
        out.append({
            "scholar_indx": index, "seed_file": "src/scripts/seed-narrator-bios-phase0.ts", "seed_line": line,
            "name_arabic": field("name_arabic"), "kunya": field("kunya"), "nasab": field("nasab"), "nisba": field("nisba"),
            "tabaqah_enum": field("tabaqah"), "death_year_hijri": field("death_date_hijri", False),
            "death_year_gregorian": field("death_date_gregorian", False), "geographic_region": field("geographic_region"),
            "reliability_consensus_enum": field("reliability_consensus"),
            "lexicon_death_date_place_verbatim": lex.get("death_date_place"),
            "lexicon_death_date_hijri_parsed": lex.get("death_date_hijri"),
            "provenance_note": "hand-written Phase-0 seed; cites general works in comments only; no edition or page",
            **STATUS,
        })
    return out


def ibadi_rawis_candidates(lexicon, index):
    out = []
    with IBADI_RAWIS.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        previous = reader.line_num
        for number, row in enumerate(reader, 1):
            line = previous + 1
            previous = reader.line_num
            arabic = re.findall(r"\(\s*([؀-ۿ][^)]*?)\s*\)", row["name"])
            join = join_by_name(arabic[-1] if arabic else "", index) if arabic else {"join_status": "no_arabic_in_name"}
            out.append({
                "ibadi_rawis_id": row["scholar_indx"], "file": "datasets/archive/loose-files-20260610/musnad_rawis.csv",
                "csv_line": line, "name_verbatim": row["name"], "grade_marker_verbatim": row["grade"],
                "birth_date_place_verbatim": row["birth_date_place"], "death_date_hijri_verbatim": row["death_date_hijri"],
                "death_date_gregorian_verbatim": row["death_date_gregorian"], "death_place_verbatim": row["death_place"],
                "places_of_stay_verbatim": row["places_of_stay"], "teachers_verbatim": row["teachers"],
                "students_verbatim": row["students"], "area_of_interest_verbatim": row["area_of_interest"],
                "tags_verbatim": row["tags"], "books_verbatim": row["books"], **join, **STATUS,
                "note": "ids 60001-60020 are absent from all_rawis.csv (ids 1-40023, none >= 60000): not joined to the registry"})
    return out


def provider_narrators(index):
    seen = collections.OrderedDict()
    for rel, tradition in PARSED:
        for hadith in json.loads((HADITH / rel).read_text(encoding="utf-8"))["hadiths"]:
            detail = hadith["sanad_detail"]
            if isinstance(detail, str):
                try:
                    detail = ast.literal_eval(detail)
                except (ValueError, SyntaxError):
                    detail = []
            for entry in detail:
                key = (tradition, entry["name_ar"], entry["tabaqah"], entry["school"])
                seen.setdefault(key, {"names_en": set(), "occurrences": 0, "file": rel})
                seen[key]["occurrences"] += 1
                seen[key]["names_en"].add(entry["name_en"])
    out = []
    for (tradition, name_ar, tabaqah, school), info in seen.items():
        out.append({"tradition": tradition, "file": f"datasets/hadith-data/{info['file']}", "field": "hadiths[].sanad_detail[]",
                    "name_ar_verbatim": name_ar, "name_en_verbatim": sorted(info["names_en"]), "tabaqah_enum": tabaqah,
                    "school_verbatim": school, "occurrences_in_chains": info["occurrences"],
                    **join_by_name(name_ar, index), **STATUS,
                    "note": "provider tabaqah/school are parser-assigned labels, not cited"})
    return out


def openiti_author_claims():
    out = []
    for rel, tradition in OPENITI_FILES:
        text = (HADITH / rel).read_text(encoding="utf-8-sig")
        header = text.split("#META#Header#End#")[0] if "#META#Header#End#" in text else text[:6000]
        for number, line in enumerate(header.splitlines(), 1):
            if not line.startswith("#META#"):
                continue
            keep = re.search(r"AuthorBORN|AuthorDIED|المتوفى|EdPUBLISHER|الناشر|ترقيم الصفحات|ReadONLINE|LibREADONLINE", line)
            if keep:
                out.append({"tradition": tradition, "file": f"datasets/hadith-data/{rel}", "header_line": number,
                            "claim_text_verbatim": line.strip()[:700], **STATUS})
    return out


def pure_canon_header_claims():
    out = []
    for number, line in enumerate(PURE_CANON.open(encoding="utf-8"), 1):
        record = json.loads(line)
        if "اسم المؤلف" in record["source"] or "معلومات عن النشرة" in record["source"]:
            source = record["source"]
            born = re.search(r"ت الميلاد\s*(\d+)", source)
            died = re.search(r"ت الوفاة\s*(\d+)", source)
            out.append({
                "file": "datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon.jsonl", "jsonl_line": number,
                "pure_canon_id": record["id"], "hadith_no": record["hadith_no"],
                "header_text_verbatim": source[: source.find(record["text_ar"][:20]) if record["text_ar"][:20] in source else 900][:900],
                "compiler_birth_year_hijri_as_written": int(born.group(1)) if born else None,
                "compiler_death_year_hijri_as_written": int(died.group(1)) if died else None,
                "edition_text_verbatim": (re.search(r"معلومات عن النشرة.*?(?=عدد الأجزاء\s*\d+|$)", source) or [None])[0],
                "volumes_text": (re.search(r"عدد الأجزاء\s*\d+", source) or [None])[0], **STATUS})
    return out


def main():
    out_dir = common.output_directory(JOB)
    lexicon, index = lexicon_arabic_index()
    inputs = common.input_fingerprints(LEXICON, SEED_TS, IBADI_RAWIS, PURE_CANON, *[HADITH / r for r, _ in PARSED],
                                       *[HADITH / r for r, _ in OPENITI_FILES])
    seed = seed_candidates(lexicon)
    rawis = ibadi_rawis_candidates(lexicon, index)
    provider = provider_narrators(index)
    claims = openiti_author_claims()
    pure = pure_canon_header_claims()
    counts = {
        "phase0_seed_candidates.jsonl": common.write_jsonl(out_dir, "phase0_seed_candidates.jsonl", seed),
        "ibadi_musnad_rawis_candidates.jsonl": common.write_jsonl(out_dir, "ibadi_musnad_rawis_candidates.jsonl", rawis),
        "provider_sanad_detail_narrators.jsonl": common.write_jsonl(out_dir, "provider_sanad_detail_narrators.jsonl", provider),
        "openiti_header_author_edition_claims.jsonl": common.write_jsonl(out_dir, "openiti_header_author_edition_claims.jsonl", claims),
        "pure_canon_compiler_edition_header_claims.jsonl": common.write_jsonl(out_dir, "pure_canon_compiler_edition_header_claims.jsonl", pure),
    }
    seed_agree = collections.Counter()
    for row in seed:
        lex = row["lexicon_death_date_hijri_parsed"]
        seed_agree["no_seed_death_year" if not row["death_year_hijri"] else
                   "lexicon_blank" if lex in (None, "NA", "") else
                   "agrees" if str(row["death_year_hijri"]) == lex else "differs"] += 1
    inventory = {
        "header": common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/biography-recovery/inventory_other_local_biography.py", inputs),
        "output_rows": counts,
        "phase0_seed_vs_lexicon_death_year": dict(seed_agree),
        "ibadi_rawis_join": dict(collections.Counter(r["join_status"] for r in rawis)),
        "provider_narrators_join": dict(collections.Counter(r["join_status"] for r in provider)),
        "assets_examined": [
            {"asset": "datasets/hadith-data/shia-hadith/v2_books/*.json", "narrator_biography": "none",
             "detail": "33,190 records; fields are text/book metadata, thaqalaynSanad (free text) and gradingsFull; "
                       "gradingsFull author.{name_ar,link,death_date} are null on every one of 16,835 entries"},
            {"asset": "datasets/hadith-data/{ibadi,zaydi,rida}-hadith/parsed_hadiths.json", "narrator_biography": "tabaqah+school label only",
             "detail": f"{len(provider)} distinct (name, tabaqah, school) triples in sanad_detail; parser-assigned"},
            {"asset": "datasets/archive/loose-files-20260610/musnad_rawis.csv", "narrator_biography": "yes, rich (18 Ibadi narrators)",
             "detail": "ids 60001-60020 not in all_rawis.csv; dates as free text with variant years"},
            {"asset": "src/scripts/seed-narrator-bios-phase0.ts", "narrator_biography": "yes, 21 hand-written narrators",
             "detail": "joins directly on scholar_indx"},
            {"asset": "datasets/hadith-data/openiti-sources/*", "narrator_biography": "author-level only (the book's compiler)",
             "detail": "AuthorBORN/AuthorDIED/Shamela 'المتوفى' strings in headers; no narrator entries, no rijal text"},
            {"asset": "datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon.jsonl", "narrator_biography": "compiler birth/death only",
             "detail": "8 header rows embed compiler name, kunya, nisba, birth and death years and the printed edition"},
            {"asset": "datasets/hadith-data/development/neo4j-import/*/nodes/narrators.csv", "narrator_biography": "none",
             "detail": "6 columns: ids and name only"},
            {"asset": "datasets/hadith-data/classical_narrator_gap.csv", "narrator_biography": "none", "detail": "unresolved surface forms"},
            {"asset": "datasets/archive/datasets.7z", "narrator_biography": "not examined",
             "detail": "no 7-Zip on this machine and no standard-library reader; 17.6 MB dated 2026-03-23"},
            {"asset": "any rijal / tabaqat / Tahdhib / Taqrib / Mizan / Najashi / Tusi text", "narrator_biography": "none present",
             "detail": "git ls-files and a filesystem search under datasets/ and docs/ found no such file; OpenITI texts on disk are only the three hadith collections"},
        ],
    }
    common.write_json(out_dir, "local_asset_inventory.json", inventory)
    print(json.dumps({k: v for k, v in inventory.items() if k not in ("header", "assets_examined")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
