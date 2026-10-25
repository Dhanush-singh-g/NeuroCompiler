# Unseen-family instruction-count evaluation — 25 October 2026

The expanded SL, offline RL and hybrid models were trained on **40 authored synthetic programs across 24 algorithm families**, using **3,832 native-checked transitions**. A fixed split reserves **12 programs from six different families** for a single evaluation after freezing the model. Two variants of one family are correlated; there are six independent family groups, not twelve independent algorithms.

**Result:** raw SL/RL/hybrid policies each use fewer LLVM IR instructions than O3 on eight programs and more on four. The static checkpoint/O3 guard retains eight reductions and falls back to O3 for four. This is count reduction on a small synthetic holdout, not established runtime improvement or real-world generalization.

**The fixed baseline is competitive.** Giving the fixed terminal sequence the same O3 fallback by arithmetic produces a slightly better aggregate count result than the guarded hybrid. These results do not demonstrate a learning-specific or RL-specific advantage. No parameters or weights were changed after opening the test outcomes.

## Aggregate counts

| Method | Fewer than O3 | Equal | More | Geometric-mean count reduction vs O3 |
| --- | ---: | ---: | ---: | ---: |
| Standard O3 | 0 | 12 | 0 | 0.00% |
| Standard Oz | 8 | 2 | 2 | 15.27% |
| Fixed: mem2reg → instcombine → simplifycfg → GVN | 8 | 0 | 4 | 18.58% |
| One seeded random four-pass sequence per program | 5 | 0 | 7 | -29.71% |
| SL raw terminal | 8 | 0 | 4 | 17.61% |
| SL + static guard | 8 | 4 | 0 | 29.34% |
| RL raw terminal | 8 | 0 | 4 | 17.58% |
| RL + static guard | 8 | 4 | 0 | 29.32% |
| Hybrid raw terminal | 8 | 0 | 4 | 17.58% |
| Hybrid + static guard | 8 | 4 | 0 | 29.32% |
| fixed terminal guarded (derived) | 8 | 4 | 0 | 29.55% |
| random terminal guarded (derived) | 5 | 7 | 0 | 8.31% |
| Oz terminal guarded (derived) | 8 | 4 | 0 | 16.46% |

A count ratio is O3 count divided by candidate count. The percentage above is one minus the geometric mean of candidate/O3 counts, not a runtime speedup. Both variants receive equal weight; each family has two variants, so the family-balanced result is the same.

The derived controls were added after evaluation to separate the effect of the guard from learning. They are the arithmetic minimum of the already measured baseline terminal count and O3 count. They involve no additional program runs, tuning, or retraining. Baseline intermediate checkpoints were not scored. For this particular evaluated set, all learned best-checkpoint counts equal their raw terminal counts; the derived fixed+O3 comparison is therefore especially relevant.

## Every reserved program

| Program | O3 | Oz | Fixed | Random | SL raw | RL raw | Hybrid raw | Hybrid guarded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| crc32_0 | 74 | 74 | 53 | 114 | 55 | 55 | 55 | 55 |
| crc32_1 | 74 | 74 | 53 | 55 | 55 | 55 | 55 | 55 |
| edit_distance_0 | 147 | 160 | 126 | 146 | 124 | 126 | 126 | 126 |
| edit_distance_1 | 147 | 160 | 126 | 230 | 124 | 126 | 126 | 126 |
| heapsort_0 | 170 | 147 | 145 | 266 | 144 | 142 | 142 | 142 |
| heapsort_1 | 168 | 143 | 144 | 158 | 144 | 142 | 142 | 142 |
| floyd_warshall_0 | 425 | 185 | 99 | 320 | 99 | 99 | 99 | 99 |
| floyd_warshall_1 | 425 | 185 | 99 | 287 | 99 | 99 | 99 | 99 |
| integer_sqrt_0 | 45 | 42 | 55 | 60 | 58 | 58 | 58 | 45 |
| integer_sqrt_1 | 45 | 42 | 55 | 65 | 58 | 58 | 58 | 45 |
| rational_bezier_0 | 40 | 39 | 78 | 143 | 78 | 78 | 78 | 40 |
| rational_bezier_1 | 40 | 39 | 78 | 99 | 78 | 78 | 78 | 40 |

