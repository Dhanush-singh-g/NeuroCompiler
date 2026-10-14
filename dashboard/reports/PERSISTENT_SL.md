# Persistent isolated measurement and supervised follow-up

This iteration compares measurement methods before collecting a separately
declared supervised study. Prior sources, measurements, models and snapshots
remain unchanged. All measurements describe warm native library API work on
the current Intel Xeon VM, excluding startup, input preparation, IPC and client
validation. They do not measure whole-application speedup.

The completed SL study retains **11 qualified targets across six original
programs**, versus zero in the preceding study. All 16 model configurations
execute, with 128 program-level CV fits. No experimental policy qualifies;
the default remains O3 and **no learned gain over O3 is established**. A
separate preselected training probe reproduces 12.1% lower BLAKE2 API CPU time.

## Method qualification

The training-only pilot freezes eight already opened inputs, three methods,
three blocks and 24 pairs before collection in
`results/persistent_declaration.json`. The methods are fresh worker processes,
persistent isolated children with batch alternation, and persistent isolated
children with alternation after every API invocation. Each process loads one
implementation. The parent never loads either DSO. Each child performs three
initial untimed invocations and checks each measured result against its
reference; the Python collector independently checks the expected oracle.

Both sides of each null control use the **same exact O3 file**. Prior calibrated
repetition counts are rounded up to even and held equal across methods. The
micro method balances which implementation executes first inside every pair
and retains every invocation's CPU/wall clocks. IPC remains outside the API
timers. Pair clocks must exactly match the sums of the retained traces. Child
PIDs must differ; their virtual entry addresses may be equal because they have
separate address spaces. Parent death terminates children, and a bounded worker
timeout prevents orphaned native jobs.

All raw pairs remain available. Controls require block and bootstrap bounds
within 3%, as well as pooled actual starting-side and every block's order
difference within `log(1.03)`. CPU and wall qualify independently. No outlier or
steal filtering, minimum substitution, failed-control replacement or repeated
sampling until success is permitted.

| Method | Pilot CPU controls | Pilot wall controls |
|---|---:|---:|
| Fresh processes | 7/8 | 6/8 |
| Persistent batch | 6/8 | 6/8 |
| Persistent micro | 7/8 | 7/8 |

The declared rule requires at least six passes on each clock, maximizes the
smaller coverage count, and prefers micro then batch then fresh on ties.
It selects micro. One independently declared confirmation, without method
substitution or retries, again passes **7/8 on both clocks**. The pilot's micro
failure is cJSON flat; confirmation's failure is SHA256 random. Different
failures and reasonably good fresh-process coverage limit attribution to the
worker change. This does not establish universally stable VM measurements.

Pilot and confirmation retain 72 and 24 cells respectively: 1,728 and 576
pairs. They supply **zero fit targets** and never choose compiler settings or
model parameters.

## Independent training-headroom probe

Before the pilot, its declaration permits exactly one conditional follow-up:
BLAKE2 reference on the random input with O3 vectorization disabled, after the
independent method confirmation passes. `persistent_probe_declaration.json`
binds the sources, artifacts, case, method and nine-cell schedule before that
probe's clocks. It measures O3/O3, candidate/candidate and O3/candidate across
three blocks, with 24 pairs per cell.

Both self-controls and effect order checks pass on both clocks. CPU speedup is
**1.137116x**, bootstrap interval **1.127040–1.145032x**; wall is **1.137155x**,
interval **1.126985–1.145084x**. CPU block ratios are 1.130101x, 1.143317x and
1.137116x. Every block and the lower confidence bound exceed the declared 1.03x
floor. This corresponds to approximately **12.1% less API CPU time**.

This independently reproduces compiler headroom on one preselected, previously
opened training case. It is not an SL prediction, broad unseen-program result,
whole-application speedup or cross-machine replication. Its 216 pairs are
excluded from fitting and model selection.

## Supervised protocol

