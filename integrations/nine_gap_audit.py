"""Independent data-only audit of a supplied nine-gap certificate archive.

Does not import or execute archive code. Uses physical slots, exact fractions,
and the repository's trusted visible replay. This checks the nine-gap bundle;
it does not recheck the separate projection coverage or <=3-block theorem.
"""
import argparse
from fractions import Fraction
from functools import lru_cache
import hashlib
from itertools import permutations
import json
from pathlib import Path
import time
import zipfile

from src.lrx.certificates import replay_visible

MEMBER='literature/multiset_nine_gap_complete_certificates_20260924.json'
ROOT=tuple(range(1,9))+(0,)*9


def profile(state,word):
    if len(state)!=17 or tuple(state[::2])!=(0,)*9 or sorted(state[1::2])!=list(range(1,9)):
        raise ValueError('not a nine-gap base')
    if any(c not in 'LRX' for c in word) or replay_visible(tuple(state),word)!=ROOT:
        raise ValueError('reference does not sort')
    slots=[-(i//2+1) if i%2==0 else x for i,x in enumerate(state)]
    cursor=0;blocked=set();swaps=[0]*9;gap=[0]*10;gaps=[];nx=0
    for c in word:
        if c in 'LR':
            sign=1 if c=='L' else -1
            atom=slots[cursor if c=='L' else (cursor-1)%17]
            gap[0]+=sign
            if atom<0:gap[-atom]+=sign
            cursor=(cursor+sign)%17
        else:
            nx+=1;a,b=cursor,(cursor+1)%17;blocked.add(b)
            left,right=slots[a],slots[b]
            if left<0 and right<0:raise ValueError('zero-zero swap')
            zero=left if left<0 else right if right<0 else None
            if zero is not None:swaps[-zero-1]+=1
            if left<0:gap[-left]+=1
            gaps.append(gap);gap=[0]*10
            if right<0:gap[-right]-=1
            slots[a],slots[b]=right,left
    gaps.append(gap)
    if any(min(g)<0<max(g) for g in gaps):raise ValueError('non-affine sign pattern')
    base=nx+sum(abs(g[0]) for g in gaps)
    if base!=len(word):raise ValueError('base price mismatch')
    beta=[2*swaps[j]+sum(abs(g[j+1]) for g in gaps) for j in range(9)]
    return dict(finish=cursor,blocked=blocked,base=base,beta=beta,swaps=swaps,nx=nx)


def stretch(state,word,lengths):
    """Literal macros with physical atom slots; simplify inverse rotations only."""
    slots=[-(i//2+1) if i%2==0 else x for i,x in enumerate(state)]
    cursor=0;output=[];initial=[]
    for atom in slots:initial.extend([atom] if atom>0 else [0]*lengths[-atom-1])
    def emit(letters):
        for c in letters:
            if output and (output[-1],c) in (('L','R'),('R','L')):output.pop()
            else:output.append(c)
    for c in word:
        if c in 'LR':
            atom=slots[cursor if c=='L' else (cursor-1)%17]
            emit(c*(lengths[-atom-1] if atom<0 else 1))
            cursor=(cursor+(1 if c=='L' else -1))%17
        else:
            a,b=cursor,(cursor+1)%17;left,right=slots[a],slots[b]
            if left<0 and right<0:raise ValueError('zero-zero macro')
            if left<0:
                z=lengths[-left-1]-1;emit('L'*z+'X'+'RX'*z)
            elif right<0:
                z=lengths[-right-1]-1;emit('X'+'LX'*z+'R'*z)
            else:emit('X')
            slots[a],slots[b]=right,left
    return tuple(initial),''.join(output)


def ranks(state,cut,finish):
    targets={x:(finish+x-1-cut)%17 for x in range(1,9)}
    zeros=iter(sorted(set(range(17))-set(targets.values())))
    return tuple(targets[x] if x else next(zeros) for x in state[cut:]+state[:cut])


def statistics(state,p,cut):
    inv=sum(a>b for i,a in enumerate(p) for b in p[i+1:])
    positive=[(i-cut)%17 for i,x in enumerate(state) if x]
    sigma=[]
    for i,x in enumerate(state):
        if x==0:
            j=(i-cut)%17
            sigma.append(sum((k<j and p[k]>p[j]) or (k>j and p[k]<p[j]) for k in positive))
    return inv,sigma


def audit(data):
    if data['format']!='lrx_nine_gap_comparison_certificate_v1' or data['m']!=8 or data['slots']!=list(range(9)):
        raise ValueError('unexpected bundle format')
    records=data['records'];expected=list(permutations(range(1,9)))
    if len(records)!=40320 or sorted(r['order_index'] for r in records)!=list(range(40320)):
        raise ValueError('incomplete or duplicate order universe')
    if any(tuple(r['labels'])!=expected[r['order_index']] for r in records):raise ValueError('order mapping mismatch')
    catalog=data['catalog'];infos=[profile(s['state'],s['word']) for s in catalog]
    slope_checks=0
    for source,info in zip(catalog,infos):
        for j in range(9):
            lengths=[1]*9;lengths[j]=2
            initial,word=stretch(source['state'],source['word'],lengths)
            if replay_visible(initial,word)!=tuple(range(1,9))+(0,)*10 or len(word)!=info['base']+info['beta'][j]:
                raise ValueError('literal stretch coefficient mismatch')
            slope_checks+=1
    @lru_cache(None)
    def reference(source,cut):
        if type(source) is not int or not 0<=source<len(catalog) or type(cut) is not int or not 0<=cut<17:
            raise ValueError('invalid source/cut')
        info=infos[source]
        if cut in info['blocked']:raise ValueError('swap crosses cut')
        s=catalog[source]['state'];q=ranks(s,cut,info['finish']);inv,sigma=statistics(s,q,cut)
        if inv!=info['nx'] or sigma!=info['swaps']:raise ValueError('reference swap minimality')
        return [sorted(q[:j]) for j in range(1,18)]
    rows=0;letters=0;max_base=Fraction(0);used=set()
    for number,record in enumerate(records):
        state=[0]
        for x in record['labels']:state.extend([x,0])
        weights=[Fraction(row['weight']) for row in record['mixture']]
        if not weights or min(weights)<=0 or sum(weights)!=1:raise ValueError('invalid weights')
        bsum=Fraction(0);gsum=[Fraction(0)]*9;choices=[]
        cache={}
        for w,row in zip(weights,record['mixture']):
            source,cut=row['source'],row['cut'];qprefix=reference(source,cut);info=infos[source];used.add(source)
            key=(cut,info['finish'])
            if key not in cache:
                p=ranks(state,cut,info['finish']);inv,sigma=statistics(state,p,cut)
                cache[key]=(p,inv,sigma,[sorted(p[:j]) for j in range(1,18)])
            p,inv,sigma,prefix=cache[key]
            if any(a>b for pp,qq in zip(prefix,qprefix) for a,b in zip(pp,qq)):raise ValueError('dominance failure')
            if inv>info['nx'] or any(s<t or (s-t)%2 for s,t in zip(info['swaps'],sigma)):
                raise ValueError('negative or odd savings')
            base=info['base']-info['nx']+inv
            gamma=[b-s+t for b,s,t in zip(info['beta'],info['swaps'],sigma)]
            bsum+=w*base
            for j,g in enumerate(gamma):gsum[j]+=w*g
            choices.append((base,source,cut,p));rows+=1
        if bsum>=85 or max(gsum)>6:raise ValueError('mixture inequality failure')
        max_base=max(max_base,bsum)
        base,source,cut,p=min(choices);p=list(p);cursor=(-cut)%17;word=[]
        for c in catalog[source]['word']:
            if c=='X':
                if cursor==16:raise ValueError('comparison wraps cut')
                if p[cursor]>p[cursor+1]:
                    p[cursor],p[cursor+1]=p[cursor+1],p[cursor];word.append(c)
            else:cursor=(cursor+(1 if c=='L' else -1))%17;word.append(c)
        if p!=list(range(17)) or len(word)!=base or base>84 or replay_visible(tuple(state),''.join(word))!=ROOT:
            raise ValueError('comparison replay failure')
        letters+=len(word)
        if (number+1)%5000==0:print(json.dumps(dict(checked=number+1)),flush=True)
    if used!=set(range(len(catalog))):raise ValueError('unused catalog references')
    return dict(status='PASS',orders=len(records),reference_words=len(catalog),mixture_rows=rows,
        literal_stretch_checks=slope_checks,reference_cut_checks=reference.cache_info().currsize,unit_comparison_words=len(records),
        unit_comparison_letters=letters,max_weighted_base=str(max_base),
        scope='Nine-gap certificate inequalities and word premises independently checked; general-length conclusion uses the paper lemmas. Projection counts and <=3-block dependency not rechecked.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('archive');ap.add_argument('output');args=ap.parse_args()
    out=Path(args.output)
    if out.exists():raise FileExistsError(out)
    start=time.perf_counter();raw=Path(args.archive).read_bytes()
    with zipfile.ZipFile(args.archive) as z:data=json.loads(z.read(MEMBER))
    report=audit(data);report.update(seconds=time.perf_counter()-start,archive_sha256=hashlib.sha256(raw).hexdigest(),
        auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
