"""Fast tests for the independent m=8 package checker (autoresearch/verify-m8-260924/checker)."""
import os
import sys
import unittest
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(ROOT, 'autoresearch', 'verify-m8-260924', 'checker')
sys.path.insert(0, CHECKER)

try:
    import lrxm8 as C
except ImportError:  # checker directory absent
    C = None

V8 = [0, 5, 0, 8, 7, 0, 6, 4, 3, 2, 1, 0]
W1 = 'XLLXLXRRXRRXLXLLXRXRXRRRXRXRXRXLXLXLXLXRRXRXLXRR'
W2 = 'LXLLLXLLXRXLLXRXRXRRXRXLLXLXLLXLXRXRXRXRXRXLXLXLLXLXLXRXRXRXRXRXRX'
Q7 = [0, 1, 0, 8, 0, 7, 6, 5, 4, 0, 3, 2]
WQ7 = 'LXLXRXRXRXRRXRXRXRXRXLXLXLXLLXLLXLXLXLXRXLLLLXLXRXRRR'


@unittest.skipIf(C is None, 'checker not present')
class M8CheckerTest(unittest.TestCase):
    def test_word_execution(self):
        v = [3, 0, 1, 2]
        self.assertEqual(C.run_naive(v, 'L'), [0, 1, 2, 3])
        self.assertEqual(C.run_naive(v, 'R'), [2, 3, 0, 1])
        self.assertEqual(C.run_naive(v, 'X'), [0, 3, 1, 2])
        for w in ('LXRXXLLR', 'RRXLXLX', W1):
            self.assertEqual(C.run(V8, w), C.run_naive(V8, w))

    def test_lift_macro_literal(self):
        p = C.Profile(V8, W1)
        self.assertEqual((p.base, p.beta, p.same_sign), (48, [9, 6, 0, 8], True))
        for z in ((0, 0, 0, 0), (2, 0, 1, 0), (1, 3, 0, 2)):
            w = p.lift(z)
            self.assertTrue(C.is_root(C.run(C.stretch(V8, p.picks, z), w)))
            self.assertEqual(len(w), p.affine(z))
        # X on (0^{1+z}, a) -> L^z X (RX)^z moves a in front of the block
        self.assertEqual(C.run([0, 0, 0, 5, 1], 'LL' + 'X' + 'RX' * 2), [5, 0, 0, 0, 1])

    def test_mixture_criterion(self):
        costs = [(C.Profile(V8, W).base, C.Profile(V8, W).beta) for W in (W1, W2)]
        ok, B, beta = C.mixture_criterion(costs, ['5/8', '3/8'], 4)
        self.assertTrue(ok)
        self.assertEqual(B, Fraction(219, 4))
        self.assertEqual(beta, [6, Fraction(9, 2), 3, 5])
        ok, _, _ = C.mixture_criterion(costs, ['1', '0'], 4)
        self.assertFalse(ok)

    def test_comparison_transfer(self):
        ref = C.Reference(Q7, WQ7)
        P = C.base_vector([2, 1, 6, 3, 4, 7, 5, 8], 0b1000111)
        base, beta, _ = ref.transfer(P, 5)
        self.assertEqual((base, beta), (41, [3, 4, 5, 6]))
        ref.literal_transfer(P, 5, [(0, 2, 3, 2)], base, beta)
        with self.assertRaises(C.CheckError):
            ref.transfer(P, 4)  # cut crossed by a swap

    def test_projection(self):
        child, w, keep = C.project(V8, W1, {1})
        self.assertEqual(child, [0, 5, 8, 7, 0, 6, 4, 3, 2, 1, 0])
        self.assertTrue(C.is_root(C.run(child, w)))
        parent, kid = C.Profile(V8, W1).beta, C.Profile(child, w).beta
        for j, pj in enumerate((0, 2, 3)):  # Lemma 5: retained slopes do not grow
            self.assertLessEqual(kid[j], parent[pj])


if __name__ == '__main__':
    unittest.main()
