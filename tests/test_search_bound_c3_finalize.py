"""Tests for bound-m campaign 3 finalize (integrations/bound_c3_finalize.py). No provider calls,
no ports; every set and run directory is a tiny synthetic fixture built in a temp directory, and
`target_m12_families` is stubbed for the end-to-end test (its own logic is tested separately)."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from integrations import bound_c3_finalize as fin
from integrations.bound_task import SCHEMA, make_family

SRC_GOOD = 'def certify(family):\n    return {"words": [""]}\n'          # certifies an already-sorted family
SRC_BAD = 'def certify(family):\n    return {"words": ["L"]}\n'          # breaks an already-sorted family


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _family_set(fams, set_name, screen=None):
    out = {"schema": SCHEMA, "set": set_name, "families": fams}
    if screen is not None:
        out["screen"] = screen
    return json.dumps(out)


class Fixture:
    """Builds one tiny offline campaign-3 tree (c3 config + c2 frozen files + two live runs)."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        # trailing-gap identity families: base is already target-sorted, so word "" certifies them.
        self.f9 = make_family(list(range(1, 10)), 1 << 9)      # development, m=9
        self.f11 = make_family(list(range(1, 12)), 1 << 11)    # validation, m=11
        self.f12 = make_family(list(range(1, 13)), 1 << 12)    # holdout, m=12 (the "target" family)
        self.f11b = make_family(list(range(1, 12)), 1)          # holdout, fresh m=11 (leading gap: "" misses)

        c2dir = tmp / "c2-frozen"
        c2dir.mkdir()
        c1dir = tmp / "c1-frozen"
        c1dir.mkdir()
        dev_text = _family_set([self.f9], "development", screen=[self.f9["id"]])
        (c1dir / "development.json").write_text(dev_text)
        (c1dir / "c1-manifest.json").write_text("{}")
        val_text = _family_set([self.f11], "holdout")
        hold_text = _family_set([self.f12, self.f11b], "holdout")
        (c2dir / "validation.json").write_text(val_text)
        (c2dir / "holdout.json").write_text(hold_text)
        man = {"development": {"path": str(c1dir / "development.json"), "sha256": _sha(dev_text),
                                "c1_manifest": str(c1dir / "c1-manifest.json"), "c1_manifest_sha256": _sha("{}")},
               "files": {"validation.json": _sha(val_text), "holdout.json": _sha(hold_text)}}
        (c2dir / "manifest.json").write_text(json.dumps(man))
        self.man_path = c2dir / "manifest.json"

        controls_dir = tmp / "controls"
        controls_dir.mkdir()
        (controls_dir / "seed-c3.py").write_text(SRC_GOOD)
        (controls_dir / "adaevolve-s2-one-leaf.py").write_text(SRC_BAD)

        cache_dir = tmp / "eval-cache"
        self.cc = {"frozen_manifest": str(self.man_path), "eval_cache": str(cache_dir),
                   "controls": {"seed_c3": str(controls_dir / "seed-c3.py"),
                                "adaevolve_s2_one_leaf": str(controls_dir / "adaevolve-s2-one-leaf.py")}}
        (tmp / "campaign-config-c3.json").write_text(json.dumps(self.cc))

        self._live("adaevolve", 1, seed_src=SRC_BAD, best_src=SRC_GOOD)  # engine improves on its seed
        self._live("evox", 1, seed_src=SRC_GOOD, best_src=SRC_GOOD)      # engine keeps the seed (finalist is seed)

    def _live(self, engine, seed, seed_src, best_src):
        run_dir = self.tmp / f"live-{engine}-s{seed}-000000"
        ev = run_dir / "verified" / "evaluations"
        ev.mkdir(parents=True)
        (ev / "candidate-0001.py").write_text(best_src)
        (ev / "candidate-0002.py").write_text(seed_src)
        (run_dir / "verified" / "best.py").write_text(best_src)
        manifest = {"engine": engine, "seed": seed, "status": "COMPLETE", "seed_sha256": _sha(seed_src),
                    "verified_best_hash": _sha(best_src),
                    "evaluation_trace": [{"candidate_hash": _sha(best_src), "full": {"combined_score": 1.0}}],
                    "mechanism_evidence": {}}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

    def args(self, run_dir):
        import argparse
        return argparse.Namespace(run_dir=run_dir, jobs=1)


