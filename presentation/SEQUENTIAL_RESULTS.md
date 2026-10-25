> **Historical eight-program prototype.** The default artifact has been replaced
> by the expanded model. These results apply to the preserved files in
> `presentation/sequential_v1`, not the current default model. See
> [the expanded unseen-family evaluation](../UNSEEN_EVALUATION.md).

# SL / RL / hybrid prototype results

Objective: LLVM IR instruction count. These are five familiar presentation inputs, not an independent held-out evaluation. All 90 O0/O3/selected output checks passed; runtime gains were not assessed.

| Example | Initial | O3 | SL | RL | Hybrid |
| --- | ---: | ---: | ---: | ---: | ---: |
| sieve | 168 | 101 | 63 | 65 | 65 |
| histogram | 155 | 111 | 65 | 65 | 65 |
| mix | 101 | 42 | 33 | 33 | 33 |
| matrix | 227 | 91 | 94 | 94 | 94 |
| stdin | 28 | 18 | 20 | 20 | 20 |

All new policies reduce initial IR count on these inputs. O3 still has fewer instructions on matrix and stdin. SL is slightly smaller than RL/hybrid on the familiar training sieve; hybrid is not guaranteed better. Smaller IR does not establish faster native execution.

Model/dataset/input hashes and action traces are in sequential_evaluation.json. Source and training provenance are in sequential_training.json and sequential_model.json. No validation/test set was used to select these results.
