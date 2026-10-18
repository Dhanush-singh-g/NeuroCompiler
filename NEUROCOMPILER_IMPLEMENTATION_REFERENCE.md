# NeuroCompiler — Implementation Reference and Project History

Prepared: 18 October 2026

Implementation and experiment scope: work published through 14 October 2026

Repository: Dhanush-singh-g/NeuroCompiler

## Purpose and reading scope

This is a standalone implementation reference for a collaborator who will not read the source code. It explains the implemented components, the information passed between them, the experimental decisions, the results, and the unresolved issues. File names identify where a component lives; understanding this document does not depend on opening those files.

The account is based on the retained implementation and experiment records. It is not a new line-by-line audit of the repository. A workspace startup failure temporarily delayed preparation on 18 October; the workspace subsequently became available and this document was saved. No new performance experiment or model training was performed while preparing this reference.

## 1. Actual project status

NeuroCompiler is a research prototype for selecting LLVM compiler settings using supervised learning. It is not a completed reinforcement-learning compiler or a production compilation service.

Working components include compilation, benchmark registration, independent correctness checks, static features, native measurement workers, statistical qualification, supervised fitting, grouped validation, default-policy handling, evidence audits, a portable source runner, and a recorded-results dashboard.

The research objective remains unresolved: the latest studies have not established a qualified learned improvement over LLVM O3 on unseen implementations.

A preselected BLAKE2 training workload showed about 12.1% less API CPU time under a no-vectorization setting. This is a measured opportunity in the candidate space, not a result achieved by a generalizing learned selector.

The operational default is O3. RL and an SL/RL hybrid remain future work.

## 2. What the compiler selector is intended to learn

LLVM O3 is a collection of optimization passes and heuristics. It is a strong default, but it does not guarantee the fastest execution for every implementation, input, processor, and compiler version.

NeuroCompiler tests a finite menu of alternatives. The supervised component uses static information about the implementation, input, and candidate setting to estimate whether an alternative is beneficial. LLVM still performs optimization and machine-code generation.

The implemented approach does not generate machine code with an LLM or perform unrestricted LLVM pass-order discovery. Its learned components include Ridge regression and random forests. The project name is not evidence of a completed deep neural compiler.

Success requires more than identifying an attractive setting after measuring a program. A policy must be fitted and selected without using its fresh evaluation outcomes, then make useful decisions on implementations withheld from fitting and selection.

## 3. Two generations of compiler infrastructure

The earlier implementation uses CompilerGym with LLVM10. It provides the original environment integration, baseline handling, dataset-generation scripts, supervised training, and source/bitcode optimization interface.

The later studies use LLVM19 and registered native library workloads. They add independent API drivers, source pinning, shared-library artifacts, controlled execution workers, timed-region features, stronger statistical controls, and separately versioned experiments.

These are related research stages, but their timing labels are not interchangeable. A process-level measurement from an earlier compiler context is not silently added to a later warm-API CPU-time dataset.

Implementation references: src/benchmarks/compiler_gym_env.py, src/benchmarks/baselines.py, src/benchmarks/runtime.py, src/benchmarks/paired_runtime.py, and the versioned native benchmark modules.

## 4. End-to-end implementation flow

The intended workflow has ten stages.

1. Register a source implementation and its input fixtures.
2. Retrieve and materialize pinned upstream sources.
3. Build the baseline, reference, and candidate artifacts.
4. Extract candidate-specific static features.
5. Check correctness against independent expectations.
6. Freeze sources, artifacts, inputs, splits, and the measurement protocol.
7. Admit and independently confirm a suitable execution target.
8. Collect candidate comparisons and retain only qualified labels.
9. Fit and validate candidate selectors by original implementation.
10. Freeze a selected policy before fresh development execution.

Every stage has a different responsibility. Successful compilation does not imply correctness. Correctness does not imply stable timing. Stable timing does not imply a useful predictor. A trained predictor does not imply generalization.

