# NeuroCompiler — Project State and Handoff

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
