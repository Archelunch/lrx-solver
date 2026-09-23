"""Data-only adjacent-comparison policies feeding exact all-length mixtures."""
import hashlib
import json
import time
from fractions import Fraction
from functools import lru_cache
from itertools import permutations

from integrations.projected_mixtures import (state_for, project, comparison, ranks,
    materialize, verify_mixture)
from integrations.mixture_lp import optimize

ORDERS = tuple(permutations(range(1, 9)))
FEATURES = ('rotation', 'zero_rotation', 'zero_swap', 'position', 'rank_gap')
SCHEMA = '''Return one JSON object, no code:
{"kind":"mixture_policy","name":"description","rules":[{"cuts":[0,4,8],"weights":{"rotation":1,"zero_rotation":1,"zero_swap":0,"position":0,"rank_gap":0},"direction":"shortest","tie":"left"}]}
1..8 rules, each has 1..4 distinct cuts (integers 0..16, reduced modulo n).
All five weights must be integers -16..16. direction is shortest/left/right;
tie is left/right. No other fields or state-specific exceptions.
For each rule and cut, construct a complete word on the family's unit-block state.
Keep a physical array with stable ranks toward canonical target, linearized at cut.
Choose an adjacent inverted pair that does not cross cut. Choose rotation direction
by direction (shortest uses fewest steps, tie left). Minimize weighted sum of:
rotation=steps to pair; zero_rotation=zeros crossed by that rotation;
zero_swap=1 if pair contains a zero; position=pair index relative to cut;
rank_gap=left rank minus right rank. Break score ties by physical pair index
ascending (tie left) or descending (tie right). Rotate, swap, repeat; finally
rotate by shortest path back to canonical phase. Every swap decreases inversions.
Each policy supplies at most 32 words per family. Existing catalog profiles stay
fixed; LP finds mixtures of those profiles and new words. Exact weights must sum
one, weighted base <31+6k and every weighted block slope <=6. Such a mixture
certifies all positive block lengths via reviewed comparison/stretching lemmas.
Maximize number of certified development families, then reduce base-price deficits.
A miss is not infeasibility. Seek complementary slope profiles, not only short words.
'''


class Policy:
    def __init__(self, spec):
        if not isinstance(spec, dict) or set(spec) != {'kind','name','rules'} or spec['kind'] != 'mixture_policy':
            raise ValueError('invalid mixture policy fields')
        if not isinstance(spec['name'],str) or len(spec['name'])>160: raise ValueError('invalid name')
        if not isinstance(spec['rules'],list) or not 1<=len(spec['rules'])<=8: raise ValueError('invalid rules')
        for r in spec['rules']:
            if not isinstance(r,dict) or set(r)!={'cuts','weights','direction','tie'}: raise ValueError('invalid rule')
            if not isinstance(r['cuts'],list) or not 1<=len(r['cuts'])<=4 or any(type(c) is not int or not 0<=c<=16 for c in r['cuts']) or len(set(r['cuts']))!=len(r['cuts']): raise ValueError('invalid cuts')
            if not isinstance(r['weights'],dict) or set(r['weights'])!=set(FEATURES) or any(type(v) is not int or not -16<=v<=16 for v in r['weights'].values()): raise ValueError('invalid weights')
            if r['direction'] not in ('shortest','left','right') or r['tie'] not in ('left','right'): raise ValueError('invalid direction/tie')
        self.spec=json.loads(json.dumps(spec))
        self.hash=hashlib.sha256(json.dumps({k:v for k,v in spec.items() if k!='name'},sort_keys=True).encode()).hexdigest()[:16]


def construct(state, cut, rule):
    n=len(state);cut%=n;atoms=list(state);at=0;word=[]
    rank=list(ranks(tuple(state),cut,0))
    # rank is stored in linear-cut order, atoms in physical order.
    while True:
        choices=[]
        for pos in range(n):
            j=(pos-cut)%n
            if j==n-1 or rank[j]<=rank[j+1]: continue
            left=(pos-at)%n;right=(at-pos)%n
            direction=rule['direction']
            if direction=='shortest': direction='left' if left<=right else 'right'
            steps=left if direction=='left' else right
            crossed=[(at+t)%n for t in range(steps)] if direction=='left' else [(at-1-t)%n for t in range(steps)]
            values=(steps,sum(atoms[t]==0 for t in crossed),int(atoms[pos]==0 or atoms[(pos+1)%n]==0),j,rank[j]-rank[j+1])
            score=sum(rule['weights'][f]*v for f,v in zip(FEATURES,values))
            choices.append((score,pos if rule['tie']=='left' else -pos,pos,j,direction,steps))
        if not choices: break
        _,_,pos,j,direction,steps=min(choices)
        word.extend(('L' if direction=='left' else 'R')*steps);word.append('X')
        at=pos;atoms[pos],atoms[(pos+1)%n]=atoms[(pos+1)%n],atoms[pos]
        rank[j],rank[j+1]=rank[j+1],rank[j]
    left=(-at)%n;right=at
    word.extend('L'*left if left<=right else 'R'*right)
    return ''.join(word)


