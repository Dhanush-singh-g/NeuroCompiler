# Persistent native pairs and CPU-service-time SL

This iteration changes the measurement architecture and the training objective.
SL learns **native CPU service time**, while **wall latency is measured and
qualified independently**. CPU demand is useful for reducing descheduling noise;
it does not guarantee a wall-time improvement. Default deployment remains O3.

The approach builds on the benchmarking and CompilerGym research discussed in
[RESEARCH_SL.md](RESEARCH_SL.md). It does not replace runtime with instruction
counts, remove interrupted samples, or reinterpret best-case timings as median
latency. Earlier frozen studies and models remain unchanged.

## Measurement design

- Each timing cell is one persistent process loading two scientific-kernel DSOs.
  Logical left/right executions alternate within that process. Every invocation
  allocates and initializes fresh inputs, runs the kernel, then consumes every
  live-out value. Initialization, hashing and process launch remain outside
  kernel timers. Two warmups per side precede recorded pairs.
- CLOCK_THREAD_CPUTIME_ID and CLOCK_MONOTONIC bracket the same kernel.
  Every raw pair and both clocks are retained. Scheduler steal increments span
  the whole worker process and are diagnostic, not a reason to delete a pair.
- A copied, byte-identical O3 DSO is loaded separately for the unchanged baseline
  control. This tests code-placement effects as well as scheduling variability.
  Candidate self-controls accompany every non-identical candidate comparison.
- The formal study is declared before candidate measurements: three blocks,
  24 pairs/cell, CPU2, O3-calibrated 40 ms CPU batches, and unchanged 3% control
  and confirmation gates. O3 invocations below 20 microseconds are ineligible
  because instrumentation overhead could be material. No retries until success.
- Qualification is per program and candidate. Failed controls are retained.
  Complete-menu acceptance remains the original study result. A separate,
  explicitly declared partial-label view admits each passing candidate only
  after its O3 control also passes. It keeps losses and leaves unqualified
  targets missing; it never substitutes zero for an unknown result.

These are warm, repeated PIC scientific-kernel measurements. They are distinct
from cold application startup or end-to-end application latency. CPU-frequency
changes and other contention can still affect CPU time; qualification remains
necessary. Native artifacts require compatible CPU features.

## Stronger baseline and candidate space

The baseline uses LLVM19.1.7 default O3 with `-march=native`, PIC, strict floating
point, and `-ffp-contract=off`. All candidates use identical native backend,
support, timers, inputs, and correctness criteria. The eight settings are:

| Setting | Change |
|---|---|
| O3 | Native target, standard O3 pipeline |
| O2 | Standard O2 pipeline |
| O3_no_vector | Disable loop and SLP vectorization |
| O3_no_unroll | Zero aggressive unroll budget; disable runtime unroll |
| O3_interchange | Enable LLVM's experimental loop-interchange pass |
| O3_interleave1 | Force vector interleave count one |
| O3_no_slp | Disable SLP vectorization |
| instcombine_O3 | Instruction combining before O3, with fixpoint verification |

Identical compiled DSOs reuse their baseline outcome. Every configuration must
match the prior full numeric output hash and an independently compiled O0
reference. A forced-vector-width prototype failed exact-output checking and
was rejected before the formal experiment; its diagnostics are preserved.
Numerical tolerances were not relaxed to admit that candidate.
Candidate self-controls load the same DSO twice and therefore share code
placement. They test temporal stability; unlike the separately copied O3
control, they do not independently certify candidate placement effects.

The three-program diagnostic pilot used correlation, gemm, and durbin, selected
across training families. Two passed both CPU and wall controls under its smaller
budget. Pilot timings are excluded from training. The separately frozen formal
study increases batching/sample count and adds loop interchange; it is not a
repeat of an identical protocol until a favorable result appears.

## Learning and frozen evaluation

The new independent bundle uses 160 static features: 153 function/CFG/transform
features and seven candidate indicators. Ridge point/lower-bound models weigh
regressions more heavily, with equal total weight per original program. Whole
families are held out in CV. Defaults for the old LLVM19 learner remain compatible;
the new menu is supplied explicitly instead of silently changing old models.

The complete-menu study admits four kernels, all from one family. After the
training study, `paired_partial_declaration.json` freezes a method revision:
admit qualified candidate measurements individually and require every selected
CV prediction to have a qualified outcome. The original raw study is unchanged.
Partial training contains 19 programs and 109 nonbaseline configuration labels,
but **101 are byte-identical O3 aliases**. Only **eight are distinct measured
candidate outcomes across seven programs**. This is sparse information, not
109 independent optimization measurements. Negative qualified targets remain.

All eight point/lower-bound Ridge/floor variants have missing selected CV targets.
Their CV scores are withheld and none is selected. The original new selection
artifact therefore contains no learner. `paired_preset_declaration.json` then
declares a separate fixed lower-bound Ridge model (alpha10, floor3%) after
training inspection and before development. This is a diagnostic hypothesis,
**not CV-certified selection or deployment validation**. It is saved separately
as `sl_paired_native_preset_20261011_bundle.joblib`; default remains O3.

