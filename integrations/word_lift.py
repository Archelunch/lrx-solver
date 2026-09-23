"""Exact routing of an added zero through a *fixed* projection word.

Search-side construction, not an exact decision over all projection words.
No generated code is executed. Successful words are independently replayed.
"""
from src.lrx.certificates import CertificateValidator
from src.lrx.state import validate_vector


def _closure(j, n):
    if j == 0:
        return ((0, ''), (1, 'X'), (n-1, 'L'))
    if j == 1:
        return ((1, ''), (0, 'X'), (n-1, 'XL'))
    if j == n-1:
        return ((n-1, ''), (0, 'R'), (1, 'RX'))
    return ((j, ''),)


def _project(letter, j, n):
    if letter == 'L':
        return j-1 if j > 0 else None
    if letter == 'R':
        return j+1 if j < n-1 else None
    return j if j >= 2 else None


def _validate(m, r, u, j, word):
    if type(m) is not int or type(r) is not int or m < 2 or r < 1:
        raise ValueError('requires m >= 2 and r >= 1')
    n = m+r
    if type(j) is not int or not 0 <= j < n:
        raise ValueError('invalid marked position')
    u = tuple(u)
    validate_vector(u, m, r-1)
    if not isinstance(word, str) or any(c not in 'LRX' for c in word):
        raise ValueError('invalid projection word')
    w = u
    for c in word:
        v = w[1:]+w[:1] if c == 'L' else w[-1:]+w[:-1] if c == 'R' else (w[1],w[0])+w[2:]
        if v == w:
            raise ValueError('every projected letter must change the smaller vector')
        w = v
    if w != tuple(range(1,m+1))+(0,)*(r-1):
        raise ValueError('projection word does not sort the smaller vector')
    return u


def lift_fixed_word(m, r, u, j, word):
    """Shortest full lift projecting exactly to word, or fixed-word infeasibility.

    O((m+r)(len(word)+1)) operations and storage. Infeasibility is only for
    this letter word, not H_q or A_q. All accepted terminal marks are used.
    """
    u = _validate(m,r,u,j,word)
    n = m+r
    inf = 3*len(word)+3
    costs = [inf]*n
    final = [None]*n
    for a in range(n):
        for b, repair in _closure(a,n):
            if b >= m and len(repair) < costs[a]:
                costs[a] = len(repair)
                final[a] = repair
    layers = []
    for c in reversed(word):
        nxt = [inf]*n
        policy = [None]*n
        for a in range(n):
            for b, repair in _closure(a,n):
                k = _project(c,b,n)
                if k is None or costs[k] == inf:
                    continue
                cost = len(repair)+1+costs[k]
                if cost < nxt[a]:
                    nxt[a] = cost
                    policy[a] = (repair+c,k)
        layers.append(policy)
        costs = nxt
    if costs[j] == inf:
        return {'status':'NO_FIXED_WORD_LIFT','length':None,'projection_length':len(word)}
    start_j = j
    pieces=[]
    for policy in reversed(layers):
        segment,j = policy[j]
        pieces.append(segment)
    pieces.append(final[j])
    full = ''.join(pieces)
    cert = CertificateValidator(m,r).replay_word(full,start_state=(u,start_j),max_steps=max(100_000,len(full)))
    if not (cert.replay_valid and cert.terminal and cert.projection_sequence == word
            and len(full) == costs[start_j]):
        raise AssertionError('fixed-word lift failed independent replay')
    return {'status':'WITNESS','length':len(full),'overhead':len(full)-len(word),
            'projection_length':len(word),'word':full,'projection_word':word}


def left_sweep_lift(m,r,u,j,word):
    """Greedy constructive lift for L/X words; endpoint condition is explicit.

    If it succeeds, overhead <= 2 floor((k+n-1-j)/(n-2)), k=#L.
    Failure rejects only this greedy construction, not all fixed-word lifts.
    """
    u = _validate(m,r,u,j,word)
    if 'R' in word:
        raise ValueError('left sweep requires an L/X projection word')
    n=m+r
    initial_j=j
    pieces=[]
    for c in word:
        if c == 'L':
            if j == 0:
                pieces.append('L')
                j=n-1
            pieces.append('L')
            j-=1
        else:
            if j == 1:
                pieces.append('XL')
                j=n-1
            elif j == 0:
                pieces.append('L')
                j=n-1
            pieces.append('X')
    if j == 0:
        pieces.append('L')
        j=n-1
    elif j == 1:
        pieces.append('XL')
        j=n-1
    upper=2*((word.count('L')+n-1-initial_j)//(n-2))
    if j < m:
        return {'status':'GREEDY_ENDPOINT_MISS','final_j':j,'overhead_bound':upper}
    full=''.join(pieces)
    cert=CertificateValidator(m,r).replay_word(full,start_state=(u,initial_j),max_steps=max(100_000,len(full)))
    overhead=len(full)-len(word)
    if not (cert.replay_valid and cert.terminal and cert.projection_sequence==word
            and overhead<=upper):
        raise AssertionError('left-sweep construction failed independent replay')
    return {'status':'WITNESS','word':full,'length':len(full),'overhead':overhead,
            'overhead_bound':upper,'projection_length':len(word),'final_j':j}
