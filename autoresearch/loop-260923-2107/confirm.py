"""One-shot confirmation after both frozen campaigns finish; no model calls."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from integrations.lift_policy import Policy,PolicyEvaluator,baseline
from tools.orchestrator import trusted_status

P=Path(__file__).resolve().parent
if (P/'confirmation-results.json').exists():
    raise RuntimeError('confirmation was already run; preserve original evidence')
if not trusted_status()['ok']:
    raise RuntimeError('trusted hash mismatch')
manifest=json.loads((P/'manifest.json').read_text())
for name,digest in manifest.items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
        raise RuntimeError(f'frozen contract changed: {name}')
summaries={engine:json.loads((P/f'{engine}-run/summary.json').read_text()) for engine in ('sequential','evox')}
policies={'baseline':baseline()}|{engine:s['best']['spec'] for engine,s in summaries.items()}
evaluator=PolicyEvaluator(json.loads((P/'confirmation.json').read_text()),role='confirmation',max_words=96)
results={name:evaluator.evaluate(spec) for name,spec in policies.items()}
(P/'confirmation-results.json').write_text(json.dumps(results,indent=2)+'\n')
observations=[]
for engine,s in summaries.items():
    relative=f'autoresearch/loop-260923-2107/{engine}-run/evals/{s["best"]["hash"]}.json'
    path=ROOT/relative;train=json.loads(path.read_text())
    observations.append(dict(id=f'{engine}-construction',status='finite_verified',source_role='development',
        statement=f'This policy certifies {len(train["cases"])-train["missed"]}/{len(train["cases"])} frozen development vectors within the conjectured bound, with projection cap T(m,r-1)+1.',
        scope='Finite development cases only. Portfolio misses are not lower bounds. Uses exact smaller BFS distances.',
        policy=policies[engine],evidence=[dict(path=relative,sha256=hashlib.sha256(path.read_bytes()).hexdigest())]))
(P/'development-observations.json').write_text(json.dumps(dict(version=1,facts=observations),indent=2)+'\n')
print(json.dumps({name:dict(hash=Policy(policies[name]).hash,missed=r['missed'],max_excess=r['max_excess'],seconds=r['seconds']) for name,r in results.items()},indent=2))
