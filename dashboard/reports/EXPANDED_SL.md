# Expanded corpus and portable native measurement

12 October 2026. This iteration addresses usable-data coverage and target
reliability. It adds eight pinned upstream libraries and a source-only Linux
runner. Earlier experiments, native artifacts, models and evidence remain
unchanged. No previous runtime label is pooled into this experiment.

## Corpus and correctness

| Item | Previous SL study | New prepared corpus |
|---|---:|---:|
| Original training implementations | 13 | 21 |
| Training inputs with correctness checks | 26 | 42 |
| Formal inputs preselected for a future admitted study | 26 | 21 |
| Fresh development implementations | Previous two were already opened | 2 |

The 21 training implementations are zlib, Expat, Lua, LZ4, jsmn, BZip2,
BLAKE2 reference, cJSON, inih, TinyExpr, Parson, picohttpparser, B-Con SHA256,
Monocypher, yyjson, json-parser, miniz, FastLZ, Frozen, yxml and MPack.
Monocypher/yyjson are explicitly opened training implementations now, rather
than fresh holdouts. Their older clocks are excluded. The six new training
libraries cover compression, DOM/SAX parsing, streaming XML and MessagePack.

The new development implementations are **sheredom/json.h and libdeflate**,
with two inputs each. Their sources are pinned and bundled; they are not
built or executed before model freeze. Input variants stay grouped by original
implementation. They are not additional independent programs. These are native
library API workloads, not full end-user application latency measurements.

`results/expanded_source_pins.json` records all 23 archives, roots, HTTPS
origins and SHA256 hashes. New GitHub sources have exact commit pins. yxml is
the explicitly identified JulStrat mirror of Yoran Heling's parser; its
copyright and archive remain intact. Original archives, including licenses,
are retained in `data/processed/expanded_sources`. The previous 15 archives
are copied only after matching their existing hashes.

Every training implementation is rebuilt from C source on the current target;
no old bitcode or native library is reused. All **42 inputs pass four settings**
against O0 and independent oracles: 168 correctness cells with two pairs each,
or 336 O0/candidate pairs. All 42 meet the minimum invocation duration.
LLVM19 native PIC compilation preserves strict floating point and disables
contraction. The 95 predictor fields use the existing timed-region analysis.

New JSON/MessagePack oracles reconstruct semantic trees in Python. The XML
oracle uses Python ElementTree, including entity normalization. Compression
requires exact reconstruction of the original bytes, checked independently:
system zlib for zlib/miniz, system LZ4 decoding for LZ4, and a specification-based
Python level-1 decoder for FastLZ. **40 native compressed streams** are checked
across O0 and all four settings. This avoids requiring identical compressed
bytes from different system-library versions.

The first Frozen adapter wrongly hashed array indices as object keys. The
upstream SAX API supplies both as `name`. A container stack now distinguishes
them; a native regression test covers nested arrays and numeric object keys.
The failed preflight and diagnostic source/output remain preserved, as does
the first build under `failed_builds`. The repaired preflight has no failures.
This correction occurs before formal source/protocol freeze.

## Frozen timing and model protocol

`results/expanded_native_20261012/frozen.json` binds sources, tool hashes,
CPU model/flags, archives, input manifests, 16 fixed model configurations and
the machine-admission budget. Native CPU2 is separate from CPU0 orchestration.
Each implementation has two correctness inputs, but formal training preselects
one input per implementation, balancing dataset breadth against timing cost.
The formal recommendation menu is O3, O2 and no-vector. Large-inline remains
available for correctness/features and is not recommended or timed for learning.

Persistent isolated children each load one DSO; the parent loads neither.
After three initial untimed invocations, the collector alternates after every
API invocation and retains all CPU/wall traces. Counts are equal and even,
calibrated from O3 only for a **200ms API CPU target per side per pair**, versus
40ms previously. These are service targets, not total process elapsed time.
Three blocks of 24 pairs retain failed controls without outlier deletion,
minimum substitution or retry-until-pass. Aggregates must sum their traces.

Both clocks independently require the unchanged 3% null-control block/interval
bounds and pooled actual starting-side/every-block order bounds. Candidate
effects additionally need both self-controls and qualified order; confirmed
gains require every block and the interval lower bound above 1.03x. Only new
qualified training effects can fit models. Preflight, calibration, admission,
CPU-screen, confirmation and earlier-study clocks are excluded.

The six-input admission cohort spans zlib random, Expat nested, LZ4 random,
json-parser nested, miniz random and MPack nested. All six must pass CPU AND wall,
followed by exactly one independent confirmation. A failed gate blocks
confirmation, training, fitting and development execution before output files
or holdout build directories are created. This is a stricter admission rule
than the previous eight-input pilot's six-pass requirement; coverage counts
must not be compared as a controlled method-effect estimate.

The CPU2 gate retains **18 cells/432 pairs** and passes **4/6 on both clocks**.
zlib fails order qualification; Expat fails order and interval/block checks.
Expat's third identical-O3 block ratio is approximately **0.9014x**, a large
difference without changing optimization. Longer batches alone therefore do
not establish reliable measurements on this target. No new training labels,
model fits or development executions follow that failed admission.

## Available CPU target screen

