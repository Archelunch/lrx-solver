# Session 08 — exact new mixtures after projection

The local phase produced **76 exact family certificates** at m=8, with no
API calls or new dependencies. Each certificate covers arbitrary positive
lengths of its retained zero blocks using the reviewed comparison/stretching
lemmas. The general conjecture and full m=8 case remain open.

## Frozen experiment and results

We selected source-reported unresolved families with 4–8 retained gaps:
20 development and 10 confirmation families per block count. For each selected
family we independently recomputed the inherited mixture's projected base
price and checked exclusion from the supplied reverse-order transfer domains.
This is a selected-case baseline, not a reconstruction of the global union.

| Retained blocks | Development certified / 20 | Confirmation certified / 10 |
|---|---:|---:|
| 4 | 14 | 7 |
| 5 | 10 | 6 |
| 6 | 10 | 5 |
| 7 | 10 | 3 |
| 8 | 8 | 3 |
| Total | **52/100** | **24/50** |

The original inherited weights fail the base-price criterion on every one of
these 150 cases. The successful new certificates consist of:

- **60 families** using the inherited word support: 39 development, 21 confirmation;
- **16 more families** using a fixed seeded pool of 128 existing catalog words
  and their admissible projected cuts: 13 development, 3 confirmation.

No new reference words were generated. The available catalog has 4,670 words;
most were not searched in the expanded-pool stage. The 74 misses are only
failures to find a certificate in this bounded search. We do not certify LP
optimality or infeasibility, even when the numerical solver reports an optimum.

The fixed method took 3.255s on development and 1.754s on confirmation,
excluding inventory decoding and later audits. These are single-run timings,
not a controlled benchmark. The largest retained nondominated LP had 13 columns
on development and 11 on confirmation. No run hit the 500-pivot limit.

## What actually improved

A small standard-library two-phase simplex chooses a basis numerically.
The basis is solved again with exact rational arithmetic. Acceptance requires
nonnegative weights summing exactly to one, weighted base <31+6k, and every
retained slope <=6. Candidate profiles are reconstructed from immutable
catalog references before acceptance; model-provided resource values are
never trusted. Negative or numerically unreliable reconstruction is a miss.

Projection coefficients are recomputed rather than merely inheriting the
nine-gap upper bounds. A development-only ablation, run after the experiment,
finds 38 certificates using reweighted inherited support with old coefficient
bounds, versus 39 using recomputed bounds. Thus reweighting itself explains
most of the inherited-support gain; tighter projection bounds add one case.
This ablation did not change or select the confirmation method.

GEPA, AdaEvolve and EvoX were **not run in this session**. The successful
search was deterministic weight optimization, exactly the cheap first phase
of the agreed plan. No paid phase was needed. A mixture-domain adapter for
those planners is still future work; the prior lifting adapter remains intact.

## Concrete infinite-family certificate

For positive a,b,c,d, consider

    v=(4,0^a,8,3,0^b,6,0^c,1,5,0^d,7,2).

This is mask 90, label order index 19755. Let z=(a-1,b-1,c-1,d-1).
Four projected comparison words have rational weights

    (1/3, 1/5, 1/15, 2/5),

with weighted base **797/15** and weighted slopes **(6,6,5,6)**.
Therefore their weighted cost is bounded by

    797/15 + 6z_1 + 6z_2 + 5z_3 + 6z_4
      < 55 + 6(z_1+z_2+z_3+z_4) = T(v)+1.

At least one actual sorting word is no longer than this average. Its integer
length is at most T(v)=6n-18. This certifies all positive a,b,c,d, not just the
three expanded words saved as additional replay checks. The inherited weighted
base was 2757/49 >=55, so the old weights did not certify this family.

The source/cut references and exact weights are in the first entry of
`train-v2-results.json`; full source data are pinned by `manifest-v2.json`.
The argument uses the manuscript's reviewed comparison/stretching lemmas,
not a new standalone formalization of those lemmas or a claim of historical
novelty beyond the supplied covering methods.

## Verification and scope

A separate audit computed 226 unique projected reference words by repeatedly
deleting marked zeros through the locked CertificateValidator, then compared
those words with the search-side projection interpreter. Every comparison
agreed. It reconstructed all 227 support components and replayed **1,811**
expanded component words. Every accepted component has a uniform-sign affine
rotation profile; the more general upper-bound path was unnecessary here.
Exact weights and stored cost bounds were checked again. See
`certificate-audit.json` and `audit_results.py`.

New tests cover all 511 nonempty deletion masks on a reference word, literal
multivariate expansion, corrupt input, exact strict-bound rejection, residual
byte encoding, and numerical LP proposals against exact vertex enumeration
(including 80 small two-dimensional problems). **327 tests pass**, compileall
and CLI smoke pass, trusted hashes remain unchanged. The auditor and optimizer
are search-side code; the trusted lock was not edited.

The residual inventory has 4,495,529 entries consistent with its supplied
boolean table. That is an encoding consistency check, not an independent
proof of the reported global union coverage. Accordingly we do not simply
increase the manuscript's 16,107,991 total by 76 or claim a newly verified
remaining-family count. We certify these 76 named families and their
exclusion from the checked baseline methods on these cases.

## Preserved failed attempt

The first sampler interpreted a hexadecimal byte string as a big-endian
integer. Its fifth development case was already covered by inherited weights,
so the baseline guard stopped execution. No confirmation optimization ran.
The corrected decoder reads little-endian bytes and checks every residual bit
against the supplied NPY boolean matrix without NumPy or pickle. Original
files and logs are preserved; only version-2 results count. See
`protocol-correction.md`. This was an input-codec bug, not a mathematical
counterexample or disagreement between trusted replay engines.

## Accounting and next step

API cost: **$0**. Current research budget remaining: **$19.851381**.
No archive code was imported or executed; no dependencies were installed.
The legacy spend ledger remains a separate historical-accounting limitation.

The next cheap experiment is a wider existing-catalog search on unresolved
**development** families, with fresh structural confirmation frozen before
any new method selection. Expand beyond the 128-word pool toward the complete
4,670-word catalog, and measure how many failures are catalog limitations
rather than search limitations. Only then consider new word generation or
EvoX/GEPA/AdaEvolve policies for allocating expensive catalog search. Preserve
all accepted exact certificates as an immutable archive. Further global
coverage claims require reconciling the full baseline and its dependencies.
