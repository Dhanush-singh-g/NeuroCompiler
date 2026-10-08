import compiler_gym
import numpy as np

from configs.passes import CURATED_PASSES
from src.benchmarks.runtime import measure_runtime


BENCHMARK = "benchmark://cbench-v1/qsort"

WARMUPS = 2
MEASUREMENTS = 10


def main():

    env = compiler_gym.make(
        "llvm-v0",
        benchmark=BENCHMARK,
    )

    action_names = list(env.action_space.names)

    # ---------------------------------
    # Baseline runtime
    # ---------------------------------

    env.reset()

    baseline = measure_runtime(
        env,
        warmup_runs=WARMUPS,
        measurement_runs=MEASUREMENTS,
    )

    baseline_runtime = baseline.median

    print()
    print("Benchmark:", BENCHMARK)
    print("Baseline median:", baseline_runtime)
    print()

    print(
        f"{'Pass':20} "
        f"{'Runtime(ms)':>12} "
        f"{'Speedup':>10} "
        f"{'Change %':>10} "
        f"{'IR':>10}"
    )

    print("-" * 70)

    results = []

    # ---------------------------------
    # Test each pass independently
    # ---------------------------------

    for pass_name in CURATED_PASSES:

        env.reset()

        action_id = action_names.index(pass_name)

        before_ir = env.observation["IrInstructionCount"]

        env.step(action_id)

        after_ir = env.observation["IrInstructionCount"]

        result = measure_runtime(
            env,
            warmup_runs=WARMUPS,
            measurement_runs=MEASUREMENTS,
        )

        runtime = result.median

        speedup = baseline_runtime / runtime

        change_percent = (
            (baseline_runtime - runtime)
            / baseline_runtime
            * 100
        )

        results.append(
            (
                pass_name,
                runtime,
                speedup,
                change_percent,
                before_ir,
                after_ir,
            )
        )

    # ---------------------------------
    # Sort best → worst
    # ---------------------------------

    results.sort(
        key=lambda x: x[2],
        reverse=True,
    )

    for (
        pass_name,
        runtime,
        speedup,
        change_percent,
        before_ir,
        after_ir,
    ) in results:

        print(
            f"{pass_name:20} "
            f"{runtime * 1000:12.3f} "
            f"{speedup:10.4f} "
            f"{change_percent:9.2f}% "
            f"{before_ir:4}->{after_ir:<4}"
        )

    env.close()


if __name__ == "__main__":
    main()
