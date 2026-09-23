import itertools
import json
import unittest
from pathlib import Path

from src.lrx.candidates import Candidate, CandidateError, run_beam, run_rules
from src.lrx.certificates import replay_visible
from src.lrx.dsl import DslError, Env, EvalError, compile_expr, features

ROOT = Path(__file__).resolve().parents[1]


def brute_cinv(v):
    seq = [x for x in v if x]
    best = None
    for k in range(len(seq)):
        rot = seq[k:] + seq[:k]
        inv = sum(
            1
            for i in range(len(rot))
            for j in range(i + 1, len(rot))
            if rot[i] > rot[j]
        )
        best = inv if best is None else min(best, inv)
    return best


class FeatureTests(unittest.TestCase):
    def test_hand_computed_n5(self):
        f = features((3, 0, 1, 2, 0), 3, 2)
        self.assertEqual(f["inv"], 2)
        self.assertEqual(f["cinv"], 0)
        self.assertEqual(f["pos1"], 2)
        self.assertEqual(f["zero_gap_max"], 3)
        self.assertEqual(f["zero_gap_min"], 2)
        self.assertEqual(f["zeros_block"], 0)
        self.assertEqual(f["disp_sum"], 6)  # tokens 1,2,3 at 2,3,0: 2+2+2
        self.assertEqual(f["T"], 7)
        root = features((1, 2, 3, 0, 0), 3, 2)
        self.assertEqual(
            (
                root["is_root"],
                root["csorted"],
                root["rot_dist"],
                root["hamming"],
                root["zeros_block"],
            ),
            (1, 1, 0, 0, 1),
        )

    def test_cinv_matches_brute_force(self):
        for v in itertools.permutations((1, 2, 3, 4, 0, 0)):
            self.assertEqual(features(v, 4, 2)["cinv"], brute_cinv(v), v)

    def test_rotation_features(self):
        v = (0, 1, 2, 3, 0)  # root rotated right by one
        f = features(v, 3, 2)
        self.assertEqual((f["csorted"], f["rot_dist"], f["zeros_block"]), (1, 1, 1))


class DslTests(unittest.TestCase):
    def test_compile_and_eval(self):
        env = Env((3, 0, 1, 2, 0), 3, 2)
        self.assertEqual(compile_expr(["add", "inv", 5])(env), 7)
        self.assertEqual(compile_expr(["sum_tokens", "dmin"])(env), 6)
        self.assertEqual(compile_expr(["max_tokens", ["mul", "t", "at_tgt"]])(env), 0)
        self.assertEqual(compile_expr(["at", -1])(env), 0)
        self.assertEqual(compile_expr(["pos", 3])(env), 0)
        self.assertEqual(compile_expr(["if", ["gt", "a", "b"], 1, 2])(env), 1)

    def test_rejections(self):
        for bad in [
            "nope",
            ["frob", 1],
            "t",
            ["sum_tokens", ["sum_tokens", "t"]],
            10**6,
            ["sub", 1],
            {"op": "add"},
        ]:
            with self.assertRaises(DslError, msg=bad):
                compile_expr(bad)
        deep = 1
        for _ in range(12):
            deep = ["neg", deep]
        with self.assertRaises(DslError):
            compile_expr(deep)

    def test_bad_divisor_is_eval_error(self):
        env = Env((1, 2, 0), 2, 1)
        with self.assertRaises(EvalError):
            compile_expr(["floordiv", 3, ["sub", "a", 1]])(env)