The expanded experiment stopped at target admission. It therefore did not collect new training labels, fit its expanded selector, or execute its fresh development implementations.

Implementation reference: scripts/expanded_study.py.

## 5. Source pinning and workload registration

A registered workload connects an upstream implementation to a controlled experiment. Its registration identifies the archive, source recipe, C driver, input fixture, expected output, compiler candidates, and measurement metadata.

Source archives have SHA256 checksums. Newly added GitHub sources are also pinned to exact commits. Retaining the archives avoids dependence on later changes to upstream branches. Licenses and source provenance are retained with them.

The new sources include json-parser, json.h, Frozen, miniz, libdeflate, FastLZ, MPack, and yxml. The yxml source is explicitly identified as a JulStrat mirror rather than described as the authoritative upstream repository.

The build materializer applies path restrictions and controls the treatment of archive links. A source archive is not extracted blindly into arbitrary filesystem locations.

Implementation references: src/benchmarks/expanded.py and results/expanded_source_pins.json.

## 6. Latest corpus and independence rules

The expanded prepared corpus has 21 original training implementations and two correctness fixtures per implementation, giving 42 training inputs.

The formal performance study preselects one input per training implementation, giving 21 formal training inputs if the target is admitted. Both fixtures still receive correctness checks.

The training implementations are:

| Area | Implementations |
| --- | --- |
| Compression | zlib, LZ4, BZip2, miniz, FastLZ |
| Cryptography and hashing | BLAKE2 reference, B-Con SHA256, Monocypher |
| JSON and serialization | jsmn, cJSON, Parson, yyjson, json-parser, Frozen, MPack |
| XML, configuration and protocol parsing | Expat, yxml, inih, picohttpparser |
| Interpreter and expression evaluation | Lua, TinyExpr |

Two additional implementations are reserved for fresh development: sheredom/json.h and libdeflate. Their four fixtures are pinned but were not built or executed in the expanded study.

This gives 23 pinned implementations including development, not 46 independent programs. Input variants remain grouped by their original implementation. Sharing an algorithm family between training and development is allowed; unseen-implementation evaluation is not the same as unseen-algorithm-family evaluation.

Monocypher and yyjson were opened during a previous development study. They were explicitly moved into training. They are not fresh holdouts in the expanded study, and their earlier timings were not pooled into its labels.

## 7. Compilation implementation

The expanded build produces an O0 correctness reference and four named compiler settings: O3, O2, O3 with vectorization disabled, and O3 with a larger-inline configuration.

Only O3, O2, and no-vectorization are active recommendation choices in the expanded study. Large-inline is built for correctness and features but excluded from recommendations. Earlier studies used different menus.

The build first creates initial LLVM IR with frontend optimization passes controlled explicitly. It then applies the declared candidate pipeline and produces position-independent native shared libraries. The expanded workflow records strict floating-point behavior, disables contraction, and records CPU-specific code generation.

Tool versions, executable hashes, source hashes, initial IR hashes, and artifact hashes connect the result to its compilation context. Symbol binding is controlled in the native shared-library workflow to reduce unintended interaction between implementations.

Some candidate settings produce equivalent artifacts for a particular implementation. Such aliases are not counted as independent useful transformations. Candidate names, compiled alternatives, and eligible training targets are different counts.

Because native CPU features are used, the output is not a portable executable for every machine. A changed CPU may require new builds and always requires appropriately declared performance evaluation.

Implementation references: src/benchmarks/expanded.py and the earlier build support in src/benchmarks/region.py, invocation.py, and broad.py.

## 8. Driver and oracle implementation

A driver adapts each upstream library to the benchmark interface. It prepares or receives the declared input, runs the relevant library operation, and provides results that can be checked independently.

The correctness system does not simply compare whether two executables exited successfully. It checks declared results against independent expectations.

JSON fixtures use semantic reconstruction rather than relying only on textual formatting. MessagePack fixtures use specification-based expectations. XML fixtures use expectations derived using Python ElementTree.

