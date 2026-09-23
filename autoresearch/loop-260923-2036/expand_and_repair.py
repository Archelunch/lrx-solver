"""Expand the finite family; test a precisely restricted one-defect repair."""
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('portfolio',OUT/'route_portfolio.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
from integrations.word_lift import lift_fixed_word
from src.lrx.table_bfs import DistanceTable


def repair(m,pp,v):
    path=OUT/f'm{m}r3-repair.json'
    if path.exists(): raise RuntimeError('refusing overwrite')
    table=DistanceTable(ROOT/'datasets/generated',m,2)
    q=pp+1;bound=pp+m-2
    candidates=[];cache={};start=time.perf_counter()
    def geodesic(u,order):
        key=(u,order)
        if key not in cache: cache[key]=p.geodesic(table,u,order)
        return cache[key]
    best=None;tested=0;found=False
    # Stop at the first certified fit; otherwise this is only a portfolio miss.
    for j,x in enumerate(v):
        if x: continue
        u=v[:j]+v[j+1:];seen=set()
        for prefix_order in p.ORDERS:
            base=geodesic(u,prefix_order)
            w=u;prefix=''
            for i in range(len(base)+1):
                d=table.distance(w)
                for c in 'LRX':
                    w2=p.move(w,c);d2=table.distance(w2)
                    if w2==w or d2<d or i+1+d2>q: continue
                    for suffix_order in p.ORDERS:
                        word=prefix+c+geodesic(w2,suffix_order)
                        if word in seen: continue
                        seen.add(word);tested+=1
                        result=lift_fixed_word(m,3,u,j,word)
                        if result['length'] is not None and (best is None or result['length']<best['length']):
                            best=dict(result,j=j,defect_index=i,defect_letter=c,
                                 distance_before=d,distance_after=d2,
                                 defect_vector=w,prefix_order=''.join(prefix_order),
                                 suffix_order=''.join(suffix_order),d_initial=table.distance(u))
                            candidates.append(best)
                        if best and best['length']<=bound:
                            found=True;break
                    if found: break
                if found: break
                if i<len(base):
                    prefix+=base[i];w=p.move(w,base[i])
            if found: break
        if found: break
    data=dict(m=m,r=3,v=v,q=q,bound=bound,within_bound=found,
              tested=tested,seconds=time.perf_counter()-start,best=best,improvements=candidates,
              failure_semantics='Only the one-defect six-order construction is tested')
    path.write_text(json.dumps(data,indent=2)+'\n')
    print('repair',m,found,tested,data['seconds'],flush=True)

repair(8,42,(2,1,0,0,0,7,8,6,5,4,3))
repair(9,52,(2,1,0,0,0,9,8,7,6,5,4,3))
table=DistanceTable(ROOT/'runs/bfs-crosscheck-260923/tables',8,8)
vectors=sorted({v[:j]+(0,)+v[j:] for v in table.states_at(77) for j in range(17)})
(OUT/'m8r9-all-frozen.json').write_text(json.dumps(dict(m=8,r=9,q=79,bound=84,vectors=vectors),indent=2)+'\n')
del table
p.run('m8r9-all-geodesics',8,9,vectors,79,84,ROOT/'runs/bfs-crosscheck-260923/tables')
