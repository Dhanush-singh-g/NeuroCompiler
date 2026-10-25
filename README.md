> **Expanded SL/RL demo:** 40 training programs, 3,832 native-checked
> transitions, a frozen 12-program unseen-family count evaluation, and an
> explicit static checkpoint/O3 guard are available on this presentation
> branch. See [results and limitations](UNSEEN_EVALUATION.md). Count reduction
> is not a runtime speedup, and an RL-specific advantage remains unproven.

# NeuroCompiler

**Live presentation branch:** [PRESENTATION.md](PRESENTATION.md) explains the
Windows/WSL2 setup and five-minute demonstration. The new decision explorer
accepts C programs, extracts static features, shows an existing experimental
model's LLVM pipeline prediction, and optionally checks output and compares
native runs in a four-way **O1 / O2 / O3 / NeuroCompiler** comparison. Start it with `bash scripts/start_presentation.sh` after
setup. The Learning policy dropdown also provides trained SL/RL/hybrid instruction-count modes. The approved research default remains O3; this feature does not establish learned
generalization or alter the preserved research studies.

An experimental LLVM optimization project with a legacy supervised runtime
selector and new SL, offline RL, and hybrid instruction-count proxy policies. Runtime improvement over O3 is the research objective;
successful learned generalization has not yet been established.

The [results dashboard](dashboard/README.md) provides an interactive overview,
benchmark explorer and measurement-control matrix from preserved evidence.
The recorded dashboard snapshot is included in Git, so it works directly from
a fresh clone. See [START_HERE.md](START_HERE.md) for Windows, macOS and Linux
instructions. Run `python scripts/serve_dashboard.py --port 8000` from this
directory, then enter `http://127.0.0.1:8000` in your own computer's browser.
It needs only Python 3.10+ and no pip/npm packages; it does not run benchmarks or
imply a learned gain. The full generated research workspace is distributed
separately through [GitHub releases](https://github.com/Dhanush-singh-g/NeuroCompiler/releases).
Rebuilding dashboard data is optional and requires restoring those raw records.

The current prototype uses candidate-specific function and CFG features, pooled
supervised prediction with uncertainty/regression penalties, controlled runtime labels, program-grouped validation,
an explicit O3 fallback, and experimental learned policies. The earlier LLVM10
CLI accepts a new C or LLVM bitcode file without executing the input. Current
LLVM19 studies export library artifacts for registered workloads; their evidence
remains separate from the earlier arbitrary-source workflow.

See [EXPANDED_SL.md](EXPANDED_SL.md) for the latest iteration: 21 training
implementations/42 correctness inputs, eight newly pinned libraries, and two
untouched development implementations. Every training input passes all four
settings; 40 compressed streams pass independent reconstruction and 123 tests
pass. A source-only portable Linux kit passes a relocated fresh-build check.
Longer-batch admission and separate screens of all five logical CPUs find no
target meeting the declared controls, so no new training labels/models are
created. Earlier evidence remains intact; a quieter target is the next
prerequisite. No new learned O3 gain is claimed.

See [PERSISTENT_SL.md](PERSISTENT_SL.md) for the preceding iteration: separately
loaded persistent workers and a declared measurement-method pilot. Micro
interleaving passes 7/8 inputs in both the pilot and independent confirmation.
A preselected BLAKE2 training probe reproduces 1.137x speedup, or 12.1% less
API CPU time. A separate fresh-timing SL study retains 11 qualified candidate
targets across six original programs, versus zero previously. All 16 model
configurations execute 128 program-level CV fits: eight forests choose O3
everywhere; eight Ridge variants lack outcome coverage. No model qualifies.
Only one of four repeated-development inputs has valid timing controls and
chooses O3. No learned gain is established. 113 tests pass; earlier evidence
and frozen source remain intact. Shared-VM timing coverage remains a limit.

See [REGION_SL.md](REGION_SL.md) for the preceding iteration: timed-region CFG
features, one implementation per process and actual-side order qualification
within every block. The study has 13 training implementations / 26 workloads and
two fresh development implementations / four workloads. All pass correctness.
Only seven training baseline controls pass; no candidate control or development
control qualifies. VM steal rises during the run. No candidate labels survive,
so no model is fitted and O3 remains the default. Holdout scores are unavailable.
101 tests, 120 independent native correctness comparisons and the evidence audit
pass. The feature ablation cannot assess prediction quality without labels.

See [BROAD_SL.md](BROAD_SL.md) for the preceding iteration: ten training programs
(20 workloads), two held-out implementations (four workloads), seven settings
and 16 Ridge/forest comparisons. Its separate-process BLAKE2 confirmation shows
1.139x CPU/wall speedup, or 12.2% less API CPU time, on one selected training
workload. This is compiler headroom, not learned generalization. Its models fail
selection gates. That evidence remains unchanged and separate from this run.

See [INVOCATION_SL.md](INVOCATION_SL.md) for the preceding iteration: switching after
each library invocation, separate baseline/candidate placement controls, and
three newly added upstream libraries. The corpus has five training programs
(ten workloads) and xxHash as an entire-program development holdout. All ten
training workloads pass unchanged controls; 34 distinct candidate outcomes
qualify. All eight supervised models have scorable program-held-out validation,
but none passes the gain gates. O2 has about 3% measured speedup on one Expat
training input; its separate-process confirmation misses the declared 3% floor.
No unseen-program learned gain is established. Default remains O3. 81 unit tests
and 60 independent O0/candidate correctness comparisons pass.

See [PAIRED_SL.md](PAIRED_SL.md) for the preceding iteration: persistent native paired
measurements, CPU-service-time SL with independent wall confirmation, and eight
LLVM19 settings. All 22 training and six development kernels pass correctness.
Partial training retains eight distinct qualified candidate outcomes; a training
kernel shows 1.169x speedup over native O3. Development controls admit only one
program, where the frozen diagnostic model chooses O3. No new unseen-program SL
gain is established; default remains O3. Its 72-test result is preserved.

See [RESEARCH_SL.md](RESEARCH_SL.md) for the preceding corpus/research iteration:
pinned 30-kernel PolyBench, explicit input repairs and scheduler diagnostics.
Its separate failed timing study is preserved and contributes no runtime labels.

See [ROBUST_SL.md](ROBUST_SL.md) for the preceding iteration: pinned zlib, Expat and
Lua workloads, real-program model scoring, and 49 passing unit tests. New runtime
studies failed unchanged controls, so they supply no new training labels or gain
claim. The selected default remains O3.

See [TRANSFORM_SL.md](TRANSFORM_SL.md) for the earlier 2.72% experimental TIFF
development gain and its limits. It has not been reproduced in the current noisy
instance. Experimental policies require their documented confirmation and scope.

See [COMPACT_SL.md](COMPACT_SL.md) for the protocol, commands, results and scope.
Earlier architecture and constraints are in [NEUROCOMPILER_STATE.md](NEUROCOMPILER_STATE.md).

Activate the pinned cloud environment with
`source /workspace/.neurocompiler/activate.sh`. The new corpus uses a separate
private LLVM19 toolchain; the earlier LLVM10 environment is preserved.
Models and timing reports are local artifacts;
GitHub publishing is a separate action.