After the failed CPU2 study, a separately declared diagnostic screens unused
logical CPUs 1, 3 and 4. The same freshly source-built binaries and equal even
counts are valid on these identical-ISA cores of this machine; the declaration
records this reuse explicitly. No CPU2 control is repeated. All 54 cells are
retained, and all six inputs on both clocks must pass before selecting a CPU.
Selection uses the greatest minimum control margin, with lowest CPU ID ties.
Exactly one independent confirmation is allowed if a CPU qualifies; no
alternate core is tried after a failed confirmation. Sources and schedules
are bound in `results/expanded_target_declaration.json`.

None qualifies. CPU0, previously reserved for orchestration, then receives one
separately declared 18-cell screen with orchestration moved to CPU1; it also
fails. Its generic collector and CPU0 launcher are both hash-bound before any
timing in `results/expanded_cpu0_declaration.json`. The original CPU2 evidence
and three-core screen remain unchanged. No additional target search follows.

| Native logical CPU | Passed CPU controls | Passed wall controls |
|---|---:|---:|
| 2: initial study | 4/6 | 4/6 |
| 1: unused-core screen | 5/6 | 5/6 |
| 3: unused-core screen | 3/6 | 2/6 |
| 4: unused-core screen | 1/6 | 1/6 |
| 0: final unused-core screen | 3/6 | 3/6 |

All five logical CPUs have been checked, with **90 cells/2,160 pairs** overall.
Both conditional confirmation files record no selected target and zero native
confirmation cells. All these clocks are diagnostic admission data, never
training labels. This does not prove that every individual program is
unmeasurable; it means no target meets this study's conservative admission
rule. CPU1's five valid controls do not silently replace the declared six-pass
requirement. Gate relaxation after observing results is not used.

The expanded corpus contributes **no new qualified training labels or model
fits in this run**. The preceding study's 11 qualified targets remain separate
and unchanged. The next performance experiment needs a quieter target and a
new context/declaration; another hyperparameter sweep on these blocked clocks
does not resolve the issue. A learned gain over O3 is still unestablished.

## Portable source runner

`results/expanded_portable_sources.zip` is approximately 16MB and includes
source code, checksum-pinned archives and licenses, dependency pins, a per-file
SHA manifest and `PORTABLE_RUNNER.md`. It excludes generated NeuroCompiler
native binaries, fitted models and previous runtime labels. It supports Linux
with Python3.10, LLVM19 and a system LZ4 decoder; this workflow does not import
CompilerGym or need LLVM10. All upstream archives are bundled, so builds need
no new upstream download.

The relocation test extracts it into a temporary directory, verifies its SHA
manifest, imports project modules exclusively from that relocated tree, builds
a fresh worker/FastLZ library, checks all four pipelines and independently
decodes five streams. The test confirms no CompilerGym import and 95 feature
fields. This validates relocation on the current CPU, not performance on a
different machine. Another CPU requires fresh builds, a new context directory
and new admission; Intel-native binaries are not portable Ryzen binaries.

From the extracted directory, with a configured LLVM19 path and allowed CPUs:

```bash
export NEUROCOMPILER_LLVM19=/usr/lib/llvm-19/bin
taskset -c 0 python scripts/expanded_study.py prepare --output runs/local_001 --cpu 2
taskset -c 0 python scripts/expanded_study.py declare --output runs/local_001
taskset -c 0 python scripts/expanded_study.py gate --output runs/local_001
```

Only if all six pass both clocks, run `confirmation`. Only if that independent
check also passes, run `train`, `fit`, then `development` with the same output
directory. `evaluate_expanded.py --output runs/local_001` reconstructs frozen
development results; `expanded_study.py verify --output runs/local_001` checks
evidence without sampling. Completed collectors support `--resume` and never
resample a complete study. One-shot declarations/models refuse overwrite.

All **123 tests** pass, including actual native adapter regression, independent
FastLZ decoding/corrupt-stream bounds, MessagePack specification examples,
archive traversal guards, whole-program CV separation and exclusion of the
unmeasured inline setting. Earlier runtime outcomes and the 12.1% BLAKE2
training-headroom result remain separate. No new learned O3 gain is claimed.
No completion percentage or guaranteed iteration count follows from this work.

## Evidence audit and persistence

The base audit independently regenerates all 42 inputs/oracles, checks 724
materialized upstream files against their pinned archives, reconstructs 12
clock/order groups, rejects nine evidence corruptions and verifies all four
downstream actions reject the failed gate. No fresh development build directory
or new model/label file exists. All 53 directly embedded generated files from
the prior persistent snapshot remain unchanged; the nested older evidence
remains protected by that ZIP's unchanged hash.

The three-core audit independently checks 54 declared starting seeds and 36
clock/order groups, rejects five corruptions and verifies completed resumes
preserve screen/confirmation/original failed-gate hashes. The CPU0 audit checks
18 seeds and 12 clock/order groups and preserves its completed hashes.
The helper context equals the frozen CPU2 context; the diagnostic target CPUs
are separately explicit in their declarations and collector calls.

The source-only kit passes SHA/CRC verification and relocated fresh native
build testing. The full immutable `results/expanded_iteration.zip` preserves
current source/data/results and that kit, nesting the unchanged
`persistent_iteration.zip` plus its adjacent completion log. Its own
`expanded_snapshot.log` is written after ZIP creation and remains outside it.

Startup instructions are saved as a draft while existing install/network/
repository settings are retained. Review/save environment settings and Publish
the prepared filesystem snapshot to retain local work. No new package/service
or Git commit/push is performed. Fresh-task restoration and another physical
machine's performance remain untested.
