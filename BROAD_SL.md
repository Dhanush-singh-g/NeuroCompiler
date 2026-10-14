# Broader supervised native-library study

This iteration freezes ten original training implementations, two inputs per
implementation, and two fresh entire-program development holdouts. Its purpose
is to improve candidate coverage and assess generalized selection against native
LLVM19 O3. It makes no promise that a fixed number of iterations will produce a
runtime gain. Default remains O3 until independent evidence supports promotion.

## Frozen corpus and candidate budget

| Original implementation | Pinned version/ref | Split | Workloads |
|---|---|---|---|
| zlib | 1.3.1 | Training | Pattern/random compression round trip |
| Expat | 2.7.3 | Training | Flat/nested XML callbacks |
| Lua | 5.4.8 | Training | Numeric loop/table sorting |
| LZ4 | 1.10.0 | Training | Pattern/random compression round trip |
| jsmn | 1.1.0 | Training | Flat/nested JSON tokenization |
| bzip2 | 1.0.8 | Training | Pattern/random compression round trip |
| BLAKE2 reference | 20190724 | Training | Pattern/random BLAKE2b hashing |
| cJSON | 1.7.19 | Training | Flat/nested JSON parsing |
| inih | r62 | Training | Single/multiple-section INI parsing |
| TinyExpr | 1.1.1 | Training | Arithmetic/function expressions |
| Parson | ec53fb6528b45811df9db0db22cab96a94a96a11 | Development | Flat/nested JSON parsing |
| picohttpparser | 465a7ff09fbd3432fe56c673451f5460154d1f07 | Development | Short/many-header HTTP request parsing |

This is **10 training programs / 20 training workloads** and **2 development
programs / 4 workloads**. Seven upstream implementations are newly added.
Input variants are grouped with their original implementation; they are not
independent programs. These small libraries are not full end-user applications.
Training and development can share algorithm families; the claim under test is
generalization to distinct implementations, not previously unseen algorithms.
The preceding xxHash holdout, scientific medley and reserved cBench programs
are not used in this experiment.

Official HTTPS archives, immutable commit refs and SHA-256 pins are retained.
Materialized C/header bytes are audited against those archives. Only five
previously validated initial bitcode modules are reused after verifying identical
source bytes; **all formal runtime samples are collected anew**. Earlier labels,
raw failures, models and archives are preserved and never pooled into this fit.

The seven settings are O3, O2, Os, O3 without loop/SLP vectorization, O3 with
inlining threshold 50 or 1000, and O3 with loop unrolling disabled. Native LLVM
19.1.7, march=native, PIC, strict FP and ff-contract=off remain fixed. Before
formal declaration, the unrolling option was corrected from threshold controls
to LLVM's `-disable-loop-unrolling`. This correction used static binary aliases,
not performance observations. Initial source/menu/build records and unused
artifacts remain retained. The final compiled menu has 39 distinct alternatives;
duplicate binaries are not extra targets. jsmn's entire final menu is O3-identical.

The prior training-only menu showed useful O2 headroom and frequent instcombine
regressions. This study drops instcombine and explicitly explores inlining and
unrolling under a fixed menu. It is bounded candidate search, not arbitrary
phase-order exploration or an RL experiment.

## Correctness and measurement

All 20 training workloads pass a preflight O0/candidate comparison across all
seven settings, against independent semantic oracles. Preflight clocks are
retained but excluded from all formal fitting. New oracles use Python bz2,
hashlib.blake2b, json.loads, ConfigParser, direct arithmetic, and an independent
HTTP request interpretation. Earlier Python/system zlib, Expat, Lua arithmetic,
system LZ4 and independent jsmn-token boundary oracles remain. Compression
validates exact decoded bytes; parsing hashes a defined semantic traversal.
Checks are for the frozen inputs, not proofs on all possible library inputs.

Inputs are immutable and cached outside timers. State/results are fresh per
invocation. JSON libraries time parsing; semantic traversal and deletion are
outside their clocks. HTTP times request parsing into freshly allocated output
structures; preparation, result hashing and freeing are outside the clocks.
TinyExpr times repeated expression parsing/evaluation. INI includes callback
folding inside its parse time. Compression includes encode/decode; BLAKE2b
times hashing. These are explicitly different application API workloads, and
their absolute times are never compared across programs to infer a label.

The previously validated worker switches sides after each invocation. Equal
counts are calibrated to 40ms CPU per aggregate batch, with three blocks of 24
pairs. Baseline and candidate self-controls load separate byte-identical DSOs
at distinct entry addresses. All raw pairs and both clocks remain, including
failed controls. CPU and wall controls/confirmation qualify separately at 3%.
No retries until acceptance, interruption filtering, or minimum-latency
substitution are allowed. Native timings are sequential on CPU2; heavy builds
and native audits do not overlap them.

