"""External identity claims (hadith-kg, Riwayat) and the machine-reviewed rule. See pg_export/AGENTS.md §External
identity and the load proposal in reconciled/README.md.

Pure rules (`person_key`, `standing_identity`, `riwayat_label_reason`) plus `ExternalSources`, which reads the reconciled
sidecars, checks each file against its build manifest and each claim against the projection's mention and Arabic, and
returns rows for the projection. A source's id is that source's claim: nothing here merges two narrators, imports a
verdict, or crosses traditions.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from transliteration import latin_name, strip_marks

# Candidate bases (enum mention_candidate_basis). Bases that may carry the machine-reviewed tier by themselves:
CONFIRMED_SOURCE_BASES = frozenset({
    "source_index_confirmed_by_text", "source_hadith_kg_confirmed_by_text", "source_riwayat_confirmed_by_text",
})
K6_BASES = frozenset({"source_index", "source_index_confirmed_by_text"})
HADITH_KG_BASES = frozenset({"source_hadith_kg", "source_hadith_kg_confirmed_by_text"})
EXTERNAL_BASES = frozenset(HADITH_KG_BASES | {"source_riwayat", "source_riwayat_confirmed_by_text"})
SOURCE_POSITION_BASES = frozenset(K6_BASES | EXTERNAL_BASES)
# Labels, never contests (owner 2026-11-21): kunya-only names and an unqualified shared Imam kunya.
NON_CONTESTING_BASES = frozenset({"name_kunya_only", "imam_kunya_candidate"})
RIWAYAT_AUTOMATIC = "riwayat_automatic_linking"

# Which evidence set the standing identity, strongest first (chain_mentions.extraction_method).
STANDING_METHODS = (
    "source_index_confirmed_by_text", "two_sources_agree", "source_hadith_kg_confirmed_by_text",
    "source_riwayat_confirmed_by_text", "imam_kunya_convention", "named_in_opening_isnad",
)
# A printed edition's own note names the person (edition_identifications.json): it stands over the index it corrects.
EDITION_BASIS = "edition_identification"
# The work's own opening isnad names the person (opening_isnad_rules.json); the detail cites the report.
OPENING_ISNAD_BASIS = "named_in_opening_isnad"
# A surface that is a kunya alone («أبو عبيدة»): no source can be confirmed by such text (owner, round 2, P7).
KUNYA_ONLY_SURFACE = re.compile(r"^(?:أبو|ابو|أبي|ابي|أبا|ابا|أم|ام)\s+\S+$")
KUNYA_ONLY_DEMOTION = {
    "source_hadith_kg_confirmed_by_text": "source_hadith_kg", "source_riwayat_confirmed_by_text": "source_riwayat",
    "source_index_confirmed_by_text": "source_index",
}


def demote_kunya_only(candidate: "Candidate", surface_ar: str) -> "Candidate":
    """A kunya-only surface cannot confirm a source's identity: the candidate stays, without the confirmation."""
    lowered = KUNYA_ONLY_DEMOTION.get(candidate.basis)
    if lowered is None or not KUNYA_ONLY_SURFACE.match(strip_marks(surface_ar).strip()):
        return candidate
    reason = "kunya-only surface: not confirmable by text"
    return Candidate(candidate.narrator_id, lowered, f"{reason} (was {candidate.detail})" if candidate.detail else reason,
                     candidate.source_position, candidate.source_ref, candidate.origin, candidate.placeholder,
                     candidate.label_like)

RIWAYAT_LABEL_FLAGS = frozenset({"merged_names_suspect", "compound_source_name", "junk_name"})


def narrator_id_for(external_id: str) -> str:
    """`hadith-kg:rawi:12` -> `narrator:hadith-kg:12`; `riwayat:N0000620` -> `narrator:riwayat:N0000620`."""
    if external_id.startswith("hadith-kg:rawi:"):
        return "narrator:hadith-kg:" + external_id.removeprefix("hadith-kg:rawi:")
    if external_id.startswith("riwayat:"):
        return "narrator:" + external_id
    raise ValueError(f"unknown external narrator id {external_id!r}")


