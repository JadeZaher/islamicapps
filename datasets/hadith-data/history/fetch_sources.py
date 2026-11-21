"""Fetches the OpenITI texts the history lane cites, pinned to a commit, and writes one README per source directory.

    python -B datasets/hadith-data/history/fetch_sources.py            # download missing files, verify, write READMEs
    python -B datasets/hadith-data/history/fetch_sources.py --verify   # verify checksums only, no network

Generic client identity, no authentication, no project or personal details sent. See datasets/hadith-data/history/README.md.
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXTERNAL = REPO_ROOT / 'datasets' / 'sources' / 'external'
MANIFEST = Path(__file__).resolve().parent / 'sources_manifest.json'
USER_AGENT = 'generic-client/1.0'
LICENCE = ('CC BY-NC-SA 4.0 (OpenITI corpus; release 2025.1.9 on Zenodo, https://zenodo.org/records/17767721, '
           'concept DOI 10.5281/zenodo.3082463). Attribution to OpenITI and the upstream library named in the .yml; '
           'non-commercial use only; derivatives under the same licence.')

# (key, repo, commit, data path, version file, role, tradition of the work's author as OpenITI/the work presents it)
SOURCES = [
    ('openiti-0240KhalifaIbnKhayyat.Tarikh', '0250AH', '0cc00c0646c81988c75a3815fe6d9a5fa65ce592',
     'data/0240IbnKhayyatCusfuri/0240IbnKhayyatCusfuri.Tarikh', '0240IbnKhayyatCusfuri.Tarikh.JK000412-ara1.completed',
     'Annalistic chronicle to 232 AH: accessions, battles and deaths year by year', 'Sunni'),
    ('openiti-0310Tabari.Tarikh', '0325AH', '089e665b4958e0f145a46941987fb81cf3dda1b8',
     'data/0310Tabari/0310Tabari.Tarikh', '0310Tabari.Tarikh.Shamela0009783BK1-ara1.mARkdown',
     'General annalistic chronicle to 302 AH', 'Sunni'),
    ('openiti-0911Suyuti.TarikhKhulafa', '0925AH', '4f0f4562d1e13083c593e3a0ca6a19a3eb33805e',
     'data/0911Suyuti/0911Suyuti.TarikhKhulafa', '0911Suyuti.TarikhKhulafa.Shamela0011997-ara1.completed',
     'Caliphs to the author\'s time, with accession and death dates; later political chronology', 'Sunni'),
    ('openiti-0911Suyuti.TabaqatHuffaz', '0925AH', '4f0f4562d1e13083c593e3a0ca6a19a3eb33805e',
     'data/0911Suyuti/0911Suyuti.TabaqatHuffaz', '0911Suyuti.TabaqatHuffaz.JK000753-ara1.mARkdown',
     'Biographies of hadith scholars to the 9th century AH (compilers and later scholars)', 'Sunni'),
    ('openiti-0413ShaykhMufid.Irshad', '0425AH', '3a3c829e55a1e4fb614aa857e0d85f51d6a9f0ee',
     'data/0413ShaykhMufid/0413ShaykhMufid.Irshad', '0413ShaykhMufid.Irshad.Shia001294Vols-ara1',
     'Lives of the twelve Imams with birth and death dates', 'Imami'),
    ('openiti-0460ShaykhTusi.Ghayba', '0475AH', 'cc9beb0d9645e8cdce892556423b9926a127054f',
     'data/0460ShaykhTusi/0460ShaykhTusi.Ghayba', '0460ShaykhTusi.Ghayba.Zaydiyya0000283-ara1',
     'The occultation and the four deputies, with their deaths', 'Imami'),
    ('openiti-0424AbuTalibHaruni.IfadaFiTarikhAimma', '0425AH', '3a3c829e55a1e4fb614aa857e0d85f51d6a9f0ee',
     'data/0424AbuTalibYahyaHaruni/0424AbuTalibYahyaHaruni.IfadaFiTarikhAimma',
     '0424AbuTalibYahyaHaruni.IfadaFiTarikhAimma.Zaydiyya0000088-ara1',
     'History of the Zaydi imams to the author\'s time', 'Zaydi'),
    ('openiti-0353AbuCabbasHasani.Masabih', '0375AH', 'ab52219710c6bf15a93d6e39886f0ca602d27952',
     'data/0353AbuCabbasHasani/0353AbuCabbasHasani.Masabih', '0353AbuCabbasHasani.Masabih.Zaydiyya0000087BK1-ara1.completed',
     'Lives of the Zaydi imams (al-Masabih)', 'Zaydi'),
    ('openiti-0362AbuFarajIsbahani.MaqatilTalibiyyin', '0375AH', 'ab52219710c6bf15a93d6e39886f0ca602d27952',
     'data/0362AbuFarajIsbahani/0362AbuFarajIsbahani.MaqatilTalibiyyin',
     '0362AbuFarajIsbahani.MaqatilTalibiyyin.Shamela0012404-ara1.completed',
     'The deaths and risings of the Talibids (Zayd b. Ali, Yahya b. Zayd, al-Nafs al-Zakiyya, ...)', None),
    ('openiti-0670AhmadDarjini.TabaqatMashayikh', '0675AH', '4b1d2886508b435eb0377ccab96e1da96cc8ee0a',
     'data/0670AhmadDarjini/0670AhmadDarjini.TabaqatMashayikhBiMaghrib',
     '0670AhmadDarjini.TabaqatMashayikhBiMaghrib.ShamIbadiyya0000107-ara1',
     'Ibadi scholars and imams of the Maghrib by generation', 'Ibadi'),
    ('openiti-0928Shammakhi.Siyar', '0950AH', 'd57b81e495eae739920ba3b7869fe1133890c23d',
     'data/0928AbuCabbasShammakhi/0928AbuCabbasShammakhi.Siyar', '0928AbuCabbasShammakhi.Siyar.ShamIbadiyya0000115-ara1.mARkdown',
     'Ibadi biographies and imamates (Kitab al-Siyar)', 'Ibadi'),
    ('openiti-1332Salimi.TuhfatAcyan', '1350AH', '6d0c197e84a46a3cadbd36a045d09cb2bc9aa71e',
     'data/1332NurDinSalimi/1332NurDinSalimi.TuhfatAcyan', '1332NurDinSalimi.TuhfatAcyan.ShamIbadiyya0000281-ara1',
     'History of the Ibadi imamates of Oman (Tuhfat al-Acyan)', 'Ibadi'),
]


def raw_url(repo, commit, path):
    return f'https://raw.githubusercontent.com/OpenITI/{repo}/{commit}/{path}'


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def download(url, target):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    target.write_bytes(data)


def readme(entry, files):
    rows = '\n'.join(f"| `{f['file']}` | {f['bytes']:,} | `{f['sha256']}` |" for f in files)
    return f"""# {entry['key']}