The inherited main statistic's order diagnostic compares pooled even/odd pair
indices. Starting sides can reverse between blocks, so that diagnostic can hide
opposing order associations. A separate declaration made during collection
regroups aggregate pairs by their recorded starting side, both within blocks
and across blocks, and flags differences above 3%. It is a sensitivity audit,
not a change to primary labels or selection. Aggregate batches can already
balance both micro-orders, and individual invocation times cannot be recovered
from their sums. The extra report makes this limitation and observed flags
explicit instead of silently altering the frozen method.

Both implementations coexist in primary workers. Cache/predictor/placement
interactions can differ from one deployed implementation. A separately declared
secondary study may confirm at most one training winner with one DSO per fresh
process, using the greatest primary CPU interval lower bound and lexical ties.
Its results never change the model, primary labels or CV selection. It cannot
independently validate an entire learned policy or remove selection uncertainty.

## Supervised selection and completion criteria

There are 163 static features: the 153-field transformation vector, six candidate
indicators, and four input descriptors. That inherited vector contains two
constant legacy descriptor slots; varying input descriptors are appended
separately. Runtime is absent from prediction.
Fit rows exclude baseline and duplicate aliases. Qualified negative targets
remain. Total fit weight is equal per original program across all inputs, with
regressions initially weighted twice before per-program normalization.

The declaration fixes 16 model variants: eight Ridge variants (alpha 1/10,
point/lower-bound labels, 1%/3% choice floors) and eight random forests (depth
3/6, point/lower-bound labels, 1%/3% floors). Forests use 128 trees, leaf minimum
4, a fixed seed and one thread. CV holds all inputs of an original program out
together. At least five original programs must have distinct qualified targets.
Any selected prediction without a qualified outcome withholds the aggregate
score. Selection requires positive regression-penalized utility, worst program
at least 0.97x and at least one confirmed CV gain. A rejected menu yields no
experimental selector; a forced preset is not created.

The selected bundle is frozen before development builds/native execution.
Development measures only O3 and frozen predictions, with independent clock
coverage. Program bootstrap intervals omit timing uncertainty and cannot establish
population-wide gains from two holdouts. Menu/hyperparameter selection can
optimistically bias CV; held-out evaluation is needed to assess the selected
learner. Reserved final tests remain closed. Default compiler behavior remains O3.

Completion for this iteration means executing or explicitly excluding every
declared program, preserving all fixed samples, evaluating all 16 model variants,
running frozen holdouts, and producing audited sources/exports/results plus an
immutable snapshot. Completion of these deliverables does not imply successful
generalization, RL/hybrid completion or guaranteed improvement over O3.

