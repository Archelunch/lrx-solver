from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent
m=json.loads((r/'MANIFEST.json').read_text())
for x in m['files']:
 p=r/x['path'];assert p.is_file(),x['path']
 assert p.stat().st_size==x['bytes'],x['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
print('SHA-256 verified:',len(m['files']),'files. Integrity only; run --full for the mathematical certificate.')