def authority_of(narrator_id: str) -> str:
    """`rawi`, `hadith-kg`, `riwayat` or `imam` from a narrator id."""
    return narrator_id.split(":")[1]


@dataclass(frozen=True)
class Candidate:
    narrator_id: str
    basis: str
    detail: str | None = None
    source_position: int | None = None
    source_ref: str | None = None
    origin: str | None = None
    placeholder: str | None = None   # the target narrator's placeholder reason (a label, never a contest)
    label_like: bool = False         # the target is a label-like external record (cannot carry the tier)


@dataclass
class PersonKeys:
    """Cross-registry bridges used only to compare two candidates (never to merge narrators or pages)."""
    lexicon_link: dict[str, str] = field(default_factory=dict)      # external narrator -> narrator:rawi:<indx>
    riwayat_to_kg: dict[str, str] = field(default_factory=dict)     # riwayat narrator -> its one hadith-kg narrator

    def key(self, narrator_id: str) -> str:
        if narrator_id in self.lexicon_link:
            return self.lexicon_link[narrator_id]
        if narrator_id in self.riwayat_to_kg:
            return self.key(self.riwayat_to_kg[narrator_id])
        return narrator_id


def contests(candidates: Sequence[Candidate], keys: PersonKeys) -> bool:
    """True when two contesting candidates are known to name different people: their person keys differ within one
    authority. An unlinked pair across authorities is not comparable, so not a contest (reconciled/README.md §c)."""
    by_authority: dict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        if candidate.basis in NON_CONTESTING_BASES or candidate.placeholder:
            continue
        person = keys.key(candidate.narrator_id)
        by_authority[authority_of(person)].add(person)
    return any(len(people) > 1 for people in by_authority.values())


def standing_identity(candidates: Sequence[Candidate], keys: PersonKeys) -> tuple[str, str] | None:
    """(narrator_id, method) of the machine-reviewed identity, or None.

    Evidence, strongest first: the K6 source index confirmed by the text; two independent sources agreeing (a K6
    claim and a hadith-kg claim whose person keys meet); hadith-kg confirmed by the text; Riwayat confirmed by the text
    from an annotation, not its automatic linker, on a record that is not label-like; an Imam's conventional kunya.
    The mention must be uncontested. Riwayat's Sunni ids are hadith-kg's own, so they never count as a second source.
    """
    edition = [c for c in candidates if c.basis == EDITION_BASIS]
    if edition:
        return edition[0].narrator_id, EDITION_BASIS
    if contests(candidates, keys):
        return None
    k6 = [c for c in candidates if c.basis in K6_BASES and not c.placeholder]
    found: list[tuple[str, str]] = []
    for c in candidates:
        if c.basis == "source_index_confirmed_by_text" and not c.placeholder:
            found.append(("source_index_confirmed_by_text", c.narrator_id))
    for c in candidates:
        if c.basis in HADITH_KG_BASES and not c.placeholder:
            for claim in k6:
                if keys.key(c.narrator_id) == keys.key(claim.narrator_id):
                    found.append(("two_sources_agree", claim.narrator_id))
    for c in candidates:
        if c.placeholder:
            continue
        if c.basis == "source_hadith_kg_confirmed_by_text":
            found.append(("source_hadith_kg_confirmed_by_text", c.narrator_id))
        elif c.basis == "source_riwayat_confirmed_by_text" and c.origin != RIWAYAT_AUTOMATIC and not c.label_like:
            found.append(("source_riwayat_confirmed_by_text", c.narrator_id))
        elif c.basis == "imam_kunya_convention":
            found.append(("imam_kunya_convention", c.narrator_id))
        elif c.basis == OPENING_ISNAD_BASIS:
            found.append((OPENING_ISNAD_BASIS, c.narrator_id))
    if not found:
        return None
    found.sort(key=lambda item: (STANDING_METHODS.index(item[0]), item[1]))
    method, narrator_id = found[0]
    return narrator_id, method


