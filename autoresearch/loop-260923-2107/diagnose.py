"""Development-only ablations after both arms finish; never select on confirmation."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from integrations.lift_policy import PolicyEvaluator,construct
P=Path(__file__).resolve().parent
if (P/'diagnostics.json').exists():raise RuntimeError('preserve existing diagnostics')
summaries={engine:json.loads((P/f'{engine}-run/summary.json').read_text()) for engine in ('sequential','evox')}
evaluator=PolicyEvaluator(json.loads((P/'train.json').read_text()),max_words=96)
results={}
for engine,summary in summaries.items():
    spec=summary['best']['spec'];original=evaluator.evaluate(spec)
    no_detours=copy.deepcopy(spec)
    for p in no_detours['paths']:p.update(detour='none',detour_steps=[])
    control=evaluator.evaluate(no_detours)
    remove=[]
    if len(spec['paths'])>1:
        for i in range(len(spec['paths'])):
            reduced=copy.deepcopy(spec);reduced['paths'].pop(i)
            r=evaluator.evaluate(reduced)
            remove.append(dict(removed_path=i,missed=r['missed'],max_excess=r['max_excess'],complexity=r['complexity']))
    witnesses=[]
    for row in original['cases']:
        if not row['within_bound']:continue
        b=row['best'];j=b['j'];v=tuple(row['v']);u=v[:j]+v[j+1:];table=evaluator.table(row['m'],row['r'])
        d=table.distance(u);slack=sum(1+event['after']-event['before'] for event in b['defects'])
        assert b['projection_length']==d+slack
        matching=[]
        for i,path in enumerate(spec['paths']):
            for defect in [None]+path['detour_steps']:
                candidate=construct(table,u,path,row['q'],defect)
                if candidate and candidate[0]==b['projection_word']:matching.append(dict(path=i,defect=defect))
        assert matching
        witnesses.append(dict(case=row['case'],smaller_distance=d,projection_slack=slack,
            routing_overhead=b['overhead'],repair_budget=row['bound']-b['projection_length'],matching_paths=matching))
    results[engine]=dict(original_missed=original['missed'],geodesic_only_missed=control['missed'],
        geodesic_only_failures=[r['case'] for r in control['cases'] if not r['within_bound']],
        remove_one_path=remove,witnesses=witnesses)
(P/'diagnostics.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{x:v[x] for x in ('original_missed','geodesic_only_missed','remove_one_path')} for k,v in results.items()},indent=2))
