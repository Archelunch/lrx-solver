"""Loop v3 for sort-m9 (integrations/sort_loop3.py, sort_loop3_finalize.py): offline, mock HTTP only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

from integrations import lift_backends as lb
from integrations import official_backends as ob
from integrations import sort_evaluator as E
from integrations import sort_loop3 as L
from integrations import sort_loop3_finalize as F
from integrations import sort_control_naive as naive
from src.lrx.certificates import replay_visible
from tests.test_search_sort_task import GEN, optimal, small_states, write_set

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "autoresearch" / "sort-m9-v3-260925"
VENV = ROOT / ".venv-official" / "bin" / "python"
SWEEP = ROOT / "integrations" / "sort_control_sweep.py"
NAIVE = ROOT / "integrations" / "sort_control_naive.py"
T42 = "22866c893796cbab703ea5b9e403e05ea86f9f171d67fad72a04cab63d166c65"


def configs():
    cc = json.loads((CAMP / "campaign-config.json").read_text())
    return cc, json.loads((CAMP / "broker-config.json").read_text()), \
        json.loads((CAMP / "broker-config-reflection.json").read_text())


def venv_json(script, payload):
    env = L.sky_worker_environment(Path(tempfile.gettempdir()), Path(tempfile.gettempdir()), "http://127.0.0.1:1/v1")
    env.pop("PYTHONPATH")
    out = subprocess.run([str(VENV), "-c", script], input=json.dumps(payload), capture_output=True, text=True,
                         cwd=ROOT, timeout=120, env=env)
    if out.returncode:
        raise AssertionError(out.stderr[-2000:])
    return json.loads(out.stdout.strip().splitlines()[-1])


def tables42():
    return E.Tables({(4, 2): (GEN / "dist_m4_r2.bin", T42)})


def scored(states, fn):
    rows = [E.score_state(s, {"status": "ok"}, {"word": fn(s["v"]), "seconds": 0, "cpu_seconds": 0}) for s in states]
    return dict(E.aggregate(rows), results=rows), rows


class Server:
    """Scripted JSON HTTP server: handler(path, body) -> (status, payload); records requests."""

    def __init__(self, handler):
        self.requests = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                outer.requests.append((self.path, body))
                status, payload = handler(self.path, body)
                raw = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *_a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def chat(content, finish="stop"):
    return 200, {"choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}]}


class FrozenInputsTest(unittest.TestCase):
    def test_instances_and_screen_on_the_frozen_development_set(self):
        man = json.loads((CAMP / "frozen-v3" / "manifest.json").read_text())
        dev = json.loads((ROOT / "autoresearch/sort-m9-260925/frozen/development.json").read_text())["states"]
        inst, screen = L.build_instances(dev), L.build_screen(dev)
        self.assertEqual((len(inst), {len(v) for v in inst.values()}), (30, {50}))
        self.assertEqual(sorted(i for v in inst.values() for i in v), sorted(s["id"] for s in dev))
        self.assertEqual(len(screen), 100)
        self.assertLessEqual(set(screen), {s["id"] for s in dev})
        radius = {s["id"] for s in dev if s["d"] == s["budget"]}
        self.assertEqual(len(radius), 15)
        self.assertLessEqual(radius, set(screen))
        for name, obj, key in (("instances.json", {"schema": "lrx-sort-instances-v1", "instances": inst},
                                "instances_sha256"),
                               ("screen-ids.json", {"schema": "lrx-sort-screen-v1", "ids": screen}, "screen_sha256")):
            self.assertEqual(L._sha((json.dumps(obj, indent=1) + "\n").encode()), man[key])
        got = L.load_frozen_v3(CAMP / "frozen-v3" / "manifest.json", man["development_sha256"])
        self.assertEqual(got, (inst, screen))
        with self.assertRaises(RuntimeError):
            L.load_frozen_v3(CAMP / "frozen-v3" / "manifest.json", "0" * 64)


class ScoreTest(unittest.TestCase):
    def test_instance_score_and_no_valid_state(self):
        states, _ = small_states(8)
        _, rows = scored(states, naive.sort_word)
        v = [r for r in rows if r["valid"]]
        want = sum(r["within"] for r in rows) / 8 + 0.25 / (1 + sum(r["excess"] for r in v) / len(v))
        self.assertAlmostEqual(L.instance_score(rows), want)
        _, bad = scored(states, lambda v: "")
        self.assertEqual(L.instance_score(bad), -1.0)

    def test_union_of_instance_rows_aggregates_to_the_full_evaluation(self):
        states, _ = small_states(12)
        with tempfile.TemporaryDirectory() as d:
            full = E.evaluate(SWEEP, states, require_os_sandbox=False, jobs=2)
            parts = [E.evaluate(SWEEP, states[:5], require_os_sandbox=False, jobs=2),
                     E.evaluate(SWEEP, states[5:], require_os_sandbox=False, jobs=2)]
        agg = E.aggregate(parts[1]["results"] + parts[0]["results"])
        for k in ("combined_score", "within_budget", "valid", "mean_excess", "per_r", "min_r_within_rate"):
            self.assertEqual(agg[k], full[k], k)

    def test_sky_metrics_are_floats_with_full_score_and_sentinel(self):
        states, _ = small_states(8)
        res, _ = scored(states, naive.sort_word)
        _, bad = scored(states, lambda v: "")
        for scope, r in (("screen", res), ("full", res), ("full", E.aggregate(bad))):
            m = L.sky_metrics(r, scope)
            self.assertTrue(all(type(v) is float for v in m.values()))
            self.assertIn("full_score", m)
            self.assertEqual(set(m), set(L.SKY_METRIC_KEYS[scope]))
        self.assertEqual(L.sky_metrics(res, "screen")["full_score"], -2.0)
        self.assertEqual(L.sky_metrics(E.aggregate(bad), "full")["neg_mean_excess"], -1000.0)


class KnobsTest(unittest.TestCase):
    def test_engine_knobs(self):
        cc, bc, rbc = configs()
        thr = cc["screen_threshold"]
        for seed in cc["seeds"]:
            g = L.engine_knobs(cc, "gepa", seed, bc, rbc)
            self.assertEqual((g["engine"]["seed"], g["engine"]["frontier_type"],
                              g["reflection"]["reflection_minibatch_size"]), (seed, "instance", 3))
            self.assertEqual(g["engine"]["max_metric_calls"], L.gepa_metric_calls(30, 3, 200))
            self.assertIsNone(g["merge"])
            for eng in ("adaevolve", "evox"):
                sky = L.engine_knobs(cc, eng, seed, bc, rbc)["sky"]
                db = sky["search"]["database"]
                self.assertEqual(db["random_seed"], seed)
                self.assertEqual(db["pareto_objectives"], ["within_rate", "worst_r_rate", "neg_mean_excess"])
                self.assertEqual(db["fitness_key"], "full_score")
                self.assertTrue(all(db["higher_is_better"].values()))
                self.assertEqual(sky["evaluator"], {"timeout": 900, "max_retries": 0, "cascade_evaluation": True,
                                                    "cascade_thresholds": [thr, thr],
                                                    "inject_evaluator_context": False})
                self.assertEqual(sky["max_parallel_iterations"], 1)
            evox = L.engine_knobs(cc, "evox", seed, bc, rbc)["sky"]
            self.assertEqual(evox["search"]["switch_interval"], 201)
            self.assertFalse(evox["search"]["database"]["auto_generate_variation_operators"])
            self.assertNotIn("guide_models", evox["llm"])
            self.assertTrue(lb.evox_strategy_evolution_enabled(200, False))  # why v3 never calls it
        with self.assertRaises(ValueError):
            L.sky_config_v3(dict(cc, evox_strategy_evolution=True), "evox", 1, bc, rbc)

    @unittest.skipUnless(VENV.exists(), "needs .venv-official")
    def test_sky_worker_environment_has_no_openai_base(self):
        env = L.sky_worker_environment(Path("/s"), Path("/r"), "http://127.0.0.1:1/v1")
        self.assertNotIn("OPENAI_API_BASE", env)
        self.assertNotIn("OPENAI_BASE_URL", env)
        self.assertEqual(env["OPENAI_API_KEY"], "local-broker")

    def test_configs_parse_in_the_pinned_engines(self):
        """load_config as the Sky CLI runs it, in the Sky worker environment (no OPENAI_API_BASE)."""
        cc, bc, rbc = configs()
        script = ("import json, os, sys, tempfile\nfrom skydiscover.optimize.config import load_config\n"
                  "from gepa.optimize_anything import EngineConfig, ReflectionConfig\n"
                  "p = json.load(sys.stdin)\nout = {}\n"
                  "for name, sky in p['sky'].items():\n"
                  "    path = os.path.join(tempfile.mkdtemp(), 'c.yaml')\n"
                  "    open(path, 'w').write(json.dumps(sky))\n"
                  "    c = load_config(path)\n"
                  "    db = c.search.database\n"
                  "    out[name] = {'seed': db.random_seed, 'fitness': db.fitness_key, 'pareto': db.pareto_objectives,"
                  " 'inject': c.evaluator.inject_evaluator_context, 'cascade': c.evaluator.cascade_evaluation,"
                  " 'thr': c.evaluator.cascade_thresholds, 'guide': [m.api_base for m in c.llm.guide_models],"
                  " 'models': [m.api_base for m in c.llm.models], 'switch': c.search.switch_interval}\n"
                  "e = EngineConfig(**p['gepa']['engine']); r = ReflectionConfig(reflection_lm=None, **p['gepa']['reflection'])\n"
                  "out['gepa'] = [e.seed, e.frontier_type, r.reflection_minibatch_size, e.cache_evaluation]\n"
                  "print(json.dumps(out))\n")
        payload = {"sky": {e: L.engine_knobs(cc, e, 2, bc, rbc)["sky"] for e in ("adaevolve", "evox")},
                   "gepa": L.engine_knobs(cc, "gepa", 2, bc, rbc)}
        got = venv_json(script, payload)
        flash, refl = f"http://127.0.0.1:{cc['broker_port']}/v1", f"http://127.0.0.1:{cc['reflection']['broker_port']}/v1"
        self.assertEqual(got["adaevolve"]["guide"], [refl])
        self.assertEqual(got["adaevolve"]["models"], [flash])
        self.assertEqual(got["evox"]["guide"], [flash])  # EvoX: no guide model, falls back to flash
        for e in ("adaevolve", "evox"):
            self.assertEqual((got[e]["seed"], got[e]["fitness"], got[e]["inject"], got[e]["cascade"]),
                             (2, "full_score", False, True))
        self.assertEqual(got["evox"]["switch"], 201)
        self.assertEqual(got["gepa"], [2, "instance", 3, False])  # parent minibatch re-evaluated


def load_stub(url, timeout=5):
    """Import the rendered evaluator stub with a stand-in EvaluationResult (records metrics/artifacts)."""
    fake = types.ModuleType("skydiscover.optimize.evaluation.evaluation_result")

    class EvaluationResult:
        def __init__(self, metrics, artifacts=None):
            self.metrics, self.artifacts = metrics, artifacts or {}
    fake.EvaluationResult = EvaluationResult
    names = ["skydiscover", "skydiscover.optimize", "skydiscover.optimize.evaluation"]
    patch = {n: types.ModuleType(n) for n in names}
    patch[fake.__name__] = fake
    with tempfile.TemporaryDirectory() as d, mock.patch.dict(sys.modules, patch):
        path = Path(d) / "evaluator.py"
        path.write_text(L.sky_evaluator_source(url, timeout))
        spec = importlib.util.spec_from_file_location("stub_eval", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


class SkyStubTest(unittest.TestCase):
    def test_stage_metrics_failure_and_proxy(self):
        states, _ = small_states(8)
        res, _ = scored(states, naive.sort_word)
        _, bad = scored(states, lambda v: "")
        outputs = {"screen": L.sky_metrics(res, "screen"), "full": L.sky_metrics(E.aggregate(bad), "full")}
        fail = {"on": False}

        def handler(path, body):
            if fail["on"]:
                return 429, {"error": "full evaluation budget exhausted"}
            return 200, {"metrics": outputs[body["scope"]], "artifacts": {"feedback": "x", "worst_states": "y"}}
        srv = Server(handler)
        try:
            stub = load_stub(srv.url)
            with tempfile.TemporaryDirectory() as d:
                prog = Path(d) / "p.py"
                prog.write_text("def sort_word(v):\n    return ''\n")
                s1, s2 = stub.evaluate_stage1(str(prog)), stub.evaluate_stage2(str(prog))
                fail["on"] = True
                f = stub.evaluate(str(prog))
        finally:
            srv.close()
        self.assertEqual([b["scope"] for _, b in srv.requests], ["screen", "full", "full"])
        self.assertEqual((s1.metrics["stage"], s1.metrics["full_score"]), (1.0, -2.0))
        self.assertEqual(s2.metrics["neg_mean_excess"], -1000.0)
        self.assertEqual(f.metrics, {"full_score": -2.0, "combined_score": -2.0, "stage": 0.0})
        self.assertIn("evaluation failed", f.artifacts["feedback"])
        self.assertIn("worst_states", s1.artifacts)
        for r in (s1, s2, f):
            self.assertTrue(all(type(v) is float for v in r.metrics.values()))
        self.assertNotIn("frozen", L.sky_evaluator_source("http://x", 1))
        if VENV.exists():
            cc, _, _ = configs()
            db = L.sky_config_v3(cc, "adaevolve", 1, configs()[1], configs()[2])["search"]["database"]
            merged = dict(s1.metrics, **s2.metrics)  # SkyDiscover cascade merge {**stage1, **stage2}
            got = venv_json("import json, sys\nfrom skydiscover.optimize.utils.metrics import compute_proxy_score\n"
                            "p = json.load(sys.stdin)\nprint(json.dumps([compute_proxy_score(m, fitness_key=p['k'], "
                            "pareto_objectives=p['o'], higher_is_better=p['h']) for m in p['m']]))",
                            {"k": db["fitness_key"], "o": db["pareto_objectives"], "h": db["higher_is_better"],
                             "m": [s1.metrics, merged, f.metrics]})
            self.assertEqual(got, [-2.0, merged["full_score"], -2.0])


class WordsAndPacketTest(unittest.TestCase):
    def test_optimal_divergence_and_aligned_word(self):
        states, t = small_states(12)
        tables = tables42()
        for s in states:
            w = L.optimal_word(tables, s["v"])
            self.assertEqual(len(w), s["d"])
            self.assertEqual(replay_visible(tuple(s["v"]), w), E.root(4, 2))
            self.assertIsNone(L.divergence(tables, s, w))
        s = states[-1]
        for word in ("XX" + optimal(t, s["v"]), naive.sort_word(s["v"])):
            div = L.divergence(tables, s, word)
            trace = tables.prefix_trace(s, word)["first_off_shortest_path"]
            self.assertEqual(div["step"], trace["step"])
            aligned = L.aligned_optimal(tables, s["v"], word, div["step"])
            self.assertEqual(len(aligned), s["d"])
            self.assertEqual(aligned[:div["step"] - 1], word[:div["step"] - 1])
            self.assertEqual(replay_visible(tuple(s["v"]), aligned), E.root(4, 2))

    def test_packet_caps_elision_seed_line_and_reveal_cap(self):
        states, _ = small_states(12)
        res, rows = scored(states, naive.sort_word)
        rows[0] = E.score_state(states[0], {"status": "ok"}, {"word": "L" * 400, "seconds": 0, "cpu_seconds": 0})
        rows[1] = E.score_state(states[1], {"status": "ok"}, {"word": "L", "seconds": 0, "cpu_seconds": 0})
        res = dict(E.aggregate(rows), results=rows)
        seed, _ = scored(states, lambda v: optimal(small_states(12)[1], v))
        reveal = L.Reveal(1)
        art = L.packet_v2(res, rows, "none", {s["id"]: s for s in states}, tables42(), seed, reveal, "full")
        text = "\n".join(art.values())
        self.assertTrue(art["feedback"].startswith(L.PACKET_MARK))
        self.assertTrue(all(len(v) <= L.KEY_MAX for v in art.values()))
        self.assertIn("seed per (m,r)", art["feedback"])
        self.assertLessEqual(text.count("\n- "), L.WORST_N)
        self.assertIn("(len 400)", text)
        self.assertNotIn("L" * 161, text)
        self.assertEqual(len(reveal.ids), 1)
        self.assertIn("withheld (reveal cap)", text)
        head, blocks = L.packet_parts(res, rows * 30, "none", {s["id"]: s for s in states}, None, seed, L.Reveal(0),
                                      "full")
        self.assertLessEqual(len(L.packet_text(head, blocks, L.INSTANCE_MAX)), L.INSTANCE_MAX)
        self.assertEqual(L.Withhold().allow("x"), False)

    def test_no_holdout_id_or_vector_in_packets(self):
        states, _ = small_states(12)
        dev, hold = states[:8], states[8:]
        with tempfile.TemporaryDirectory() as d:
            v = L.SortVerifierV3(write_set(d, dev), Path(d) / "run", cache_dir=None, engine="t",
                                 instances={"a": [s["id"] for s in dev[:4]], "b": [s["id"] for s in dev[4:]]},
                                 screen_ids=[s["id"] for s in dev[:3]], budgets={}, reveal_cap=50, jobs=2,
                                 require_os_sandbox=False, tables=tables42())
            v.evaluate(NAIVE.read_text(), "full", final=True)
            out = [v.evaluate(NAIVE.read_text(), "screen"), v.evaluate(NAIVE.read_text(), "full")]
            inst = v.evaluate_instances(NAIVE.read_text(), ["a", "b"])
            blob = json.dumps(out) + json.dumps(inst)
            for s in hold:
                self.assertNotIn(s["id"], blob)
            with self.assertRaises(ValueError):
                L.SortVerifierV3(write_set(d, dev, "holdout"), Path(d) / "run2", cache_dir=None, engine="t",
                                 instances={"a": [s["id"] for s in dev]}, screen_ids=[], budgets={}, reveal_cap=1,
                                 require_os_sandbox=False)


class VerifierTest(unittest.TestCase):
    def test_budgets_cache_reuse_and_full_rows(self):
        states, _ = small_states(12)
        ids = [s["id"] for s in states]
        with tempfile.TemporaryDirectory() as d:
            v = L.SortVerifierV3(write_set(d, states), Path(d) / "run", cache_dir=Path(d) / "cache", engine="t",
                                 instances={"a": ids[:4], "b": ids[4:8], "c": ids[8:]}, screen_ids=ids[:3],
                                 budgets={"max_screen_evals": 1, "max_full_evals": 1, "max_state_evals": 24},
                                 reveal_cap=5, jobs=2, require_os_sandbox=False, tables=tables42())
            seed = v.evaluate(SWEEP.read_text(), "full", final=True, use_cache=False)
            self.assertEqual(v.used["states"], 12)
            v.evaluate(NAIVE.read_text(), "screen")
            with self.assertRaises(PermissionError):
                v.evaluate(NAIVE.read_text(), "screen")
            part = v.evaluate_instances(NAIVE.read_text(), ["a", "b"])
            self.assertEqual(part["scope"], "instances")
            used = v.used["states"]
            again = v.evaluate_instances(NAIVE.read_text(), ["a", "b", "c"])
            self.assertEqual(v.used["states"], used + 4)  # a, b are cache hits; only c runs
            self.assertEqual(again["scope"], "full")
            self.assertIn("full", again)
            self.assertEqual([r["scope"] for r in v.state["evaluations"]], ["full", "screen", "instances", "full"])
            self.assertEqual(v.best_full()["candidate_hash"], seed["candidate_hash"])
            side = again["results"][0]["side_info"]
            self.assertLessEqual(len(side["feedback"]), L.INSTANCE_MAX)
            self.assertEqual(side["seed_within"], v.seed_instance["a"]["within_budget"])
            with self.assertRaises(PermissionError):  # state cap reached (12 + 8 + 4 = 24)
                v.evaluate_instances(SWEEP.read_text(), ["a"])
            srv, url = v.serve()
            try:
                with self.assertRaises(Exception) as ctx:
                    L._post(url + "/evaluate", {"source": SWEEP.read_text(), "scope": "full"}, 30)
                self.assertEqual(getattr(ctx.exception, "code", None), 429)
            finally:
                srv.shutdown()
                srv.server_close()


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.order = []
        self.diag_status = 200

        def diag(path, body):
            self.order.append("diagnosis")
            if self.diag_status != 200:
                return self.diag_status, {"error": "stop"}
            return chat("Rotate first.\n```python\nimport os\n```\nThen sweep.")

        def write(path, body):
            self.order.append("write")
            return chat("```python\ndef sort_word(v):\n    return ''\n```")
        self.d, self.w = Server(diag), Server(write)

    def tearDown(self):
        self.d.close()
        self.w.close()

    def lm(self, **kw):
        return L.make_lm(self.w.url, "flash", 100, 10, None, reflection_url=self.d.url, reflection_model="pro",
                         reflection_max_tokens=50, reflection_timeout=10, **kw)

    def test_order_strip_and_placeholder_guard(self):
        msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "U SORT_PACKET_V2"}]
        sol = lb.messages_sha256(L.with_diagnosis(msgs, L.DIAGNOSIS_PLACEHOLDER))
        dia = lb.messages_sha256(L.diagnosis_messages(msgs))
        lm = self.lm(expected=sol, expected_diagnosis=dia)
        out = lm(msgs)
        self.assertIn("def sort_word", out)
        self.assertEqual(self.order, ["diagnosis", "write"])
        sent = self.w.requests[0][1]["messages"]
        self.assertIn(L.DIAGNOSIS_APPEND + "Rotate first.\n[code removed]\nThen sweep.", sent[-1]["content"])
        self.assertNotIn("import os", json.dumps(sent))
        self.assertEqual(self.d.requests[0][1]["messages"][0]["content"], L.REFLECT_SYSTEM)
        self.assertEqual(lb.messages_sha256(L.guard_view(sent)), sol)
        self.assertEqual(lm.writer.receipts[0]["packet_seen"], True)

    def test_guard_mismatch_halts_before_any_call(self):
        msgs = [{"role": "user", "content": "U"}]
        with self.assertRaises(L.FirstPromptMismatch):
            self.lm(expected_diagnosis="0" * 64)(msgs)
        self.assertEqual(self.order, [])
        with self.assertRaises(L.FirstPromptMismatch):
            self.lm(expected="0" * 64)(msgs)
        self.assertEqual(self.order, ["diagnosis"])

    def test_reflection_429_and_5xx_halt(self):
        for code in (429, 500):
            self.diag_status = code
            with self.assertRaises(ob.BrokerHalted):
                self.lm()([{"role": "user", "content": "U"}])
        self.assertNotIn("write", self.order)


class ApprovalTest(unittest.TestCase):
    def camp_copy(self, d):
        camp = Path(d) / "camp"
        shutil.copytree(CAMP / "frozen-v3", camp / "frozen-v3")
        for name in ("broker-config.json", "broker-config-reflection.json", "campaign-config.json",
                     "first-prompt-gepa-s1.sha256"):
            shutil.copyfile(CAMP / name, camp / name)
        cc = json.loads((camp / "campaign-config.json").read_text())
        cc["frozen_v3_manifest"] = str(camp / "frozen-v3" / "manifest.json")
        (camp / "campaign-config.json").write_text(json.dumps(cc))
        return camp

    def test_hash_covers_configs_data_prompts_and_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            camp = self.camp_copy(d)
            material = L.approval_material_v3(camp)
            self.assertIn("research_budget", material["code_sha256"])
            self.assertEqual(set(material["engine_knobs"]), {f"{a}/s{s}" for a in L.ARMS for s in (1, 2, 3)})
            self.assertIn("reflection", material["brokers"])
            base = L.approval_hash_v3(camp)
            self.assertEqual(base, L.approval_hash_v3(camp))

            def changed(path, edit):
                old = path.read_bytes()
                edit(path)
                try:
                    return L.approval_hash_v3(camp)
                finally:
                    path.write_bytes(old)

            def jedit(key, value):
                def f(p):
                    obj = json.loads(p.read_text())
                    obj[key] = value
                    p.write_text(json.dumps(obj))
                return f
            for path, edit in ((camp / "campaign-config.json", jedit("screen_threshold", 1.2)),
                               (camp / "campaign-config.json", jedit("reveal_optimal_max_states", 301)),
                               (camp / "broker-config-reflection.json", jedit("model", "other")),
                               (camp / "frozen-v3" / "instances.json", lambda p: p.write_text(p.read_text() + " ")),
                               (camp / "frozen-v3" / "screen-ids.json", lambda p: p.write_text(p.read_text() + " ")),
                               (camp / "first-prompt-gepa-s1.sha256", lambda p: p.write_text("f" * 64))):
                self.assertNotEqual(changed(path, edit), base, path.name)
            with self.assertRaises(SystemExit):
                L.check_approval_v3(camp)
            (camp / "payload-approved.sha256").write_text("0" * 64 + "\n")
            with self.assertRaises(SystemExit):
                L.check_approval_v3(camp)
            (camp / "payload-approved.sha256").write_text(base + "\n")
            self.assertEqual(L.check_approval_v3(camp), base)
            bc = json.loads((camp / "broker-config.json").read_text())
            (camp / "broker-config.json").write_text(json.dumps(dict(bc, dry_run_payload_sha256="0" * 64)))
            (camp / "payload-approved.sha256").write_text(L.approval_hash_v3(camp) + "\n")
            with self.assertRaises(SystemExit):
                L.check_approval_v3(camp)


class EvoxLeakTest(unittest.TestCase):
    def test_meta_request_is_a_leak(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "ledger.json"
            self.assertIsNotNone(L.evox_leak(ledger, {}))  # nothing to verify
            rec = Path(str(ledger) + ".receipts")
            rec.mkdir()
            sol = {"request_payload": {"messages": [{"role": "user", "content": "improve sort_word"}]}}
            (rec / "attempt-0001.json").write_text(json.dumps(sol))
            self.assertIsNone(L.evox_leak(ledger, {"generated_strategy_artifacts": []}))
            self.assertIsNotNone(L.evox_leak(ledger, {"generated_strategy_artifacts": ["x/code.py"]}))
            meta = {"request_payload": {"messages": [{"role": "user", "content":
                                                      "Write an EvolvedProgramDatabase search algorithm"}]}}
            (rec / "attempt-0002.json").write_text(json.dumps(meta))
            self.assertIn("strategy", L.evox_leak(ledger, {"generated_strategy_artifacts": []}))


class FinalizeTest(unittest.TestCase):
    def build(self, d):
        states, _ = small_states(12)
        frozen = Path(d) / "frozen"
        frozen.mkdir()
        dev = write_set(frozen, states[:8])
        hold = write_set(frozen, states[8:], "holdout")
        (frozen / "manifest.json").write_text(json.dumps({
            "files": {"development.json": L._sha(dev.read_bytes()), "holdout.json": L._sha(hold.read_bytes())},
            "tables": [{"m": 4, "r": 2, "path": "datasets/generated/dist_m4_r2.bin", "table_sha256": T42}]}))
        camp = Path(d) / "camp"
        camp.mkdir()
        runs = [("gepa", 1, "COMPLETE", SWEEP, "a"), ("gepa", 1, "COMPLETE", NAIVE, "b"),
                ("gepa", 2, "COMPLETE", NAIVE, "a"), ("gepa", 3, "COMPLETE", SWEEP, "a"),
                ("sequential", 1, "COMPLETE", NAIVE, "a"), ("sequential", 2, "COMPLETE", SWEEP, "a"),
                ("sequential", 3, "BROKER_STOPPED", NAIVE, "a"), ("sequential", 3, "COMPLETE", NAIVE, "b")]
        for arm, seed, status, src, tag in runs:
            run = camp / f"live-v3-{arm}-s{seed}-{tag}"
            (run / "verified").mkdir(parents=True)
            shutil.copyfile(src, run / "verified" / "best.py")
            m = {"engine": arm, "seed": seed, "status": status, "verified_best_hash": L._sha(src.read_bytes()),
                 "revealed_ids": [states[0]["id"], states[1]["id"]], "mechanism_evidence": {"accepted_steps": [1]}}
            if status == "COMPLETE":
                m["verified_best_result"] = {"combined_score": 1.0}
            (run / "manifest.json").write_text(json.dumps(m))
        return camp, frozen / "manifest.json", states

    def test_per_arm_spread_once_only_holdout_exclusions_and_gap(self):
        with tempfile.TemporaryDirectory() as d:
            camp, fm, states = self.build(d)
            calls = []
            real = E.evaluate

            def counting(src, sts, **kw):
                calls.append((Path(src).name, sts[0]["id"]))
                return real(src, sts, **kw)
            with mock.patch.object(E, "evaluate", side_effect=counting):
                s = F.finalize(camp, frozen_manifest=fm, naive=NAIVE, sweep=SWEEP, jobs=2, sandbox=False)
                n_first = len(calls)
                s2 = F.finalize(camp, frozen_manifest=fm, naive=NAIVE, sweep=SWEEP, jobs=2, sandbox=False)
            self.assertEqual(len(calls), n_first)  # second call reuses the hash-checked results
            holdout_first = [c for c in calls if c[1] == states[8]["id"]]
            self.assertEqual(len(holdout_first), 8)  # 6 finalists + 2 controls, once each
            self.assertEqual(s["per_arm"], s2["per_arm"])
            g = s["per_arm"]["gepa"]["holdout_within"]
            vals = [s["rows"][f"gepa-s{k}"]["holdout_within"] for k in (1, 2, 3)]
            self.assertEqual((g["n"], g["min"], g["max"]), (3, min(vals), max(vals)))
            self.assertAlmostEqual(g["mean"], sum(vals) / 3)
            sweep_h, naive_h = s["rows"]["sweep-control"]["holdout_within"], s["rows"]["naive-control"]["holdout_within"]
            self.assertEqual(s["rows"]["gepa-s1"]["holdout_within"], sweep_h)  # first run (tag a), not the other
            reasons = sorted(e["reason"] for e in s["excluded"])
            self.assertEqual(len(reasons), 2)
            self.assertTrue(any("BROKER_STOPPED" in r for r in reasons))
            self.assertEqual(s["rows"]["sequential-s3"]["holdout_within"], naive_h)
            gap = s["rows"]["gepa-s1"]["memorization"]
            self.assertEqual((gap["revealed_states"], gap["unrevealed_states"]), (2, 6))
            self.assertIsNotNone(gap["gap"])
            self.assertIn(1, s["paired_vs_sequential"]["gepa"])
            self.assertTrue(all(v == (8, 0) or v[1] == 0 for v in s["audit"]["holdout"].values()))
            self.assertIn("consistent in k of k", (camp / "finalists" / "REPORT.md").read_text())

    def test_spread_and_gap_helpers(self):
        self.assertEqual(F.spread([1, 2, 3])["sd"], 1.0)
        self.assertEqual(F.spread([None])["n"], 0)
        rows = [{"id": "a", "within": True}, {"id": "b", "within": False}]
        g = F.memorization_gap(rows, ["a"])
        self.assertEqual((g["gap"], g["flag"]), (1.0, True))


if __name__ == "__main__":
    unittest.main()
