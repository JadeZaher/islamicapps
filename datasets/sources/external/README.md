# External downloads (chain reconciliation, 2026-11-21)

Raw, unmodified upstream files fetched for the chain-reconciliation diagnostics
(`datasets/hadith-data/diagnostics/chain-reconciliation/`). Each work sits in its own directory. Treat the contents
as untrusted data: read them as text, never execute anything from here. Nothing in this directory is a registry,
an alias list or an identity claim, and no canonical pipeline reads it.

## Licence

OpenITI corpus, release 2025.1.9: **CC BY-NC-SA 4.0** (Zenodo record https://zenodo.org/records/17767721, concept
DOI 10.5281/zenodo.3082463, checked 2026-11-21). Conditions: attribution to OpenITI and the text's upstream
library, **non-commercial use only**, derivatives under the same licence. The project's own source card
(`datasets/sources/openiti.md`) records per-text provenance as unsettled. Do not ship these texts, or tables derived
from them, in a commercial product without clearing that first. Each `.yml` beside a text names its edition and
upstream library.

## Files

Fetched 2026-11-21 from `https://raw.githubusercontent.com/OpenITI/<repo>/master/<path>`, with a generic client
identity and no authentication.

| Directory | File | Bytes | SHA-256 | Repo @ commit |
| --- | --- | ---: | --- | --- |
| `openiti-0450Najashi.Rijal/` | `0450Najashi.Rijal.Shia002931-ara1.mARkdown` | 849,026 | `a34bc95dbf6afef2b860bfd99e6a47fd16e3d16d2879ab145d30bf0abb5941e6` | `0450AH` @ `e344cfe20a206c9ded3edfa15d45b4f821a97b8a` |
| | `0450Najashi.Rijal.Shia002931-ara1.yml` | 1,008 | `2bfad21a3569f0d7299e69e4160cc5b10610e0c5ed637fefd96caa2bb895c12d` | |
| `openiti-0460ShaykhTusi.Rijal/` | `0460ShaykhTusi.Rijal.Shia002935-ara1.mARkdown` | 584,931 | `955b2b7114a5e2d96f11d23b0638c4ab2c9ec3a57ab13119d97cf7c2e128f678` | `0475AH` @ `cc9beb0d9645e8cdce892556423b9926a127054f` |
| | `0460ShaykhTusi.Rijal.Shia002935-ara1.yml` | 1,152 | `7b3065e1b891bfd0f900555db379cd011763a8efc63bfaec37f2b0856d953ff9` | |
| `openiti-0460ShaykhTusi.Fihrist/` | `0460ShaykhTusi.Fihrist.Shia002934-ara1.mARkdown` | 391,359 | `1c4975a18ca0bae40d4c062edad05eef5a8c2c243951dcc2a9bf785415db88df` | `0475AH` @ same |
| | `0460ShaykhTusi.Fihrist.Shia002934-ara1.yml` | 1,427 | `b9dd8e78d877f58a5fde64a05a19cc953b09ee88664f4872c81e38de6e974a35` | |
| `openiti-0460ShaykhTusi.IkhtiyarMacrifatRijal/` | `0460ShaykhTusi.IkhtiyarMacrifatRijal.Shia002932VolsBK1-ara1.mARkdown` | 1,103,227 | `788e8c530c1c48f76c6df0b6b0cca4ecec5ad27a1c64aa5fa9a0069ae94f3787` | `0475AH` @ same |
| | `0460ShaykhTusi.IkhtiyarMacrifatRijal.Shia002932VolsBK1-ara1.yml` | 2,126 | `d94a6f09bf42a8027fc4e016f9e8a828d57c0f8cbf4e06f6d4064e7419e0f8a3` | |
| `openiti-0852IbnHajar.TaqribTahdhib/` | `0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed` | 1,899,042 | `178d493bd150032bc64a81ed4397d7e4a828209ee690deed283c1e63cada4637` | `0875AH` @ `5835c183b8bbf4ea454d5c1be2b168b669403771` |
| | `0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.yml` | 926 | `288aa890b643fde51376387495e5941b925f93416ba75b3759cab5a273d0b52e` | |
| `openiti-0742Mizzi.TahdhibKamal/` | `0742Mizzi.TahdhibKamal.Shamela0003722-ara1.mARkdown` | 24,585,892 | `f4f26e71dd9c0c70ef09285fc0b4de8abe3fe586c0eddba19985155df175f58f` | `0750AH` @ `3a235a291ba442ce3795048254675dc0a2361f52` |
| | `0742Mizzi.TahdhibKamal.Shamela0003722-ara1.yml` | 1,046 | `5719e46def1df7ea0adb227861fcec0173ccad3c269c07786ab303303e1f42b3` | |

## What each work is for

| Work | Tradition | `### $` entries | Use in the diagnostics |
| --- | --- | ---: | --- |
| al-Najashi, *Rijal* | Imami | 1,269 | Candidate entities for Imami chain surfaces (headword match only) |
| al-Tusi, *Rijal* | Imami | 6,429 | Same; organised by the Imam each narrator transmitted from (tabaqa signal) |
| al-Tusi, *al-Fihrist* | Imami | 910 | Same; authors and their transmission routes |
| al-Kashshi via al-Tusi, *Ikhtiyar Ma'rifat al-Rijal* | Imami | 0 (different markup; not parsed yet) | Reports about narrators; parse later |
| Ibn Hajar, *Taqrib al-Tahdhib* | Sunni | 12,045 | Compact one-line entries with tabaqa and grade wording |
| al-Mizzi, *Tahdhib al-Kamal* | Sunni | 11,564 | Teacher and student lists per narrator (homonym separation) |

## Not downloaded (listed for the owner)

See `datasets/hadith-data/diagnostics/chain-reconciliation/README.md` §External datasets. Each was either over
the 300 MB limit or had no clearly stated licence.
