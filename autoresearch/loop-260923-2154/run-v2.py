"""Bounded, data-only mixture search; no model calls or archive code imports."""
import argparse,hashlib,json,random,sys,time,zipfile
from fractions import Fraction
from functools import lru_cache
from itertools import permutations
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];sys.path.insert(0,str(ROOT))
from integrations.projected_mixtures import project,comparison,verify_mixture,materialize,state_for
from integrations.mixture_lp import optimize
from tools.orchestrator import trusted_status


def family_mask(base):
    seen=mask=0
    for x in base:
        if x:seen+=1
        else:mask|=1<<seen
    return mask


@lru_cache(None)
def clauses(base,origin,word):
    expanded=[];j=0
    for x in base:
        if x:expanded.append(x)
        else:expanded.extend([0]*origin[j]);j+=1
    n=len(expanded);at=0;blocked=set()
    for c in word:
        if c=='X':blocked.add((at+1)%n)
        else:at=(at+(1 if c=='L' else -1))%n
    labels=tuple(x for x in base if x);out=set()
    for cut in range(n):
        if cut in blocked:continue
        start=sum(bool(x) for x in expanded[:cut])%8
        window=labels[start:]+labels[:start]
        order=sorted(range(1,9),key=lambda x:(at+x-1-cut)%n)
        rank={x:i for i,x in enumerate(order)};q=tuple(rank[x] for x in window);width=q[0]+1
        if q!=tuple(range(width-1,-1,-1))+tuple(range(7,width-1,-1)):
            raise ValueError('reverse domain pattern premise failed')
        out.add((start,width,frozenset(window[:width])))
    return tuple(out)


def reverse_accepts(base,tree,labels):
    if tree['kind']=='split':return reverse_accepts(base,tree['left'],labels) and reverse_accepts(base,tree['right'],labels)
    if tree['kind']!='affine':raise ValueError('unknown reverse tree node')
    for row in tree['rows']:
        if Fraction(row['weight'])==0:continue
        available=clauses(tuple(base),tuple(row['origin']),row['word'])
        if not any(frozenset(labels[(start+j)%8] for j in range(width))==wanted for start,width,wanted in available):return False
    return True