class CandidateTests(unittest.TestCase):
    def test_schema_rejections(self):
        for bad in [
            {},
            {"kind": "zzz"},
            {"kind": "bound"},
            {"kind": "bound", "expr": 1, "extra": 1},
            {"kind": "radius", "expr": "inv"},
            {"kind": "bound", "expr": "rot"},
            {"kind": "rules", "rules": []},
            {"kind": "rules", "rules": [{"if": 1, "do": "Q"}]},
            {"kind": "beam", "expr": 1, "beam_width": 99},
            "not json",
        ]:
            with self.assertRaises(CandidateError, msg=bad):
                Candidate(bad)

    def test_hash_ignores_name_and_notes(self):
        a = Candidate({"kind": "bound", "expr": "T", "name": "a"})
        b = Candidate({"kind": "bound", "expr": "T", "notes": "b"})
        c = Candidate({"kind": "bound", "expr": "n"})
        self.assertEqual(a.hash, b.hash)
        self.assertNotEqual(a.hash, c.hash)

    def test_baselines_are_valid(self):
        for path in sorted((ROOT / "candidates" / "baselines").glob("*.json")):
            Candidate(json.loads(path.read_text()))

    def test_bubble_rules_sort_every_small_state(self):
        cand = Candidate(
            json.loads(
                (ROOT / "candidates" / "baselines" / "rules_bubble.json").read_text()
            )
        )
        root = (1, 2, 3, 0, 0)
        for v in set(itertools.permutations(root)):
            word, reason = run_rules(cand, v, 3, 2, 4 * 25)
            self.assertEqual(reason, "solved", v)
            self.assertEqual(replay_visible(v, word), root)

    def test_cycle_and_step_cap(self):
        looping = Candidate({"kind": "rules", "rules": [{"if": 1, "do": "X"}]})
        word, reason = run_rules(looping, (0, 2, 1), 2, 1, 100)
        self.assertIsNone(word)
        self.assertTrue(
            reason.startswith("cycle after 3 steps; first moves XXX"), reason
        )
        counting = Candidate(
            {"kind": "rules", "rules": [{"if": ["ge", "steps", 0], "do": "X"}]}
        )
        word, reason = run_rules(counting, (0, 2, 1), 2, 1, 50)
        self.assertIsNone(word)
        self.assertTrue(reason.startswith("step cap 50"), reason)

    def test_registers(self):
        cand = Candidate(
            {
                "kind": "rules",
                "default": "L",
                "rules": [{"if": ["eq", "r0", 0], "do": "R", "set": {"r0": 1}}],
            }
        )
        word, reason = run_rules(cand, (0, 1, 2), 2, 1, 50)
        self.assertEqual(reason, "solved")
        self.assertTrue(word.startswith("R"))
        self.assertEqual(replay_visible((0, 1, 2), word), (1, 2, 0))

    def test_beam_solves_small(self):
        cand = Candidate(
            {"kind": "beam", "expr": ["add", "disp_sum", "cinv"], "beam_width": 16}
        )
        word, reason = run_beam(cand, (3, 0, 1, 2, 0), 3, 2, 5000)
        self.assertEqual(reason, "solved")
        self.assertEqual(replay_visible((3, 0, 1, 2, 0), word), (1, 2, 3, 0, 0))


if __name__ == "__main__":
    unittest.main()


class FuzzTests(unittest.TestCase):
    def test_random_json_never_crashes_validator(self):
        import random

        rng = random.Random(0)
        atoms = [
            0,
            1,
            -3,
            10**7,
            "L",
            "X",
            "inv",
            "t",
            "rules",
            None,
            True,
            1.5,
            [],
            {},
        ]

        def junk(depth=0):
            roll = rng.random()
            if depth > 3 or roll < 0.4:
                return rng.choice(atoms)
            if roll < 0.7:
                return [junk(depth + 1) for _ in range(rng.randint(0, 4))]
            keys = ["if", "do", "set", "kind", "expr", "rules", "default", "r0", "x"]
            return {rng.choice(keys): junk(depth + 1) for _ in range(rng.randint(0, 3))}

        for _ in range(3000):
            spec = {
                "kind": rng.choice(
                    ["rules", "bound", "potential", "beam", "radius", [], 3]
                )
            }
            spec.update(
                {
                    k: junk()
                    for k in rng.sample(["expr", "rules", "default", "beam_width"], 2)
                }
            )
            try:
                Candidate(spec)
            except CandidateError:
                pass
        for bad in [
            {"kind": "rules", "rules": [{"if": 1, "do": ["L"]}]},
            {"kind": "rules", "rules": [{"if": 1, "do": "L"}], "default": ["X"]},
            {"kind": "rules", "rules": [{"if": 1, "do": "L", "set": {"r0": {}}}]},
            {"kind": ["rules"]},
        ]:
            with self.assertRaises(CandidateError):
                Candidate(bad)


class TokenDistanceOpTests(unittest.TestCase):
    def test_dist_of(self):
        env = Env(
            (3, 0, 1, 2, 0), 3, 2
        )  # token 3 at 0 (target 2), token 1 at 2 (target 0)
        self.assertEqual(compile_expr(["cw_of", "a"])(env), 3)
        self.assertEqual(compile_expr(["ccw_of", "a"])(env), 2)
        self.assertEqual(compile_expr(["dmin_of", "a"])(env), 2)
        self.assertEqual(compile_expr(["dmin_of", 1])(env), 2)
        self.assertEqual(compile_expr(["dmin_of", "b"])(env), 0)  # b is a zero
        self.assertEqual(compile_expr(["dmin_of", 99])(env), 0)
        with self.assertRaises(DslError):
            compile_expr(["dmin_of", 1, 2])
