# Research-guided corpus and measurement iteration

This is the preserved 10 October iteration report. The later persistent-pair
CPU/wall study and its qualified training evidence are in [PAIRED_SL.md](PAIRED_SL.md).

The project now supports a pinned 30-kernel scientific corpus and LLVM 19.1.7,
alongside the preserved LLVM 10 application studies. Compilation and output
correctness improved; reliable new runtime labels remain blocked by this VM.
No new improvement over O3 is established, and the default policy remains O3.

## Research consulted

- [CompilerGym: Robust, Performant Compiler Optimization Environments for AI
  Research](https://arxiv.org/abs/2109.08267), Cummins et al.: motivates broader
  datasets, reproducible environments, amortizing empirical search with learning,
  and evaluating generalization across domains. Its instruction-count results
  are a different objective from runtime. The new corpus uses entire-family
  holdouts and an independent runtime model rather than mixing incompatible data.
- [AutoPhase: Compiler Phase-Ordering for High Level Synthesis with Deep
  Reinforcement Learning](https://arxiv.org/abs/1901.04615), Haj-Ali et al.: shows
  that pass ordering can be learned using static LLVM features. The early paper's
  reported improvement concerns LegUp HLS circuit cycles, not native CPU runtime.
  It motivates investigating pass choices but does not guarantee this project's
  result. RL remains future work; this iteration follows the requested SL-first scope.
- [Robust benchmarking in noisy environments](https://arxiv.org/abs/1608.04295),
  Chen and Revels: distinguishes timer overhead from environmental delay, shows
  why repetition alone cannot remove all bias, and motivates calibrated batching.
  Its minimum estimator targets best-case time. This project still uses paired
  median kernel latency: it neither relabels minima as average performance nor
  deletes interrupted trials to manufacture a gain.
- [Official PolyBench/C source](https://www.cs.colostate.edu/~pouchet/software/polybench/):
  the available official archive is version **3.2**, not 4.2.1. It is pinned by
  SHA-256 `1caddda5806dbe5556e0bbb4e367846a2470e6c677e5d872bdb16ace36a571f7`.
  Upstream copyright notices and source files are retained unchanged.

Primary PDFs, extracted paper text, and the official archive are retained under
`results/research_sources/`. Research ideas guide the implementation; reported
results from different objectives are not evidence that our learner beats O3.

## Corpus and correctness repairs

| Split | Kernel count | Correct across O0 and six candidate pipelines | Timing-qualified |
|---|---:|---:|---:|
| Training: datamining, linear-algebra kernels/solvers | 22 | 22 | 0 |
| Development: stencils | 6 | 6 | Not timed |
| Reserved: medley | 2 | Not executed | Not evaluated |

These are **30 scientific kernels, not 30 real applications**. Historical accepted
training is still **seven real applications plus six auxiliary synthetic kernels**;
the new corpus supplies no accepted runtime labels yet. Input variants are never
counted as independent programs. The original reserved susan, tiff2rgba, and
tiffmedian applications also remain untouched.

The old suite had invalid numerical inputs: cholesky, trisolv, gramschmidt, lu,
and ludcmp used singular/zero-diagonal matrices, while trmm overflowed its
large scalar update. Six explicit initializer adapters provide diagonally
dominant/full-column-rank matrices or bounded scaling. A separate development
adapter initializes fdtd-apml's previously uninitialized Bza live-in to zero.
Kernel computation is unchanged. These are **adapted inputs**, and results must
not be represented as measurements of unmodified PolyBench initialization.
Both upstream and prepared source hashes are recorded. Failed build diagnostics
and corrected artifacts are retained instead of silently overwriting them.

Every pipeline must produce finite live-out values and match the **full binary
numeric output hash** of an O0 reference on repeated fresh inputs. The worker
consumes every live-out value outside the timer, preventing dead-code elimination
without relying on PolyBench's rounded printed strings. This checks compiler
transformation equivalence; it is not a proof of each numerical algorithm.

## Measurement changes and findings

An unchanged zlib executable's 24-run scheduler diagnostic observed 0–40 ms
of steal ticks and wall times of 220–272 ms. Wall time and steal increments had
Pearson correlation **0.878**. Hypervisor contention is a measured contributor;
this does not prove that it explains every source of noise.

The new worker measures only the kernel with CLOCK_MONOTONIC. Allocation,
initialization, output hashing, two warmups, and process launch are outside
the kernel timer. Every invocation reinitializes inputs. O3 alone determines
batch repetitions for a 15 ms active-kernel target. All pipeline executions
share separately compiled support and measurement objects, strict floating-point
flags (`-ffp-contract=off`, no fast-math), and the same native backend settings.

The fixed menu is default O3, O2, Os, instcombine-before-O3, O3 plus unroll, and
O3 plus GVN/DCE. LLVM19's explicit instcombine invocation needs
`max-iterations=10` to satisfy its enabled fixpoint verification; verification
is preserved. Identical ELF candidates reuse their baseline result.

The declared study used three blocks, eight alternating pairs per cell, CPU2,
and 3% unchanged-control/gain gates. Effect comparisons alternated order. Review
found that identical-name controls retained positional A/B labels; this is
fixed for new collector revision 2 with a regression test. The completed failed
study remains unchanged, supplies no labels, and must not be treated as positive
evidence. **156 cells and 2,496 timed worker processes**
were retained. **918 processes had positive steal increments**. All 22 O3
controls failed, so **zero new programs and zero new candidate labels were fitted**.
The complete study is preserved. Noise was not fixed merely by removing launch
overhead; a timing-capable runner is still necessary. Scheduler ticks span the
whole process, including untimed work, and have coarse clock-tick resolution.
Zero observed steal does not establish zero interference.

Future collection runs now perform unchanged-code preflight first and stop before
candidate search if readiness fails. The new development split was checked for
correctness only: no performance tuning or runtime labels from it were used.
The learning bundle explicitly contains O3 and no fitted experimental regressor.

## Learning and evidence protection

The new SL implementation supports five candidate-specific, 153-dimensional
static transformation vectors. Its entrypoint is the renamed benchmark main;
the earlier application's feature behavior is preserved. LLVM19 kernel-latency
labels are kept separate from LLVM10 end-to-end application labels.

When qualified data exists, Ridge models predict point or lower-bound log
speedup, weigh regressions more heavily, normalize total weight per program,
and use whole-family held-out validation. Model/floor tuning uses training only;
development choices are frozen before timing. Conditional CV/model-selection
uncertainty, only three training families, and domain limits are explicit.
Neither a training oracle nor instruction-count reduction is called an SL gain.

Verification rechecks pinned sources, adapted sources, candidate bitcode/ELF
hashes, re-extracted features, complete cell coverage, raw timing bindings,
output checksums, controls, and effect summaries. Reported gains cannot be edited
independently of the raw measurements. Prior frozen artifacts remain preserved.

## Commands and remaining work

```bash
source /workspace/.neurocompiler/activate.sh
python -m unittest tests.test_compact tests.test_transform tests.test_robust tests.test_polybench
python scripts/collect_polybench.py --resume       # verifies the completed old study; no rerun
python scripts/check_polybench_timing.py           # expected exit 2 on this VM
python scripts/collect_polybench.py --split development --build-only --resume
python scripts/optimize_polybench.py --case fdtd-apml --output results/polybench_export
```

The private LLVM19 setup is retained under `/workspace/.neurocompiler/llvm19`.
It coexists with the original Python3.10/CompilerGym/LLVM10 environment. New
studies should use a fresh experiment identity, preserve the existing reports,
and pass the same unchanged-code preflight on a dedicated or demonstrably quiet
runner before collecting labels. Repeatedly resuming a failed preflight does
not create new trials or improve its result.

Once that prerequisite is met, collect the complete training menu, fit/freeze
the family-validated SL learner, and evaluate stencils without retuning. Then
broaden real application families before unlocking final tests. RL/hybrid should
follow a reliable runtime reward and a stronger SL baseline. There is no honest
completion percentage or guaranteed speedup to report from these measurements.

Changes and artifacts are local. No commit or GitHub push was performed.

Independent verification passed 196 native output checks, rejected edited raw
timings and invented gains, and checked 490 prior generated files unchanged.
The default exported fdtd-apml executable also matched its full output reference.
The snapshot is `results/polybench_iteration.zip`, with per-file hashes and the
previous robust snapshot included. The cloud setup draft saves startup/refresh
instructions; publication is a separate user action in environment settings.

On a suitable runner, use a fresh identity rather than replacing this study:

```bash
python scripts/collect_polybench.py --name dedicated_run1 --preflight-only
# Only after preflight passes:
python scripts/collect_polybench.py --name dedicated_run1 --resume
python scripts/train_polybench.py --name dedicated_run1
python scripts/collect_polybench.py --name dedicated_run1 --split development
python scripts/evaluate_polybench.py --name dedicated_run1
```
