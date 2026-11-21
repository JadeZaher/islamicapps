"""Builds the history lane's load-ready candidates: cited claims for seed and new events, era boundaries and
narrator-event involvement, each with one complete citation and an AI-review record. Deterministic; no network, no
database. See README.md (§Method, §How history claims are AI-reviewed, §Load specification).

    python -B datasets/hadith-data/history/build_history_candidates.py
"""
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import history_text as ht  # noqa: E402
from claims_spec import (CLAIMS, COMPILATION_SPLITS, NAME_FORMS, NEW_EVENTS, NEW_PLACES, SEED_PLACE_FORMS,  # noqa: E402
                         TAQRIB_CENTURY)

REPO = ht.REPO_ROOT
SEED_FILE = REPO / 'src' / 'scripts' / 'db' / 'seed-history.ts'
BIO = REPO / 'datasets' / 'hadith-data' / 'diagnostics' / 'biography-verification'
LEXICON_LINKS = BIO / 'lexicon_rijal_links.jsonl.gz'
OUT = HERE / 'output'
AI_RULE_VERSION = 'history-ai-review-v1'
AI_PROCEDURE = 'datasets/hadith-data/history/build_history_candidates.py (deterministic string and number checks; no language model)'
LICENCE_SHORT = 'CC BY-NC-SA 4.0 (OpenITI release 2025.1.9)'
ANNALS = {'khalifa', 'tabari'}


# ---------- seed ----------

def stable_seed_id(namespace, *parts):
    """Same rule as stableSeedId in src/scripts/db/seed-history.ts."""
    normalized = '|'.join(re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(p)).strip().lower()) for p in parts)
    return f"{namespace}:{hashlib.sha256(f'{namespace}|{normalized}'.encode()).hexdigest()[:24]}"


def parse_seed():
    source = SEED_FILE.read_text(encoding='utf-8')
    events = []
    block = source[source.index('const LEGACY_EVENTS'):source.index('];', source.index('const LEGACY_EVENTS'))]
    for line in block.splitlines():
        if 'title:' not in line:
            continue
        field = lambda name: re.search(name + r': "((?:[^"\\]|\\.)*)"', line).group(1)  # noqa: E731
        number = lambda name: (lambda m: int(m.group(1)) if m else None)(re.search(name + r': (-?\d+)', line))  # noqa: E731
        events.append({'title': field('title'), 'title_arabic': field('title_arabic'), 'year_hijri': number(r'\byear_hijri'),
                       'end_year_hijri': number('end_year_hijri'), 'category': field('category'),
                       'location_name': field('location_name')})
    corrections = {'Birth of Prophet Muhammad': -53}
    for event in events:
        event['id'] = stable_seed_id('historical-event', event['title'], event['year_hijri'])
        event['start_year_hijri'] = corrections.get(event['title'], event['year_hijri'])
    epochs = []
    block = source[source.index('export const EPOCHS'):source.index('];', source.index('export const EPOCHS'))]
    for chunk in re.split(r"\n\s*\{ id: ", block)[1:]:
        number = lambda name: (lambda m: (None if m.group(1) == 'null' else int(m.group(1))) if m else None)(re.search(r'\b' + name + r': (-?\d+|null)', chunk))  # noqa: E731
        name = re.search(r"""\bname: (['"])(.*?)\1""", chunk).group(2)
        tradition = re.search(r"tradition: '(\w+)'", chunk)
        epochs.append({'id': re.match(r"'([^']+)'", chunk).group(1), 'name': name,
                       'tradition': tradition.group(1) if tradition else None,
                       'start': number('start'), 'start_latest': number('start_latest'),
                       'end': number('end'), 'end_latest': number('end_latest')})
    locations = re.findall(r'\{name: "([^"]+)", name_arabic', source)
    return events, epochs, locations


# ---------- Arabic year words ----------

UNITS = {'احد': 1, 'احدي': 1, 'واحد': 1, 'واحده': 1, 'اثنتين': 2, 'اثنين': 2, 'اثنتي': 2, 'اثني': 2, 'ثلاث': 3, 'ثلاثه': 3,
         'اربع': 4, 'اربعه': 4, 'خمس': 5, 'خمسه': 5, 'ست': 6, 'سته': 6, 'سبع': 7, 'سبعه': 7, 'ثمان': 8, 'ثماني': 8, 'ثمانيه': 8,
         'تسع': 9, 'تسعه': 9}
TENS = {'عشر': 10, 'عشره': 10, 'عشرين': 20, 'ثلاثين': 30, 'اربعين': 40, 'خمسين': 50, 'ستين': 60, 'سبعين': 70, 'ثمانين': 80, 'تسعين': 90}
HUNDREDS = {'مايه': 100, 'ماه': 100, 'مايتين': 200, 'ثلاثمايه': 300, 'اربعمايه': 400, 'خمسمايه': 500, 'ستمايه': 600,
            'سبعمايه': 700, 'ثمانمايه': 800, 'تسعمايه': 900}


