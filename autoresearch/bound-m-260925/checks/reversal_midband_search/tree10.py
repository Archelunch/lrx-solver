import json, sys
from mb import *
from gen import pool as spool
from integrations.bound3_evaluator import score_output, leaf_lp
from integrations.bound3_audit import audit_claim
from integrations.bound_task import make_family
S='/private/tmp/claude-502/-Users-pavluhin-Documents-Projects-lrx-lab/963a3e98-bd38-4e90-ab10-89151e23a5b4/scratchpad/mb/'
rows=[json.loads(l) for l in open(S+'cg-results.jsonl')]
m,g=int(sys.argv[1]),int(sys.argv[2])
def words_at(o):
    ws=set()
    for r in rows:
        if r['m']==m and r['g']==g and r['origin']==list(o): ws.update(w for _,_,w in r['front'])
    ws.update(v[0] for v in spool(m,g,o).values())
    tb=tab(m,sum(o))
    if tb:
        ws.update(shortest_dag(state_0g(m,g,o),tb,limit=50)[2])
    st=state_0g(m,g,o); picks=[0,o[0]]; fr={}
    for w in ws:
        p=C.Profile(st,w,picks); k=(p.base,)+tuple(p.beta)
        if k not in fr or len(w)<len(fr[k]): fr[k]=w
    keys=sorted(fr); keys=[x for x in keys if not any(y!=x and all(a<=b for a,b in zip(y,x)) for y in keys)]
    return [(fr[k],k[0],list(k[1:])) for k in keys][:32]
W={o:words_at(o) for o in [(1,1),(2,1),(3,1),(4,1)]}
fam=make_family(list(range(m,0,-1)),1|1<<g); s=m-2
def leaf(l,h):
    best=None
    for o,ws in W.items():
        if o[0]>l: continue
        box=[(l,h),(1,None)]
        costs=[(B+bt[0]*(l-o[0]),bt) for _,B,bt in ws]
        r=leaf_lp(costs,box,s,C.budget(m,l+1))
        lhs=r['value'] if r['status']=='CERTIFIED' else None
        if lhs is not None and (best is None or lhs<best[0]): best=(lhs,{'words':[w for w,_,_ in ws],'origins':list(o)})
        if lhs is None and best is None: pass
    return best
for c in range(2,8):
    leaves=[]; ok=True; l=1
    # greedy widest leaves before c
    while l<c:
        h=next((h for h in range(c-1,l-1,-1) if leaf(l,h)),None)
        if h is None: ok=False; break
        leaves.append((leaf(l,h)[1],h)); l=h+1
    last=leaf(c,None)
    print('cut',c,'prefix ok',ok,'last leaf', None if last is None else last[0], [h for _,h in leaves])
    if ok and last:
        tree=last[1]
        for node,h in reversed(leaves): tree={'j':0,'t':h,'le':node,'ge':tree}
        r=score_output(fam,{'tree':tree}); print(' score',r['status'],r['gap'],r.get('n_leaves'))
        if r['status']=='CERTIFIED':
            print(' audit',audit_claim(fam,r['output'],r['certificate']))
            json.dump({'m':m,'g':g,'tree':tree},open(S+'tree-%d-%d.json'%(m,g),'w')); break
