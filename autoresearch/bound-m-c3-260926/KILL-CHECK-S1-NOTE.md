# Seed-1 kill check (2026-09-26)

First attempt crashed in the evaluator's worker kill path (EPERM under Seatbelt) and, after that fix,
in kill_check's relative_to on a relative campaign path; both fixed (commits 466d01b, e666b94; the
evaluator kill helper changes the approval hash, so seeds 2 and 3 need re-approval).

Second attempt (offline, validation m=11, 165 families, first 15 fully evaluated distinct proposals
per arm): sequential best 157 (9 accepted), AdaEvolve best 159 (11 accepted), EvoX best 157 (5
accepted), GEPA no accepted proposal. The seed scored 111 in that run, against 157 at prep: a direct
re-evaluation under the same machine load gave 154 with 3 wall timeouts (the C oracle for the
middle band was saturating the CPU, load average about 23). The 111 is therefore a load artefact,
not the seed's score. Against the prep score 157: AdaEvolve 159 beats the seed, sequential and
EvoX tie. Verdict under the pre-registered rule: CONTINUE (at least one arm beats the seed).

Caveat for the seed-1 runs themselves: they overlapped the C oracle from about 13:20, so development
evaluations of candidates may have suffered wall timeouts; finalize re-evaluates every finalist, and
the oracle processes were reniced to 19 before any further run.