def prune(profiles):
    kept=[]
    for p in sorted(profiles,key=lambda p:(p['base'],sum(p['gamma']))):
        if not any(q['base']<=p['base'] and all(a<=b for a,b in zip(q['gamma'],p['gamma'])) for q in kept): kept.append(p)
    return kept


@lru_cache(32768)
def projected(source_json,mask):
    return project(json.loads(source_json),mask,0)[:2]


def catalog_profiles(case,bundle,pool):
    labels=ORDERS[case['order_index']];profiles=[];seen=set()
    record=bundle['records'][case['order_index']]
    if record['order_index']!=case['order_index']: raise ValueError('record order mismatch')
    sources=set(pool)|{r['source'] for r in record['mixture']}
    for i in sorted(sources):
        state,word=projected(json.dumps(bundle['catalog'][i],sort_keys=True),case['mask'])
        for cut in range(len(state)):
            if (word,cut) in seen: continue
            seen.add((word,cut));p=comparison(state,word,cut,labels)
            if p: profiles.append(dict(p,source=i))
    return prune(profiles)


def certificate(profiles, result):
    if result['status']!='CERTIFICATE': return None
    support=[dict(profile=p,weight=w) for p,w in zip(profiles,result['weights']) if Fraction(w)>0]
    rebuilt=[]
    for row in support:
        p=row['profile'];q=comparison(tuple(p['state']),p['word'],p['cut'],[x for x in p['target'] if x])
        if q is None or any(q[key]!=p[key] for key in q): raise ValueError('profile reconstruction failed')
        rebuilt.append(q)
        for lengths in ([1]*len(q['gamma']),list(range(1,len(q['gamma'])+1))): materialize(q,lengths)
    bounds=verify_mixture(rebuilt,[s['weight'] for s in support])
    return dict(bounds=bounds,support=support,scope='all positive lengths via reviewed manuscript lemmas')


class Evaluator:
    def __init__(self,cases,baseline,role='train'):
        if role not in ('train','confirmation'): raise ValueError('invalid role')
        self.role=role;self.cases=cases;self.baseline=baseline;self.cache={}
        self.dataset_hash=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()
    def evaluate(self,spec):
        policy=Policy(spec)
        if policy.hash in self.cache:return self.cache[policy.hash]
        start=time.perf_counter();rows=[]
        for case in self.cases:
            profiles=list(self.baseline[case['id']]);state=state_for(ORDERS[case['order_index']],case['mask']);seen=set();added=[]
            for rule in policy.spec['rules']:
                for rawcut in rule['cuts']:
                    cut=rawcut%len(state);word=construct(state,cut,rule)
                    if (cut,word) in seen:continue
                    seen.add((cut,word));p=comparison(state,word,cut,ORDERS[case['order_index']])
                    if p is None:raise ValueError('constructed word failed comparison premises')
                    profiles.append(p);added.append({'base':p['base'],'gamma':p['gamma']})
            profiles=prune(profiles);result=optimize(profiles);cert=certificate(profiles,result)
            deficit=max(0,float(Fraction(result['base']))-(31+6*case['blocks'])) if 'base' in result else 100
            rows.append(dict(case=case,certificate=cert,deficit=deficit,lp_status=result['status'],profiles=added))
        missed=sum(r['certificate'] is None for r in rows)
        penalty=sum(min(100,r['deficit']) for r in rows)
        score=-(100*len(rows)+1)*missed-penalty
        graphs=[dict(graph=f'k{k}',score=-sum(1000*(r['certificate'] is None)+min(100,r['deficit']) for r in rows if r['case']['blocks']==k),failures=sum(r['certificate'] is None for r in rows if r['case']['blocks']==k),role=self.role,feedback=self.role=='train') for k in range(4,9)]
        result=dict(valid=True,kind='mixture_policy',candidate_hash=policy.hash,score=score,feasible=missed==0,stopped=False,missed=missed,certified=len(rows)-missed,instances={g['graph']:g['score'] for g in graphs},graphs=graphs,cases=rows,seconds=time.perf_counter()-start)
        self.cache[policy.hash]=result;return result
    def feedback(self,result):
        if self.role!='train':raise ValueError('confirmation feedback forbidden')
        return dict(score=result['score'],certified=result['certified'],missed=result['missed'],graphs=result['graphs'],failures=[dict(case=r['case'],base_deficit=r['deficit'],generated_profiles=r['profiles'][:8]) for r in sorted(result['cases'],key=lambda r:-r['deficit']) if r['certificate'] is None][:4],interpretation='Misses do not prove infeasibility; equal base threshold is insufficient. Every slope must be <=6.')
