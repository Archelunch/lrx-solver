import json, sys
from mb import *
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim
from integrations.bound_task import make_family
rows=[json.loads(l) for l in open('/private/tmp/claude-502/-Users-pavluhin-Documents-Projects-lrx-lab/963a3e98-bd38-4e90-ab10-89151e23a5b4/scratchpad/mb/cg-results.jsonl')]
def front(m,g,o,wid=-1):
    r=[x for x in rows if x['m']==m and x['g']==g and x['origin']==list(o) and x['width0']==wid][-1]
    ws = sorted(r['front'], key=lambda x: x[0])
    return [w for _,_,w in ws][:32]
out = {}
for g in (3,5,6):
    out[(9,g)] = {'words': front(9,g,(1,1))}
out[(9,4)] = {'tree': {'j':0,'t':1,'le':{'words':front(9,4,(1,1),1),'origins':[1,1]},'ge':{'words':front(9,4,(2,1)),'origins':[2,1]}}}
for (m,g),o in out.items():
    fam = make_family(list(range(m,0,-1)), 1|1<<g)
    r = score_output(fam, o)
    print(m,g,r['status'],r['gap'],r.get('n_leaves'), [(x['box'],x['lhs'],[(s['weight'],s['base'],s['beta']) for s in x['support']]) for x in r['leaves']])
    if r['status']=='CERTIFIED': print('  audit', audit_claim(fam, r['output'], r['certificate']))
