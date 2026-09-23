"""Inspect the certified successful smaller path for the known m8 obstruction."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from autoresearch.lift_forward import decide_vector
from src.lrx.table_bfs import DistanceTable
from src.lrx.certificates import CertificateValidator
p=Path(__file__).resolve().parent
path=p/'m8r3-exact-profile.json'
if path.exists(): raise RuntimeError('refusing overwrite')
v=(2,1,0,0,0,7,8,6,5,4,3);table=DistanceTable(ROOT/'datasets/generated',8,2)
a=decide_vector(8,3,v,43,48,table.dist,max_states=200000)
assert a['within_bound']
b=a['witness'];j=b['j'];u=v[:j]+v[j+1:]
c=CertificateValidator(8,3).replay_word(b['word'],start_state=(u,j))
w=u;events=[]
for i,letter in enumerate(c.projection_sequence):
 w2=w[1:]+w[:1] if letter=='L' else w[-1:]+w[:-1] if letter=='R' else (w[1],w[0])+w[2:]
 d=table.distance(w);d2=table.distance(w2)
 if d2>=d: events.append(dict(index=i,letter=letter,before=w,after=w2,d_before=d,d_after=d2))
 w=w2
path.write_text(json.dumps(dict(result=a,projection_word=c.projection_sequence,defects=events),indent=2)+'\n')
print(json.dumps(dict(length=b['H'],projection=len(c.projection_sequence),defects=events)))