def finalize(profiles,result,case,catalog,labels):
    if result['status']!='CERTIFICATE':return None
    kept=[(p,w) for p,w in zip(profiles,result['weights']) if Fraction(w)>0]
    # Reconstruct the selected columns from the immutable source data again.
    rebuilt=[];weights=[];references=[]
    for p,w in kept:
        state,word,_=project(catalog[p['source']],case['mask'],0)
        check=comparison(state,word,p['cut'],labels)
        if check is None or (check['base'],check['gamma'])!=(p['base'],p['gamma']):raise ValueError('profile reconstruction mismatch')
        rebuilt.append(check);weights.append(w);references.append(dict(source=p['source'],cut=p['cut'],weight=w))
    bounds=verify_mixture(rebuilt,weights);literal=[];k=case['blocks']
    for lengths in ([1]*k,[j+1 for j in range(k)],[7 if j%2 else 2 for j in range(k)]):
        chosen=min(range(len(rebuilt)),key=lambda i:rebuilt[i]['base']+sum(g*(ell-1) for g,ell in zip(rebuilt[i]['gamma'],lengths)))
        witness=materialize(rebuilt[chosen],lengths)
        if witness['length']>30+6*sum(lengths):raise ValueError('target exceeded')
        literal.append(dict(lengths=lengths,chosen=chosen,**witness))
    return dict(references=references,bounds=bounds,literal_checks=literal,claim='all positive block lengths, conditional on reviewed comparison/stretching lemmas')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--role',choices=['train','confirmation'],required=True);args=ap.parse_args()
    if not trusted_status()['ok']:raise RuntimeError('trusted mismatch')
    output=P/f'{args.role}-v2-results.json'
    if output.exists():raise FileExistsError(output)
    if args.role=='confirmation' and not (P/'train-v2-results.json').exists():raise RuntimeError('finish training first')
    config=json.loads((P/'config-v2.json').read_text());cases=json.loads((P/f'{args.role}-v2.json').read_text())
    manifest=json.loads((P/'manifest-v2.json').read_text())
    for name,digest in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen file changed: '+name)
    with zipfile.ZipFile(ROOT/'autoresearch/loop-260923-2107/incoming/verification.zip') as z:
        bundle=json.loads(z.read('literature/multiset_nine_gap_complete_certificates_20260924.json'))
        reverse=json.loads(z.read('literature/multiset_reverse_m8_complete_certificates_20260923.json'))
    records={r['order_index']:r for r in bundle['records']};catalog=bundle['catalog'];orders=list(permutations(range(1,9)))
    reverse_by_mask={}
    for f in reverse['families']:reverse_by_mask.setdefault(family_mask(f['base']),[]).append(f)
    start=time.perf_counter();results=[];pool=list(range(len(catalog)))
    random.Random(config['seed']).shuffle(pool);pool=pool[:config['extra_catalog_sources']]
    for case in cases:
        if time.perf_counter()-start>config['max_seconds']:break
        began=time.perf_counter();labels=orders[case['order_index']];record=records[case['order_index']]
        if any(reverse_accepts(f['base'],f['tree'],labels) for f in reverse_by_mask.get(case['mask'],[])):
            raise ValueError('source residual unexpectedly covered by reverse transfer')
        profiles=[];oldweights=[]
        for row in record['mixture']:
            state,word,cut=project(catalog[row['source']],case['mask'],row['cut'])
            p=comparison(state,word,cut,labels)
            if p is None:raise ValueError('inherited comparison premise failed')
            profiles.append(dict(p,source=row['source']));oldweights.append(Fraction(row['weight']))
        if sum(oldweights)!=1:raise ValueError('inherited weights malformed')
        oldbase=sum(w*p['base'] for w,p in zip(oldweights,profiles))
        oldslopes=[sum(w*p['gamma'][j] for w,p in zip(oldweights,profiles)) for j in range(case['blocks'])]
        if oldbase<31+6*case['blocks']:raise ValueError('source residual already meets inherited criterion')
        if max(oldslopes)>6:raise ValueError('projected slopes violate inherited guarantee')
        first=optimize(profiles,config['pivot_limit']);cert=finalize(profiles,first,case,catalog,labels);stage='inherited-support'
        columns=len(profiles);second=None
        if cert is None:
            seen={(p['source'],p['cut']) for p in profiles}
            for source in pool:
                state,word,_=project(catalog[source],case['mask'],0)
                for cut in range(len(state)):
                    if (source,cut) in seen:continue
                    p=comparison(state,word,cut,labels)
                    if p:profiles.append(dict(p,source=source));seen.add((source,cut))
            # Coefficient dominance is safe for every nonnegative excess length.
            nondominated=[]
            for p in sorted(profiles,key=lambda p:(p['base'],sum(p['gamma']),p['source'],p['cut'])):
                vector=[p['base']]+p['gamma']
                if not any(all(a<=b for a,b in zip([q['base']]+q['gamma'],vector)) for q in nondominated):nondominated.append(p)
            profiles=nondominated;columns=len(profiles)
            second=optimize(profiles,config['pivot_limit']);cert=finalize(profiles,second,case,catalog,labels);stage='expanded-pool'
        result=dict(**case,labels=labels,baseline=dict(inherited_base=str(oldbase),threshold=31+6*case['blocks'],reverse_transfer_covered=False),
            stage=stage,columns=columns,inherited_search={k:v for k,v in first.items() if k!='weights'},
            expanded_search=None if second is None else {k:v for k,v in second.items() if k!='weights'},certificate=cert,seconds=time.perf_counter()-began)
        results.append(result)
        print(json.dumps(dict(done=len(results),role=args.role,certified=sum(r['certificate'] is not None for r in results),case=case['id'],stage=stage,seconds=round(result['seconds'],3))),flush=True)
    summary=dict(role=args.role,status='COMPLETE' if len(results)==len(cases) else 'INCOMPLETE',cases=len(results),planned=len(cases),
        certified=sum(r['certificate'] is not None for r in results),api_cost_usd=0,seconds=time.perf_counter()-start,results=results,
        scope='Additional certificates relative to checked inherited-weight and supplied reverse-transfer methods on selected source-reported residual cases; global coverage counts not reconstructed.')
    output.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='results'}))

if __name__=='__main__':main()
