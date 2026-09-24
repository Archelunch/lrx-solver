"""Exact verifier for refined affine leaves and exhaustive split trees.

No optimizer and no distance oracle are imported. Box coordinates are
positive integer lengths of the zero atoms in the original base.
"""
from collections import Counter
from fractions import Fraction
from multiset_free_phase import replay
from multiset_zero_stretch import certificate,checked_lift,expanded_state


def target(n,m):
    return (m-2)*n-(m*m-3*m-4)//2


def check_base(base):
    base=tuple(base);m=max(base)
    assert m>=8 and base.count(0)>=1
    assert sorted(v for v in base if v)==list(range(1,m+1))
    return m,base.count(0)


def check_box(lower,upper,s):
    assert len(lower)==len(upper)==s
    assert all(type(v) is int and v>=1 for v in lower)
    assert all(v is None or (type(v) is int and v>=lo) for lo,v in zip(lower,upper))


def row_profile(base,row,lower):
    m,s=check_base(base)
    origin=row['origin'];picks=row['picks']
    assert len(origin)==len(picks)==s
    assert all(type(v) is int and 1<=v<=lo for v,lo in zip(origin,lower))
    refined=expanded_state(base,origin)
    cert=certificate(refined,row['word'])
    assert cert['final']==replay(refined,row['word'])==tuple(range(1,m+1))+(0,)*sum(origin)
    assert cert['base_cost']==row['base_cost']==len(row['word'])
    beta=[];start=0
    for length,pick in zip(origin,picks):
        assert type(pick) is int and start<=pick<start+length
        beta.append(cert['beta'][pick]);start+=length
    assert beta==row['beta']
    value=row['base_cost']+sum(b*(lo-o) for b,lo,o in zip(beta,lower,origin))
    return value,beta


def verify_leaf(base,rows,lower,upper):
    m,s=check_base(base);check_box(lower,upper,s)
    assert rows
    weights=[Fraction(row['weight']) for row in rows]
    assert all(w>=0 for w in weights) and sum(weights)==1
    mean=Fraction(0);beta=[Fraction(0)]*s
    for row,w in zip(rows,weights):
        value,coefficients=row_profile(base,row,lower)
        mean+=w*value
        beta=[b+w*c for b,c in zip(beta,coefficients)]
    worst=mean-target(m+sum(lower),m)
    for b,lo,hi in zip(beta,lower,upper):
        if hi is None: assert b<=m-2
        else: worst+=max(Fraction(0),(b-(m-2))*(hi-lo))
    assert worst<1
    return dict(mean_at_lower=str(mean),mean_beta=list(map(str,beta)),worst_excess=str(worst))


def verify_tree(base,tree):
    _,s=check_base(base);counts=Counter()
    def visit(node,lower,upper,depth):
        counts['nodes']+=1;counts['max_depth']=max(counts['max_depth'],depth)
        assert isinstance(node,dict)
        if node.get('kind')=='split':
            axis,cut=node['axis'],node['cut']
            assert type(axis) is int and 0<=axis<s
            assert type(cut) is int and lower[axis]<=cut
            assert upper[axis] is None or cut<upper[axis]
            left_upper=list(upper);left_upper[axis]=cut
            right_lower=list(lower);right_lower[axis]=cut+1
            visit(node['left'],lower,left_upper,depth+1)
            visit(node['right'],right_lower,upper,depth+1)
            counts['splits']+=1
        else:
            assert node.get('kind')=='affine'
            checked=verify_leaf(base,node['rows'],lower,upper)
            if 'checked' in node: assert checked==node['checked']
            counts['leaves']+=1;counts['words']+=len(node['rows'])
            counts['refined_rows']+=sum(any(v>1 for v in row['origin']) for row in node['rows'])
    visit(tree,[1]*s,[None]*s,0)
    return dict(counts)


def lifted_row(base,row,lengths):
    origin=row['origin']
    assert all(ell>=o for ell,o in zip(lengths,origin))
    refined=expanded_state(base,origin)
    atom_lengths=[1]*sum(origin)
    for ell,o,pick in zip(lengths,origin,row['picks']):
        atom_lengths[pick]+=ell-o
    assert expanded_state(refined,atom_lengths)==expanded_state(base,lengths)
    result=checked_lift(refined,row['word'],atom_lengths)
    assert len(result)==row['base_cost']+sum(b*(ell-o) for b,ell,o in zip(row['beta'],lengths,origin))
    return result


def word_for(base,tree,lengths):
    m,s=check_base(base)
    assert len(lengths)==s and all(type(ell) is int and ell>=1 for ell in lengths)
    node=tree
    while node.get('kind')=='split':
        node=node['left'] if lengths[node['axis']]<=node['cut'] else node['right']
    assert node.get('kind')=='affine'
    word=min((lifted_row(base,row,lengths) for row in node['rows']),key=len)
    assert len(word)<=target(m+sum(lengths),m)
    assert replay(expanded_state(base,lengths),word)==tuple(range(1,m+1))+(0,)*sum(lengths)
    return word
