from dataclasses import dataclass
from typing import List

import compiler_gym
import numpy as np


@dataclass
class PairedRuntimeResult:
    baseline_runtimes: List[float]
    transformed_runtimes: List[float]
    speedups: List[float]

    median_baseline: float
    median_transformed: float
    median_speedup: float
    median_log_speedup: float
    improvement_percent: float


def _single_runtime(env):
    """
    One measured execution.
    CompilerGym performs the configured warmup before it.
    """
    values = np.asarray(env.observation["Runtime"], dtype=float)

    if len(values) == 0:
        raise RuntimeError("No runtime measurement returned")

    return float(np.median(values))


def measure_paired_pass(
    benchmark_uri: str,
    pass_name: str,
    pairs: int = 10,
    warmup_runs: int = 1,
):
    baseline_env = compiler_gym.make(
        "llvm-v0",
        benchmark=benchmark_uri,
    )

    transformed_env = compiler_gym.make(
        "llvm-v0",
        benchmark=benchmark_uri,
    )

    baseline_env.reset()
    transformed_env.reset()

    try:
        action_names = list(transformed_env.action_space.names)

        if pass_name not in action_names:
            raise ValueError(
                f"Unknown LLVM pass: {pass_name}"
            )

        action_id = action_names.index(pass_name)

        # Apply transformation once.
        transformed_env.step(action_id)

        # Each observation request returns one measured runtime.
        baseline_env.runtime_warmup_runs_count = warmup_runs
        baseline_env.runtime_observation_count = 1

        transformed_env.runtime_warmup_runs_count = warmup_runs
        transformed_env.runtime_observation_count = 1

        baseline_times = []
        transformed_times = []
        speedups = []

        for i in range(pairs):

            # Alternate execution order to reduce systematic bias.
            if i % 2 == 0:

                baseline = _single_runtime(baseline_env)
                transformed = _single_runtime(transformed_env)

            else:

                transformed = _single_runtime(transformed_env)
                baseline = _single_runtime(baseline_env)

            baseline_times.append(baseline)
            transformed_times.append(transformed)

            speedups.append(
                baseline / transformed
            )

        speedups_array = np.asarray(
            speedups,
            dtype=float,
        )

        median_speedup = float(
            np.median(speedups_array)
        )

        log_speedups = np.log(
            speedups_array
        )

        return PairedRuntimeResult(
            baseline_runtimes=baseline_times,
            transformed_runtimes=transformed_times,
            speedups=speedups,

            median_baseline=float(
                np.median(baseline_times)
            ),

            median_transformed=float(
                np.median(transformed_times)
            ),

            median_speedup=median_speedup,

            median_log_speedup=float(
                np.median(log_speedups)
            ),

            improvement_percent=(
                median_speedup - 1.0
            ) * 100.0,
        )

    finally:
        baseline_env.close()
        transformed_env.close()
