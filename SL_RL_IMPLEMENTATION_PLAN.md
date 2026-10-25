> **25 October 2026 expansion:** the current count model uses 40 training
> programs / 24 families / 3,832 native-checked transitions, with a frozen
> 12-program / six-family evaluation and an explicit checkpoint/O3 static
> guard. The original implementation notes below describe the first
> eight-program prototype; see [the current evaluation](UNSEEN_EVALUATION.md).

# NeuroCompiler: original-plan alignment and SL/RL implementation

Prepared 25 October 2026 after reading the supplied NeuroCompiler Project Plan.pdf.

## What the original plan requires

The PDF proposes a pass-profitability supervised model followed by an RL agent
that learns pass ordering. Runtime speedup minus compilation cost is its reward.
Its examples and statements of completed work are planning context, not verified
performance evidence. Before this update the web app implemented only an earlier supervised finite-menu selector and a four-way runtime comparison. This update adds trained instruction-count SL/RL/hybrid modes; these remain experimental and are not runtime-trained or deployment-qualified.

Existing program-level feature/runtime rows are not automatically RL experience.
An RL dataset needs current IR features, action, resulting IR features, reward,
terminal state, program identity, context and available next actions. Sequences
and intermediate states matter. A static pass ranking alone is supervised
learning; a one-step choice without future rewards is a contextual bandit.

## New code in this change

- `src/rl/llvm_environment.py`: a real LLVM10 transition environment. Each action
  runs opt, verifies the resulting IR, extracts updated module features and
  records history/remaining steps. STOP and a bounded horizon terminate episodes.
  It records transformation cost but deliberately does not invent runtime rewards.
  LLVM verification is structural, not a native semantic-correctness check.
- `src/rl/offline.py`: fitted Q iteration with discounted next-state Bellman
  targets, plus a supervised immediate-reward predictor and a hybrid top-k SL
  action mask followed by Q selection. This is offline RL, not PPO/deep RL or
  the existing 156-feature presentation model.
- Runtime training rejects missing correctness/control qualification, mixed
  objectives, mixed contexts and non-training split rows. Unsupported actions,
  invalid states and nonterminal STOP transitions are rejected.
- Synthetic unit tests show that RL selects a useful preparation action for its
  delayed reward while SL chooses the larger immediate reward. Such tests are
  software validation, not compiler speedup evidence or trained artifact results.

## Actual trained prototype and product status

After the user accepted instruction count as an objective, a versioned collector
ran real LLVM transformations on eight already-opened synthetic kernels. It
produced 512 state/action/reward/next-state transitions, not 512 programs. All are
training rows. `presentation/sequential_training.json` contains the declaration,
source/tool/implementation hashes and transitions. `sequential_model.json`
contains trained immediate-reward SL and fitted-Q coefficients, normalization,
training provenance and limitations. No pickle or deep-learning runtime is needed.

The web app now has four learning-policy selections: legacy runtime-estimate SL,
new immediate-reward SL, RL, and hybrid SL+RL. The three new modes explicitly
optimize **instruction count**. They run a bounded four-step real LLVM sequence,
show the action trace and initial/selected/O3 counts, freeze the selected artifact,
and then offer the existing correctness-checked four-way native comparison.
The legacy model and frozen research studies are preserved.

There is no runtime-trained RL model or qualified unseen-real-program result.
The new model is experimental. Its action-support check is global rather than
state-local; offline extrapolation remains a limitation. Training data uses LLVM
structural verification, not native execution. The app checks output before
benchmarking each submitted program. Training fixtures and familiar demo inputs
are not held-out scientific evaluation.

## Remaining work toward the original research objective

1. **Declare a new context and splits.** Bind compiler/tools, action definitions,
   feature schema, reward objective, machine, seeds, horizon and original-program
   train/validation/test families before collecting outcomes. Preserve all old
   frozen studies and reserved workloads. Never count input variants as programs.
2. **Generate transitions.** Use bounded seeded exploration, fixed/random
   sequences and STOP. Log every attempted action and rejected transformation.
   For runtime rewards, compile and check each resulting executable on multiple
   fixtures; retain raw CPU/wall traces and unchanged-executable controls.
3. **Choose reward explicitly.** Runtime objective uses qualified timing and a
   declared compilation-cost penalty. Failed controls are missing rewards, not
   zero rewards or losses. Instruction count can bootstrap an explicitly labelled
   proxy prototype, but cannot be reported as runtime acceleration. Do not pool
   proxy and runtime rows, older incompatible clocks, or calibration data.
4. **Train SL and RL.** Fit immediate action profitability for SL. Train the
   offline Q agent on supported transitions with future rewards. Use SL-only,
   RL-only, hybrid, random and fixed-sequence ablations. SL masking can discard a
   valuable preparation action, so hybrid superiority is a hypothesis to test.
5. **Validate and freeze.** Use whole-program validation, inspect unsupported
   state/action extrapolation, then freeze model/source hashes before opening
   fresh tests. Report all regressions, timing coverage, uncertainty and overhead.
6. **Extend product evaluation.** The three proxy product modes are now integrated after actual artifact training. For future runtime-trained models, show
   state/action sequences, predicted versus realized reward, STOP reason and
   objective. Add the frozen selected executable to correctness/runtime comparison
   without changing the pre-timing prediction to whichever sample wins.

For a short presentation deadline, a proxy-trained prototype is a narrower
deliverable than validated runtime RL. The runtime objective still needs a target
that passes reward controls. The latest app results do not establish that.
The user accepted either instruction-count or execution-time reduction. The current implementation uses the instruction-count objective explicitly; runtime training remains separate future work.

## Research consulted

- [CompilerGym: Robust, Performant Compiler Optimization Environments for AI
  Research](https://arxiv.org/abs/2109.08267). Its abstract describes reusable
  production compiler environments and reproducible experimentation. It supports
  the state/action/reward environment approach; adopting it is not a speedup claim.
- [AutoPhase: Compiler Phase-Ordering for High Level Synthesis with Deep
  Reinforcement Learning](https://arxiv.org/abs/1901.04615). Its abstract supports
  sequential LLVM pass selection. Its reported gains concern circuit performance
  in high-level synthesis, not a guaranteed improvement in native CPU runtime.
- [LLVM MLGO documentation](https://llvm.org/docs/MLGO.html), consulted as an
  official reference for learned optimization integration. It is not an existing
  component of NeuroCompiler or proof that this project has equivalent results.

Only abstracts/official documentation were consulted in this pass; these notes
are not a full literature review or reproduction of those systems.
