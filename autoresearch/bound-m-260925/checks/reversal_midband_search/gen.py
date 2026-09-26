"""word_S candidates: pre 'RX', block-1 schedule core (seed o0+ds, schedule 'rr'+x with no 'll'), block-2 all-'r' core."""
import sys, time, itertools, json
from sched import *
def scheds(L):
    out=[]
    for x in itertools.product('lr', repeat=max(0,L-2)):
        x=''.join(x)
        if 'll' in x or x.startswith('l') and False: continue
        out.append(('rr'+x)[:L])
    return sorted(set(out))
def word_S(m, g, b, ds, sc1, fin='L', o=(1,1)):
    st = state_0g(m,g,o); n=len(st); o0=o[0]
    a = m-g-b
    L1 = g+a  # schedule length = block-1 cells - 1
    if a < 0 or len(sc1) != L1: return st, None
    return st, sched_word(st, b, [(o0+ds, sc1), (n-b, 'r'*(b+o0-1))], fin, 'RX')
def pool(m, g, o=(1,1)):
    picks=[0,o[0]]; fr={}
    for b in range(max(1,(m-5)//2), (m-1)//2+1):
        a=m-g-b
        if a<0: continue
        for sc1 in scheds(g+a):
            for ds in (1,2,3):
                for fin in 'LR':
                    st,w = word_S(m,g,b,ds,sc1,fin,o)
                    if w is None: continue
                    try: p=C.Profile(st,w,picks)
                    except C.CheckError: continue
                    k=(p.base,)+tuple(p.beta)
                    if k not in fr: fr[k]=(w,b,ds,sc1,fin)
    keys=sorted(fr); keys=[x for x in keys if not any(y!=x and all(a<=b for a,b in zip(y,x)) for y in keys)]
    return {k:fr[k] for k in keys}
if __name__=='__main__':
    out={}
    for m in range(int(sys.argv[1]), int(sys.argv[2])+1):
        j=m//4; s=m-2
        for g in range(j+1, m-j):
            t0=time.process_time()
            fr=pool(m,g); T=C.budget(m,2)
            val,_=leaf_dual([(k[0],list(k[1:])) for k in fr],2,s,T,{}) if fr else (None,None)
            single=min([k[0]-T for k in fr if max(k[1:])<=s], default=None)
            print(m,g,'front',len(fr),'root LP',val,'best single B-T',single,'%.1fs'%(time.process_time()-t0),flush=True)
            out['%d,%d'%(m,g)]={'value':str(val),'front':[[k[0],list(k[1:])]+list(v) for k,v in fr.items()]}
    json.dump(out, open('gen-%s-%s.json'%(sys.argv[1],sys.argv[2]),'w'))