def riwayat_name_key(name: str | None) -> str:
    """Comparison key for Riwayat's own names: marks, tatweel and alef forms folded."""
    key = strip_marks(name or "")
    key = re.sub("[أإآٱ]", "ا", key).replace("ى", "ي").replace("ة", "ه")
    return " ".join(key.split())


def riwayat_label_reason(row: dict, shared_names: set[str]) -> str | None:
    """Why a Riwayat id names a label as written in chains rather than an established person, or None.

    Placeholder names (single word, kunya alone, collective, relational); a name held by several Riwayat ids with real
    use (each at least 3 mentions and a tenth of the name's total); Riwayat's own merge or junk flags; a bare nasab
    (`ابن فضال`), which names a family.
    """
    if row.get("name_placeholder_reason"):
        return f"placeholder:{row['name_placeholder_reason']}"
    flags = sorted(RIWAYAT_LABEL_FLAGS & set(row.get("flags") or []))
    if flags:
        return f"riwayat_flag:{flags[0]}"
    key = riwayat_name_key(row.get("name_ar"))
    if key in shared_names:
        return "name_held_by_several_ids"
    words = key.split()
    if len(words) == 2 and words[0] == "ابن":
        return "nasab_only_label"
    return None


def shared_riwayat_names(rows: Iterable[dict]) -> set[str]:
    totals: Counter = Counter()
    holders: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        key = riwayat_name_key(row.get("name_ar"))
        uses = int(row.get("claims_in_our_mentions") or 0)
        totals[key] += uses
        holders[key].append(uses)
    shared = set()
    for key, uses in holders.items():
        real = [count for count in uses if count >= 3 and count >= totals[key] / 10]
        if len(real) >= 2:
            shared.add(key)
    return shared


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


class ExternalSourceError(ValueError):
    pass


LICENCE = {
    "hadith_kg": "CC BY 4.0 (hadith-kg by emadjumaah)",
    "riwayat": "CC0 1.0 (Riwayat corpus, Abdullah Ansar); inherited names keep their sources' licences",
    "imam_register": "Shura wa Istehsan register (imam_kunya_conventions.json)",
}


