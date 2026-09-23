import json
import random
import tempfile
import unittest
from pathlib import Path
from integrations.mixture_policy import Policy, construct, Evaluator, state_for, comparison, materialize
from integrations.mixture_campaign import MixtureCampaign
from src.lrx.certificates import replay_visible


def seed():
    return dict(kind='mixture_policy',name='test',rules=[dict(cuts=[0,4,8],weights=dict(rotation=1,zero_rotation=0,zero_swap=0,position=0,rank_gap=0),direction='shortest',tie='left')])


class MixturePolicyTests(unittest.TestCase):
    def test_construct_and_stretch(self):
        rng=random.Random(93)
        for _ in range(60):
            labels=list(range(1,9));rng.shuffle(labels);mask=rng.randrange(1,512)
            state=state_for(labels,mask);rule=seed()['rules'][0]
            rule['weights']={k:rng.randrange(-3,4) for k in rule['weights']}
            rule['direction']=rng.choice(['left','right','shortest']);rule['tie']=rng.choice(['left','right'])
            cut=rng.randrange(len(state));word=construct(state,cut,rule)
            self.assertEqual(replay_visible(state,word),tuple(range(1,9))+(0,)*mask.bit_count())
            profile=comparison(state,word,cut,labels);self.assertIsNotNone(profile)
            materialize(profile,[rng.randrange(1,5) for _ in range(mask.bit_count())])
    def test_strict_schema(self):
        for key,value in [('code','print(1)'),('rules',[]),('name',12)]:
            s=seed();s[key]=value
            with self.assertRaises(ValueError):Policy(s)
        s=seed();s['rules'][0]['weights']['rotation']=True
        with self.assertRaises(ValueError):Policy(s)
        s=seed();h=Policy(s).hash;s['name']='renamed';self.assertEqual(h,Policy(s).hash)
    def test_confirmation_boundary(self):
        e=Evaluator([dict(id='a',order_index=0,mask=15,blocks=4)],{'a':[]},role='confirmation')
        r=e.evaluate(seed());self.assertTrue(r['valid'])
        with self.assertRaises(ValueError):e.feedback(r)
    def test_all_planners_without_network(self):
        class Context:
            sha='test';data={'version':1,'facts':[]}
        class Fake:
            def usage(self):return {'requests':0,'cost_usd':0}
            def propose(self,*args,**kwargs):return {'spec':seed(),'text':json.dumps(seed())}
            def reflect(self,*args,**kwargs):return {'text':'{}'}
        for engine in ('sequential','gepa','adaevolve','evox'):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);(p/'seed.json').write_text(json.dumps(seed()))
                e=Evaluator([dict(id='a',order_index=0,mask=15,blocks=4)],{'a':[]})
                cfg=dict(engine=engine,kinds=['mixture_policy'],seeds=[str(p/'seed.json')],max_proposals=2,final_heldout_top=0,batch=1,eval_workers=1)
                campaign=MixtureCampaign(cfg,p/'run',Fake(),e,Context())
                result=campaign.run();self.assertIsNotNone(result['best'])

if __name__=='__main__':unittest.main()
