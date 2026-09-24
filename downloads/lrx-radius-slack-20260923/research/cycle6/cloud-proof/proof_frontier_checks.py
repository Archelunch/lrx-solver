#!/usr/bin/env python3
"""Literal erasure accounting, no graph search or coordinator DP."""
import itertools
import json
from pathlib import Path
from proof_replay import step

def project(v, mark):
    return tuple(0 if x<0 else x for x in v if x!=mark)

def check():
    counts={}
    for m,r in [(2,2),(2,3),(3,2)]:
        marks=tuple(range(-r,0)); count=0
        for v in itertools.permutations(tuple(range(1,m+1))+marks):
            for a in 'LRX':
                if a=='X' and v[0]<0 and v[1]<0: continue
                w=step(v,a)
                lost=sum(project(v,z)==project(w,z) for z in marks)
                expected=int((a=='L' and v[0]<0) or (a=='R' and v[-1]<0) or (a=='X' and ((v[0]<0)!=(v[1]<0))))
                assert lost==expected
                count+=1
        counts[f'm={m},r={r}']=count
    arithmetic=0
    for r in range(2,6):
        for losses in itertools.product(range(6),repeat=r):
            for t in range(1,7):
                if sum(losses)>=r*(t-1)+1:
                    assert max(losses)>=t
                arithmetic+=1
    data={'scope':'Finite literal single-step accounting and pigeonhole arithmetic; no BFS or candidate certification','local_checks':counts,'arithmetic_checks':arithmetic,'candidate_status':'reported by coordinator; independent certificate pending'}
    Path(__file__).with_name('proof_frontier_checks.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data))

if __name__=='__main__': check()