def year_from_words(text):
    """Hijri year written in words after the last سنة/عام (or the whole phrase); None when no number word is found."""
    folded = ht.fold(text)
    folded = re.sub(r'[^ء-ي ]', ' ', folded)
    markers = [m.end() for m in re.finditer(r'(^| )(سنه|عام|راس) ', folded)]
    tail = folded[markers[-1]:] if markers else folded
    total, seen, previous_unit = 0, False, None
    for raw in tail.split():
        word = raw[1:] if raw.startswith('و') and raw[1:] in {**UNITS, **TENS, **HUNDREDS} else raw
        if word in ('من', 'التاريخ'):
            break
        if word in HUNDREDS:
            total += HUNDREDS[word]
        elif word in TENS:
            total += TENS[word]
            if word in ('عشر', 'عشره') and previous_unit is None and seen:
                pass
        elif word in UNITS:
            total += UNITS[word]
            previous_unit = word
        else:
            if seen:
                break
            continue
        seen = True
    return total if seen else None


# ---------- citations ----------

def edition_record(key):
    meta = ht.header(key)
    directory, name, title, title_ar, author, died, tradition = ht.WORKS[key]
    return {
        'work_id': f'work:openiti:{ht.openiti_uri(key).rsplit(".", 1)[0]}',
        'edition_id': f'edition:openiti:{ht.openiti_uri(key)}',
        'title': title, 'title_ar': meta.get('020.BookTITLE', title_ar), 'author': author,
        'author_full_ar': meta.get('010.AuthorNAME'), 'author_death_year_hijri': died, 'tradition_of_author': tradition,
        'openiti_uri': ht.openiti_uri(key), 'source_file': f'datasets/sources/external/{directory}/{name}',
        'source_sha256': ht.sha256_file(ht.work_path(key)),
        'editor': meta.get('040.EdEDITOR'), 'publisher': meta.get('043.EdPUBLISHER'), 'place': meta.get('044.EdPLACE'),
        'year': meta.get('045.EdYEAR'), 'edition_number': meta.get('041.EdNUMBER'),
        'library_uri': meta.get('030.LibURI'), 'library_url': meta.get('031.LibURL') or meta.get('031.LibREADONLINE'),
        'locator_scheme': 'vNpM = volume and printed page from OpenITI PageV markers (page of a passage = first marker after it); line = line in the OpenITI file; span = character offsets in the UTF-8-decoded file',
        'licence': LICENCE_SHORT, 'rights_status': 'pending',
    }


def make_citation(key, clean_start, clean_end, passage_clean_span, edition, heading=None, entry_number=None):
    text = ht.load(key)
    start, end = passage_clean_span
    raw_start, raw_end = text.raw_offset(start), text.raw_offset(end - 1) + 1
    quote = re.sub(r'\s+', ' ', text.clean[start:end]).strip()
    page = text.page_at(text.raw_offset(clean_start))
    line = text.line_at(text.raw_offset(clean_start))
    locator = {'volume': page[0] if page else None, 'page': page[1] if page else None, 'entry': entry_number,
               'openiti_line': line, 'section_heading': heading}
    span = {'char_start': raw_start, 'char_end': raw_end,
            'byte_start': len(text.raw[:raw_start].encode('utf-8')), 'byte_end': len(text.raw[:raw_end].encode('utf-8'))}
    cid = 'cit:history:' + hashlib.sha256(f"{edition['openiti_uri']}|{raw_start}|{raw_end}".encode()).hexdigest()[:20]
    locator_text = ', '.join(x for x in [f"v{page[0]} p{page[1]}" if page else None, f'entry {entry_number}' if entry_number else None,
                                         f'OpenITI line {line}'] if x)
    return {
        'id': cid, 'work_id': edition['work_id'], 'edition_id': edition['edition_id'],
        'work': {'author': edition['author'], 'title': edition['title'], 'title_ar': edition['title_ar'],
                 'tradition_of_author': edition['tradition_of_author']},
        'edition': {k: edition[k] for k in ('openiti_uri', 'editor', 'publisher', 'place', 'year', 'edition_number', 'library_uri')},
        'locator': locator, 'locator_text': locator_text, 'volume': str(page[0]) if page else None,
        'page': str(page[1]) if page else None, 'quote_ar': quote, 'source_span': span,
        'source_file': edition['source_file'], 'source_sha256': edition['source_sha256'],
        'source_reference': f"{edition['author']}, {edition['title']}, {locator_text} (OpenITI {edition['openiti_uri']})",
        'licence': LICENCE_SHORT, 'quote_normalization': 'OpenITI markup removed (PageV, ms, ~~, #, |, $), whitespace collapsed; letters unchanged',
    }


# ---------- claims ----------

def find_hits(spec):
    text = ht.load(spec['work'])
    anchor = spec['anchor']
    # literal anchors match across OpenITI line breaks and markup gaps: tokens joined by \s+
    pattern = anchor[3:] if anchor.startswith('RE:') else r'\s+'.join(re.escape(t) for t in ht.fold(anchor).split())
    hits = text.search(pattern)
    if spec.get('heading'):
        wanted = ht.fold(spec['heading'])
        hits = [h for h in hits if wanted in ht.fold(text.heading_at(text.raw_offset(h[0])) or '')]
    return hits


def passage_span(text, start, end, before, after, entry):
    if entry:
        raw = text.raw_offset(start)
        starts = [h[0] for h in text.headings]
        import bisect
        index = bisect.bisect_right(starts, raw) - 1
        begin = bisect.bisect_left(text.offsets, starts[index])
        finish = bisect.bisect_left(text.offsets, starts[index + 1]) if index + 1 < len(starts) else len(text.clean)
        return begin, finish
    import bisect
    starts = [h[0] for h in text.headings]
    index = bisect.bisect_right(starts, text.raw_offset(start)) - 1
    section_begin = bisect.bisect_left(text.offsets, starts[index]) if index >= 0 else 0
    section_end = bisect.bisect_left(text.offsets, starts[index + 1]) if index + 1 < len(starts) else len(text.clean)
    first, last = _window(text, start, end, before, after)
    return max(first, section_begin), min(last, section_end)


