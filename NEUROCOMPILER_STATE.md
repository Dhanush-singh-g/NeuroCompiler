# NeuroCompiler — Project State and Handoff

## GitHub distribution: 14 October 2026

The user authorized committing and pushing all project work to
Dhanush-singh-g/NeuroCompiler. Source, tests, reports, model bundles and the
recorded dashboard snapshot belong in main. Generated data/models/results are
preserved separately in the project-snapshot-2026-10-14 release, with a full
per-file manifest and archive checksum; RESEARCH_ARCHIVE.json describes it.
Existing experimental snapshots remain unchanged. Historical reports below
describe their original local-only state at the time of each experiment.

For a fresh clone, read START_HERE.md and run serve_dashboard.py directly.
Do NOT rebuild the data snapshot as a startup step: raw records are in the
release and are optional for viewing. Python 3.10+ suffices on Windows,
macOS or Linux. Linux/LLVM19 is still required for compiler experiments.
The staged clean-checkout HTTP smoke test passes without data downloads.
The 137-test research/dashboard/archive suite passes, and the additional
internal-link archive regression also passes. Restore checks reject tampering,
traversal, archive links and conflicting existing files; executable bits are
preserved. Large generated artifacts are not ordinary Git blobs. No new
timing experiment, model fitting or development execution was performed.

## Dashboard: 13 October 2026

The static results frontend is documented in dashboard/README.md. Build its
curated data with `python scripts/build_dashboard.py`; start the allowlisted
local server with `python scripts/serve_dashboard.py --port 8000`. Only the
standard library is required. No new native benchmarks, model training or
holdout execution is triggered. Existing frozen sources/evidence stay intact.
Overview, searchable program/input correctness, compiler-setting selection,
CPU/wall admission matrix, failure details, provenance and exports are available.
Missing data stays unavailable; BLAKE2 training headroom stays separate from
learned generalization. Tests/browser checks and screenshots are retained under
results/dashboard_*. Direct file opening is blocked by managed Chromium;
the HTTP workflow is verified. No deployment, GitHub commit or push performed.

## Latest iteration: expanded corpus and portable target qualification, 12 October 2026

- Report: EXPANDED_SL.md. Training increases from 13 implementations/26
  inputs to 21 implementations/42 correctness inputs. Monocypher/yyjson are
  explicitly opened training now; their older clocks are excluded. Six new
  training libraries: json-parser, miniz, FastLZ, Frozen, yxml, MPack. Two new
  untouched development implementations: sheredom/json.h and libdeflate,
  four future inputs; archives pinned but native builds/executions stay closed.
- All 23 archives/commit pins/licenses retained in expanded_sources, with
  relative paths and SHA256 in expanded_source_pins.json. yxml is the named
  JulStrat mirror of Yoran Heling's parser. All 21 training implementations
  freshly source-built with LLVM19/native/PIC/strict FP, no old bitcode/DSO
  reuse. All 42 inputs eligible and correct across four pipelines: 168 cells,
  two O0/candidate pairs each, 336 pairs. Forty compressed streams independently
  decode to original bytes (Python zlib, system LZ4, Python FastLZ level-1).
- Frozen SAX adapter initially hashed array indices as object keys. Repaired
  with container tracking before formal freeze; failed preflight/diagnostic
  and build preserved. Native regression covers numeric keys/nested arrays.
  All 123 tests pass. Full-source/package paths remain portable; no new install.
- Formal protocol selects one input per original training implementation,
  21 inputs, to bound runtime while all 42 receive correctness. Static features
  remain 95. Formal choices O3/O2/no-vector; large-inline correctness/features
  only and never predicted. Sixteen fixed models with whole-program CV;
  missing outcomes unscorable/default O3. No gate/correctness/older clock fits.
- Source/protocol/context frozen at results/expanded_native_20261012/frozen.json.
  Micro isolated workers, three warmups, equal even counts, 200ms CPU service
  target per side/pair, three blocks/24 pairs; same 3% block/CI/actual-side
  and every-block order bounds CPU/wall independently. All six admission inputs
  must pass both clocks and one independent confirmation; no failed retries.
- CPU2 initial admission fails 4/6 CPU and 4/6 wall: zlib order failure,
  Expat interval/block/order failure including identical-O3 third-block ratio
  0.9014x. All downstream confirmation/train/fit/development actions reject
  before creating outputs or opening fresh holdouts. No new fit labels/models.
- Separate predeclared diagnostic screens identical-ISA unused logical CPUs
  1/3/4 with the same fresh binaries/counts: CPU1 5/5 passed CPU/wall controls,
  CPU3 3/2, CPU4 1/1, each out of six. None qualifies under all-six rule.
  CPU0 then screened once with orchestration on CPU1: 3/3 out of six, fails.
  Both conditional confirmations have zero native cells/selected target None.
  Total 90 cells/2,160 null pairs across all five CPUs. No threshold relaxation,
  no further CPU search, no compiler-effect sampling or fitting with these data.
- This is a conservative admission failure, not proof every program is
  unmeasurable. Do not claim dataset growth produced more usable ML labels:
  prior 11 qualified targets remain in their separate study. Need quieter
  fresh target/context before another expanded performance study. No learned
  gain established; earlier 12.1% BLAKE2 training headroom remains unchanged.