Raw, unmodified OpenITI text fetched for the history lane (`datasets/hadith-data/history/`). Untrusted data: read as
text, never executed. Git-ignored except this README.

- **Work:** `{entry['version_file'].split('-ara')[0].rsplit('.', 1)[0]}`; version `{entry['version_file']}`
- **Use:** {entry['role']}
- **Author's tradition (as the work presents itself):** {entry['tradition'] or 'not assigned here (cited per claim, see the history README)'}
- **Repository:** `OpenITI/{entry['repo']}` at commit `{entry['commit']}`
- **URL:** {entry['url']}
- **Fetched:** {entry['fetched']} with client identity `{USER_AGENT}`, no authentication
- **Licence:** {LICENCE}
- **Edition:** as recorded in the `.yml` beside the text and in `datasets/hadith-data/history/works_and_editions.json`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
{rows}
"""


def main():
    verify_only = '--verify' in sys.argv
    previous = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    manifest = {}
    for key, repo, commit, data_path, version_file, role, tradition in SOURCES:
        directory = EXTERNAL / key
        directory.mkdir(parents=True, exist_ok=True)
        files = []
        for name in (version_file, version_file.split('.completed')[0].split('.mARkdown')[0] + '.yml'):
            target = directory / name
            url = raw_url(repo, commit, f'{data_path}/{name}')
            if not target.exists():
                if verify_only:
                    raise SystemExit(f'missing {target}')
                download(url, target)
            files.append({'file': name, 'url': url, 'bytes': target.stat().st_size, 'sha256': sha256(target)})
        fetched = previous.get(key, {}).get('fetched', '2026-11-21')
        entry = {'key': key, 'repo': repo, 'commit': commit, 'version_file': version_file, 'role': role,
                 'tradition': tradition, 'url': files[0]['url'], 'fetched': fetched, 'licence': LICENCE, 'files': files}
        if previous.get(key) and previous[key]['files'] != files:
            raise SystemExit(f'checksum changed for {key}')
        manifest[key] = entry
        (directory / 'README.md').write_text(readme(entry, files), encoding='utf-8', newline='\n')
        print(f"{key}: {files[0]['bytes']:,} bytes {files[0]['sha256'][:12]}")
    total = sum(f['bytes'] for e in manifest.values() for f in e['files'])
    print(f'total {total:,} bytes')
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
