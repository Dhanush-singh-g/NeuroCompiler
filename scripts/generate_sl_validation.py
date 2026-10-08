import csv
import math
from pathlib import Path

import compiler_gym
import numpy as np

from configs.benchmarks import VALIDATION_BENCHMARKS
from configs.passes import CURATED_PASSES


OUTPUT = Path("data/processed/sl_validation.csv")

WARMUPS = 1
MEASUREMENTS = 3

POSITIVE_THRESHOLD = 1.03
NEGATIVE_THRESHOLD = 0.97


def measure_runtime(env):
    env.runtime_warmup_runs_count = WARMUPS
    env.runtime_observation_count = MEASUREMENTS

    values = np.asarray(
        env.observation["Runtime"],
        dtype=float,
    )

    if len(values) == 0:
        raise RuntimeError("No runtime measurements returned")

    return float(np.median(values))


def classify(speedup):
    if speedup > POSITIVE_THRESHOLD:
        return "beneficial"

    if speedup < NEGATIVE_THRESHOLD:
        return "harmful"

    return "neutral"


def main():

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    total = ( len(VALIDATION_BENCHMARKS)*len(CURATED_PASSES))
    

    sample_number = 0

    for benchmark_index, benchmark in enumerate(
        VALIDATION_BENCHMARKS,
        start=1,
    ):

        print()
        print("=" * 70)
        print(
            f"Benchmark "
            f"{benchmark_index}/{len(VALIDATION_BENCHMARKS)}:"
        )
        print(benchmark)
        print("=" * 70)

        # Get initial-state features once.
        feature_env = compiler_gym.make(
            "llvm-v0",
            benchmark=benchmark,
        )

        feature_env.reset()

        try:
            features = list(
                feature_env.observation["Autophase"]
            )

            assert len(features) == 56

        finally:
            feature_env.close()

        for pass_name in CURATED_PASSES:

            sample_number += 1

            print(
                f"[{sample_number}/{total}] "
                f"{pass_name}"
            )

            baseline_env = compiler_gym.make(
                "llvm-v0",
                benchmark=benchmark,
            )

            transformed_env = compiler_gym.make(
                "llvm-v0",
                benchmark=benchmark,
            )

            try:
                baseline_env.reset()
                transformed_env.reset()

                action_names = list(
                    transformed_env.action_space.names
                )

                action_id = action_names.index(
                    pass_name
                )

                ir_before = transformed_env.observation[
                    "IrInstructionCount"
                ]

                transformed_env.step(action_id)

                ir_after = transformed_env.observation[
                    "IrInstructionCount"
                ]

                # Alternate which one is measured first
                # across samples to reduce systematic bias.
                if sample_number % 2 == 0:

                    transformed_runtime = measure_runtime(
                        transformed_env
                    )

                    baseline_runtime = measure_runtime(
                        baseline_env
                    )

                else:

                    baseline_runtime = measure_runtime(
                        baseline_env
                    )

                    transformed_runtime = measure_runtime(
                        transformed_env
                    )

                speedup = (
                    baseline_runtime
                    / transformed_runtime
                )

                log_speedup = math.log(speedup)

                label = classify(speedup)

                row = {
                    "benchmark": benchmark,
                    "pass_name": pass_name,
                    "pass_id": action_id,
                    "ir_before": ir_before,
                    "ir_after": ir_after,
                    "baseline_runtime": baseline_runtime,
                    "transformed_runtime": transformed_runtime,
                    "speedup": speedup,
                    "log_speedup": log_speedup,
                    "label": label,
                }

                for i, value in enumerate(features):
                    row[f"feature_{i}"] = value

                rows.append(row)

                print(
                    f"    "
                    f"{baseline_runtime * 1000:.3f} ms"
                    f" -> "
                    f"{transformed_runtime * 1000:.3f} ms"
                    f" | {speedup:.3f}x"
                    f" | {label}"
                )

            except Exception as exc:

                print(
                    "    FAILED:",
                    exc,
                )

            finally:
                baseline_env.close()
                transformed_env.close()

            # Save continuously.
            if rows:

                with OUTPUT.open(
                    "w",
                    newline="",
                ) as f:

                    writer = csv.DictWriter(
                        f,
                        fieldnames=rows[0].keys(),
                    )

                    writer.writeheader()
                    writer.writerows(rows)

    print()
    print("=" * 70)
    print("DATASET COMPLETE")
    print("=" * 70)

    print("Samples:", len(rows))
    print("Output:", OUTPUT)


if __name__ == "__main__":
    main()
