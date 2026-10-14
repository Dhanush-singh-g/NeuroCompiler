# Candidate-aware supervised compiler prototype

This iteration replaces progress percentages with concrete milestones: static
candidate features, expanded controlled training, learned configuration choices,
fresh native confirmation, and a runnable optimizer for a new C or LLVM file.
The comparator remains LLVM 10 `opt -O3` on the same initial bitcode, followed
by optimized native code generation. This is not a current-LLVM or source-Clang
comparison. RL and hybrid learning remain future work.

## What was implemented

- A 156-feature extractor compares every candidate with O3. It summarizes
  functions, CFG edges and cyclic regions, instruction categories, main, static
  direct-call reachability, signed changes, absolute function changes, executable
  size, input bytes, iteration count and configuration identity. Function names
  and benchmark identities are not predictor inputs.
- Cyclic CFG regions are strongly connected components, not natural-loop nesting
  or measured hotness. Direct reachability is a lower bound when indirect calls
  exist; that uncertainty is an explicit feature. LLVM instruction counts are
  features only: every target remains controlled native runtime.
- Eight independent deterministic synthetic kernels cover integer reduction,
  stencil, matrix multiplication, sparse gather, polynomial evaluation, insertion
  sort, dependent hashing and a sieve. Only O3 duration calibrates their iteration
  counts, before candidate timing. They expand training contexts, not real-world
  benchmark coverage. Source C, initial IR, candidate IR, ELF hashes, reference
  stdout and calibration records are preserved.
- Six kernels passed the controls. Matrix multiplication and polynomial evaluation
  failed initial controls and were excluded. Together with seven reliable cBench
  programs, the pooled model has 39 measured candidate labels across 13 program
  groups. Executable-identical O3 aliases have exact zero effect and can never
  produce an optimization choice. Negative and uncertain effects remain signed.
- Pooled Ridge regressors (alpha 1 and 10) and Extra Trees (96 trees, depth 4,
  minimum leaf 3) share training information across candidate transformations.
  Scaling and program weighting are fitted inside program-disjoint folds.
  Guarded predictors calibrate an overprediction margin in inner disjoint folds.
- A separate training-only policy study compares decision floors of 0%, 1%, and
  3%. Prediction thresholds and measured confirmation gates are separate. Model
  selection requires CV mean >1.01, program-bootstrap lower >1, worst original
  program >=1/1.03, and confirmed gains on at least two held program groups.
  The best experimental predictor is retained even if these deployment gates fail.
- `scripts/optimize_transform.py` accepts a linkable C or LLVM bitcode file,
  creates the four candidate pipelines, extracts static features, selects a
  configuration, and exports bitcode plus an optional executable. It never
  executes the input program. The default uses the selected policy; the
  experimental predictor requires an explicit flag.

## Training and initial development evidence

The 3% decision-floor study did not produce a deployable learner; its best raw
Ridge alpha-10 CV speedup was 1.00120x, and all eligible development predictions
were O3. The decision-floor study's best experimental model was raw Ridge
alpha 1 with a 0% floor. Its conditional grouped CV score was 1.008875x, interval
0.99546–1.03075x, worst-program 0.97879x. It chose the bitcount winning pipeline
when bitcount was excluded from regression fitting. That is a conditional model
CV result: the candidate menu itself was inherited from earlier training-wide
search, so it does not independently evaluate search plus learning generalization.

No predictor passed the deployment rule. The default policy stays O3. The frozen
experimental policy chose the loop-rotation/LICM pipeline for JPEG decoding and
instcombine-before-O3 for TIFF dithering. Fresh 10-pair, four-block measurements
under the earlier 3% controls/gain gate yielded:

| Development input | Experimental SL choice | Speedup | Paired interval | >3% confirmed |
| --- | --- | ---: | --- | --- |
| jpeg-d dataset 2 | loop-rotation/LICM | Excluded: candidate control failed | — | No |
| jpeg-d dataset 16 | loop-rotation/LICM | 1.01046x | 1.00341–1.01936x | No |
| tiffdither dataset 2 | instcombine-before-O3 | 1.02551x | 1.01929–1.03024x | No |
| tiffdither dataset 10 | instcombine-before-O3 | 1.01653x | 1.00881–1.02438x | No |

The experimental policy thus made beneficial point choices, but none passed
the declared 3% confirmation threshold. The point grouped score 1.01572x includes
only three accepted inputs of two programs; its program-only bootstrap omits
timing uncertainty and cannot establish a suite-wide gain. Do not relabel these
results after changing a threshold.

## Separate higher-precision confirmation

One new study was specified before its first timing: the same frozen model and
choices, four blocks of 40 pairs, CPU 2, one warmup per executable per cell,
unchanged-O3 and unchanged-candidate controls within 1%, and a minimum confirmed
gain of 1%. All effect blocks and the hierarchical interval lower endpoint must
clear 1.01. No rejected cell or input is retried until it passes. This is a new
measurement-resolution experiment prompted by the pilot's smaller positive
effects, not a retrospective change to the earlier 3% study.

