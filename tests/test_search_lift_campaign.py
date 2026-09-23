"""Construction search stays data-only, replayed, bounded and train-only."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from integrations.lift_policy import Policy, PolicyEvaluator, baseline, construct, move, ROOT
from integrations.lift_campaign import LiftCampaign, PolicyProposer, ResearchContext
from src.lrx.evolve import EVOX_START
from src.lrx.certificates import replay_visible

CONTEXT=ROOT/'autoresearch/loop-260923-2107/context-v1.json'
CASE=dict(id='root',family='m8r3',m=8,r=3,v=list(range(1,9))+[0]*3,q=43,bound=48)

class LiftPolicyTests(unittest.TestCase):
    def test_schema_and_semantic_identity(self):
        p=baseline()
        self.assertEqual(Policy(p).hash,Policy(dict(p,name='renamed')).hash)
        bad=[dict(p,code='print(1)'),dict(p,zero_order='by_vector')]
        for key,value in [('period',True),('detour_steps',[[1]]),('orders',['LX']),('axis','vector')]:
            b=copy.deepcopy(p);b['paths'][0][key]=value;bad.append(b)
        for b in bad:
            with self.assertRaises(ValueError):Policy(b)

    def test_construct_budget_and_replay(self):
        evaluator=PolicyEvaluator([CASE]);table=evaluator.table(8,3)
        root=tuple(CASE['v'][:-1]);u=move(root,'L');path=baseline()['paths'][0]
        word,events=construct(table,u,path,1)
        self.assertEqual(replay_visible(u,word),root);self.assertFalse(events)
        self.assertIsNone(construct(table,u,path,0))
        path=dict(path,detour='uphill',detour_steps=[0])
        self.assertIsNone(construct(table,u,path,1,0))
        word,events=construct(table,u,path,3,0)
        self.assertEqual(replay_visible(u,word),root)
        self.assertEqual(events[0]['after'],events[0]['before']+1)
        self.assertEqual(len(word),3)

    def test_cap_is_portfolio_miss_not_counterexample(self):
        c=dict(CASE,v=[2,1,0,0,0,7,8,6,5,4,3])
        ev=PolicyEvaluator([c],max_words=1);result=ev.evaluate(baseline())
        row=result['cases'][0]
        self.assertEqual(row['status'],'PORTFOLIO_MISS')
        self.assertTrue(row['word_cap_reached']);self.assertEqual(row['generated'],1)
        self.assertTrue(result['valid']);self.assertFalse(result['feasible'])
        self.assertIs(ev.evaluate(baseline()),result)

    def test_confirmation_cannot_become_feedback(self):
        ev=PolicyEvaluator([CASE],role='confirmation')
        result=ev.evaluate(baseline());self.assertTrue(result['feasible'])
        with self.assertRaises(ValueError):ev.feedback(result)
        self.assertFalse(result['graphs'][0]['feedback'])
        with self.assertRaises(ValueError):PolicyEvaluator([dict(CASE,q=42)])

    def test_evidence_integrity_and_roles(self):
        context=ResearchContext(CONTEXT)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'context.json'
            for field,value in [('source_role','confirmation'),('status','proved_universal')]:
                data=copy.deepcopy(context.data);data['facts'][0][field]=value
                p.write_text(json.dumps(data))
                with self.assertRaises(ValueError):ResearchContext(p)
            data=copy.deepcopy(context.data);data['facts'][0]['evidence'][0]['sha256']='bad'
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):ResearchContext(p)

    def test_empty_reply_is_invalid_not_crash(self):
        backend=SimpleNamespace(client=SimpleNamespace(complete=lambda messages:{'text':''}),usage=lambda:{})
        p=PolicyProposer(backend,ResearchContext(CONTEXT))
        self.assertIsNone(p.propose('exploit',[],['lift_policy'])['spec'])

    def test_all_engines_use_adapter_and_evox_reflection(self):
        for engine in ('sequential','gepa','adaevolve','evox'):
            with self.subTest(engine=engine),tempfile.TemporaryDirectory() as d:
                messages=[]
                def complete(msg):
                    messages.append(msg)
                    text=json.dumps(dict(EVOX_START,parent='random',history=7)) if 'JSON search strategy' in msg[0]['content'] else json.dumps(baseline())
                    return dict(text=text,cost_usd=0)
                backend=SimpleNamespace(client=SimpleNamespace(complete=complete),usage=lambda:{'cost_usd':0})
                context=ResearchContext(CONTEXT);proposer=PolicyProposer(backend,context)
                seed=Path(d)/'seed.json';seed.write_text(json.dumps(baseline()))
                cfg=dict(engine=engine,kinds=['lift_policy'],seeds=[str(seed)],max_proposals=3,
                    batch=1,eval_workers=1,select='score',final_heldout_top=0,window=1)
                campaign=LiftCampaign(cfg,Path(d)/'run',proposer,PolicyEvaluator([CASE]),context)
                result=campaign.run()
                self.assertEqual(result['proposals'],3);self.assertEqual(result['valid_proposals'],3)
                self.assertEqual(result['heldout'],[])
                self.assertTrue(all(context.render() in m[0]['content'] for m in messages))
                if engine=='evox':
                    self.assertEqual(result['strategy']['parent'],'random')
                    self.assertEqual(result['strategy']['history'],7)
                    self.assertTrue(result['strategy_history'])
