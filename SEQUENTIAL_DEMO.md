# Run the trained SL / RL / hybrid demo

In Ubuntu/WSL, stop the old server with Ctrl+C, then run from your checkout:

```bash
cd ~/NeuroCompiler-live
git pull --ff-only
bash scripts/setup_presentation.sh
bash scripts/start_presentation.sh
```

Open your normal Windows browser at `http://localhost:8000` and refresh.

1. For the familiar demo choose **Prime sieve / training example**. To try a
   family excluded from the expanded model training, choose any **evaluated
   unseen-family demo** (CRC32, edit distance, heapsort, Floyd Warshall, integer
   sqrt, or rational Bezier). These have already been evaluated; repeating them
   is a demonstration, not a fresh holdout test. Their preset arguments differ.
2. For Prime sieve set arguments `1600`, stdin blank, iterations descriptor `1600`.
   For the six evaluated-family demos keep their preset arguments `500`.
3. Under **Learning policy**, select **Hybrid SL + RL · instruction-count objective**.
4. Click **Analyze & predict**. The main summary compares **Standard LLVM -O3**
   against **NeuroCompiler**, showing its learning method and selected pass sequence.
   Execution times say **Not measured** until you run the program.
5. Expand **How NeuroCompiler selected these passes** for per-step instruction
   counts, SL estimates, Q estimates, and shortlisted actions. These static counts
   are not machine instructions or speed.
6. Click **Measure execution times**, confirm trusted code, and run the comparison. For Prime sieve, expected stdout is
   `25765905600`. Runtime preference still requires native controls; smaller IR
   does not automatically win the runtime comparison. The main summary now shows
   both execution times in milliseconds and the observed difference vs -O3.
   Switch CPU/wall clocks with the labelled selector; inference and compilation
   are excluded. O1/O2 and reliability details remain under **Run & compare**.
7. Repeat with **SL · instruction-count objective** and **RL · instruction-count
   objective**. The old runtime-estimate model remains under **Legacy SL**.

The committed artifacts are trained already: **3,832 native-checked LLVM
transitions from 40 synthetic programs across 24 families**. The family-disjoint
frozen evaluation contains 12 programs from six other families. See
[complete unseen-family results](UNSEEN_EVALUATION.md); guarded policies reduce
counts on eight and retain O3 on four, but do not establish a learning-specific
or runtime advantage. The **Model & scope** tab includes the full baseline
comparison. The static checkpoint/O3 guard selects the emitted artifact before
runtime measurements. It cannot protect execution time. Normal setup does not retrain or require
a GPU. Source/tool hashes, reward definition, feature schema, action definitions,
seed and training parameters are recorded in sequential_training.json. Model
weights and dataset hash are in sequential_model.json.

SL predicts immediate pass reward. RL uses fitted Q iteration with discounted
future rewards. Hybrid retains the top three SL actions plus STOP, then selects
using the Q model. It may equal RL or perform worse than SL. A bounded four-step
horizon prevents endless inference; STOP can terminate earlier. Repeated no-op
actions can occur because the approximation and corpus are limited.

The reward is log instruction-count reduction minus a fixed 0.001 non-STOP action
cost. Recorded pass compilation time is informational; this is not a runtime or
measured-compilation-time reward. Training uses LLVM structural verification and two fixed native input checks
per transition. Native output validation is also performed by the product
before timing.

The original eight-program prototype is preserved in presentation/sequential_v1.
See [historical prototype results](presentation/SEQUENTIAL_RESULTS.md), the
[original-plan mapping and research notes](SL_RL_IMPLEMENTATION_PLAN.md), and
[a checked hybrid screenshot](presentation/screenshots/hybrid-decision.png).
The five familiar example probes are not an independent test set. Runtime-trained
RL, larger real-program coverage and untouched-program validation remain open.

Optional developer reproduction, from the repository root after setup:

```bash
.presentation/venv/bin/python scripts/train_generalization.py --output .presentation/my_fresh_rl_run
.presentation/venv/bin/python scripts/evaluate_generalization.py --run .presentation/my_fresh_rl_run
```

Use a fresh output directory. The generator refuses overwrites and does not
replace the bundled model automatically. It generates training transitions only from
the declared training families and freezes the model before the separate
evaluation command opens the new synthetic test families. It does not open
older reserved research tests.