`results/persistent_sl_declaration.json` freezes a new study after method
confirmation. It reuses verified source builds and static features on the same
compatible CPU, with fresh clocks for every formal label. Training has 13
original upstream implementations and two inputs each: zlib, Expat, Lua, LZ4,
jsmn, BZip2, BLAKE2 reference, cJSON, inih, TinyExpr, Parson, picohttpparser and
B-Con SHA256. Input variants remain grouped by original implementation.

The menu remains O3, O2, O3 with vectorization disabled, and O3 with inline
threshold 1000. Byte-identical settings are deduplicated. The 95 timed-region
predictor fields and all 16 Ridge/forest configurations remain unchanged.
Equal total training weight is assigned to each original implementation.
Validation leaves out whole implementations, requires qualified outcomes for
every prediction, and reports unscorable predictions instead of imputing them.
The experimental policy requires positive validation utility, worst original
program >=0.97x, and at least one confirmed gain. O3 remains the default.

Fresh native O0/candidate checks and independent oracles precede each split's
formal collection. These correctness clocks and all earlier, pilot,
confirmation and probe clocks are excluded from labels. Candidate timing
proceeds only after a passing CPU baseline control; CPU/wall effect outcomes
qualify independently. Both self-controls and effect order must pass. A
confirmed gain additionally needs all blocks and the interval lower bound
above 1.03x. The collector retains failed candidate controls and negative
effects without rerunning them.

Monocypher and yyjson are **repeated development**, with four inputs total;
earlier iterations already executed them. Predictions freeze before their new
native executions. This iteration does not label them fresh or claim an
untouched final test. Reserved medley/cBench tests remain closed.

## Supervised results

| Quantity | Training | Repeated development |
|---|---:|---:|
| Original upstream implementations | 13 | 2 |
| Correct input workloads | 26 | 4 |
| Formal cells / pairs / aggregate timed batches | 216 / 5,184 / 10,368 | 12 / 288 / 576 |
| Baseline controls passed, each clock | 11 | 1 |
| Distinct candidate/input targets measured | 23 | 0 |
| Qualified candidate targets, each clock | 11 | 0 |
| Confirmed candidate gains, each clock | 0 | 0 |

Every input passes fresh independent-oracle correctness across the four
settings. Training correctness retains 104 cells with two O0/candidate pairs
each; development retains 16 cells. These clocks are excluded from learning.
The primary raw files are `results/persistent_native_20261011_train.json` and
`results/persistent_native_20261011_development.json`. CPU and wall agree on
qualification in this run; neither clock guarantees immunity to VM noise.

Eleven distinct targets qualify across Expat, inih, Lua, LZ4, picohttpparser
and zlib. Their measured outcomes include regressions, which remain fit data.
For example, Lua numeric/O2 is 0.875446x and inih sections/large-inline is
0.876625x, approximately 14.2% and 14.1% more CPU time respectively. Nested
Expat/no-vector is 1.042164x, but its interval is 1.023107–1.061019x; the lower
bound misses the 1.03x confirmation floor. Neither BLAKE2 input passes primary
baseline controls, so the separate successful probe supplies no BLAKE2 fit
target. Its evidence is deliberately not pooled into this dataset.

All 16 configurations actually fit their eight original-program folds: **128
CV fits**. Six original programs contribute candidate targets; the 11
baseline-qualified inputs span eight original programs for validation.
Eight Ridge variants recommend some settings whose held-program outcomes did
not qualify, so all eight are unscorable. Eight forest variants are fully
scorable and choose O3 on every input, with conditional score 1.000x and zero
utility/confirmed gains. No variant passes the declared policy gate.
`models/sl_persistent_native_20261011_bundle.joblib` has `experimental=None`.
These are actual fits, unlike the previous study's 16 eligibility checks.