Compression fixtures require exact recovery of the original plaintext. The system uses independent system zlib and LZ4 decoding where applicable and an independent Python FastLZ level-1 decoder. Different correct compressed streams can therefore pass if they reconstruct the same original input.

Checksums and result counts make outputs observable and help detect incorrect or absent computation.

The expanded study records 168 correctness cells: 42 inputs across four settings. Each cell contains two O0/candidate pairs, giving 336 pairs. Forty native compression streams are independently reconstructed across reference and candidate artifacts.

These are fixture-level checks, not a formal proof for every possible input accepted by each library.

Implementation references: src/benchmarks/expanded_drivers.py and tests/test_expanded.py.

## 9. Manifest and measurement record design

A per-input manifest is the connection between the source implementation, fixture, compiler artifacts, and validation. It records the program identity, input identity and hash, source pin, source hashes, initial IR, artifact paths and hashes, aliases, candidate features, expected output, repetitions, correctness evidence, interoperability checks, calibration, and eligibility.

A measurement record identifies the case, method, block, role, baseline and candidate choices, repetition count, worker process identities, recorded entry addresses, and samples.

Samples retain actual execution order, CPU and wall aggregates for both sides, checksums, result counts, and invocation traces. The system can therefore inspect more than a final speedup number.

Clock summaries record a speed ratio, log-speedup, interval, block ratios, starting-order differences, and qualification decisions. Candidate summaries distinguish qualification from confirmed gain.

Model-selection records bind the model to its training evidence, record the default and experimental policies, identify the fixed model comparisons, and retain qualification and protocol information.

These records support traceability. A result is not just a number detached from its source, compiler, input, and protocol.

## 10. Native worker implementation

The execution design evolved from earlier process timing through paired execution, per-invocation alternation, separate-process comparisons, and persistent isolated workers.

In the later persistent design, the parent coordinates children that load one implementation each after fork. The parent loads neither implementation. Initial untimed invocations warm up the workload.

The worker uses equal, even repetition counts and alternates actual starting sides. CPU service time and wall time are retained independently. Output checksums remain part of the recorded result. Aggregate timing is checked against invocation traces.

Process identity and code placement checks are interpreted according to the worker design. Separate processes can legitimately map functions at the same virtual address. An address condition intended for two co-resident copies must not be applied blindly to isolated children.

The purpose of isolation is to reduce particular measurement concerns. It is not a guarantee against all cache, frequency, contention, or scheduling effects.

Implementation references: src/benchmarks/persistent_library_worker.c, persistent.py, isolated_library_worker.c, invocation_worker.c, and paired_worker.c.

## 11. Performance objective and timing units

The latest objective is warm native library API CPU time, with independent wall confirmation. Startup and client input/output are excluded from the intended timed region.

The speed ratio is baseline time divided by candidate time. A ratio above one indicates less candidate time. Time reduction is one minus the reciprocal of the ratio, expressed as a percentage.

A ratio near 1.137 corresponds to approximately 12.1% less time. It does not mean 13.7% less time.

CPU time reduces sensitivity to some forms of descheduling, but it still reflects processor frequency, cache behavior, and contention. Wall time captures additional elapsed-time effects. Neither clock alone certifies a stable experiment.

The latest calibration targets 200 milliseconds of API CPU service per side per pair. This is a service-time target, not a claim that the whole subprocess or user application lasts 200 milliseconds.

## 12. Identical-policy controls and starting-order qualification

An identical-O3 control compares equivalent optimization settings. Its expected ratio is near one. A substantial difference warns that the measurement system can create apparent improvements without a compiler change.

The expanded multiplicative tolerance permits ratios between one divided by 1.03 and 1.03, approximately 0.97087 to 1.03.

Qualification checks block ratios, interval bounds, pooled starting-side behavior, and starting-side behavior in every block.

