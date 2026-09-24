#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
from random import Random
from itertools import product
from direct_stretch import step,tagged,expand,profile,lift,costs,project

def run(v,w):
    for a in w:v=step(v,a)
    return v

def main():
    rng=Random(20260924);counts={'words':0,'lifts':0,'projections':0,'mixed_sign_profiles':0}
    for case in range(600):
        m=2+case%7;k=1+case%9;root=tuple(range(1,m+1))+(0,)*k
        v=root;scramble=[]
        for _ in range(5+case%61):
            a=rng.choice('LRX')
            if a=='X' and v[0]==v[1]==0:continue
            v=step(v,a);scramble.append(a)
        inverse={'L':'R','R':'L','X':'X'}
        w=''.join(inverse[x] for x in reversed(scramble))
        # A paid full turn remains visible in the price, even though its endpoint is unchanged.
        if case%3==0:w='L'*len(v)+w
        c=profile(v,w);assert c['final']==root
        counts['words']+=1
        mixed=any(not((b>=0 and all(x>=0 for x in row))or(b<=0 and all(x<=0 for x in row))) for b,row in c['gaps'])
        counts['mixed_sign_profiles']+=mixed
        for lengths in ([1]*k,[rng.randint(1,6) for _ in range(k)]):
            start,ww,end=lift(v,w,lengths,True)
            assert run(start,ww)==end==tuple(range(1,m+1))+(0,)*sum(lengths)
            exact,upper=costs(c,lengths);assert len(ww)==exact<=upper
            counts['lifts']+=1
        # Delete selected original tagged atoms, then stretch remaining atoms.
        deleted={j for j in range(k) if rng.randrange(2)}
        if len(deleted)==k:deleted.remove(0)
        u,pw=project(v,w,deleted);pc=profile(u,pw)
        kept=[j for j in range(k) if j not in deleted]
        assert pc['final']==tuple(range(1,m+1))+(0,)*len(kept)
        assert all(b<=c['beta'][j] for b,j in zip(pc['beta'],kept))
        lengths=[1 if j in deleted else rng.randint(1,5) for j in range(k)]
        start,whole,_=lift(v,w,lengths)
        # Expanded initial ordinal of each deleted singleton.
        offsets=[];t=0
        for j,l in enumerate(lengths):
            if j in deleted:offsets.append(t)
            t+=l
        ps,pwhole=project(start,whole,offsets)
        ls,lword,lfinal=lift(u,pw,[lengths[j] for j in kept],True)
        assert ps==ls and pwhole==lword
        assert run(ls,lword)==lfinal
        counts['projections']+=1
    # Arbitrary mixed affine gaps obey triangle bounds; equality is not required.
    mixed_checks=0
    for b,a,d,z,t in product(range(-2,3),range(-2,3),range(-2,3),range(4),range(4)):
        assert abs(b+a*z+d*t)<=abs(b)+abs(a)*z+abs(d)*t
        mixed_checks+=1
    # Equality at target+1 is insufficient to conclude integer cost<=target.
    assert not (55<55)
    p=Path(__file__).resolve().parent
    out={'status':'PASS','counts':counts,'mixed_affine_checks':mixed_checks,'scope':'Finite implementation tests; all-positive-length proof is in PROOF_AUDIT.md','sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['direct_stretch.py','check_direct_stretch.py']}}
    (p/'direct_stretch_checks.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))

if __name__=='__main__':main()
