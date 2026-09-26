#!/usr/bin/env python3
"""Driver for lrxtree_wide (n <= 20, m <= 13): treeoracle.py with the binary and the size check swapped.

Importing this module patches the treeoracle module in place (BIN and encode_tree), so leaf_colgen.py and
probe.py run unchanged against the wide binary:  python3 treeoracle_wide.py leaf_colgen ARGS...  or
python3 treeoracle_wide.py probe ARGS...  Every returned word is still re-priced by negcert_general.price.
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import treeoracle as TO  # noqa: E402

NG = TO.NG
NARROW_BIN = TO.BIN
WIDE_BIN = os.path.join(HERE, 'lrxtree_wide')


def encode_tree(vec, picks, W=(1, 1, 1)):
    m = sum(1 for x in vec if x)
    blocks = NG.blocks_of(vec)
    if len(blocks) != 2 or len(vec) > 20 or m > 13 or any(picks[j] not in blocks[j] for j in range(2)):
        raise ValueError('two blocks, n <= 20, m <= 13, one pick per block')
    out, zi = [], 0
    for x in vec:
        if x == 0:
            j = picks.index(zi) if zi in picks else None
            out.append(m + j if j is not None and W[1 + j] > 0 else m + 2)
            zi += 1
        else:
            out.append(x - 1)
    return m, out


_narrow_encode = TO.encode_tree


def use_wide():
    TO.BIN = WIDE_BIN
    TO.encode_tree = encode_tree


def use_narrow():
    TO.BIN = NARROW_BIN
    TO.encode_tree = _narrow_encode


run = TO.run

if __name__ == '__main__':
    use_wide()
    target = sys.argv[1]
    sys.argv = [os.path.join(HERE, target + '.py')] + sys.argv[2:]
    runpy.run_path(sys.argv[0], run_name='__main__')
