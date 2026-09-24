#!/usr/bin/env python3
"""Independent literal checks; no ranking, dependencies, or large BFS."""
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def step(v, a):
    if a == 'L': return v[1:] + v[:1]
    if a == 'R': return v[-1:] + v[:-1]
    return (v[1], v[0]) + v[2:]

def delete(v):
    return tuple(x for x in v if x != -1)

def pair_step(u, j, a):
    n = len(u) + 1
    if a == 'L': return (u, n-1) if j == 0 else (step(u,a), j-1)
    if a == 'R': return (u, 0) if j == n-1 else (step(u,a), j+1)
    return (u,1-j) if j < 2 else (step(u,a),j)

def run(v, word):
    for a in word: v = step(v,a)
    return v

def ball(v, radius):
    seen = {v}; front = {v}
    for _ in range(radius):
        front = {step(w,a) for w in front for a in 'LRX'} - seen
        seen |= front
        assert len(seen) < 100000
    return seen

def main():
    checks = 0
    for n in range(4,8):
        for v in set(itertools.permutations((-1,0)+tuple(range(1,n-1)))):
            for a in 'LRX':
                w = step(v,a)
                assert pair_step(delete(v),v.index(-1),a) == (delete(w),w.index(-1))
                checks += 1
    family = []; letters = 0
    for k in range(2,101):
        for m in (8*k-1,8*k,9*k):
            v = tuple(range(1,k+1))+(0,)+tuple(range(k+1,m-k+2))+(0,)+tuple(range(m-k+2,m+1))
            word = 'L'*(k-1)+'X'+'RX'*(k-1)+'R'*k+'X'+'LX'*(k-2)+'LLL'
            target = tuple(range(1,m+1))+(0,0)
            assert len(word)==6*k-2 and run(v,word)==target
            projections=[]
            for j in (k,m+2-k):
                w=v[:j]+(-1,)+v[j+1:]; q=0
                for a in word:
                    z=step(w,a); q += delete(w)!=delete(z); w=z
                    letters+=1
                assert tuple(0 if x==-1 else x for x in w)==target
                assert q==5*k-3
                projections.append(q)
            family.append(dict(k=k,m=m,length=len(word),projections=projections))
    exact=[]
    for k in range(2,6):
        m=8*k-1
        v=tuple(range(1,k+1))+(0,)+tuple(range(k+1,m-k+2))+(0,)+tuple(range(m-k+2,m+1))
        a,b=3*k-2,3*k-1
        bv=ball(v,a); br=ball(tuple(range(1,m+1))+(0,0),b)
        assert not bv & br
        exact.append(dict(k=k,m=m,distance=6*k-2,radii=[a,b],ball_sizes=[len(bv),len(br)]))
    sample=(2,5,1,0,6,7,0,4,3,8)
    word='LXLLXLXLLLLXLXRRXRXRXLLLXLXLXRXRX'
    assert run(sample,word)==tuple(range(1,9))+(0,0)
    report=dict(scope='Finite local transition and family checks, not arbitrary-size proof',transition_checks=checks,family=family,marked_letters=letters,exact_family=exact,source_sample_length=len(word),source_sha256=hashlib.sha256((ROOT/'input/marked-zero-20260923/lrx_multiset_marked_zero_reduction.tex').read_bytes()).hexdigest())
    out=Path(__file__).with_name('proof_replay.json')
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='family'}))

if __name__=='__main__': main()
