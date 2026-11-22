# Round 4: assemble sample_check.csv, verdicts.tsv and summary.json from the per-item read verdicts
# (v_main.txt, v_override.txt, u_main.txt, p_main.txt) and print every figure the README quotes.
import json, csv, math, collections


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})"


ids = json.load(open('sample_ids.json', encoding='utf8'))
unc = json.load(open('sample_ids_uncertain.json', encoding='utf8'))
pairs = json.load(open('pair_ids.json', encoding='utf8'))
v = {}
for f in ('v_main.txt', 'v_override.txt'):
    for l in open(f, encoding='utf8'):
        p = l.rstrip('\n').split('\t')
        p += [''] * (5 - len(p))
        v[int(p[0])] = p[1:]
u = {}
for l in open('u_main.txt', encoding='utf8'):
    p = l.rstrip('\n').split('\t')
    p += [''] * (4 - len(p))
    u[int(p[0])] = p[1:]
pp = {}
for l in open('p_main.txt', encoding='utf8'):
    p = l.rstrip('\n').split('\t')
    p += [''] * (4 - len(p))
    pp[int(p[0])] = p[1:]
assert len(v) == len(ids) == 310 and len(u) == len(unc) == 60 and len(pp) == len(pairs) == 150
JUDGMENT = {25, 55, 231}   # Companion named in the matn: a judgment call, same rule as round 3's rabi_0644 / rabi_0229
JUDGMENT_U = {3, 26}
rows = []
tsv = []
for i, x in enumerate(ids):
    verdict, report, kind, note = v[i]
    work = x['coll'].split(':')[-1]
    rows.append([x['lane'], work, 'random_checked', x['chain_id'], x['hadith_id'], verdict, kind, report, 'read',
                 ('companion_in_matn_judgment; ' if i in JUDGMENT else '') + note, '', '', '', ''])
    tsv.append(['main', i, x['lane'], x['hadith_id'], x['chain_id'], verdict, kind, note])
for i, x in enumerate(unc):
    verdict, kind, note = u[i]
    work = x['coll'].split(':')[-1]
    rows.append([x['lane'], work, 'random_uncertain', x['chain_id'], x['hadith_id'], verdict, kind, '', 'read',
                 ('companion_in_matn_judgment; ' if i in JUDGMENT_U else '') + note, '|'.join(x['reasons'] or []), '', '', ''])
    tsv.append(['uncertain', i, x['lane'], x['hadith_id'], x['chain_id'], verdict, kind, note])
for i, x in enumerate(pairs):
    verdict, idflag, note = pp[i]
    work = x['coll'].split(':')[-1]
    rows.append(['pair_' + x['lane'], work, 'random_pair', x['chain_id'], x['hadith_id'], 'ok' if verdict == 'yes' else 'defect',
                 'identity_' + idflag if idflag else '', '', 'read',
                 f"student={x['student']} teacher={x['teacher']} supports={x['support_n']}; " + note, '', '', '', ''])
    tsv.append(['pair', i, 'pair_' + x['lane'], x['hadith_id'], x['chain_id'], 'ok' if verdict == 'yes' else 'defect',
                'identity_' + idflag if idflag else '', note])
with open('sample_check.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['lane', 'work', 'stratum', 'chain_id', 'hadith_id', 'verdict', 'kind', 'report_verdict', 'judged_by', 'note',
                'structure_reasons', 'online_source', 'online_url', 'online_quote'])
    w.writerows(rows)
with open('verdicts.tsv', 'w', encoding='utf-8', newline='') as f:
    f.write('set\tindex\tlane\thadith_id\tchain_id\tverdict\tkind\tnote\n')
    for r in tsv:
        f.write('\t'.join(str(c).replace('\t', ' ').replace('\n', ' ') for c in r) + '\n')

S = {}


def grp(name, sel, col):
    xs = [(i, x) for i, x in enumerate(ids) if sel(x)]
    k = sum(1 for i, x in xs if v[i][col] == 'defect')
    S[name] = (k, len(xs))
    return k, len(xs)


