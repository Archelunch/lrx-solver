"""Existing evolutionary engines over data-only mixture word policies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from integrations.mixture_policy import Policy, Evaluator, SCHEMA
from integrations.lift_campaign import ResearchContext, PolicyProposer, LiftCampaign, SCHEMA as LIFT_SCHEMA
from src.lrx.evolve import Campaign, build_proposer
from src.lrx.prompt import extract_candidate
from tools.orchestrator import trusted_status


class Proposer(PolicyProposer):
    def _call(self,messages):
        messages=[dict(m,content=m['content'].replace(LIFT_SCHEMA,SCHEMA).replace('lifting construction','mixture word construction')) for m in messages]
        return super()._call(messages)
    def propose(self,mode,parents,kinds,insights=None,seed=0,context=None):
        payload=dict(task='Improve a reusable word-construction policy to certify additional infinite LRX families.',mode=mode,parents=parents,engine_context=context or {},unverified_hypotheses=insights or '',context_sha256=self.research.sha)
        out=self._call([dict(role='system',content=SCHEMA+'\nEvidence context:\n'+self.research.render()),dict(role='user',content=json.dumps(payload))])
        out.setdefault('spec',None)
        if out.get('text'):
            try:
                spec=extract_candidate(out['text']);Policy(spec);out['spec']=spec
            except (ValueError,TypeError,KeyError) as e:out.update(spec=None,error='ValueError: '+str(e))
        return out


class MixtureCampaign(LiftCampaign):
    def __init__(self,cfg,run_dir,proposer,task_evaluator,research):
        if cfg.get('final_heldout_top',0)!=0 or cfg.get('kinds')!=['mixture_policy'] or cfg.get('select','score')!='score' or task_evaluator.role!='train':raise ValueError('invalid mixture campaign contract')
        self.task_evaluator=task_evaluator;self.research=research;self.infra_failures=0
        Campaign.__init__(self,cfg,run_dir,proposer)
        (self.run_dir/'context.json').write_text(json.dumps(research.data,indent=2)+'\n')
        files=['integrations/mixture_policy.py','integrations/mixture_campaign.py','integrations/projected_mixtures.py','integrations/mixture_lp.py','src/lrx/evolve.py']
        (self.run_dir/'contract.json').write_text(json.dumps(dict(context_sha256=research.sha,dataset_sha256=task_evaluator.dataset_hash,implementation={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files},confirmation_in_proposals=False),indent=2)+'\n')
    def evaluate_specs(self,specs,pool):
        results=[]
        for spec in specs:
            if spec is None:results.append(None);continue
            try:policy=Policy(spec)
            except (ValueError,TypeError,KeyError) as e:
                results.append(dict(valid=False,error=str(e),score=-1e12,feasible=False,instances={},graphs=[]));continue
            if policy.hash in self.by_hash:results.append(dict(self.records[self.by_hash[policy.hash]]['eval'],duplicate_of=self.by_hash[policy.hash]))
            else:results.append(self.task_evaluator.evaluate(spec))
        return results
    def summary(self):
        out=Campaign.summary(self);out.update(task='exact projected-mixture word construction',context_sha256=self.research.sha,dataset_sha256=self.task_evaluator.dataset_hash)
        (self.run_dir/'summary.json').write_text(json.dumps(out,indent=2)+'\n');return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('config');ap.add_argument('--allow-network',action='store_true');args=ap.parse_args()
    if os.environ.get('LRX_FORBID_NETWORK') and args.allow_network:raise RuntimeError('network forbidden')
    data=json.loads(Path(args.config).read_text())
    if not trusted_status()['ok']:raise RuntimeError('trusted mismatch')
    for name,digest in data['manifest'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen input changed: '+name)
    research=ResearchContext(data['context_file']);cfg=data['campaign']
    evaluator=Evaluator(json.loads(Path(data['train_file']).read_text()),json.loads(Path(data['baseline_file']).read_text()))
    proposer=Proposer(build_proposer(cfg,args.allow_network),research)
    run=MixtureCampaign(cfg,Path(data['run_dir']),proposer,evaluator,research)
    try:print(json.dumps(run.run()))
    finally:(Path(data['run_dir'])/'final-usage.json').write_text(json.dumps(proposer.usage(),indent=2)+'\n')

if __name__=='__main__':main()
