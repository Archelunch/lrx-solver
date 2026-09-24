#!/usr/bin/env python3
"""Independent stdlib-only verifier. Imports neither search nor peer routines.

Uses a fixed physical circle and moving cursor; search rotates tagged arrays.
All-length validity follows from the block-macro lemma in THEOREM_RU.md.
Finite stretched-word tests are additional checks, not its replacement.
"""
import argparse
import ast
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import permutations
import json
from pathlib import Path
from random import Random
import struct
import time
import zipfile


def require(condition,message):
    if not condition:raise ValueError(message)


def read_coverage(path):
    with zipfile.ZipFile(path) as z:
        raw=z.read('union_covered.npy')
    require(raw[:6]==b'\x93NUMPY','NPY magic')
    version=tuple(raw[6:8]);require(version in ((1,0),(2,0)),'NPY version')
    size=2 if version==(1,0) else 4
    hlen=int.from_bytes(raw[8:8+size],'little')
    header=ast.literal_eval(raw[8+size:8+size+hlen].decode('latin1'))
    require(header=={'descr':'|b1','fortran_order':False,'shape':(40320,512)},'coverage array shape/dtype')
    data=raw[8+size+hlen:];require(len(data)==40320*512,'coverage array size')
    return data


def inspect_word(state,word):
    """Derive an affine upper price by symbolic expansion of block macros."""
    require(set(word)<={'L','R','X'},'alphabet')
    n=len(state); k=state.count(0);circle=[];ordinal=0
    for x in state:
        if x:circle.append(('label',x))
        else:circle.append(('zero',ordinal));ordinal+=1
    head=0; pending=[0]*(k+1);gaps=[];inside=[0]*(k+1)
    def step_vector(atom,sign):
        v=[0]*(k+1);v[0]=sign
        if atom[0]=='zero':v[1+atom[1]]=sign
        return v
    def add(v):
        for j,x in enumerate(v):pending[j]+=x
    for letter in word:
        if letter=='L':
            add(step_vector(circle[head],1));head=(head+1)%n
        elif letter=='R':
            head=(head-1)%n;add(step_vector(circle[head],-1))
        else:
            j=(head+1)%n;left,right=circle[head],circle[j]
            require(left[0]!='zero' or right[0]!='zero','X between two zero atoms')
            inside[0]+=1
            if left[0]=='zero':
                pending[1+left[1]]+=1;inside[1+left[1]]+=2
            if right[0]=='zero':inside[1+right[1]]+=2
            gaps.append(tuple(pending));pending=[0]*(k+1)
            if right[0]=='zero':pending[1+right[1]]-=1
            circle[head],circle[j]=right,left
    gaps.append(tuple(pending))
    goal=[circle[(head+j)%n][1] if circle[(head+j)%n][0]=='label' else 0 for j in range(n)]
    require(goal==list(range(1,9))+[0]*k,'unit word does not reach canonical root')
    upper=[inside[j]+sum(abs(g[j]) for g in gaps) for j in range(k+1)]
    return {'base_cost':upper[0],'beta':upper[1:],'inside':inside,'gaps':gaps}


def expanded_check(state,word,lengths,profile):
    """Literal blocks and explicit L/R/X, separate from symbolic cursor code."""
    units=[];start=[];j=0
    for x in state:
        length=1 if x else lengths[j]
        if not x:j+=1
        units.append((x,length));start.extend([x]*length)
    expanded=[]
    def emit(text):
        for c in text:
            if expanded and expanded[-1]+c in ('LR','RL'):expanded.pop()
            else:expanded.append(c)
    for c in word:
        if c=='L':emit('L'*units[0][1]);units=units[1:]+units[:1]
        elif c=='R':emit('R'*units[-1][1]);units=units[-1:]+units[:-1]
        else:
            if units[0][0]==0:
                q=units[0][1]-1;emit('L'*q+'X'+'RX'*q)
            elif units[1][0]==0:
                q=units[1][1]-1;emit('X'+'LX'*q+'R'*q)
            else:emit('X')
            units[0],units[1]=units[1],units[0]
    actual=start[:]
    for c in expanded:
        if c=='X':actual[0],actual[1]=actual[1],actual[0]
        elif c=='L':actual=actual[1:]+actual[:1]
        else:actual=actual[-1:]+actual[:-1]
    require(actual==list(range(1,9))+[0]*sum(lengths),'expanded word wrong endpoint')
    z=[l-1 for l in lengths]
    exact=profile['inside'][0]+sum(a*b for a,b in zip(profile['inside'][1:],z))
    exact+=sum(abs(g[0]+sum(a*b for a,b in zip(g[1:],z))) for g in profile['gaps'])
    upper=profile['base_cost']+sum(a*b for a,b in zip(profile['beta'],z))
    require(len(expanded)==exact<=upper,'expanded price/upper formula mismatch')
    return len(expanded)


