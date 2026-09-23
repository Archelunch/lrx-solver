"""One bounded mathematical JSON consultation; never executes the reply."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.lrx.evolve import build_proposer
from tools.orchestrator import trusted_status

p = Path(__file__).parent
assert trusted_status()["ok"]
output = p / "consult-result.json"
if output.exists():
    raise FileExistsError(output)
proposer = build_proposer({"provider": json.loads((p / "provider.json").read_text())}, True)
messages = [{"role": "system", "content": "You are a skeptical mathematical reviewer. Give explicit arguments, no claimed proof from finite tests. Reply in JSON."},
            {"role": "user", "content": (p / "consult-prompt.txt").read_text()}]
try:
    reply = proposer.client.complete(messages)
    output.write_text(json.dumps(reply, indent=2) + "\n")
finally:
    (p / "usage.json").write_text(json.dumps(proposer.usage(), indent=2) + "\n")
print(json.dumps(proposer.usage()))
