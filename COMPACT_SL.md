# Compact supervised-learning experiment

This experiment compares complete optimization pipelines against LLVM 10
`opt -O3` on the same CompilerGym cBench bitcode. It does not compare against
a current LLVM release or a source-level Clang build.

## Training results

The fresh run completed 232 paired timing cells: 4,640 timed executions and
464 cell warmups, excluding profiles and build-correctness checks. Seven inputs
from seven original programs supplied complete controlled menus. Qsort and
stringsearch were too short; patricia failed the initial O3 control; standard
bitcount and CRC32 each failed a candidate control. None was retried.

| Training input | Configuration | Speedup | Paired interval | Confirmed >3% |
| --- | --- | ---: | --- | --- |
| Bitcount, 11,250,000 iterations | mem2reg_loop_rotate_licm_O3 | 1.1390x | 1.1371–1.1460x | Yes |
| TIFF grayscale, dataset 2 | instcombine_O3 | 1.0449x | 1.0391–1.0555x | Yes |
| JPEG encoding, dataset 14 | O3_gvn_dce | 1.0333x | 1.0188–1.0565x | No |

These are configuration-search results on training inputs, not learned gains.
The JPEG result failed both the interval floor and one effect block's floor.
The broad menu's earlier reported result cannot substitute for this replication.

| Predictor | Grouped CV speedup | Changed input choices |
| --- | ---: | ---: |
| Raw Ridge | 1.001147x | 2 |
| Raw program median | 1.000000x | 0 |
| Guarded Ridge | 1.000500x | 1 |
| Guarded program median | 1.000000x | 0 |

The raw Ridge changes were blowfish and dijkstra, neither with a confirmed gain.
The guarded Ridge change was dijkstra. No guarded predictor passed the selection
rule, so `models/sl_compact_selector.joblib` is the explicit O3 policy. All four
fitted diagnostic predictors are retained in a separate artifact. Useful runtime
headroom is reproducible, but the present static predictors have not learned
how to exploit it on unseen programs.

## Frozen development results

Four inputs from two original programs (jpeg-d and tiffdither) supplied complete
controlled menus; stringsearch2 was too short. The run completed 112 cells,
2,240 timed executions and 224 cell warmups. Every selected and diagnostic
learner chose O3 on the four included inputs: native speedup is exactly 1.0x
because the selected executable is identical to O3. No learned gain is shown.

The fixed, training-derived `mem2reg_loop_rotate_licm_O3` configuration passed
the gain gates on both tiffdither inputs:

| Development input | Speedup over O3 | Paired interval |
| --- | ---: | --- |
| tiffdither dataset 2 | 1.0469x (4.69% speedup) | 1.0408–1.0517x |
| tiffdither dataset 10 | 1.0433x (4.33% speedup) | 1.0389–1.0474x |

These are two inputs of one program, not two independent programs. The chosen
menu was frozen from training search before these effects were measured.
This is evidence of fixed-pipeline transfer to a fit-disjoint development program,
not SL success, a pristine final-test result, or a family-disjoint result.
The summary fixed-policy point scores were 1.02367x for this pipeline, 0.99786x
for O3_gvn_dce, and 1.02231x for instcombine_O3, across just two original programs.
Their point-estimate bootstrap does not justify a robust overall suite gain.

The raw Ridge predictor selected the loop pipeline on the excluded, short
stringsearch2 input; this decision is retained but not counted as a reliable
speedup. Validation was not used to select a new model or replace its O3 policy.

The next modeling milestone is candidate-specific transformation and function/
loop features, accompanied by additional independent training programs. Global
module counts with seven training programs do not currently identify these
opportunities. Keep this development data labeled as previously observed and
reserve the untouched test programs for a final frozen comparison. RL remains
unimplemented and should not be presented as a demonstrated improvement.

## Verification and saved artifacts

Twenty unit tests passed, including complete-menu exclusion, signed labels,
artifact aliases, invalid data, nested program isolation, and deployment fallback.
The three existing executable workflows also passed: sixteen curated LLVM
passes, the runtime harness, and O0/O2/O3 baselines. Their legacy Runtime timings
are smoke checks only and are not pooled with this native experiment.

An actual Clang IR round trip preserved every textual function body in the
representative O3 bitcount build under the code-generation flags. Static inference
on jpeg-d exported bitcode with SHA256
`5edb341909ba65322635f142ed5f733d3f879081dc3c57f46971e2e7bbec7088`, exactly
matching the frozen O3 artifact, without native timing. All seven earlier
model/data/result artifacts whose hashes were recorded remained unchanged.

Raw studies, summaries and provenance are in `results/compact_*.json`; native
manifests and executables are in `data/processed/compact_train` and
`data/processed/compact_validation`. Models are `models/sl_compact_selector.joblib`
and `models/sl_compact_comparators.joblib`. The snapshot is
`results/compact_iteration.zip`, generated by `scripts/snapshot_compact.py` with
CRC and per-file SHA256 verification. These changes are local; no GitHub commit
or push has been made.

## Workspace recovery

At the start of this iteration the checkout contained the initial implementation
and early SL audit artifacts. The later teacher-search scripts, reports, models,
and ZIP snapshots mentioned in the conversation were absent. They could not be
verified or recovered locally. The compact menu below was reconstructed from
the previously reported training-search choices. Only newly collected raw
measurements support the results of this iteration. Existing files and the
legacy SL model were preserved.

## Fixed experiment

The four choices are O3, `mem2reg_loop_rotate_licm_O3`, `O3_gvn_dce`, and
`instcombine_O3`. Each underscore-separated sequence runs its listed passes in
order; the stages and flags are explicit in `src/benchmarks/compact.py`.