def verify_case(case,coverage,orders,expand=False):
    index,mask=case['order_index'],case['mask']
    require(type(index)==int and 0<=index<40320,'order index')
    require(type(mask)==int and 0<mask<512 and 4<=mask.bit_count()<=8,'mask')
    require(coverage[index*512+mask]==0,'family was already in peer coverage')
    labels=orders[index];require(list(labels)==case['labels'],'label order')
    state=[]
    for j in range(9):
        if mask>>j&1:state.append(0)
        if j<8:state.append(labels[j])
    require(state==case['base_state'],'state/mask mismatch')
    k=state.count(0);target=30+6*k
    require(case['target_base']==target,'target base')
    rows=case['rows'];require(0<len(rows)<=50,'row count')
    weights=[Fraction(row['weight']) for row in rows]
    require(all(x>0 for x in weights) and sum(weights)==1,'weights')
    profiles=[]
    for row in rows:
        profile=inspect_word(state,row['word']);profiles.append(profile)
        require(profile['base_cost']==row['base_cost'] and profile['beta']==row['beta'],'declared word price mismatch')
        mixed=sum(not(all(v>=0 for v in g) or all(v<=0 for v in g)) for g in profile['gaps'])
        require(mixed==row['mixed_gaps'],'declared gap signs mismatch')
    base=sum(w*p['base_cost'] for w,p in zip(weights,profiles))
    slopes=[sum(w*p['beta'][j] for w,p in zip(weights,profiles)) for j in range(k)]
    require(base<target+1 and max(slopes)<=6,'all-length certificate inequality')
    require(str(base)==case['mean_base'] and list(map(str,slopes))==case['mean_beta'],'declared means mismatch')
    replays=0
    if expand:
        rng=Random(20260924+index*512+mask)
        vectors=[[1]*k,[2]*k,[7]*k]+[[1 if j!=i else 9 for j in range(k)] for i in range(k)]
        vectors += [[rng.randrange(1,9) for _ in range(k)] for _ in range(5)]
        for lengths in vectors:
            prices=[expanded_check(state,row['word'],lengths,p) for row,p in zip(rows,profiles)]
            require(min(prices)<=30+6*sum(lengths),'expanded minimum exceeds target')
            replays+=len(rows)
    return {'k':k,'rows':len(rows),'letters':sum(len(r['word']) for r in rows),'replays':replays}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('certificate',type=Path)
    parser.add_argument('--coverage',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();require(not args.output.exists(),'refuse report overwrite');start=time.monotonic()
    bundle=json.loads(args.certificate.read_text())
    require(hashlib.sha256(args.coverage.read_bytes()).hexdigest()==bundle['source_coverage_sha256'],'coverage hash')
    coverage=read_coverage(args.coverage);orders=list(permutations(range(1,9)))
    counts=Counter();by_k=Counter();seen=set()
    for i,case in enumerate(bundle['cases']):
        key=case['order_index'],case['mask'];require(key not in seen,'duplicate family');seen.add(key)
        q=verify_case(case,coverage,orders,expand=i<30 or i%257==0)
        for name in ('rows','letters','replays'):counts[name]+=q[name]
        by_k[q['k']]+=1
    require(seen,'empty certificate')
    original=bundle['cases'][0]
    for kind in ('weight','slope','word'):
        bad=json.loads(json.dumps(original))
        if kind=='weight':bad['rows'][0]['weight']=str(Fraction(bad['rows'][0]['weight'])+1)
        elif kind=='slope':bad['rows'][0]['beta'][0]-=1
        else:bad['rows'][0]['word']='?'+bad['rows'][0]['word'][1:]
        try:verify_case(bad,coverage,orders)
        except ValueError:counts['negative_controls_rejected']+=1
        else:raise ValueError('corrupted certificate accepted')
    report={'status':'PASS','families':len(seen),'by_blocks':dict(by_k),'counts':dict(counts),
        'checks':'all base words and exact rational inequalities; sampled expanded words; mathematical block-macro lemma required',
        'full_m8_proved':False,'full_conjecture_proved':False,'human_reviewed':False,
        'certificate_sha256':hashlib.sha256(args.certificate.read_bytes()).hexdigest(),
        'coverage_sha256':bundle['source_coverage_sha256'],
        'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seconds':time.monotonic()-start}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
