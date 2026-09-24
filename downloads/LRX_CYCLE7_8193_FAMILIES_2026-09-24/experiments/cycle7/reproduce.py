#!/usr/bin/env python3
"""Full certificate verification with Python >=3.10, standard library only."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile

root=Path(__file__).resolve().parents[2]
if sys.version_info < (3,10) or sys.flags.optimize:
    raise SystemExit('Use Python >=3.10 without -O / PYTHONOPTIMIZE.')
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=root/'runs/cycle7/reproductions'/stamp;out.mkdir(parents=True)
checker=root/'experiments/cycle7/verify_certificates.py'
certificate=root/'runs/cycle7/certificates.json'
coverage=root/'sources/2026-09-24-nine-gap/extracted/literature/multiset_nine_gap_projection_search_20260924.npz'
cmd=[sys.executable,str(checker),str(certificate),'--coverage',str(coverage),'--output',str(out/'verification.json')]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
(out/'stdout.txt').write_text(r.stdout);(out/'stderr.txt').write_text(r.stderr)
(out/'receipt.json').write_text(json.dumps({'command':cmd,'returncode':r.returncode,'python':sys.version,
    'sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [checker,certificate,coverage]}},indent=2)+'\n')
print(r.stdout,end='');print(r.stderr,end='',file=sys.stderr)
if r.returncode:
    raise SystemExit(r.returncode)

# Keep the independent reviewer's code byte-for-byte. Reconstruct its input
# layout in a temporary directory; no source modules are imported by this driver.
review=root/'research/cycle7/cloud-proof'
catalog=root/'sources/2026-09-24-nine-gap/extracted/literature/multiset_nine_gap_complete_certificates_20260924.json'
with tempfile.TemporaryDirectory(prefix='lrx-cycle7-review-') as temporary:
    # macOS /var -> /private/var must match the reviewer's resolved __file__.
    work=Path(temporary).resolve()
    mapping={
        review/'direct_stretch.py':work/'direct_stretch.py',
        review/'verify_new_certificates.py':work/'verify_new_certificates.py',
        certificate:work/'review-input/runs/cycle7/certificates.json',
        coverage:work/'input/literature'/coverage.name,
        catalog:work/'input/literature'/catalog.name,
    }
    for source,destination in mapping.items():
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    independent_cmd=[sys.executable,str(work/'verify_new_certificates.py'),'--output',str(out/'reviewer-verification.json')]
    r=subprocess.run(independent_cmd,capture_output=True,text=True,timeout=180)
    (out/'reviewer-stdout.txt').write_text(r.stdout)
    (out/'reviewer-stderr.txt').write_text(r.stderr)
    (out/'reviewer-receipt.json').write_text(json.dumps({
        'command':independent_cmd,'returncode':r.returncode,'python':sys.version,
        'sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in mapping},
        'temporary_layout':'Original independent checker and inputs copied without alteration.',
    },indent=2)+'\n')
    print(r.stdout,end='');print(r.stderr,end='',file=sys.stderr)
print('Saved:',out)
raise SystemExit(r.returncode)