- Portable kit: results/expanded_portable_sources.zip (~16MB), SHA/CRC
  manifest, full upstream archives/licenses, Python3.10 dependency pins and
  PORTABLE_RUNNER.md. No generated NeuroCompiler binaries/models/old labels.
  Needs Linux, LLVM19, numpy/sklearn/joblib and system LZ4 decoder; no CompilerGym
  or LLVM10 import in this workflow. Relocation test in /tmp builds FastLZ
  fresh, checks four pipelines/five independent streams/95 fields and module
  origins. Different physical-machine performance and fresh-task restore untested.
- Completed commands: expanded_study.py gate --output results/expanded_native_20261012
  --resume and expanded_study.py verify with same output do no new timing.
  screen_expanded_targets.py --resume / --confirmation --resume verify the
  three-core study. screen_expanded_cpu0.py equivalents verify CPU0. One-shot
  declarations/packages/audits/snapshots refuse overwrite. All native collectors,
  builds and audits run sequentially. Default orchestration0/native2; CPU0
  diagnostic uses orchestration1/native0. Restore activation with existing
  /workspace/.neurocompiler/activate.sh; private LLVM19/LLVM10 remain unchanged.
- Base audit checks 724 upstream files, 42 regenerated inputs/oracles, 12 order
  groups, nine corruptions/downstream guards; all 53 directly embedded prior
  generated files unchanged. Target audit checks 54 seeds/36 order groups/five
  corruptions and hashes; CPU0 checks 18 seeds/12 order groups and completed
  hashes. Both fresh development sources stay unexecuted. Reserved tests closed.
- Snapshot expanded_iteration.zip nests intact persistent_iteration.zip plus
  adjacent old completion log. Its own expanded_snapshot.log stays outside.
  Startup draft saving is separate from publication; review/save settings and
  Publish prepared filesystem to retain local work. No Git commit/push or new
  package/service. Do not invent project completion % or guaranteed iteration
  counts. The source implementation is advanced; learned research success open.

## Preceding iteration: persistent isolated qualification and fresh SL labels, 11 October 2026

- Report: `PERSISTENT_SL.md`. New code leaves all prior frozen sources and
  experiments intact. Activate with `source /workspace/.neurocompiler/activate.sh`.
  No new dependencies/services; existing private LLVM19.1.7 and LLVM10 remain.
- Eight opened training inputs, three methods, three blocks of 24 pairs,
  72 pilot cells. Same exact O3 path on both sides. Micro/batch each fork two
  children, loading one DSO per child only after fork; parent loads neither.
  Three initial untimed invocations per child; independent output oracles.
  Micro alternates after every API invocation with even repetitions and keeps
  every invocation clock. Aggregates must exactly sum traces. Separate PIDs,
  not unequal virtual addresses, prove isolation. Parent death kills children.
- Frozen method rule: >=6/8 controls each clock, maximum minimum coverage,
  ties micro > batch > fresh. Pilot CPU/wall: fresh 7/6, batch 6/6, micro 7/7.
  One independent confirmation passes micro 7/7, 24 cells. Pilot/confirmation
  failures differ; do not attribute all improvement to method or promise VM
  stability. Pooled actual starting-side AND every block order differences,
  block/interval bounds all stay at 3%, independently on CPU/wall.
- Predeclared conditional BLAKE2 random/no-vector probe: nine cells/216 pairs,
  both self-controls/effect order qualify, CPU 1.137116x [1.127040,1.145032],
  wall 1.137155x [1.126985,1.145084]. All blocks/lower bounds exceed 1.03x;
  approximately 12.1% less API CPU time. Previously opened training headroom
  only; never fit/retune with these timings or call it SL/unseen improvement.
- Separate frozen SL study `persistent_native_20261011`: 13 original training
  implementations/26 inputs, same four settings and 95-field timed features,
  source-verified existing compatible Intel builds; every formal clock fresh.
  Correctness: 104 train/16 development cells, two O0/candidate pairs each,
  all pass independent oracles. Pilot/probe/earlier/correctness clocks excluded
  from fit targets. Intel march=native artifacts require rebuild on Ryzen.
- Training: 216 cells/5,184 pairs/10,368 aggregate API batches. Eleven baseline
  controls pass CPU/wall, 23 candidate/input targets measured, 11 qualify
  each clock across six original programs. Negative targets retained; no
  primary confirmed gain. Neither BLAKE2 baseline qualifies in this larger
  study; do not import its probe to repair missing labels or retry failures.
- All 16 fixed models actually execute 128 program-level CV fits. Eight
  forest variants fully score across eight baseline-qualified original
  programs/11 inputs, all choose O3, utility zero/score 1.000x. Eight Ridge
  variants predict settings with unqualified held-program outcomes and are
  unscorable. No policy passes; bundle experimental=None/default O3.
  This is actual fitting, unlike the preceding zero-target eligibility checks.
- Monocypher/yyjson four inputs are explicitly REPEATED development, not
  fresh holdouts. Frozen decisions all O3. Twelve cells/288 pairs; only
  Monocypher pattern qualifies CPU/wall, conditional unchanged-O3 score 1x.
  Other three fail controls and contribute no score. Final tests remain closed.
- The collector's protocol object inherited pilot descriptive strings. The
  pre-fit `persistent_sl_protocol_clarification.json` binds the separate
  `train_persistent.py` fitter and correct full-study model metadata, with
  numeric gates/splits/parameters/labels/folds/decisions unchanged. Preserve
  this clarification, archived fitter source and original declaration.
