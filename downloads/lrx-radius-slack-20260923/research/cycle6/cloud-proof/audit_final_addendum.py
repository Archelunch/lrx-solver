#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
from proof_replay import step,delete,ball

p=Path(__file__).resolve().parent
d=json.loads((p/'packed-m8-r4-witnesses.json').read_text())
checks=[]
for s in d['exceptional_states']:
    v=tuple(s['v']); marks=[j for j,x in enumerate(v) if not x]
    for l in s['layers']:
        projections=[]
        for j in marks:
            t=v[:j]+(-1,)+v[j+1:]; q=0
            for a in l['word']:
                u=step(t,a);q+=delete(t)!=delete(u);t=u
            assert tuple(0 if x==-1 else x for x in t)==tuple(range(1,9))+(0,)*4
            projections.append(q)
        assert len(l['word'])==l['word_length']<=s['distance']+l['extra_full_steps']
        assert projections[marks.index(l['marked_index'])]==l['minimum_projection']
        assert all(q>=minimum for q,minimum in zip(projections,l['minimum_projection_per_mark']))
        checks.append({'v':list(v),'length':len(l['word']),'projections':projections})
assert sum(d['layers'][0]['histogram'].values())==d['full_states']==19958400
assert d['P']==48 and d['full_radius']==54
z=next(s for s in d['exceptional_states'] if s['v']==[4,1,2,3,0,0,0,0,6,7,8,5])
assert z['distance']==50 and z['layers'][0]['minimum_projection_per_mark']==[50]*4
balls=[]
for k,expected in zip(range(2,6),[(42,94),(307,682),(1989,4405),(11990,26536)]):
    m=8*k-1; root=tuple(range(1,m+1))+(0,0)
    v=tuple(range(1,k+1))+(0,)+tuple(range(k+1,m-k+2))+(0,)+tuple(range(m-k+2,m+1))
    br=ball(root,3*k-2);bv=ball(v,3*k-1)
    assert (len(br),len(bv))==expected and not br&bv
    balls.append({'k':k,'root_radius':3*k-2,'v_radius':3*k-1,'sizes':[len(br),len(bv)],'disjoint':True})
out={'m8r4_marked_replays':4*len(checks),'m8r4_words':checks,'source_ball_order_corrected':balls,'provenance_note':'Supplied packed_budget_check.cpp caps exceptional_states at20; m8r4 JSON contains59. Exact source variant for extended witness export needs inclusion in coordinator package. Central m8r3 contains5 and is unaffected.','sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['packed-m8-r4-witnesses.json','packed_budget_check.cpp','RESULTS.md','COORDINATOR_REVIEW.md']}}
(p/'proof_final_addendum.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'replays':out['m8r4_marked_replays'],'source_balls':balls,'provenance_note':out['provenance_note']}))
