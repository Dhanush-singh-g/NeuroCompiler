# Timed-region supervised study

This separately versioned iteration tests whether static features of measured
library work help supervised selection. It also makes the separate-process
measurement method the primary protocol and requires actual starting-order
checks within every block. The experiment is frozen in
`results/region_declaration.json` before formal timing. The code passes
correctness checks, but the run admits **zero qualified candidate targets**.
No supervised selector is fitted; the default remains O3. A learned gain over
O3 is not established by this iteration.

## Results

| Quantity | Training | Fresh development |
|---|---:|---:|
| Original upstream implementations | 13 | 2 |
| Correct, eligible workloads | 26 | 4 |
| Formal cells / pairs / timed batches | 192 / 4,608 / 9,216 | 12 / 288 / 576 |
| Baseline CPU controls passed | 7 | 0 |
| Baseline wall controls passed | 7 | 0 |
| Distinct candidate/input targets measured | 19 | 0 |
| Qualified candidate targets, either clock | 0 | 0 |
| Confirmed gains, either clock | 0 | 0 |

There are 29 distinct compiled training alternatives and 58 potential
candidate/input targets. Only seven workloads pass baseline controls; their
19 distinct alternatives receive the declared candidate measurements. Every
candidate self-control fails, and only four effects pass order qualification
on either clock. Failed controls, effects, negative estimates and all raw pairs
remain in `results/region_native_20261011_train.json`. No sample is filtered and
no failed control is retried until accepted.

All 16 model configurations are ineligible because there are no qualified
candidate targets. They are **not trained models or scored CV folds**.
The frozen bundle contains `experimental=None`. The declared 95-versus-160-field
feature ablation also has zero fit/scorable configurations in both views; it
cannot show whether timed-region features improve prediction.

Monocypher and yyjson build only after the fallback bundle and selection are
frozen. All four workloads pass correctness across all four settings and choose
O3. Their timing controls fail on both clocks, so CPU/wall holdout scores are
**unavailable**, rather than a measured 1.000x result. See
`results/region_native_20261011_evaluation.json`.

The descriptive post-study diagnosis in `results/region_timing_diagnosis.json`
records median observed training steal fractions of 1.61%, 14.97% and 21.22%
across the three baseline blocks. Development medians are 17.59%, 12.40% and
19.14%. Fractions use the retained user/system/idle/steal tick subset and are
approximate. Increased steal coincides with failed null controls, supporting
host contention as a contributor without proving causality. Changing clocks
or adding repetitions does not establish removal of VM bias. This run cannot
separate model quality from unavailable runtime labels.

The preceding separate-process 12.2% BLAKE2 training result remains preserved
in `BROAD_SL.md`; it is not a new confirmation or a learned result here.

## Verification and preservation

101 unit tests pass, including CFG/timer-boundary and mixed-phase tests,
actual-side bias checks, whole-program weighting, grouped validation, missing
outcomes and deterministic O3 fallback. The training-only preflight passes
104 O0/candidate comparisons; its clocks are excluded from fit labels.
The independent final audit passes 120 native O0/candidate comparisons, checks
216 source files and 12 reused initial modules, replays all 16 eligibility
results, reconstructs 136 actual-side clock groups and rejects eight evidence
corruptions. The O3 yyjson export matches hashes and its independent oracle;
uncertified experimental export is rejected before creating a directory.
All 655 directly embedded prior generated files are unchanged. No reserved
final test is executed. 115 Python files parse successfully.

Completed resumes and repeated evaluation preserve both raw study hashes:
train `98eff2021e5901cab7bc93d1c706c1c1f18f77b39b58c5b3f0b83d6c90cee5b6`,
development `cfc3f6971f9e054c5b373f2c0e566c8291ec889ac35986b86681453a19b6b03e`.
The immutable `results/region_iteration.zip` includes a per-file SHA manifest,
current code/data/results/bundle, complete pinned source archives and the prior
broad ZIP plus its adjacent completion log. Its own `region_snapshot.log` is
written after ZIP creation and remains outside that ZIP. Startup instructions
are saved as a draft; publishing that prepared snapshot remains a user action.
No Git commit/push or new install was performed, and fresh-task restoration is
not claimed.

## Corpus and controls

Training has 13 original implementations and 26 workloads: zlib, Expat, Lua,
LZ4, jsmn, BZip2, BLAKE2 reference, cJSON, inih, TinyExpr, Parson,
picohttpparser and B-Con SHA-256, each with two inputs. Parson and
picohttpparser were development programs in the preceding study and are now
explicitly opened training programs. Their earlier runtime labels are excluded.
The current fresh development implementations are Monocypher 4.0.2 (BLAKE2b)
and yyjson 0.10.0, with two inputs each. Whole implementations stay together in
cross-validation. Sharing algorithm families is allowed; these are unseen
implementations, not unseen algorithms. Prior xxHash and reserved cBench/medley
tests remain separate and closed to this experiment.

