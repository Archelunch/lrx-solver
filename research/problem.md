# Problem and exact computations

The visible vectors permute `(1,...,m,0^r)`, with `n=m+r`. L rotates left,
R rotates right, and X exchanges the first two entries. The canonical root
is fixed; its eccentricity is the sorting radius, not the graph diameter.

For `m>=8, r>=2` the **open conjecture** is

    E_r(n) <= T_m(n) = m(m+1)/2 + (r-1)(m-2).

There are `n!/r!` visible states and `n!/(r-1)!` distinguished-zero states.
Never substitute a single distinguished-root eccentricity for the visible radius.

## Marked-zero projection

Deleting one distinguished zero gives `(u,j)`. The accepted terminal set consists
of the smaller canonical root and **any** insertion position `j>=m`.

| Operation | Condition | Result |
|---|---|---|
| L | j=0 | (u,n-1) |
| L | j>0 | (Lu,j-1) |
| R | j=n-1 | (u,0) |
| R | j<n-1 | (Ru,j+1) |
| X | j<2 | (u,1-j) |
| X | j>=2 | (Xu,j) |

Count a projection step exactly when u changes. Do **not** cancel inverse
projected moves. Zero-projection movement connects positions `1--0--n-1`;
other positions have their own zero-length self path and cannot be omitted.

`F_e(u,j)` minimizes full word length with projection length at most `d(u)+e`.
`H_q(u,j)` minimizes it with projection length at most `q`.
Thus `F_e(u,j)=H_(d(u)+e)(u,j)`.

F uses `c=1+d(u')-d(u)` and processes states in `(e,d(u))` order.
H decreases q on every projection-changing transition.
Both use the exact zero-projection closure. H enumerates smaller states using
BFS in this reference implementation but does not use BFS distances in its recurrence.

The current implementation retains bounded layers for witness reconstruction;
it is not a memory-optimized C++ replacement.

## Next research target

Let `P=E_(r-1)(n-1)`. Evaluate

    A_P(v) = min_{j:v[j]=0} H_P(v without j,j) <= P+m-2.

This is a stronger lifting claim, not the original conjecture.
Alternatively use `Q=T_m(n-1)` and test `min_j H_Q <= Q+m-2`.
The latter would suffice inductively without proving the stronger radius recursion.

Failure to find a heuristic word is not a distance lower bound.
A finite DP failure concerns its restricted class of projections.
Resource exhaustion is INCOMPLETE, never mathematical infinity.