class ExternalSources:
    """The reconciled external sidecars, verified and indexed for the projection."""

    FILES = {
        "claims": "external_mention_claims.jsonl.gz",
        "hadith_kg_narrators": "hadith_kg_narrators.jsonl.gz",
        "riwayat_narrators": "riwayat_narrators.jsonl.gz",
        "links": "external_narrator_lexicon_links.jsonl.gz",
    }

    def __init__(self, directory: Path):
        self.directory = directory
        manifest = json.loads((directory / "external_identity_sidecars.manifest.json").read_text(encoding="utf-8"))
        self.hashes: dict[str, str] = {}
        for role, name in self.FILES.items():
            expected = manifest["outputs"][role]["sha256"]
            actual = _sha256(directory / name)
            if actual != expected:
                raise ExternalSourceError(f"{name}: SHA-256 differs from its build manifest")
            self.hashes[name] = actual
        crosswalk_manifest = json.loads((directory / "external_report_crosswalk.manifest.json").read_text(encoding="utf-8"))
        crosswalk = directory / crosswalk_manifest["output"]["file"]
        if _sha256(crosswalk) != crosswalk_manifest["output"]["sha256"]:
            raise ExternalSourceError("external_report_crosswalk.jsonl.gz: SHA-256 differs from its build manifest")
        self.hashes[crosswalk.name] = crosswalk_manifest["output"]["sha256"]
        self.report_arabic: dict[tuple[str, str], str] = {}
        for row in _rows(crosswalk):
            if row.get("used"):
                self.report_arabic[(row["hadith_id"], row["dataset"])] = row["arabic_sha256"]

        self.claims_by_mention: dict[str, list[dict]] = defaultdict(list)
        referenced: set[str] = set()
        for row in _rows(directory / self.FILES["claims"]):
            self.claims_by_mention[row["mention_id"]].append(row)
            referenced.add(row["external_narrator_id"])
        self.links = list(_rows(directory / self.FILES["links"]))
        referenced |= {link["external_narrator_id"] for link in self.links}

        self.registry: dict[str, dict] = {}
        riwayat_rows = []
        for row in _rows(directory / self.FILES["riwayat_narrators"]):
            riwayat_rows.append({"name_ar": row.get("name_ar"), "claims_in_our_mentions": row.get("claims_in_our_mentions")})
            if row["external_narrator_id"] in referenced:
                self.registry[row["external_narrator_id"]] = row
        self.shared_names = shared_riwayat_names(riwayat_rows)
        for row in _rows(directory / self.FILES["hadith_kg_narrators"]):
            if row["external_narrator_id"] in referenced:
                self.registry[row["external_narrator_id"]] = row
        missing = referenced - set(self.registry)
        if missing:
            raise ExternalSourceError(f"{len(missing)} referenced external narrators absent from the registries")

    # -- narrators ---------------------------------------------------------------------------------------------------
    def placeholder(self, external_id: str) -> str | None:
        row = self.registry[external_id]
        if row.get("name_placeholder_reason"):
            return row["name_placeholder_reason"]
        if row["dataset"] == "hadith_kg" and (row.get("dataset_assertions") or {}).get("is_stub"):
            return "hadith_kg_stub_narrator"
        return None

    def label_reason(self, external_id: str) -> str | None:
        row = self.registry[external_id]
        return riwayat_label_reason(row, self.shared_names) if row["dataset"] == "riwayat" else None

    def narrator_rows(self, arabic_norm) -> list[list]:
        """narrators rows: id, authority, authority_key, scholar_indx, name, name_ar, name_en, name_ar_normalized,
        placeholder_reason, name_latin, name_latin_basis."""
        rows = []
        for external_id, row in sorted(self.registry.items()):
            narrator_id = narrator_id_for(external_id)
            name_ar = (row.get("name_ar") or "").strip() or None
            authority = "hadith_kg" if row["dataset"] == "hadith_kg" else "riwayat"
            key = narrator_id.split(":", 2)[2]
            latin = latin_name(name_ar) if name_ar else None
            rows.append([narrator_id, authority, key, None, name_ar or external_id, name_ar, None,
                         arabic_norm(name_ar) if name_ar else None, self.placeholder(external_id),
                         latin[0] if latin else None, latin[1] if latin else None])
        return rows

    def profile_rows(self) -> list[list]:
        """narrator_source_profiles rows: narrator_id, source, assertions (JSON), licence, label_reason, asserted_by,
        review_state."""
        rows = []
        for external_id, row in sorted(self.registry.items()):
            if row["dataset"] == "hadith_kg":
                assertions = {
                    "dataset_assertions": row.get("dataset_assertions") or {},
                    "popular_name_ar": row.get("popular_name_ar"),
                    "tradition_context_chain_positions": row.get("tradition_context_chain_positions") or {},
                }
            else:
                assertions = {
                    "dataset_assertions": row.get("dataset_assertions") or {},
                    "name_forms": row.get("name_forms") or [],
                    "name_source": row.get("name_source"),
                    "flags": row.get("flags") or [],
                    "tradition_label": row.get("tradition_label"),
                    "tradition_context_mentions": row.get("tradition_context_mentions") or {},
                }
            rows.append([narrator_id_for(external_id), row["dataset"], json.dumps(assertions, ensure_ascii=False,
                         sort_keys=True), LICENCE[row["dataset"]], self.label_reason(external_id), row["asserted_by"],
                         "source_unverified"])
        return rows

    def external_id_rows(self) -> list[list]:
        """narrator_external_ids rows: id, narrator_id, namespace, external_id, asserted_by (Riwayat's crosswalk ids)."""
        rows = []
        for external_id, row in sorted(self.registry.items()):
            if row["dataset"] != "riwayat":
                continue
            narrator_id = narrator_id_for(external_id)
            for namespace, values in sorted((row.get("crosswalk") or {}).items()):
                for value in sorted(set(values or [])):
                    rows.append([f"external-id:{narrator_id.removeprefix('narrator:')}:{namespace}:{value}", narrator_id,
                                 namespace, str(value), "riwayat"])
        return rows

    def person_keys(self, lexicon_ids: set[str], lexicon_placeholders: dict[str, str]) -> PersonKeys:
        keys = PersonKeys()
        for link in self.links:
            target = f"narrator:rawi:{link['scholar_indx']}"
            if target in lexicon_ids and str(link["scholar_indx"]) not in lexicon_placeholders:
                external = narrator_id_for(link["external_narrator_id"])
                if keys.lexicon_link.get(external, target) != target:
                    raise ExternalSourceError(f"{external}: two lexicon link candidates; the bridge must be unique")
                keys.lexicon_link[external] = target
        for external_id, row in self.registry.items():
            if row["dataset"] != "riwayat":
                continue
            kg = (row.get("crosswalk") or {}).get("kg") or []
            if len(set(kg)) == 1:
                target = f"hadith-kg:rawi:{kg[0]}"
                if target in self.registry:
                    keys.riwayat_to_kg[narrator_id_for(external_id)] = narrator_id_for(target)
        return keys

    def link_rows(self, lexicon_ids: set[str], lexicon_placeholders: dict[str, str]) -> tuple[list[list], Counter]:
        """narrator_link_candidates rows: id, external_narrator_id, rawi_narrator_id, basis, evidence (JSON), review_state."""
        rows, dropped = [], Counter()
        for link in sorted(self.links, key=lambda item: (item["external_narrator_id"], str(item["scholar_indx"]))):
            target = f"narrator:rawi:{link['scholar_indx']}"
            if target not in lexicon_ids:
                dropped["lexicon_row_not_loaded"] += 1
                continue
            if str(link["scholar_indx"]) in lexicon_placeholders:
                dropped["lexicon_row_is_placeholder"] += 1
                continue
            external = narrator_id_for(link["external_narrator_id"])
            evidence = {key: value for key, value in link.items()
                        if key not in ("external_narrator_id", "scholar_indx", "basis", "review_state")}
            rows.append([f"narrator-link:{external.removeprefix('narrator:')}:{target.removeprefix('narrator:')}",
                         external, target, link["basis"], json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                         "unreviewed"])
        return rows, dropped

    # -- mention claims ----------------------------------------------------------------------------------------------
    def candidates_for(self, mention_id: str, hadith_id: str, surface_ar: str, arabic_sha256: str,
                       counts: Counter) -> list[Candidate]:
        """Candidates from the external claims at one mention; refuses a claim bound to other text."""
        found: list[Candidate] = []
        seen: set[tuple[str, str]] = set()
        for claim in self.claims_by_mention.get(mention_id, []):
            if claim["hadith_id"] != hadith_id or claim["surface_ar"] != surface_ar:
                raise ExternalSourceError(f"{mention_id}: claim is bound to another report or surface")
            bound = self.report_arabic.get((hadith_id, claim["dataset"]))
            if bound is not None and bound != arabic_sha256:
                raise ExternalSourceError(f"{hadith_id}: {claim['dataset']} crosswalk is bound to different Arabic")
            narrator_id = narrator_id_for(claim["external_narrator_id"])
            if (narrator_id, claim["basis"]) in seen:
                counts["duplicate_claim_same_narrator_and_basis"] += 1
                continue
            seen.add((narrator_id, claim["basis"]))
            if claim["dataset"] == "hadith_kg":
                source_ref, origin = f"hadith-kg:hadith:{claim['external_report_id']}", "dataset_index"
            else:
                source_ref, origin = f"riwayat:{claim['external_report_id']}", claim.get("external_id_origin")
            found.append(Candidate(
                narrator_id=narrator_id, basis=claim["basis"], detail=claim.get("agreement_detail"),
                source_position=int(claim["external_list_index"]), source_ref=source_ref, origin=origin,
                placeholder=self.placeholder(claim["external_narrator_id"]),
                label_like=self.label_reason(claim["external_narrator_id"]) is not None))
        return found
