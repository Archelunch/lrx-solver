from pathlib import Path
import json
from urllib.request import Request, urlopen
def evaluate(program_path):
    source = Path(program_path).read_text(encoding='utf-8')
    payload = json.dumps({'source': source}).encode('utf-8')
    req = Request('http://127.0.0.1:51591/evaluate', payload, {'Content-Type': 'application/json'})
    with urlopen(req, timeout=120) as response:
        return json.load(response)