For order checks, the recorded left/right time ratio is interpreted according to which side actually started first. Differences between these groups are checked within blocks and after pooling. A simple even/odd grouping is not assumed to be an adequate substitute.

Candidate effects are role-specific. A genuine improvement outside the identical-policy tolerance is not expected to pass as a null control. It instead needs qualified baseline and candidate self-controls, acceptable effect-order behavior, and the declared gain criteria.

This explains why a shared statistics record can show a false null-control flag for a genuine effect while still recording the effect as qualified and confirmed. The role and surrounding controls matter.

Implementation reference: the clock-effect and qualification logic in src/benchmarks/region.py.

## 13. Expanded admission and its actual result

The expanded protocol uses three blocks of 24 matched pairs, O3-only calibration, equal even repetitions, three initial untimed invocations, independent CPU/wall checks, recorded intervals, starting-order checks, and a fixed three-percent tolerance.

The cohort contains zlib random, Expat nested, LZ4 random, json-parser nested, miniz random, and MPack nested.

All six must qualify on both clocks. One independent confirmation then follows. Failure blocks downstream collection and fitting.

| Logical CPU | CPU controls passed | Wall controls passed | Admitted |
| --- | ---: | ---: | --- |
| 2 | 4/6 | 4/6 | No |
| 1 | 5/6 | 5/6 | No |
| 3 | 3/6 | 2/6 | No |
| 4 | 1/6 | 1/6 | No |
| 0 | 3/6 | 3/6 | No |

The retained admission screen contains 90 cells and 2,160 pairs. One Expat identical-O3 block was approximately 0.9014 despite no optimization change.

No target qualified. Conditional confirmation records contain no selected target and zero native confirmation cells.

This is a failure of the declared admission requirement. It does not prove every individual program is unmeasurable, that all cloud targets fail, or that improving over O3 is impossible. It also does not justify lowering the requirement after observing five passing controls on one CPU.

## 14. Candidate effects and label eligibility

A baseline control must qualify before its corresponding candidate outcomes can be treated as useful learning evidence. A candidate additionally needs appropriate self-controls and effect-order qualification.

A confirmed gain needs the declared interval lower bound and every effect block above the 1.03 gain floor, with the required clock checks.

All observations remain in the evidence. The project does not manufacture qualification by selecting minimum timings, deleting inconvenient samples, substituting missing outcomes, or retrying until a control passes.

A source implementation, input fixture, raw pair, candidate outcome, and qualified label are different units. More fixtures or more raw samples do not automatically produce more independent useful learning examples.

The expanded corpus added sources and correctness coverage but zero new qualified training labels because target admission failed.

## 15. Feature representation implementation

The later representation attempts to describe the API work being measured. It examines control-flow graphs and reachable direct callees rather than assigning equal importance to all source code.

The recorded expanded representation has 95 fields: 88 timed-region fields, three candidate-choice indicators, and four input descriptors.

The representation includes candidate-specific changes and uncertainty or incomplete visibility. It is static analysis, not a dynamic profile.

Indirect calls, external functions, and mixed preparation/verification paths limit visibility. Static instruction counts are not dynamic execution frequencies. The usefulness of the representation remains an empirical question.

Implementation references: src/features/timed_region.py, src/features/transform.py, and the supervised region/expanded modules.

## 16. Supervised model fitting and decision behavior

The implemented comparisons include Ridge regression and random forests. The later workflow estimates candidate log-benefit relative to O3 and applies declared selection behavior, including uncertainty/regression penalties and fallback handling.

The precise numeric configuration is study-specific. The implementation should not be described as simply choosing the largest unconstrained prediction.

Training uses qualified candidate outcomes. Equivalent aliases and unavailable measurements do not become artificial independent rows.

Validation groups by original implementation. Input variants of the same implementation stay together. Program weighting prevents an implementation with more recorded rows from dominating merely because of that row count.

A held-program prediction cannot be evaluated using the model's prediction as truth. If the selected candidate has no qualified measured outcome, its evaluation is unscorable.