Every executable uses Clang 10 `-O3 -Xclang -disable-llvm-passes`: optimized
machine-code generation while preserving the chosen IR pipeline. No target
specific `-march=native` flag is added. Input, bitcode and executable hashes,
commands, and byte-exact stdout/output-file reference hashes are retained.
Each build must match O3 output on two fresh runs. Each timing cell checks
output during both warmups. This is a test on the nominated inputs, not a proof
of correctness for every possible input.

Training scope is twelve inputs from eleven original training programs, including
two bitcount iteration counts grouped as one program. SHA is omitted because
prior work reported nondeterministic output. Inputs were nominated from the
earlier workload metadata rather than selected using this iteration's effects.
The five development inputs belong to jpeg-d, tiffdither, and stringsearch2.
The reserved susan, tiff2rgba and tiffmedian programs are untouched.

The protocol is saved before profiling: one warmup and three O3 duration samples;
eligible durations 25–500 ms; CPU 2; four blocks of ten alternating execution
pairs. An initial O3-versus-identical-O3 control qualifies each input. Every
distinct candidate then receives both an unchanged-candidate control and an
O3-versus-candidate effect measurement in each randomized block. The initial
O3 control precedes candidate collection; it is not repeated for each candidate.
No failed control is retried or relaxed. Blocking subprocess timings include
process launch and output capture, with build, cleanup and hashing excluded.

Control acceptance requires all block medians and a deterministic hierarchical
95% bootstrap interval to lie within [1/1.03, 1.03], plus bounded execution-order
bias. The bootstrap resamples blocks and pairs within blocks. A gain requires
every effect block and the interval's lower endpoint to exceed 1.03. These are
empirical exploratory gates, not simultaneous multiple-comparison guarantees.
Speedup means O3 time divided by candidate time; percentage speedup and percentage
runtime reduction are different quantities.

An input becomes a training row only if the whole menu passes its controls.
Negative and uncertain point targets remain signed log-speedups. Unmeasured
choices are never assigned synthetic zero targets. Executable-identical aliases
have an exact zero target and share the measured executable's outcome.

## Learning and evaluation

Features are 56 initial AutoPhase counts, input-file bytes, and the bitcount
iteration count. They are static; runtime measurements never enter prediction.
The two model families are Ridge regression (fixed alpha 10) and a per-choice
program-median predictor. Both weight each original program equally. Scaling
is fitted inside each training fold, including constant-feature handling.

Raw and guarded versions undergo leave-one-original-program-out evaluation.
The guarded versions subtract an 80th-percentile overprediction margin obtained
from inner program-disjoint folds and choose a candidate only above a 3% floor.
This margin is empirical, not a guaranteed predictive confidence bound.
Only guarded policies can become the selected model: grouped CV mean >1.01,
program-bootstrap lower endpoint >1, and worst-program speedup >=1/1.03;
otherwise the explicit O3 policy is saved. Fewer than five complete training
programs cannot run the required outer evaluation and select O3.

The menu came from previous training-wide search, so these CV estimates are
conditional on that menu and do not independently evaluate search plus learning.
The selected model and all four diagnostic predictors are frozen before
development measurements. Their static decisions are saved before candidate
timings. Model, decision and training-data hashes bind the evaluation. Diagnostic
models are reported together; validation does not select a replacement model.

Development programs were examined in earlier work: these are fresh measurements
on fit-disjoint programs, not a pristine final holdout. JPEG and TIFF programs
share library code, so this does not establish family-disjoint generalization.
All summary scores average inputs within original programs and then average
program log-speedups. Summary bootstrap intervals resample program point estimates
and omit timing uncertainty; per-input paired intervals are retained separately.
With very few validation programs, neither narrow summary intervals nor isolated
wins establish a suite-wide improvement.

## Reproduce in the cloud environment

```bash
source /workspace/.neurocompiler/activate.sh
python -m scripts.collect_compact --split train
python -m scripts.analyze_compact --split train
taskset -c 0 python -m scripts.train_compact
python -m scripts.collect_compact --split validation --model models/sl_compact_selector.joblib
python -m scripts.analyze_compact --split validation
python -m scripts.evaluate_compact
taskset -c 0 python -m unittest discover -s tests -v
```

Collectors support `--resume`; a completed experiment is verified without
repeating timings. Interrupted timing cells are repeated as whole cells; completed
cells retain their original records and schedule. An interrupted build leaves
its directory for inspection rather than silently replacing its artifacts.
Collectors refuse to overwrite existing studies without `--resume`. Training
refuses to overwrite existing model artifacts. Use a separate checkout or rename
the experiment outputs deliberately for an independent replication.

Static export from a frozen manifest requires no native timing:

```bash
python -m scripts.predict_compact \
  --manifest data/processed/compact_validation/jpeg-d_2/manifest.json \
  --output results/compact_inference.bc
```

The pre-existing environment activation supplies Python 3.10, CompilerGym 0.2.5,
LLVM 10, NumPy 1.23.5, scikit-learn 1.3.2 and joblib 1.3.2. The environment and
tool checksums are saved in `results/compact_environment.json`. No dependency
or cloud setup changes were required. Run only one native collector at a time;
run learning/unit tests on CPU 0 so they do not share the timing CPU.

New generated data and models are ignored by Git. A verified ZIP snapshot will
preserve code, manifests, executables, raw timings, and model artifacts, excluding
the virtual environment, the downloaded multi-gigabyte runtime datasets, secrets,
and Git metadata. Reproduction requires CompilerGym's runtime datasets at the
paths recorded in the manifests.