- 113 unit tests pass. Collectors/builds/native audits run sequentially, CPU0
  orchestration/CPU2 native work. Resume only with `measure_persistent.py
  --resume`, `confirm_persistent.py confirmation|probe --resume`, and
  `study_persistent.py train|development --resume`; completed runs do not
  resample. `study_persistent.py evaluate` verifies frozen predictions.
  One-shot model/audit/snapshot scripts reject overwrite. Default export:
  `optimize_persistent.py --case yyjson_flat --output <fresh-directory>`.
  Uncertified --experimental rejects before creating output.
- Independent final audit: 120 native O0/candidate comparisons with the old
  fresh-process collector; all 16 CV variants replayed, 222 actual-side clock
  groups independently reconstructed, ten evidence corruptions rejected;
  default export oracle passes and uncertified export rejects. All 565 prior
  directly embedded generated files remain unchanged; 122 Python files parse.
  The first audit harness attempt failed on TypeError versus ValueError for
  deliberately ragged data; failed log preserved, harness corrected, no data
  or primary source/model changes. Completed resumes preserve six evidence
  hashes and perform no new timing. Preserve persistent_final_checks.json.
- Snapshot: results/persistent_iteration.zip and per-file SHA manifest;
  nested unchanged region ZIP plus its adjacent completion log. Its own
  persistent_snapshot.log remains outside the ZIP. Startup configuration is
  saved as a draft, not applied/published. Review/save settings and Publish
  the prepared filesystem snapshot to retain local changes. Fresh-task
  restoration is untested; no Git commit/push or new install was performed.
- Generalized O3 gain, reliable wider runtime coverage, RL/hybrid and full
  research completion remain open. The timer provides usable labels on some
  inputs, not universal stability. Need more qualified distinct targets and
  positive examples on a stable target before another performance claim;
  use new source/context/declaration and truly untouched final implementations.
  More hyperparameter trials cannot fix unstable rewards. Do not invent
  completion percentages or guaranteed iteration counts. GitHub was not pushed.

## Preceding iteration: timed-region features and isolated primary measurements, 11 October 2026

- Current report/commands: `REGION_SL.md`. New versioned modules/scripts leave
  all frozen prior sources/evidence unchanged. Timed CFG state propagation
  removes untimed preparation/validation from predictor counts, handles loops
  and mixed-phase joins, and flags indirect-call lower bounds. There are 95
  static predictor fields; external library bodies/dynamic hotness are unknown.
- Training: 13 original implementations, 26 workloads. Previously opened
  Parson/picohttpparser now train; new B-Con SHA256 source is commit-pinned.
  Fresh development: Monocypher 4.0.2 and yyjson 0.10.0, four workloads.
  Independent hashlib/JSON oracles; original source archives/licenses retained.
  Twelve initial modules reused after exact source checks; all formal timings
  new. Do not pool previous runtime labels or use old development as unseen.
- Fixed bounded menu: O3, O2, no-vector, large-inline. Source/pins/splits/16
  model configurations/feature ablation frozen before formal collection in
  `results/region_declaration.json`. 29 distinct training alternatives have
  58 potential input targets. Each worker loads one implementation; adjacent
  fresh processes alternate order with three untimed invocations before a
  calibrated 40ms CPU batch. Actual pooled side and every block's order
  difference must pass 3% bounds for controls AND effects. All pairs retained.
- Correctness/eligibility: all 26 train and four development workloads pass
  all four settings. Training retains 192 cells / 4,608 pairs / 9,216 batches.
  Seven baseline controls pass each clock; 19 distinct targets are measured,
  none passes candidate controls. Only four effects pass order gates. Zero fit
  targets; all 16 variants are withheld without model fitting or scored folds.
  Bundle `models/sl_region_native_20261011_bundle.joblib` has experimental=None.
- Model freeze precedes holdout builds/executions. Fresh development retains
  12 cells / 288 pairs / 576 batches; all four O3 choices have failed controls
  on both clocks. CPU/wall scores are null, not measured 1.000x results.
  There is no new confirmed training or learned holdout gain. Old BLAKE2
  confirmation remains preserved; never present it as a current ML result.
- Descriptive diagnosis: median observed training steal fractions rise from
  1.61% to 14.97% to 21.22% across baseline blocks. Development medians
  17.59%, 12.40%, 19.14%. Recorded tick subset makes these approximate;
  association supports host contention but is not causal proof. No filtering,
  label relabelling, retries until success or forced policy is permitted.
- Declared diagnostic 95-field timed versus 160-field whole-entry ablation
  uses identical current targets/folds; both have zero fit/scorable variants.
  This run cannot assess feature effects on prediction or generalization.
- 101 unit tests pass. Independent audit passes 120 native O0/candidate
  comparisons, checks 216 source files / 12 reused modules, replays all 16
  eligibility decisions, independently reconstructs 136 actual-side clock
  groups and rejects eight evidence corruptions. All 655 directly embedded
  prior generated evidence files remain unchanged, including nested archives.
  O3 yyjson export passes hashes/oracle; uncertified experimental export rejects.
  Reserved medley/cBench tests remain closed. Completed resumes and repeated
  evaluation must preserve raw hashes and perform no new native timing.
- Snapshot: `results/region_iteration.zip`, nested prior broad ZIP and adjacent
  old completion log; `region_snapshot.log` is outside its own ZIP. Save the
  startup draft without replacing install/network/repositories; publication
  is separate. Current instance tests do not establish fresh-task restoration.
  No Git commit/push or new dependency/service installation.