The conservative outcome can be O3. Always choosing O3 is operationally acceptable, but does not establish positive learned utility.

Implementation references: src/supervised/region.py, src/supervised/expanded.py, scripts/train_persistent.py, and the earlier versioned selectors.

## 17. Completed supervised result versus blocked expanded result

The preceding persistent study actually performed 16 fixed model comparisons with 128 program-level cross-validation fits.

Eight forest variants were fully scorable but chose O3 everywhere. Eight Ridge variants lacked qualified outcomes for some selected held-program candidates and were unscorable. No model passed selection.

The study measured 23 distinct candidate targets and retained 11 qualified targets across six original implementations. It also had 11 baseline-qualified inputs; that equal number describes a different unit.

The expanded study has downstream fitting code, but never reached it. It is incorrect to report expanded training accuracy, a fitted expanded selector, or fresh development performance.

An exported model bundle is not proof that a useful learned policy exists. Some bundles explicitly contain no qualified experimental selector and retain an O3 default.

## 18. The BLAKE2 headroom result

A separately declared preselected training probe compared the no-vectorization setting with O3.

The recorded CPU ratio was approximately 1.137116, with an interval of approximately 1.127040 to 1.145032. The wall ratio was approximately 1.137155. The CPU-time reduction was approximately 12.1%.

Baseline and candidate controls and effect-order checks qualified for the probe. It was excluded from fitting and retuning.

In the separate primary supervised study, BLAKE2 baseline controls failed. The successful probe cannot repair those labels.

The result demonstrates case-specific compiler headroom in the tested context. It does not demonstrate learned generalization, whole-application acceleration, or cross-machine replication.

## 19. Experiment history and why the design changed

### Original implementation

The initial system established CompilerGym integration, baseline measurement, features, dataset generation, supervised fitting, and an optimization interface. It provided the foundation rather than proof of useful generalization.

### Compact and transformation studies

These established finite candidate menus, comparators, transformation representations, selectors, and retained experiment records. An earlier TIFF development result around 2.72% was not reproduced in the later noisy context and is not a newly confirmed general gain.

### Robust real-library study

Real-library workloads and stronger reliability checks were added. Unchanged controls failed, so those clocks did not become valid labels. O3 remained the default.

### Research and PolyBench work

Literature consultation, a pinned 30-kernel corpus, fixture repairs, and scheduling diagnostics expanded the research infrastructure. A later paired scientific study used 22 training and six development kernels. These kernels are not pooled with the latest library corpus.

### Paired study

Persistent paired measurements and CPU-service-time evaluation were added. Only eight distinct candidate outcomes qualified. A selected ludcmp training result near 1.169 showed headroom, but not unseen learned improvement.

### Invocation study

Per-invocation alternation was used with five training implementations and ten inputs, plus xxHash development inputs. Thirty-four candidate outcomes qualified under that method. All eight model variants were scorable but failed the gain requirements. A promising Expat O2 effect missed the independent confirmation floor.

### Broad study

The corpus grew to ten training implementations and twenty inputs, with two fresh development implementations, seven settings, and sixteen model comparisons. The primary method qualified 67 of 78 outcomes. A stronger actual-order diagnostic flagged some of them, exposing a weakness in the earlier grouping method. Original primary records were retained. Selected BLAKE2 headroom was confirmed near 1.139, but no learned selector qualified.

### Region study

Timed-region features, stronger actual-side checks, and isolated loading were added. Thirteen training implementations and 26 inputs produced 192 cells and 4,608 pairs. Only seven baseline controls passed each clock. Nineteen candidate targets were measured, but candidate controls failed and no fit targets remained. Sixteen eligibility decisions are not sixteen trained models.

### Persistent study

