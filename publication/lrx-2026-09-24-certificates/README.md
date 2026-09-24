# Shareable LRX certificates

[REPORT.md](REPORT.md) states and proves two exact `m=8` named-family bounds: one six-block arrangement for every positive length vector, and one five-block arrangement when its first zero block has length at least two. It includes complete unit words, rational weights and resource profiles, the direct-word expansion argument, and exact dual obstructions limited to frozen finite pools.

Run the accompanying standalone verifier from this directory with `python verify.py`. It reads `certificates.json` and checks the words, profiles, mixtures, dual inequalities, and sample literal expansions. The arbitrary-length proof is the algebra in the report; sample replays test the implementation.

These certificates concern only the two displayed LRX families. The canonical-root sorting radius conjecture remains open. The expansion and mixture method is from the user-supplied nine-gap `m=8` manuscript attributed to Chaos_ghost. The added columns are new relative to the specified frozen pools; no literature priority or global coverage count is claimed. Human mathematical peer review and Lean formalization are still pending.
