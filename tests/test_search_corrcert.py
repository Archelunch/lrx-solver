"""Fast checks for the corr-cert-260924 exact evaluator (autoresearch, search side)."""
import json
import os
import sys
import unittest
from fractions import Fraction
from itertools import permutations
from math import comb

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "autoresearch", "corr-cert-260924")
sys.path.insert(0, HERE)
import corrcert as cc  # noqa: E402
from validate_identities import check_perm  # noqa: E402


def trivial_cert(m, Q=1):
    """All triple and mu coefficients zero; lambda_ab = Q * min_q kappa_ab(q)."""
    n = m - 1
    return {"m": m, "Q": Q,
            "lambda": {pr: Q * min(cc.kappa(m, *pr, q) for q in range(1, m)) for pr in cc.pairs(m)},
            "mu": {a: [0] * n for a in range(m)},
            "alpha": {t: [0] * n for t in cc.triples(m)},
            "beta": {t: [0] * n for t in cc.triples(m)},
            "gamma": {t: [0] * n for t in cc.triples(m)}}


class CorrCertTest(unittest.TestCase):
    def test_identities_full_enumeration_m4_m5(self):
        for m in (4, 5):
            worst = max(cc.stats(p)["E"] for p in permutations(range(m)))
            self.assertEqual(worst, 0)
            for p in permutations(range(m)):
                self.assertEqual(check_perm(p)[1], [], p)

    def test_equality_order(self):
        for m in (4, 7, 12):
            self.assertEqual(cc.stats([(-i) % m for i in range(m)])["E"], 0)

    def test_hand_built_certificate_accepted(self):
        m = 5
        cert = trivial_cert(m)
        r = cc.check_certificate(m, cert)
        self.assertTrue(r["ok"])
        self.assertEqual(r["checks"], cc.expected_checks(m))
        J = sum(cert["lambda"].values())
        self.assertEqual(r["epsilon"], Fraction(-J, m) - 4 * comb(m, 3))
        self.assertEqual(r["proves"], r["epsilon"] < 1)
        # json round trip preserves the certificate
        self.assertEqual(cc.from_json(json.loads(json.dumps(cc.to_json(cert))))["lambda"], cert["lambda"])

    def test_corruption_rejected(self):
        m = 5
        for desc, rejected in cc.negative_controls(m, trivial_cert(m)):
            self.assertTrue(rejected, desc)
        bad = trivial_cert(m)
        bad["alpha"][(0, 1, 2)][0] = 1
        bad["beta"][(0, 1, 2)][0] = 1
        r = cc.check_certificate(m, bad)
        self.assertFalse(r["ok"])
        self.assertEqual(r["violations"][0][:6], ("triple5", 0, 1, 2, 1, 1))

    def test_repair_makes_valid(self):
        m = 5
        cert = trivial_cert(m)
        cert["alpha"][(1, 2, 3)] = [3, 1, 4, 1]
        self.assertFalse(cc.check_certificate(m, cert)["ok"])
        self.assertTrue(cc.check_certificate(m, cc.repair(cert))["ok"])

    def test_generated_m4_certificate_if_present(self):
        path = os.path.join(HERE, "certs", "m4.json")
        if not os.path.exists(path):
            self.skipTest("certs/m4.json not generated")
        with open(path) as fh:
            r = cc.check_certificate(4, cc.from_json(json.load(fh)))
        self.assertTrue(r["ok"] and r["proves"])


if __name__ == "__main__":
    unittest.main()