- Next prerequisite: a target that passes unchanged null controls. A quieter
  dedicated runner or locally rebuilt laptop study requires new declaration/
  context and fresh native builds when CPU features differ. Intel march=native
  artifacts are not portable Ryzen binaries. Rejecting unstable rewards is
  necessary before fitting SL/RL. Generalized O3 gains, RL/hybrid and full
  project completion remain open; the earlier five-iteration estimate is not
  a guarantee. Do not give unsupported completion percentages.


## Preceding iteration: broader library corpus and nonlinear SL, 11 October 2026

- Report/commands: `BROAD_SL.md`. Ten original training programs / 20 workloads;
  two fresh whole-program development holdouts (Parson and picohttpparser) /
  four workloads. Added bzip2, BLAKE2 reference, cJSON, inih, TinyExpr and the
  two holdouts, with official HTTPS archive/commit pins and independent oracles.
  Earlier xxHash and original medley/cBench reserved tests are not used.
- Seven native LLVM19 settings explore optimization level, vectorization,
  inlining thresholds and disabling unrolling. All runtime samples are new;
  five initial bitcode modules are reused after exact source verification.
  Static menu finalization precedes declaration and keeps preliminary artifacts.
  Preflight: 140 O0/candidate/oracle comparisons, clocks excluded from fitting.
- All 20 training workloads are correct/eligible and pass declared O3 controls
  on both clocks. Training retains 528 cells / 12,672 pairs / 25,344 API batches.
  Thirty-nine compiled alternatives yield 78 outcomes; 67 qualify, 11 candidate
  controls fail. Forty-two aliases are not fit rows. Nine programs have distinct
  targets; jsmn's entire tested menu is O3-identical. Qualified losses remain.
- Six workload/candidate pairs pass declared primary gain gates: zlib_random
  large-inline, expat_nested O2, lua_tables small-inline, both BLAKE2 inputs
  no-vector, TinyExpr arithmetic large-inline. They are training search results.
  Best-observed-input training oracle: optimistic 1.028333x, not an SL result.
- Inherited order diagnostics pool even/odd indices despite varying starting
  sides. Separately declared actual-side/per-block sensitivity flags 17 CPU
  candidate controls and 20 effects (wall 16/21), with no baseline flags.
  Only 39 CPU / 40 wall primary-qualified targets have no additional flag in
  any role. Primary labels/selection stay frozen; report the limitation.
- Strongest lower-bound primary winner blake2_random/no-vector is selected by
  the predeclared rule despite its primary flags, without substituting another
  winner. Isolated confirmation: one DSO per fresh process, 16 invocations,
  432 outputs. Both controls pass; CPU 1.138758x (1.132303–1.145635x), wall
  1.138687x (1.132117–1.145469x), all blocks >1.03x; 12.185% less API CPU.
  Descriptive secondary actual-side diagnostic has no flags. This is selected
  training headroom in the current runner/reference implementation, not learned
  generalization, multi-machine replication, or an application-wide gain.
- Sixteen fixed Ridge/forest variants are evaluated and independently replayed.
  Eight CV variants are unscorable due to missing qualified choices. Eight are
  scorable but fail gates: lower forests choose O3 everywhere; others regress.
  Bundle `models/sl_broad_native_20261011_bundle.joblib` has experimental=None,
  default O3. Do not force an uncertified preset or pool incompatible old labels.
- Frozen development: both new implementations / all four workloads are correct
  across all seven settings and qualify on both clocks, no order flags. All
  choices O3; scores 1.000x, no learned gain. Twelve cells / 288 pairs / 576
  batches retained. Model freeze precedes development builds/native execution.
- 87 tests and 168 independent native O0/candidate comparisons pass. Source
  provenance checks 179 files and five reused modules. All 16 CV variants replay;
  five primary and four secondary corruptions reject. All 366 directly embedded
  prior generated artifacts remain unchanged, including the nested old archive.
  Default Parson export passes hashes/oracle; uncertified experimental export
  rejects before creating a directory. Completed resume/evaluation do not sample.
- Archive: `results/broad_iteration.zip`, SHA manifest, prior invocation ZIP
  nested, adjacent `broad_snapshot.log` outside its own archive. Startup draft
  saves current commands without changing installation/network/repositories.
  Native timings stay sequential on CPU2 without heavy-build/native-audit overlap.
  No new install, Git commit or push; reserved test executions remain zero.
- Next research work: versioned actual-side measurement qualification and
  timed-region features excluding untimed client preparation/verification;
  more distinct implementations in promising domains, then fresh holdouts.
  Neither proposed change is yet shown to improve SL. Do not promise project
  completion or an O3 gain within the earlier five-iteration estimate. RL/hybrid
  and generalized learned improvement remain open milestones.

## Preceding iteration: invocation-level real-library pairs, 11 October 2026

- Report: `INVOCATION_SL.md`. The worker switches after each invocation and uses
  separate byte-identical baseline and candidate copies for placement controls.
  Private native LLVM19 O3, strict FP, three 24-pair blocks, 40ms CPU batches and
  3% gates remain. Old measurement studies and models are preserved separately.
- Added pinned LZ4 1.10.0, jsmn 1.1.0 and xxHash 0.8.3. Training comprises five
  original programs (zlib, Expat, Lua, LZ4, jsmn), two inputs each; xxHash's two
  inputs form an entire-program development holdout. Inputs are not new programs.
  API CPU/wall time excludes startup/client I/O. Independent Python/system
  oracles and O0 checks pass across all 12 workloads and five settings.