def _window(text, start, end, before, after):
    window = text.passage(start, end, before, after, cap=900)
    # locate the window back in the clean text (passage() collapses whitespace, so search near the hit)
    lo = max(0, start - 1200)
    region = text.clean[lo:end + 1200]
    collapsed, index_map = [], []
    for i, ch in enumerate(region):
        if ch.isspace():
            if collapsed and collapsed[-1] == ' ':
                continue
            collapsed.append(' ')
        else:
            collapsed.append(ch)
        index_map.append(i)
    joined = ''.join(collapsed)
    position = joined.find(window)
    if position < 0:
        raise RuntimeError('passage window not found back in text')
    return lo + index_map[position], lo + index_map[position + len(window) - 1] + 1


def evaluate(spec, edition_cache):
    key = spec['work']
    text = ht.load(key)
    hits = find_hits(spec)
    nth = spec.get('nth', 0)
    if len(hits) <= nth:
        return None, {'target': spec['target'], 'work': key, 'anchor': spec['anchor'], 'hits': len(hits),
                      'reason': 'anchor not found in the text on disk'}
    start, end = hits[nth]
    raw = text.raw_offset(start)
    entry = spec.get('entry', False)
    span = passage_span(text, start, end, spec.get('before', 0), spec.get('after', 1), entry)
    heading = text.heading_at(raw)
    year_heading = text.year_heading_at(raw) if key in ANNALS else None
    entry_number = None
    if entry and heading:
        number = re.match(r'\$*\s*(\d+)', heading)
        entry_number = number.group(1) if number else None
    edition = edition_cache.setdefault(key, edition_record(key))
    citation = make_citation(key, start, end, span, edition, heading=heading, entry_number=entry_number)
    if year_heading:
        citation['locator']['annal_heading'] = year_heading
    return {'spec': spec, 'citation': citation, 'year_heading': year_heading, 'hit_count': len(hits)}, None


def ai_review(result):
    """The history AI-review rule (README §How history claims are AI-reviewed). Returns (outcome, checks, reasons)."""
    spec, citation = result['spec'], result['citation']
    quote = ht.fold(citation['quote_ar'])
    heading = ht.fold(result['year_heading'] or '')
    stated = ht.fold(spec['stated']) if not spec['stated'].startswith('RE:') else None
    basis = spec.get('basis', 'passage')
    checks, reasons = [], []
    complete = all([citation['work_id'], citation['edition_id'], citation['quote_ar'], citation['source_sha256'],
                    citation['locator']['page'] is not None or citation['locator']['openiti_line']])
    checks.append({'check': 'citation_complete', 'passed': complete,
                   'detail': 'work, edition, locator, verbatim passage, character span and source SHA-256 all present'})
    in_passage = stated is not None and stated in quote
    in_heading = stated is not None and basis == 'section_heading' and stated in heading
    checks.append({'check': 'stated_phrase_in_source', 'passed': in_passage or in_heading,
                   'detail': f"'{spec['stated']}' found in the {'passage' if in_passage else 'annal heading' if in_heading else 'source: NOT FOUND'}"})
    if spec['year'] is None:
        reasons.append('date_not_stated_as_a_year (' + (spec.get('reckoning') or 'no year') + ')')
        checks.append({'check': 'year_stated', 'passed': False, 'detail': 'the passage gives ' + (spec.get('reckoning') or 'no date')})
    else:
        source_text = result['year_heading'] if basis == 'section_heading' else spec['stated']
        words_year = year_from_words(source_text or '')
        exact = words_year == spec['year']
        century_missing = words_year is not None and words_year < 100 <= spec['year'] and words_year == spec['year'] % 100
        checks.append({'check': 'year_words_equal_claim', 'passed': exact,
                       'detail': f"year read from the words: {words_year}; claim: {spec['year']}" + ('; the century is not written' if century_missing else '')})
        if century_missing:
            reasons.append('century_not_written (supplied by ' + ('the author\'s stated convention' if TAQRIB_CENTURY in spec.get('flags', []) else 'context') + ')')
        elif not exact:
            reasons.append('year_words_do_not_match_claim')
    if basis == 'section_heading':
        checks.append({'check': 'annal_placement', 'passed': True,
                       'detail': f"dated by the annal heading '{result['year_heading']}' the passage sits under"})
    if not complete:
        reasons.append('citation_incomplete')
    if not (in_passage or in_heading):
        reasons.append('stated_phrase_not_in_source')
    if 'possible_text_variant' in spec.get('flags', []) or 'text_reads_107_beside_177' in spec.get('flags', []):
        checks.append({'check': 'text_variant_flag', 'passed': True, 'detail': 'flagged: ' + ', '.join(spec['flags'])})
    outcome = 'passed' if not reasons else 'failed'
    return outcome, checks, reasons


def seed_comparison(year, low, high):
    if year is None or low is None:
        return 'not_comparable'
    high = low if high is None else high
    if low <= year <= high:
        return 'agrees' if low == high else 'within_seed_range'
    return f'differs_by_{min(abs(year - low), abs(year - high))}'


def target_key(target):
    return '|'.join(str(x) for x in target)


