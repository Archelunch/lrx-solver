#!/usr/bin/env python3
"""Record bounded native computations and provenance."""
import argparse, datetime, hashlib, json, pathlib, platform, subprocess, time
p=argparse.ArgumentParser()
p.add_argument('m',type=int);p.add_argument('r',type=int)
p.add_argument('--witness',action='store_true');p.add_argument('--full',action='store_true')
p.add_argument('--timeout',type=int,default=600)
p.add_argument('--state-limit',type=int,default=3000000)
a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
binary=root/'experiments/cycle6/radius_slack'
cmd=[str(binary),str(a.m),str(a.r)]+(['--witness'] if a.witness else [])+(['--full'] if a.full else [])+[f'--state-limit={a.state_limit}']
prefix=root/f'runs/cycle6/exact-m{a.m}-r{a.r}'
if prefix.with_suffix('.json').exists():raise SystemExit('Refusing to overwrite a recorded computation')
meta={'command':cmd,'cwd':str(root),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'timeout_seconds':a.timeout,'platform':platform.platform(),'source_sha256':hashlib.sha256((root/'experiments/cycle6/radius_slack.cpp').read_bytes()).hexdigest(),
      'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
start=time.monotonic()
with prefix.with_suffix('.json').open('w') as out,prefix.with_suffix('.stderr.log').open('w') as err:
 try: meta['exit_code']=subprocess.run(cmd,cwd=root,stdout=out,stderr=err,timeout=a.timeout).returncode
 except subprocess.TimeoutExpired:meta['timed_out']=True;meta['exit_code']=124
meta['wall_seconds']=time.monotonic()-start
prefix.with_suffix('.manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
if meta['exit_code']==0:
 data=json.loads(prefix.with_suffix('.json').read_text())
 print(json.dumps({k:data[k] for k in ('m','r','P','visible_states','max_A_P','missing','excess','full_radius','max_lift_gap','elapsed_seconds')},ensure_ascii=False),flush=True)
else: print(json.dumps(meta),flush=True)
raise SystemExit(meta['exit_code'])