- All ten training baseline controls pass both clocks. All 34 distinct candidate/
  workload outcomes qualify; negative results remain. Seventeen compiled
  alternatives and six O3-identical jsmn aliases are not counted as programs.
  Training retains 234 cells / 5,616 pairs / 11,232 timed API batches.
- All eight whole-original-program CV variants are scorable, but none passes
  the gain gates. Best utility variant scores 0.999431x, two changed workloads,
  zero confirmed CV gains. No forced diagnostic learner is fitted. Default O3;
  `models/sl_invocation_native_20261011_bundle.joblib` has experimental=None.
- O2 on the nested-XML training input has primary qualified CPU speedup
  1.034304x, interval 1.030261–1.041807x; wall 1.034186x. A declared post-study
  confirmation with only one implementation per process retains 432 outputs.
  Both controls pass, CPU speedup 1.030862x (1.018357–1.039170x), wall 1.030840x.
  One block and lower bounds miss 1.03x. This does not confirm improvement above
  the declared floor, and no secondary timing is used for fitting or retuning.
- Frozen development chooses O3 for both inputs. xxhash_random passes controls
  on both clocks; xxhash_pattern fails and stays excluded. Conditional score
  1.000x; no learned unseen-program gain. Six control cells / 144 pairs / 288
  batches retained. Original medley/cBench final tests remain closed.
- 81 unit tests and 60 independent O0/candidate comparisons pass. Four primary
  and four secondary tamper checks reject corruption. Materialized upstream
  sources match pinned archives; secondary statistics and outputs are audited.
  All 800 prior generated files in paired_iteration.zip are unchanged. Default
  xxhash_random export passes oracle and hash checks; unqualified experimental
  export rejects before making a directory. Resume/evaluation reuse completed
  frozen studies without collecting new timings.
- Evidence snapshot: `results/invocation_iteration.zip`, with SHA manifest and
  prior paired snapshot nested. Freeze source/selection/splits before all new
  studies; never overwrite existing reports. New invocation experiment names
  are fixed constants and need a separately versioned workflow/declaration.
  Native timing must stay sequential on CPU2 without concurrent native checks
  or heavy builds. No new package install, Git commit or push this iteration.
- Next: broader distinct real-program coverage and training-only candidate
  discovery, then more entire-program holdouts. Data collection and CV coverage
  improved materially; profitable generalized selection remains unproved.
  Do not pool scientific or application-startup labels into warm library API
  targets. Retain O3 until independent learned gain qualifies; defer RL/hybrid.

## Preceding iteration: persistent pairs and CPU-service-time SL, 11 October 2026

- Full report and commands: `PAIRED_SL.md`. Native LLVM19 O3 uses march=native,
  PIC and strict FP. A persistent DSO worker alternates logical pairs, refreshes
  inputs and records CPU service time and wall kernel latency independently.
  All interrupted samples remain; 3% controls and confirmation gates are retained.
- Eight pipeline settings pass finite, full-value output equivalence on all
  22 training and six development kernels. Three settings are O3-identical
  throughout training; the compiled menu has 36 distinct non-O3 alternatives.
- Formal training: 258 cells / 6,192 pairs / 12,384 timed kernel batches.
  O3 CPU controls pass 19/22. Only four complete menus qualify, all one family.
  A declared post-study partial-label view retains 19 programs, but 109 candidate
  labels comprise 101 O3-identical aliases and only eight distinct measurements
  across seven programs. Qualified losses remain; missing targets stay absent.
- The adapted-input training kernel ludcmp shows qualified search headroom:
  instcombine before O3 yields 1.16926x CPU speedup (14.48% lower CPU time),
  interval 1.13312–1.20613x, and 1.17030x wall speedup. Both controls and all
  three effect blocks pass. This is one training kernel, not a learned,
  unseen-program, application-wide or independently replicated result.
- All eight Ridge/floor CV variants have unscorable predictions due to missing
  qualified targets. None is selected. The original new bundle contains no
  experimental model. A separate declared fixed lower-bound Ridge10/floor3%
  diagnostic is frozen before development; it is explicitly not CV-certified.
  Bundle: `models/sl_paired_native_preset_20261011_bundle.joblib`. Default is O3.
- Development: all six correct, one too short to time, only seidel-2d passes
  controls on both clocks. That frozen choice is O3; conditional scores 1.000x,
  zero changed choices, zero confirmed gains. Predicted no-vector on eligible
  adi is excluded after baseline failure. Failed controls are never retried
  until success. Development retains 15 cells / 360 pairs / 720 timed batches.
- 72 unit tests and 224 independent O0/candidate comparisons pass. Pair order,
  invented gain and feature tampering are rejected. 1,525 prior generated files
  match the earlier archive. Its sole completion-log mismatch is explained and
  verified against the actual archive: stdout was empty when archived and later
  contained the final ZIP hash/count/size. Neither old file is modified.
- Default and opt-in experimental adi exports match their frozen bitcode/DSOs
  and full output hashes. Export manifests disclose missing performance
  qualification and CV status. The numerical check supplies no new speedup label.
- Reports: `results/paired_native_20261011_{train,development,evaluation,verification}.json`,
  both selection artifacts, declarations, source provenance and export checks.
  Snapshot: `results/paired_iteration.zip`, including the immutable prior ZIP.
  Startup instructions: `results/paired_start_skill.md` and environment draft.
