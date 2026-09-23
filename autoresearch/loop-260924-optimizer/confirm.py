"""One-shot confirmation after both campaign summaries exist; no model calls."""
import hashlib,json,sys,zipfile
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];sys.path.insert(0,str(ROOT))
from integrations.mixture_policy import catalog_profiles,certificate,Evaluator
from integrations.mixture_lp import optimize
from tools.orchestrator import trusted_status
assert trusted_status()['ok']
output=P/'confirmation-results.json'
if output.exists():raise FileExistsError(output)
configs=[json.loads((P/(arm+'-config.json')).read_text()) for arm in ('sequential','evox')]
for cfg in configs:
    if not (Path(cfg['run_dir'])/'summary.json').exists():raise RuntimeError('both arms must finish first')
    for name,digest in cfg['manifest'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen input changed')
cases=json.loads((P/'confirmation.json').read_text());pool=json.loads((P/'pool.json').read_text())
with zipfile.ZipFile(ROOT/'autoresearch/loop-260923-2107/incoming/verification.zip') as z:bundle=json.loads(z.read('literature/multiset_nine_gap_complete_certificates_20260924.json'))
baseline={};rows=[]
for c in cases:
    profiles=catalog_profiles(c,bundle,pool);baseline[c['id']]=profiles
    rows.append(dict(case=c,certificate=certificate(profiles,optimize(profiles))))
e=Evaluator(cases,baseline,role='confirmation');arms={}
for arm in ('sequential','evox'):
    spec=json.loads((P/(arm+'-run')/'best.json').read_text());arms[arm]=e.evaluate(spec)
result=dict(baseline=rows,arms=arms,scope='One frozen structural sample; no statistical engine ranking; no feedback to proposers.')
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(baseline=sum(bool(r['certificate']) for r in rows),arms={k:v['certified'] for k,v in arms.items()},cases=len(cases))))
