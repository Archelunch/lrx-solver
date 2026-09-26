import json, time
from mb import *
ORIG = [(1,1),(2,1),(1,2),(3,1),(1,3),(2,2)]
rows = []
def sample_shortest(st, tb, limit):
    v0 = ids(st); d0 = tb.d(v0); words=[]
    def succ(v):
        out=[('L',v[1:]+v[:1]),('R',v[-1:]+v[:-1])]
        if not (v[0]>=ZID and v[1]>=ZID): out.append(('X',(v[1],v[0])+v[2:]))
        return out
    def walk(v,dv,w):
        if len(words)>=limit: return
        if dv==0: words.append(''.join(w)); return
        for ch,u in succ(v):
            if tb.d(u)==dv-1:
                w.append(ch); walk(u,dv-1,w); w.pop()
    walk(v0,d0,[]); return d0, words
for m in (9,10,11):
    j = m//4
    for g in range(j+1, m-j):
        for o in ORIG:
            tb = tab(m, sum(o))
            if tb is None: continue
            st = state_0g(m,g,o); T = C.budget(m, sum(o)); picks=[0,o[0]]
            t0=time.process_time()
            if m < 11:
                d0,total,words,_ = shortest_dag(st, tb, limit=2000)
            else:
                d0,words = sample_shortest(st, tb, 200); total=None
            fr = {}
            for w in words:
                p = C.Profile(st,w,picks); fr.setdefault(tuple(p.beta), w)
            keys=sorted(fr); par=[x for x in keys if not any(y!=x and all(a<=b for a,b in zip(y,x)) for y in keys)]
            row={'m':m,'g':g,'origin':list(o),'dist':d0,'T':T,'dist_minus_T':d0-T,'n_shortest':total,'sampled':len(words),'shortest_beta_front':[list(x) for x in par],'example':fr[par[0]]}
            rows.append(row)
            print(m,g,o,'d',d0,'T',T,'d-T',d0-T,'#sw',total,'front',par,'%.1fs'%(time.process_time()-t0),flush=True)
json.dump(rows, open('dists.json','w'))