The confirmation completed 48 cells, 3,840 paired timed executions and 96 cell
warmups. Every input passed both 1% controls. The frozen experimental SL policy
produced:

| Development input | Speedup over O3 | Paired interval | Confirmed >1% |
| --- | ---: | --- | --- |
| jpeg-d dataset 2 | 0.99328x (0.67% slowdown) | 0.98979–0.99788x | No |
| jpeg-d dataset 16 | 1.00897x (0.90% speedup) | 1.00506–1.01142x | No |
| tiffdither dataset 2 | **1.02724x (2.72% speedup)** | **1.02354–1.03054x** | **Yes** |
| tiffdither dataset 10 | 1.01363x (1.36% speedup) | 1.00905–1.01695x | No |

The TIFF dataset-2 effect cleared the 1% floor in all four blocks and at the
interval's lower endpoint, with the same learned choice frozen before timing.
This is an experimental learned configuration gain on one development input,
not an oracle choice made from its timing results. It is a narrower milestone
than general improvement: the JPEG regression is real evidence against promoting
the policy as uniformly beneficial. The point grouped score is 1.010706x over
two original programs; its program-only bootstrap omits timing uncertainty and
does not establish a robust suite-wide result. The default selected policy
remains O3 because the training model-selection gates failed.

Across the new kernel collection and all three development studies there were
168 cells, 6,240 paired timed executions and 336 cell warmups, excluding profiling,
calibration and build correctness. All prior artifacts remain unchanged.

Per-input intervals resample timing blocks and pairs. Empirical control gates and
bootstrap intervals do not constitute a formal simultaneous multiple-comparison
guarantee. JPEG/TIFF development programs were examined in earlier iterations,
and feature design was informed by development diagnosis. These are fresh
measurements on fit-disjoint development programs, not a pristine final test.
JPEG and TIFF programs share library code; family-disjoint generalization is
not established. Reserved susan, tiff2rgba and tiffmedian remain untouched.

## Use the trained optimizer

```bash
source /workspace/.neurocompiler/activate.sh
python -m scripts.optimize_transform \
  --input program.c --output results/program.bc \
  --executable results/program.out \
  --model models/sl_transform_policy_bundle.joblib
```

Use `--experimental` to request the frozen experimental predictor. Supply
`--input-bytes` and `--iterations` when known, and repeat `--link=-lm` or other
link options as needed. The input must define a linkable main function.
Predictions do not imply a runtime gain. The command refuses to overwrite
existing artifacts and records model/input/bitcode hashes and the selected policy.

Both source-file and bitcode inference are exercised on real artifacts. A
source-file export reproduced an independently frozen O3 bitcode/executable.
Experimental bitcode inference selected the loop-rotation/LICM pipeline for
bitcount and exactly matched its independently frozen bitcode and ELF hashes.
Compilers, extraction and model prediction run during inference; the input
program does not run.

All 32 unit tests passed, covering CFG parsing, indirect-call uncertainty,
candidate deltas, aliases, nested isolation, decision/gain thresholds and the
unchanged old timing protocol. Actual cached feature vectors were re-extracted
and matched against every frozen real and synthetic candidate. Completed native
studies are independently verified by recomputing coverage, decisions, controls
and outcomes from raw records. Static inference, compileall and diff checks
passed. Failed controls and old >3% labels were not reclassified.

## Reproduce and verify

```bash
source /workspace/.neurocompiler/activate.sh
taskset -c 0 python -m scripts.extract_transform --split train
taskset -c 0 python -m scripts.extract_transform --split validation
python -m scripts.collect_kernels
taskset -c 0 python -m scripts.train_transform
python -m scripts.evaluate_transform
taskset -c 0 python -m scripts.train_transform --prefix transform_policy
python -m scripts.evaluate_transform --prefix transform_policy
python -m scripts.evaluate_transform --prefix transform_policy --precision
taskset -c 0 python -m unittest discover -s tests -v
python -m scripts.verify_transform
python -m scripts.snapshot_transform
```

Run only one native collector at a time. Completed collectors refuse to overwrite
artifacts; `--resume` verifies or resumes existing studies. Training and extraction
also protect existing artifacts. An independent replication requires separate
output locations or an isolated copy, not deletion of previous evidence.

All prior models, raw studies and the previous snapshot are preserved. No
dependencies or cloud configuration changes were required. The new snapshot
contains code, essential source/bitcode/executable artifacts, static feature
matrices, raw native records, models, reports and logs with per-file SHA256/CRC
verification. Generated output files and intermediate pass stages can be
recreated and are omitted, along with the virtual environment and external
cBench runtime datasets. Restore under the same workspace paths with the pinned
environment and CompilerGym runtime data. Nothing has been committed or pushed
to GitHub by this iteration.
