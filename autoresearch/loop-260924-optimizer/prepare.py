import hashlib, json, random, sys, zipfile
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];sys.path.insert(0,str(ROOT))
from integrations.mixture_inventory import residual_inventory
from integrations.mixture_policy import catalog_profiles, certificate, Evaluator
from integrations.mixture_lp import optimize
old=ROOT/'autoresearch/loop-260923-2154'
archive=ROOT/'autoresearch/loop-260923-2107/incoming/verification.zip'
res=residual_inventory(archive);rng=random.Random(2026092409)
used={(c['mask'],c['order_index']) for role in ('train','confirmation') for c in json.loads((old/f'{role}-v2.json').read_text())}
confirmation=[]
for k in range(4,9):
    masks=[m for m in res if m.bit_count()==k]
    while sum(c['blocks']==k for c in confirmation)<6:
        m=rng.choice(masks);i=rng.randrange(40320)
        if (m,i) in used or not res[m]>>i&1:continue
        used.add((m,i));confirmation.append(dict(id=f'k{k}-mask{m}-order{i}',mask=m,order_index=i,blocks=k))
(P/'confirmation.json').write_text(json.dumps(confirmation,indent=2)+'\n')
train=[{k:r[k] for k in ('id','mask','order_index','blocks')} for r in json.loads((old/'train-v2-results.json').read_text())['results'] if r['certificate'] is None]
(P/'baseline-cases.json').write_text(json.dumps(train,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:bundle=json.loads(z.read('literature/multiset_nine_gap_complete_certificates_20260924.json'))
pool=list(range(len(bundle['catalog'])));random.Random(2026092408).shuffle(pool);pool=pool[:512]
(P/'pool.json').write_text(json.dumps(pool)+'\n')
baseline={};rows=[];remaining=[]
for c in train:
    profiles=catalog_profiles(c,bundle,pool);result=optimize(profiles);cert=certificate(profiles,result)
    baseline[c['id']]=profiles;rows.append(dict(case=c,result=result,certificate=cert))
    if cert is None:remaining.append(c)
    print(json.dumps(dict(done=len(rows),closed=sum(r['certificate'] is not None for r in rows))),flush=True)
(P/'baseline.json').write_text(json.dumps(baseline)+'\n')
(P/'baseline-results.json').write_text(json.dumps(rows,indent=2)+'\n')
(P/'train.json').write_text(json.dumps(remaining,indent=2)+'\n')
seed=dict(kind='mixture_policy',name='nearest adjacent inversion, three cuts',rules=[dict(cuts=[0,4,8],weights=dict(rotation=1,zero_rotation=0,zero_swap=0,position=0,rank_gap=0),direction='shortest',tie='left')])
(P/'seed.json').write_text(json.dumps(seed,indent=2)+'\n')
result=Evaluator(remaining,baseline).evaluate(seed)
(P/'seed-eval.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(train=len(remaining),baseline_closed=len(train)-len(remaining),seed_certified=result['certified'],seed_seconds=result['seconds'])))
