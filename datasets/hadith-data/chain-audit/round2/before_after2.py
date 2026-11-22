# For each Imami hadith with a judged defect: are the stored chains identical in projection-m1 (before the Imami fix) and m3 (now)?
import csv,sys,collections,json
csv.field_size_limit(10**9)
B='../../development/chain-builder-r2-2026-11-22/'
want=set(open('imami_defect_hadiths.txt').read().split())
def load(p):
    d=collections.defaultdict(lambda: collections.defaultdict(list))
    with open(B+p+'/canonical/chain_mentions.csv',encoding='utf8',newline='') as f:
        for r in csv.DictReader(f):
            if r['hadith_id'] in want:d[r['hadith_id']][r['chain_id']].append((int(r['position']),r['surface_ar']))
    return {h:sorted(' > '.join(s for _,s in sorted(m)) for m in cs.values()) for h,cs in d.items()}
a=load('projection-m1');b=load('projection-m3')
same=[h for h in want if a.get(h)==b.get(h)];diff=[h for h in want if a.get(h)!=b.get(h)]
print('defect hadiths',len(want),'unchanged by the fix',len(same),'changed',len(diff))
json.dump({'same':same,'diff':diff},open('imami_before_after.json','w'))
for h in diff[:14]:
    print('--',h.split(':')[-1][:8]);print(' BEFORE:',' | '.join(a.get(h,[]))[:260]);print(' NOW   :',' | '.join(b.get(h,[]))[:260])
