"""Small deterministic two-phase simplex proposer, with exact reconstruction.

Floating point chooses a basis only. Returned weights and inequalities are
checked with Fraction. No failure here proves mathematical infeasibility.
"""
from fractions import Fraction


def solve(matrix, rhs, exact=False):
    n=len(rhs);cast=Fraction if exact else float
    a=[[cast(x) for x in row]+[cast(y)] for row,y in zip(matrix,rhs)]
    for j in range(n):
        pivot=max(range(j,n),key=lambda i:abs(a[i][j]))
        if (a[pivot][j]==0 if exact else abs(a[pivot][j])<1e-10):return None
        a[j],a[pivot]=a[pivot],a[j];div=a[j][j]
        a[j]=[v/div for v in a[j]]
        for i in range(n):
            if i!=j:
                div=a[i][j]
                a[i]=[v-div*w for v,w in zip(a[i],a[j])]
    return [row[-1] for row in a]


def optimize(profiles,limit=500):
    if not profiles:return dict(status='NO_CERTIFICATE',reason='empty support')
    k=len(profiles[0]['gamma']);n=len(profiles);m=k+1
    columns=[list(p['gamma'])+[1] for p in profiles]
    columns += [[int(i==j) for i in range(m)] for j in range(k)]
    columns.append([0]*k+[1]);art=len(columns)-1
    basis=list(range(n,n+k))+[art];rhs=[6]*k+[1];pivots=0
    def matrix():return [[columns[j][i] for j in basis] for i in range(m)]
    for phase in (1,2):
        costs=[0]*art+[-1] if phase==1 else [-p['base'] for p in profiles]+[0]*(k+1)
        while pivots<limit:
            b=matrix();values=solve(b,rhs)
            if values is None or min(values)<-1e-7:return dict(status='NO_CERTIFICATE',reason='numerical basis failure')
            dual=solve(list(map(list,zip(*b))),[costs[j] for j in basis])
            if dual is None:return dict(status='NO_CERTIFICATE',reason='singular dual basis')
            available=range(art+1 if phase==1 else art)
            # Bland's index rule limits cycling on highly degenerate slope faces.
            enter=next((j for j in available if j not in basis and costs[j]-sum(x*y for x,y in zip(dual,columns[j]))>1e-8),None)
            if enter is None:break
            direction=solve(b,columns[enter]);eligible=[i for i,d in enumerate(direction) if d>1e-9]
            if not eligible:return dict(status='NO_CERTIFICATE',reason='unbounded numerical proposal')
            leave=min(eligible,key=lambda i:(max(0,values[i])/direction[i],basis[i]))
            basis[leave]=enter;pivots+=1
        else:return dict(status='NO_CERTIFICATE',reason='pivot cap',pivots=pivots)
        if phase==1:
            if art in basis:
                pos=basis.index(art)
                if values[pos]>1e-7:return dict(status='NO_CERTIFICATE',reason='phase I did not find feasibility')
                for j in range(art):
                    if j not in basis:
                        d=solve(matrix(),columns[j])
                        if d is not None and abs(d[pos])>1e-9:basis[pos]=j;break
                else:return dict(status='NO_CERTIFICATE',reason='degenerate artificial basis')
    exact=solve(matrix(),rhs,exact=True)
    if exact is None or min(exact)<0:return dict(status='NO_CERTIFICATE',reason='exact basis rejected')
    weights=[Fraction(0)]*n
    for j,w in zip(basis,exact):
        if j<n:weights[j]=w
    if sum(weights)!=1 or any(sum(w*p['gamma'][j] for w,p in zip(weights,profiles))>6 for j in range(k)):
        return dict(status='NO_CERTIFICATE',reason='exact inequalities rejected')
    base=sum(w*p['base'] for w,p in zip(weights,profiles))
    return dict(status='CERTIFICATE' if base<31+6*k else 'NO_CERTIFICATE',
        reason='exact feasible weights; optimum not independently certified',
        weights=[str(w) for w in weights],base=str(base),pivots=pivots)
