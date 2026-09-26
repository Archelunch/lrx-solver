#!/usr/bin/env python3
"""Seed words for a refined leaf: root-pool words of (m..1){0,g} (fast/runs colgen JSONs and midband seed pools)
lifted by Lemma 1 to z = origin - 1 (words on the stretched = refined base).  Seeds only; every word is re-priced
on the refined base by leaf_colgen.py."""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..')))
from integrations import lrx_m as C
m, g, z0, z1 = map(int, sys.argv[1:5])
base = C.base_vector(list(range(m, 0, -1)), 1 | (1 << g))
words = set()
for f in glob.glob(os.path.join(HERE, '..', 'fast', 'runs', 'colgen-m%d-g%d-*.json' % (m, g))) + glob.glob(os.path.join(HERE, '..', 'midband-runs', 'colgen-m%d-g%d*.json' % (m, g))):
    words.update(json.load(open(f)).get('words', []))
for f in glob.glob(os.path.join(HERE, '..', 'midband-runs', 'pool-seeds*.json')):
    for pt, w in json.load(open(f)).get('%d,%d' % (m, g), []):
        words.add(w)
for f in sys.argv[5:]:
    words.update(open(f).read().split())
out = set()
for w in words:
    try:
        out.add(C.Profile(base, w).lift((z0, z1)))
    except C.CheckError:
        pass
print('\n'.join(sorted(out)))
print('%d root words, %d lifted' % (len(words), len(out)), file=sys.stderr)
