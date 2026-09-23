"""Freeze development/confirmation data, evidence context, and matched configs."""
import hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from integrations.lift_policy import baseline,move
P=Path(__file__).resolve().parent

def save(name,data):
 path=P/name
 if path.exists(): raise RuntimeError(f'refusing overwrite {path}')
 path.write_text(json.dumps(data,indent=2)+'\n')

def evidence(path):
 return dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())

def fact(id,status,statement,path,scope):
 return dict(id=id,status=status,statement=statement,scope=scope,source_role='development',evidence=[evidence(path)])

facts=[
 fact('target','open','For m>=8,r>=2, E_r(m+r)<=T=m(m+1)/2+(r-1)(m-2). Main conjecture remains open. The general r=2 base and universal suitable-word existence are unresolved.','research/problem.md','universal target, not established'),
 fact('routing','proved_auxiliary','A fixed smaller sorting word with all projection-changing letters has an exact n-position routing DP. Zero-projection repairs use 1--0--(n-1), length at most 2 between projected letters. All terminal j>=m are allowed.','autoresearch/loop-260923-2036/proof-note.md','fixed word only; elementary argument, not proof-assistant formalized'),
 fact('sweep','proved_auxiliary','For L/X words with k left rotations from initial mark j, the specified greedy repair costs at most 2 floor((k+n-1-j)/(n-2)), conditional on its terminal-position test. This does not establish existence of suitable short words.','autoresearch/loop-260923-2036/proof-note.md','L/X-only conditional construction; hard-family words use both directions'),
 fact('erasures','proved_auxiliary','For any full word W, marked-zero projection length is |W|-S-I_z, S counting swaps of two zeros, I_z its boundary carries and swaps with positives. This audits a word; it does not construct one.','autoresearch/loop-260923-2004/proof-note.md','m>=2,r>=1'),
 fact('old-cap','refuted','Old A_P<=P+m-2 is false: m8r3 vector (2,1,0,0,0,7,8,6,5,4,3), P42,A42=49; m9r3 vector (2,1,0,0,0,9,8,7,6,5,4,3),P52,A52=61. Use Q=T(m,r-1), projection q=Q+1 and full bound B=Q+m-2.','autoresearch/loop-260923-1737/lift-domain-benchmark.json','refutes stronger old lifting claim, not original conjecture'),
 fact('portfolio','finite_verified','Six fixed geodesic priority orders yield A54<=58 on 27 m8r5 antipode insertions and A77<=83 on 346 m8r9 antipode insertions. This covers special families only.','autoresearch/loop-260923-2036/report.md','finite development examples, not exhaustive graphs'),
 fact('repair','finite_verified','The m9r3 obstruction is repaired by one level step and suitable descents (projection53,length59). The m8r3 witness has projection43,length47 with an uphill step at projection index5 from distance36 to37. Static-priority prefixes/suffixes miss that m8 repair: descent choices must coordinate with routing.','autoresearch/loop-260923-2036/report.md','known examples; not universal rules'),
 fact('direction','hypothesis','Alternating or distance-dependent priority orders, paired with a controlled detour, may coordinate descents with zero routing. Test reusable policies; do not encode individual vectors.','autoresearch/loop-260923-2036/report.md','unproved search hypothesis')]
save('context-v1.json',dict(version=1,goal='Discover a reusable short-word construction supporting the LRX induction step.',
 invariants=['Main conjecture open','Finite tests are finite','Portfolio miss is not a lower bound','No generated code','Confirmation data never enters proposer context'],facts=facts))
train=[];seen=set()
def case(m,r,v,family,index):
 q=m*(m+1)//2+(r-2)*(m-2)+1;b=q+m-3
 return dict(id=f'{family}-{index}',family=family,m=m,r=r,v=list(v),q=q,bound=b)
def add(m,r,v,family):
 key=(m,r,tuple(v))
 if key not in seen:
  seen.add(key);train.append(case(m,r,v,family,len(train)))
for m,v in [(8,(2,1,0,0,0,7,8,6,5,4,3)),(9,(2,1,0,0,0,9,8,7,6,5,4,3))]:
 add(m,3,v,f'm{m}r3-obstruction')
 for c in 'LRX':
  u=move(v,c);add(m,3,u,f'm{m}r3-neighbours')
  add(m,3,move(u,'X'),f'm{m}r3-neighbours')
v=(8,7,9,6,5,4,3,2,1,0,0,0,0)
add(9,4,v,'m9r4-band-edge')
for c in 'LRX':add(9,4,move(v,c),'m9r4-band-edge')
for r,filename in [(5,'m8r5-frozen.json'),(9,'frozen-cases.json')]:
 vectors=json.loads((ROOT/'autoresearch/loop-260923-2004'/filename).read_text())['vectors']
 for i in range(6):add(8,r,vectors[i*(len(vectors)-1)//5],f'm8r{r}-antipode-insertions')
save('train.json',train)
rng=random.Random(2026092407);confirmation=[];used=set(seen)
for m,r in [(8,3),(9,3),(9,4),(8,5),(8,9)]:
 for i in range(24):
  while True:
   v=list(range(1,m+1))+[0]*r;rng.shuffle(v);key=(m,r,tuple(v))
   if key not in used:break
  used.add(key);confirmation.append(case(m,r,v,f'm{m}r{r}-fresh',i))
save('confirmation.json',confirmation)
save('seed.json',baseline())
provider=json.loads((ROOT/'autoresearch/loop-260923-2036/provider.json').read_text())
provider.update(max_spend_usd=2.5,max_requests=18,max_output_tokens=2500,max_reasoning_tokens=16000,timeout_sec=360)
for engine in ('sequential','evox'):
 cfg=dict(engine=engine,kinds=['lift_policy'],seeds=[str(P/'seed.json')],select='score',
  max_proposals=12,batch=1,seed=307,eval_workers=1,max_wall_seconds=5400,
  final_heldout_top=0,history=4,inspirations=1,focus=True,window=3,provider=provider)
 if engine=='evox':cfg['strategy']=dict(parent='best',modes={'exploit':1.0},inspirations=1,inspiration_pool='top',history=4,focus=True,tactic=None)
 save(engine+'-config.json',dict(campaign=cfg,context_file=str(P/'context-v1.json'),train_file=str(P/'train.json'),max_words=96,run_dir=str(P/(engine+'-run'))))
print(json.dumps(dict(train=len(train),confirmation=len(confirmation),cap_usd=5,proposals=24)))
