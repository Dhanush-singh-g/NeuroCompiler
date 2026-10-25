# Live application verification

## Evidence and prediction diagnostics — 25 October 2026

**67 selected tests pass.** They include stale/tampered artifact rejection,
incorrect aggregate rejection even when report hashes are refreshed, fold
leakage detection, training-range bound consistency, equal checkpoint selection,
and family bootstrap clustering. The real LLVM fifty-function module is flagged
outside the observed training range; reference/selected native output agrees.
The advisory check leaves the original policy selection unchanged.

Four-fold training-family SL validation records immediate-reward MAE 0.04141
and best-immediate-action fraction 70.4%, with ties accepted and equal family
weight. These are component diagnostics, not runtime or overall compiler
accuracy. Original SL/RL coefficients were replayed from the frozen data and
matched. Every original declared implementation hash remains valid.

The post-hoc baseline audit uses all five states plus O3 for fixed/random
sequences. The exploratory six-family interval for the fixed/hybrid count ratio
is [0.9816, 1.0088], so a hybrid advantage remains unestablished. Seven total input
arguments now have candidate-output coverage; the new five account for 720
additional passing checks, including all guarded baseline outputs.

Browser checks verify all six existing evaluated demos and mode/count export
consistency, native CRC output, two clocks, range warnings on unfamiliar C,
Markdown/JSON exports, and mobile layout. New evidence metrics and the audit
JSON download are checked against the actual artifacts. All added analyses are
post-hoc and are described in [CREDIBILITY.md](../CREDIBILITY.md). They do not
open a new unseen-program study or change the deployed weights.

## Expanded family-disjoint count study — 25 October 2026

Forty authored synthetic training programs from 24 families produce 3,832
transitions. Every probed training transform passes two native inputs against
agreeing GCC/Clang O0 references. A single model/split/declaration is frozen
before compiling twelve reserved programs from six other algorithm families.
All 240 held-out candidate-output checks pass. Raw SL/RL/hybrid policies each
reduce counts on eight and increase counts on four. The explicit static
checkpoint/O3 guard reduces counts on eight and selects O3 on four. Fixed-pass
controls remain competitive; no RL-specific, runtime or real-world advantage is
claimed. Full numbers and derived guarded-baseline controls are in
[UNSEEN_EVALUATION.md](../UNSEEN_EVALUATION.md).

**58 tests pass**, including dataset/model hash binding, family separation,
checkpoint rollback, O3 tie preference and native correctness in all modes.
The legacy browser regression passes. Separate browser checks confirm all six
new demos match the frozen raw/guarded counts and model SHA, including real O3
binary identity on both fallback families. Current modes, native CRC output,
CPU/wall summary values, guard provenance in Markdown, reload and mobile layout
are checked. A long-hash overflow in the new scope panel was fixed during browser
verification. The results are visible under Model & scope; the screenshot
[unseen-count-evaluation.png](screenshots/unseen-count-evaluation.png) records
the actual baseline table. Historical verification entries below refer to the
prior artifacts; original sequential files are retained in sequential_v1.

## Standard vs learned runtime summary — 25 October 2026

The summary above all detail tabs presents standard LLVM -O3 and NeuroCompiler
with large measured execution times, explicit method/pass labels, and static IR
counts. Before execution it says Not measured. CPU/wall clocks update the summary
and comparison table together. Technical model details are collapsed by default.

The 54-test suite and updated legacy browser acceptance check pass. Additional
real-browser checks for SL, RL, and hybrid match the displayed action sequence
and counts to the downloaded analysis JSON. A hybrid native run verifies both
CPU/wall summary times against exported four-way measurements, restored results
after refresh, visibility across all tabs, mobile layout, and clearing old times
when input changes. No page errors were observed. The actual diagnostic screenshot
is [runtime-comparison.png](screenshots/runtime-comparison.png); it contains an
inconclusive measurement, not evidence of a runtime improvement. Models, rewards,
and timing reliability thresholds were unchanged.

## Trained sequential proxy modes — 25 October 2026

The user accepted instruction count or execution time as an objective. This
update implements the instruction-count version explicitly. A source/tool-bound
collector generated 512 actual LLVM state/action/next-state transitions across
eight previously opened synthetic training programs. Immediate-reward ridge SL
and 20 rounds of offline fitted Q iteration were trained on those transitions.
The hybrid selects from a top-three SL shortlist plus STOP using Q values.
Weights, dataset and diagnostic evaluation are committed as portable JSON.

The product exposes legacy SL plus new SL, RL and hybrid selections. New modes
show real opt action traces, initial/selected/O3 counts, four-way static counts,
objective and limitations. The selected artifact is frozen before the independent
native output/runtime comparison. Model/schema/tool hashes are checked; no
submitted program is used to update weights. The legacy coefficients and all
frozen studies remain unchanged.

