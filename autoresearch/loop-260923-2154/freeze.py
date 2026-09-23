"""Freeze structural cases from the supplied residual inventory, before search."""
import hashlib,json,random,zipfile
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
archive=ROOT/'autoresearch/loop-260923-2107/incoming/verification.zip'
with zipfile.ZipFile(archive) as z:res=json.loads(z.read('literature/multiset_nine_gap_projection_search_20260924.json'))
rng=random.Random(2026092408);used=set();roles={'train':[],'confirmation':[]}
for k in range(4,9):
    masks=[(r['mask'],int(r['order_bits_hex'],16)) for r in res['residual'] if r['mask'].bit_count()==k]
    for role,count in [('train',20),('confirmation',10)]:
        while sum(c['blocks']==k for c in roles[role])<count:
            mask,bits=rng.choice(masks);index=rng.randrange(40320)
            if not bits>>index&1 or (mask,index) in used:continue
            used.add((mask,index));roles[role].append(dict(id=f'k{k}-mask{mask}-order{index}',mask=mask,order_index=index,blocks=k))
for name,data in roles.items():
    with (P/f'{name}.json').open('x') as f:json.dump(data,f,indent=2)
config=dict(seed=2026092408,extra_catalog_sources=128,pivot_limit=500,max_seconds=1800,
    baseline='independently checked inherited mixture and scalar reverse transfer exclusion on selected source-reported residual cases; not a reconstructed global complement',api_spend_usd=0)
with (P/'config.json').open('x') as f:json.dump(config,f,indent=2)
print({k:len(v) for k,v in roles.items()})
