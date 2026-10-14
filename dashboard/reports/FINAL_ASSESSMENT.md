# Final assessment — 13 October 2026

The current study is inconclusive about learned improvements over LLVM `-O3`.
It does not establish that the objective is impossible. It also does not
establish that supervised learning or reinforcement learning improves performance.

## What is complete

The expanded native benchmark corpus contains 21 training implementations and
42 correctness inputs. The preceding iteration verified all four compiler
settings on these inputs and reported 123 passing tests. Two new development
implementations remain untouched. A portable source runner, pinned upstream
archives, independent correctness oracles, grouped model validation code and
immutable experiment records are available.

The earlier BLAKE2 result showed about 12.1% less CPU time for one selected
training workload. This is evidence of case-specific optimization headroom,
not a learned or generalizable result. The preceding supervised study produced
no qualified learned selector; the operational recommendation remains O3.

## Why performance evaluation stops here

The expanded study's declared admission rule required six identical-O3 controls
to qualify on both CPU and wall clocks, followed by independent confirmation.
All five available logical CPUs were tested, retaining 90 cells and 2,160 pairs.
None qualified. Consequently, the expanded experiment produced no training
labels, fitted models or held-out performance results.

On 13 October, the available environment still reports the same CPU model,
kernel, five logical CPUs and four-CPU quota as the recorded context. These
observations cannot prove host identity or current timing stability. They also
do not establish a quieter execution target. No additional timing run was
started, and no admission threshold was relaxed after observing the failures.

The frozen base context and original gate, three-core screen, CPU0 screen and
empty conditional confirmations were reverified without resampling. All four
screen/confirmation hashes and the original gate hash match the previous audit.
The initial verification invocation used an incorrect helper signature; the
corrected invocation completed successfully without changing the evidence.
Machine-readable results are in `results/final_assessment_20261013.json`.

## Decision and remaining work

Conclude the current cloud performance study as inconclusive due to failed
measurement admission. Preserve the project as a functioning experimental
prototype with an unproven research outcome. Do not claim the full SL/RL/hybrid
goal is complete or infer a completion percentage from the benchmark count.

Reopen performance evaluation only when a meaningfully changed execution
environment is available. A new isolated cloud target can suffice; ownership
of a Linux computer is not required. No such target has been provisioned here.
Fresh source builds and a separately declared admission/confirmation must pass
before collecting labels, fitting the fixed model candidates and opening the
two development implementations. Even a successful run can find no learned gain.

GPT-6.1 Sol High is sufficient for implementation and analysis. Greater model
effort does not provide control over host scheduling or CPU frequency.
No further iteration count or improvement guarantee is justified.

This assessment and its verification record are local workspace files. They
have not been committed or pushed to GitHub. Existing experiment snapshots
remain unchanged and do not include this later assessment.
