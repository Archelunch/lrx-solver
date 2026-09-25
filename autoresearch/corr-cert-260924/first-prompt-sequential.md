# First sequential control prompt (corr-cert-260924)

This is the exact `messages` array the sequential control client sends to the local broker on iteration 1 for the seed program. The broker forwards it unchanged, adding only transport fields (see `broker-config.json` and the `--dry-run` payload). It was captured offline from a zero-provider run with the frozen development set. Only development data (m=4..12) appears; the holdout set (m=13..20) is never loaded.

- Messages SHA-256 (canonical JSON, sorted keys, no spaces): `9687177e0d54f6b009ad9f0981013a1891e57436aef7a50b8a3c1351b2653cfa`
- Message roles: ['system', 'user']. A separate system message carries the fixed background.
- Client request fields: model `gemini-3.8-flash`, max_tokens `8192`, reasoning_effort `low`
- Captured from: `run` (request-0001.json)
- A live sequential control run halts before its first model request if these messages hash differently.

## Message 1: system

``````text
Find universal coefficients for the Theorem 3 correlation certificate (THEOREM.md). The candidate source must define coefficients(m) -> dict returning the JSON-safe encoding: {'m': m, 'Q': positive int, 'lambda': {'a,b': int}, 'mu': {'a': [int]*(m-1)}, 'alpha'/'beta'/'gamma': {'a,b,c': [int]*(m-1)}} with comma-joined decimal keys, a<b or a<b<c, and mu[a] indexed q=1..m-1. All values must be exact Python ints. The source must be at most 64 KiB, use the standard library only, and finish each m within 10 seconds. The trusted evaluator decodes this into corrcert.py's cert dict and calls corrcert.check_certificate(m, cert) exactly: it passes iff every triple condition (5) and pair condition (6) holds and epsilon < 1. Misses prove nothing about any m. LP optimum is 0 for every m; E=0 only at the reversal orders p_i = -i mod m; forced tight rows at q = m-(b-a) and triple rows at (m-(b-a), m-(c-b)); linear potentials alpha=xq+c1, beta=xt+c2, gamma=-xs+c3 satisfy (5) iff c1+c2+c3<=0 and c1+c2+c3+xm<=0.
Two exact epsilon=0 certificates, printed compactly (indices a<b<...<m-1; mu_a and alpha/beta/gamma[a,b,c] are lists over q=1..m-1; a triple/pair not listed is all zero):
m=4, Q=1: lambda (0,1)=12 (0,2)=4 (0,3)=0 (1,2)=-24 (1,3)=-12 (2,3)=-20; mu_0=[-8,-4,0] mu_1=[-4,0,4] mu_2=[4,0,-4] mu_3=[0,-4,-8]; all alpha/beta/gamma=0 (pure linear potentials, no triple terms needed at m=4).
m=5, Q=1: lambda (0,1)=25 (0,2)=20 (0,3)=15 (0,4)=0 (1,2)=-15 (1,3)=0 (1,4)=-5 (2,3)=-35 (2,4)=-20 (3,4)=-35; mu_0=[-14,-18,3,4] mu_1=[-17,-9,-16,2] mu_2=[-10,0,0,-10] mu_3=[2,-16,-9,-17] mu_4=[4,3,-18,-14]; nonzero triples (16 nonzero entries, all +-5, each a width-2 run of consecutive q): (0,1,2) alpha=[0,-5,-5,0] beta=[0,0,0,5] gamma=[0,0,-5,0]; (0,1,4) alpha=[-5,-5,0,0] beta=[0,0,0,-5] gamma=[0,0,5,0]; (0,3,4) alpha=[0,0,0,-5] beta=[-5,-5,0,0] gamma=[0,0,5,0]; (2,3,4) alpha=[0,0,0,5] beta=[0,-5,-5,0] gamma=[0,0,-5,0].
A deterministic control already tried polynomial coefficients: degree<=3 polynomials in (a,b,c,m) plus step/indicator terms at the kappa thresholds, and q times those steps, fit m=4..8 exactly but failed at the first untried m=9 (about 1200 violated rows). The bottleneck is triples with a unit gap (b-a==1 or c-b==1); freeing only those triples' coefficients from the polynomial made the fit exact through m=10, so unit-gap triples need dependence the low-degree polynomials could not express. In the infeasibility structure, about 60% of the violation mass sits on wrapping rows (q+t>m) and about a third at the equality-order row q=m-(b-a); the heaviest gap classes are (b-a,c-b) in {(1,1),(1,2),(2,1),(1,3)}. This does not prescribe a fix; possibilities worth exploring include triple potentials depending on min/max of the gaps, floor/mod expressions, or piecewise definitions with breakpoints tied to both q and m-q. Every known epsilon=0 certificate is tight at the reversal-order rows q=m-(b-a) and (m-(b-a), m-(c-b)). coefficients(m) may compute its output algorithmically for the given m (loops, or a small exact linear solve restricted to the known-tight rows, are fine); it must stay standard-library and finish within 10 seconds per m regardless of method. A construction with a human-checkable argument for why it holds for every m is worth more than a lookup table over development m; the holdout set tests m your program has never seen. Do not read files, the network, or environment variables.
``````

## Message 2: user

``````text
Improve this executable Python coefficients(m) program. Return the entire replacement Python source in one fenced code block. Maximize the number of development m in 4..12 that pass corrcert.check_certificate exactly, then reduce the exact violation magnitude on m that fail. Only development instances are shown; a program that is uniform in m is far more valuable than one hard-coded per m.