All four frozen repeated-development decisions choose O3. Only Monocypher
pattern passes both clocks; its conditional score is 1.000x, representing
unchanged O3. Monocypher random and both yyjson inputs fail controls and do not
contribute scores. This is one qualified input of one previously executed
implementation, with no changed decisions or learned improvement. See
`results/persistent_native_20261011_evaluation.json`.

The eight-input confirmation does not guarantee coverage over the larger
corpus or a longer run. The primary study admits 11/26 baseline controls and
11/23 measured candidate targets; these limits constrain the learning
comparison. Before another SL/RL performance claim, the project needs stable
fresh native measurements and substantially more distinct qualified training
targets, including confirmed positive examples. A dedicated compatible target
or source rebuild on a quieter target needs a new declaration and fresh
untouched implementations for final evaluation. More hyperparameter trials
cannot repair missing or unstable rewards. No retry-until-pass is proposed.

## Commands and preservation

All **113 unit tests** pass. The independent final audit checks 120 native
O0/candidate comparisons using the older fresh-process collector, replays
all 16 CV variants, independently reconstructs 222 actual-side clock groups,
and rejects ten corruptions of pairs, traces, clocks, process identity,
checksums, features and reported results. The default yyjson export matches
its independent oracle; uncertified experimental export rejects before making
a directory. All 565 directly embedded prior generated evidence files remain
unchanged. 122 Python sources parse successfully. Results are retained in
`results/persistent_verification.json`.

The initial audit harness expected only `ValueError`; the missing-pair
negative test instead raised `TypeError` from a ragged array. The failed
attempt is preserved in `persistent_verification_first_attempt.log`. Handling
both valid rejection exceptions repairs the harness, with no collector,
measurement, label or model changes. The subsequent full audit passes.

Activate with `source /workspace/.neurocompiler/activate.sh`. Collectors,
builds and native audits run sequentially, orchestration on CPU0 and native
workers on CPU2. Existing private LLVM19.1.7 and LLVM10 are preserved. There
are no new dependencies or services. Native Intel artifacts must be rebuilt
from source for a CPU with different features.

The declarations and one-shot fitting/audit/snapshot scripts refuse overwrite.
Completed resumes verify evidence and perform no new timing:

```bash
taskset -c 0 python scripts/measure_persistent.py --resume
taskset -c 0 python scripts/confirm_persistent.py confirmation --resume
taskset -c 0 python scripts/confirm_persistent.py probe --resume
taskset -c 0 python scripts/study_persistent.py train --resume
taskset -c 0 python scripts/study_persistent.py development --resume
taskset -c 0 python scripts/study_persistent.py evaluate
```

The original one-shot workflow uses `--declare` for the pilot and each
confirmation stage, then `study_persistent.py declare`, `train`,
`train_persistent.py`, and `study_persistent.py development` / `evaluate`.
The pre-fit protocol clarification corrects descriptive pilot text inherited
by the SL collector declaration. It binds the new fitter while leaving all
numeric gates, split manifests, model parameters and decisions unchanged.
A new study requires separately versioned
source/declaration/context; these fixed completed studies are not a mechanism
for repeating failed controls.

Default registered export to a fresh directory:

```bash
taskset -c 0 python scripts/optimize_persistent.py \
  --case yyjson_flat --output results/persistent_export_new
```

Evidence remains local. GitHub commit/push requires separate authorization.
Saving startup instructions creates a configuration draft; review/save its
settings and Publish the prepared environment snapshot to retain local work.
Fresh-task restoration has not been independently verified. No completion
percentage or guaranteed iteration count is inferred from these experiments.

The immutable `results/persistent_iteration.zip` includes a per-file SHA
manifest, current source and evidence, the full preceding region ZIP and its
adjacent completion log. Its own `persistent_snapshot.log` is created after
the ZIP and intentionally remains outside it. Earlier pinned source archives
and models remain available in that nested snapshot and the prepared live
environment. Completed resume/evaluation checks preserve all six raw/report
hashes; see `results/persistent_final_checks.json`.