def main():
    OUT.mkdir(exist_ok=True)
    events, epochs, seed_locations = parse_seed()
    seed_by_title = {e['title']: e for e in events}
    epoch_by_id = {e['id']: e for e in epochs}
    edition_cache, citations, claims, not_found = {}, {}, [], []
    for index, spec in enumerate(CLAIMS):
        target = spec['target']
        if target[0] == 'event' and target[1] not in seed_by_title:
            raise SystemExit(f'unknown seed event {target[1]}')
        if target[0] == 'epoch' and target[1] not in epoch_by_id:
            raise SystemExit(f'unknown epoch {target[1]}')
        if target[0] == 'new' and target[1] not in NEW_EVENTS:
            raise SystemExit(f'unknown new event {target[1]}')
        result, missing = evaluate(spec, edition_cache)
        if missing:
            not_found.append(missing)
            if not spec.get('optional'):
                print('ANCHOR NOT FOUND (non-optional):', missing, file=sys.stderr)
            continue
        if spec.get('optional') and spec['year'] is None and spec['anchor'].startswith('RE:') and spec['stated'] in ('سنة', 'RE:مات', 'RE:مات سنه'):
            # exploratory optional specs record what was found only when they carry a dated claim
            not_found.append({'target': target, 'work': spec['work'], 'anchor': spec['anchor'], 'hits': result['hit_count'],
                              'reason': 'searched; no dated statement adopted', 'first_hit_locator': result['citation']['locator_text']})
            continue
        citation = result['citation']
        citations[citation['id']] = citation
        outcome, checks, reasons = ai_review(result)
        if target[0] == 'event':
            seed = seed_by_title[target[1]]
            comparison = seed_comparison(spec['year'], seed['start_year_hijri'], seed['start_year_hijri'])
        elif target[0] == 'epoch':
            epoch = epoch_by_id[target[1]]
            low, high = (epoch['start'], epoch['start_latest']) if target[2] == 'start' else (epoch['end'], epoch['end_latest'])
            comparison = seed_comparison(spec['year'], low, high)
        else:
            comparison = 'new_event'
        claim_id = 'hclaim:' + hashlib.sha256(f"{target_key(target)}|{citation['id']}|{spec['year']}".encode()).hexdigest()[:20]
        claims.append({
            'id': claim_id, 'target_kind': target[0], 'target': target[1], 'boundary': target[2] if target[0] == 'epoch' else None,
            'predicate': 'era_boundary' if target[0] == 'epoch' else 'event_date',
            'year_hijri': spec['year'], 'alternatives_stated': spec.get('alternatives', []),
            'month_day': spec.get('month_day'), 'stated_ar': spec['stated'], 'date_basis': spec.get('basis', 'passage'),
            'qualifier': spec.get('qualifier'), 'reckoning': spec.get('reckoning'),
            'attributed_to': spec.get('attributed_to') or ht.WORKS[spec['work']][4],
            'statement_en': spec['statement_en'], 'note': spec.get('note'), 'flags': spec.get('flags', []),
            'seed_comparison': comparison, 'citation_id': citation['id'],
            'citation_status': 'cited' if checks[0]['passed'] else 'not_yet_cited',
            'ai_review': {'rule': AI_RULE_VERSION, 'procedure': AI_PROCEDURE, 'model': None, 'outcome': outcome,
                          'checks': checks, 'failure_reasons': reasons, 'passage_checked': citation['id']},
            'perspective': {'source_work': ht.WORKS[spec['work']][2], 'source_author': ht.WORKS[spec['work']][4],
                            'source_tradition': ht.WORKS[spec['work']][6],
                            'event_tradition_context': (NEW_EVENTS[target[1]][3] if target[0] == 'new'
                                                        else epoch_by_id[target[1]]['tradition'] if target[0] == 'epoch' else None)},
            'human_reviews': [], 'spec_index': index,
        })

    # competing claims: same target, different passing years
    by_target = defaultdict(list)
    for c in claims:
        by_target[(c['target_kind'], c['target'], c['boundary'])].append(c)
    for group in by_target.values():
        years = {c['year_hijri'] for c in group if c['ai_review']['outcome'] == 'passed'}
        for c in group:
            c['competing_years_in_cited_sources'] = sorted(y for y in years if y != c['year_hijri'])
            c['ai_review']['checks'].append({'check': 'competing_claims_shown', 'passed': True,
                                             'detail': 'other cited years for this target: ' + (', '.join(map(str, c['competing_years_in_cited_sources'])) or 'none')})

    # ---- narrator-event involvement (Taqrib entries that state it; links only where the lexicon link is unique) ----
    involvement = narrator_involvement(edition_cache, citations, seed_by_title)

    # ---- events ----
    event_rows = []
    for seed in events:
        group = by_target.get(('event', seed['title'], None), [])
        passing = [c for c in group if c['ai_review']['outcome'] == 'passed']
        status = assess(group, passing)
        split = COMPILATION_SPLITS.get(seed['title'])
        event_rows.append({
            'id': seed['id'], 'origin': 'seed', 'title': seed['title'], 'title_arabic': seed['title_arabic'],
            'seed_start_year_hijri': seed['start_year_hijri'], 'seed_end_year_hijri': seed['end_year_hijri'],
            'category': seed['category'], 'location_name': seed['location_name'],
            'location_proposal': 'location:proposed:egypt-misr' if seed['location_name'] == 'Egypt' else None,
            'tradition_context': None, 'claim_ids': [c['id'] for c in group], 'cited_years': sorted({c['year_hijri'] for c in passing}),
            'assessment': status,
            'proposal': ({'action': 'split_compilation_event', 'death_event': split[0], 'reason': split[1],
                          'compilation_date': 'unknown: no text on disk dates the compilation'} if split else None),
            'publishable_under_ai_rule': bool(passing) and not split,
        })
    for key, (title, title_ar, category, tradition, location) in NEW_EVENTS.items():
        group = by_target.get(('new', key, None), [])
        passing = [c for c in group if c['ai_review']['outcome'] == 'passed']
        primary = passing[0] if passing else (group[0] if group else None)
        year = primary['year_hijri'] if primary else None
        event_rows.append({
            'id': stable_seed_id('historical-event', title, year if year is not None else 'undated'), 'origin': 'history_lane_candidate',
            'key': key, 'title': title, 'title_arabic': title_ar, 'start_year_hijri': year, 'category': category,
            'location_name': location, 'tradition_context': tradition, 'claim_ids': [c['id'] for c in group],
            'cited_years': sorted({c['year_hijri'] for c in passing}), 'assessment': assess(group, passing),
            'replaces_seed_title': next((t for t, s in COMPILATION_SPLITS.items() if s[0] == key), None),
            'publishable_under_ai_rule': bool(passing),
        })

    epoch_rows = []
    for epoch in epochs:
        row = {'id': epoch['id'], 'name': epoch['name'], 'tradition_context': epoch['tradition'],
               'seed_start': [epoch['start'], epoch['start_latest']], 'seed_end': [epoch['end'], epoch['end_latest']]}
        for boundary in ('start', 'end'):
            group = by_target.get(('epoch', epoch['id'], boundary), [])
            passing = [c for c in group if c['ai_review']['outcome'] == 'passed']
            row[f'{boundary}_claim_ids'] = [c['id'] for c in group]
            row[f'{boundary}_cited_years'] = sorted({c['year_hijri'] for c in passing})
            row[f'{boundary}_assessment'] = assess(group, passing) if not (boundary == 'end' and epoch['end'] is None) else 'open_ended'
        row['publishable_under_ai_rule'] = row['start_assessment'] in ('supported', 'supported_with_competing_date', 'contradicted') and \
            row['end_assessment'] in ('supported', 'supported_with_competing_date', 'contradicted', 'open_ended')
        row['citation_id_for_epochs_row'] = next((cid for cid in row['start_claim_ids']), None)
        epoch_rows.append(row)

    location_rows = [{
        'id': 'location:proposed:egypt-misr', 'name': 'Egypt (Misr)', 'name_arabic': 'مصر', 'region': 'Egypt',
        'modern_country': 'Egypt', 'latitude': None, 'longitude': None, 'kind': 'region',
        'reasoning': ('Two seed events name "Egypt" and no seeded place matches. "Misr" in the sources names the province '
                      '(e.g. Ibn Hajar on al-Shafii: "nazil Misr", settled in Egypt), not a city: Fustat was its capital in that '
                      'period and Cairo was founded only in 358. Mapping either event to Fustat or Cairo would assert a city the '
                      'passage does not state. A region-level place keeps what the source says; a curator may later add a '
                      'city-level link where a source names it. No coordinates are proposed for a region.'),
        'supporting_citation_ids': [c['citation_id'] for c in claims if c['target'] == "Death of Imam al-Shafi'i" and c['spec_index'] is not None and 'taqrib' in c['attributed_to'].lower()] or None,
        'events_to_link': [e['id'] for e in event_rows if e.get('location_name') == 'Egypt'],
    }]

    location_rows += gazetteer(seed_locations, citations)
    egypt_forms = re.compile(r'(?<![ء-ي])(?:و|ب|ل)?مصر(?![ء-ي])')
    location_rows[0]['forms_ar'] = ['مصر']
    location_rows[0]['coordinates_basis'] = 'none (region)'
    location_rows[0]['cited_in_citation_ids'] = sorted(cid for cid, c in citations.items() if egypt_forms.search(ht.fold(c['quote_ar'])))
    location_rows[0].pop('supporting_citation_ids', None)
    (OUT / 'event_name_forms.json').write_text(json.dumps(event_name_forms(event_rows, epochs), ensure_ascii=False, indent=1) + '\n',
                                              encoding='utf-8', newline='\n')
    write_outputs(edition_cache, citations, claims, event_rows, epoch_rows, involvement, location_rows, not_found, events, epochs)


