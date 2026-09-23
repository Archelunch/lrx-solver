"""Complete frozen antipode-insertion family, with bounded per-mark work."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from autoresearch.lift_forward import decide_vector
from src.lrx.table_bfs import DistanceTable
from src.lrx.certificates import CertificateValidator
from integrations.zero_erasure import count_projections
OUT=Path(__file__).resolve().parent
path=OUT/'m8r5-checks.jsonl'
if path.exists(): raise RuntimeError('refusing overwrite')
table=DistanceTable(ROOT/'datasets/generated',8,4)
anti=table.states_at(table.radius)
vectors=sorted({v[:j]+(0,)+v[j:] for v in anti for j in range(13)})
(OUT/'m8r5-frozen.json').write_text(json.dumps(dict(m=8,r=5,q=55,bound=60,
    smaller_radius=table.radius,antipodes=len(anti),vectors=vectors),indent=2)+'\n')
start=time.perf_counter()
counts={'positive':0,'negative':0,'incomplete':0}
for i,v in enumerate(vectors):
    t=time.perf_counter()
    result=decide_vector(8,5,v,55,60,table.dist,max_states=100000)
    if result['within_bound']:
        word=result['witness']['word']
        counted=count_projections(v,8,5,word)
        for row in counted['deletions']:
            j=row['j']
            cert=CertificateValidator(8,5).replay_word(word,start_state=(v[:j]+v[j+1:],j))
            assert cert.terminal and cert.replay_valid and cert.projection_length==row['projection_length']
        result['all_zero_counts']=counted
    key='positive' if result['within_bound'] is True else 'negative' if result['within_bound'] is False else 'incomplete'
    counts[key]+=1
    with path.open('a') as f: f.write(json.dumps(dict(v=v,result=result,seconds=time.perf_counter()-t))+'\n')
    print(i+1,len(vectors),key,round(time.perf_counter()-t,3),flush=True)
    if key=='negative': break
(OUT/'m8r5-summary.json').write_text(json.dumps(dict(counts,seconds=time.perf_counter()-start,total=len(vectors)),indent=2)+'\n')
