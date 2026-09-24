"""Independent direct macro lift and safe affine certificate, stdlib only.

No sign-coherence assumption, comparator transfer, optimizer or graph search.
"""
from fractions import Fraction

def step(a,c):
    if c=='L': return a[1:]+a[:1]
    if c=='R': return a[-1:]+a[:-1]
    if c=='X': return (a[1],a[0])+a[2:]
    raise ValueError(c)

def tagged(v):
    a=[]; k=0
    for x in v:
        assert type(x) is int and x>=0
        if x: a.append(x)
        else: k+=1;a.append(-k)
    return tuple(a),k

def expand(a,lengths):
    return tuple(y for x in a for y in ([x] if x>0 else [0]*lengths[-x-1]))

def reduce_rotations(w):
    out=[]
    for c in w:
        if out and (out[-1],c) in [('L','R'),('R','L')]:out.pop()
        else:out.append(c)
    return ''.join(out)

def profile(v,w):
    a,k=tagged(v);s=[0]*k;c=0;row=[0]*k;gaps=[];xs=0
    assert len(v)>=2
    for op in w:
        if op in 'LR':
            sign=1 if op=='L' else -1
            x=a[0] if op=='L' else a[-1]
            c+=sign
            if x<0:row[-x-1]+=sign
        else:
            assert op=='X' and not(a[0]<0 and a[1]<0)
            xs+=1
            if a[0]<0:
                j=-a[0]-1;s[j]+=1;row[j]+=1
            elif a[1]<0:s[-a[1]-1]+=1
            gaps.append((c,tuple(row)));c=0;row=[0]*k
            if a[1]<0:row[-a[1]-1]-=1
        a=step(a,op)
    gaps.append((c,tuple(row)))
    return {'k':k,'x':xs,'swaps':s,'gaps':gaps,'B':xs+sum(abs(c) for c,row in gaps),
            'beta':[2*s[j]+sum(abs(row[j]) for c,row in gaps) for j in range(k)],
            'final':tuple(max(x,0) for x in a)}

def costs(cert,lengths):
    assert len(lengths)==cert['k'] and all(type(x) is int and x>=1 for x in lengths)
    z=[x-1 for x in lengths]
    exact=cert['x']+2*sum(s*t for s,t in zip(cert['swaps'],z))+sum(abs(c+sum(x*t for x,t in zip(row,z))) for c,row in cert['gaps'])
    upper=cert['B']+sum(x*t for x,t in zip(cert['beta'],z))
    assert exact<=upper
    return exact,upper

def lift(v,w,lengths,check_prefixes=False):
    a,k=tagged(v)
    assert len(lengths)==k and all(type(x) is int and x>=1 for x in lengths)
    source=expand(a,lengths);state=source;pieces=[]
    for op in w:
        if op=='L':piece='L'*(1 if a[0]>0 else lengths[-a[0]-1])
        elif op=='R':piece='R'*(1 if a[-1]>0 else lengths[-a[-1]-1])
        else:
            assert op=='X' and not(a[0]<0 and a[1]<0)
            if a[0]<0:
                z=lengths[-a[0]-1]-1;piece='L'*z+'X'+'RX'*z
            elif a[1]<0:
                z=lengths[-a[1]-1]-1;piece='X'+'LX'*z+'R'*z
            else:piece='X'
        pieces.append(piece);a=step(a,op)
        if check_prefixes:
            for c in piece:state=step(state,c)
            assert state==expand(a,lengths)
    result=reduce_rotations(''.join(pieces))
    return source,result,expand(a,lengths)

def project(v,w,deleted):
    a,k=tagged(v);deleted=set(deleted);assert deleted<=set(range(k))
    def keep(x):return x>0 or -x-1 not in deleted
    def erase(t):return tuple(max(x,0) for x in t if keep(x))
    source=erase(a);state=source;out=[];assert len(source)>=2
    for c in w:
        emit=keep(a[0]) if c=='L' else keep(a[-1]) if c=='R' else keep(a[0]) and keep(a[1])
        a=step(a,c)
        if emit:out.append(c);state=step(state,c)
        assert state==erase(a)
    return source,reduce_rotations(''.join(out))

def verify_mixture(v,rows):
    m=max(v);k=v.count(0);assert m==8 and 4<=k<=8
    assert sorted(x for x in v if x)==list(range(1,9))
    weights=[Fraction(r['weight']) for r in rows]
    assert weights and all(t>=0 for t in weights) and sum(weights)==1
    certs=[profile(v,r['word']) for r in rows]
    assert all(c['final']==tuple(range(1,9))+(0,)*k for c in certs)
    b=sum(t*c['B'] for t,c in zip(weights,certs))
    beta=[sum(t*c['beta'][j] for t,c in zip(weights,certs)) for j in range(k)]
    assert b<31+6*k and all(x<=6 for x in beta)
    return {'mean_B':str(b),'mean_beta':list(map(str,beta)),'strict_margin':str(31+6*k-b)}
