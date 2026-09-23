"""Frozen six-order geodesic portfolio, exact routing and trusted replay."""
import itertools
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from integrations.word_lift import lift_fixed_word,left_sweep_lift
from src.lrx.table_bfs import DistanceTable
OUT=Path(__file__).resolve().parent
ORDERS=list(itertools.permutations('LRX'))


def move(u,c):
    return u[1:]+u[:1] if c=='L' else u[-1:]+u[:-1] if c=='R' else (u[1],u[0])+u[2:]


def geodesic(table,u,order):
    w=u;d=table.distance(w);letters=[]
    while d:
        for c in order:
            v=move(w,c)
            if table.distance(v)==d-1:
                letters.append(c);w=v;d-=1;break
        else: raise AssertionError('complete table has no descending neighbour')
    return ''.join(letters)


def run(name,m,r,vectors,q,bound,path):
    out=OUT/(name+'.json')
    if out.exists(): raise RuntimeError('refusing overwrite')
    table=DistanceTable(path,m,r-1)
    cache={};rows=[]
    start=time.perf_counter()
    for v in vectors:
        v=tuple(v);candidates=[]
        for j,x in enumerate(v):
            if x: continue
            u=v[:j]+v[j+1:]
            if u not in cache:
                cache[u]=[(order,geodesic(table,u,order)) for order in ORDERS]
            seen=set()
            for order,word in cache[u]:
                if word in seen or len(word)>q: continue
                seen.add(word)
                result=lift_fixed_word(m,r,u,j,word)
                result.update(j=j,order=''.join(order))
                if 'R' not in word:
                    result['left_sweep']=left_sweep_lift(m,r,u,j,word)
                candidates.append(result)
        finite=[a for a in candidates if a['length'] is not None]
        best=min(finite,key=lambda a:a['length']) if finite else None
        positive=best is not None and best['length']<=bound
        rows.append(dict(v=v,within_bound=positive,best=best,candidates=candidates))
        print(name,len(rows),positive,best['length'] if best else None,flush=True)
    data=dict(m=m,r=r,q=q,bound=bound,orders=[''.join(o) for o in ORDERS],
         smaller_radius=table.radius,seconds=time.perf_counter()-start,
         positive=sum(a['within_bound'] for a in rows),total=len(rows),rows=rows,
         failure_semantics='Portfolio miss only; never a negative for A_q or the conjecture')
    out.write_text(json.dumps(data,indent=2)+'\n')
    return data

if __name__=='__main__':
    old=ROOT/'autoresearch/loop-260923-2004'
    run('m8r5-geodesics',8,5,json.loads((old/'m8r5-frozen.json').read_text())['vectors'],55,60,ROOT/'datasets/generated')
    run('m8r9-geodesics',8,9,json.loads((old/'frozen-cases.json').read_text())['vectors'],79,84,ROOT/'runs/bfs-crosscheck-260923/tables')
    for m,p,v in [(8,42,(2,1,0,0,0,7,8,6,5,4,3)),(9,52,(2,1,0,0,0,9,8,7,6,5,4,3))]:
        data=run(f'm{m}r3-control',m,3,[v],p,p+m-2,ROOT/'datasets/generated')
        assert data['positive']==0, 'known exact obstruction contradicted'
