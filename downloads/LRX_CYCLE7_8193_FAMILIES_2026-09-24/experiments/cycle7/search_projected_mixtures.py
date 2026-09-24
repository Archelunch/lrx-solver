#!/usr/bin/env python3
"""Discovery only: materialize peer comparison words, project, then reoptimize."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import linprog

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'sources/2026-09-24-nine-gap/extracted'
sys.path.insert(0,str(SOURCE/'scripts'))
from audit_multiset_nine_gap_cover import compare_word, state_for
from multiset_zero_projection import project_deleting_zeros
from multiset_zero_stretch import cancel_rotations, remove_zero_swaps


def profile(state,word):
    zero=0;atoms=[]
    for x in state:
        if x: atoms.append(x)
        else: zero+=1;atoms.append(-zero)
    r=zero;swaps=[0]*r;gaps=[];c=0;a=[0]*r;xs=0
    for letter in word:
        if letter=='L':
            c+=1
            if atoms[0]<0:a[-atoms[0]-1]+=1
            atoms=atoms[1:]+atoms[:1]
        elif letter=='R':
            c-=1
            if atoms[-1]<0:a[-atoms[-1]-1]-=1
            atoms=atoms[-1:]+atoms[:-1]
        else:
            assert letter=='X' and not(atoms[0]<0 and atoms[1]<0)
            xs+=1; tail=[0]*r
            if atoms[0]<0:
                j=-atoms[0]-1;swaps[j]+=1;a[j]+=1
            elif atoms[1]<0:
                j=-atoms[1]-1;swaps[j]+=1;tail[j]-=1
            gaps.append([c,a]);c,a=0,tail
            atoms[0],atoms[1]=atoms[1],atoms[0]
    gaps.append([c,a])
    assert [max(0,x) for x in atoms]==list(range(1,9))+[0]*r
    return {'base_cost':xs+sum(abs(c) for c,a in gaps),
            'beta':[2*swaps[j]+sum(abs(a[j]) for c,a in gaps) for j in range(r)],
            'mixed_gaps':sum(not((c>=0 and all(v>=0 for v in a)) or (c<=0 and all(v<=0 for v in a))) for c,a in gaps)}


def exact_weights(rows,weights,k):
    ids=[i for i,w in enumerate(weights) if w>1e-8]
    if not ids:return None
    w=[Fraction(float(weights[i])).limit_denominator(10**6) for i in ids]
    total=sum(w);w=[x/total for x in w]
    base=sum(x*rows[i]['base_cost'] for i,x in zip(ids,w))
    beta=[sum(x*rows[i]['beta'][j] for i,x in zip(ids,w)) for j in range(k)]
    if base>=31+6*k or any(x>6 for x in beta):return None
    return [dict(rows[i],weight=str(x)) for i,x in zip(ids,w)],str(base),list(map(str,beta))


def main():
    p=argparse.ArgumentParser();p.add_argument('--per-k',type=int,default=20)
    p.add_argument('--blocks',type=int,nargs='+',default=[8,7,6,5,4],choices=range(4,9))
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    start=time.monotonic()
    src=SOURCE/'literature/multiset_nine_gap_complete_certificates_20260924.json'
    table=SOURCE/'literature/multiset_nine_gap_projection_search_20260924.npz'
    bundle=json.loads(src.read_text());coverage=np.load(table)['union_covered']
    catalog=bundle['catalog'];cases=[];attempts=[];cache={}
    for k in args.blocks:
        masks=[m for m in range(1,512) if m.bit_count()==k]
        ii,jj=np.where(~coverage[:,masks])
        for index,j in list(zip(ii,jj))[:args.per_k]:
            index=int(index);mask=masks[j];record=bundle['records'][index]
            full=state_for(record['labels']);dead=[z for z in range(9) if not(mask>>z&1)]
            rows=[];seen=set();state=None
            for old in record['mixture']:
                key=(index,old['source'],old['cut'])
                if key not in cache:cache[key]=compare_word(full,catalog[old['source']]['word'],old['cut'])
                state,word=project_deleting_zeros(full,cache[key],dead,check_every_step=True)
                word=cancel_rotations(remove_zero_swaps(state,word))
                if word in seen:continue
                seen.add(word);q=profile(state,word)
                rows.append(dict(word=word,source=old['source'],cut=old['cut'],**q))
            answer=linprog([x['base_cost'] for x in rows],
                A_ub=np.asarray([x['beta'] for x in rows]).T,b_ub=[6]*k,
                A_eq=np.ones((1,len(rows))),b_eq=[1],bounds=(0,None),method='highs')
            exact=exact_weights(rows,answer.x,k) if answer.success else None
            attempt={'order_index':index,'mask':mask,'k':k,'columns':len(rows),'solver_status':int(answer.status),
                     'lp_base':float(answer.fun) if answer.success else None,'certified':exact is not None}
            attempts.append(attempt)
            if exact:
                chosen,base,beta=exact
                cases.append({'order_index':index,'labels':record['labels'],'mask':mask,'base_state':list(state),
                    'prior_union_covered':False,'target_base':30+6*k,'rows':chosen,'mean_base':base,'mean_beta':beta})
                print(json.dumps({'found':len(cases),**attempt,'exact_base':base}),flush=True)
    result={'format':'lrx_cycle7_explicit_mixtures_v1','status':'DISCOVERY_REQUIRES_INDEPENDENT_AUDIT',
            'source_bundle_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
            'source_coverage_sha256':hashlib.sha256(table.read_bytes()).hexdigest(),
            'cases':cases,'attempts':attempts,'seconds':time.monotonic()-start}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'attempted':len(attempts),'found':len(cases),'seconds':result['seconds']}),flush=True)


if __name__=='__main__':main()
