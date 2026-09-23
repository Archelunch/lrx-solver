"""Bounded data-only word-construction policies, evaluated by trusted replay.

This search-side language is separate from the locked controller DSL. A miss
is a portfolio failure, never a counterexample to A_q or the LRX conjecture.
"""
import hashlib
import json
import time
from pathlib import Path

from integrations.word_lift import lift_fixed_word
from src.lrx.table_bfs import DistanceTable
from src.lrx.state import validate_vector

ROOT=Path(__file__).resolve().parents[1]
ORDERS=('LRX','LXR','RLX','RXL','XLR','XRL')


class Policy:
    def __init__(self,spec):
        if not isinstance(spec,dict) or set(spec)-{'kind','name','zero_order','paths'}:
            raise ValueError('policy keys: kind,name,zero_order,paths')
        if spec.get('kind')!='lift_policy': raise ValueError('kind must be lift_policy')
        if not isinstance(spec.get('name',''),str) or len(spec.get('name',''))>100:
            raise ValueError('name must be <=100 characters')
        if spec.get('zero_order') not in ('left','right','distance_high','distance_low'):
            raise ValueError('invalid zero_order')
        paths=spec.get('paths')
        if not isinstance(paths,list) or not 1<=len(paths)<=8: raise ValueError('1..8 paths required')
        for p in paths:
            if not isinstance(p,dict) or set(p)!={'orders','period','axis','detour','detour_steps'}:
                raise ValueError('path keys: orders,period,axis,detour,detour_steps')
            if not isinstance(p['orders'],list) or not 1<=len(p['orders'])<=4 or any(o not in ORDERS for o in p['orders']):
                raise ValueError('orders: 1..4 permutations of LRX')
            if type(p['period']) is not int or not 1<=p['period']<=16: raise ValueError('period 1..16')
            if p['axis'] not in ('step','distance','front_zeros'): raise ValueError('invalid axis')
            if p['detour'] not in ('none','level','uphill','either'): raise ValueError('invalid detour')
            steps=p['detour_steps']
            if not isinstance(steps,list) or len(steps)>4 or any(type(i) is not int or not 0<=i<=32 for i in steps) or len(set(steps))!=len(steps):
                raise ValueError('detour_steps: up to 4 distinct integers 0..32')
            if p['detour']=='none' and steps: raise ValueError('none detour requires empty steps')
        self.spec=json.loads(json.dumps(spec))
        canonical={k:v for k,v in spec.items() if k!='name'}
        self.hash=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
        self.kind='lift_policy'
        self.complexity=sum(1+len(p['orders'])+len(p['detour_steps']) for p in paths)


def baseline():
    return dict(kind='lift_policy',name='six fixed geodesic orders',zero_order='left',
        paths=[dict(orders=[o],period=1,axis='step',detour='none',detour_steps=[]) for o in ORDERS])


def move(w,c):
    return w[1:]+w[:1] if c=='L' else w[-1:]+w[:-1] if c=='R' else (w[1],w[0])+w[2:]


