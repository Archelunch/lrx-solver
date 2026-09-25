from pathlib import Path
import json
from urllib.request import Request, urlopen
from skydiscover.optimize.evaluation.evaluation_result import EvaluationResult
def evaluate(program_path):
    source = Path(program_path).read_text(encoding='utf-8')
    payload = json.dumps({'source': source}).encode('utf-8')
    req = Request('http://127.0.0.1:61508/evaluate', payload, {'Content-Type': 'application/json'})
    with urlopen(req, timeout=60) as response:
        out = json.load(response)
    metrics = {'combined_score': float(out['combined_score']), 'passes': float(out['passes']),
               'violation_sum': float(out['violation_sum'])}
    return EvaluationResult(metrics=metrics, artifacts={'feedback': out['feedback']})