- Next performance prerequisite: a stable runner and broader qualified
  real-program labels before frozen unseen-program validation and RL/hybrid.
  Scientific kernels, warm PIC CPU time, and old application wall labels remain
  separate. Medley and all cBench final tests remain closed. No new broad SL gain
  or completion percentage is established. All work is local; no commit or push.

## Latest iteration: research-guided corpus and timing diagnostics, 10 October 2026

- Read CompilerGym, AutoPhase, and Robust benchmarking in noisy environments.
  HLS cycle and instruction-count results are distinct from native runtime gains.
  Detailed citations, methodology, commands, and limits: `RESEARCH_SL.md`.
- Added official pinned PolyBench/C 3.2: 22 training, six stencil development,
  and two reserved medley kernels. All 28 executed kernels pass finite output
  and full-value equivalence checks against O0 across six LLVM19 pipelines.
  Six numerical input adapters and a separate uninitialized Bza repair preserve
  upstream files and kernel computations; these adaptations are disclosed.
- LLVM19.1.7 works privately beside LLVM10. The new worker consumes outputs,
  reinitializes each repetition, and measures kernel latency in-process with
  launch/init/hash costs outside the timer. Records retain scheduler tick deltas.
- An unchanged 24-run zlib diagnostic found wall/steal correlation 0.878.
  Hypervisor contention is a measured contributor; other noise remains possible.
- Formal training study: 156 cells, 2,496 timed workers, 918 with positive steal.
  All 22 O3 controls failed the declared 3% gates. Zero new labels were fitted.
  Historical accepted training remains seven real programs plus six synthetic
  kernels. Scientific kernels are not counted as real applications.
- Independent SL supports candidate-specific static LLVM19 features, lower-bound
  and regression-weighted Ridge, and entire-family held-out CV. No regressor was
  fitted to failed labels. `models/sl_polybench19_bundle.joblib` is explicit O3.
- Future collection performs qualification preflight before candidate timing.
  Development timing is blocked until a qualified learner exists. Development
  correctness passed; its runtime was not tuned. All old and new reserved tests
  remain untouched. A timing-capable runner is the next external prerequisite.
- New reports: `results/polybench_{train,development,selection,readiness,verification}.json`.
  60 unit tests and 196 independent native output checks passed; edited raw
  timings and invented gains were rejected; 490 prior generated files verified
  unchanged. Default fdtd-apml export matched its full output reference.
  Snapshot: `results/polybench_iteration.zip`. Reusable LLVM19 refresh/start
  instructions were saved to the environment draft; publication remains separate.
  Compilation/correctness readiness and performance-measurement readiness differ.
  No modern O3 gain or project completion percentage is established. Changes
  remain local; no commit or push. RL/hybrid remain future work.

## Latest iteration: real workloads and regression-aware SL, 10 October 2026

- Added pinned zlib 1.3.1, Expat 2.7.3 and Lua 5.4.8 implementations with two
  deterministic inputs each. Native drivers compile all four pipelines and pass
  byte-exact output checks and independent Python/system-library checksum oracles.
  These are three upstream programs with custom workloads, not six new programs.
- The six-input pilot failed all unchanged O3 controls before candidate effects.
  A separately declared study with three fixed first inputs, longer O3-calibrated
  durations and 20 pairs/block also failed all initial 3% controls. Failed reports
  are preserved, never fitted. Accepted training remains seven real programs plus
  six auxiliary kernels, 39 candidate rows. No retry until acceptance was used.
- Added point/lower-bound Ridge and regression-weighted lower-bound prediction.
  Real programs determine CV scores; synthetic kernels supply optional fit data
  and never count as evidence of real-program generalization. Entire original
  programs, including all input variants, are held out together.
- The risk-aware experimental policy is
  `with_kernels_lower_risk_ridge10_floor0.01`: CV point score 1.00223x on seven
  real programs, two changed choices, no point regressions and no confirmed gains.
  It fails deployment gates and abstains to O3 on all four eligible development
  inputs. The higher-ranked point predictor reproduces the previous choices and
  retains a CV regression; default remains O3.
- Final bundle: `models/sl_robust_long_bundle.joblib`; it also retains the previous
  experimental model as an immutable reference. The earlier `sl_robust_bundle`
  is a pilot artifact saved before the longer timing study, and is preserved.
- Fresh 4-block/40-pair/1% development timing failed all four initial O3 controls.
  No new effects were accepted and no new speedup was established. Earlier 2.72%
  TIFF development evidence remains historical, not reproduced in this instance.
  Both wall and process CPU clocks were unstable; address-layout/CPU diagnostics
  did not resolve the measured variability. Exact platform cause is undetermined.
- `scripts/check_timing.py` rejects the failed study with exit 2. Runtime readiness
  is false under these protocols, although compilation and correctness work.
  New aggregate intervals include timing-block/pair and original-program resampling.
- 49 unit tests passed; 34 actual static cases re-extracted; 36 native oracle/output
  checks passed. Default source inference and risk-aware non-O3 bitcode inference
  matched frozen bitcode/executables. Corrupt reported gains were rejected and
  prior generated artifacts retained. Syntax and whitespace checks passed.
  Tiny prediction-score round-off across numerical backends is tolerated while
  configurations, hashes, protocols and reported effects remain exact.
- New formal timing: 52 cells, 2,240 timed executions and 104 cell warmups; separate
  clock/placement diagnostics add 576 executions. No positive targets were selected
  from failed controls. No development runtime target was fitted.
