# Real-program coverage and regression-aware SL

This iteration adds pinned upstream workloads, uncertainty-aware learners, and
an explicit check that refuses noisy runtime evidence. The default remains O3.
The previously confirmed 2.72% TIFF development gain remains an earlier
experimental result; this iteration must establish its own timing validity.

## Upstream workloads and correctness

Three actual upstream implementations are compiled into standalone native
drivers: zlib 1.3.1, Expat 2.7.3, and Lua 5.4.8. Each has two deterministic inputs.
These are library/interpreter workloads with custom drivers, not six independent
applications or a claim of disjoint implementation families. Versions, URLs,
archive SHA-256, compiled source/header hashes, drivers, inputs, initial LLVM
bitcode, final candidate bitcode and executables are preserved. Upstream
licenses are retained in the pinned archives.

Every candidate must match O3 byte for byte on stdout. Zlib additionally checks
compression/decompression and input equality internally; Expat and Lua must
successfully parse/execute their input. Python/system-library oracles independently
check each workload checksum. These checks occur outside timed measurements.
The LLVM 10 four-pipeline menu and native backend flags match the prior studies.

The six-input pilot uses the unchanged original 4-block, 10-pair, 3% protocol.
It rejected all six inputs on unchanged O3 controls before collecting any
candidate effects. `results/real_train.json` retains these failures.

A separate study was declared after the failure, with three fixed first inputs,
longer workloads (O3-only calibration targeting 250 ms), 20 pairs per block,
and unchanged 3% controls/gain floor. No candidate effects informed this change.
All three initial controls also failed. `results/real_train_long.json` retains
that result; no completed study was rerun until acceptance. Accepted real
training coverage therefore remains **seven original programs**, not ten.

Both wall and child-process CPU timing diagnostics were unstable. CPU placement
and fixed address layout did not resolve the observed variability. These
diagnostics are not candidate effects or training labels. The placement
diagnostic overlapped a short model-fit attempt on CPU 0, so its CPU-0 samples
are not isolated performance evidence. The precise platform cause remains
undetermined; the measured noise prevents runtime readiness under these protocols.

## Learning and regression management

`src/supervised/robust.py` compares point-target Ridge, lower-timing-bound Ridge,
and lower-bound Ridge with twice the loss weight for measured regressions.
Weights are normalized within each original program, so multiple inputs do not
increase that program's total weight. The lower-bound target and loss penalty
are predictive heuristics and provide no runtime guarantee.

Cross-validation holds out every input of an original real program together.
Synthetic kernels may supply auxiliary training rows, but **never contribute to
the held-out score or the number of real programs**. The fixed grid compares
real-only versus auxiliary-kernel fitting, three target/loss variants, Ridge
strengths 1 and 10, and decision floors 0% and 1%. Distinct studies namespace
their case identifiers while retaining the original-program group.

Deployment requires mean >1.01x, a positive program-bootstrap lower bound,
worst program >=1/1.03, worst input >=1/1.01, and confirmed gains on at least two
held-out original programs. No candidate passed, so the selected model is O3.
The experimental rank maximizes mean program log gain minus twice the mean
negative program log gain; it falls back to O3 if every utility is nonpositive.
An additional risk-aware experimental policy is frozen from that ranking among
the uncertainty-penalized variants. The previous learned policy is retained as
a fixed reference without refitting.

`models/sl_robust_long_bundle.joblib` contains:

- Default: O3.
- Experimental: `with_kernels_point_ridge1_floor0`, reproducing the prior
  development choices. CV score on real programs: 1.01616x, with a regression and only
  one confirmed held-program gain; it fails the deployment rule.
- Risk-aware experimental: `with_kernels_lower_risk_ridge10_floor0.01`.
  Real-program CV point score: 1.00223x, two non-O3 choices, no regressions in
  those held-program predictions, and zero confirmed gains. On the four eligible
  development inputs it abstains to O3, including both TIFF gains and JPEG risks.