A declared method pilot compared fresh, batch, and micro-interleaved execution. Micro-interleaving qualified seven of eight inputs on both clocks in the pilot and confirmation under that study's rule. A separate primary study retained 216 cells, 5,184 pairs, and 11 qualified candidate targets. It recorded zero primary confirmed gains. All sixteen configurations were evaluated; none qualified. Repeated development chose O3, with only one of four inputs supplying qualified CPU/wall scores.

### Expanded study

The corpus grew to 21 training implementations and 42 correctness inputs, with fresh sources, longer batches, a portable source runner, and bounded all-core screening. Correctness passed, but no target passed admission. There were no new expanded labels or model fits.

The studies changed workload scope, menus, clocks, worker design, features, and qualification. Their numbers cannot be combined as one homogeneous dataset or interpreted as repeated successful training runs.

## 20. Defects and limitations encountered

| Problem | Implementation response | Remaining interpretation |
| --- | --- | --- |
| Old dependency compatibility | Private compatibility libraries, explicit tool paths and pinned packages | Research setup remains separate from frontend viewing |
| Source or fixture defects | Correct before formal measurement and retain failures | Fixture correctness is not universal semantic proof |
| Compression stream differences | Compare independently reconstructed plaintext | Different compressed bytes are not automatically incorrect |
| Frozen SAX array/key confusion | Track container type and add native regression | Fixed before formal freeze |
| Co-resident placement effects | Explore isolated processes and one-library-per-child execution | Isolation does not guarantee stability |
| Actual starting-order effects | Check pooled and every-block actual-side behavior | Stronger checks reject some earlier attractive outcomes |
| CPU versus wall variability | Qualify both independently | Neither clock alone solves all machine effects |
| Sparse candidate coverage | Preserve failures and reject invented missing outcomes | More data collection is useful only if qualified |
| Development reuse | Explicitly open prior holdouts and reserve fresh implementations | Reused development cannot be called fresh |
| Audit exception mismatch | Recognize intended rejection for ragged corrupt data | Audit correction did not change primary outcomes |
| Inherited pilot wording | Add hash-bound pre-fit clarification | Numeric protocol and decisions remain unchanged |
| Incomplete operational helper binding | Audit actual context and document the limitation | Strengthen future protocol rather than editing old evidence |
| Fresh-clone exporter behavior | Serve the committed snapshot directly | Raw records are required only for intentional refresh |
| Large archive storage | Separate checked archive branch from main | Main-only cloning avoids optional large downloads |
| Release upload authentication | Use the working Git publication route | The release links the archive branch |
| Managed browser file restrictions | Verify HTTP serving | Direct local-file opening remains unverified here |
| Overconfident schedules and percentages | Record an inconclusive outcome and remove guarantees | No fixed iteration count establishes research success |

Scheduler-steal observations are diagnostic associations, not proof of the sole cause of every failure.

## 21. Evidence integrity implementation

Sources, inputs, artifacts, tools, splits, and protocol details are connected using hashes and declarations. Collector source copies are retained so a later changed script cannot silently redefine an old study.

Raw samples, failed controls, negative outcomes, and audit failures are kept rather than discarded.

Auditors check combinations of independent correctness, source materialization, artifact identity, trace reconciliation, order calculations, cross-validation replay, corruption rejection, preservation of earlier evidence, and downstream guards.

A completed resume verifies/reuses existing completed evidence without resampling. One-shot declarations and models refuse overwrites. Preparation repair addresses diagnosed pre-freeze build/correctness defects; it is not a performance retry mechanism.

A checksum establishes identity. It does not by itself establish that an experimental method is adequate. Provenance and measurement validity remain separate responsibilities.

Implementation references: scripts/audit_expanded.py, audit_expanded_targets.py, audit_persistent.py, and the versioned verification tools.

## 22. Frontend implementation

The frontend uses static HTML, CSS, vanilla JavaScript, and a Python standard-library HTTP server. It is not a React service and has no browser source-compilation or live model-execution endpoint.

The overview displays corpus coverage, baseline-control stability, study stages, default policy, and explicitly training-only BLAKE2 headroom.

