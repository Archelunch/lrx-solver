#!/usr/bin/env python3
"""Explicit scientific artifact allowlist; no chat logs or credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists():
    raise SystemExit('Choose a new archive name; published evidence is immutable.')

paths=[
 'research/cycle7/PROJECT.md','research/cycle7/claims.json',
 'runs/cycle7/certificates.json','runs/cycle7/environment.json',
 'runs/cycle7/discovery-100.json','runs/cycle7/discovery-eight-blocks.json',
 'runs/cycle7/source-nine-gap-audit.json','runs/cycle7/source-projection-audit.json',
 'runs/cycle7/independent-final.json',
 'sources/2026-09-24-nine-gap/manifest.json',
 'sources/2026-09-24-nine-gap/lrx_multiset_nine_gap_m8.tex',
]
for name in ['THEOREM_RU.md','RESULTS.md','NEXT_PASS.md','VERSION_NOTE.md','PACKAGE_README_RU.md']:
    paths.append('reports/cycle7/'+name)
for name in ['search_projected_mixtures.py','verify_certificates.py','reproduce.py','verify_bundle.py','build_package.py']:
    paths.append('experiments/cycle7/'+name)
for name in ['PROOF_AUDIT.md','REVIEW_NEW_CERTIFICATES.md','direct_stretch.py',
             'check_direct_stretch.py','direct_stretch_checks.json','source_cover_audit.json',
             'verify_new_certificates.py','new_certificates_independent_audit_v2.json']:
    paths.append('research/cycle7/cloud-proof/'+name)
source_manifest=json.loads((root/'sources/2026-09-24-nine-gap/manifest.json').read_text())
for entry in source_manifest['members']:
    path='sources/2026-09-24-nine-gap/extracted/'+entry['path']
    data=(root/path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=entry['sha256']:
        raise SystemExit('Source changed: '+path)
    paths.append(path)
if len(paths)!=len(set(paths)):
    raise SystemExit('Duplicate package path')
payload={path:(root/path).read_bytes() for path in sorted(paths)}
payload['README.md']=(root/'reports/cycle7/PACKAGE_README_RU.md').read_bytes()
manifest={'format':'lrx_cycle7_package_v1','date':'2026-09-24','files':[
    {'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    for path,data in sorted(payload.items())]}
payload['MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for path,data in sorted(payload.items()):
        info=zipfile.ZipInfo(path,date_time=(2026,9,24,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644<<16
        archive.writestr(info,data,compresslevel=9)
print(json.dumps({'path':str(args.output),'files':len(payload),
    'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))