def event_name_forms(event_rows, epochs):
    """Stable id + Arabic name forms (as written and folded) for every event and era, for mention matching."""
    out = []
    for event in event_rows:
        key = event.get('key') or event['title']
        forms = [event['title_arabic']] + NAME_FORMS.get(key, [])
        out.append({'kind': 'event', 'id': event['id'], 'key': key, 'title': event['title'], 'tradition_context': event.get('tradition_context'),
                    'forms_ar': forms, 'forms_folded': sorted({ht.fold(f) for f in forms})})
    for epoch in epochs:
        forms = [f for f in [epoch.get('name_arabic')] if f]
        out.append({'kind': 'epoch', 'id': epoch['id'], 'key': epoch['id'], 'title': epoch['name'], 'tradition_context': epoch['tradition'],
                    'forms_ar': forms, 'forms_folded': sorted({ht.fold(f) for f in forms})})
    return out


def gazetteer(seed_locations, citations):
    """Seeded places reconciled (ids kept) plus proposed places; each lists the citations whose passage names it."""
    quotes = {cid: ' ' + ht.fold(c['quote_ar']) + ' ' for cid, c in citations.items()}

    def cited(forms):
        patterns = [re.compile(r'(?<![ء-ي])(?:و|ب|ل)?' + re.escape(ht.fold(f)) + r'(?![ء-ي])') for f in forms]
        return [cid for cid, quote in sorted(quotes.items()) if any(p.search(quote) for p in patterns)]

    ambiguous = {'أحد': 'also "one/anyone"', 'المدينة': 'also "the city" (any city)', 'عمان': 'also Amman', 'مصر': 'also "a garrison city"',
                 'النهر': 'also "the river"', 'الفتح': 'also "the conquest" (any)'}
    rows = []
    for name in seed_locations:
        forms = SEED_PLACE_FORMS.get(name, [])
        rows.append({'id': stable_seed_id('location', name), 'origin': 'seed', 'name': name, 'forms_ar': forms,
                     'coordinates_basis': 'editorial (seed), not sourced', 'cited_in_citation_ids': cited(forms) if forms else []})
    for key, name, forms, region, country, kind, lat, lon in NEW_PLACES:
        if key == 'egypt-misr':
            continue
        rows.append({'id': f'location:proposed:{key}', 'origin': 'history_lane_candidate', 'name': name, 'name_arabic': forms[0],
                     'forms_ar': forms, 'region': region, 'modern_country': country, 'kind': kind, 'latitude': lat, 'longitude': lon,
                     'coordinates_basis': 'editorial (well-known site), not sourced' if lat is not None else 'none (region)',
                     'cited_in_citation_ids': cited(forms)})
    for row in rows:
        row['ambiguous_forms'] = {f: ambiguous[f] for f in row['forms_ar'] if f in ambiguous}
        row['mention_basis'] = 'form occurs in the cited passage (candidate mention; ambiguous forms need a reader)'
    return rows


