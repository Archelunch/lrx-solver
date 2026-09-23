"""Cross-check certificates through trusted repeated marked-zero projection."""
import json,sys,zipfile
from pathlib import Path
from functools import lru_cache
from fractions import Fraction
P=Path(__file__).resolve().parent;ROOT=P.parents[1];sys.path.insert(0,str(ROOT))
from src.lrx.certificates import CertificateValidator
from integrations.projected_mixtures import project,comparison,materialize,verify_mixture
from integrations.mixture_lp import optimize

with zipfile.ZipFile(ROOT/'autoresearch/loop-260923-2107/incoming/verification.zip') as z:
    bundle=json.loads(z.read('literature/multiset_nine_gap_complete_certificates_20260924.json'))
catalog=bundle['catalog'];records={r['order_index']:r for r in bundle['records']}

@lru_cache(None)
def trusted_projection(source,mask):
    state=tuple(catalog[source]['state']);word=catalog[source]['word']
    for gap in reversed(range(9)):
        if mask>>gap&1:continue
        j=2*gap;u=state[:j]+state[j+1:]
        result=CertificateValidator(8,len(state)-8).replay_word(word,start_state=(u,j))
        if not result.replay_valid or not result.terminal:raise ValueError('trusted projection failed')
        word=result.projection_sequence;state=u
    reduced=[]
    for c in word:
        if reduced and (reduced[-1],c) in (('L','R'),('R','L')):reduced.pop()
        else:reduced.append(c)
    expected,other,_=project(catalog[source],mask,0)
    if state!=expected or ''.join(reduced)!=other:raise ValueError('independent projection disagreement')
    return state,other

summary={};ablation=[]
for role in ['train','confirmation']:
    data=json.loads((P/f'{role}-v2-results.json').read_text());families=components=literal=nonaffine=0
    for row in data['results']:
        cert=row['certificate']
        if cert:
            profiles=[];weights=[]
            for ref in cert['references']:
                state,word=trusted_projection(ref['source'],row['mask'])
                profile=comparison(state,word,ref['cut'],row['labels'])
                if profile is None:raise ValueError('comparison premise failed')
                profiles.append(profile);weights.append(ref['weight']);components+=1;nonaffine+=not profile['affine']
                k=row['blocks']
                for lengths in [[1]*k]+[[1+int(i==j) for i in range(k)] for j in range(k)]+[list(range(2,k+2))]:
                    materialize(profile,lengths);literal+=1
            checked=verify_mixture(profiles,weights)
            if checked!=cert['bounds']:raise ValueError('stored bound mismatch')
            families+=1
        if role=='train':
            profiles=[]
            for ref in records[row['order_index']]['mixture']:
                source=catalog[ref['source']]
                full=comparison(tuple(source['state']),source['word'],ref['cut'],row['labels'])
                state,word,cut=project(source,row['mask'],ref['cut'])
                projected=comparison(state,word,cut,row['labels'])
                upper=[g for j,g in enumerate(full['gamma']) if row['mask']>>j&1]
                if any(a>b for a,b in zip(projected['gamma'],upper)):raise ValueError('coefficient monotonicity violated')
                profiles.append(dict(base=projected['base'],gamma=upper))
            result=optimize(profiles)
            if result['status']=='CERTIFICATE':verify_mixture(profiles,result['weights'])
            ablation.append(dict(case=row['id'],status=result['status'],base=result.get('base')))
    summary[role]=dict(certified_families=families,components=components,expanded_component_replays=literal,nonaffine_upper_bound_components=nonaffine)
report=dict(status='PASS',roles=summary,unique_trusted_projections=trusted_projection.cache_info().currsize,
    development_ablation=dict(description='Optimize inherited support retaining the old nine-gap coefficient bounds, instead of recomputing projected coefficients.',certified=sum(r['status']=='CERTIFICATE' for r in ablation),cases=ablation))
with (P/'certificate-audit.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='development_ablation'}));print('old-coefficient ablation',report['development_ablation']['certified'])
