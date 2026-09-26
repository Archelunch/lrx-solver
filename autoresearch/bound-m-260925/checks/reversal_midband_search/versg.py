import json
from gen import pool
from mb import C
from integrations.bound3_evaluator import score_output
from integrations.bound3_audit import audit_claim
from integrations.bound_task import make_family
res=[]
for m in range(9,17):
    j=m//4
    for g in range(j+1,m-j):
        fr=pool(m,g)
        if not fr: continue
        words=[v[0] for k,v in sorted(fr.items())][:32]
        fam=make_family(list(range(m,0,-1)),1|1<<g)
        r=score_output(fam,{'words':words})
        au=audit_claim(fam,r['output'],r['certificate']) if r['status']=='CERTIFIED' else None
        sup=[(s['weight'],s['base'],s['beta']) for s in r['leaves'][0]['support']] if r.get('leaves') else None
        print(m,g,r['status'],'gap',r['gap'],'lhs',r['leaves'][0]['lhs'],'audit',au,'support',sup,flush=True)
        res.append({'m':m,'g':g,'status':r['status'],'gap':r['gap'],'lhs':r['leaves'][0]['lhs'],'audit':au,
                    'words':[s['word'] for s in r['leaves'][0]['support']],'params':[fr[k][1:] for k in sorted(fr)][:32]})
json.dump(res,open('%s/wordS-root.json'%'/private/tmp/claude-502/-Users-pavluhin-Documents-Projects-lrx-lab/963a3e98-bd38-4e90-ab10-89151e23a5b4/scratchpad/mb','w'))