The benchmark explorer searches implementations and inputs, filters training versus development, switches recorded compiler-setting evidence, and shows source pins.

The measurement view displays the five-CPU matrix with CPU/wall switching, intervals, block values, and failure explanations.

Source hashes, report downloads, JSON export, missing-data states, keyboard dialog behavior, and responsive layouts are implemented.

Changing a compiler setting in the UI changes the record displayed. It does not execute that compiler setting.

## 23. Frontend data and server behavior

The exporter reads a fixed set of preserved studies and creates a compact snapshot. It interprets complete recorded correctness pairs, checks certain declaration hashes, and checks recorded control summaries. It does not rebuild libraries or independently recompute all scientific statistics in the browser.

Missing and invalid data remain unavailable. They do not become passing controls, invented demonstrations, zero-gain measurements, or successful policy results.

The committed JSON and bundled JavaScript allow the dashboard to start without raw research downloads. An intentional data refresh needs the underlying records.

The server binds to loopback by default and serves an explicit asset/report allowlist. It rejects unrelated paths, checks resolved containment, and applies caching/content-type/security headers. It does not expose the whole repository or provide a production multi-user authentication system.

Recorded browser checks cover desktop/mobile layout, search, setting selection, empty results, reserved development, both clocks, control details, provenance, keyboard dismissal, actual JSON export, and missing snapshots.

Implementation references: scripts/build_dashboard.py, scripts/serve_dashboard.py, dashboard/app.js, dashboard/data.json, and dashboard/results.js.

## 24. Publication and archive implementation

The October 14 main publication contains source, tests, reports, fourteen model bundles, and the recorded frontend. The main commit is 97b1717593ce1d3372461e5e1529e8b7959e97c2.

Large generated files are on research-archive-2026-10-14, at commit 05b320b871ab9fb83324c397afc7652cfe234992. A release page links this archive.

The generated workspace preserves 6,529 files and 2,995,330,244 extracted bytes. Its joined gzip is 1,937,023,187 bytes, stored in 58 ordered parts. Per-part, full-archive, and per-file checksums are retained.

The package includes data, models, raw evidence, binaries, logs, upstream sources/licenses, and original experiment ZIP snapshots. Git metadata, virtual environments, and Python caches are omitted.

The packaging helper rejects external or nonfile symlinks and materializes internal file links while recording their original targets.

The join helper checks every part and the final archive before accepting its output. It refuses existing output or temporary files and removes its own failed partial output.

The restore helper checks the archive hash, member types, paths, file coverage and hashes, and existing-file conflicts before restoration. It refuses destructive replacement, preserves ordinary executable bits, and never executes artifacts or unpickles models.

Artifact restoration does not reproduce the original live machine's performance conditions.

Implementation references: scripts/package_research_workspace.py, scripts/join_research_archive.py, scripts/restore_research_workspace.py, and RESEARCH_ARCHIVE.json.

## 25. Validation history

The expanded iteration reported 123 passing tests. Frontend work added ten dashboard tests.

Publication validation ran a selected 137-test research/dashboard/archive suite that included four initial archive tests. An internal-link regression and two archive-reassembly regressions were added and passed afterward. The final archive module contains seven tests.

These checks cover implementation behavior, oracles, leakage safeguards, malformed records, corruption, server restrictions, and restoration behavior. They do not establish learned runtime improvement.

The published dashboard was also smoke-tested from a fresh GitHub main clone without raw data or a build step.

Scientific tests require their documented dependencies and, for some tests, the appropriate native toolchain. Browser checks have optional browser-automation dependencies.

## 26. How to operate the existing application

Viewing the dashboard requires Python 3.10 or newer and the main source checkout or main ZIP. It does not require Linux, LLVM, CompilerGym, a GPU, or the optional large archive.

Start the supplied dashboard server from the project folder and open its local address on the same computer. Keep its terminal running while using the application. The complete platform-specific procedure is in START_HERE.md.