- `previous_frozen`: the earlier immutable experimental model.

The earlier `sl_robust_bundle.joblib` is an immutable pilot model saved before the
longer timing study; use the `robust_long` bundle for the final iteration.
Accepted labels still comprise 39 candidate rows from seven real and six
synthetic programs. All failed new timings are excluded from fitting.

Model-grid ranking is adaptive on training CV. Menu and feature design reflect
prior development observations. Current development is fit-disjoint but already
observed, and JPEG/TIFF share implementation families with training. Reserved
susan/tiff2rgba/tiffmedian tests remain untouched. RL and hybrid are still future
work; this iteration does not establish suite-wide improvement over O3.

## Fresh development and verification

All model decisions are frozen before the new development study uses fresh
4-block, 40-pair timing with 1% controls and gain floor. A case contributes only
when its initial and selected-executable controls pass. Aggregate intervals
resample original programs and the paired timing blocks/pairs within each fixed
input, so timing uncertainty is included. Inputs do not become independent
programs. `scripts.evaluate_robust.verify_study()` checks frozen hashes,
fit/development disjointness, choices, complete timing coverage, positive
samples, and recomputes the reported results from raw records.

The final run and verification outcomes are recorded in
`results/robust_verification.json` and summarized in `NEUROCOMPILER_STATE.md`.
All four eligible development inputs failed the initial 1% controls. Consequently
there are zero accepted new effects, no aggregate speedup estimate, and no new
runtime improvement claim. The old 2.72% TIFF result has not been independently
reproduced in this noisy instance.

49 unit tests passed. Static features were re-extracted from 34 actual frozen
cases, and 36 native candidate/output checks passed the independent oracles.
Source-file default-O3 and bitcode-file risk-aware non-O3 inference match the
independently frozen bitcode and executable hashes. Corrupting a reported gain
was rejected. All generated artifacts in the prior snapshot were preserved.
Frozen prediction verification permits only tiny finite score round-off
(absolute 1e-14 / relative 1e-12) across numerical backends. Pipeline names,
hashes, protocols and reported runtime statistics remain exact. This fixes an
actual replay failure after CPU-affinity changes without changing any decision.

## Commands and saved work

Activate the existing pinned environment:

```bash
source /workspace/.neurocompiler/activate.sh
python -m scripts.fetch_real_sources
python -m scripts.collect_real --resume
python -m scripts.collect_real_long --resume
python -m scripts.evaluate_robust --resume
python -m scripts.check_timing --study results/real_train_long.json
python -m unittest tests.test_compact tests.test_transform tests.test_robust
```

`--resume` verifies a completed study without repeating native timing. The
readiness command intentionally exits 2 for the preserved failed-control study;
that is a diagnosed timing failure, not a successful runtime-readiness check.
Frozen training commands refuse to overwrite artifacts. On a new experiment,
allocate a new output identity and declare its scope and budget before effects;
do not erase these failures or silently widen their thresholds.

Static inference exports LLVM bitcode and an optional executable without running
the program:

```bash
python -m scripts.optimize_transform --input program.bc --output results/program.bc \
  --model models/sl_robust_long_bundle.joblib
python -m scripts.optimize_transform --input program.bc --output results/program_risk.bc \
  --model models/sl_robust_long_bundle.joblib --risk-aware
```

`--experimental` and `--risk-aware` are mutually exclusive. The risk-aware policy
is experimental, not an approved deployment model. Workload metadata uses
`--input-bytes` and `--iterations`; native link dependencies use `--link`.

`results/robust_iteration.zip` preserves code, models, reports, required inputs,
frozen bitcode/executables, pinned archives and a SHA-256 file manifest. On
restoration under `/workspace/NeuroCompiler`, run `scripts.fetch_real_sources`
to extract any missing upstream trees before verifying build-source hashes.
No new environment dependencies are required. Changes and artifacts are local;
no commit or GitHub push was performed.