groups = [
    ('Sunni (K6 six + Pure Canon)', lambda x: x['lane'].startswith('sunni')),
    ('Sunni K6 text works', lambda x: x['lane'] == 'sunni_k6'),
    ('Sunni Pure Canon', lambda x: x['lane'] == 'sunni_pc'),
    ('Muslim', lambda x: x['coll'].endswith(':muslim')),
    ('Imami', lambda x: x['lane'] == 'imami'),
    ('al-Kafi', lambda x: x['coll'].endswith('al-kafi')),
    ('Faqih', lambda x: x['coll'].endswith('faqih')),
    ('Thawab', lambda x: x['coll'].endswith('thawab-al-amal')),
    ('al-Rabi', lambda x: x['lane'] == 'rabi'),
    ('Zayd', lambda x: x['lane'] == 'zayd'),
    ('Rida', lambda x: x['lane'] == 'rida'),
]
for name, sel in groups:
    a = grp(name, sel, 0)
    b = grp(name + ' (report)', sel, 1)
    print(f"{name}: chain {fmt(*a)} | report-level {fmt(*b)}")
k6 = [(i, x) for i, x in enumerate(ids) if x['lane'] == 'sunni_k6']
print('K6 excluding judgment items:', fmt(sum(1 for i, x in k6 if v[i][0] == 'defect' and i not in JUDGMENT), sum(1 for i, x in k6 if i not in JUDGMENT)))
for w_ in ['bukhari', 'muslim', 'nasai', 'tirmidhi', 'abudawud', 'ibnmajah']:
    xs = [(i, x) for i, x in k6 if x['coll'].endswith(w_)]
    print(w_, sum(1 for i, x in xs if v[i][0] == 'defect'), len(xs))
print('chain defect kinds', collections.Counter(v[i][2] for i, x in enumerate(ids) if v[i][0] == 'defect'))
print('--- uncertain')
for lane in ('u_sunni', 'u_imami', None):
    xs = [(i, x) for i, x in enumerate(unc) if lane is None or x['lane'] == lane]
    k = sum(1 for i, x in xs if u[i][0] == 'correct')
    print(lane or 'all', fmt(k, len(xs)))
rc = collections.defaultdict(lambda: [0, 0])
for i, x in enumerate(unc):
    for r in (x['reasons'] or []):
        rc[r][1] += 1
        rc[r][0] += u[i][0] == 'correct'
print('by reason (a chain counts under each reason it carries):')
for r, (k, n) in sorted(rc.items(), key=lambda t: -t[1][1]):
    print(' ', r, fmt(k, n))
sole = collections.defaultdict(lambda: [0, 0])
for i, x in enumerate(unc):
    if len(x['reasons'] or []) == 1:
        r = x['reasons'][0]
        sole[r][1] += 1
        sole[r][0] += u[i][0] == 'correct'
print('single-reason chains:')
for r, (k, n) in sorted(sole.items(), key=lambda t: -t[1][1]):
    print(' ', r, fmt(k, n))
print('uncertain defect kinds', collections.Counter(u[i][1] for i, x in enumerate(unc) if u[i][0] == 'defect'))
print('--- pairs')
for lane in ('sunni', 'imami', None):
    xs = [(i, x) for i, x in enumerate(pairs) if lane is None or x['lane'] == lane]
    k = sum(1 for i, x in xs if pp[i][0] == 'yes')
    print(lane or 'all', fmt(k, len(xs)))
strong = [i for i in pp if pp[i][1] == 'strong']
weak = [i for i in pp if pp[i][1] == 'weak']
print('identity strong', strong, 'weak', weak, fmt(len(strong), 150), fmt(len(strong) + len(weak), 150))
json.dump({'groups': {k: {'defects': a, 'n': b} for k, (a, b) in S.items()}}, open('summary.json', 'w'), ensure_ascii=False, indent=1)
