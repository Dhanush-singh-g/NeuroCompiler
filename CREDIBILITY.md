# Evidence and reliability improvements — 25 October 2026

This update adds measured prediction diagnostics, equal-checkpoint controls,
stronger output checks, and evidence integrity checks. It does **not** change the
frozen model weights or claim a new runtime speedup. The original synthetic
holdout has already been opened; all follow-up analysis is labelled post-hoc.

## What is now measured

The SL component was assessed with four family-disjoint folds over the 24
training families. Every seed/size variant of one family stays in the same fold.
The held-out six-family final evaluation is not used in these fits. Hyperparameters
remain fixed; no fold score selects a replacement model. Duplicate probes of the
same program, bitcode state, features and action are collapsed before scoring.
Family means receive equal weight, so large families cannot dominate the score.

| Diagnostic | SL | Constant predictor/action | Always zero reward / STOP |
| --- | ---: | ---: | ---: |
| Mean absolute immediate-reward error | 0.04141 | 0.09093 | 0.08577 |
| Fraction selecting a best immediate action, ties accepted | 70.4% | 32.9% | 9.6% |
| Mean immediate-action regret | 0.01064 | 0.05984 | 0.27374 |

Reward units are log instruction-count reduction minus the declared fixed action
cost. Regret is the best observed immediate reward minus the chosen action's
reward. All eight actions, including STOP, were actually probed at each scored
state. The constant action/predictor is determined from training-fold family
means only. The always-STOP comparison is computed from the same scored states.

**70.4% is not compiler accuracy, runtime prediction accuracy, the fraction of
programs improved, a confidence probability, or validation of RL's future-value
estimates.** It is a diagnostic score for the immediate SL component on
family-separated training-data folds. The deployed full model remains unchanged.
The per-family scores and every fold's family/program assignments are committed
in [model_validation.json](presentation/model_validation.json).

## Fairer optimization baselines

The earlier fixed/random controls used the last output of a four-pass sequence.
The product's learned policy could instead retain an earlier checkpoint. The
new audit inspects all five existing states for both baselines: initial IR and
four transformed checkpoints. It applies the identical minimum-count rule and
prefers O3 on ties. No parameters, policy decisions or sequence seeds are tuned.

| Method with checkpoint/O3 guard | Fewer than O3 | Equal | More | Geometric-mean instruction-count reduction |
| --- | ---: | ---: | ---: | ---: |
| Fixed passes | 8 | 4 | 0 | 29.55% |
| Seeded random passes | 5 | 7 | 0 | 21.08% |
| Hybrid | 8 | 4 | 0 | 29.32% |

The random baseline benefits materially from keeping an intermediate checkpoint.
This is why the terminal-only comparison was insufficient. The original report
is preserved, with its original terminal-only derived controls clearly labelled.
The new equal-checkpoint evidence is separate in
[checkpoint_baseline_audit.json](presentation/checkpoint_baseline_audit.json).

We also computed exploratory percentile intervals by resampling **six family
means**, not twelve correlated variants, using 20,000 draws and a fixed seed.
The fixed/hybrid instruction-count ratio is **0.9967**, with a 95% interval of
**[0.9816, 1.0088]**. Above one favors hybrid. This interval includes one and does
not establish a hybrid advantage. It is post-hoc, unadjusted and based on authored
synthetic families, not representative sampling of real software. Neither the
ratio nor its interval describes runtime.

## More correctness checks

The ten original methods and the two baselines with equal checkpoint selection
were checked on five additional iteration arguments: `0`, `2`, `7`, `11`, `31`.
This adds **720 candidate-output checks**, all passing, on the same twelve
previously evaluated programs. GCC O0 and Clang O0 references agree on every
additional input. Chosen baseline checkpoints are compiled with the same native
codegen contract as the learned artifacts. The audit records executable/bitcode
hashes, prefix counts and input check results.

The original 240 candidate-output checks remain separate. These checks expand
input coverage; they are not new unseen-program evidence, undefined-behavior
proof, or semantic equivalence verification. Runtime is not measured by the audit.

## Honest handling of unfamiliar inputs

Each learned rollout now reports whether any scored feature lies outside the
observed training ranges. This uses the frozen training inputs, with model and
dataset hashes bound to the profile. The original environment extracts the
features from diagnostic bitcode copies, avoiding a separate feature definition.
No submitted program is executed to obtain this diagnostic.

The result appears beside the main standard-vs-NeuroCompiler comparison and in
JSON/Markdown exports. A range check is **advisory**: it never changes the frozen
policy's pass selection. Being within the coordinate-wise ranges does not prove
that the combined state or chosen action has training support. It is not
calibrated uncertainty. Range checks also do not qualify a runtime prediction.
A real fifty-function C module is tested to exercise the out-of-range path and
confirm that the emitted executable still matches the reference output.

## Evidence integrity

Startup verifies model/data/split/declaration hashes and the added diagnostic
manifest. The checks also validate training reward arithmetic, state/count and
action-history consistency, train/test family separation, cross-validation
fold separation, guard minima, expanded input-check coverage, and aggregate
arithmetic. Incorrect or mismatched artifacts are rejected rather than displayed
as current evidence. The original declared training/evaluation implementation
hashes still match.

An explicit coefficient replay refit the original learner on the committed
transitions and matched both immediate SL and fitted-Q coefficients within the
specified numerical tolerance. The recorded result is in
[weights_audit.json](presentation/weights_audit.json). Startup checks that record
and its bindings; it does not repeat training. Hashes establish consistency, not
a digital signature, independent review or scientific correctness.

The **Model & scope** tab displays these checks, the diagnostic SL metrics and
the fair baseline comparison. **Download evidence audit .json** exports the
summary. Detailed committed inputs/results remain available for review.

## Reproduce

After normal setup, from the repository root:

```bash
.presentation/venv/bin/python scripts/audit_evidence.py --refit
.presentation/venv/bin/python scripts/validate_count_model.py --output .presentation/my_validation
```

Use a fresh validation directory. These commands do not replace deployed weights.
To replay the already-opened program cases and their checkpoint/input audit
with the **exact committed model and dataset**, use:

```bash
.presentation/venv/bin/python scripts/replay_count_evidence.py --output .presentation/my_evidence_replay
```

This copies the canonical frozen artifacts into a new directory, runs the
original evaluator, then applies the checkpoint audit. It avoids falsely binding
a newly collected dataset's timing/hash metadata to the original study. Replayed
bitcode paths and hashes may differ, but the frozen model/data remain exact.
The output is replication of opened examples, not fresh unseen-program evidence.
No files under presentation are replaced. Use a fresh directory; partial replay
runs are preserved instead of overwritten.

Do not use either post-hoc diagnostic to silently choose a better-looking model
on the opened test families. A future performance model needs a separate
development set and new untouched test families, preferably pinned real-world
programs. The original lower-level audit requires retained artifacts from the
matching frozen model context; do not pass it arbitrary binaries or artifacts
from a different training run.

## Verification and remaining limits

**67 selected tests pass**, including corruption/leakage/incorrect-summary
rejections, family bootstrap clustering, guard behavior and real LLVM/native
range diagnostics. Browser checks cover the existing six evaluated examples,
all learning modes, native output, both clocks, evidence export, unfamiliar-input
warning and mobile layout. The frozen training, model and original evaluation
remain unchanged.

The project now measures an SL component's prediction quality and exposes more
trustworthy limitations. It still does not demonstrate an RL-specific advantage,
reliable runtime improvement over O3, or generalization to real applications.
The currently supported improvement remains LLVM instruction count on a small
synthetic family-disjoint evaluation, with an explicit deterministic guard.