`results/region_source_pins.json` binds the three additional official upstream
HTTPS archives by commit/tag and SHA256. Archive contents, including licenses,
are retained. Drivers use independent Python `hashlib` oracles for SHA-256 and
BLAKE2b; yyjson's recursive semantic checksum is checked against Python JSON.
Existing oracles remain in use for the other programs. Compilation uses native
LLVM19.1.7, PIC, strict floating point and contraction disabled. Twelve initial
modules are reused only after exact source verification. All formal timings are
new and cannot be pooled with previous studies.

The bounded menu is O3, O2, O3 with vectorization disabled, and O3 with inline
threshold 1000. It was chosen from already opened training evidence before
formal collection. Aliases are deduplicated by executable bytes. Compared with
the preceding seven-setting menu, this trades search coverage for collecting
more original programs under stronger controls.

Each timed batch runs a single DSO in a fresh worker process. A reference and
two warmups precede calibrated, equal-count timed API invocations. Adjacent
processes alternate O3/candidate order; every raw output and interruption is
retained. Three blocks of 24 pairs use a 40ms CPU batch target. Baseline and
candidate self-controls compare byte-identical binaries in separate processes.
Code-address inequality is not a requirement for this protocol. CPU service
time and wall latency qualify independently. Both pooled **actual starting
side** and each block's order difference must be <= log(1.03), including effects.
The null controls must also satisfy 3% block and bootstrap interval bounds.
Confirmed gains require qualified controls/effects, all blocks >1.03x and a
bootstrap lower bound >1.03x. Failed records are not retried until accepted.

## Features and learning

The new CFG analysis follows active/inactive timer states through branches and
loops, regardless of block text order. It counts active entry instructions and
the full direct-call closure rooted in them; untimed client preparation,
semantic traversal and cleanup are excluded when they do not share a timed
path. Ambiguous instructions reachable both inside and outside the timer are
excluded from these lower-bound counts and explicitly counted as uncertainty.
Indirect callbacks remain unresolved and flagged. External library bodies are
outside the linked-IR counts. The features are static;
cold/error paths can remain, and counts are not a measure of dynamic hotness.
Missing timer boundaries reject extraction rather than falling back silently.

The 95 fields contain 88 timed entry/closure O3 counts, candidate deltas and
uncertainty fields, three setting indicators and four input descriptors. There
are no runtime-derived predictor inputs. Sixteen predeclared Ridge/forest
variants use only qualified, distinct targets. Each upstream program has equal
total training weight across its inputs. Entire-program CV must be fully
scorable, have positive penalized utility, worst program >=0.97x and at least
one confirmed gain. Otherwise the bundle holds no experimental selector and
the default remains O3. Development sources are first built/executed after
model and selection hashes are checked. Only frozen predictions receive formal
effect measurements; holdouts cannot select configurations or tune the model.

A separately declared diagnostic compares these features with 160 whole-entry
features on **identical current qualified labels, parameters and grouped folds**.
The 32 ablation configurations do not change primary selection or use holdout outcomes.
This comparison separates feature effects from the changed measurement context.

## Reproduction

```bash
cd /workspace/NeuroCompiler
source /workspace/.neurocompiler/activate.sh
python -m unittest tests.test_compact tests.test_transform tests.test_robust tests.test_polybench tests.test_paired tests.test_invocation tests.test_broad tests.test_region tests.test_region_learning
python scripts/collect_region.py --resume
python scripts/train_region.py
python scripts/collect_region.py --split development --resume
python scripts/evaluate_region.py
python scripts/ablate_region_features.py
python scripts/optimize_region.py --case yyjson_flat --output results/region_export_new
python scripts/verify_region.py
python scripts/snapshot_region.py
```

Collection resumes verify completed runs without sampling. Model training,
ablation, verification and snapshot scripts refuse overwrite; completed reports
should be inspected rather than replaced. Export requires a fresh directory;
uncertified experimental export rejects. Native performance measurements,
development builds and independent native audits must run sequentially; CPU2
is reserved for native measurements and CPU0 for orchestration/builds.

## Limits and research basis

The retained CompilerGym paper (arXiv:2109.08267) motivates benchmark separation
and comparison with compiler baselines; its search/code-size results do not
promise native CPU gains. The retained benchmarking paper (arXiv:1608.04295)
discusses environmental bias and repetition. We preserve our declared paired
median API objective instead of replacing it with a best/minimum sample.
AutoPhase (arXiv:1901.04615) concerns HLS cycles and cannot establish this study's
CPU result. Source PDFs/text are in `results/research_sources`.

Three blocks on one VM and two held-out programs provide limited evidence.
Bootstrap intervals describe the retained timings, not cross-machine validity
or elimination of systematic bias. Program bootstrap intervals omit timing
uncertainty. Warm library API measurements exclude startup and client I/O.
Neither an individual training gain nor an O3 fallback constitutes learned
generalization. RL/hybrid and broader independent validation remain open.

The immediate performance prerequisite is a runner that passes the unchanged
null controls. A dedicated or quieter target needs a new declared study and
fresh native builds when CPU features differ. The laptop target must be rebuilt
from pinned source; these Intel `march=native` binaries are not a portable Ryzen
release. Training SL/RL on the current rejected estimates would give misleading
rewards. The earlier five-iteration estimate is not a guaranteed completion
schedule or a promise of beating O3.