The retained [CompilerGym paper](https://arxiv.org/abs/2109.08267) distinguishes
single-program search from policies that generalize to unseen environments and
evaluates across dataset domains. Its cross-dataset code-size results are not
native CPU speedups. The [benchmarking paper](https://arxiv.org/abs/1608.04295)
informs the limits of repetition and environmental bias; its minimum estimator
is not substituted for this study's paired summaries. These ideas motivate
broader independent implementations and fixed holdouts, not a promise of a gain.

## Completed results, 11 October 2026

All 20 training workloads are correct and eligible. All 20 O3 baseline controls
pass independently on both clocks under the declared method. The fixed study
retains **528 cells / 12,672 pairs / 25,344 timed API batches**. Of 78 distinct
candidate/workload outcomes, **67 qualify on both clocks** and 11 fail candidate
controls. Failures are retained without retry. Nine original training programs
supply distinct fit targets; jsmn supplies only O3-identical choices. The 42
configuration/input aliases are not extra fit observations.

Six primary candidate/workload pairs pass the declared >3% gain gates on both
clocks:

| Training workload | Candidate | CPU speedup | Wall speedup | Additional start-order sensitivity |
|---|---|---:|---:|---|
| zlib_random | O3_large_inline | 1.063619x | 1.063789x | No flags |
| expat_nested | O2 | 1.035935x | 1.035947x | No flags |
| lua_tables | O3_small_inline | 1.057406x | 1.057427x | No flags |
| blake2_pattern | O3_no_vector | 1.141816x | 1.141589x | Effect flagged on both clocks |
| blake2_random | O3_no_vector | 1.131542x | 1.131684x | Candidate control flagged on both; wall effect flagged |
| tinyexpr_arithmetic | O3_large_inline | 1.093318x | 1.093444x | Effect flagged on both clocks |

These are training search results under a finite menu, not learned predictions
on unseen programs. An oracle choosing the best observed qualified configuration
per training input scores **1.028333x** after equal weighting per original program.
That is an optimistic diagnostic for these observed choices/inputs, not a
population upper bound or evidence that a learner attains it.

The separately declared primary start-order sensitivity flags 17 candidate
control groups and 20 effect groups on CPU; 16 and 21 respectively on wall.
No baseline control group is flagged. Among the 67 primary-qualified outcomes,
39 CPU and 40 wall outcomes have no flag in baseline, candidate control or effect.
These are diagnostic counts, not replacement training labels. The primary
qualification and its method remain frozen. Do not describe all 67 targets as
robust to the stronger order check or ignore the flags in the table.

All 16 declared model variants execute. **Eight have complete CV coverage**;
the other eight choose at least one candidate without qualified timing evidence,
so their aggregate score is withheld. The scorable lower-bound forests choose
O3 for all workloads: 1.000x, zero changed choices, zero confirmed gains, utility
0. Other scorable variants regress: point-label forests at the 3% choice floor
score 0.993550x, worst program 0.937025x; lower-bound Ridge10 scores 0.995414x,
worst 0.956623x. **No variant passes the selection gates.** The frozen bundle
has experimental=None and default O3. Larger coverage and a nonlinear model
have not established generalized selection; missing qualifications still matter.

The predeclared secondary rule selects `blake2_random/O3_no_vector`, whose
primary CPU interval has the greatest lower bound. The primary sensitivity flag
does not cause a winner substitution or retuning. One implementation is loaded
per fresh process, 16 invocations per side, three untimed warmups, and alternating
process order. Both self-controls use the same binary in separate processes;
the inherited primary separate-copy address descriptor does not apply here.

The independent-method confirmation retains **9 cells / 216 pairs / 432 worker
outputs**. Both controls pass on both clocks. CPU speedup is **1.138758x**,
interval **1.132303–1.145635x**, with blocks 1.142303, 1.134959 and 1.138758x.
This is **12.1850% lower API CPU time**. Wall speedup is **1.138687x**, interval
1.132117–1.145469x. Both interval lower bounds and all blocks exceed 1.03x.
An additional descriptive secondary start-order diagnostic flags no control or
effect group on either clock. This supports real headroom on this selected
training workload in the current runner, despite its primary sensitivity flags.
It is not SL generalization, cross-machine replication, a full-application
speedup, or evidence about optimized SIMD BLAKE2 implementations. The benchmark
uses the pinned upstream **reference** implementation and warm 4MiB hashing API.
No secondary data enters fitting or selection.

Both fresh development implementations build only after model freeze. All four
workloads are correct across seven settings, eligible, and baseline-qualified
on both clocks, with no additional order flags. Frozen choices are O3 for all
four: conditional CPU and wall scores **1.000x**, two original programs, zero
changed choices, zero learned gains. Development retains **12 control cells /
288 pairs / 576 batches**. This is substantially better holdout coverage than
the preceding study, but no learned gain is claimed.

Validation passes **87 unit tests** and **168 independent O0/candidate
comparisons**, plus all 140 preflight comparisons. The audit checks 179 source
files against pinned archives or declared generated text, verifies all five
reused initial modules, replays every one of the 16 grouped CV variants, checks
all 432 secondary outputs/statistics, and rejects five primary plus four
secondary evidence corruptions. All **366 generated files directly embedded in
the preceding invocation archive** are unchanged; its nested paired archive
preserves still-earlier evidence. Default Parson export passes hashes and an
independent oracle; an unqualified experimental export is rejected before
creating a directory. Both completed collectors and repeated evaluation verify
without any new performance samples. Reserved final test executions: zero.

Reports: `results/broad_native_20261011_{train,selection,development,evaluation,
verification}.json`; model: `models/sl_broad_native_20261011_bundle.joblib`;
secondary: `results/broad_isolated_{declaration,confirmation}.json`; order
diagnostics: `results/broad_order_sensitivity.json` and
`results/broad_secondary_order_diagnostic.json`. The immutable snapshot is
`results/broad_iteration.zip`, with a verified per-file SHA manifest and the
preceding invocation archive nested inside. Its own completion log stays
alongside the archive.

The next changes should address the observed limits: use a versioned measurement
method with starting-side checks that cannot cancel across blocks, and investigate
features specific to timed API regions rather than client preparation/result
verification. Current whole-module/direct-reachability features include untimed
work. These are hypotheses for a new declared study, not fixes shown to improve
generalization. Add distinct implementations within promising domains, then freeze
selection before fresh holdouts. Keep SL certification and RL/hybrid completion
open; the earlier five-iteration completion estimate was not evidence-based.

## Commands

```bash
source /workspace/.neurocompiler/activate.sh
python -m unittest tests.test_compact tests.test_transform tests.test_robust tests.test_polybench tests.test_paired tests.test_invocation tests.test_broad
python scripts/collect_broad.py --resume
python scripts/collect_broad.py --split development --resume
python scripts/evaluate_broad.py
python scripts/optimize_broad.py --case parson_flat --output results/broad_export_new
```

Identifiers/declarations are versioned and fixed. Completed collection verifies
without new sampling; training and snapshots refuse overwrite. A new experiment
needs a new name/code/declaration, not modification of this study. Keep prior
archives and root source copies intact. No Git commit or push is performed.
