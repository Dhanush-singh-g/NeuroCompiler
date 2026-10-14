# Invocation-paired native-library SL

This iteration addresses the previous study's eight distinct candidate targets
and poor development timing coverage. It changes the worker's switching interval
and uses a separate real-library corpus. Default remains native LLVM19 O3.
The declaration, split, menu, source pins, CV parameters and selection gates
are frozen before the new pilot and formal timings. Earlier evidence is unchanged.

## Measurement change

The old worker accumulated an entire 40ms side before switching. It also ran
untimed initialization and output consumption between kernel invocations, so
the elapsed gap between corresponding left/right executions could exceed 40ms.
The new worker switches after **each invocation** and alternates which side
starts each micro-pair. It sums equal invocation counts into each reported pair.
Three blocks of 24 pairs, O3-calibrated 40ms CPU batches, and the existing 3%
control/confirmation gates remain. There is no retry until acceptance.

Both clocks bracket the same API work. Every formal raw pair, including failures,
is retained. CPU service time and wall time qualify separately. Neither steal
filtering nor subtracting interruptions is used. CPU time still responds to
frequency, cache and other contention; controls remain necessary.

Baseline **and candidate** controls load separate byte-identical copies at
distinct entry addresses. This fixes the preceding candidate self-control's
shared placement. Placement controls do not establish robustness across all
possible address layouts. Native ordering tests log every invocation and verify
actual A/B/B/A switching, rather than trusting the reported counters alone.

A control-only pilot uses three predetermined training kernels: correlation,
gemm and durbin. All three pass CPU and wall gates on the first fixed trial.
Pilot observations are excluded from fitting. Its calibration diagnostics are
not retained; formal real-library calibrations are retained in each manifest.
This is a protocol-specific observation, not proof that this VM is generally
stable or that the switching change alone caused every improvement.
The two implementations coexist and alternate within one process. Cache and
branch-predictor interactions can differ from repeatedly running one deployed
implementation. The secondary isolated confirmation below probes this limit;
it does not change the frozen learner or establish deployment-wide robustness.

## Real programs and input semantics

| Original implementation | Version | Split | Two deterministic workloads |
|---|---|---|---|
| zlib | 1.3.1 | Training | Patterned/random compression and decompression |
| Expat | 2.7.3 | Training | Flat/nested XML with event callbacks |
| Lua | 5.4.8 | Training | Integer arithmetic and table sorting |
| LZ4 | 1.10.0 | Training | Patterned/random compression and decompression |
| jsmn | 1.1.0 | Training | Flat/nested JSON tokenization |
| xxHash | 0.8.3 | Development only | Patterned/random XXH64 hashing |

This is **five training programs and ten training workloads**, plus **one
entirely held-out program and two development workloads**. Three upstream
implementations are newly added; zlib/Expat/Lua were previously available under
a different wall-time study. Variants and scientific kernels are not counted
as additional real programs. Existing cBench/medley final tests remain closed.

Official HTTPS tag archives and their SHA-256 pins are retained. Needed C/header
files are copied into a separate build tree; upstream files and old builds are
unchanged. Client drivers cache immutable input bytes outside timers. Library
state, parsing/interpreter state and client output buffers are fresh each call.
Library-owned allocation/teardown is timed where the workload includes it;
client buffer allocation, file reading and verification are outside the clocks.
Compiler memory barriers prevent moving measured input reads across timers.

Independent correctness oracles use Python/system zlib, Python Expat,
direct Python arithmetic for Lua, system LZ4 with byte-exact round trips,
Python JSON decoding/token boundaries, and an independent Python XXH64
implementation checked against 28 official seeded/long-input vectors and
three short vectors. Every compiled setting also
matches an O0 reference. These are checksums of the workload's defined result,
with per-invocation round-trip checks for compression; they are not a proof
of the libraries' behavior on arbitrary inputs.

## Learning and limits

The five settings are O3, O2, Os, O3 without loop/SLP vectorization, and
instcombine before O3. All use LLVM19.1.7, march=native, PIC, strict FP and
ff-contract=off. There are 161 static features: 153 IR transformation metrics,
four candidate indicators, and four input descriptors (log byte size, byte
entropy, printable fraction and zero fraction). No runtime enters prediction.

Only baseline-qualified programs and independently qualified candidate outcomes
are admitted. All signs are retained; unqualified targets stay absent.
O3-identical and duplicate non-O3 binaries do **not** inflate fit rows. Total
fit weight is equal per original upstream program across all its qualified
inputs; negative targets receive twice the initial weight before normalization.

CV holds both inputs of each original program out together. At least five
original programs must supply distinct qualified targets. Every selected CV
prediction needs a qualified outcome; otherwise its score is withheld. The
declared Ridge/floor menu contains eight variants. Experimental selection also
requires positive regression-penalized utility, worst original-program score
at least 0.97x, and at least one confirmed gain. A failed gate yields no
experimental learner; there is no forced diagnostic preset.

The model is frozen before xxHash builds or native execution. Development times
only O3 and the frozen decision. It never searches for a development winner.
Both clock scores use their own qualified coverage. Aggregate bootstrap intervals
resample original programs and omit timing uncertainty; retain per-case intervals.
One development program cannot establish broad generalization. These warm PIC
library API labels remain separate from scientific-kernel and application-startup
labels. This iteration implements supervised learning; RL/hybrid remain future work.

## Results: fixed study completed, 11 October 2026

