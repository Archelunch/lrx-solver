"""Turn marginal choices of complementary arcs into explicit word mixtures.

No coverage conjecture is assumed. Each output word is replayed by the existing
symbolic verifier; profile changes and all mixture weights are exact.
"""
from collections import defaultdict
from fractions import Fraction
from multiset_zero_stretch import certificate


def flipped_word(word,cert,n,chosen):
    parts=word.split('X');assert len(parts)==len(cert['gaps'])
    pieces=[]
    for index,(part,(constant,coeff)) in enumerate(zip(parts,cert['gaps'])):
        assert set(part)<=set('LR') and part.count('L')-part.count('R')==constant
        if index in chosen:
            assert abs(constant)<n and any(coeff) and all(abs(c)<=1 for c in coeff)
            sign=1 if constant>0 else -1 if constant<0 else 1 if any(c>0 for c in coeff) else -1
            constant-=sign*n
            part=('L' if constant>=0 else 'R')*abs(constant)
        pieces.append(part)
    return 'X'.join(pieces)


def materialize_circle_rows(state,rows):
    state=tuple(state);n=len(state);m=max(state);target=tuple(range(1,m+1))+(0,)*(n-m)
    aggregate=defaultdict(Fraction);expected_base=Fraction(0);expected_beta=[Fraction(0)]*(n-m)
    source_total=Fraction(0)
    for row in rows:
        weight=Fraction(row['weight']);assert weight>=0;source_total+=weight
        word=row['word'];cert=certificate(state,word);assert cert['final']==target
        assert cert['base_cost']==row['base_cost'] and list(cert['beta'])==list(row['beta'])
        probabilities={}
        for choice in row.get('flips',[]):
            gap=choice['gap'];probability=Fraction(choice['probability'])
            assert type(gap) is int and 0<=gap<len(cert['gaps']) and gap not in probabilities
            assert 0<=probability<=1
            c,coeff=cert['gaps'][gap]
            assert abs(c)<n and any(coeff) and all(abs(v)<=1 for v in coeff)
            probabilities[gap]=probability
        mean_base=Fraction(cert['base_cost']);mean_beta=list(map(Fraction,cert['beta']))
        for gap,probability in probabilities.items():
            c,coeff=cert['gaps'][gap];mean_base+=probability*(n-2*abs(c))
            mean_beta=[b+probability*(1-2*abs(v)) for b,v in zip(mean_beta,coeff)]
        expected_base+=weight*mean_base
        expected_beta=[b+weight*c for b,c in zip(expected_beta,mean_beta)]
        cuts=sorted({Fraction(0),Fraction(1),*probabilities.values()})
        for left,right in zip(cuts,cuts[1:]):
            chosen={gap for gap,p in probabilities.items() if p>=right}
            new_word=flipped_word(word,cert,n,chosen);actual=certificate(state,new_word)
            base=cert['base_cost'];beta=list(cert['beta'])
            for gap in chosen:
                c,coeff=cert['gaps'][gap];base+=n-2*abs(c)
                beta=[b+1-2*abs(v) for b,v in zip(beta,coeff)]
            assert actual['final']==target and actual['base_cost']==base and actual['beta']==tuple(beta)
            aggregate[new_word]+=weight*(right-left)
    assert source_total==1 and sum(aggregate.values())==1
    result=[];mean_base=Fraction(0);mean_beta=[Fraction(0)]*(n-m)
    for word,weight in sorted(aggregate.items()):
        if not weight:continue
        cert=certificate(state,word)
        result.append(dict(word=word,weight=str(weight),base_cost=cert['base_cost'],beta=list(cert['beta'])))
        mean_base+=weight*cert['base_cost'];mean_beta=[b+weight*c for b,c in zip(mean_beta,cert['beta'])]
    assert mean_base==expected_base and mean_beta==expected_beta
    return result


def circle_certificate(state,words):
    from search_multiset_zero_stretch import circle_mixture,verify
    result=circle_mixture(tuple(state),list(words))
    if not result['certified']:return result
    rows=materialize_circle_rows(state,result['rows'])
    checked=verify(state,rows)
    return dict(certified=True,method='materialized_circle_mixture',rows=rows,checked=checked,
                original_rows=len(result['rows']),explicit_words=len(rows))