def construct(table,u,path,q,defect=None):
    """At most one prescribed non-descending edge; every other edge descends."""
    w=tuple(u);d=table.distance(w);letters=[];events=[]
    if d>q: return None
    while d:
        t=len(letters)
        axis=t if path['axis']=='step' else d if path['axis']=='distance' else int(w[0]==0)+int(w[1]==0)
        order=path['orders'][(axis//path['period'])%len(path['orders'])]
        picked=None
        for c in order:
            w2=move(w,c)
            if w2==w: continue
            d2=table.distance(w2)
            if t==defect:
                good=(d2==d if path['detour']=='level' else d2==d+1 if path['detour']=='uphill' else d2>=d)
            else: good=d2==d-1
            if good and t+1+d2<=q:
                picked=(c,w2,d2);break
        if picked is None: return None
        c,w2,d2=picked
        if d2>=d: events.append(dict(index=t,letter=c,before=d,after=d2))
        letters.append(c);w,d=w2,d2
    if defect is not None and not events: return None
    return ''.join(letters),events


class PolicyEvaluator:
    def __init__(self,dataset,role='train',max_words=96):
        if role not in ('train','confirmation'): raise ValueError('invalid role')
        self.dataset=json.loads(json.dumps(dataset))
        if not self.dataset: raise ValueError('empty dataset')
        self.role=role
        if type(max_words) is not int or max_words<1: raise ValueError('invalid word cap')
        self.max_words=max_words;self.tables={};self.cache={}
        for c in self.dataset:
            validate_vector(tuple(c['v']),c['m'],c['r'])
            m,r=c['m'],c['r']
            if m<8 or r<3: raise ValueError('this proof-facing evaluator requires m>=8,r>=3')
            q=m*(m+1)//2+(r-2)*(m-2)+1
            b=m*(m+1)//2+(r-1)*(m-2)
            if c['q']!=q or c['bound']!=b: raise ValueError('case must use conjecture-facing q=Q+1 and B=T')
        self.dataset_hash=hashlib.sha256(json.dumps(self.dataset,sort_keys=True).encode()).hexdigest()

    def table(self,m,r):
        key=(m,r)
        if key not in self.tables:
            directory=ROOT/'datasets/generated'
            if not (directory/f'dist_m{m}_r{r-1}.json').exists():
                directory=ROOT/'runs/bfs-crosscheck-260923/tables'
            self.tables[key]=DistanceTable(directory,m,r-1)
        return self.tables[key]

    def evaluate_case(self,policy,c):
        m,r,v=c['m'],c['r'],tuple(c['v']);table=self.table(m,r)
        zeros=[j for j,x in enumerate(v) if x==0]
        if policy.spec['zero_order']=='right': zeros.reverse()
        elif policy.spec['zero_order'].startswith('distance'):
            zeros.sort(key=lambda j:table.distance(v[:j]+v[j+1:]),reverse=policy.spec['zero_order']=='distance_high')
        # Every deletion and path gets its base-word opportunity before detours.
        variants=[(path,None) for path in policy.spec['paths']]
        variants += [(path,t) for path in policy.spec['paths'] for t in path['detour_steps']]
        tried=0;generated=0;best=None;seen=set();capped=False
        for path,defect in variants:
            for j in zeros:
                if generated>=self.max_words:
                    capped=True;break
                generated+=1
                u=v[:j]+v[j+1:]
                candidate=construct(table,u,path,c['q'],defect)
                if candidate is None: continue
                word,events=candidate
                if (j,word) in seen: continue
                seen.add((j,word));tried+=1
                lift=lift_fixed_word(m,r,u,j,word)
                if lift['length'] is not None and (best is None or lift['length']<best['length']):
                    best=dict(lift,j=j,defects=events)
                if best and best['length']<=c['bound']: break
            if capped or (best and best['length']<=c['bound']): break
        return dict(case=c['id'],family=c['family'],m=m,r=r,v=v,q=c['q'],bound=c['bound'],
            within_bound=bool(best and best['length']<=c['bound']),best=best,
            generated=generated,routed=tried,word_cap_reached=capped,
            status='WITNESS' if best and best['length']<=c['bound'] else 'PORTFOLIO_MISS')

    def evaluate(self,spec):
        policy=Policy(spec)
        if policy.hash in self.cache: return self.cache[policy.hash]
        start=time.perf_counter();rows=[self.evaluate_case(policy,c) for c in self.dataset]
        groups={}
        for row in rows: groups.setdefault(row['family'],[]).append(row)
        def excess(row):
            return min(100,max(0,row['best']['length']-row['bound'])) if row['best'] else 100
        missed=sum(not row['within_bound'] for row in rows)
        over=[excess(row) for row in rows]
        excess_weight=100*len(rows)+1
        miss_weight=101*excess_weight
        score=-miss_weight*missed-excess_weight*max(over,default=0)-sum(over)-policy.complexity/10000
        graphs=[]
        for key,items in groups.items():
            failures=sum(not x['within_bound'] for x in items)
            graphs.append(dict(graph=key,m=items[0]['m'],r=items[0]['r'],role=self.role,
                feedback=self.role=='train',checked=len(items),failures=failures,incomplete=0,
                score=-1000*failures-sum(excess(x) for x in items),
                T=items[0]['bound'],value_max=max((x['best']['length'] for x in items if x['best']),default=None)))
        out=dict(valid=True,kind='lift_policy',candidate_hash=policy.hash,score=score,
             feasible=missed==0,stopped=False,instances={g['graph']:g['score'] for g in graphs},
             graphs=graphs,cases=rows,missed=missed,max_excess=max(over,default=0),
             complexity=policy.complexity,seconds=time.perf_counter()-start,
             dataset_sha256=self.dataset_hash,claim_scope='finite construction evidence; misses are not lower bounds')
        self.cache[policy.hash]=out
        return out

    def feedback(self,result):
        if self.role!='train': raise ValueError('confirmation feedback is forbidden')
        rows=sorted(result['cases'],key=lambda x:(x['within_bound'],-(x['best']['length']-x['bound'] if x['best'] else 100)))
        return dict(score=result['score'],missed=result['missed'],max_excess=result['max_excess'],
            complexity=result['complexity'],families=result['instances'],graphs=result['graphs'],
            failures=[{k:x[k] for k in ('case','m','r','v','q','bound','status','generated','routed','word_cap_reached')}
              | {'best_length':x['best']['length'] if x['best'] else None,
                 'projection_length':x['best']['projection_length'] if x['best'] else None,
                 'routing_overhead':x['best']['overhead'] if x['best'] else None,
                 'defects':x['best']['defects'] if x['best'] else []}
              for x in rows if not x['within_bound']][:4],
            interpretation='A portfolio miss is not a lifting counterexample. Scoring prioritizes fewer misses, then excess, then simpler policies.')
