#!/usr/bin/env python3
"""Proof-branch complete review, stdlib only; imports only our direct_stretch.

No coordinator profile/checker, optimizer, Bruhat transfer or BFS is used.
"""
import ast
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import permutations
import json
from pathlib import Path
import struct
import time
import zipfile
from direct_stretch import profile,lift,costs,step

ROOT=Path(__file__).resolve().parent

def coverage_bytes(path):
    with zipfile.ZipFile(path) as archive: data=archive.read('union_covered.npy')
    assert data[:6]==b'\x93NUMPY'
    if data[6:8]==b'\x01\x00': start=10;size=struct.unpack_from('<H',data,8)[0]
    elif data[6:8]==b'\x02\x00':start=12;size=struct.unpack_from('<I',data,8)[0]
    else:raise ValueError('Unsupported NPY version')
    meta=ast.literal_eval(data[start:start+size].decode('latin1').strip())
    assert meta['shape']==(40320,512) and meta['descr']=='|b1' and meta['fortran_order'] is False
    body=data[start+size:];assert len(body)==40320*512 and set(body)<={0,1}
    return body

def check_case(case,covered,orders):
    i=case['order_index'];mask=case['mask']
    assert type(i) is int and 0<=i<len(orders)
    assert type(mask) is int and 0<mask<512 and 4<=mask.bit_count()<=8
    assert covered[i*512+mask]==0
    labels=orders[i];assert list(labels)==case['labels']
    v=[]
    for slot in range(9):
        if mask & (1<<slot):v.append(0)
        if slot<8:v.append(labels[slot])
    assert v==case['base_state'];v=tuple(v);k=mask.bit_count()
    assert case['target_base']==30+6*k and case['prior_union_covered'] is False
    rows=case['rows'];assert rows
    weights=[Fraction(row['weight']) for row in rows]
    assert all(w>0 for w in weights) and sum(weights)==1
    pp=[];mixed=0
    for row in rows:
        p=profile(v,row['word']);pp.append(p)
        assert p['final']==tuple(range(1,9))+(0,)*k
        assert p['B']==row['base_cost'] and p['beta']==row['beta']
        bad=sum(not((c>=0 and all(a>=0 for a in aa))or(c<=0 and all(a<=0 for a in aa))) for c,aa in p['gaps'])
        assert bad==row['mixed_gaps'];mixed+=bad
    B=sum(w*p['B'] for w,p in zip(weights,pp))
    beta=[sum(w*p['beta'][j] for w,p in zip(weights,pp)) for j in range(k)]
    assert B<31+6*k and all(b<=6 for b in beta)
    assert str(B)==case['mean_base'] and list(map(str,beta))==case['mean_beta']
    return v,pp,weights,B,beta,mixed

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'new_certificates_independent_audit.json')
    args=parser.parse_args()
    assert not args.output.exists(), 'Choose a fresh --output path'
    started=time.monotonic()
    certpath=ROOT/'review-input/runs/cycle7/certificates.json'
    covpath=ROOT/'input/literature/multiset_nine_gap_projection_search_20260924.npz'
    sourcepath=ROOT/'input/literature/multiset_nine_gap_complete_certificates_20260924.json'
    bundle=json.loads(certpath.read_text())
    assert bundle['format']=='lrx_cycle7_explicit_mixtures_v1' and bundle['m']==8
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(covpath)==bundle['source_coverage_sha256']
    assert digest(sourcepath)==bundle['source_bundle_sha256']
    covered=coverage_bytes(covpath);orders=list(permutations(range(1,9)))
    seen=set();byk=Counter();rows=letters=mixed=replays=0;special={};replay_records=[]
    for index,case in enumerate(bundle['cases']):
        key=(case['order_index'],case['mask']);assert key not in seen;seen.add(key)
        v,pp,weights,B,beta,mm=check_case(case,covered,orders)
        k=v.count(0);byk[k]+=1;rows+=len(pp);letters+=sum(len(r['word']) for r in case['rows']);mixed+=mm
        if key in [(5,83),(5,31)]:
            special[str(key)]={'labels':case['labels'],'mask':case['mask'],'base':list(v),'rows':case['rows'],'mean_B':str(B),'mean_beta':list(map(str,beta)),'strict_margin':str(31+6*k-B)}
        if index%1024==0 or key in [(5,83),(5,31)]:
            for lengths in ([97+j for j in range(k)],[1001]+[1]*(k-1),[1<<j for j in range(k)]):
                values=[]
                for row,p in zip(case['rows'],pp):
                    start,word,end=lift(v,row['word'],lengths,False)
                    current=start
                    for a in word:current=step(current,a)
                    assert current==end==tuple(range(1,9))+(0,)*sum(lengths)
                    exact,upper=costs(p,lengths);assert len(word)==exact<=upper
                    values.append(len(word));replays+=1
                assert min(values)<=30+6*sum(lengths)
                assert sum(w*l for w,l in zip(weights,values))<31+6*sum(lengths)
                replay_records.append({'order_index':key[0],'mask':key[1],'lengths':lengths,'prices':values})
    assert len(seen)==8193 and rows==32417 and dict(byk)=={5:2,4:1,7:2,8:8188} and mixed==0
    s=special['(5, 83)'];assert s['mean_B']=='274/5' and s['mean_beta']==['27/5','6','6','22/5']
    assert sorted((r['base_cost'],tuple(r['beta']),r['weight']) for r in s['rows'])==[(48,(5,8,6,0),'3/5'),(65,(6,3,6,11),'2/5')]
    s=special['(5, 31)'];assert s['mean_B']=='59' and s['mean_beta']==['6','3','0','3','6']
    # Stronger five-block bound: B<=29+6k, beta<=6.
    assert Fraction(s['mean_B'])<=29+6*5
    missing8=sum(covered[i*512+mask]==0 for i in range(40320) for mask in range(1,512) if mask.bit_count()==8)
    assert missing8==10248
    bad_cases=[]
    sample=bundle['cases'][0]
    for mutation in ('weight','slope','word','mask','index'):
        bad=json.loads(json.dumps(sample))
        if mutation=='weight':bad['rows'][0]['weight']='0'
        if mutation=='slope':bad['rows'][0]['beta'][0]+=1
        if mutation=='word':bad['rows'][0]['word']+='?'
        if mutation=='mask':bad['mask']=511
        if mutation=='index':bad['order_index']+=1
        try:check_case(bad,covered,orders)
        except (AssertionError,ValueError):bad_cases.append(mutation)
        else:raise AssertionError('Corrupt certificate accepted')
    out={'status':'PASS','families':len(seen),'rows':rows,'base_letters':letters,'by_blocks':dict(byk),'mixed_gaps':mixed,'large_length_replays':replays,'negative_controls_rejected':bad_cases,'previously_uncovered_eight_block_families':missing8,'remaining_eight_block_families_relative_to_snapshot':missing8-byk[8],'special_cases':special,'large_length_examples':replay_records,'novelty_scope':'Every distinct pair absent in exact supplied union_covered snapshot; not a claim of absolute priority versus unseen newer posts.','all_lengths_basis':'PROOF_AUDIT.md direct block-macro proof and exact rational inequalities, not finite replay extrapolation','full_m8_proved':False,'full_conjecture_proved':False,'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [certpath,covpath,sourcepath,ROOT/'direct_stretch.py',Path(__file__)]},'seconds':time.monotonic()-started}
    destination=args.output;assert not destination.exists()
    destination.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['special_cases','large_length_examples','source_sha256']},ensure_ascii=False))

if __name__=='__main__':main()
