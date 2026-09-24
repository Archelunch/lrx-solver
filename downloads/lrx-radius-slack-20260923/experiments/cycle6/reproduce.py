#!/usr/bin/env python3
"""One-command fresh reproduction; stdlib Python plus a C++17 compiler.

Default: independent small graphs, family words, archived witness replay.
--full: rebuild both C++ checkers and repeat the two full counterexample runs.
--extended: also repeat both neighboring parameter pairs.
"""
import argparse, datetime, hashlib, json, pathlib, platform, shutil, subprocess, sys, time

p=argparse.ArgumentParser()
p.add_argument('--full',action='store_true')
p.add_argument('--extended',action='store_true')
a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
tag=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=root/'runs/cycle6/reproductions'/tag;out.mkdir(parents=True)
steps=[]

def run(name,cmd,timeout=600):
    start=time.monotonic()
    with (out/(name+'.stdout')).open('w') as stdout,(out/(name+'.stderr')).open('w') as stderr:
        try:code=subprocess.run(list(map(str,cmd)),cwd=root,stdout=stdout,stderr=stderr,timeout=timeout).returncode
        except subprocess.TimeoutExpired:code=124
    steps.append({'name':name,'command':list(map(str,cmd)),'exit_code':code,'seconds':time.monotonic()-start})
    (out/'manifest.json').write_text(json.dumps({'platform':platform.platform(),'steps':steps},indent=2)+'\n')
    if code:raise SystemExit(f'{name} failed ({code}); see {out}')
    print(f'{name}: OK',flush=True)
    return out/(name+'.stdout')

checker=root/'experiments/cycle6/independent_check.py'
run('literal-small',[sys.executable,checker,'--output',out/'literal-small.json'])
run('family',[sys.executable,checker,'--family','--output',out/'family.json'])
run('archived-words',[sys.executable,checker,'--verify-packed',root/'runs/cycle6/packed-m8-r3.json','--output',out/'archived-words.json'])
if a.full or a.extended:
    cc=shutil.which('clang++') or shutil.which('g++')
    if not cc:raise SystemExit('Full verification requires a C++17 compiler (clang++ or g++).')
    run('compiler-version',[cc,'--version'])
    for name in ['radius_slack','packed_budget_check']:
        run('compile-'+name,[cc,'-std=c++17','-O3','-Wall','-Wextra',root/f'experiments/cycle6/{name}.cpp','-o',out/name])
    run('compare-small',[sys.executable,checker,'--binary',out/'radius_slack','--output',out/'compare-small.json'])
    run('compare-dual-small',[sys.executable,checker,'--packed-binary',out/'packed_budget_check','--output',out/'compare-dual-small.json'])
    primary=run('primary-m8-r3',[out/'radius_slack',8,3,'--full'])
    secondary=run('independent-m8-r3',[out/'packed_budget_check',8,3,2])
    x=json.loads(primary.read_text());y=json.loads(secondary.read_text())
    v=[2,1,0,0,0,7,8,6,5,4,3]
    assert x['P']==y['P']==42 and x['full_radius']==y['full_radius']==48
    assert x['visible_states']==y['full_states']==6652800
    assert x['excess']==1 and x['violations'][0]['v']==v and x['violations'][0]['A_P']==49
    example=next(z for z in y['exceptional_states'] if z['v']==v)
    assert example['distance']==47
    assert [z['minimum_projection_per_mark'] for z in example['layers']]==[[43]*3,[43]*3,[41]*3]
    assert y['layers'][0]['over_P']==5 and y['layers'][1]['over_P']==1 and y['layers'][2]['over_P']==0
    assert max(map(int,y['layers'][0]['histogram']))==43
    run('fresh-words',[sys.executable,checker,'--verify-packed',secondary,'--output',out/'fresh-words.json'])
    if a.extended:
        for m,r,cap in [(8,2,3000000),(8,4,7000000),(9,2,4000000)]:
            rp=run(f'primary-m{m}-r{r}',[out/'radius_slack',m,r,f'--state-limit={cap}'])
            sp=run(f'independent-m{m}-r{r}',[out/'packed_budget_check',m,r,0])
            xx=json.loads(rp.read_text());yy=json.loads(sp.read_text())
            assert xx['P']==yy['P'] and xx['max_A_P']>=yy['full_radius']
            assert sum(xx['histogram'].values())+xx['missing']==yy['full_states']
            expected={(8,2):(36,42,36),(8,4):(48,54,50),(9,2):(45,52,45)}[m,r]
            assert (xx['P'],xx['max_A_P'],max(map(int,yy['layers'][0]['histogram'])))==expected
            assert xx['missing']==xx['excess']==0 and xx['max_A_P']==yy['full_radius']
    (out/'COUNTEREXAMPLE_VERIFIED.json').write_text(json.dumps({'v':v,'D':47,'P':42,'A_P':49,'bound':48,'general_conjecture_disproved':False,'absolute_radius_candidate_disproved_by_exact_enumeration':True},indent=2)+'\n')
manifest=json.loads((out/'manifest.json').read_text())
manifest['sources']=[{'path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in (root/'experiments/cycle6').glob('*') if path.suffix in ['.py','.cpp']]
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out)
