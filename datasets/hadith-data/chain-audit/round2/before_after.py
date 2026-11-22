# Before (projection-m1, pre-Imami fix) vs now (projection-m3) mentions for chosen Imami hadiths.
import csv,sys,collections
csv.field_size_limit(10**9)
B='../../development/chain-builder-r2-2026-11-22/'
want=set(sys.argv[1:])
def load(p):
    d=collections.defaultdict(lambda: collections.defaultdict(list))
    with open(B+p+'/canonical/chain_mentions.csv',encoding='utf8',newline='') as f:
        for r in csv.DictReader(f):
            if r['hadith_id'] in want:d[r['hadith_id']][r['chain_id']].append((int(r['position']),r['surface_ar']))
    return d
for p in ('projection-m1','projection-m3'):
    d=load(p);print('==',p)
    for h in sorted(want):
        for c,m in sorted(d[h].items())[:4]:
            print(h.split(':')[-1][:8],c.split(':')[-1],' > '.join(s for _,s in sorted(m)))
