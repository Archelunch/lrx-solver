# Offline replay of completed provider output

This is a zero-provider **offline replay** of the completed Grok source that the
live budget broker rejected after its reasoning-token reservation was exceeded.
It is not another live Grok turn, an accepted live GEPA proposal, or a new
engine comparison. The exact frozen source is
`../broker-rejected-complete-proposal.py` (SHA-256
`d061094815415ad528e1f195423df107ac47aab4a33679bc936ab07cee1f6619`).
GEPA's selected `output/best.py` has the same source except for its terminal
newline (SHA-256 `e33fb8a21e0904c2899d63843e604d10e09503a3af01701ec8f8f07c372fc3ac`).

Pinned GEPA 0.1.4 received that source through `--offline-proposal` and made
one native reflection. Its hard-case minibatch included
`k5-mask302-order15713`; GEPA selected the proposal after a subsample score
change from 0 to 0.37766530943592475 and a full 16-case score change from 0
to 0.023604081839745297. The trusted coordinator rechecked the selected
program: 16/16 candidate executions were OK, 15/16 exact finite development
families certified, zero new certificates versus the frozen incumbent, and
exact graded secondary score `14887/630696`. K5 remains uncertified.

`manifest.json`, `output/summary.json`, `console.log`, and
`verified/e33fb8a21e0904c2-evaluation.json` are the raw evidence. The
development archive was copied to `../offline-replay-02-input/` before this
run; the tracked initial archive was unchanged. No broker was running and no
model request was made. The first replay in `../offline-replay-01/` is retained:
native GEPA selected the same candidate, but coordinator finalization raised
on the exact fractional secondary score. A search-side `Fraction` parsing fix
and regression test preceded this second replay.