The fixed model is frozen before the stencil development split is built and
timed. Development measures its frozen choice and O3, rather than searching the
full menu for a development winner. CPU and wall scores qualify independently.
Training oracles describe search headroom, not learned or unseen-program results.

## Training evidence

All 22 training kernels pass finite, full-output equivalence for all eight
pipelines. There are 36 distinct non-O3 alternatives over the corpus; three
settings generate identical O3 binaries throughout. O3 CPU controls pass for
19 programs. Of these, 32 distinct candidates are timed and eight pass their
own CPU controls. Only 2mm, gemm, syrk and trmm have fully qualified menus.
The study retains 258 cells / 6,192 pairs / 12,384 timed kernel batches,
including failed controls. Pilot and warmup executions are separate.

The adapted-input **training** kernel ludcmp has qualified headroom:

| Candidate | CPU speedup vs O3 | Paired interval | Wall speedup |
|---|---:|---:|---:|
| O2 | 1.15980x | 1.06005–1.18779x | 1.15989x |
| instcombine before O3 | 1.16926x | 1.13312–1.20613x | 1.17030x |

Both have passing baseline and candidate controls on both clocks and all three
effect blocks exceed the 3% floor. The second corresponds to **14.48% lower
kernel CPU time**, with wall time 14.55% lower. This is conditional evidence from
one small scientific kernel with adapted initialization and multiple candidates
searched; it does not establish broad learned improvement or end-to-end speedup.
The failed no-vector control for this kernel is excluded despite a positive
point estimate. Other qualified candidates include losses and small gains below
the confirmation floor. The headroom has not been independently replicated.

## Frozen development evidence

All six stencil kernels pass correctness. The frozen diagnostic model chooses
no-vector for adi and jacobi-1d-imper, and O3 for the other four. The 1D Jacobi
kernel is below the declared minimum duration and is excluded from timing.
Of the five eligible kernels, only seidel-2d passes O3 CPU and wall controls.
The other four failures are retained. In particular, adi lacks a qualified
baseline, so its predicted non-O3 choice is not timed or scored.

The sole qualified policy choice is therefore unchanged O3: conditional CPU
and wall scores are 1.000x, with zero changes and zero confirmed gains. The
one-program bootstrap [1,1] simply describes that unchanged choice; it supplies
no evidence of generalization or suite-wide certainty. **No new learned
improvement is established**, and no failed control is retried until success.
The development study retains 15 cells / 360 pairs / 720 timed kernel batches.

The new target and worker yield useful training measurements, but a stable
runner remains necessary for broader performance validation. Next work should
collect broader real-program labels and measure new frozen predictions on a
runner that passes unchanged controls, before attempting RL or hybrid search.

Only the 22 training and six development kernels are available. The two medley
kernels and original cBench final tests remain reserved. Scientific kernels do
not count as real applications. These results do not establish RL or hybrid
performance, application-domain generalization, or project completion.

## Reproduce or inspect

72 unit tests and 224 independent native O0/candidate comparisons pass. Integrity
checks reject changed pair order, invented gains and altered static features.
1,525 earlier generated artifacts match the previous archive. Its completion
log was empty when archived and populated afterward; the exception is recorded
and its exact count/size/hash verified against the actual archive. No prior
measurement, model, archive or completion log is modified.

Default and experimental adi exports match the original bitcode/DSOs and full
numeric outputs. The experimental manifest records unqualified performance and
uncertified CV status. Export checks establish correctness, not a speedup.
`results/paired_iteration.zip` preserves source, evidence and the preceding ZIP
with per-file SHA-256 verification. `snapshot_paired.py` excludes its own
completion log to avoid the prior self-referential logging issue.

```bash
source /workspace/.neurocompiler/activate.sh
python -m unittest tests.test_compact tests.test_transform tests.test_robust tests.test_polybench tests.test_paired
python scripts/collect_paired.py --resume  # verifies completed study without new timings
python scripts/collect_paired.py --split development --resume
python scripts/evaluate_paired.py
python scripts/optimize_paired.py --case adi --output results/paired_export
python scripts/optimize_paired.py --case adi --experimental --output results/paired_export_experimental
```

The frozen model was produced with `python scripts/train_paired.py --policy-name
paired_native_preset_20261011 --fixed-preset` and development collection with
`python scripts/collect_paired.py --split development --policy-name
paired_native_preset_20261011`. Training refuses to overwrite frozen artifacts.
Another experiment needs a fresh `--name` and matching, separately versioned
training declarations, supplied with `--partial-declaration` and (for a fixed
diagnostic) `--preset-declaration`. Their schemas are the retained declarations;
bind the new training SHA and policy name before fitting. Preserve old reports.
Collect timings sequentially without concurrent builds. A new host
must rebuild native-target artifacts and qualify controls. No new package
install is required; private LLVM19 and the Python environment are reused.

Collection-source copies and declarations, candidate bitcode/DSOs, calibrated
repetitions, paired raw clocks, controls, model provenance, frozen predictions,
and verification evidence are retained. All changes remain local; no commit
or GitHub push was performed.