- Report: `ROBUST_SL.md`; data: `results/real_train{,_long}.json`,
  `results/robust_long_selection.json`, `results/robust_long_development.json`,
  `results/runtime_readiness.json`, `results/robust_verification.json`;
  snapshot: `results/robust_iteration.zip`. All changes remain local; no commit,
  push, new environment dependencies or configuration changes.
- Next useful prerequisite is a timing-capable instance or dedicated runner that
  passes unchanged controls, followed by broader real-program labels and frozen
  final evaluation. Reserved susan/tiff2rgba/tiffmedian tests remain untouched.
  RL/hybrid are unimplemented. Do not claim completion or suite-wide gains.

## Latest milestone: candidate-aware experimental SL, 10 October 2026

- A frozen learned policy selected instcombine-before-O3 for TIFF dithering
  dataset 2 and achieved **1.02724x (2.72% speedup) over LLVM 10 opt O3**.
  Paired interval: 1.02354–1.03054x. Both unchanged controls and all four effect
  blocks passed a separately declared 1% confirmation protocol with 40 pairs
  per block. This is an experimental development result, not a pristine final
  test or family-disjoint generalization.
- The same policy regressed jpeg-d dataset 2 by 0.67%; other gains were below
  the confirmation gate. Its two-program point score was 1.010706x; the summary
  bootstrap omits timing uncertainty and is not a robust suite-wide claim.
- Default remains O3: no predictor passed the training deployment gates.
  Experimental model: `raw_ridge1_floor0`, frozen from training CV, in
  `models/sl_transform_policy_bundle.joblib`. The earlier 3% studies retain
  their original, unconfirmed labels. No retries until acceptance were used.
- New static features: 156 candidate-versus-O3 function, CFG/cyclic-region,
  opcode, direct-reachability and transformation features. No benchmark identity,
  instruction-count reward or measured runtime is a predictor input.
- Training: seven reliable real programs plus six controlled synthetic kernels,
  39 complete candidate labels. Eight synthetic kernels were attempted; two
  failed initial controls. Synthetic kernels are not extra real-world coverage.
- Three pooled model families, raw/guarded predictors and training-only decision
  floors 0%, 1%, 3% were evaluated with program-disjoint inner/outer fits. CV is
  conditional on prior training-wide menu selection and development-informed
  feature design. No development runtime target was fitted.
- `scripts/optimize_transform.py` accepts a new C or LLVM bitcode file and
  exports selected bitcode plus an optional executable without running it.
  Source-file default-O3 and experimental non-O3 inference matched frozen BC/ELF.
- 32 unit tests passed; actual cached features were re-extracted from all frozen
  candidate IR. Raw coverage, decisions, controls, effects and hashes verified.
  New experiments: 168 cells / 6,240 paired timed executions / 336 cell warmups.
- Report: `TRANSFORM_SL.md`; data: `results/kernel_train.json`,
  `results/transform_policy_selection.json`, `results/transform_policy_confirmation.json`;
  snapshot: `results/transform_iteration.zip`. Old artifacts/snapshot preserved.
  No dependency/configuration changes, commit or GitHub push.
- Remaining: more independent real training programs, broader frozen final
  evaluation and regression control; RL and hybrid learning remain unimplemented.
  Reserved susan/tiff2rgba/tiffmedian test programs remain untouched. Report
  milestones and measured evidence instead of project-completion percentages.

## Latest iteration: compact SL, 10 October 2026

This workspace contained an older checkout; later teacher-search artifacts
mentioned in the conversation were absent. The current iteration reconstructed
the four-choice menu from that history and collected new evidence. See
`COMPACT_SL.md`; the older sections below describe the original handoff.

- Complete controlled menus: seven training inputs from seven original programs;
  four development inputs from two original programs. No reserved test was used.
- New training confirmations over LLVM 10 opt O3: long bitcount 1.1390x and
  TIFF grayscale 1.0449x. JPEG encoding 1.0333x point estimate did not clear the
  confirmation gates. These are fixed-configuration results, not learned gains.
- A training-derived fixed pipeline transferred to development TIFF dithering:
  1.0469x and 1.0433x on two inputs of the same program, with all gates passed.
  Development was previously observed; do not call it a pristine final holdout
  or claim generalization across unrelated families.
- Grouped SL cross-validation did not pass the deployment rule. The selected
  model remains O3, and all four frozen diagnostic learners chose O3 on eligible
  development inputs. Learned improvement remains unproven. RL is not implemented.
- Twenty unit tests and three existing executable smoke workflows passed;
  static inference and native code-generation preservation were verified.
- Training: 232 cells / 4,640 paired timed executions; development:
  112 cells / 2,240 paired timed executions. Failed controls were excluded without
  retries. Negative targets were retained and complete menus were required.
- New code: `src/benchmarks/compact.py`, `src/supervised/compact.py`,
  `scripts/{collect,analyze,train,evaluate,predict}_compact.py`,
  `scripts/snapshot_compact.py`, and `tests/test_compact.py`.
- Data: `results/compact_train.json`, `results/compact_validation.json`;
  models: `models/sl_compact_selector.joblib`, `models/sl_compact_comparators.joblib`;
  reports: `results/compact_selection.json`, `results/compact_evaluation.json`;
  snapshot: `results/compact_iteration.zip`. All are local; nothing was pushed.
