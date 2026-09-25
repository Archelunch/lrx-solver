"""Fast tests for the independent lift audit (integrations/lift_audit.py)."""
import subprocess
import sys
import unittest

from integrations import lift_audit as A
from integrations import lift_control_naive as N
from integrations import lift_task as T
from tests.test_search_lift_eval import parent


class LiftAuditTest(unittest.TestCase):
    def test_audit_does_not_import_the_evaluator(self):
        code = ("import sys, integrations.lift_audit as a; a.checker(9); "
                "print(sorted(m for m in ('integrations.lift_evaluator', 'integrations.lift_task', "
                "'integrations.lrx_m') if m in sys.modules))")
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), '[]')

    def test_child_reconstruction_matches_task_builder(self):
        for inst in T.build_instances(parent()):
            labels, mask, base, k = A.child_of(inst)
            self.assertEqual((labels, mask, base, k), (inst['child']['labels'], inst['child']['mask'],
                                                       inst['child']['unit_base'], inst['child']['k']))

    def test_bad_claims_disagree(self):
        inst = T.build_instances(parent())[0]
        out = N.lift(inst)
        w0 = out['words'][0]
        ok, why = A.audit_claim(inst, out, {'words': [w0], 'weights': ['1']})
        self.assertFalse(ok)
        self.assertIn('weighted', why)
        self.assertFalse(A.audit_claim(inst, out, {'words': ['X'], 'weights': ['1']})[0])
        self.assertFalse(A.audit_claim(inst, {'words': ['L'] + out['words']}, {'words': [w0], 'weights': ['1']})[0])
        self.assertFalse(A.audit_claim(inst, out, {'words': [w0], 'weights': ['1/2']})[0])


if __name__ == '__main__':
    unittest.main()