def assess(group, passing):
    if not group:
        return 'nothing_found'
    if not passing:
        return 'cited_but_not_stated_as_year' if any(c['citation_status'] == 'cited' for c in group) else 'nothing_found'
    comparisons = {c['seed_comparison'] for c in passing}
    if all(x in ('agrees', 'within_seed_range') for x in comparisons):
        return 'supported'
    if comparisons == {'new_event'}:
        return 'supported' if len({c['year_hijri'] for c in passing}) == 1 else 'supported_with_competing_date'
    if any(x in ('agrees', 'within_seed_range') for x in comparisons):
        return 'supported_with_competing_date'
    return 'contradicted'


INVOLVEMENT_PATTERNS = [
    # (event target, role, folded regex)
    (('event', 'Battle of Badr'), 'Participant', r'(?<![ء-ي])شهد بدرا'),
    (('event', 'Battle of Uhud'), 'Killed', r'(استشهد|قتل) (باحد|يوم احد)'),
    (('event', 'Battle of Uhud'), 'Participant', r'شهد احدا'),
    (('event', 'Battle of the Camel'), 'Killed', r'(استشهد|قتل) (يوم الجمل|بالجمل|في وقعه الجمل)'),
    (('event', 'Battle of the Camel'), 'Participant', r'شهد الجمل'),
    (('event', 'Battle of Siffin'), 'Killed', r'(استشهد|قتل)( مع علي)? (بصفين|يوم صفين|في صفين)'),
    (('event', 'Battle of Siffin'), 'Participant', r'شهد صفين'),
    (('event', 'Martyrdom of Husayn at Karbala'), 'Killed', r'قتل مع الحسين|(استشهد|قتل) (بكربلاء|بالطف)'),
    (('event', 'Battle of Yarmouk'), 'Killed', r'(استشهد|قتل) (باليرموك|يوم اليرموك)'),
    (('event', 'Battle of Yarmouk'), 'Participant', r'شهد اليرموك'),
    (('event', 'Conquest of Persia (Battle of Qadisiyyah)'), 'Killed', r'(استشهد|قتل) (بالقادسيه|يوم القادسيه)'),
    (('event', 'Conquest of Persia (Battle of Qadisiyyah)'), 'Participant', r'شهد القادسيه'),
    (('new', 'battle-of-al-harra'), 'Killed', r'(استشهد|قتل) (يوم الحره|بالحره|في وقعه الحره)'),
    (('new', 'battle-of-yamama'), 'Killed', r'(استشهد|قتل) (باليمامه|يوم اليمامه)'),
]
NEGATION = re.compile(r'(لم|ما|ولم) $')
OTHER_SUBJECT = re.compile(r'(ابوه|ابيه|ابنه|اخوه|جده|عمه|زوجها|ابوها) [^ ]* ?$')