class Finalize(unittest.TestCase):
    def test_end_to_end_offline(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            fx = Fixture(tmp)
            target_ids = [fx.f12["id"]] + [f"dummy-target-{i}" for i in range(13)]
            self.assertEqual(len(target_ids), 14)
            with mock.patch.object(fin, "target_m12_families", return_value=target_ids):
                out = fin.finalize(fx.args(tmp))
            # selection: adaevolve's finalist beat its seed; evox kept its seed
            selection = json.loads((tmp / "finalists" / "selection.json").read_text())
            self.assertFalse(selection["adaevolve-s1"]["finalist_is_seed"])
            self.assertTrue(selection["evox-s1"]["finalist_is_seed"])
            self.assertEqual(selection["adaevolve-s1"]["finalist"], _sha(SRC_GOOD))
            # frozen finalist sources exist and match the manifest
            man = json.loads((tmp / "finalists" / "manifest.json").read_text())
            self.assertEqual(set(man["frozen_sources"]), {"adaevolve-s1", "evox-s1"})
            self.assertEqual(man["target_families"], target_ids)
            for k in man["frozen_sources"]:
                self.assertTrue((tmp / "finalists" / "sources" / f"{k}.py").is_file())
            # results.json: the good source certifies development, validation and the target family
            results = json.loads((tmp / "finalists" / "results.json").read_text())
            rows = results["summary"]["rows"]
            self.assertEqual(rows["adaevolve-s1"]["dev_pct"], 100.0)
            self.assertEqual(rows["adaevolve-s1"]["validation_pct"], 100.0)
            self.assertEqual(rows["adaevolve-s1"]["holdout_m12_pct"], 100.0)
            self.assertEqual(rows["adaevolve-s1"]["target_certified"], 1)
            self.assertIsNotNone(rows["adaevolve-s1"]["deterministic"])
            self.assertTrue(rows["adaevolve-s1"]["deterministic"])
            # revtree-b never touches validation/holdout
            self.assertNotIn("revtree-b", results["summary"]["rows"])
            self.assertNotIn("revtree-b", results["audit"]["validation"])
            self.assertNotIn("revtree-b", results["audit"]["holdout"])
            # a control key is present and never re-evaluated on the holdout
            self.assertIn("seed-c3", rows)
            self.assertEqual(rows["seed-c3"]["holdout_m12_pct"], 100.0)  # SRC_GOOD control
            self.assertEqual(rows["adaevolve-s2-one-leaf"]["holdout_m12_pct"], 0.0)  # SRC_BAD control
            self.assertTrue((tmp / "finalists" / "REPORT.md").is_file())
            self.assertIn("bound-m-c3-260926 finalists", (tmp / "finalists" / "REPORT.md").read_text())
            # per-arm success rule surfaced
            self.assertIn("adaevolve", out["per_arm"])
            self.assertIn("evox", out["per_arm"])
            self.assertEqual(out["success"], results["summary"]["success"])

            # rerun is idempotent: the frozen manifest and journaled holdout are not touched again
            before = (tmp / "finalists" / "holdout-arms" / "adaevolve-s1.json").read_text()
            with mock.patch.object(fin, "target_m12_families", return_value=target_ids):
                fin.finalize(fx.args(tmp))  # rerun: frozen manifest and journaled holdout must not change
            after = (tmp / "finalists" / "holdout-arms" / "adaevolve-s1.json").read_text()
            self.assertEqual(before, after)

    def test_holdout_one_shot_guard_refuses_unfinished_marker(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            fx = Fixture(tmp)
            target_ids = [f"dummy-target-{i}" for i in range(14)]
            journal = tmp / "finalists" / "holdout-arms"
            journal.mkdir(parents=True)
            (journal / "adaevolve-s1.started").write_text("2026-01-01T00:00:00Z\n")
            with mock.patch.object(fin, "target_m12_families", return_value=target_ids):
                with self.assertRaises(SystemExit) as ctx:
                    fin.finalize(fx.args(tmp))
            self.assertIn("not rerunning it", str(ctx.exception))

    def test_target_family_count_mismatch_aborts(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            fx = Fixture(tmp)
            with mock.patch.object(fin, "target_m12_families", return_value=["only-one"]):
                with self.assertRaises(SystemExit) as ctx:
                    fin.finalize(fx.args(tmp))
            self.assertIn("expected 14", str(ctx.exception))


class TargetFamilies(unittest.TestCase):
    def test_recomputed_as_intersection_of_missed_m12_ids(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d)
            holdout_arms = camp / "finalists" / "holdout-arms"
            holdout_arms.mkdir(parents=True)
            rows = {
                "adaevolve-s2": [{"id": "a", "m": 12, "status": "CERTIFIED"}, {"id": "b", "m": 12, "status": "NO_CERTIFICATE"}],
                "evox-s3": [{"id": "a", "m": 12, "status": "NO_CERTIFICATE"}, {"id": "b", "m": 12, "status": "NO_CERTIFICATE"}],
                "seed-evox-c1": [{"id": "a", "m": 12, "status": "NO_CERTIFICATE"}, {"id": "b", "m": 12, "status": "CERTIFIED"}],
                "sweeplp-b": [{"id": "a", "m": 12, "status": "NO_CERTIFICATE"}, {"id": "b", "m": 12, "status": "NO_CERTIFICATE"}],
            }
            for arm, r in rows.items():
                (holdout_arms / f"{arm}.json").write_text(json.dumps({"arm": arm, "result": {"rows": r}}))
            # "a" is missed only by evox-s3 and sweeplp-b (adaevolve-s2 certifies it) -> not a target
            # "b" is missed by adaevolve-s2, evox-s3, sweeplp-b but certified by seed-evox-c1 -> not a target
            got = fin.target_m12_families(c2_camp=camp)
            self.assertEqual(got, [])

    def test_family_missed_by_all_four_is_a_target(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d)
            holdout_arms = camp / "finalists" / "holdout-arms"
            holdout_arms.mkdir(parents=True)
            for arm in fin.TARGET_ARMS:
                rows = [{"id": "z", "m": 12, "status": "NO_CERTIFICATE"}, {"id": "y", "m": 11, "status": "CERTIFIED"}]
                (holdout_arms / f"{arm}.json").write_text(json.dumps({"arm": arm, "result": {"rows": rows}}))
            got = fin.target_m12_families(c2_camp=camp)
            self.assertEqual(got, ["z"])  # "y" is m=11, never a candidate target


if __name__ == "__main__":
    unittest.main()