Current program:
```python
"""Seed candidate for corr-cert-260924: the F1 linear-potential family from
FIT-SPEC.md ("linear potentials only ... mu_a(q) = y_a q + v_a ... zero
bumps"), with triple functions identically zero (the x=0, c1=c2=c3=0 point of
the linear family in THEOREM.md's structural note, which always satisfies
(5) with equality 0<=0) and mu_a(q) generalizing THEOREM.md's exact m=4
certificate (mu_0=4(q-3), mu_1=4(q-2), mu_2=-4(q-2), mu_3=-4(q-1) at Q=1) by
the single formula mu_a(q) = 4*(q - (m-1-a)) for every a, not only the
reversal-symmetric half. This is a literal, honest first guess, not a fit:
FIT-SPEC.md is explicit that no closed form is established, and PATTERNS.md
shows mu_a(q) is not linear in q for m >= 5. It is expected to score well
only at m = 4 (where it reduces to the group's exact certificate) and is
reported here, unmodified, together with its real corr_evaluator score for
m = 4..12 -- it is not hand-tuned to pass.

Stdlib only. Output is the JSON-safe encoding documented in
integrations/corr_task.py (encode_cert): lambda/alpha/beta/gamma keyed by
comma-joined ints "a,b" / "a,b,c", mu keyed by "a".

MULT is the one tunable knob (search-and-replace target for mock proposers
in offline smokes; a live model may edit it too): the slope of mu_a(q) in q.
"""

MULT = 4


def coefficients(m):
    Q = 1
    lam = {"%d,%d" % (a, b): 0 for a in range(m) for b in range(a + 1, m)}
    mu = {str(a): [MULT * (q - (m - 1 - a)) for q in range(1, m)] for a in range(m)}
    zero = [0] * (m - 1)
    alpha, beta, gamma = {}, {}, {}
    for a in range(m):
        for b in range(a + 1, m):
            for c in range(b + 1, m):
                key = "%d,%d,%d" % (a, b, c)
                alpha[key] = list(zero)
                beta[key] = list(zero)
                gamma[key] = list(zero)
    return {"m": m, "Q": Q, "lambda": lam, "mu": mu, "alpha": alpha, "beta": beta, "gamma": gamma}

```

Evaluator feedback:
CORR_PACKET_V1 (development only; search signal, not proof)
this candidate: 0/9 m passing, violation_sum 233998.000; best so far: 0/9 passing, violation_sum 233998
- m=4 FAIL: epsilon=-22, failure=None
  pair6 (a,b)=(2,3) gap=(b-a=1) q=1 slack=-36 kappa_ab(q)=-24
  pair6 (a,b)=(2,3) gap=(b-a=1) q=3 slack=-36 kappa_ab(q)=-24
  pair6 (a,b)=(1,3) gap=(b-a=2) q=1 slack=-32 kappa_ab(q)=-24
- m=5 FAIL: epsilon=-48, failure=None
  pair6 (a,b)=(3,4) gap=(b-a=1) q=4 slack=-64 kappa_ab(q)=-48
  pair6 (a,b)=(3,4) gap=(b-a=1) q=1 slack=-58 kappa_ab(q)=-42
  pair6 (a,b)=(2,3) gap=(b-a=1) q=4 slack=-56 kappa_ab(q)=-48
- m=6 FAIL: epsilon=-90, failure=None
  pair6 (a,b)=(3,4) gap=(b-a=1) q=5 slack=-104 kappa_ab(q)=-92
  pair6 (a,b)=(4,5) gap=(b-a=1) q=5 slack=-100 kappa_ab(q)=-80
  pair6 (a,b)=(3,5) gap=(b-a=2) q=1 slack=-84 kappa_ab(q)=-68
- m=7 FAIL: epsilon=-152, failure=None
  pair6 (a,b)=(4,5) gap=(b-a=1) q=6 slack=-164 kappa_ab(q)=-148
  pair6 (a,b)=(5,6) gap=(b-a=1) q=6 slack=-144 kappa_ab(q)=-120
  pair6 (a,b)=(3,4) gap=(b-a=1) q=6 slack=-128 kappa_ab(q)=-120
- m=8 FAIL: epsilon=-238, failure=None
  pair6 (a,b)=(5,6) gap=(b-a=1) q=7 slack=-236 kappa_ab(q)=-216
  pair6 (a,b)=(4,5) gap=(b-a=1) q=7 slack=-196 kappa_ab(q)=-184
  pair6 (a,b)=(6,7) gap=(b-a=1) q=7 slack=-196 kappa_ab(q)=-168
- m=9 FAIL: epsilon=-352, failure=None
  pair6 (a,b)=(6,7) gap=(b-a=1) q=8 slack=-320 kappa_ab(q)=-296
  pair6 (a,b)=(5,6) gap=(b-a=1) q=8 slack=-276 kappa_ab(q)=-260
  pair6 (a,b)=(7,8) gap=(b-a=1) q=8 slack=-256 kappa_ab(q)=-224
- m=10 FAIL: epsilon=-498, failure=None
  pair6 (a,b)=(7,8) gap=(b-a=1) q=9 slack=-416 kappa_ab(q)=-388
  pair6 (a,b)=(6,7) gap=(b-a=1) q=9 slack=-368 kappa_ab(q)=-348
LP optimum is 0 for every m; E=0 only at the reversal orders p_i = -i mod m; forced tight rows at q = m-(b-a) and triple rows at (m-(b-a), m-(c-b)); linear potentials alpha=xq+c1, beta=xt+c2, gamma=-xs+c3 satisfy (5) iff c1+c2+c3<=0 and c1+c2+c3+xm<=0.
``````
