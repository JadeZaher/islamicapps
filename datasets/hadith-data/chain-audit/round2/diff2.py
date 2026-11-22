# Per-hadith comparison of old (m2c) and new (m3) Sunni surfaces: trimmed (new is a proper contiguous sub-run of old) and dropped (old has no counterpart).
import csv,json,re,collections,random
csv.field_size_limit(10**9)
B='../../development/chain-builder-r2-2026-11-22/'
def norm(s):
    s=re.sub(r'[ً-ْٰـ]','',s);s=re.sub('[أإآٱ]','ا',s).replace('ى','ي')
    return tuple(t for t in re.split(r'[^ء-ي]+',s) if t)
def load(p):
    d=collections.defaultdict(list)
    with open(B+p+'/canonical/chain_mentions.csv',encoding='utf8',newline='') as f:
        for r in csv.DictReader(f):
            h=r['hadith_id']
            if h.startswith('hadith:k6:') or h.startswith('hadith:pure-canon:'):d[h].append((r['chain_id'],int(r['position']),r['surface_ar']))
    return d
old=load('projection-m2c');new=load('projection-m3')
def sub(a,b):  # b proper contiguous sub-run of a
    n=len(b)
    return n<len(a) and any(a[i:i+n]==b for i in range(len(a)-n+1))
trim=[];drop=[]
for h,ol in old.items():
    nl=new.get(h,[]);nset={norm(s):(c,p,s) for c,p,s in nl}
    for c,p,s in ol:
        o=norm(s)
        if not o:continue
        if o in nset:continue
        hit=[v for k,v in nset.items() if k and sub(o,k)]
        sup=[v for k,v in nset.items() if k and (o==k or (len(k)>len(o) and sub(k,o)))]
        if hit:trim.append((h,c,p,s,hit[0][2],hit[0][0]))
        elif not sup:drop.append((h,c,p,s))
json.dump({'trim':trim,'drop':drop},open('sunni_diff2.json','w',encoding='utf8'),ensure_ascii=False)
print('trim',len(trim),'drop',len(drop))
