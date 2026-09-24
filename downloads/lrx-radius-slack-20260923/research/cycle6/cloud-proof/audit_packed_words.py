#!/usr/bin/env python3
"""Proof branch: literal replay for ALL marks, JSON consistency and provenance."""
import hashlib
import json
import math
from pathlib import Path
from proof_replay import step,delete

def main():
    p=Path(__file__).resolve().parent
    packed=json.loads((p/'packed-m8-r3.json').read_text())
    exact=json.loads((p/'exact-m8-r3.json').read_text())
    assert packed['P']==exact['P']==42
    assert packed['full_radius']==exact['full_radius']==48
    assert packed['full_states']==exact['visible_states']==math.factorial(11)//math.factorial(3)
    assert packed['smaller_states']==exact['small_states']==math.factorial(10)//math.factorial(2)
    assert sum(exact['histogram'].values())==packed['full_states']
    assert sum(exact['gap_histogram'].values())==packed['full_states']
    for layer in packed['layers']:
        assert sum(layer['histogram'].values())==packed['full_states']
        assert sum(v for k,v in layer['histogram'].items() if int(k)>42)==layer['over_P']
    assert [x['over_P'] for x in packed['layers']]==[5,1,0]
    records=[]
    for s in packed['exceptional_states']:
        v=tuple(s['v']); marks=[j for j,x in enumerate(v) if x==0]
        for layer in s['layers']:
            qs=[]
            for j in marks:
                w=v[:j]+(-1,)+v[j+1:]; q=0
                for a in layer['word']:
                    nxt=step(w,a); q+=delete(nxt)!=delete(w); w=nxt
                assert tuple(0 if x==-1 else x for x in w)==tuple(range(1,9))+(0,0,0)
                qs.append(q)
            assert len(layer['word'])==layer['word_length']<=s['distance']+layer['extra_full_steps']
            selected=marks.index(layer['marked_index'])
            assert qs[selected]==layer['minimum_projection']
            assert all(q>=minimum for q,minimum in zip(qs,layer['minimum_projection_per_mark']))
            visible=v; Z=C=loops=0
            for a in layer['word']:
                Z+=a=='X' and ((visible[0]==0)!=(visible[1]==0))
                C+=(a=='L' and visible[0]==0) or (a=='R' and visible[-1]==0)
                loops+=a=='X' and visible[0]==visible[1]==0
                visible=step(visible,a)
            if not loops: assert Z+C==sum(len(layer['word'])-q for q in qs)
            records.append({'v':list(v),'extra':layer['extra_full_steps'],'length':len(layer['word']),'replayed_projection_all_marks':qs,'reported_minima':layer['minimum_projection_per_mark'],'Z':Z,'C':C,'zero_zero_swaps':loops})
    target=[2,1,0,0,0,7,8,6,5,4,3]
    t=next(s for s in packed['exceptional_states'] if s['v']==target)
    assert [l['minimum_projection_per_mark'] for l in t['layers']]==[[43]*3,[43]*3,[41]*3]
    out={'scope':'45 literal marked replays of 15 supplied words, aggregate consistency; lower-bound exclusion relies on reviewed exhaustive DP, not these words alone','files_sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['packed-m8-r3.json','exact-m8-r3.json','packed_budget_check.cpp','independent_check.py']},'word_records':records}
    (p/'proof_packed_audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'marked_replays':45,'candidate_word_profiles':[x for x in records if x['v']==target],'files_sha256':out['files_sha256']}))

if __name__=='__main__': main()