**54 selected tests pass**, including delayed-reward learning versus immediate
SL, hybrid masking, reward/context/split guards, real LLVM transitions/STOP, all
three trained modes compiling and preserving native output, plus prior app,
ranking, dashboard and archive tests. Across five familiar examples and three
policies, 90 O0/O3/selected output checks pass. These are diagnostic examples,
not held-out scientific validation; mixed IR results against O3 are recorded in
SEQUENTIAL_RESULTS.md, including losses.

Browser checks exercise all three trained modes, hybrid native output and four-way
comparison, IR and Markdown export, static counts, active learning labels and
mobile layout with zero page errors. The legacy browser regression also passes.
Proxy training uses structural LLVM verification, not native semantic checking
of every training transition. Native correctness is separately gated in the app.
No runtime-trained RL artifact or unseen-real-program gain is claimed.

## O1 / O2 / O3 / NeuroCompiler — 25 October 2026

The application now builds the original four model pipelines, freezes the learned
decision, and then builds explicit O1/O2 comparison baselines. Display options
are O1, O2, O3, and the model-selected artifact. Comparison-only baselines are
never model inputs or new learned choices. Shared initial LLVM10 bitcode and
matching baseline codegen levels are recorded; these are reproducible LLVM
pipeline baselines, not a claim of equivalence to every Clang driver's defaults.

`live-four-way-v3` measures a self-control for each distinct executable and all
unordered direct pairs. Every cell retains 12 pairs/three blocks; cell order and
balanced starting order are fixed-seed shuffled. Bootstrap replicates increase
to 8000, with interval tails adjusted across all cells and both clocks. Existing
duration/CV/order/control tolerances remain. Preference requires complete pair
coverage, passed self-controls and direct lower bounds above 1.03× against every
competitor on both clocks, plus a consistent observed ranking. Shared executable
winners and all-identical entries are explicit; fastest observed is separate.

**48 selected tests pass** across live application, four-way ranking, scorecard,
dashboard and archive tests. Cases cover genuine O1/O2 artifacts, no O1/O2 model
features, prediction frozen before baseline completion/execution, NC and O1
ranking fixtures, close ties, failed controls, missing pairs, shared identities,
CPU/wall tradeoffs, and avoiding an individual NC win for a shared O3 executable.
Synthetic ranking fixtures are software tests, not native gain evidence.

All seven positive programs in DEMO_PROGRAMS.md pass O0 plus all six built
pipelines twice: **98 matching native output executions**. Five recent four-way
analyses match the original frozen model's raw scores and choices to 1e-10.
Desktop/mobile Playwright checks pass with zero browser errors/external requests,
including four runtime cards, O1 IR inspection, updated Markdown/JSON exports,
session counts, stdin/upload, stale-input invalidation and failure recovery.
Screenshots are actual acceptance-run observations; timing remains inconclusive.

No frozen research source, model coefficients, formal study data, or reserved
workload changed. There was no model training or new generalization claim.

The following sections describe earlier presentation versions.

## Large runtimes, preference, and session scorecard

The existing theme is retained. O3 and NeuroCompiler program runtimes now have
large separate cards, other pipeline times are larger in the table, and a large
demo-preference banner highlights a comparator only for qualified faster/slower
results. It explicitly keeps identical code and inconclusive results without a
preferred option. CPU/WALL changes the displayed runtime values. These are
executable times, excluding analysis and compilation overhead.

The session scorecard separates the known sieve training example, other bundled
demos, and custom inputs with unverified provenance. Repeated input/model pairs
count once using the latest completed comparison; model versions and different
inputs remain separate. Wins/losses require both clocks, correctness blocks are
separate, and failed timing checks are tracked even for unchanged code. Session
counts are descriptive and reset with the server; JSON export is available.
Expandable plain-language descriptions explain the optimization passes.

**40 selected tests pass** across live-app, scorecard, dashboard, and archive
tests. Added cases cover repeat-input deduplication, latest-comparison behavior,
provenance separation, model versions, correctness blocks, and rejecting a win
supported by only one clock. Browser checks pass on desktop/mobile, including
runtime font size, same-code/no-preference behavior, pass explanations, and a
real session-summary download. UI-only fixtures separately exercise NC/O3
preferred-card highlighting and unqualified suppression; fixtures are not saved
or presented as native experiments. Actual live controls remain inconclusive.

No model weights, research data, or formal protocols changed in this update.

## Comparison clarity and native timing update