All ten training workloads are correct and long enough to time. All ten O3
self-controls pass independently on CPU and wall clocks. Across five original
programs, there are 17 distinct compiled alternatives and **34 qualified
candidate/workload outcomes**, with candidate self-controls passing on both
clocks. Six jsmn configuration/input aliases are O3-identical and excluded from
fitting. Qualification retains real regressions: for example, jsmn instcombine
is approximately 0.87x O3. This new library study is not pooled with the preceding
scientific study's eight distinct outcomes.

Training retains 234 worker cells, 5,616 aggregate pairs and 11,232 timed API
batches. Each batch contains the manifest's equal calibrated invocation count;
these counts are not counts of independent programs or fresh processes.
Both main-clock calibrations and every raw formal sample are retained.

All eight Ridge/floor variants now have fully scorable leave-one-original-program-
out validation. None passes the predeclared selection gates. The best utility
variant, Ridge1/lower-bound/floor3%, scores 0.999431x across five original
programs, with a program-resampling interval of 0.998295–1.000000x, two changed
workloads and zero confirmed CV gains. This is progress in usable data and
validation coverage, but the model has not learned a beneficial compiler policy.
The frozen bundle contains no experimental selector; its default is O3.

One **training** workload, `expat_nested`, shows O2 search headroom under the
primary pairing protocol: CPU speedup 1.034304x (3.3166% lower CPU time), interval
1.030261–1.041807x, and wall speedup 1.034186x, interval 1.030188–1.041808x.
Both controls, the interval lower bounds and all three effect blocks pass the
declared 3% threshold. This is a selected training result, not an SL prediction
on an unseen program.

A separately declared **post-study** secondary confirmation loads only one
implementation per fresh worker process. It alternates process order and sums
API clocks over 102 invocations per side, twice the primary calibrated count.
Startup, I/O and three untimed warmups are outside API clocks. Its self-controls
run the same binary in separate processes; the inherited primary protocol's
separate-copy address descriptor does not apply. No secondary timing enters
fitting, selection or a retroactive change to the primary study.

All nine secondary cells retain 216 pairs and 432 worker outputs. O3 and O2
controls pass on both clocks. CPU speedup is 1.030862x, interval
1.018357–1.039170x, with blocks 1.034354, 1.023388 and 1.030862x. Wall speedup
is 1.030840x, interval 1.018329–1.039175x. **The 3% confirmation floor is not
met:** one block and both lower bounds fall below 1.03x. This supports positive
headroom on this training input within this run, but not a confirmed deployment
gain above the declared floor. It does not show that coexistence caused the
difference, nor quantify all selection/multiple-comparison uncertainty.

Development starts only after freezing the model. Both xxHash workloads pass
O0/oracle correctness across all settings. `xxhash_random` passes CPU and wall
baseline controls; `xxhash_pattern` fails both and remains excluded. The frozen
policy chooses O3 for both. Conditional qualified scores are therefore 1.000x
with no changed choices and no learned gain. Only one held-out original program
and one qualified input are covered; this cannot establish broad generalization.
Development adds six control cells, 144 pairs and 288 batches. There are no
development candidate searches or executions of reserved final tests.

Validation: **81 unit tests pass**, including actual native invocation-order
and placement checks, independent XXH64 vectors, input grouping, program weights,
alias deduplication and missing-target handling. An independent audit passes
60 O0/candidate comparisons, rejects four primary evidence corruptions and
verifies all 800 generated files embedded in the prior paired snapshot unchanged.
The additional audit compares materialized sources against pinned archive bytes,
recomputes secondary statistics and validates every secondary output, rejects
four secondary corruptions, and checks a default export against its independent
oracle. An unqualified experimental export is rejected before creating an output
directory. The initial long-vector test fixture used the wrong generator constant;
the corrected fixture follows upstream exactly, without changing the XXH64
algorithm or expected vectors. Both failure and successful test logs are retained.

Main reports are `results/invocation_native_20261011_{train,selection,development,
evaluation,verification}.json`; secondary declarations and raw results are
`results/invocation_isolated_{declaration,confirmation}.json`. The frozen model
is `models/sl_invocation_native_20261011_bundle.joblib`. The source/data/evidence
snapshot is `results/invocation_iteration.zip`, with a verified per-file SHA
manifest and the preceding paired archive nested inside. Its own post-creation
completion log is kept alongside the archive.

The next research bottleneck is candidate profitability and generalization:
broaden distinct real training programs, discover profitable training candidates
under a fixed budget, and test on additional entire-program holdouts after
freezing selection. Keep these changes in a new declared study. Five training
programs are still small, and one development input failed controls. RL/hybrid
should wait for usable rewards and positive independent SL validation.

## Commands

```bash
source /workspace/.neurocompiler/activate.sh
python -m unittest tests.test_compact tests.test_transform tests.test_robust tests.test_polybench tests.test_paired tests.test_invocation
python scripts/collect_invocation.py --resume
python scripts/collect_invocation.py --split development --resume
python scripts/evaluate_invocation.py
python scripts/optimize_invocation.py --case xxhash_random --output results/invocation_export_new
```

Completed collectors verify without new sampling. Training refuses to replace
the frozen model. Current experiment identifiers are intentionally fixed; a
new study needs a separately versioned declaration/name/split rather than editing
old results. Native timings are sequential on CPU2, with builds/orchestration
on CPU0. No new package install is required. Artifacts require compatible CPU
features. No commit or GitHub push is performed.
