"""Projection/comparison profiles for arbitrary retained gaps at m=8.

Archive data only; no archive code is executed. Bounds apply to all positive
block lengths through the reviewed comparison and stretching lemmas.
"""
from fractions import Fraction
from src.lrx.certificates import replay_visible


def state_for(labels,mask):
    out=[]
    for j in range(9):
        if mask>>j&1:out.append(0)
        if j<8:out.append(labels[j])
    return tuple(out)


def project(source,mask,cut):
    if type(mask) is not int or not 1<=mask<512:raise ValueError('nonempty nine-gap mask required')
    state=source['state']
    if len(state)!=17 or tuple(state[::2])!=(0,)*9 or sorted(state[1::2])!=list(range(1,9)) or type(cut) is not int or not 0<=cut<17:
        raise ValueError('invalid reference or cut')
    atoms=[x if x else -(i//2+1) for i,x in enumerate(state)]
    def keep(x):return x>0 or bool(mask>>(-x-1)&1)
    initial=tuple(x if x>0 else 0 for x in atoms if keep(x))
    newcut=sum(keep(x) for x in atoms[:cut])%len(initial);word=[]
    for c in source['word']:
        if c=='L':retained=keep(atoms[0]);atoms=atoms[1:]+atoms[:1]
        elif c=='R':retained=keep(atoms[-1]);atoms=atoms[-1:]+atoms[:-1]
        elif c=='X':
            retained=keep(atoms[0]) and keep(atoms[1]);atoms[0],atoms[1]=atoms[1],atoms[0]
        else:raise ValueError('invalid letter')
        if retained:
            if word and (word[-1],c) in (('L','R'),('R','L')):word.pop()
            else:word.append(c)
    word=''.join(word)
    if replay_visible(initial,word)!=tuple(range(1,9))+(0,)*mask.bit_count():raise ValueError('projected replay failed')
    return initial,word,newcut


def resources(state,word):
    n=len(state);ordinal=0;atoms=[]
    for x in state:
        if not x:ordinal+=1;atoms.append(-ordinal)
        else:atoms.append(x)
    k=ordinal;at=0;swaps=[0]*k;gap=[0]*(k+1);gaps=[];blocked=set();nx=0
    for c in word:
        if c in 'LR':
            sign=1 if c=='L' else -1;atom=atoms[at if c=='L' else (at-1)%n]
            gap[0]+=sign
            if atom<0:gap[-atom]+=sign
            at=(at+sign)%n
        elif c=='X':
            a,b=at,(at+1)%n;left,right=atoms[a],atoms[b];blocked.add(b);nx+=1
            if left<0 and right<0:raise ValueError('zero-zero swap')
            if left<0:swaps[-left-1]+=1;gap[-left]+=1
            elif right<0:swaps[-right-1]+=1
            gaps.append(gap);gap=[0]*(k+1)
            if right<0:gap[-right]-=1
            atoms[a],atoms[b]=right,left
        else:raise ValueError('invalid letter')
    gaps.append(gap)
    base=nx+sum(abs(g[0]) for g in gaps)
    if base!=len(word):raise ValueError('rotation runs not reduced')
    return dict(base=base,beta=[2*swaps[j]+sum(abs(g[j+1]) for g in gaps) for j in range(k)],
        finish=at,blocked=blocked,nx=nx,swaps=swaps,
        affine=all(not min(g)<0<max(g) for g in gaps))


def ranks(state,cut,finish):
    n=len(state);targets={x:(finish+x-1-cut)%n for x in range(1,9)}
    zeros=iter(sorted(set(range(n))-set(targets.values())))
    return tuple(targets[x] if x else next(zeros) for x in state[cut:]+state[:cut])


def counts(state,p,cut):
    n=len(state);inv=sum(x>y for i,x in enumerate(p) for y in p[i+1:])
    named=[(i-cut)%n for i,x in enumerate(state) if x]
    sigma=[]
    for i,x in enumerate(state):
        if not x:
            j=(i-cut)%n;sigma.append(sum((t<j and p[t]>p[j]) or (t>j and p[t]<p[j]) for t in named))
    return inv,sigma


def dominates(p,q):
    return all(all(a<=b for a,b in zip(sorted(p[:j]),sorted(q[:j]))) for j in range(1,len(p)+1))


def comparison(state,word,cut,labels):
    if sorted(labels)!=list(range(1,9)):raise ValueError('invalid labels')
    if replay_visible(tuple(state),word)!=tuple(range(1,9))+(0,)*(len(state)-8):raise ValueError('reference replay failed')
    info=resources(state,word);n=len(state)
    if type(cut) is not int or not 0<=cut<n or cut in info['blocked']:return None
    actual=iter(labels);target=tuple(next(actual) if x else 0 for x in state)
    q=ranks(state,cut,info['finish']);p=ranks(target,cut,info['finish'])
    if not dominates(p,q):return None
    invq,sq=counts(state,q,cut);invp,sp=counts(target,p,cut)
    if invq!=info['nx'] or sq!=info['swaps']:return None
    if invp>invq or any(a<b for a,b in zip(sq,sp)):raise ValueError('invalid dominance savings')
    return dict(base=info['base']-invq+invp,gamma=[b-s+t for b,s,t in zip(info['beta'],sq,sp)],
        state=list(state),target=list(target),word=word,cut=cut,affine=info['affine'])


def verify_mixture(profiles,weights):
    w=[Fraction(x) for x in weights]
    if not profiles or len(w)!=len(profiles) or min(w)<0 or sum(w)!=1:raise ValueError('invalid weights')
    k=len(profiles[0]['gamma'])
    base=sum(x*p['base'] for x,p in zip(w,profiles))
    gamma=[sum(x*p['gamma'][j] for x,p in zip(w,profiles)) for j in range(k)]
    if base>=31+6*k or max(gamma)>6:raise ValueError('mixture outside certificate inequalities')
    return dict(base=str(base),gamma=[str(x) for x in gamma],margin=str(31+6*k-base))


def materialize(profile,lengths):
    """Independent literal expansion followed by comparisons, then trusted replay."""
    state=profile['state'];word=profile['word'];cut=profile['cut'];n=len(state)
    zeros=iter(range(len(lengths)));atoms=[x if x else -(next(zeros)+1) for x in state]
    initial=[];expanded_cut=0
    for i,x in enumerate(atoms):
        part=[x] if x>0 else [0]*lengths[-x-1];initial.extend(part)
        if i<cut:expanded_cut+=len(part)
    lifted=[]
    for c in word:
        if c=='L':
            a=atoms[0];lifted.extend('L'*(1 if a>0 else lengths[-a-1]));atoms=atoms[1:]+atoms[:1]
        elif c=='R':
            a=atoms[-1];lifted.extend('R'*(1 if a>0 else lengths[-a-1]));atoms=atoms[-1:]+atoms[:-1]
        else:
            a,b=atoms[:2]
            if a<0:z=lengths[-a-1]-1;lifted.extend('L'*z+'X'+'RX'*z)
            elif b<0:z=lengths[-b-1]-1;lifted.extend('X'+'LX'*z+'R'*z)
            else:lifted.append('X')
            atoms[0],atoms[1]=b,a
    reduced=[]
    for c in lifted:
        if reduced and (reduced[-1],c) in (('L','R'),('R','L')):reduced.pop()
        else:reduced.append(c)
    target=[];zero=0
    for x in profile['target']:
        if x:target.append(x)
        else:target.extend([0]*lengths[zero]);zero+=1
    finish=(reduced.count('L')-reduced.count('R'))%len(target)
    p=list(ranks(target,expanded_cut,finish));at=(-expanded_cut)%len(p);answer=[]
    for c in reduced:
        if c=='X':
            if at==len(p)-1:raise ValueError('expanded cut crossed')
            if p[at]>p[at+1]:p[at],p[at+1]=p[at+1],p[at];answer.append(c)
        else:at=(at+(1 if c=='L' else -1))%len(p);answer.append(c)
    answer=''.join(answer);upper=profile['base']+sum(g*(ell-1) for g,ell in zip(profile['gamma'],lengths))
    if replay_visible(tuple(target),answer)!=tuple(range(1,9))+(0,)*sum(lengths) or len(answer)>upper:
        raise ValueError('expanded comparison certificate failed')
    return dict(word=answer,length=len(answer),upper=upper)