- Next: candidate-specific transformation and function/loop features, and more
  independent training programs. Keep current validation results marked observed
  and preserve the reserved tests for a final frozen evaluation.

## 1. Project Objective

NeuroCompiler is a machine-learning-based LLVM compiler optimization system.

The objective is to learn program-specific LLVM pass sequences using supervised learning (SL) and reinforcement learning (RL), then evaluate their runtime performance against LLVM optimization levels such as `-O2` and `-O3`.

Architecture:

`LLVM IR → AutoPhase Features → SL Pass Ranking → Top-K Candidates → RL Pass Selection → LLVM Transformation → STOP → Optimized Program`

Runtime performance is the primary objective. LLVM IR instruction count is diagnostic information, not the optimization reward.

## 2. Environment

- OS: Ubuntu under WSL2
- Python: 3.10
- Conda environment: `neurocompiler`
- CompilerGym: 0.2.5
- LLVM: CompilerGym-bundled LLVM 10
- NumPy: 1.23.5
- pandas: 2.0.3
- scikit-learn: 1.3.2
- joblib: 1.3.2
- Gym: 0.21.0
- AutoPhase features: 56
- CompilerGym LLVM action space: 124

The legacy environment requires pinned dependencies. Do not upgrade packages indiscriminately.

## 3. Benchmark Configuration

Dataset: `cbench-v1`.

Of 23 available benchmarks, 18 were found buildable and runnable.

Benchmark split:

- Training: 12 programs
- Validation: 3 programs
- Test: 3 programs

Exact assignments are defined in `configs/benchmarks.py`.

Keep benchmark-level separation. Do not use the held-out test benchmarks for model selection or hyperparameter tuning.

## 4. Curated LLVM Passes

Sixteen passes are defined in `configs/passes.py`:

`adce`, `simplifycfg`, `constprop`, `dce`, `dse`, `early-cse`, `inline`, `gvn`, `ipsccp`, `instcombine`, `jump-threading`, `licm`, `loop-rotate`, `loop-unroll`, `mem2reg`, `sroa`.

A STOP action is planned for sequential RL.

## 5. Implemented Components

- CompilerGym environment initialization
- AutoPhase feature extraction
- LLVM action mapping and pass execution
- Runtime measurement
- Paired runtime experiments
- `-O0`, `-O2`, and `-O3` baseline generation
- cBench benchmark scanning
- Supervised dataset generation
- Initial supervised model training
- Supervised validation evaluation

Inspect the repository for exact implementations and existing tests.

## 6. Runtime Methodology

Development measurements generally use:

- CPU affinity via `taskset -c 2`
- One warmup
- Three measured executions
- Median runtime

Paired runtime experiments demonstrated substantial timing noise and occasional outliers.

Final evaluation must use more rigorous measurements, interleaving, warmups, repeated executions, and robust statistics.

Speedup is calculated as:

`runtime_before / runtime_after`

For final comparison against LLVM `-O3`:

`runtime_O3 / runtime_NeuroCompiler`

## 7. Supervised Learning Results

Training dataset:

- 12 benchmarks
- 16 passes per benchmark
- 192 rows
- 56 AutoPhase features
- Pass identity
- Runtime-derived labels

Validation dataset:

- 3 unseen benchmarks
- 48 rows

Current model:

`HistGradientBoostingRegressor`

Inputs: AutoPhase features and one-hot pass identity.

Target: clipped log-speedup.

The initial model predicted identical scores for all passes. Reducing `min_samples_leaf` allowed action-specific predictions, but validation ranking remained poor.

Latest validation results:

- Average Spearman correlation: -0.0069
- Recall@4: 0.0833
- SL Top-1 geometric mean speedup: 0.9271×
- Global-pass baseline: 0.9607×
- Observed oracle: 1.8352× (unverified, affected by potentially noisy measurements)

**The supervised model has not demonstrated generalization. Do not describe it as successful.**

Some unusually large speedups are suspicious, including `jpeg-d / sroa` and `tiff2bw / constprop`.

## 8. Next Development Tasks

1. Audit the dataset and supervised-learning pipeline.
2. Investigate runtime measurement anomalies.
3. Compare simple regularized models with gradient boosting.
4. Evaluate predictions on unseen benchmarks using pass-ranking metrics.
5. Improve training data using multiple LLVM states per benchmark.
6. Implement runtime-aware RL experience collection.
7. Train an RL policy with STOP.
8. Integrate SL Top-K candidate selection with RL.
9. Evaluate against `-O2`, `-O3`, fixed, random, SL-only, and RL-only strategies.
10. Produce ablations, plots, and reproducible results.

## 9. Important Constraints

- Preserve the existing architecture unless a concrete technical issue justifies changing it.
- Do not use IR instruction reduction as a substitute for runtime reward.
- Do not silently fall back to random policies when trained models are missing.
- Do not leak validation/test benchmarks into training.
- Do not claim improvements over `-O3` using speedups relative to an unoptimized program.
- Prefer reproducible, benchmark-level evaluations.
- Avoid expensive runtime experiments unless their expected cost is justified.
- The project must remain feasible on a Ryzen 5 5600H laptop with 16 GB RAM.

## 10. Current Status

The LLVM environment, benchmark harness, datasets, and initial SL training pipeline are operational.

The main unresolved problem is poor supervised-learning generalization.

RL, hybrid inference, and final comparative evaluation have not yet been implemented.

**Immediate next task: audit and improve the SL modelling/evaluation pipeline before starting RL.**
