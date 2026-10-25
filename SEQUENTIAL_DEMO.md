# Run the trained SL / RL / hybrid demo

In Ubuntu/WSL, stop the old server with Ctrl+C, then run from your checkout:

```bash
cd ~/NeuroCompiler-live
git pull --ff-only
bash scripts/setup_presentation.sh
bash scripts/start_presentation.sh
```

Open your normal Windows browser at `http://localhost:8000` and refresh.

1. Choose **Prime sieve / training example**.
2. Set arguments `1600`, stdin blank, iterations descriptor `1600`.
3. Under **Learning policy**, select **Hybrid SL + RL · instruction-count objective**.
4. Click **Analyze & predict**. The main summary compares **Standard LLVM -O3**
   against **NeuroCompiler**, showing its learning method and selected pass sequence.
   Execution times say **Not measured** until you run the program.
5. Expand **How NeuroCompiler selected these passes** for per-step instruction
   counts, SL estimates, Q estimates, and shortlisted actions. These static counts
   are not machine instructions or speed.
6. Click **Measure execution times**, confirm trusted code, and run the comparison. Expected stdout is
   `25765905600`. Runtime preference still requires native controls; smaller IR
   does not automatically win the runtime comparison. The main summary now shows
   both execution times in milliseconds and the observed difference vs -O3.
   Switch CPU/wall clocks with the labelled selector; inference and compilation
   are excluded. O1/O2 and reliability details remain under **Run & compare**.
7. Repeat with **SL · instruction-count objective** and **RL · instruction-count
   objective**. The old runtime-estimate model remains under **Legacy SL**.

The committed artifacts are trained already: 512 real LLVM transitions from eight
previously opened synthetic programs. Normal setup does not retrain or require
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
measured-compilation-time reward. Training uses LLVM structural verification.
Native output validation is performed separately by the product before timing.

See [prototype results](presentation/SEQUENTIAL_RESULTS.md), the
[original-plan mapping and research notes](SL_RL_IMPLEMENTATION_PLAN.md), and
[a checked hybrid screenshot](presentation/screenshots/hybrid-decision.png).
The five familiar example probes are not an independent test set. Runtime-trained
RL, larger real-program coverage and untouched-program validation remain open.

Optional developer reproduction, from the repository root after setup:

```bash
.presentation/venv/bin/python scripts/train_sequential.py --output .presentation/my_fresh_rl_run
```

Use a fresh output directory. The generator refuses overwrites and does not
replace the bundled model automatically. It generates training transitions from
the declared eight synthetic sources; it does not open reserved research tests.