All ten method/baseline outputs for each of the twelve programs matched the references on both fixed inputs: **240 candidate-output checks passed**. GCC O0 and Clang O0 references also agreed on those inputs. This checks these executions; it is not semantic equivalence proof. Native runtimes were not measured in this study.

## What changed in the product

The new hybrid mode is the default for a fresh session. SL/RL predict a four-step LLVM pass sequence. Before native timing, the compiler keeps every intermediate bitcode checkpoint and compares their static counts with O3. The smallest count is emitted, preferring O3 on ties. The UI labels this as a static guard, reports the emitted sequence, and retains the full raw learned trace and count for review. The guard prevents count increases; it provides no execution-time protection. All runtime correctness and reliability checks remain in force.

The guard is deterministic static selection around a learned proposal. It is not an RL reward, online retraining, runtime autotuning, or a calibrated uncertainty estimate. O3 fallback must not be presented as a learned improvement. Six evaluated-family demos are available in the example picker, one preselected variant for every family rather than only winning examples. Reusing these examples is no longer a fresh unseen-program test.

## Why lower counts may run slower

O3 can inline functions, unroll loops and vectorize operations, increasing IR count while reducing execution time. A shorter sequence can retain calls or scalar loops. Fewer IR instructions therefore do not imply fewer executed machine instructions, smaller executable files, or faster runtime. Oz is a useful size-oriented baseline, but its objective is not exactly module-wide IR count.

## Reproducibility and reservations

Run these from the repository root after normal setup, using a new directory:

```bash
.presentation/venv/bin/python scripts/train_generalization.py --output .presentation/my_count_study
.presentation/venv/bin/python scripts/evaluate_generalization.py --run .presentation/my_count_study
```

The training collector writes the source/family split and declaration before collection, excludes all test families, checks every probed training transform on two fixed inputs, and freezes model/dataset/declaration hashes. Three collection trajectories per training program use seeded random exploration, immediate-reward greedy exploration, and a fixed sequence. Hyperparameters remain gamma 0.9, twenty fitted-Q iterations, ridge 1 and hybrid top-three plus STOP. Rewards remain log instruction-count reduction minus a fixed 0.001 non-STOP cost. Measured compilation elapsed time is informational, not a reward component.

The evaluator checks frozen hashes, source implementation hashes, compiler context and family separation. It refuses to overwrite or restart an evaluation directory. If a run fails, preserve it and investigate; do not silently remove the marker and retry to select favorable outcomes. The committed report is the first frozen evaluation.

Artifacts: [source corpus](src/rl/corpus.py), [split](presentation/generalization_split.json), [declaration](presentation/generalization_declaration.json), [frozen hashes](presentation/generalization_frozen.json), [training transitions](presentation/sequential_training.json), [model](presentation/sequential_model.json), [full results](presentation/generalization_results.json). The original 512-row/eight-program model, data and evaluation are preserved in presentation/sequential_v1.

Older runtime studies, library programs reserved for research, legacy SL weights and main branch are untouched. Authored synthetic sources share scaffolding and are not a representative real-world software distribution. Four steps, eight available actions, coarse linear state/value approximations, global rather than state-local action support, and limited correctness inputs remain important limits.

## What the result supports

A trained SL/RL pipeline can generate count-reducing code for some algorithm families absent from its training split. The product can now test that claim without using the held-out programs to train or select weights. An advantage of RL over simpler static methods, reliable runtime speedups, and generalization to real applications remain unproven. Future model tuning needs a new development split and new untouched test families; these evaluated cases must not be reused for fresh generalization claims.

For a running local app, the browser checks are reproducible with Playwright and
Chromium installed:

```bash
python scripts/check_generalization_browser.py --url http://127.0.0.1:8000/
```

This runs the six already-evaluated demos and a trusted CRC native comparison.
It verifies UI/export consistency, not a fresh generalization or timing study.

## Subsequent post-hoc audit

The original model, counts and report above remain frozen.
[CREDIBILITY.md](CREDIBILITY.md) adds equal-checkpoint fixed/random controls,
720 additional input checks, exploratory family-cluster intervals and separate
training-family SL validation. It does not create a new unseen-program test or
change the trained weights. The newer random-checkpoint guard achieves 21.08%
count reduction; the 8.31% terminal-only derived control above remains historical.