The existing visual theme/layout is retained. The decision view now distinguishes
identical executable menus from a model preference for O3, displays time estimates
in percent, and collapses technical attribution details. Small effects and
training-scale extrapolation are flagged. The comparison summary explicitly
identifies NeuroCompiler's choice, its time change against O3, reliability
failures, and any available gap to the fastest qualified point estimate.

Choosing the same O3 executable is displayed as unchanged code, with a reference
ratio of 1; the raw null-control ratio remains diagnostic data. Percentage time
changes use reciprocal speedup with the correct denominator. Summary times use
paired geometric means so they agree with the paired ratio; the detailed table
continues to show medians. Qualified-menu rankings are post-measurement point
estimates, not learned choices or proven optima.

`live-native-process-v2` uses a small C fork/exec/wait4 helper to exclude Python
launch and Python pre-execution setup from the measured interval. Native process
startup remains included. The helper preserves affinity/resource limits, records
the CPU identifier, and terminates its child when its parent dies. Helper and
model hashes are checked before execution. Model hashing uses the same bytes as
inference; invalid numerical thresholds/scores are rejected. A fixed-seed
shuffled schedule balances starting order within every block. Quality thresholds
are unchanged. This versions the presentation protocol only; old results and
formal research protocols are not rewritten or pooled.

Current checks: **34 live/dashboard/archive tests** and **32 original
transform/compact tests** pass. Added cases cover identity versus noisy controls,
faster/slower percentages, gap denominators, distinct-menu explanations, invalid
model thresholds, native clock separation, and changed helper/model rejection.
Desktop/mobile acceptance checks cover the updated summary, unchanged-code case,
and inconclusive tiny programs. The unsupported-interpreter PATH setup check
selects a compatible Python; the cloud's private legacy libtinfo activation is
still required, whereas documented Ubuntu setup installs that system dependency.

The model coefficients/menu and original raw decision rule are unchanged. These
engineering changes do not establish improved model accuracy or generalization.
The checked live timing controls remain inconclusive and are not new labels.

## Initial application verification

Verified on the current **x86_64 Linux cloud environment**. Windows/WSL2 setup is
documented in `PRESENTATION.md` and needs rehearsal on the presentation computer.

- Created a separate app environment with only numpy1.26.4 and networkx3.4.2.
  Inference does not require sklearn, CompilerGym, or loading a pickle.
- Downloaded the complete upstream LLVM10 archive over HTTPS, verified the
  published SHA256, extracted the selected tools, checked binary hashes, and
  verified a second installation attempt without replacing them.
- Executed the documented setup and startup helpers. The setup smoke check
  compiles real C through all four pipelines, extracts156 fields per alternative,
  and predicts without native program execution. Repeat setup passes.
- **29 tests pass** across `tests.test_presentation`, `tests.test_dashboard`, and
  `tests.test_workspace_archive`. The twelve live-app tests include real
  compilation, argv/stdin, model contracts, short/noisy measurement rejection,
  Host/Origin/session protection, source-analysis without execution, output
  mismatch blocking, artifact tampering, bitcode exports, compiler errors,
  cancellation, serialization, and a bounded infinite loop.
- **32 existing tests pass** across `tests.test_transform` and
  `tests.test_compact`, using the original research Python environment.
- Portable-model scores/choices match the original frozen sklearn selector on
  five checked live analyses, to 1e-10 numerical tolerance.
- Chromium/Playwright acceptance checks pass: desktop/mobile panels, code
  analysis, attribution, IR selection, trusted execution, matching output,
  CPU/wall display, Markdown/JSON downloads, refresh recovery, keyboard tab
  navigation, editing invalidation, compiler-error recovery, real stdin,
  actual `.c` upload, refresh during compilation, and the preserved research
  dashboard. **Zero browser errors and zero external application requests.**
- A separate browser check downloaded both model-selected and approved-O3
  bitcode and matched their bytes against the analysis's artifact SHA256 values.
  The checked desktop screenshot is `presentation/screenshots/decision.png`.
- JavaScript syntax and Git whitespace checks pass.

The prime sieve is explicitly a **synthetic training example**, not a fresh
test. Its checked static prediction is O3→GVN→DCE. Demonstration self-controls
did not qualify, so live timing interpretations remained **inconclusive**.
The tiny stdin example printed55 and was also correctly too short to qualify.
These are application acceptance checks, not new formal research results.

No frozen study source, declaration, report, model, dashboard snapshot, or
reserved workload was changed. No training/holdout evaluation or RL experiment
was launched. Existing training-only headroom and failed selection/admission
results retain their original scope. Learned generalization over O3 remains
unproven; the approved policy remains O3.

Current machine artifacts/logs stay under ignored `.presentation/` and `/tmp`.
They are not required to start a fresh checkout. The portable model's exact
original model/report/training provenance is retained in `presentation/model.json`.
