# Hadiths that have a live chain in the earlier projection but none now (OpenITI works: v6 -> m3; Imami: m1 -> m3).
import csv,collections,json,sys
csv.field_size_limit(10**9)
D='../../development/'
def hs(path,pref):
    s=collections.Counter()
    with open(path,encoding='utf8',newline='') as f:
        for r in csv.DictReader(f):
            if r['hadith_id'].startswith(pref):s[r['hadith_id']]+=1
    return s
res={}
for name,pref,before in [('openiti','hadith:openiti:',D+'openiti-fix-2026-11-21/projection-v6/canonical/chains.csv'),('imami_thaq','hadith:thaqalayn:',D+'chain-builder-r2-2026-11-22/projection-m1/canonical/chains.csv')]:
    try:
        b=hs(before,pref)
    except Exception as e:
        print(name,'before missing',e);continue
    a=hs(D+'chain-builder-r2-2026-11-22/projection-m3/canonical/chains.csv',pref)
    lost=[h for h in b if h not in a];gained=[h for h in a if h not in b]
    print(name,'hadiths with chain before',len(b),'after',len(a),'lost',len(lost),'gained',len(gained))
    res[name]={'lost':lost,'gained':gained[:50]}
    c=collections.Counter(h.split(':')[2] if name=='openiti' else 'thaq' for h in lost);print(' lost by',dict(c))
json.dump(res,open('nochain.json','w'))