def narrator_involvement(edition_cache, citations, seed_by_title):
    links = {}
    with gzip.open(LEXICON_LINKS, 'rt', encoding='utf-8') as handle:
        for line in handle:
            row = json.loads(line)
            if row['source'] == 'ibn_hajar_taqrib' and row['status'] == 'unique':
                links.setdefault(row['entry_number'], []).append(row)
    text = ht.load('taqrib')
    edition = edition_cache.setdefault('taqrib', edition_record('taqrib'))
    import bisect
    rows = []
    heads = text.headings
    for index, (raw_start, heading_text, _level) in enumerate(heads):
        number = re.match(r'\$*\s*(\d+) ', ht.fold(heading_text) + ' ')
        if not number:
            continue
        begin = bisect.bisect_left(text.offsets, raw_start)
        finish = bisect.bisect_left(text.offsets, heads[index + 1][0]) if index + 1 < len(heads) else len(text.clean)
        folded = ht.fold(re.sub(r'\s+', ' ', text.clean[begin:finish]))
        for target, role, pattern in INVOLVEMENT_PATTERNS:
            for match in re.finditer(pattern, folded):
                before = folded[max(0, match.start() - 25):match.start()]
                flags = []
                if NEGATION.search(before):
                    continue
                if OTHER_SUBJECT.search(before):
                    flags.append('subject_may_differ')
                if re.search(r'(^| )(قيل|ويقال|يقال|زعم)( |$)', before[-14:]):
                    flags.append('reported_as_it_is_said')
                if re.search(r'(لا يصح|ولا يصح|وهم|غلط|والصواب)', folded[match.end():match.end() + 30]):
                    flags.append('source_rejects_the_report')
                if re.search(r'(قال|ذكر) [^ ]+ ?[^ ]*$', before[-25:]):
                    flags.append('attributed_to_an_authority')
                entry_number = number.group(1)
                link = links.get(entry_number, [])
                citation = make_citation('taqrib', begin, finish, (begin, finish), edition, heading=heading_text, entry_number=entry_number)
                citations[citation['id']] = citation
                narrator = f"narrator:rawi:{link[0]['scholar_indx']}" if len(link) == 1 else None
                event_id = seed_by_title[target[1]]['id'] if target[0] == 'event' else None
                passed = narrator is not None and not (set(flags) - {'attributed_to_an_authority'})
                reasons = ([] if narrator else ['no_unique_lexicon_link_for_this_entry']) + flags
                rows.append({
                    'id': 'hinv:' + hashlib.sha256(f'{entry_number}|{target_key(target)}|{role}'.encode()).hexdigest()[:20],
                    'narrator_id': narrator, 'lexicon_link': ({'scholar_indx': link[0]['scholar_indx'], 'tier': link[0]['tier'],
                                                               'basis': 'exact name key, unique on both sides (candidate link, not an identification)'} if len(link) == 1 else None),
                    'taqrib_entry': entry_number, 'event_target': target[1], 'event_id': event_id,
                    'event_new_key': target[1] if target[0] == 'new' else None, 'role': role,
                    'stated_ar': match.group(0), 'citation_id': citation['id'], 'citation_status': 'cited',
                    'ai_review': {'rule': AI_RULE_VERSION, 'procedure': AI_PROCEDURE, 'model': None,
                                  'outcome': 'passed' if passed else 'failed', 'failure_reasons': reasons,
                                  'checks': [{'check': 'involvement_phrase_in_entry', 'passed': True, 'detail': match.group(0)},
                                             {'check': 'not_negated', 'passed': True, 'detail': 'no لم/ما before the phrase'},
                                             {'check': 'subject_is_headword', 'passed': not flags, 'detail': 'no kin word (أبوه, ابنه ...) before the phrase' if not flags else 'a kin word precedes the phrase'},
                                             {'check': 'narrator_link_unique', 'passed': narrator is not None, 'detail': 'lexicon link unique on both sides' if narrator else 'no unique lexicon link'}]},
                    'human_reviews': [], 'basis': 'stated in the narrator\'s own Taqrib entry; never inferred from overlapping dates',
                })
                break
    # Tabari: Ahmad b. Hanbal named among those examined in the Mihna (218)
    ahmad = links.get('96', [])
    hits = ht.load('tabari').search(ht.fold('أحمد بن حنبل وقتيبة وسعدويه الواسطي'))
    if hits and len(ahmad) == 1:
        tabari = ht.load('tabari')
        span = passage_span(tabari, hits[0][0], hits[0][1], 1, 1, False)
        cit = make_citation('tabari', hits[0][0], hits[0][1], span, edition_cache.setdefault('tabari', edition_record('tabari')),
                            heading=tabari.heading_at(tabari.raw_offset(hits[0][0])))
        cit['locator']['annal_heading'] = tabari.year_heading_at(tabari.raw_offset(hits[0][0]))
        citations[cit['id']] = cit
        rows.append({'id': 'hinv:' + hashlib.sha256(b'tabari-mihna-ahmad').hexdigest()[:20],
                     'narrator_id': f"narrator:rawi:{ahmad[0]['scholar_indx']}", 'lexicon_link': {'scholar_indx': ahmad[0]['scholar_indx'], 'tier': ahmad[0]['tier'], 'basis': 'Taqrib entry 96 linked by exact name key'},
                     'taqrib_entry': '96', 'event_target': 'Ahmad ibn Hanbal and the Mihna', 'event_id': seed_by_title['Ahmad ibn Hanbal and the Mihna']['id'],
                     'event_new_key': None, 'role': 'Examined', 'stated_ar': 'أحمد بن حنبل', 'citation_id': cit['id'], 'citation_status': 'cited',
                     'ai_review': {'rule': AI_RULE_VERSION, 'procedure': AI_PROCEDURE, 'model': None, 'outcome': 'passed', 'failure_reasons': [],
                                   'checks': [{'check': 'involvement_phrase_in_passage', 'passed': True, 'detail': 'named in the list of those sent for examination, annal of 218'}]},
                     'human_reviews': [], 'basis': 'named in the passage'})
    return rows