Do not run the exporter as an ordinary installation step. The snapshot is already committed. Without restored research records, an intentional refresh correctly makes affected sections unavailable.

Running compiler experiments is a separate operation. It requires the documented Linux/toolchain environment, inputs and sources, a fresh context, and successful admission before downstream work.

Restoring the optional archive requires substantial disk space for Git's archive checkout, the joined archive, and extracted files—roughly nine gigabytes in total.

## 27. Scientific execution order and stopping rules

Preparation builds and validates fixtures. Declaration freezes the context and protocol. Admission measures identical-policy controls. Confirmation independently checks an admitted target. Training collection measures declared candidate outcomes. Fitting selects among the fixed model configurations. Development executes only after the required model freeze. Evaluation and verification reconstruct the recorded result.

Each stage is conditional. The presence of an action in the command interface does not prove the action executed in the expanded study.

The latest run must not be resumed repeatedly to obtain new controls after failure. A changed experiment needs an appropriately versioned context and declaration.

The expanded downstream path has not been exercised end-to-end on an admitted target. Prior supervised fitting was exercised in the preceding studies.

## 28. Current unresolved engineering concerns

The versioned scripts preserve evidence but are not yet a polished general experiment-management interface. Historical configurations and descriptions require care.

Future protocols should strengthen all operational context bindings. New native contexts need fresh compilation and admission. Expanded fitting and fresh development still need a qualified execution target.

Feature visibility remains incomplete for indirect/external behavior. Candidate profitability across independent implementations remains limited. Broader evaluation is needed before making broad generalization claims.

A live compilation frontend, production authentication, arbitrary user workload onboarding, and deployment as a compiler service are separate engineering projects, not existing dashboard features.

## 29. Workspace incident during documentation

On 18 October, the selected cloud workspace initially failed during provisioning and reported executor configuration/readiness errors. Shell execution and file creation were temporarily unavailable. After the workspace became available, this implementation reference was saved.

This is a current infrastructure failure, not a newly observed defect in the compiler implementation. No new compiler run, model fit, or performance evaluation occurred in that failed session.

It does not erase the published source or invalidate the earlier fresh-clone dashboard smoke test. This document remains a reference based on published implementation records, rather than a claim of a newly completed checkout audit.

## 30. Research work required next

A useful next cycle needs a meaningfully changed execution target and a fresh declared context. A suitable isolated cloud target can suffice; personal Linux hardware is not mandatory.

Sources should be rebuilt as required, then admission and independent confirmation should run. Failure should be preserved as failure.

If admitted, collect new expanded candidate outcomes, inspect qualified positive/negative coverage, fit the declared models with original-program grouping, and freeze a qualified selector before fresh development execution.

If no model qualifies, report that outcome and retain O3. If a model qualifies, evaluate it without retuning on its development outcomes. Two fresh implementations provide limited evidence; broader claims need additional independent evaluation.

RL should follow reliable rewards, a bounded action space, useful optimization headroom, and a fair evaluation budget. It is not a remedy for unqualified measurement labels.

Changing the objective to code size or instruction count could be a legitimate new study, but would not establish the original CPU-runtime claim.

## 31. Conclusions and claim boundaries

The implementation supports describing NeuroCompiler as a substantial compiler-policy research prototype with correctness, measurement, supervised-learning, evidence-preservation, and visualization infrastructure.

It supports the reported corpus coverage, recorded correctness, actual prior model comparisons, selected training headroom, failed expanded admission, and published artifact preservation.

It does not support general improvement over O3, attribution of BLAKE2 headroom to a learned generalizer, treating missing evaluation outcomes as measured baseline scores, or describing RL/hybrid as completed.

No reliable overall completion percentage or guaranteed remaining iteration count follows from the current evidence.

The unresolved objective is to determine whether the implemented candidate-selection approach can produce a useful policy when trained and evaluated using qualified measurements.
