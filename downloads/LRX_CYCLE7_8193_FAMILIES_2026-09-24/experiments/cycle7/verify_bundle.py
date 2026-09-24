#!/usr/bin/env python3
"""Check packaged file sizes and SHA-256 values, without third-party modules."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
manifest=json.loads((root/'MANIFEST.json').read_text())
for entry in manifest['files']:
    relative=Path(entry['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise SystemExit('Unsafe manifest path')
    path=root/relative
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f'Missing/nonregular file: {relative}')
    data=path.read_bytes()
    if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
        raise SystemExit(f'Integrity failure: {relative}')
print(f"PASS: {len(manifest['files'])} files match the package manifest.")
