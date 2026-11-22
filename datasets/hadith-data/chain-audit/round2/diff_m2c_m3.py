# Sunni diff of the pre-Sunni-fix projection (m2c) against the production projection (m3): trimmed, retired and re-cut mentions/chains.
import csv,sys,json,collections
csv.field_size_limit(10**9)
B='../../development/chain-builder-r2-2026-11-22/'
def load(p):
    m={}
    with open(B+p+'/canonical/chain_mentions.csv',encoding='utf8',newline='') as f:
        for r in csv.DictReader(f):
            if r['hadith_id'].startswith('hadith:k6:') or r['hadith_id'].startswith('hadith:pure-canon:'):
                m[r['id']]=(r['hadith_id'],r['chain_id'],int(r['position']),r['surface_ar'])
    return m
old=load('projection-m2c');new=load('projection-m3')
trimmed=[];retired=[]
for k,(h,c,pos,s) in old.items():
    if k not in new:retired.append((k,h,c,pos,s))
    elif new[k][3]!=s:trimmed.append((k,h,new[k][1],new[k][2],s,new[k][3]))
ch_old=collections.defaultdict(set);ch_new=collections.defaultdict(set)
for k,(h,c,p,s) in old.items():ch_old[h].add(c)
for k,(h,c,p,s) in new.items():ch_new[h].add(c)
split=[h for h in ch_new if len(ch_new[h])>len(ch_old.get(h,()))]
json.dump({'trimmed':trimmed,'retired':retired,'split':split},open('sunni_diff.json','w',encoding='utf8'),ensure_ascii=False)
print(len(old),len(new),'trimmed',len(trimmed),'retired',len(retired),'hadiths split',len(split))
