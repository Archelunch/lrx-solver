"""Existing evolutionary planners applied to bounded LRX construction policies.

Run: python -m integrations.lift_campaign CONFIG [--allow-network]
The trusted controller candidate/evaluator modules are not modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from integrations.lift_policy import Policy,PolicyEvaluator,ROOT
from src.lrx.evolve import Campaign,build_proposer,EVOX_START
from src.lrx.prompt import extract_candidate
from tools.orchestrator import trusted_status

SCHEMA='''Return one JSON object, no code, with this schema:
{"kind":"lift_policy","name":"short description","zero_order":"left|right|distance_high|distance_low",
 "paths":[{"orders":["LRX"],"period":1,"axis":"step|distance|front_zeros",
 "detour":"none|level|uphill|either","detour_steps":[]}]}
1..8 paths. Each orders list has 1..4 permutations of LRX. period is integer 1..16.
At each projected step, choose order index floor(axis/period) modulo len(orders).
axis=step is the number of projected letters already emitted; distance is exact
smaller distance; front_zeros is the count of zeros in the first two smaller slots.
Normally take the first strictly distance-decreasing move in that order.
Each path always offers a geodesic variant. Additionally, detour_steps (up to 4
distinct integers 0..32) offers a separate variant with one prescribed non-descending
move at that step: level keeps distance; uphill increases it by one; either permits
both. The first eligible move in the current order is chosen. All other moves descend.
A variant is skipped if the detour cannot be taken within q. none requires [].
Zero order and path order matter under the fixed generation cap. All base paths are
tried before detour variants, each across zeros in zero_order. Exact fixed-word
routing chooses invisible repairs. Stop a case at the first trusted witness <=B.
No executable source, explicit state lookups, per-graph exceptions, or new fields.
The evaluator uses exact smaller BFS distances: this is construction discovery,
not an oracle-free proof or a universal bound. A miss is only a portfolio miss.
Prefer few misses, then smaller budget excess, then simple reusable policies.
'''


class ResearchContext:
    def __init__(self,path):
        self.path=Path(path);raw=self.path.read_bytes();self.data=json.loads(raw)
        if self.data.get('version')!=1: raise ValueError('context version must be 1')
        self.sha=hashlib.sha256(raw).hexdigest();ids=set()
        for fact in self.data['facts']:
            if fact['id'] in ids: raise ValueError('duplicate fact id')
            ids.add(fact['id'])
            if fact['status'] not in ('proved_auxiliary','finite_verified','refuted','incomplete','hypothesis','open'):
                raise ValueError('unknown evidence status')
            if fact.get('source_role')!='development': raise ValueError('only development evidence enters context')
            for ev in fact['evidence']:
                p=(ROOT/ev['path']).resolve()
                if not p.is_relative_to(ROOT) or p.name=='.env': raise ValueError('invalid evidence path')
                if hashlib.sha256(p.read_bytes()).hexdigest()!=ev['sha256']:
                    raise ValueError('context evidence hash mismatch')
    def render(self):
        return json.dumps(self.data,sort_keys=True)


class PolicyProposer:
    def __init__(self,backend,research):
        self.backend=backend;self.research=research
    def usage(self): return self.backend.usage()
    def _call(self,messages):
        try:
            out=self.backend.client.complete(messages)
            return dict(out,messages=messages)
        except Exception as e:
            return dict(spec=None,text=None,error=f'{type(e).__name__}: {e}',messages=messages)
    def propose(self,mode,parents,kinds,insights=None,seed=0,context=None):
        payload=dict(task='Propose an improved reusable LRX lifting construction policy.',mode=mode,
            parents=parents,engine_context=context or {},
            unverified_reflection_hypotheses=insights or '',context_sha256=self.research.sha)
        messages=[dict(role='system',content=SCHEMA+'\nResearch context (statuses are binding):\n'+self.research.render()),
                  dict(role='user',content=json.dumps(payload))]
        out=self._call(messages)
        out.setdefault('spec',None)
        if out.get('text'):
            try:
                spec=extract_candidate(out['text']);Policy(spec);out['spec']=spec
            except (ValueError,TypeError,KeyError) as e:
                out.update(spec=None,error=f'ValueError: invalid construction policy: {e}')
        return out
    def reflect(self,summary,seed=0,task='insights'):
        if task=='strategy':
            instruction=('Return one JSON search strategy object. Allowed keys and defaults: '+json.dumps(EVOX_START)+
                '. parent: best/front/top3/random; modes: nonnegative weights on exploit/explore/edit/merge; '
                'inspirations: 0..3; inspiration_pool: top/random; history: 0..8; focus: boolean; '
                'tactic: null or string <=800 characters. No generated code. Adapt context selection '
                'and mutation strategy using measured outcomes. Keep claims finite.')
        elif task=='tactics':
            instruction='Return {"tactics":[{"idea":"...","how":"...","target":"...","cautions":"..."}]} with up to 4 testable construction ideas.'
        else: instruction='Return up to 200 words of testable construction hypotheses and failure lessons. Do not claim proofs.'
        return self._call([dict(role='system',content=instruction+'\n'+SCHEMA+'\n'+self.research.render()),
                           dict(role='user',content=json.dumps(summary))])


class LiftCampaign(Campaign):
    def __init__(self,cfg,run_dir,proposer,task_evaluator,research):
        if cfg.get('final_heldout_top',0)!=0:
            raise ValueError('confirmation runs separately after ALL engines finish')
        if cfg.get('kinds')!=['lift_policy'] or cfg.get('select','score')!='score':
            raise ValueError('construction adapter requires kinds=[lift_policy] and select=score')
        if task_evaluator.role!='train': raise ValueError('campaign evaluator must be train-only')
        self.task_evaluator=task_evaluator;self.research=research;self.infra_failures=0
        super().__init__(cfg,run_dir,proposer)
        (self.run_dir/'context.json').write_text(json.dumps(research.data,indent=2)+'\n')
        hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
            ['integrations/lift_policy.py','integrations/lift_campaign.py','integrations/word_lift.py']}
        (self.run_dir/'contract.json').write_text(json.dumps(dict(context_sha256=research.sha,
            dataset_sha256=task_evaluator.dataset_hash,implementation=hashes,
            max_words=task_evaluator.max_words,confirmation_in_proposals=False),indent=2)+'\n')
    def evaluate_specs(self,specs,pool):
        results=[]
        for spec in specs:
            if spec is None: results.append(None);continue
            try: policy=Policy(spec)
            except (ValueError,TypeError,KeyError) as e:
                results.append(dict(valid=False,error=str(e),score=-1e12,feasible=False,instances={},graphs=[]));continue
            if policy.hash in self.by_hash:
                results.append(dict(self.records[self.by_hash[policy.hash]]['eval'],duplicate_of=self.by_hash[policy.hash]))
            else: results.append(self.task_evaluator.evaluate(spec))
        return results
    def make_feedback(self,spec,result):
        return self.task_evaluator.feedback(result) if result.get('valid') else {'error':result.get('error')}
    def final_heldout(self,pool): self.heldout=[]
    def summary(self):
        out=super().summary()
        out.update(task="fixed-word lifting construction",context_sha256=self.research.sha,
            dataset_sha256=self.task_evaluator.dataset_hash,contract="contract.json")
        (self.run_dir/"summary.json").write_text(json.dumps(out,indent=2)+"\n")
        return out
    def finish(self,req,out,result):
        improved=super().finish(req,out,result)
        err=out.get('error') or ''
        self.infra_failures=self.infra_failures+1 if err and not err.startswith(('ValueError','BudgetExhausted')) else 0
        if self.infra_failures>=2: self.stop_reason='two consecutive infrastructure failures'
        return improved


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('config');ap.add_argument('--allow-network',action='store_true')
    args=ap.parse_args()
    if os.environ.get('LRX_FORBID_NETWORK') and args.allow_network:
        raise RuntimeError('LRX_FORBID_NETWORK is set')
    data=json.loads(Path(args.config).read_text())
    if not trusted_status()['ok']: raise RuntimeError('trusted hash mismatch')
    research=ResearchContext(data['context_file'])
    dataset=json.loads(Path(data['train_file']).read_text())
    cfg=data['campaign'];backend=build_proposer(cfg,args.allow_network)
    proposer=PolicyProposer(backend,research)
    evaluator=PolicyEvaluator(dataset,max_words=data['max_words'])
    run=LiftCampaign(cfg,Path(data['run_dir']),proposer,evaluator,research)
    try:
        result=run.run();print(json.dumps(result))
    finally:
        (Path(data['run_dir'])/'final-usage.json').write_text(json.dumps(proposer.usage(),indent=2)+'\n')

if __name__=='__main__': main()
