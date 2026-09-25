"""Bound-m campaign 2 plumbing: splits, packet v2, seeds, sub-caps, validation-only selection."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from integrations import bound_c2 as c2
from integrations import bound_c2_finalize as fin
from integrations import bound_evaluator as E

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "autoresearch" / "bound-m-c2-260925"
C1 = ROOT / "autoresearch" / "bound-m-260925"


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _keys(fams):
    return {(tuple(f["labels"]), f["mask"]) for f in fams}


class Splits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.man = json.loads((CAMP / "frozen" / "manifest.json").read_text())
        cls.dev = E.load_set(ROOT / cls.man["development"]["path"])
        cls.val = E.load_set(CAMP / "frozen" / "validation.json", allow_holdout=True)
        cls.hold = E.load_set(CAMP / "frozen" / "holdout.json", allow_holdout=True)

    def test_hashes_and_sizes(self):
        self.assertEqual(_sha(ROOT / self.man["development"]["path"]), self.man["development"]["sha256"])
        for n in ("validation.json", "holdout.json"):
            self.assertEqual(_sha(CAMP / "frozen" / n), self.man["files"][n])
        self.assertEqual((len(self.dev), len(self.val), len(self.hold)), (303, 165, 225))
        self.assertEqual({f["m"] for f in self.val}, {11})
        self.assertEqual(sum(f["m"] == 12 for f in self.hold), 165)
        self.assertEqual(sum(f["m"] == 11 for f in self.hold), 60)

    def test_disjoint(self):
        c1 = {n: json.loads((C1 / "frozen" / f"{n}.json").read_text())["families"]
              for n in ("development", "holdout", "edge")}
        self.assertFalse(_keys(self.dev) & _keys(self.val))
        self.assertFalse(_keys(self.dev) & _keys(self.hold))
        self.assertFalse(_keys(self.val) & _keys(self.hold))
        self.assertFalse(_keys(self.hold) & _keys([f for fams in c1.values() for f in fams]))
        self.assertEqual(self.val, [f for f in c1["holdout"] if f["m"] == 11])

    def test_holdout_stratification(self):
        m12 = [f for f in self.hold if f["m"] == 12]
        self.assertEqual(sorted({f["k"] for f in m12}), list(range(2, 13)))
        for k in range(2, 13):
            self.assertEqual(sum(f["k"] == k for f in m12), 15)
        for fams, scale in ((m12, 11), ([f for f in self.hold if f["m"] == 11], 4)):
            counts = {c: sum(f["class"] == c for f in fams) for c in ("rev_rot", "near_rev", "refl", "high_inv",
                                                                     "uniform", "easy")}
            self.assertEqual(counts, {c: n * scale for c, n in fin_classes()})
        self.assertTrue(any(f["labels"] == list(range(12, 0, -1)) for f in m12))

    def test_engines_refuse_validation_and_holdout(self):
        for n in ("validation.json", "holdout.json"):
            with self.assertRaises(ValueError):
                E.guard_not_holdout(CAMP / "frozen" / n)
            with self.assertRaises(ValueError):
                E.load_set(CAMP / "frozen" / n)
        cc, _ = c2.campaign()
        hidden = c2.forbidden_ids(cc)
        self.assertEqual(len(hidden), 390)
        self.assertFalse(hidden & {f["id"] for f in self.dev})
        with tempfile.TemporaryDirectory() as tmp:
            dev = ROOT / self.man["development"]["path"]
            with self.assertRaises(ValueError):
                c2.C2Verifier(dev, Path(tmp) / "a", cache_dir=None, engine="x", provenance={}, max_requests=1,
                              forbidden_ids={self.dev[0]["id"]})
            v = c2.C2Verifier(dev, Path(tmp) / "b", cache_dir=None, engine="x", provenance={}, max_requests=1,
                              forbidden_ids=hidden)
            self.assertFalse(set(v.by_id) & hidden)


def fin_classes():
    return (("rev_rot", 4), ("near_rev", 3), ("refl", 2), ("high_inv", 3), ("uniform", 2), ("easy", 1))


class Packet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = json.loads((C1 / "controls" / "b16-sweep16-development.json").read_text())
        cls.fams = {f["id"]: f for f in json.loads((C1 / "frozen" / "development.json").read_text())["families"]}

    def test_reversal_lines_and_no_hidden_ids(self):
        text = c2.packet_v2(self.res, self.fams, "screen none", "screen")
        self.assertTrue(text.startswith(c2.PACKET_MARK))
        self.assertLessEqual(len(text), c2.PACKET_MAX)
        self.assertIn("order class: ", text)
        self.assertIn("binding at gap-LP optimum: ", text)
        self.assertIn("crossing profile A=", text)
        cc, _ = c2.campaign()
        self.assertFalse(any(i in text for i in c2.forbidden_ids(cc)))
        self.assertNotIn("m11-", text)
        self.assertNotIn("m12-", text)

    def test_hint_and_binding(self):
        hint = ["h1", "h2", "h3"]
        self.assertTrue(c2.packet_v2(self.res, self.fams, "x", "screen", hint=hint).endswith("h1\nh2\nh3"))
        self.assertTrue(c2.reversal_orbit([2, 1, 9, 8, 7, 6, 5, 4, 3]))
        self.assertFalse(c2.reversal_orbit([1, 2, 3, 4, 5, 6, 7, 8, 9]))
        row = {"budget_unit": 52, "slope_bound": 7, "gap_lp": {"base": "53"},
               "trace": {"slopes": [{"j": 0, "gap_index": 2, "excess": "8/3"}, {"j": 1, "gap_index": 3,
                                                                              "excess": "-1/3"}]}}
        self.assertEqual(c2.binding(row), "slope j=0 (gap 2) +2.67; base pinned at T+1")


class SeedsAndCaps(unittest.TestCase):
    def test_seed_program(self):
        cc, _ = c2.campaign()
        src = (ROOT / cc["seed_program"]).read_text()
        self.assertEqual(_sha(ROOT / cc["seed_program"]), cc["seed_sha256"])
        c1 = (C1 / "finalists" / "sources" / "evox.py").read_text()
        self.assertTrue(hashlib.sha256(c1.encode()).hexdigest().startswith("1031149e"))
        a, b = ast.parse(src), ast.parse(c1)
        self.assertEqual(ast.dump(ast.Module(a.body[1:], [])), ast.dump(ast.Module(b.body[1:], [])))
        self.assertNotEqual(ast.get_docstring(a), ast.get_docstring(b))
        self.assertIsNone(E.source_guard(src))

    def test_seeds_set_per_engine(self):
        cc, bc = c2.campaign()
        self.assertEqual(cc["seeds"], [1, 2, 3])
        for seed in cc["seeds"]:
            self.assertEqual(c2.engine_knobs(cc, bc, "gepa", seed)["gepa"]["seed"], seed)
            for eng in ("adaevolve", "evox"):
                sky = c2.engine_knobs(cc, bc, eng, seed)["sky"]
                self.assertEqual(sky["search"]["database"]["random_seed"], seed)
                self.assertEqual(sky["search"]["type"], eng)
            self.assertEqual(c2.engine_knobs(cc, bc, "sequential", seed)["seed"], seed)
        evox = c2.engine_knobs(cc, bc, "evox", 1)["sky"]
        self.assertFalse(evox["search"]["database"]["auto_generate_variation_operators"])
        self.assertEqual(evox["search"]["switch_interval"], evox["max_iterations"] + 1)
        w = c2._parser().parse_args(["_gepa_worker", "--seed", "s", "--dataset", "d", "--run-dir", "r",
                                     "--broker-url", "b", "--verifier-url", "v", "--model", "m", "--max-tokens", "1",
                                     "--proposals", "1", "--llm-timeout", "1", "--eval-timeout", "1",
                                     "--gepa-seed", "3"])
        self.assertEqual(w.gepa_seed, 3)

    def test_pool_subcaps_and_ledgers(self):
        cc, bc = c2.campaign()
        self.assertEqual(c2.pool(bc), 360)
        caps = [cc["engines"][e]["max_requests"] for e in c2.ARMS]
        self.assertEqual(caps, [30] * 4)
        self.assertLessEqual(sum(caps) * len(cc["seeds"]), c2.pool(bc))
        self.assertEqual(c2.effective_iterations(cc, "gepa"), 30)
        paths = {c2.ledger_path(CAMP, bc, e, s) for e in c2.ARMS for s in cc["seeds"]}
        self.assertEqual(len(paths), 12)
        self.assertTrue(all(p.name.startswith("broker-ledger-bound-c2.") for p in paths))
        with tempfile.TemporaryDirectory() as tmp:
            bc2 = dict(bc, ledger=str(Path(tmp) / "broker-ledger-bound-c2.json"))
            Path(tmp, "broker-ledger-bound-c2.gepa-s1.json").write_text(json.dumps(
                {"attempts": [{"charged_usd": 0.01}] * 350}))
            b = c2.budget_for(CAMP, cc, bc2, "evox", 1)
            self.assertEqual((b["contacts"], b["max_usd"]), (10, 56.5))
            self.assertEqual(c2.budget_for(CAMP, cc, bc2, "gepa", 1)["contacts"], 30)

    def test_approval_material_covers_every_run(self):
        mat = c2.approval_material()
        self.assertEqual(len(mat["engine_knobs"]), 12)
        self.assertEqual(set(mat["first_prompts"]), {f"{e}/s{s}" for e in c2.ARMS for s in (1, 2, 3)})
        self.assertEqual(mat["data"]["seed_sha256"], mat["campaign_config"]["seed_sha256"])
        self.assertIn("validation.json", mat["data"]["c2_files"])


class Pool(unittest.TestCase):
    FID = "m9-mask246-labels765432198"

    @classmethod
    def setUpClass(cls):
        cls.fams = {f["id"]: f for f in json.loads((C1 / "frozen" / "development.json").read_text())["families"]}
        d = CAMP / "controls"
        cls.words = {n: {r["id"]: r for r in json.loads((d / f"{n}-development.json").read_text())["rows"]}
                     for n in ("gepa-c1", "seed-evox-c1")}

    def row(self, name):
        f = self.fams[self.FID]
        out = json.dumps({"words": self.words[name][self.FID]["output_words"]})
        return E.score_family(f, {"status": "ok"}, {"index": 0, "output_json": out, "cpu_seconds": 0, "seconds": 0})

    def test_pooled_gain_and_support(self):
        gepa, seed = self.row("gepa-c1"), self.row("seed-evox-c1")
        self.assertNotEqual(gepa["status"], "CERTIFIED")
        self.assertNotEqual(seed["status"], "CERTIFIED")
        with tempfile.TemporaryDirectory() as tmp:
            pool = c2.WordPool(Path(tmp) / "pool.json", self.fams)
            self.assertTrue(pool.add(gepa, "g" * 64))
            self.assertFalse(pool.add(gepa, "g" * 64))  # same costs: nothing new
            self.assertFalse(pool.certified(self.FID))
            g = pool.gain(seed)
            self.assertTrue(g["pooled"] and g["yours"] and g["others"])
            lines = c2.pool_lines([g], self.fams)
            self.assertIn("pool_gain 1", lines[0])
            self.assertIn("newly certifiable: " + self.FID, lines[1])
            pool.add(seed, "s" * 64)
            self.assertTrue(pool.certified(self.FID))
            pool.save()
            self.assertEqual(set(json.loads((Path(tmp) / "pool.json").read_text())["families"]), {self.FID})
            costs = [(e["B"], e["beta"]) for e in pool.entries[self.FID]]
            self.assertFalse(any(a != b and a[0] <= b[0] and all(x <= y for x, y in zip(a[1], b[1]))
                                 for a in costs for b in costs))

    def test_pool_refuses_hidden_families(self):
        cc, _ = c2.campaign()
        hidden = c2.forbidden_ids(cc)
        val = json.loads((CAMP / "frozen" / "validation.json").read_text())["families"][0]
        pool = c2.WordPool("/dev/null", dict(self.fams, **{val["id"]: val}), hidden)
        with self.assertRaises(ValueError):
            pool.add({"id": val["id"], "valid": True, "words": [], "output_words": []}, "x")
        with self.assertRaises(ValueError):
            c2.WordPool("/dev/null", self.fams).add({"id": "m11-nope", "valid": True}, "x")


class Selection(unittest.TestCase):
    def test_validation_only(self):
        val = {"a" * 64: {"certified": 100, "combined_score": 150.0},
               "b" * 64: {"certified": 120, "combined_score": 140.0},
               "c" * 64: {"certified": 120, "combined_score": 141.0}}
        self.assertEqual(fin.select_finalist(val), "c" * 64)
        val["c" * 64]["combined_score"] = 140.0
        self.assertEqual(fin.select_finalist(val), "b" * 64)  # full tie: smaller sha
        self.assertEqual(fin.select_finalist.__code__.co_argcount, 1)
        with self.assertRaises(ValueError):
            fin.select_finalist({})

    def test_accepted_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = Path(tmp) / "verified" / "evaluations"
            ev.mkdir(parents=True)
            srcs = {n: f"def certify(f):\n    return {n}\n" for n in ("seed", "full", "screen_only", "gepa")}
            h = {n: hashlib.sha256(s.encode()).hexdigest() for n, s in srcs.items()}
            for i, s in enumerate(srcs.values()):
                (ev / f"candidate-{i:04d}.py").write_text(s)
            man = {"seed_sha256": h["seed"], "verified_best_hash": h["full"],
                   "evaluation_trace": [{"candidate_hash": h["full"], "full": {"x": 1}},
                                        {"candidate_hash": h["screen_only"], "full": None}],
                   "mechanism_evidence": {"candidate_sha256": [h["gepa"]]}}
            got = fin.accepted_candidates(tmp, man)
            self.assertEqual(set(got), {h["seed"], h["full"], h["gepa"]})

    def test_stats(self):
        s = fin.stats([10.0, 20.0, 30.0])
        self.assertEqual((s["n"], s["mean"], s["min"], s["max"]), (3, 20.0, 10.0, 30.0))
        self.assertAlmostEqual(s["sd"], 10.0)
        self.assertIsNone(fin.stats([5.0])["sd"])


if __name__ == "__main__":
    unittest.main()
