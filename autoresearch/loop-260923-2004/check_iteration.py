"""Reproducible local session-05 checks; never calls a provider."""
import importlib.util
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from autoresearch.lift_forward import decide_vector
from integrations.zero_erasure import count_projections
from src.lrx.certificates import CertificateValidator
from src.lrx.table_bfs import DistanceTable
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('before', OUT / 'lift_forward_before.py')
before = importlib.util.module_from_spec(spec)
spec.loader.exec_module(before)

def save(name, data):
    path = OUT / name
    if path.exists():
        raise RuntimeError(f'refusing overwrite: {path}')
    path.write_text(json.dumps(data, indent=2) + '\n')

bench = []
for m, v, p in [(8, (2,1,0,0,0,7,8,6,5,4,3),42),
                 (9, (2,1,0,0,0,9,8,7,6,5,4,3),52)]:
    table = DistanceTable(ROOT / 'datasets/generated', m, 2)
    for q in (p,p+1):
        bound=p+m-2
        rows=[]
        for name, fn in [('before',before.decide_vector),('after',decide_vector),
                         ('after',decide_vector),('before',before.decide_vector)]:
            start=time.perf_counter()
            result=fn(m,3,v,q,bound,table.dist,max_states=200000)
            rows.append(dict(engine=name,seconds=time.perf_counter()-start,result=result))
        assert all(x['result']['within_bound']==rows[0]['result']['within_bound'] for x in rows)
        assert all(x['result']['status']=='COMPLETE' for x in rows)
        bench.append(dict(m=m,r=3,v=v,q=q,bound=bound,rows=rows))
save('pruning-benchmark.json',bench)
print('benchmark complete', flush=True)

# All insertion positions of every smaller antipode, deduplicated. Freeze
# 24 evenly spaced lexicographic states before evaluating any of them.
table=DistanceTable(ROOT / 'runs/bfs-crosscheck-260923/tables',8,8)
antipodes=table.states_at(table.radius)
universe=sorted({v[:j]+(0,)+v[j:] for v in antipodes for j in range(17)})
selected=[universe[i*(len(universe)-1)//23] for i in range(24)]
save('frozen-cases.json',dict(m=8,r=9,q=79,bound=84,smaller_radius=table.radius,
     antipodes=len(antipodes),universe_size=len(universe),vectors=selected,
     state_cap_per_deletion=100000,wall_cap_between_vectors=300))
start=time.perf_counter()
results=[]
for i,v in enumerate(selected):
    if time.perf_counter()-start>300:
        break
    t=time.perf_counter()
    result=decide_vector(8,9,v,79,84,table.dist,max_states=100000)
    if result['within_bound']:
        word=result['witness']['word']
        counts=count_projections(v,8,9,word)
        validator=CertificateValidator(8,9)
        for deletion in counts['deletions']:
            j=deletion['j']
            cert=validator.replay_word(word,start_state=(v[:j]+v[j+1:],j))
            assert cert.terminal and cert.replay_valid
            assert cert.projection_length==deletion['projection_length']
        result['all_zero_counts']=counts
    row=dict(v=v,seconds=time.perf_counter()-t,result=result)
    results.append(row)
    with (OUT/'target-checks.jsonl').open('a') as f:
        f.write(json.dumps(row)+'\n')
    print(i+1,result['status'],result['within_bound'],round(row['seconds'],3),flush=True)
    if result['within_bound'] is False:
        print('STOP: new negative needs independent audit and human decision',flush=True)
        break
save('target-summary.json',dict(attempted=len(results),selected=len(selected),
    positive=sum(x['result']['within_bound'] is True for x in results),
    negative=sum(x['result']['within_bound'] is False for x in results),
    incomplete=sum(x['result']['within_bound'] is None for x in results),
    seconds=time.perf_counter()-start))
