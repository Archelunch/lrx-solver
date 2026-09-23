"""Compact campaign progress; never dumps prompts or raw event streams."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from src.lrx.trace import load_run
P=Path(__file__).resolve().parent
for engine in ('sequential','evox'):
    run=load_run(P/f'{engine}-run')
    valid=[c for c in run['candidates'] if c.get('valid')]
    best=max(valid,key=lambda c:c['score']) if valid else None
    result=json.loads((P/f'{engine}-run/evals/{best["hash"]}.json').read_text()) if best else {}
    batch=run['batches'][-1] if run['batches'] else {}
    print(json.dumps(dict(engine=engine,complete=run['complete'],proposals=batch.get('proposals',0),
        best_id=best['id'] if best else None,missed=result.get('missed'),excess=result.get('max_excess'),
        failures=[c['case'] for c in result.get('cases',[]) if not c['within_bound']],
        reflections=[dict(task=r.get('task'),strategy=r.get('strategy'),error=r.get('error') or r.get('strategy_error')) for r in run['reflections']],
        usage=(run['summary'] or batch).get('usage',{}))))
