# Before/after strings for every judged-defect chain: Sunni (m2c -> m3), Imami (m1 -> m3), others skipped.
import csv,json,collections,re
csv.field_size_limit(10**9)
B='../../development/chain-builder-r2-2026-11-22/'
D=json.load(open('defects.json',encoding='utf8'))
su=set(d['hadith_id'] for d in D if d['lane'].startswith('sunni'));im=set(d['hadith_id'] for d in D if d['lane'].startswith('imami'))
def load(p,want):
    d=collections.defaultdict(lambda: collections.defaultdict(list))
    with open(B+p+'/canonical/chain_mentions.csv',encoding='utf8',newline='') as f:
        for r in csv.DictReader(f):
            if r['hadith_id'] in want:d[r['hadith_id']][r['chain_id']].append((int(r['position']),r['surface_ar']))
    return {h:{c:' > '.join(s for _,s in sorted(m)) for c,m in cs.items()} for h,cs in d.items()}
out={'sunni_before':load('projection-m2c',su),'sunni_after':load('projection-m3',su),'imami_before':load('projection-m1',im),'imami_after':load('projection-m3',im)}
json.dump(out,open('before_after3.json','w',encoding='utf8'),ensure_ascii=False)
print({k:len(v) for k,v in out.items()})