def dump_jsonl_gz(path, rows):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', mtime=0, filename='') as handle:
        for row in rows:
            handle.write((json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8'))
    path.write_bytes(buffer.getvalue())


def write_outputs(editions, citations, claims, event_rows, epoch_rows, involvement, location_rows, not_found, events, epochs):
    claims.sort(key=lambda c: (c['target_kind'], c['target'], c['boundary'] or '', c['spec_index']))
    for c in claims:
        c.pop('spec_index', None)
    citation_rows = sorted(citations.values(), key=lambda c: c['id'])
    dump_jsonl_gz(OUT / 'citations.jsonl.gz', citation_rows)
    dump_jsonl_gz(OUT / 'date_claims.jsonl.gz', claims)
    dump_jsonl_gz(OUT / 'event_candidates.jsonl.gz', event_rows)
    dump_jsonl_gz(OUT / 'epoch_candidates.jsonl.gz', epoch_rows)
    dump_jsonl_gz(OUT / 'narrator_event_candidates.jsonl.gz', sorted(involvement, key=lambda r: r['id']))
    dump_jsonl_gz(OUT / 'location_candidates.jsonl.gz', location_rows)
    (OUT / 'works_and_editions.json').write_text(json.dumps(dict(sorted(editions.items())), ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (OUT / 'nothing_found.json').write_text(json.dumps(not_found, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    seed_events = [e for e in event_rows if e['origin'] == 'seed']
    new_events = [e for e in event_rows if e['origin'] != 'seed']
    passing_claims = [c for c in claims if c['ai_review']['outcome'] == 'passed']
    summary = {
        'ai_review_rule': AI_RULE_VERSION,
        'inputs_sha256': {'seed-history.ts': ht.sha256_file(SEED_FILE), 'lexicon_rijal_links.jsonl.gz': ht.sha256_file(LEXICON_LINKS),
                          **{e['openiti_uri']: e['source_sha256'] for e in editions.values()}},
        'seed_events': {'total': len(seed_events), **Counter(e['assessment'] for e in seed_events),
                        'compilation_split_proposals': sum(1 for e in seed_events if e['proposal'])},
        'seed_events_by_assessment': {k: sorted(e['title'] for e in seed_events if e['assessment'] == k) for k in sorted({e['assessment'] for e in seed_events})},
        'epochs': {'total': len(epoch_rows),
                   'start': Counter(r['start_assessment'] for r in epoch_rows), 'end': Counter(r['end_assessment'] for r in epoch_rows),
                   'both_boundaries_cited_and_passing': sum(1 for r in epoch_rows if r['publishable_under_ai_rule'])},
        'new_events_by_tradition': Counter(str(e['tradition_context'] or 'general') for e in new_events),
        'new_events_publishable': sum(1 for e in new_events if e['publishable_under_ai_rule']),
        'claims': {'total': len(claims), 'citation_status': Counter(c['citation_status'] for c in claims),
                   'ai_review': Counter(c['ai_review']['outcome'] for c in claims),
                   'failure_reasons': Counter(r.split(' (')[0] for c in claims for r in c['ai_review']['failure_reasons']),
                   'seed_comparison_of_passing': Counter(c['seed_comparison'] for c in passing_claims)},
        'contradicted_or_competing': [{'target': c['target'], 'boundary': c['boundary'], 'cited_year': c['year_hijri'],
                                       'seed_comparison': c['seed_comparison'], 'source': c['attributed_to'], 'citation_id': c['citation_id']}
                                      for c in passing_claims if c['seed_comparison'].startswith('differs')],
        'narrator_event_candidates': {'total': len(involvement), 'ai_review': Counter(r['ai_review']['outcome'] for r in involvement),
                                      'by_event': Counter(r['event_target'] for r in involvement),
                                      'failure_reasons': Counter(x for r in involvement for x in r['ai_review']['failure_reasons'])},
        'citations': len(citation_rows), 'nothing_found_searches': len(not_found),
    }
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    write_worksheets(claims, involvement, citations)
    print(json.dumps({k: summary[k] for k in ('seed_events', 'epochs', 'new_events_by_tradition', 'claims', 'narrator_event_candidates', 'citations')}, ensure_ascii=False, indent=1))


def write_worksheets(claims, involvement, citations):
    """150-row blank review worksheet: every date claim, then involvement rows in a fixed hash order to fill 150."""
    def digest(value):
        return hashlib.sha256(f'history-worksheet-v1|{value}'.encode()).hexdigest()
    dated = sorted(claims, key=lambda c: digest(c['id']))[:120]
    rows = [('date_claim', c['id'], c['target'], c['year_hijri'], c['stated_ar'], c['citation_id'], c['ai_review']['outcome']) for c in dated]
    extra = sorted(involvement, key=lambda r: digest(r['id']))[:150 - len(rows)]
    rows += [('involvement', r['id'], r['event_target'] + ' / ' + r['role'], None, r['stated_ar'], r['citation_id'], r['ai_review']['outcome']) for r in extra]
    with open(OUT / 'review_worksheet_150.csv', 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['row', 'kind', 'claim_id', 'target', 'claimed_year_hijri', 'stated_ar', 'source_reference', 'quote_ar',
                         'ai_review', 'reviewer_id', 'passage_states_this (yes/no/partly)', 'year_correct (yes/no)', 'subject_correct (yes/no)', 'notes'])
        for number, (kind, cid, target, year, stated, citation_id, outcome) in enumerate(rows, 1):
            citation = citations[citation_id]
            writer.writerow([number, kind, cid, target, year, stated, citation['source_reference'], citation['quote_ar'], outcome, '', '', '', '', ''])


if __name__ == '__main__':
    main()
