# Live application verification — 22 October 2026

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
  five checked live analyses, to1e-10 numerical tolerance.
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
