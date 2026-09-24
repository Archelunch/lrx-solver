#!/usr/bin/env python3
"""Small per-mark exhaustive recurrence audit against resource BFS; stdlib."""
from collections import deque
from pathlib import Path
import json
from proof_replay import step,delete
from independent_check import bfs,unmark

def audit(m,r):
    root=tuple(range(1,m+1))+(0,)*r
    D=bfs(root); ordered=sorted(D,key=D.get)
    layers=[{}, {}, {}]; marked=[]; edges={}; transition_count=0
    n=m+r; mask=(1<<(4*n))-1
    for v in ordered:
        pos=[j for j,x in enumerate(v) if x==0]
        packed=0
        for x in v: packed=(packed<<4)|x
        diff=((packed>>(4*(n-1)))^(packed>>(4*(n-2))))&15
        packed_moves=(((packed<<4)&mask)|(packed>>(4*(n-1))), (packed>>4)|((packed&15)<<(4*(n-1))), packed^(diff<<(4*(n-1)))^(diff<<(4*(n-2))))
        for op,a in enumerate('LRX'):
            lit=step(v,a); val=0
            for x in lit: val=(val<<4)|x
            assert packed_moves[op]==val
        for slot,j in enumerate(pos):
            s=v[:j]+(-1,)+v[j+1:]; marked.append(s); ee=[]
            for op,a in enumerate('LRX'):
                t=step(s,a); to=unmark(t); cost=int(delete(s)!=delete(t))
                next_slot=slot; predicted=1
                if op==0:
                    if v[0]==0: next_slot=(slot+r-1)%r
                    predicted=int(j!=0)
                if op==1:
                    if v[-1]==0: next_slot=(slot+1)%r
                    predicted=int(j!=n-1)
                if op==2:
                    if v[0]==v[1]==0 and slot<2: next_slot=1-slot
                    predicted=int(not(j<2 or v[0]==v[1]==0))
                positions=[i for i,x in enumerate(to) if x==0]
                assert positions[next_slot]==t.index(-1) and predicted==cost
                c=1+D[to]-D[v]; assert 0<=c<=2
                ee.append((t,c,cost)); transition_count+=1
            edges[s]=ee
    for e in range(3):
        for s in marked:
            val=0 if unmark(s)==root else 999
            if e: val=min(val,layers[e-1][s])
            for t,c,cost in edges[s]:
                if c<=e: val=min(val,layers[e-c][t]+cost)
            layers[e][s]=val
    cap=max(D.values())+2
    queue=deque(); distances={}; actual=[{}, {}, {}]
    for j in range(m,m+r):
        s=root[:j]+(-1,)+root[j+1:]
        distances[s,0]=0; queue.append((s,0))
    while queue:
        s,q=queue.popleft(); l=distances[s,q]
        for e in range(max(0,l-D[unmark(s)]),3): actual[e][s]=min(actual[e].get(s,999),q)
        if l==cap: continue
        for a in 'LRX':
            t=step(s,a); qp=q+int(delete(t)!=delete(s)); key=(t,qp)
            if key not in distances:
                distances[key]=l+1; queue.append(key)
    assert actual==layers
    return dict(m=m,r=r,visible_states=len(D),marked_states=len(marked),per_mark_cells_checked=3*len(marked),transitions_checked=transition_count,resource_states=len(distances))

if __name__=='__main__':
    rows=[audit(m,n-m) for n in range(4,8) for m in range(2,n-1)]
    out={'scope':'Small exhaustive per-mark equality; Python translation of source formulas, not execution of C++ binary','cases':rows,'compiler_limitation':'g++ unavailable on proof node (exit127); no software installed and no large BFS repeated'}
    Path(__file__).with_name('proof_full_slack_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))
